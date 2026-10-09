"""Run one trial end to end and publish it as an attempt that is never deleted.

`run_trial` owns publication: an attempt is written in a hidden sibling folder and renamed into
`run-N` only once complete, a replaced run moves to `attempts/run-N/<k>/` as superseded, and an
attempt that raised is kept there as incomplete (threat-model ADR result rule 7). `_run_trial` owns
the measurement: seed, invoke, check each invocation's boundary, grade, and record what it cost.
"""

from __future__ import annotations

import contextlib
import json
import secrets
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import clean_room
import judge as rubric_judge

from . import assessment, backing, catalog, fingerprints, invocation, layout, records, tracing, workspaces
from .backing import Service, ServiceUnavailable
from .checking import Context
from .constants import ROOT
from .fingerprints import HARNESS_SOURCE_SHA256
from .outcomes import CutShort, Stop, void_over_cut
from .records import AttemptState
from .tracing import TraceSummary


@dataclass(frozen=True)
class BatchSettings:
    """What every trial of one batch shares: the candidate and runtime it measures, the model and limits
    it runs with, and where its attempts are published."""

    plugin_root: Path
    label: str
    model: str | None
    out_dir: Path
    timeout: int
    executable: str
    keep_workspace: bool
    overwrite: bool = False
    env_factory: Callable[[], AbstractContextManager[dict[str, str]]] | None = None
    docker: str = "docker"
    expected_plugin_digest: str | None = None  # the digest the batch started with; a change voids the trial
    judge_binding: rubric_judge.JudgeBinding | None = None
    runtime: dict[str, Any] | None = None


def run_trial(spec: Mapping[str, Any], *, run_number: int, settings: BatchSettings) -> dict[str, Any]:
    """Publish a complete attempt; a failed overwrite leaves the previous run intact."""
    if "followups" in spec:
        problems = catalog.validate_scenario(spec)
        if problems:
            raise ValueError("; ".join(problems))
    rubric_judge.validate_binding(settings.judge_binding, fingerprints.required_rubrics(spec))
    target = layout.run_dir(settings.out_dir, spec["id"], settings.label, run_number)
    if target.exists() and not settings.overwrite:
        raise RuntimeError(f"{target} already exists; pass --overwrite or a --run-offset")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Every attempt stays visible (threat-model ADR result rule 7): a replaced run and an attempt that
    # never published move into the slot's history, which run-N globs never match.
    history = layout.history_dir(target)
    following = layout.next_number(history)
    current = (_attempt_number(target) or following) if target.exists() else None
    number = max(following, (current or 0) + 1)
    attempt = _new_attempt_dir(target)
    _write_attempt(attempt, number, AttemptState.FINAL)
    started_at = records.utc_now()

    def record(incomplete: str | None = None) -> None:
        """This attempt's v1 record; a raised attempt's carries why it ended."""
        records.write_record(
            attempt,
            spec,
            label=settings.label,
            run_number=run_number,
            attempt=number,
            started_at=started_at,
            model=settings.model,
            timeout=settings.timeout,
            incomplete=incomplete,
        )

    backup, published = None, False
    try:
        summary = _run_trial(spec, run_number, attempt, settings)
        summary["attempt"] = number
        try:
            record()
        except ValueError as exc:
            # The verdict stands (result rule 6), and the record only maps facts the attempt's files
            # keep, so it can be written once the runner is fixed; the batch goes on.
            summary["record_problem"] = f"record refused: {exc}"[:500]
            print(f"warning: {attempt} is published without record.json: {exc}", file=sys.stderr, flush=True)
        if target.exists():
            backup = layout.backup_dir(target, secrets.token_hex(8))
            target.rename(backup)
        try:
            attempt.rename(target)
            published = True
        except BaseException:
            if backup is not None:
                backup.rename(target)
            raise
        if backup is not None:
            try:
                _keep_attempt(backup, history, current, AttemptState.SUPERSEDED, f"replaced by attempt {number}")
            except Exception as exc:
                print(f"warning: published {target}; previous run retained at {backup}: {exc}", file=sys.stderr)
        print(json.dumps(summary), flush=True)
        return summary
    except BaseException as exc:
        if not published and attempt.exists():
            reason = f"{type(exc).__name__}: {exc}"[:500]
            try:
                _record_raised_cost(attempt)
            except Exception as cost_error:  # no timing.json leaves the cost unknown, which the cap refuses
                print(f"warning: no cost recorded for the incomplete attempt {attempt}: {cost_error}", file=sys.stderr)
            try:
                record(incomplete=reason)
            except Exception as record_error:
                print(f"warning: no record for the incomplete attempt {attempt}: {record_error}", file=sys.stderr)
            try:
                _keep_attempt(attempt, history, number, AttemptState.INCOMPLETE, reason)
            except Exception as keep_error:
                print(f"warning: could not keep the incomplete attempt {attempt}: {keep_error}", file=sys.stderr)
        raise


