"""Read-only campaign accounting over saved v1 attempts; no grading or host discovery.

    python evals/campaign_report.py BUNDLE --selection selection.json --label claude [--json]

Exit 0 means a report was produced, including measurement gaps. Exit 3 means the
arguments or selection could not be read. Evidence links are relative to BUNDLE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

from probe import layout
from probe.records import RECORD_FORMAT, RecordV1
from pydantic import ValidationError

_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*\Z")
_MAX_JSON = 8 * 1024 * 1024


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def _safe(root: Path, path: Path) -> bool:
    """Reject symlinks at every component before opening or traversing a path."""
    try:
        relative = path.relative_to(root)
        return not root.is_symlink() and all(
            part not in (".", "..") and not (root.joinpath(*relative.parts[: index + 1])).is_symlink()
            for index, part in enumerate(relative.parts)
        )
    except (OSError, ValueError):
        return False


def _children(root: Path, path: Path) -> list[Path]:
    if not _safe(root, path):
        return []
    try:
        return sorted(path.iterdir(), key=lambda child: child.name) if path.is_dir() else []
    except OSError:
        return []


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _read(root: Path, path: Path) -> Any:
    if not _safe(root, path):
        raise ValueError("unsafe evidence path or symlink")
    try:
        if not path.is_file() or path.stat().st_size > _MAX_JSON:
            raise ValueError("missing, non-file or oversized evidence")
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
        _digest(value)  # Refuse NaN/Infinity, including values in unknown sidecar fields.
        return value
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("unreadable or malformed JSON evidence") from None


def _usd(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _folders(root: Path, label_dir: Path) -> Iterator[tuple[Path, int, int | None, str]]:
    if not _safe(root, label_dir):
        yield label_dir, 1, None, "published"
        return
    for folder in _children(root, label_dir):
        slot = layout.slot(folder.name)
        if slot is not None:
            yield folder, slot, None, "published"
        elif (slot := layout.hidden_slot(folder.name)) is not None:
            yield folder, slot, None, "unpublished"
    history = label_dir / "attempts"
    if history.is_symlink():
        yield history, 1, None, "unpublished"
    for slot_dir in _children(root, history):
        slot = layout.slot(slot_dir.name)
        if slot is None:
            continue
        if not _safe(root, slot_dir):
            yield slot_dir, slot, None, "unpublished"
        for folder in _children(root, slot_dir):
            if (number := layout.number(folder.name)) is not None:
                yield folder, slot, number, "kept"


def _sidecar(root: Path, folder: Path, name: str, problems: list[str]) -> Any:
    path = folder / name
    if not path.exists() and not path.is_symlink():
        return None
    try:
        value = _read(root, path)
        if value is None:
            raise ValueError("present sidecar contains null instead of evidence")
        return value
    except ValueError as exc:
        problems.append(f"{name}: {exc}")
        return None


def _billing(value: Any, problems: list[str]) -> float | None:
    if value is None:
        return None
    if not isinstance(value, dict) or type(value.get("complete")) is not bool:
        problems.append("billing.json: malformed provider billing")
        return None
    if value["complete"] is False and value.get("measured_usd") is None:
        return None
    before, after = value.get("before"), value.get("after")
    old = _usd(before.get("usage")) if isinstance(before, dict) else None
    new = _usd(after.get("usage")) if isinstance(after, dict) else None
    measured = _usd(value.get("measured_usd"))
    if (
        value["complete"] is not True
        or old is None
        or new is None
        or measured is None
        or new < old
        or not math.isclose(round(new - old, 9), measured, abs_tol=1e-9)
    ):
        problems.append("billing.json: provider measurement does not match usage receipts")
        return None
    return measured


def _identity_problems(
    record: dict[str, Any], identity: Any, binding: Any, manifest: Mapping[str, Any], task: Mapping[str, Any]
) -> list[str]:
    problems = []
    if identity is not None:
        if not isinstance(identity, dict):
            problems.append("identity.json: expected an identity object")
        else:
            if (
                identity.get("instance_id") != record["case"]["id"]
                or _digest(identity) != record["case"]["case_sha256"]
            ):
                problems.append("identity.json: case identity does not match record")
            for key in ("dataset", "revision"):
                if key in manifest and identity.get(key) != manifest[key]:
                    problems.append(f"identity.json: {key} differs from selection")
            fields = task.get("field_hashes", {})
            if isinstance(fields, Mapping):
                for field, source in (("FAIL_TO_PASS", "fail_to_pass_sha256"), ("PASS_TO_PASS", "pass_to_pass_sha256")):
                    if field in fields and fields[field] != identity.get(source):
                        problems.append(f"identity.json: {field} differs from selection")
                if "base_commit" in fields and fields["base_commit"] != _digest(identity.get("base_commit")):
                    problems.append("identity.json: base_commit differs from selection")
    if "case_sha256" in task and task["case_sha256"] != record["case"]["case_sha256"]:
        problems.append("case digest differs from selection")
    if binding is not None:
        if not isinstance(binding, dict) or binding.get("selection_sha256") != _digest(manifest):
            problems.append("binding.json: selection binding differs from manifest")
        if isinstance(binding, dict):
            runtime = record["conditions"]["runtime"] or {}
            for key, expected in (
                ("plugin_sha256", record["candidate"]["plugin_source_sha256"]),
                ("adapter_sha256", record["runner"]["runner_source_sha256"]),
                ("cli_version", runtime.get("cli_version")),
                ("model", record["conditions"]["requested_model"]),
            ):
                if key in binding and binding[key] != expected:
                    problems.append(f"binding.json: {key} differs from record")
            images = binding.get("images")
            if isinstance(images, dict) and isinstance(identity, dict):
                image = images.get(record["case"]["id"], {})
                if not isinstance(image, dict) or image.get("image_id") != identity.get("image_digest"):
                    problems.append("binding.json: image differs from case identity")
    return problems


def _attempt(
    root: Path,
    folder: Path,
    case: str,
    label: str,
    slot: int,
    number: int | None,
    location: str,
    manifest: Mapping[str, Any],
    task: Mapping[str, Any],
) -> dict[str, Any]:
    where = folder.relative_to(root).as_posix()
    problems: list[str] = []
    row: dict[str, Any] = {
        "folder": where,
        "record": f"{where}/record.json",
        "location": location,
        "valid": False,
        "number": number,
        "state": None,
        "verdict": None,
        "problems": problems,
        "provider_measured_usd": None,
        "cli_estimated_usd": None,
    }
    row["provider_measured_usd"] = _billing(_sidecar(root, folder, "billing.json", problems), problems)
    try:
        raw = _read(root, folder / "record.json")
        if not isinstance(raw, dict) or raw.get("format") != RECORD_FORMAT or type(raw["format"]["version"]) is not int:
            raise ValueError("unsupported record format or version; only v1 is readable")
        # Re-encode to enforce the model's JSON-level strict contract.
        value = RecordV1.model_validate_json(json.dumps(raw)).model_dump(mode="json")
    except (ValueError, ValidationError) as exc:
        # Validation errors may contain untrusted input values: report their location only.
        problem = f"record violates v1 at {exc.errors()[0]['loc']}" if isinstance(exc, ValidationError) else str(exc)
        problems.append(problem)
        return row
    attempt = value["attempt"]
    row.update(
        {
            key: value[key]
            for key in (
                "case",
                "candidate",
                "runner",
                "conditions",
                "run_end",
                "checks",
                "verdict",
                "assessments",
                "cost",
            )
        }
    )
    row.update(number=attempt["number"], state=attempt["state"], attempt=attempt)
    if value["case"]["id"] != case or attempt["label"] != label or attempt["slot"] != slot:
        problems.append("record case, label or slot disagrees with its folder")
    if location == "published" and attempt["state"] != "final":
        problems.append("published record is not final")
    if location == "kept" and (attempt["state"] == "final" or attempt["number"] != number):
        problems.append("kept attempt identity disagrees with folder")
    if location == "unpublished":
        problems.append("unpublished attempt cannot complete a slot")
    links = {"record.json": row["record"]}
    paths = [*value["evidence"].values(), *(entry["grading"] for entry in value["assessments"])]
    for relative in paths:
        path = folder / relative
        if not _safe(root, path) or not path.is_file():
            problems.append(f"missing or unsafe evidence: {relative}")
        else:
            try:
                with path.open("rb"):
                    pass
                links[relative] = f"{where}/{relative}"
            except OSError:
                problems.append(f"unreadable evidence: {relative}")
    row["evidence"] = links
    identity = _sidecar(root, folder, "identity.json", problems)
    binding = _sidecar(root, folder, "binding.json", problems)
    try:
        problems.extend(_identity_problems(value, identity, binding, manifest, task))
    except (TypeError, ValueError):
        problems.append("identity.json or binding.json: malformed identity")
    row["binding"] = binding
    cost = value["cost"]
    known = [_usd(cost[key]) for key in ("trial_usd", "judge_usd")]
    if any(cost[key] is not None and _usd(cost[key]) is None for key in ("trial_usd", "judge_usd", "known_usd")):
        problems.append("CLI cost contains an invalid USD amount")
    else:
        components = (
            math.fsum(amount for amount in known if amount is not None)
            if any(amount is not None for amount in known)
            else None
        )
        floor = _usd(cost["known_usd"])
        # Native records include priced judge calls even when the total judge
        # cost is unavailable. The writer rounds that known floor to six decimals.
        row["cli_estimated_usd"] = floor if floor is not None else components
        if floor is not None and components is not None:
            agrees = math.isclose(floor, components, rel_tol=0, abs_tol=0.000000500001)
            if (all(amount is not None for amount in known) and not agrees) or (floor < components and not agrees):
                problems.append("CLI cost floor disagrees with known components")
    cleanup = _sidecar(root, folder, "cleanup.json", problems)
    cleanup_status = "unknown"
    if isinstance(cleanup, list) and cleanup:
        cleanup_status = (
            "complete"
            if all(isinstance(item, dict) and item.get("present") is False for item in cleanup)
            else "unresolved"
        )
    elif isinstance(cleanup, dict):
        cleanup_status = (
            "complete" if (cleanup.get("complete") is True or cleanup.get("removed") is True) else "unresolved"
        )
    review = _sidecar(root, folder, "policy-review.json", problems)
    semantics = "unknown"
    conversation = _sidecar(root, folder, "conversation.json", problems)
    if isinstance(conversation, dict) and conversation.get("profile") == "incident-v1":
        trace = _sidecar(root, folder, "outputs/trace-summary.json", problems)
        if isinstance(trace, dict) and trace.get("semantic_assessment") == "UNVERIFIED":
            semantics = "UNVERIFIED"
    verifier = _sidecar(root, folder, "verifier/verifier-receipt.json", problems)
    if verifier is not None and (
        not isinstance(verifier, dict)
        or verifier.get("instance_id", case) != case
        or verifier.get("outcome") not in ("PASS", "FAIL", "INCONCLUSIVE")
    ):
        problems.append("independent verifier receipt is malformed or names another case")
    row["dimensions"] = {
        "execution": value["run_end"],
        "independent_verifier": verifier or {"outcome": "unknown"},
        "cleanup": {"status": cleanup_status, "receipt": cleanup},
        "policy_review": review if isinstance(review, dict) else {"status": "unknown"},
        "semantic_assessment": semantics,
    }
    row["valid"] = not problems
    return row


def _group_identity(attempt: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
    conditions = attempt["conditions"]
    runtime = conditions["runtime"] or {}
    host = runtime.get("host_identity") or {}
    identity = {
        "candidate": {key: value for key, value in attempt["candidate"].items() if key != "plugin_root"},
        "runner": attempt["runner"],
        "conditions": conditions,
        "binding": attempt.get("binding"),
    }
    complete = bool(
        identity["candidate"].get("plugin_source_sha256")
        and identity["runner"].get("runner_source_sha256")
        and conditions.get("requested_model")
        and len(conditions.get("observed_models") or []) == 1
        and conditions.get("execution_profile")
        and runtime.get("cli_version")
        and all(runtime.get("host_platform", {}).get(key) for key in ("system", "release", "machine"))
        and host.get("hostname")
        and host.get("account_id")
        and type(host.get("elevated")) is bool
        and host.get("identity_source")
        and not host.get("problem")
    )
    return identity, complete


def _total(attempts: list[dict[str, Any]], key: str) -> dict[str, Any]:
    amounts = [row[key] for row in attempts if row[key] is not None]
    unknown = sum(
        row[key] is None or (key == "cli_estimated_usd" and not row.get("cost", {}).get("complete")) for row in attempts
    )
    return {
        "known_usd": round(math.fsum(amounts), 9) if amounts else None,
        "unknown_attempts": unknown,
        "complete": bool(attempts) and unknown == 0,
    }


def build_report(bundle: Path, selection: Mapping[str, Any], label: str) -> dict[str, Any]:
    """Account for selected slots and every saved attempt without executing or rescoring."""
    if not _NAME.fullmatch(label):
        raise ValueError("label must be a safe folder name")
    root = Path(bundle).absolute()
    manifest_digest = _digest(selection)
    selection_problems: list[str] = []
    tasks: dict[str, Mapping[str, Any]] = {}
    raw_tasks = selection.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError("selection requires tasks[] with instance_id")
    for task in raw_tasks:
        case = task.get("instance_id") if isinstance(task, Mapping) else None
        if not isinstance(case, str) or not _NAME.fullmatch(case):
            selection_problems.append("selected task has missing or unsafe instance_id")
        elif case in tasks:
            selection_problems.append(f"duplicate selected instance_id: {case}")
        else:
            tasks[case] = task
    trials = selection.get("trials", 1)
    if type(trials) is not int or not 1 <= trials <= 10000:
        raise ValueError("selection trials must be an integer from 1 to 10000")
    case_ids = set(tasks)
    case_ids.update(
        child.name[5:]
        for child in _children(root, root)
        if child.name.startswith("eval-") and _NAME.fullmatch(child.name[5:])
    )
    cases: dict[str, Any] = {}
    all_attempts: list[dict[str, Any]] = []
    counts = dict.fromkeys(
        (
            "selected_cases",
            "expected_slots",
            "started_slots",
            "completed_slots",
            "recorded_verdicts",
            "measured_slots",
            "missing_slots",
            "invalid_slots",
            "failures_to_measure_slots",
            "kept_attempts",
            "incomplete_attempts",
        ),
        0,
    )
    counts["selected_cases"] = len(tasks)
    verdict_counts = dict.fromkeys(("PASS", "FAIL", "INCONCLUSIVE"), 0)
    groups: dict[str, dict[str, Any]] = {}
    for case in sorted(case_ids):
        slots: dict[int, list[dict[str, Any]]] = {}
        for folder, slot, number, location in _folders(root, root / f"eval-{case}" / label):
            row = _attempt(root, folder, case, label, slot, number, location, selection, tasks.get(case, {}))
            slots.setdefault(slot, []).append(row)
            all_attempts.append(row)
        expected = set(range(1, trials + 1)) if case in tasks else set()
        case_rows = []
        for slot in sorted(expected | set(slots)):
            attempts = slots.get(slot, [])
            problems = [f"{row['folder']}: {problem}" for row in attempts for problem in row["problems"]]
            selected_slot = slot in expected
            if not selected_slot:
                problems.append("unselected trial slot")
            numbers = [row["number"] for row in attempts if row["number"] is not None]
            if len(numbers) != len(set(numbers)):
                problems.append("duplicate attempt identity within slot")
            finals = [row for row in attempts if row["location"] == "published"]
            final = finals[0] if len(finals) == 1 else None
            measured = bool(
                selected_slot
                and final
                and final["valid"]
                and not problems
                and final["verdict"]["status"] in ("PASS", "FAIL")
            )
            case_rows.append(
                {
                    "slot": slot,
                    "selected": selected_slot,
                    "started": bool(attempts),
                    "measured": measured,
                    "problems": problems,
                    "attempts": attempts,
                }
            )
            if not selected_slot:
                continue
            counts["expected_slots"] += 1
            counts["started_slots"] += bool(attempts)
            counts["missing_slots"] += not attempts
            counts["invalid_slots"] += bool(problems)
            counts["measured_slots"] += measured
            counts["failures_to_measure_slots"] += not measured
            if final and final.get("verdict"):
                verdict = final["verdict"]["status"]
                if verdict is not None:
                    counts["recorded_verdicts"] += 1
                    verdict_counts[verdict] += 1
                counts["completed_slots"] += final["run_end"]["kind"] == "completed"
                identity, complete = _group_identity(final)
                key = _digest(identity) if complete else final["folder"]
                group = groups.setdefault(
                    key,
                    {
                        "identity": identity,
                        "identity_complete": complete,
                        "slots": [],
                        "verdict_counts": dict.fromkeys(verdict_counts, 0),
                    },
                )
                group["slots"].append({"case": case, "slot": slot, "record": final["record"], "measured": measured})
                if measured:
                    group["verdict_counts"][verdict] += 1
        cases[case] = {"selected": case in tasks, "slots": case_rows}
    counts["kept_attempts"] = sum(row["location"] == "kept" for row in all_attempts)
    counts["incomplete_attempts"] = sum(
        row["state"] == "incomplete" or row["location"] == "unpublished" for row in all_attempts
    )
    return {
        "format": {"name": "save-toolkit.campaign-report", "version": 1},
        "label": label,
        "selection": {
            "sha256": manifest_digest,
            "raw_entries": len(raw_tasks),
            "accepted_unique_cases": len(tasks),
            "dataset": selection.get("dataset"),
            "revision": selection.get("revision"),
            "problems": selection_problems,
        },
        "counts": counts,
        "verdict_counts": verdict_counts,
        "cases": cases,
        "unselected_cases": sorted(case_ids - set(tasks)),
        "groups": list(groups.values()),
        "cost": {
            "scope": "all discovered attempts, including kept and unselected attempts",
            "provider_measured_usd": _total(all_attempts, "provider_measured_usd"),
            "cli_estimated_usd": _total(all_attempts, "cli_estimated_usd"),
        },
        "human_acceptance": "unknown",
        "key_disablement": "unknown",
        "problems": ["bundle is missing, unreadable or a symlink"]
        if not _safe(root, root) or not root.is_dir()
        else [],
    }


def _text(value: object) -> str:
    return (
        str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("<", "&lt;").replace(">", "&gt;")
    )


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render portable source links with explicit measurement and spending denominators."""
    counts = report["counts"]
    lines = [
        f"# Campaign report: {_text(report['label'])}",
        "",
        "[sourced] Saved v1 artifacts; original assessments preserved. No rescoring or acceptance decision.",
        "",
        f"Selected cases: {counts['selected_cases']}; expected slots: {counts['expected_slots']}; started: {counts['started_slots']}; completed: {counts['completed_slots']}.",
        f"Recorded verdicts: {counts['recorded_verdicts']}; measured PASS/FAIL: {counts['measured_slots']}/{counts['expected_slots']}; failures to measure: {counts['failures_to_measure_slots']}; missing: {counts['missing_slots']}; invalid: {counts['invalid_slots']}.",
        f"Kept attempts: {counts['kept_attempts']}; incomplete attempts: {counts['incomplete_attempts']}.",
        "",
    ]
    for title, key in (("Provider-measured", "provider_measured_usd"), ("CLI-estimated", "cli_estimated_usd")):
        cost = report["cost"][key]
        amount = "unknown" if cost["known_usd"] is None else f"USD {cost['known_usd']:.9g} known"
        lines.append(f"{title}: {amount}; unknown attempts: {cost['unknown_attempts']}; complete: {cost['complete']}.")
    lines.extend(
        [
            f"Cost scope: {_text(report['cost']['scope'])}.",
            "",
            f"Human acceptance: {report['human_acceptance']}. Key disablement: {report['key_disablement']}.",
            "",
            f"Measurement condition groups: {len(report['groups'])}; unknown identities remain separate.",
            "",
            "| Case | Slot | Attempt | Location | Recorded verdict | Execution | Measured slot | Evidence / problems |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case, entry in report["cases"].items():
        for slot in entry["slots"]:
            if not slot["attempts"]:
                lines.append(
                    f"| {_text(case)} | {slot['slot']} | — | missing | unknown | unknown | False | selected slot not started |"
                )
            for attempt in slot["attempts"]:
                verdict = (attempt.get("verdict") or {}).get("status") or "unknown"
                ending = (attempt.get("run_end") or {}).get("kind") or "unknown"
                links = attempt.get("evidence", {"record.json": attempt["record"]})
                evidence = "; ".join(f"[{_text(name)}]({quote(path, safe='/._-')})" for name, path in links.items())
                detail = "; ".join(slot["problems"])
                after = (attempt.get("verdict") or {}).get("after_assessment")
                if after:
                    detail = "; ".join(part for part in (detail, f"After assessment: {after}") if part)
                lines.append(
                    f"| {_text(case)} | {slot['slot']} | {attempt['number']} | {attempt['location']} | {verdict} | {ending} | {slot['measured']} | {evidence} {_text(detail)} |"
                )
                dimensions = attempt.get("dimensions")
                if dimensions:
                    lines.append(
                        f"| | | | dimensions | verifier: {_text(dimensions['independent_verifier'].get('outcome', 'unknown'))} | cleanup: {dimensions['cleanup']['status']} | review: {_text(dimensions['policy_review'].get('status', 'unknown'))}; semantic: {_text(dimensions['semantic_assessment'])} | |"
                    )
    lines.append("")
    for index, group in enumerate(report["groups"], 1):
        identity = group["identity"]
        conditions = identity["conditions"]
        runtime = conditions["runtime"] or {}
        host = runtime.get("host_identity") or {}
        profile = conditions.get("execution_profile") or {}
        lines.append(
            f"Condition group {index}: candidate {_text(identity['candidate'].get('plugin_source_sha256') or 'unknown')}; "
            f"models {_text(conditions.get('observed_models') or 'unknown')}; CLI {_text(runtime.get('cli_version') or 'unknown')}; "
            f"host {_text(host.get('hostname') or 'unknown')}; account {_text(host.get('account_id') or 'unknown')}; "
            f"elevated {_text(host.get('elevated'))}; profile {_text(profile.get('name') or 'unknown')}; "
            f"identity complete: {group['identity_complete']}."
        )
    for problem in [*report["problems"], *report["selection"]["problems"]]:
        lines.append(f"- [unverified] {_text(problem)}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--label", default="claude")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = _read(args.selection.absolute().parent, args.selection.absolute())
        if not isinstance(manifest, dict):
            raise ValueError("selection must be a JSON object")
        report = build_report(args.bundle, manifest, args.label)
        print(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) if args.json else render_markdown(report),
            end="\n" if args.json else "",
        )
    except (OSError, ValueError) as exc:
        print(f"campaign report: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
