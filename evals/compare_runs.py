"""Compare two arms of saved trials from their v1 result records (EVAL-012 WP-01).

    python evals/compare_runs.py .eval-runs/<iteration> --incumbent LABEL --candidate LABEL [--json]

Exit 0 once the report is produced, whatever it shows (a comparison is not a verdict and promotes
nothing), and 3 when it cannot be. It sits outside the runner package on purpose: the runner's
identity binds every file that grades a trial, and a report that grades nothing must not move it.

The comparison reads `record.json` only (DEC-22) and never grades. Each trial keeps the verdict its
record was written with (assessment revision 0). An arm pools its trials of one case against that
case's native threshold, taken from the scenario only while the scenario still has the digest the
records name, and a slot whose published run has no usable record pools as INCONCLUSIVE. A pair is a
gain, regression or unchanged only when both arms ran the same trial slots of the same case under
the same conditions; anything else stays visible as unmeasured, missing or not compared, never as a
pass. A case a label ran before v1 records existed is listed as legacy with the gaps its files leave;
it is not compared, and its cost is unknown. The report names folders relative to the bundle, so a
relocated bundle reports the same.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from probe import batches, catalog, fingerprints
from probe.outcomes import State
from probe.records import RECORD_FORMAT, RecordV1
from pydantic import ValidationError

REPORT_FORMAT = {"name": "save-toolkit.eval-comparison", "version": 1}
OUTCOMES = ("gain", "regression", "unchanged", "unmeasured", "missing_pair", "not_compared")

# The provenance fields that identify a legacy run's candidate and runner.
IDENTITY_FIELDS = ("plugin_commit", "plugin_source_sha256", "runner_source_sha256")
# An unpublished attempt folder: `.run-N-attempt-<token>` or `.run-N-previous-<token>`.
HIDDEN_SLOT = re.compile(r"^\.run-([1-9][0-9]*)-")

# What both arms must share for a pair to be compared; the candidate's plugin is what may differ.
MATCHED = (
    "case_sha256",
    "scenario_sha256",
    "requested_model",
    "observed_models",
    "runtime",
    "wall_clock_seconds",
    "turn_limit",
)
# What one arm's trials of a case must share to pool, as a batch refuses to pool anything else.
POOLED = (*MATCHED, "plugin_source_sha256")
DECIDED = (State.PASS, State.FAIL)


@dataclass(frozen=True)
class Trial:
    """One attempt with a usable record, by its folder relative to the bundle."""

    folder: str
    record: RecordV1
    missing_evidence: tuple[str, ...]


@dataclass
class Slot:
    """A trial slot's attempts: the published one, the kept ones, and how many records were unusable."""

    final: Trial | None = None
    kept: list[Trial] = field(default_factory=list)
    unusable: int = 0
    unpublished: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Label:
    """Everything one label holds in the bundle."""

    cases: dict[str, dict[int, Slot]] = field(default_factory=dict)
    problems: list[dict[str, str]] = field(default_factory=list)
    legacy: list[dict[str, Any]] = field(default_factory=list)
    # Hidden attempt folders, paid for and never published: each one's record, or None when unreadable.
    unpublished: list[RecordV1 | None] = field(default_factory=list)


def label_present(bundle: Path, label: str) -> bool:
    return any((case_dir / label).is_dir() for case_dir in bundle.glob("eval-*"))


