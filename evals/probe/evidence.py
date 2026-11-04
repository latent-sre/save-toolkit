"""What one attempt observed, as the evidence-v1 artifact it writes beside its grade (RUNNER-001).

`EvidenceV1` is the contract: every `evidence.json` validates against it strictly, as the JSON its
readers parse, and docs/fleet-evaluation/eval-evidence-v1.schema.json is generated from it
(`build_probe.py schema --model evidence`). It holds what the attempt saw, never what the checks
concluded: the identity it ran under, the host it ran on (in its own block, since those facts are the
computer's and not the measurement's), the parsed trace in full with a digest of each raw trace, the
workspace's git facts and state files, the backing services, how the run ended, each native turn,
and the outcomes of the probes: the checks a regrade cannot re-measure, whose live outcome is
therefore evidence. The live path serialises what it observed, probes measured; a pre-evidence run
directory is loaded into the same shape by `legacy`; `engine.grade` grades from it, live or saved.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, get_args

from pydantic import ConfigDict, Field

from . import assessment, conversations, fingerprints, invocation, layout, tracing
from .checking import Context
from .outcomes import CutShort, Ending, Outcome, Polarity, State, Stop
from .records import Sha256, UtcTime, _Section
from .tracing import TraceSummary


class EvidenceFormat(_Section):
    name: Literal["save-toolkit.eval-evidence"]
    version: Literal[1]


EVIDENCE_FORMAT = {field: get_args(info.annotation)[0] for field, info in EvidenceFormat.model_fields.items()}
FILE = "evidence.json"


class Identity(_Section):
    """What the measurement is bound to: the case, the candidate, the runner, the judge and the model.
    The same on every host that measures the same inputs."""

    case_id: str
    case_sha256: Sha256 | None = Field(
        description="The case alone: scenario, oracle bytes and rubrics, without the runner; null when a "
        "saved run recorded none, never the current inputs."
    )
    scenario_sha256: str | None = Field(description="The case bound to the runner, Python and judge that graded it.")
    plugin_commit: str | None
    plugin_inputs_dirty: bool | None
    plugin_source_sha256: str | None
    runner_commit: str | None
    runner_source_dirty: bool | None
    runner_source_sha256: str | None
    requested_model: str | None
    observed_models: list[str]
    judge_binding: dict[str, Any] | None = Field(
        description="The calibration receipt and its digest, without the judge's execution identity."
    )


class Host(_Section):
    """The computer the attempt ran on: its paths, CLI and account, and the judge's execution identity.
    A regrade elsewhere compares the measurement, not this block."""

    runtime: dict[str, Any] | None
    workspace: str | None = Field(description="The repository path the trial's commands named.")
    plugin_root: str | None
    plugin_served_from: str | None = Field(description="The image of the measured inputs the trial was served.")
    judge_execution: dict[str, Any] | None = Field(description="The judge's Python, PyYAML, source and CLI.")
    judge_cache_dir: str | None


class Trace(_Section):
    """The parsed trace, every `TraceSummary` field, with a digest of each raw trace it was read from."""

    result_text: str
    skills: list[str]
    skills_failed: list[str]
    bash_commands: list[str]
    powershell_commands: list[str]
    subagent_bash_commands: list[str]
    effect_calls: list[dict[str, Any]]
    dispatches: list[str]
    agents: list[str]
    agents_failed: list[str]
    runtime_plugins: list[Any]
    read_attempts: list[dict[str, Any]]
    tool_counts: dict[str, int]
    tool_counts_complete: bool
    denials: list[str]
    duration_ms: int
    total_tokens: int
    output_tokens: int
    models: list[str]
    usage_models: list[str]
    num_turns: int | None
    total_cost_usd: float | None
    has_result: bool
    result_is_error: bool
    result_subtype: str
    tool_errors: list[str]
    denial_details: list[dict[str, Any]]
    subagent_tool_ids: list[str]
    saw_init: bool
    advertised_tools: list[str]
    advertised_skills: list[str]
    foreign_skills: list[str]
    mcp_servers: list[Any]
    permission_mode: str
    session_id: str
    init_session_ids: list[str]
    main_skills: list[str]
    main_skills_before_effects: list[str]
    agent_returns: list[dict[str, Any]]
    conversation_sessions: list[str]
    invocation_evidence: list[dict[str, Any]]
    parent_reads_before_dispatch: list[dict[str, Any]]
    parent_skills_before_dispatch: list[str]
    main_models: list[str]
    raw_sha256: dict[str, Sha256] = Field(
        description="Each raw trace the facts were read from, by path inside the attempt folder."
    )
    restored_from_summary: bool = Field(
        description="The raw trace was gone, so only what the trace summary restores is here."
    )


class Git(_Section):
    commits_before: int
    commits_after: int
    commit_ids_before: list[str] | None
    commit_ids_after: list[str] | None
    branch: str
    changed: list[list[str]] = Field(description="Each changed path as [status, posix path].")
    problem: str | None = Field(description="Why the changed paths could not be listed, if they could not.")
    patch_sha256: Sha256 | None


class WorkspaceFacts(_Section):
    state_files: dict[str, str]
    agents_dir: bool
    baseline_branch: str


class ServiceFacts(_Section):
    name: str
    image: str
    base_url: str


class RunEnding(_Section):
    kind: Ending
    stop: Stop | None
    reason: str | None
    identity_failure: str | None = Field(description="Why the run was not the candidate declared (rule 1).")


class Turn(_Section):
    """One native invocation, as its `invocation.json` and raw trace record it."""

    folder: str
    argv: list[str]
    resume: str | None
    expected_model: str | None
    session_id: str | None
    main_models: list[str] | None
    init_session_ids: list[str] | None
    exit_code: int | None
    state: str | None
    cut_short: bool | None
    run_stop: str | None
    inconclusive: str | None
    started_at: UtcTime | None
    ended_at: UtcTime | None
    raw_sha256: Sha256 | None
    response_sha256: Sha256 | None
    # What a regrade replays the turn's boundary and release checks from, so a native run needs its
    # evidence alone. Absent from records written before they were added, which regrade from files.
    invoked: bool | None = Field(default=None, description="Whether the invocation's folder exists.")
    workspace: str | None = Field(default=None, description="The repository path this invocation ran in.")
    trace: Trace | None = Field(default=None, description="This invocation's parsed raw trace.")
    credential_markers: list[str] | None = Field(
        default=None, description="Credential-shaped markers in its final text and raw trace, by name only."
    )
    input_sha256: Sha256 | None = Field(default=None, description="Digest of the released input.md text.")
    release: dict[str, Any] | None = Field(default=None, description="Its release.json, an incident turn's.")
    judge_context_sha256: Sha256 | None = Field(
        default=None, description="Key-order-independent digest of its judge-context.json."
    )
    response_text_sha256: Sha256 | None = Field(default=None, description="Digest of the saved response.md text.")


class ProbeOutcome(_Section):
    """A check a regrade cannot re-measure, so its live outcome is evidence: a paid judgment, or a
    reading of the workspace or a service that left with the run."""

    id: str
    text: str
    kind: Polarity
    state: State
    evidence: str
    kept_as: str


class EvidenceV1(_Section):
    """One eval attempt's evidence, version 1 (docs/fleet-evaluation/contracts.md#evidence-record-v1)."""

    model_config = ConfigDict(extra="forbid", title="save-toolkit eval evidence, v1")

    format: EvidenceFormat
    written_by: Literal["live", "legacy"] = Field(description="The live attempt, or `legacy` from a saved run.")
    identity: Identity
    host: Host
    trace: Trace
    git: Git
    workspace: WorkspaceFacts
    services: list[ServiceFacts]
    service_problem: str | None
    ending: RunEnding
    turns: list[Turn]
    conversation: dict[str, Any] | None = Field(
        default=None, description="An incident conversation's index (conversation.json), when it has one."
    )
    probes: list[ProbeOutcome]