def _new_attempt_dir(target: Path) -> Path:
    """A fresh hidden sibling for one attempt. A plain mkdir inherits the parent's permissions;
    tempfile.mkdtemp makes the folder readable only by its creator on Windows (EVAL-012 DEC-23)."""
    for _ in range(16):
        attempt = layout.attempt_dir(target, secrets.token_hex(8))
        try:
            attempt.mkdir()
            return attempt
        except FileExistsError:
            continue
    raise RuntimeError(f"could not create an attempt directory beside {target}")


def _attempt_number(run_dir: Path) -> int | None:
    try:
        number = json.loads((run_dir / "attempt.json").read_text(encoding="utf-8")).get("attempt")
    except (OSError, ValueError, AttributeError):
        return None
    return number if type(number) is int and number > 0 else None


def _write_attempt(run_dir: Path, number: int, state: AttemptState, reason: str | None = None) -> None:
    (run_dir / "attempt.json").write_text(
        json.dumps(
            {
                "attempt": number,
                "state": state,
                **({"reason": reason} if reason else {}),
                "recorded_at": records.utc_now(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    records.update_record(
        run_dir,
        lambda record: record["attempt"].update(number=number, state=state, **({"reason": reason} if reason else {})),
    )


def kept_attempt_costs(
    out_dir: Path, label: str, scenario_ids: Iterable[str], model: str | None
) -> list[dict[str, Any]]:
    """The `timing.json` of each attempt a label keeps for `model`, superseded or incomplete: no batch
    summary lists them, though each was paid for (result rule 7). The summary is per label and model,
    while a label's attempts are shared, so another model's attempt does not count; one whose model
    cannot be read does, and one without a readable `timing.json` reads as an unknown cost, never zero."""
    costs: list[dict[str, Any]] = []
    for scenario_id in sorted(scenario_ids):
        for attempt, _, _ in layout.kept_attempts(layout.case_dir(out_dir, scenario_id) / label):
            timing = _read_json(attempt / "timing.json")
            requested = _requested_model(timing, _read_json(attempt / "record.json"))
            if requested is not _UNKNOWN and requested != model:
                continue
            costs.append(timing if isinstance(timing, dict) else {"cost_complete": False})
    return costs


_UNKNOWN = object()


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _requested_model(timing: object, record: object) -> object:
    """The model an attempt was run for: a graded attempt's timing names it, a raised one's record does.

    Only a string or null names a model; anything else is malformed and falls through, so a paid
    attempt is never attributed to a model no batch runs.
    """
    conditions = record.get("conditions") if isinstance(record, dict) else None
    for source in (timing, conditions):
        if isinstance(source, dict) and isinstance(source.get("requested_model", _UNKNOWN), str | None):
            return source["requested_model"]
    return _UNKNOWN


def _record_raised_cost(attempt: Path) -> None:
    """Write what an attempt that raised is known to have cost, as a graded trial's `timing.json` does:
    nothing for the CLI when it never started, else what its partial trace reports, which is unknown
    without a result event; plus any judge call its grading made."""
    if (attempt / "timing.json").exists():  # it was graded before it raised
        return
    trace_path = attempt / "stdout.jsonl"
    trial_usd = tracing.parse_trace(trace_path).total_cost_usd if trace_path.exists() else 0.0
    cost = records.trial_cost(trial_usd, records.judge_spend())
    (attempt / "timing.json").write_text(
        json.dumps(
            {
                "total_cost_usd": cost["cost_usd"],
                "known_cost_usd": cost["known_cost_usd"],
                "cost_complete": cost["cost_complete"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _keep_attempt(run_dir: Path, history: Path, number: int | None, state: AttemptState, reason: str) -> Path:
    """Move an attempt that is not the published run into the slot's history, never deleting it."""
    history.mkdir(parents=True, exist_ok=True)
    taken = layout.taken(history)
    number = number if number and number not in taken else max(taken, default=0) + 1
    destination = history / str(number)
    run_dir.rename(destination)
    _write_attempt(destination, number, state, reason)
    return destination


def _plugin_drift(candidate: Path, served: Path, expected: str) -> str | None:
    """Drift in the candidate's inputs, or in the image the trial was served, which a session with a
    shell could edit."""
    return fingerprints.plugin_drift_problem(candidate, expected) or fingerprints.plugin_drift_problem(served, expected)


def _invoke_turns(
    spec: Mapping[str, Any],
    settings: BatchSettings,
    run_out: Path,
    ws: workspaces.Workspace,
    env: dict[str, str],
    plugin_sha: str,
    binding: dict[str, Any] | None,
    scenario_identity: str,
    served: Path,
) -> tuple[str | None, str | None]:
    """Invoke the CLI for the prompt and then each follow-up, resuming the session the turn before
    opened, until a turn ends the trial: why it ended, if one did, and any identity failure."""
    inconclusive: str | None = None
    identity_failure: str | None = None
    resume = None
    for turn, prompt in enumerate([catalog.scenario_prompt(spec, served), *spec.get("followups", [])]):
        inconclusive = _plugin_drift(settings.plugin_root, served, plugin_sha)
        if fingerprints.scenario_digest(spec, binding) != scenario_identity:
            inconclusive = "scenario inputs changed before invocation; re-run the trial"
        if inconclusive:
            identity_failure = identity_failure or inconclusive
            break
        turn_out = run_out if turn == 0 else run_out / "followup"
        turn_out.mkdir(exist_ok=True)
        command = invocation.build_command(
            settings.executable,
            served,
            catalog.agent_pin(spec),
            prompt,
            settings.model,
            catalog.scenario_tools(spec),
            pre_approve=catalog.scenario_kind(spec) == "build",
            persistent=bool(spec.get("followups")),
            resume=resume,
            max_turns=spec.get("max_turns"),
        )
        returncode, timed_out = None, None
        with (
            (turn_out / "stdout.jsonl").open("w", encoding="utf-8") as out,
            (turn_out / "stderr.txt").open("w", encoding="utf-8") as err,
        ):
            try:
                returncode = subprocess.run(
                    command, cwd=str(ws.repo), env=env, stdout=out, stderr=err, timeout=settings.timeout
                ).returncode
            except subprocess.TimeoutExpired:
                timed_out = CutShort(f"timed out after {settings.timeout}s", Stop.WALL_CLOCK)
        current = tracing.parse_trace(turn_out / "stdout.jsonl")
        reason, failed = invocation.turn_reason(
            current,
            returncode,
            timed_out,
            spec,
            served,
            plugin_sha,
            ws.repo,
            resume,
            turn_out / "stdout.jsonl",
        )
        identity_failure = identity_failure or failed
        inconclusive = inconclusive or reason
        if spec.get("followups"):
            (turn_out / "invocation.json").write_text(
                json.dumps(
                    {
                        "argv": command,
                        "session_id": current.session_id,
                        "workspace": str(ws.repo.resolve()),
                        "exit_code": returncode,
                        "expected_model": spec.get("expected_model"),
                        "main_models": current.main_models,
                        "init_session_ids": current.init_session_ids,
                        "resume": resume,
                        "inconclusive": inconclusive,
                        "cut_short": isinstance(inconclusive, CutShort),
                        "run_stop": inconclusive.kind if isinstance(inconclusive, CutShort) else None,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (turn_out / "response.md").write_text(current.result_text, encoding="utf-8")
        if inconclusive:
            break
        resume = current.session_id
    return inconclusive, identity_failure


def _run_trial(spec: Mapping[str, Any], run_number: int, run_out: Path, settings: BatchSettings) -> dict[str, Any]:
    eval_name = spec["id"]
    (run_out / "outputs").mkdir(parents=True, exist_ok=True)
    # Raw traces carry whole prompts, responses, session ids, and tool payloads, and the README
    # calls them owner-only. Real on POSIX; advisory on Windows/NTFS, the same caveat clean_room
    # states for the credential copy -- the OS ACL, not this bit, is the control there.
    for directory in (run_out.parent.parent, run_out.parent, run_out, run_out / "outputs"):
        with contextlib.suppress(OSError):
            directory.chmod(stat.S_IRWXU)
    metadata = {
        "eval_id": eval_name,
        "eval_name": eval_name,
        "prompt": spec["prompt"],
        "assertions": assessment.scenario_assertions(spec),
    }
    (run_out.parent.parent / "eval_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (run_out / "eval_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Neutral prefix: the cwd is in the agent's context. The root is chosen by clean_room so no
    # CLAUDE.md/AGENTS.md sits above it -- on Windows the default temp dir is under the operator's
    # home, where every trial would inherit their personal rules.
    root = clean_room.make_workspace("ws-")
    inconclusive: str | None = None
    # A wrong candidate identity stops the batch; a backing service that never started, its scenario.
    identity_failure: str | None = None
    service_error: str | None = None
    trace = TraceSummary()
    services: list[Service] = []
    try:
        if root.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError(f"temp workspace {root} is inside the repository")
        provenance = fingerprints.plugin_provenance(settings.plugin_root)
        # The trial is served an image of the measured inputs beside its repository, never the
        # checkout: with `--plugin-dir` and `--add-dir` naming the checkout, a routing session could
        # read this repository's evals, docs and history before choosing an agent (EVAL-014).
        served = fingerprints.stage_plugin(settings.plugin_root, root / "plugin")
        provenance["plugin_served_from"] = str(served.resolve())
        binding = fingerprints.binding_for(spec, settings.judge_binding)
        scenario_identity = fingerprints.scenario_digest(spec, binding)
        if settings.expected_plugin_digest and provenance["plugin_source_sha256"] != settings.expected_plugin_digest:
            inconclusive = identity_failure = "plugin inputs changed before the trial; re-run with one candidate"
        (run_out / "provenance.json").write_text(
            json.dumps(
                {
                    **provenance,
                    **fingerprints.runner_provenance(),
                    "runtime": settings.runtime,
                    **({"judge_binding": binding} if binding else {}),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        # A routing or contract scenario has no fixture: it runs in an empty git root outside the
        # checkout, so the repo's own AGENTS.md/CLAUDE.md cannot teach it the routing answer.
        ws = workspaces.seed_workspace(
            spec if spec.get("fixture") else {**spec, "fixture": {"files": {"README.md": "# eval workspace\n"}}},
            root,
        )
        if inconclusive is None:
            try:
                services = backing.start_services(spec, settings.docker)
            except ServiceUnavailable as exc:
                services = []
                inconclusive = service_error = f"backing service unavailable: {exc}"
        trace_path = run_out / "stdout.jsonl"
        started = time.monotonic()
        if inconclusive is None:
            make_env = settings.env_factory or (lambda: clean_room.clean_env(subscriber_only=True))
            with make_env() as base_env:
                env = workspaces.child_env(base_env, ws, spec, services)
                inconclusive, failed = _invoke_turns(
                    spec,
                    settings,
                    run_out,
                    ws,
                    env,
                    provenance["plugin_source_sha256"],
                    binding,
                    scenario_identity,
                    served,
                )
                identity_failure = identity_failure or failed
        else:
            # A missing fixture target cannot be repaired by the model. Starting it here would
            # spend a call with unresolved service placeholders and could make a tool-bearing
            # agent discover or mutate an unrelated host service.
            trace_path.write_text("", encoding="utf-8")
            (run_out / "stderr.txt").write_text("", encoding="utf-8")
        elapsed = time.monotonic() - started
        if not inconclusive or isinstance(inconclusive, CutShort):  # drift voids even a cut-short run
            drift = _plugin_drift(settings.plugin_root, served, provenance["plugin_source_sha256"])
            identity_failure = identity_failure or drift
            inconclusive = void_over_cut(inconclusive, drift)
        trace = tracing.parse_trial_trace(run_out) if trace_path.exists() else TraceSummary()
        git = workspaces.collect_git_facts(ws)
        ctx = Context(
            spec,
            ws,
            trace,
            git,
            services=services,
            plugin_root=served,
            judge_binding=settings.judge_binding,
        )
        grading = assessment.grade(ctx, inconclusive=inconclusive, expected_scenario_digest=scenario_identity)
        after_assessment = None
        if services:
            try:
                backing.stop_services(services, settings.docker)
            except ServiceUnavailable as exc:
                # The assessment already stands; a leftover service blocks reusing the environment.
                after_assessment = f"backing service cleanup failed: {exc}"
            finally:
                services = []
        drift = _plugin_drift(settings.plugin_root, served, provenance["plugin_source_sha256"])
        if drift:
            identity_failure = identity_failure or drift
            grading = assessment.grade(ctx, inconclusive=drift, expected_scenario_digest=scenario_identity)
        if after_assessment:
            grading["after_assessment"] = after_assessment
        inconclusive = grading["inconclusive"]
        (run_out / "outputs" / "response.md").write_text(trace.result_text or "(no result)", encoding="utf-8")
        (run_out / "outputs" / "workspace.patch").write_text(git.patch or "(no changes)\n", encoding="utf-8")
        # Full contents (bounded), so --regrade sees the same state the live grade saw.
        state_files = {
            p.name: p.read_text(encoding="utf-8", errors="replace")[:50000]
            for p in ws.state_dir.iterdir()
            if p.is_file()
        }
        markers = invocation.credential_markers(trace.result_text, trace_path)
        if (run_out / "followup" / "stdout.jsonl").is_file():
            markers += invocation.credential_markers("", run_out / "followup" / "stdout.jsonl")
        if markers:
            print(f"WARNING: credential-shaped content in {run_out}: {markers}", file=sys.stderr, flush=True)
        (run_out / "outputs" / "trace-summary.json").write_text(
            json.dumps(
                {
                    **assessment.native_assessment(spec),
                    "status": grading["status"],
                    "inconclusive": inconclusive,
                    "after_assessment": after_assessment,
                    "run_end": grading.get("run_end"),
                    **tracing.to_saved(trace),
                    "commits_before_after": [ws.baseline_commits, git.commit_count],
                    "branch": git.branch,
                    "changed_files": ctx.git.changed,
                    **({"git_problem": git.problem} if git.problem else {}),
                    "state_files": state_files,
                    "agents_dir": (ws.repo / ".agents").exists(),
                    "plugin": provenance,
                    "runtime": settings.runtime,
                    "workspace": str(ws.repo.resolve()),
                    "judge_binding": binding,
                    "scenario_sha256": grading["scenario_sha256"],
                    "isolation": {"mode": "host"},
                    "services": [{"name": s.name, "image": s.image, "base_url": s.base_url} for s in ctx.services],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (run_out / "grading.json").write_text(json.dumps(grading, indent=2, ensure_ascii=False), encoding="utf-8")
        # Drained after grading: a rubric grader's judge call is spend this trial caused.
        judge = records.judge_spend()
        cost = records.trial_cost(trace.total_cost_usd, judge)
        trial_seconds = (trace.duration_ms or elapsed * 1000) / 1000
        (run_out / "timing.json").write_text(
            json.dumps(
                {
                    "total_tokens": trace.total_tokens,
                    "output_tokens": trace.output_tokens,
                    "duration_ms": trace.duration_ms or int(elapsed * 1000),
                    "trial_duration_seconds": round(trial_seconds, 1),
                    "total_duration_seconds": round(trial_seconds + judge["seconds"], 1),
                    "num_turns": trace.num_turns,
                    "trial_cost_usd": records.known_usd(trace.total_cost_usd),
                    "total_cost_usd": cost["cost_usd"],
                    "known_cost_usd": cost["known_cost_usd"],
                    "cost_complete": cost["cost_complete"],
                    "judge": judge,
                    "requested_model": settings.model,
                    "models": trace.models,
                    "label": settings.label,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        summary = {
            "scenario": eval_name,
            "label": settings.label,
            "run": run_number,
            "status": grading["status"],
            **assessment.native_assessment(spec),
            "passed": grading["summary"]["passed"],
            "total": grading["summary"]["total"],
            "models": trace.models,
            "tokens": trace.total_tokens,
            "seconds": round(elapsed, 1),
            "plugin_commit": provenance["plugin_commit"][:12],
            "runner_commit": (fingerprints.runner_provenance()["runner_commit"] or "")[:12] or None,
            "runner_source_sha256": HARNESS_SOURCE_SHA256,
            "plugin_source_sha256": provenance["plugin_source_sha256"],
            "scenario_sha256": grading["scenario_sha256"],
            "plugin_inputs_dirty": provenance["plugin_inputs_dirty"],
            "isolation": "host",
            "runtime": settings.runtime,
            **cost,
            **({"after_assessment": after_assessment} if after_assessment else {}),
            **({"grader_error": grading["grader_error"]} if grading.get("grader_error") else {}),
            **({"identity_failure": identity_failure} if identity_failure else {}),
            **({"service_error": service_error} if service_error else {}),
        }
        return summary
    finally:
        active_error = sys.exc_info()[1]
        try:
            backing.stop_services(services, settings.docker)
        except ServiceUnavailable as cleanup_error:
            if active_error is None:
                raise
            print(f"warning: {cleanup_error} after primary failure: {active_error}", file=sys.stderr, flush=True)
        if settings.keep_workspace:
            print(f"workspace kept at {root}", flush=True)
        else:
            workspaces.remove_tree(root)