def compare_bundle(
    bundle: Path, incumbent: str, candidate: str, scenarios: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """The logical comparison of two labels in one bundle: host-independent, so it can be diffed."""
    labels = {label: read_label(bundle, label) for label in (incumbent, candidate)}
    mixed = {label: _mixed_candidates(held) for label, held in labels.items()}
    by_id = {spec["id"]: spec for spec in scenarios}
    cases = []
    for case_id in sorted(labels[incumbent].cases.keys() | labels[candidate].cases.keys()):
        old = _assess(labels[incumbent].cases.get(case_id), by_id.get(case_id), mixed[incumbent])
        new = _assess(labels[candidate].cases.get(case_id), by_id.get(case_id), mixed[candidate])
        outcome, reason = _pair(old, new)
        cases.append({"case": case_id, "outcome": outcome, "reason": reason, "incumbent": old, "candidate": new})
    return {
        "format": REPORT_FORMAT,
        "incumbent": incumbent,
        "candidate": candidate,
        "outcomes": {name: sum(case["outcome"] == name for case in cases) for name in OUTCOMES},
        "arms": {label: _arm_summary(held) for label, held in labels.items()},
        "cases": cases,
        "problems": sorted(
            (problem for held in labels.values() for problem in held.problems), key=lambda p: p["folder"]
        ),
        "legacy": sorted((run for held in labels.values() for run in held.legacy), key=lambda r: r["folder"]),
    }


def _candidates(held: Label) -> list[str]:
    """The candidate digests a label's published trials name, across all its cases."""
    finals = (slot.final for case in held.cases.values() for slot in case.values() if slot.final)
    return sorted({digest for t in finals if (digest := t.record.candidate.plugin_source_sha256)})


def _mixed_candidates(held: Label) -> str | None:
    """Why a label is not one candidate: its outcome counts would add up several candidates' results."""
    digests = _candidates(held)
    return f"the label holds {len(digests)} candidates across its cases" if len(digests) > 1 else None


def read_label(bundle: Path, label: str) -> Label:
    held = Label()
    for case_dir in sorted(bundle.glob("eval-*")):
        label_dir = case_dir / label
        if not label_dir.is_dir():
            continue
        case_id = case_dir.name.removeprefix("eval-")
        hidden = []
        for folder in sorted(label_dir.glob(".run-*")):
            read = _read_record(folder / "record.json")
            saved = read if isinstance(read, RecordV1) else None
            held.unpublished.append(saved)
            where = folder.relative_to(bundle).as_posix()
            cost = "its record gives its cost" if saved else "its cost is unknown"
            held.problems.append(
                {
                    "folder": where,
                    "problem": f"an unpublished attempt folder (in flight, or left by a failed move): "
                    f"not compared; {cost}",
                }
            )
            match = HIDDEN_SLOT.match(folder.name)
            if match:
                hidden.append((int(match.group(1)), {"folder": where, "cost": _cost(saved) if saved else None}))
        folders = list(_attempt_folders(label_dir))
        # A case the label ran before v1 records existed is legacy throughout. The runner that writes
        # records writes attempt.json as each attempt starts, so once any folder of the case holds
        # either, one without a record is an attempt whose record was refused or never written: its
        # slot stays and fails to measure, so the arm never pools over fewer trials than it ran.
        if not any((folder / "record.json").exists() or (folder / "attempt.json").exists() for folder, _, _ in folders):
            for folder, _, _ in folders:
                where = folder.relative_to(bundle).as_posix()
                held.legacy.append({"folder": where, "label": label, "gaps": _legacy_gaps(folder)})
            continue
        slots: dict[int, Slot] = {}
        for folder, slot, number in folders:
            where = folder.relative_to(bundle).as_posix()
            entry = slots.setdefault(slot, Slot())
            record = _usable_record(folder, case_id, label, slot, number)
            if isinstance(record, str):
                held.problems.append({"folder": where, "problem": record})
                entry.unusable += 1
                continue
            trial = Trial(where, record, _unavailable(folder, where, record))
            if number is None:
                entry.final = trial
            else:
                entry.kept.append(trial)
        # An attempt that never published still started its slot: a slot only it holds fails to
        # measure, and an arm that tried a slot the other did not is not set beside it.
        for slot, row in hidden:
            slots.setdefault(slot, Slot()).unpublished.append(row)
        held.cases[case_id] = slots
    return held


def _attempt_folders(label_dir: Path) -> Iterator[tuple[Path, int, int | None]]:
    """Each attempt folder as (folder, slot, kept number): run-N is the slot's published attempt and
    attempts/run-N/<k> a kept one, superseded or incomplete."""
    for run, slot in _numbered(label_dir, "run-"):
        yield run, slot, None
    for history, slot in _numbered(label_dir / "attempts", "run-"):
        for kept, number in _numbered(history, ""):
            yield kept, slot, number


def _numbered(parent: Path, prefix: str) -> list[tuple[Path, int]]:
    """The folders named `<prefix><positive number>` as the runner writes it (`run-1`, never `run-01`, so
    two folders cannot claim one slot), in numeric order on every host."""
    found = []
    if parent.is_dir():
        for child in parent.iterdir():
            digits = child.name.removeprefix(prefix) if child.name.startswith(prefix) else ""
            if child.is_dir() and digits.isascii() and digits.isdigit() and digits == str(int(digits)) != "0":
                found.append((child, int(digits)))
    return sorted(found, key=lambda item: item[1])


def _unavailable(folder: Path, where: str, record: RecordV1) -> tuple[str, ...]:
    """The evidence links a reviewer could not open: missing, or present but unreadable."""
    unavailable = []
    for path in record.evidence.values():
        try:
            with (folder / path).open("rb"):
                pass
        except OSError:
            unavailable.append(f"{where}/{path}")
    return tuple(unavailable)


def _usable_record(folder: Path, case_id: str, label: str, slot: int, number: int | None) -> RecordV1 | str:
    """The folder's record, or why it cannot be used."""
    if not (folder / "record.json").exists():
        published = "published" if number is None else "kept"
        return (
            f"{published} without record.json, so it cannot be measured "
            "(a refused or unwritten record, or a run from before v1 records)"
        )
    record = _read_record(folder / "record.json")
    if isinstance(record, str):
        return record
    return _folder_problem(record, case_id, label, slot, number) or record


def _read_record(path: Path) -> RecordV1 | str:
    """The record at `path`, or why it cannot be used: never a partial reading."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "record is not UTF-8"
    except OSError:  # the error text names the host's reason, which would differ between hosts
        return "record cannot be read"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return f"record is not valid JSON (line {exc.lineno}, column {exc.colno})"
    form = data.get("format") if isinstance(data, dict) else None
    if not isinstance(form, dict) or form.get("name") != RECORD_FORMAT["name"]:
        return "not a save-toolkit eval record"
    if form.get("version") != RECORD_FORMAT["version"]:
        return f"record version {form.get('version')!r} is not supported; this reader takes version 1"
    try:
        return RecordV1.model_validate_json(text)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        return f"record breaks the v1 contract at {where or 'the top level'}: {first['type']}"


def _folder_problem(record: RecordV1, case_id: str, label: str, slot: int, number: int | None) -> str | None:
    """How a record disagrees with the folder the runner filed it in. A copied record, or a superseded
    one whose state update failed, would otherwise count as a second published trial."""
    attempt = record.attempt
    found = []
    if record.case.id != case_id:
        found.append(f"case {record.case.id!r} filed under {case_id!r}")
    if attempt.label != label:
        found.append(f"label {attempt.label!r} filed under {label!r}")
    if attempt.slot != slot:
        found.append(f"slot {attempt.slot} filed under run-{slot}")
    if (attempt.state == "final") != (number is None):
        found.append(f"state {attempt.state} filed as {'the published run' if number is None else 'a kept attempt'}")
    if number is not None and attempt.number != number:
        found.append(f"attempt {attempt.number} filed as {number}")
    return "record disagrees with its folder: " + "; ".join(found) if found else None


def _legacy_gaps(folder: Path) -> list[str]:
    """What a run folder without a v1 record cannot supply. A gap is cleared only by content that fills
    it: an unreadable or partial provenance.json leaves the identity gaps named."""
    try:
        loaded = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        loaded = None
    provenance = loaded if isinstance(loaded, dict) else {}
    gaps = ["no v1 record"]
    if not (folder / "grading.json").is_file():
        gaps.append("verdict and checks")
    if not all(provenance.get(field) for field in IDENTITY_FIELDS):
        gaps.append("candidate and runner identity")
    if not (folder / "timing.json").is_file():
        gaps.append("cost")
    if not provenance.get("runtime"):
        gaps.append("CLI version and host")
    return gaps


def _conditions(record: RecordV1) -> dict[str, Any]:
    runtime = record.conditions.runtime
    return {
        "case_sha256": record.case.case_sha256,
        "scenario_sha256": record.case.scenario_sha256,
        "requested_model": record.conditions.requested_model,
        "observed_models": record.conditions.observed_models,
        "runtime": runtime.model_dump(mode="json") if runtime else None,
        "wall_clock_seconds": record.conditions.wall_clock_seconds,
        "turn_limit": record.conditions.turn_limit,
        "plugin_source_sha256": record.candidate.plugin_source_sha256,
        "plugin_commit": record.candidate.plugin_commit,
    }


def _identity_gap(conditions: Mapping[str, Any]) -> str | None:
    """What a batch would refuse to pool on: one resolved model, a candidate digest, a CLI and a host,
    and the scenario identity that binds the runner which graded them."""
    runtime = conditions["runtime"] or {}
    if not conditions["scenario_sha256"]:
        return "the scenario identity is unknown"
    if len(conditions["observed_models"] or []) != 1:
        return "the trials do not record exactly one resolved model"
    if not conditions["plugin_source_sha256"]:
        return "the candidate digest is unknown"
    if not runtime.get("cli_version") or not runtime.get("host_platform"):
        return "the CLI version or host is unknown"
    return None


def _assess(
    slots: Mapping[int, Slot] | None, spec: Mapping[str, Any] | None, mixed: str | None = None
) -> dict[str, Any] | None:
    """One arm's trials of one case, pooled as the runner pools a batch, or None when it has none."""
    if not slots:
        return None
    trials = [_trial_row(number, slot) for number, slot in sorted(slots.items())]
    finals = [slot.final for slot in slots.values() if slot.final]
    # A slot without a usable published record failed to measure: it pools as INCONCLUSIVE.
    states: list[str] = [row["status"] or State.INCONCLUSIVE for row in trials]
    row: dict[str, Any] = {
        "verdict": None,
        "reason": None,
        "threshold": None,
        "passed": states.count(State.PASS),
        "slots": len(slots),
        "conditions": None,
        "trials": trials,
    }
    if not finals:
        return {**row, "reason": "no published trial has a usable record"}
    if mixed:
        return {**row, "verdict": State.INCONCLUSIVE, "reason": mixed}
    each = [_conditions(t.record) for t in finals]
    varied = [key for key in POOLED if len({json.dumps(c[key], sort_keys=True) for c in each}) > 1]
    if varied:
        reason = f"the trials are not one measurement: they differ in {', '.join(varied)}"
        return {**row, "verdict": State.INCONCLUSIVE, "reason": reason}
    conditions = each[0]
    row["conditions"] = conditions
    gap = _identity_gap(conditions)
    if gap:
        return {**row, "verdict": State.INCONCLUSIVE, "reason": gap}
    if spec is None:
        return {**row, "reason": "no scenario with this id was given, so its threshold is unknown"}
    if fingerprints.case_digest(spec) != conditions["case_sha256"]:
        return {**row, "reason": "the scenario given differs from the case these trials measured"}
    threshold = batches.effective_threshold(spec, None)
    return {**row, "verdict": batches.aggregate_verdict(states, threshold), "threshold": threshold}


def _trial_row(number: int, slot: Slot) -> dict[str, Any]:
    final = slot.final
    record = final.record if final else None
    states = [check.state for check in record.checks] if record else []
    return {
        "slot": number,
        "status": record.verdict.status if record else None,
        "folder": final.folder if final else None,
        "run_end": record.run_end.kind if record else None,
        "checks": {state.value: states.count(state) for state in State},
        "truncated_checks": sum(check.evidence_truncated for check in record.checks) if record else 0,
        "evidence": _links(final) if final else [],
        "missing_evidence": list(final.missing_evidence) if final else [],
        "cost": _cost(final.record) if final else None,
        "kept": [
            {
                "attempt": t.record.attempt.number,
                "state": t.record.attempt.state,
                "reason": t.record.attempt.reason,
                "folder": t.folder,
                "status": t.record.verdict.status,
                "evidence": _links(t),
                "missing_evidence": list(t.missing_evidence),
                "cost": _cost(t.record),
            }
            for t in sorted(slot.kept, key=lambda t: t.record.attempt.number)
        ],
        "unpublished": slot.unpublished,
        "attempts": {
            "final": int(final is not None),
            "superseded": sum(t.record.attempt.state == "superseded" for t in slot.kept),
            "incomplete": sum(t.record.attempt.state == "incomplete" for t in slot.kept),
            "unusable": slot.unusable,
            "unpublished": len(slot.unpublished),
        },
    }


def _links(trial: Trial) -> list[str]:
    return [f"{trial.folder}/{path}" for path in trial.record.evidence.values()]


def _cost(record: RecordV1) -> dict[str, Any]:
    """The record's own figures: a known floor reads as a total only when `complete` is true."""
    return record.cost.model_dump(include={"trial_usd", "judge_usd", "known_usd", "complete"})


def _pair(incumbent: Mapping[str, Any] | None, candidate: Mapping[str, Any] | None) -> tuple[str, str | None]:
    if incumbent is None or candidate is None:
        return "missing_pair", f"the {'incumbent' if incumbent is None else 'candidate'} has no trial with a v1 record"
    # A matched trial policy: an arm whose batch stopped early ran fewer slots, and its fewer trials
    # meet a threshold more easily, so it is never set beside a complete one.
    old_slots, new_slots = ([trial["slot"] for trial in arm["trials"]] for arm in (incumbent, candidate))
    if old_slots != new_slots:
        return "not_compared", f"the arms ran different trial slots: {old_slots} and {new_slots}"
    old, new = incumbent["conditions"], candidate["conditions"]
    if old and new:
        differ = [key for key in MATCHED if old[key] != new[key]]
        if differ:
            return "not_compared", f"the arms differ in {', '.join(differ)}"
    verdicts = (incumbent["verdict"], candidate["verdict"])
    unmeasured = [
        role for role, verdict in zip(("incumbent", "candidate"), verdicts, strict=True) if verdict not in DECIDED
    ]
    if unmeasured:
        return "unmeasured", f"no PASS or FAIL verdict for the {' or the '.join(unmeasured)}"
    if verdicts[0] == verdicts[1]:
        return "unchanged", None
    return ("gain" if verdicts[1] == State.PASS else "regression"), None


def _arm_summary(held: Label) -> dict[str, Any]:
    slots = [slot for case in held.cases.values() for slot in case.values()]
    trials = [t for slot in slots for t in ([slot.final] if slot.final else []) + slot.kept]
    published = [slot.final.record.verdict.status for slot in slots if slot.final]
    costs = [t.record.cost for t in trials] + [record.cost for record in held.unpublished if record]
    # Attempts with no figures this reader can use: unusable records, unreadable unpublished folders
    # and legacy runs. Their cost and judge calls are unknown, never zero.
    unread = sum(slot.unusable for slot in slots) + held.unpublished.count(None) + len(held.legacy)
    return {
        "cases": len(held.cases),
        "candidates": _candidates(held),
        "slots": len(slots),
        "published_trials": {state.value: published.count(state) for state in State},
        "slots_without_trial": sum(slot.final is None for slot in slots),
        "attempts": {
            "final": len(published),
            "superseded": sum(t.record.attempt.state == "superseded" for t in trials),
            "incomplete": sum(t.record.attempt.state == "incomplete" for t in trials),
            "unusable": sum(slot.unusable for slot in slots),
            "unpublished": len(held.unpublished),
        },
        "later_assessments": sum(len(t.record.assessments) for t in trials),
        "truncated_checks": sum(check.evidence_truncated for t in trials for check in t.record.checks),
        "missing_evidence": sum(len(t.missing_evidence) for t in trials),
        "legacy_runs": len(held.legacy),
        "cost": {
            # Superseded, incomplete and readable unpublished attempts were paid for too.
            "known_usd": round(math.fsum(cost.known_usd or 0.0 for cost in costs), 6),
            "unknown_cost_attempts": sum(cost.complete is not True for cost in costs) + unread,
            "judge_live_calls": sum(cost.judge_live_calls or 0 for cost in costs),
            "judge_cached_calls": sum(cost.judge_cached_calls or 0 for cost in costs),
            "judge_calls_unknown_attempts": sum(
                cost.judge_live_calls is None or cost.judge_cached_calls is None for cost in costs
            )
            + unread,
        },
    }


def render_text(report: Mapping[str, Any], bundle: Path) -> str:
    """The report for a person: counts first, then each case, then what could not be compared."""
    lines = [
        f"comparison of {report['incumbent']} (incumbent) and {report['candidate']} (candidate) in {bundle}",
        "each trial keeps its recorded verdict (assessment revision 0); arms pool against each case's native threshold",
        "",
    ]
    for role in ("incumbent", "candidate"):
        arm = report["arms"][report[role]]
        published, attempts, cost = arm["published_trials"], arm["attempts"], arm["cost"]
        lines.append(
            f"{role} {report[role]}: {arm['cases']} case(s), {arm['slots']} slot(s); published trials "
            f"{published['PASS']} PASS, {published['FAIL']} FAIL, {published['INCONCLUSIVE']} INCONCLUSIVE; "
            f"{arm['slots_without_trial']} slot(s) without a trial; attempts {attempts['final']} final, "
            f"{attempts['superseded']} superseded, {attempts['incomplete']} incomplete, {attempts['unusable']} "
            f"unusable, {attempts['unpublished']} unpublished; USD {cost['known_usd']:.6f} known, {cost['unknown_cost_attempts']} attempt(s) of unknown "
            f"cost; {arm['missing_evidence']} missing evidence file(s), {arm['truncated_checks']} truncated "
            f"check(s), {arm['legacy_runs']} legacy run(s)"
        )
    lines += ["", ", ".join(f"{count} {name.replace('_', ' ')}" for name, count in report["outcomes"].items()), ""]
    for case in report["cases"]:
        sides = " -> ".join(_side(case[role]) for role in ("incumbent", "candidate"))
        reason = f" ({case['reason']})" if case["reason"] else ""
        lines.append(f"{case['outcome'].replace('_', ' '):<13} {case['case']}  {sides}{reason}")
        lines += _attempt_lines(case)
    if report["problems"]:
        lines += ["", "problems:"] + [f"  {p['folder']}: {p['problem']}" for p in report["problems"]]
    if report["legacy"]:
        lines += ["", "legacy runs, not compared, cost unknown:"]
        lines += [f"  {run['folder']}: {', '.join(run['gaps'])}" for run in report["legacy"]]
    return "\n".join(lines)


def _attempt_lines(case: Mapping[str, Any]) -> list[str]:
    """Every attempt behind a case line, by folder, so the counts above can be traced to evidence."""
    lines = []
    for role in ("incumbent", "candidate"):
        for trial in (case[role] or {}).get("trials", []):
            published = (
                f"{trial['status']} {trial['folder']} ({_usd(trial['cost'])})" if trial["folder"] else "no trial"
            )
            lines.append(f"    {role} slot {trial['slot']}: {published}")
            for kept in trial["kept"]:
                verdict = kept["status"] or "no verdict"
                lines.append(
                    f"      kept attempt {kept['attempt']} {kept['state']} {verdict} {kept['folder']} ({_usd(kept['cost'])})"
                )
            lines += [f"      unpublished {row['folder']} ({_usd(row['cost'])})" for row in trial["unpublished"]]
            missing = [
                *trial["missing_evidence"],
                *(link for kept in trial["kept"] for link in kept["missing_evidence"]),
            ]
            lines += [f"      unavailable evidence {link}" for link in missing]
    return lines


def _usd(cost: Mapping[str, Any] | None) -> str:
    known = (cost or {}).get("known_usd")
    if known is None:
        return "USD unknown"
    return f"USD {known:.6f}" + ("" if cost and cost.get("complete") else ", a floor")


def _side(arm: Mapping[str, Any] | None) -> str:
    if arm is None:
        return "none"
    verdict = arm["verdict"] or "no verdict"
    reason = f" [{arm['reason']}]" if arm["reason"] and arm["verdict"] in (None, State.INCONCLUSIVE) else ""
    return f"{verdict} {arm['passed']}/{arm['slots']}{reason}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="compare_runs.py", description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("bundle", type=Path, metavar="ITERATION_DIR")
    parser.add_argument("--incumbent", required=True, metavar="LABEL")
    parser.add_argument("--candidate", required=True, metavar="LABEL")
    parser.add_argument("--scenarios", type=Path, metavar="DIR", help="scenario directory (default: the catalog)")
    parser.add_argument("--json", action="store_true", help="print the logical report as JSON")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse exits 2 on a usage error; this tool refuses with 3
        return 0 if exc.code == 0 else 3
    refusal = _refusal(args.bundle, args.incumbent, args.candidate, args.scenarios)
    if refusal:
        print(refusal, file=sys.stderr)
        return 3
    try:
        scenarios = catalog.load_all_scenarios(args.scenarios)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"invalid scenario: {exc}", file=sys.stderr)
        return 3
    try:
        report = compare_bundle(args.bundle, args.incumbent, args.candidate, scenarios)
    except OSError as exc:  # a folder the walk cannot list: no partial report stands in for the whole
        print(f"cannot read the saved runs: {exc}", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(render_text(report, args.bundle))
    return 0


def _refusal(bundle: Path, incumbent: str, candidate: str, scenario_dir: Path | None) -> str | None:
    """Why no report can be produced: no partial report stands in for a refused one."""
    if incumbent == candidate:
        return "--incumbent and --candidate must name different labels"
    if not bundle.is_dir():
        return f"no saved runs at {bundle}"
    missing = [label for label in (incumbent, candidate) if not label_present(bundle, label)]
    if missing:
        return f"no runs labelled {', '.join(map(repr, missing))} under {bundle}"
    if scenario_dir is not None and not scenario_dir.is_dir():
        return f"no scenario directory at {scenario_dir}"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