def evidence_schema() -> dict[str, Any]:
    """The JSON Schema of evidence-v1, as published for its readers."""
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **EvidenceV1.model_json_schema()}


def write(run_dir: Path, evidence: EvidenceV1) -> dict[str, Any]:
    """Write the evidence beside the attempt's artifacts, as the JSON its readers parse."""
    return _store(run_dir / FILE, evidence)


def _store(path: Path, evidence: EvidenceV1) -> dict[str, Any]:
    fields = EvidenceV1.model_validate_json(evidence.model_dump_json()).model_dump(mode="json")
    layout.write_json(path, fields)
    return fields


def file_sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def trace_facts(trace: TraceSummary, run_dir: Path | None, *, restored: bool) -> Trace:
    """Every field of the parsed trace, with the digest of each raw trace under the attempt folder."""
    raw = (
        {
            folder.relative_to(run_dir).joinpath("stdout.jsonl").as_posix(): digest
            for folder in _raw_trace_folders(run_dir)
            if (digest := file_sha256(folder / "stdout.jsonl")) is not None
        }
        if run_dir is not None
        else {}
    )
    return Trace(**dataclasses.asdict(trace), raw_sha256=raw, restored_from_summary=restored)


def _raw_trace_folders(run_dir: Path) -> list[Path]:
    """The folders whose raw traces the evidence digests. A conversation index the replay refuses
    leaves the run's own: the regrade names the damaged index itself, and the evidence must not abort it."""
    try:
        return layout.saved_folders(run_dir)
    except ValueError:
        return [run_dir]


