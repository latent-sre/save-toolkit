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
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

import clean_room
import judge as rubric_judge

from . import assessment, backing, catalog, fingerprints, invocation, records, tracing, workspaces
from .backing import Service, ServiceUnavailable
from .checking import Context
from .constants import ROOT
from .fingerprints import HARNESS_SOURCE_SHA256
from .outcomes import CutShort, Stop
from .tracing import TraceSummary


def run_trial(
    spec: Mapping[str, Any],
    *,
    plugin_root: Path,
    label: str,
    model: str | None,
    run_number: int,
    out_dir: Path,
    timeout: int,
    executable: str,
    keep_workspace: bool,
    overwrite: bool = False,
    env_factory: Callable[[], AbstractContextManager[dict[str, str]]] | None = None,
    docker: str = "docker",
    expected_plugin_digest: str | None = None,
    judge_binding: rubric_judge.JudgeBinding | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish a complete attempt; a failed overwrite leaves the previous run intact."""
    if "followups" in spec:
        problems = catalog.validate_scenario(spec)
        if problems:
            raise ValueError("; ".join(problems))
    rubric_judge.validate_binding(judge_binding, fingerprints.required_rubrics(spec))
    target = out_dir / f"eval-{spec['id']}" / label / f"run-{run_number}"
    if target.exists() and not overwrite:
        raise RuntimeError(f"{target} already exists; pass --overwrite or a --run-offset")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Every attempt stays visible (threat-model ADR result rule 7): a replaced run and an attempt that
    # never published move under <label>/attempts/run-N/<k>/, which run-N globs never match.
    history = target.parent / "attempts" / target.name
    kept = [int(p.name) for p in history.iterdir() if p.name.isdigit()] if history.is_dir() else []
    current = (_attempt_number(target) or max(kept, default=0) + 1) if target.exists() else None
    number = max([*kept, current or 0]) + 1
    attempt = _new_attempt_dir(target)
    _write_attempt(attempt, number, "final")
    started_at = records.utc_now()
    backup, published = None, False
    try:
        summary = _run_trial(
            spec,
            plugin_root=plugin_root,
            label=label,
            model=model,
            run_number=run_number,
            run_out=attempt,
            timeout=timeout,
            executable=executable,
            keep_workspace=keep_workspace,
            env_factory=env_factory,
            docker=docker,
            expected_plugin_digest=expected_plugin_digest,
            judge_binding=judge_binding,
            runtime=runtime,
        )
        summary["attempt"] = number
        records.write_record(
            attempt,
            spec,
            label=label,
            run_number=run_number,
            attempt=number,
            started_at=started_at,
            model=model,
            timeout=timeout,
        )
        if target.exists():
            backup = target.with_name(f".{target.name}-previous-{secrets.token_hex(8)}")
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
                _keep_attempt(backup, history, current, "superseded", f"replaced by attempt {number}")
            except Exception as exc:
                print(f"warning: published {target}; previous run retained at {backup}: {exc}", file=sys.stderr)
        print(json.dumps(summary), flush=True)
        return summary
    except BaseException as exc:
        if not published and attempt.exists():
            reason = f"{type(exc).__name__}: {exc}"[:500]
            try:
                records.write_record(
                    attempt,
                    spec,
                    label=label,
                    run_number=run_number,
                    attempt=number,
                    started_at=started_at,
                    model=model,
                    timeout=timeout,
                    end=("incomplete", reason),
                )
            except Exception as record_error:
                print(f"warning: no record for the incomplete attempt {attempt}: {record_error}", file=sys.stderr)
            try:
                _keep_attempt(attempt, history, number, "incomplete", reason)
            except Exception as keep_error:
                print(f"warning: could not keep the incomplete attempt {attempt}: {keep_error}", file=sys.stderr)
        raise


def _new_attempt_dir(target: Path) -> Path:
    """A fresh hidden sibling for one attempt. A plain mkdir inherits the parent's permissions;
    tempfile.mkdtemp makes the folder readable only by its creator on Windows (EVAL-012 DEC-23)."""
    for _ in range(16):
        attempt = target.with_name(f".{target.name}-attempt-{secrets.token_hex(8)}")
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


def _write_attempt(run_dir: Path, number: int, state: str, reason: str | None = None) -> None:
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
    record_path = run_dir / "record.json"
    if record_path.is_file():
        with contextlib.suppress(OSError, ValueError, AttributeError):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["attempt"].update(number=number, state=state, **({"reason": reason} if reason else {}))
            record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def _keep_attempt(run_dir: Path, history: Path, number: int | None, state: str, reason: str) -> Path:
    """Move an attempt that is not the published run into the slot's history, never deleting it."""
    history.mkdir(parents=True, exist_ok=True)
    taken = {int(p.name) for p in history.iterdir() if p.name.isdigit()}
    number = number if number and number not in taken else max(taken, default=0) + 1
    destination = history / str(number)
    run_dir.rename(destination)
    _write_attempt(destination, number, state, reason)
    return destination


def _run_trial(
    spec: Mapping[str, Any],
    *,
    plugin_root: Path,
    label: str,
    model: str | None,
    run_number: int,
    run_out: Path,
    timeout: int,
    executable: str,
    keep_workspace: bool,
    env_factory: Callable[[], AbstractContextManager[dict[str, str]]] | None = None,
    docker: str = "docker",
    expected_plugin_digest: str | None = None,
    judge_binding: rubric_judge.JudgeBinding | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    trace = TraceSummary()
    services: list[Service] = []
    try:
        if root.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError(f"temp workspace {root} is inside the repository")
        provenance = fingerprints.plugin_provenance(plugin_root)
        binding = judge_binding.metadata if judge_binding and fingerprints.required_rubrics(spec) else None
        scenario_identity = fingerprints.scenario_digest(spec, binding)
        if expected_plugin_digest and provenance["plugin_source_sha256"] != expected_plugin_digest:
            inconclusive = "plugin inputs changed before the trial; re-run with one candidate"
        (run_out / "provenance.json").write_text(
            json.dumps(
                {
                    **provenance,
                    **fingerprints.runner_provenance(),
                    "runtime": runtime,
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
                services = backing.start_services(spec, docker)
            except ServiceUnavailable as exc:
                services = []
                inconclusive = f"backing service unavailable: {exc}"
        trace_path = run_out / "stdout.jsonl"
        started = time.time()
        if inconclusive is None:
            make_env = env_factory or (lambda: clean_room.clean_env(subscriber_only=True))
            with make_env() as base_env:
                env = workspaces.child_env(base_env, ws, spec, services)
                resume = None
                for turn, prompt in enumerate([catalog.scenario_prompt(spec, plugin_root), *spec.get("followups", [])]):
                    inconclusive = fingerprints.plugin_drift_problem(plugin_root, provenance["plugin_source_sha256"])
                    if fingerprints.scenario_digest(spec, binding) != scenario_identity:
                        inconclusive = "scenario inputs changed before invocation; re-run the trial"
                    if inconclusive:
                        break
                    turn_out = run_out if turn == 0 else run_out / "followup"
                    turn_out.mkdir(exist_ok=True)
                    command = invocation.build_command(
                        executable,
                        plugin_root,
                        f"save-toolkit:{spec['agent']}" if spec.get("agent") else None,
                        prompt,
                        model,
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
                                command, cwd=str(ws.repo), env=env, stdout=out, stderr=err, timeout=timeout
                            ).returncode
                        except subprocess.TimeoutExpired:
                            timed_out = CutShort(f"timed out after {timeout}s", Stop.WALL_CLOCK)
                    current = tracing.parse_trace(turn_out / "stdout.jsonl")
                    inconclusive = inconclusive or fingerprints.plugin_drift_problem(
                        plugin_root, provenance["plugin_source_sha256"]
                    )
                    if spec.get("followups") and invocation.credential_markers(
                        current.result_text, turn_out / "stdout.jsonl"
                    ):
                        inconclusive = inconclusive or "native credential marker detected; no follow-up allowed"
                    if timed_out:
                        # The partial trace must show the declared profile before its evidence counts.
                        inconclusive = (
                            inconclusive
                            or invocation.profile_problem(current, spec, plugin_root, ws.repo)
                            or (
                                invocation.native_identity_problem(current, spec, resume, complete=False)
                                if spec.get("followups")
                                else None
                            )
                            or timed_out
                        )
                    inconclusive = inconclusive or invocation.invocation_problem(
                        current, returncode, spec, plugin_root, ws.repo, resume
                    )
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
                                    "run_stop": getattr(inconclusive, "kind", None)
                                    if isinstance(inconclusive, CutShort)
                                    else None,
                                },
                                indent=2,
                            ),
                            encoding="utf-8",
                        )
                        (turn_out / "response.md").write_text(current.result_text, encoding="utf-8")
                    if inconclusive:
                        break
                    resume = current.session_id
        else:
            # A missing fixture target cannot be repaired by the model. Starting it here would
            # spend a call with unresolved service placeholders and could make a tool-bearing
            # agent discover or mutate an unrelated host service.
            trace_path.write_text("", encoding="utf-8")
            (run_out / "stderr.txt").write_text("", encoding="utf-8")
        elapsed = time.time() - started
        if not inconclusive or isinstance(inconclusive, CutShort):  # drift voids even a cut-short run
            inconclusive = invocation.void_over_cut(
                inconclusive, fingerprints.plugin_drift_problem(plugin_root, provenance["plugin_source_sha256"])
            )
        trace = tracing.parse_trial_trace(run_out) if trace_path.exists() else TraceSummary()
        git = workspaces.collect_git_facts(ws)
        ctx = Context(spec, ws, trace, git, services=services, plugin_root=plugin_root, judge_binding=judge_binding)
        grading = assessment.grade(ctx, inconclusive=inconclusive, expected_scenario_digest=scenario_identity)
        after_assessment = None
        if services:
            try:
                backing.stop_services(services, docker)
            except ServiceUnavailable as exc:
                # The assessment already stands; a leftover service blocks reusing the environment.
                after_assessment = f"backing service cleanup failed: {exc}"
            finally:
                services = []
        drift = fingerprints.plugin_drift_problem(plugin_root, provenance["plugin_source_sha256"])
        if drift:
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
                    "conversation_sessions": trace.conversation_sessions,
                    "agent_returns": trace.agent_returns,
                    "initial_parent_reference_reads": trace.parent_reads_before_dispatch,
                    "initial_parent_skills_before_dispatch": trace.parent_skills_before_dispatch,
                    "main_models": trace.main_models,
                    "status": grading["status"],
                    "inconclusive": inconclusive,
                    "after_assessment": after_assessment,
                    "run_end": grading.get("run_end"),
                    "models": trace.models,
                    "usage_models": trace.usage_models,
                    "num_turns": trace.num_turns,
                    "tool_counts": trace.tool_counts,
                    "skills": trace.skills,
                    "skills_failed": trace.skills_failed,
                    "advertised_tools": trace.advertised_tools,
                    "mcp_servers": trace.mcp_servers,
                    "permission_mode": trace.permission_mode,
                    "dispatches": trace.dispatches,
                    "denials": trace.denials,
                    "bash_commands": trace.bash_commands,
                    "subagent_bash_commands": trace.subagent_bash_commands,
                    "powershell_commands": trace.powershell_commands,
                    "effect_calls": trace.effect_calls,
                    "tool_errors": trace.tool_errors,
                    "denial_details": trace.denial_details,
                    "commits_before_after": [ws.baseline_commits, git.commit_count],
                    "branch": git.branch,
                    "changed_files": ctx.git.changed,
                    "state_files": state_files,
                    "agents_dir": (ws.repo / ".agents").exists(),
                    "plugin": provenance,
                    "runtime": runtime,
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
                    "requested_model": model,
                    "models": trace.models,
                    "label": label,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        summary = {
            "scenario": eval_name,
            "label": label,
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
            "runtime": runtime,
            **cost,
            **({"after_assessment": after_assessment} if after_assessment else {}),
            **({"grader_error": grading["grader_error"]} if grading.get("grader_error") else {}),
        }
        return summary
    finally:
        active_error = sys.exc_info()[1]
        try:
            backing.stop_services(services, docker)
        except ServiceUnavailable as cleanup_error:
            if active_error is None:
                raise
            print(f"warning: {cleanup_error} after primary failure: {active_error}", file=sys.stderr, flush=True)
        if keep_workspace:
            print(f"workspace kept at {root}", flush=True)
        else:
            workspaces.remove_tree(root)