_UTC_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")


def _typed(value: object, kind: type) -> Any:
    """A saved value of exactly `kind`, else None: a damaged field is unknown, never coerced into
    place. The regrade names damaged invocation evidence itself; the evidence must not abort it."""
    return value if type(value) is kind else None


def _strings(value: object) -> list[str] | None:
    return list(value) if isinstance(value, list) and all(isinstance(v, str) for v in value) else None


def turns(run_dir: Path | None, spec: Mapping[str, Any] | None = None) -> list[Turn]:
    """Each native invocation the attempt saved, in order, with what a regrade replays from it; an
    attempt with one invocation has none. With the scenario, every invocation it declares is a turn,
    one that never ran recorded as not invoked: a conversation can end before its follow-up starts,
    and its replay reads that as the file replay does. A damaged field is unknown, never coerced."""
    if run_dir is None:
        return []
    folders = (
        conversations.folders(run_dir, spec)
        if spec is not None and spec.get("followups")
        else layout.saved_folders(run_dir)
    )
    if len(folders) < 2:
        return []
    return [_turn(run_dir, folder) for folder in folders]


def _turn(run_dir: Path, folder: Path) -> Turn:
    saved = layout.read_object(folder / "invocation.json") or {}
    times = {name: _typed(saved.get(name), str) for name in ("started_at", "ended_at")}
    released = conversations.released_from(folder)
    trace_path = folder / "stdout.jsonl"
    try:
        parsed = tracing.parse_trace(trace_path) if trace_path.is_file() else None
    except OSError, ValueError:
        parsed = None
    return Turn(
        folder=folder.relative_to(run_dir).as_posix() or ".",
        argv=[str(arg) for arg in saved.get("argv") or []] if isinstance(saved.get("argv"), list) else [],
        resume=_typed(saved.get("resume"), str),
        expected_model=_typed(saved.get("expected_model"), str),
        session_id=_typed(saved.get("session_id"), str),
        main_models=_strings(saved.get("main_models")),
        init_session_ids=_strings(saved.get("init_session_ids")),
        exit_code=_typed(saved.get("exit_code"), int),
        state=_typed(saved.get("state"), str),
        cut_short=_typed(saved.get("cut_short"), bool),
        run_stop=_typed(saved.get("run_stop"), str),
        inconclusive=_typed(saved.get("inconclusive"), str),
        started_at=times["started_at"] if times["started_at"] and _UTC_TIME.match(times["started_at"]) else None,
        ended_at=times["ended_at"] if times["ended_at"] and _UTC_TIME.match(times["ended_at"]) else None,
        raw_sha256=file_sha256(trace_path),
        response_sha256=file_sha256(folder / "response.md"),
        invoked=folder.exists(),
        workspace=_typed(saved.get("workspace"), str),
        trace=Trace(**dataclasses.asdict(parsed), raw_sha256={}, restored_from_summary=False) if parsed else None,
        credential_markers=invocation.credential_markers(parsed.result_text, trace_path) if parsed else None,
        input_sha256=released.input_sha256,
        release=dict(released.release) if released.release is not None else None,
        judge_context_sha256=released.judge_context_sha256,
        response_text_sha256=released.response_text_sha256,
    )


def conversation_of(run_dir: Path | None) -> dict[str, Any] | None:
    """The incident conversation index a run saved, if it saved one."""
    return layout.read_object(run_dir / "conversation.json") if run_dir is not None else None


def probes(
    spec: Mapping[str, Any], grading: Mapping[str, Any], trace: TraceSummary, plugin_root: Path, judge_binding: Any
) -> list[ProbeOutcome]:
    """The outcomes a saved grade recorded for every expectation a regrade keeps rather than
    re-measures, each found by the id the grade recorded it under, its saved scenario identity and
    position (`<identity>:<index>`), and by its text; an expectation the grade does not identify so
    is not evidence (a legacy record without identities, or one graded as another scenario)."""
    items = assessment.plan(spec, trace, None, plugin_root, judge_binding, keep=True)
    identity = grading.get("scenario_sha256")
    recorded: dict[object, Mapping[str, Any]] = {}
    for saved in grading.get("expectations") or []:
        recorded.setdefault(saved.get("id"), saved)
    probes = []
    for index, item in enumerate(items):
        saved = recorded.get(fingerprints.assertion_id(identity, index)) if isinstance(identity, str) else None
        if item.kept_as is None or saved is None or saved.get("text") != item.text:
            continue
        probes.append(
            ProbeOutcome(
                id=str(saved["id"]),
                text=item.text,
                kind=item.polarity,
                # An older grade recorded no state; the outcome reads one from what it did record.
                state=State(saved["state"])
                if "state" in saved
                else Outcome.read(saved["passed"], saved["evidence"]).state,
                evidence=str(saved.get("evidence") or ""),
                kept_as=item.kept_as,
            )
        )
    return probes


def binding_of(found: EvidenceV1) -> dict[str, Any] | None:
    """The judge binding the attempt graded under, rejoined from its measurement and host parts."""
    if found.identity.judge_binding is None:
        return None
    return {
        **found.identity.judge_binding,
        "execution": found.host.judge_execution,
        "cache_dir": found.host.judge_cache_dir,
    }


def split_binding(binding: Mapping[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None, Any]:
    """A judge binding's measurement part, its host-bound execution identity, and its cache directory."""
    if not binding:
        return None, None, None
    measurement = {key: value for key, value in binding.items() if key not in ("execution", "cache_dir")}
    return measurement, binding.get("execution"), binding.get("cache_dir")


def ending_of(grading: Mapping[str, Any], identity_failure: str | None) -> RunEnding:
    """How the run ended, as a saved grade recorded it: the v1 record's reading of the same fields.
    The reason is the run's, why it was voided or cut short, never a check's own."""
    kind = (
        Ending.VOID
        if grading.get("void")
        else Ending(grading["run_end"])
        if grading.get("run_end") in (Ending.CUT_SHORT, Ending.TURN_LIMIT)
        else Ending.COMPLETED
    )
    stop = grading.get("run_stop") if kind is Ending.CUT_SHORT else None
    reason = (
        grading.get("void")
        if kind is Ending.VOID
        else grading.get("inconclusive") or grading.get("unmeasured")
        if kind is Ending.CUT_SHORT
        else None
    )
    return RunEnding(
        kind=kind,
        stop=Stop(stop) if stop is not None else None,
        reason=str(reason) if reason else None,
        identity_failure=identity_failure,
    )


def workspace_facts(ctx: Context) -> WorkspaceFacts:
    """What the attempt left in its workspace that the checks read: read before any probe runs, since
    a probe that executes the candidate's code with the fixture's env can write here too."""
    return WorkspaceFacts(
        # In full: the checks read the state files from here, so a bounded copy would hide what a
        # forbidden action wrote past the bound (the trace summary keeps a bounded copy).
        state_files={
            layout.text_name(p.name): p.read_text(encoding="utf-8", errors="replace")
            for p in (ctx.ws.state_dir.iterdir() if ctx.ws.state_dir.is_dir() else ())
            if p.is_file()
        },
        agents_dir=(ctx.ws.repo / ".agents").exists(),
        baseline_branch=ctx.ws.baseline_branch,
    )


def ending_from(run_level: str | None, *, turn_limit: bool, identity_failure: str | None) -> RunEnding:
    """How the run that just ran ended: voided by `run_level` (rule 1), cut short by it (rules 2 and
    4), ended by the CLI at its declared turn limit, or completed."""
    if isinstance(run_level, CutShort):
        return RunEnding(
            kind=Ending.CUT_SHORT, stop=run_level.kind, reason=str(run_level), identity_failure=identity_failure
        )
    if run_level:
        return RunEnding(kind=Ending.VOID, stop=None, reason=run_level, identity_failure=identity_failure)
    kind = Ending.TURN_LIMIT if turn_limit else Ending.COMPLETED
    return RunEnding(kind=kind, stop=None, reason=None, identity_failure=identity_failure)


def ended(found: EvidenceV1, run_level: str | None, *, identity_failure: str | None) -> EvidenceV1:
    """The same evidence with how the run ended settled after it was observed: a drift of the measured
    inputs found after grading voids the run its evidence describes (rule 1)."""
    return found.model_copy(
        update={"ending": ending_from(run_level, turn_limit=False, identity_failure=identity_failure)}
    )


def from_live(
    ctx: Context,
    run_dir: Path | None,
    *,
    identity: str,
    binding: Mapping[str, Any] | None,
    ending: RunEnding,
    probes: list[ProbeOutcome],
    service_problem: str | None,
    provenance: Mapping[str, Any],
    runtime: Mapping[str, Any] | None,
    requested_model: str | None,
    workspace: WorkspaceFacts | None = None,
) -> EvidenceV1:
    """The evidence of the attempt that just ran, from the objects the trial read, before anything
    is graded: `identity` is the scenario digest the trial started under, `binding` the judge
    binding its identity binds, `probes` what `engine.probe` measured, `service_problem` a
    backing service that stopped answering, after the proxy stopped or during a probe, and
    `workspace` the workspace facts as they stood before the probes ran (read now when left out)."""
    binding, execution, cache_dir = split_binding(binding)
    git = ctx.git
    return EvidenceV1(
        format=EvidenceFormat(**EVIDENCE_FORMAT),
        written_by="live",
        identity=Identity(
            case_id=str(ctx.spec["id"]),
            case_sha256=fingerprints.case_digest(ctx.spec),
            scenario_sha256=identity,
            plugin_commit=provenance.get("plugin_commit"),
            plugin_inputs_dirty=provenance.get("plugin_inputs_dirty"),
            plugin_source_sha256=provenance.get("plugin_source_sha256"),
            runner_commit=provenance.get("runner_commit"),
            runner_source_dirty=provenance.get("runner_source_dirty"),
            runner_source_sha256=provenance.get("runner_source_sha256"),
            requested_model=requested_model,
            observed_models=list(ctx.trace.models),
            judge_binding=binding,
        ),
        host=Host(
            runtime=dict(runtime) if runtime is not None else None,
            workspace=str(ctx.ws.repo),  # as the trial's commands named it: the path the CLI ran in
            plugin_root=provenance.get("plugin_root"),
            plugin_served_from=provenance.get("plugin_served_from"),
            judge_execution=execution,
            judge_cache_dir=cache_dir,
        ),
        trace=trace_facts(ctx.trace, run_dir, restored=False),
        git=Git(
            commits_before=ctx.ws.baseline_commits,
            commits_after=git.commit_count,
            commit_ids_before=sorted(ctx.ws.baseline_commit_ids) if ctx.ws.baseline_commit_ids is not None else None,
            commit_ids_after=sorted(git.commit_ids) if git.commit_ids is not None else None,
            branch=git.branch,
            changed=[[status, path] for status, path in git.changed],
            problem=git.problem,
            patch_sha256=file_sha256(run_dir / "outputs" / "workspace.patch") if run_dir is not None else None,
        ),
        workspace=workspace or workspace_facts(ctx),
        services=[ServiceFacts(name=s.name, image=s.image, base_url=s.base_url) for s in ctx.services],
        service_problem=service_problem,
        ending=ending,
        turns=turns(run_dir, ctx.spec),
        conversation=conversation_of(run_dir),
        probes=probes,
    )
