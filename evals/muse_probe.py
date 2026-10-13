"""Run fleet eval scenarios on Muse (`muse exec`), as a separate host baseline.

This is NOT the Claude runner and its records are never comparable with a Sonnet
baseline: the model, harness, tool names and loading model all differ. It reuses
the Claude probe's scenario catalog, graders, checks and workspace seeding, but
launches `muse exec --json` and grades the Muse MSP trace it emits.

Agent pinning is prompt injection, by design: the canonical `agents/<name>.md`
(or `skills/<name>/SKILL.md`) body is prepended to the prompt, and the record
says `pin: prompt-injected`. Nothing here proves Muse enforced that role's
tools or delegation edges; tool restrictions are approximated with
`--disable-shell` / `--disable-write` / `--disable-web-tools` from the
scenario's declared tools.

Where a Muse trace cannot carry the evidence a check needs (tool arguments,
skill-load completion, dispatch targets, a rubric judge), the expectation is
INCONCLUSIVE, never a fabricated PASS or FAIL.

Usage:
  python evals/muse_probe.py validate
  python evals/muse_probe.py run --scenario agent-direct-reliability-engineer-toil-positive \
      --label muse-smoke --trials 1 --out .eval-runs/muse-check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import graders as fleet_graders
from probe import catalog, checking, workspaces
from probe.outcomes import State
from probe.tracing import TraceSummary

EVALS = Path(__file__).resolve().parent
ROOT = EVALS.parent
SCHEMA = "muse-record-v1"
SHELL_TOOL_NAMES = {"Bash", "PowerShell", "execute", "runInTerminal"}
WEB_TOOL_NAMES = {"WebSearch", "WebFetch", "web"}


SKILL_PATH_RE = re.compile(r"skills/([a-z0-9]+(?:-[a-z0-9]+)*)/SKILL\.md")
_FLEET_SKILLS: set[str] | None = None


def _fleet_skill_names() -> set[str]:
    """Canonical fleet skills: only these can be credited as loaded.

    A Muse session log also lists the host's bundled skill catalog, whose
    SKILL.md paths would otherwise credit skills nobody loaded.
    """
    global _FLEET_SKILLS
    if _FLEET_SKILLS is None:
        _FLEET_SKILLS = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    return _FLEET_SKILLS


def _skill_names_in(text: str) -> set[str]:
    normalized = text.replace("\\", "/")
    return {name for name in SKILL_PATH_RE.findall(normalized) if name in _fleet_skill_names()}


@dataclass
class MuseTrace:
    """The gradeable facts in one `muse exec --json` MSP stream."""

    model_id: str = ""
    session_id: str = ""
    result_text: str = ""
    completed: bool = False
    terminal: str = ""
    tool_counts: Counter[str] = field(default_factory=Counter)
    tool_outcomes: list[str] = field(default_factory=list)
    task_kinds: list[str] = field(default_factory=list)
    event_count: int = 0
    # Serialized tool-carrying events only: routing credit reads these, never
    # the prompt echo, which can contain the target's name without it firing.
    tool_evidence: list[str] = field(default_factory=list)
    # Skill names whose SKILL.md appears in tool evidence or the session log.
    skills_loaded: set[str] = field(default_factory=set)
    dispatch_targets: set[str] = field(default_factory=set)
    # True only when a retained session log was found to corroborate the
    # stdout stream; without it, skill/dispatch absence is unmeasured.
    session_log_found: bool = False

    @property
    def dispatches(self) -> list[str]:
        return sorted(
            name for name in self.tool_counts
            if "subagent" in name.lower() or name.lower() in {"agent", "task"}
        )

    # Muse tool name -> the Claude name count checks look up. A Muse count
    # recorded under its own name would read as zero to a `tool_call_count`
    # check naming the Claude tool, silently passing a max-zero prohibition.
    TOOL_NAME_MAP = {
        "read_file": "Read", "read": "Read", "search": "Grep",
        "write_file": "Write", "edit_file": "Edit", "edit": "Edit",
        "powershell": "PowerShell", "bash": "Bash", "web_search": "WebSearch",
        "web_fetch": "WebFetch",
    }

    def to_summary(self) -> TraceSummary:
        counts = dict(self.tool_counts)
        for name, count in self.tool_counts.items():
            mapped = self.TOOL_NAME_MAP.get(name.lower())
            if mapped and mapped != name:
                counts[mapped] = counts.get(mapped, 0) + count
        shell = [
            f"<muse shell tool: {name}>" for name, count in self.tool_counts.items()
            if any(word in name.lower() for word in ("powershell", "bash", "shell"))
            for _ in range(count)
        ]
        return TraceSummary(
            result_text=self.result_text,
            tool_counts=counts,
            tool_counts_complete=self.completed,
            models=[self.model_id] if self.model_id else [],
            has_result=self.completed,
            result_is_error=not self.completed,
            dispatches=self.dispatches,
            agents=self.dispatches,
            session_id=self.session_id,
            bash_commands=shell,
            powershell_commands=shell,
            skills=sorted(self.skills_loaded),
        )


def parse_muse_trace(text: str) -> MuseTrace:
    """Parse Muse MSP JSONL. Unknown event shapes are skipped, never trusted."""
    trace = MuseTrace()
    deltas: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        trace.event_count += 1
        stream = event.get("stream")
        if isinstance(stream, dict) and stream.get("kind") == "session" and not trace.session_id:
            trace.session_id = str(stream.get("id") or "")
        kind = event.get("payload_type", "")
        if kind in {"tool.result", "task.lifecycle.proposed", "task.lifecycle.output"}:
            trace.tool_evidence.append(line)
            trace.skills_loaded.update(_skill_names_in(line))
        if kind == "run.model.configured":
            trace.model_id = str(payload.get("model_id") or trace.model_id)
        elif kind == "run.output.delta":
            deltas.append(str(payload.get("text") or ""))
        elif kind == "run.terminal.completed":
            trace.terminal = str(payload.get("terminal") or "")
            trace.completed = trace.terminal == "completed"
            if payload.get("text"):
                trace.result_text = str(payload["text"])
        elif kind == "tool.result":
            facts = payload.get("correlation_facts")
            if isinstance(facts, dict) and facts.get("tool_name"):
                name = str(facts["tool_name"])
                trace.tool_counts[name] += 1
                trace.tool_outcomes.append(f"{name}:{facts.get('outcome', 'unknown')}")
        elif kind == "task.lifecycle.proposed":
            inner = payload.get("event")
            if isinstance(inner, dict) and inner.get("task_kind"):
                trace.task_kinds.append(str(inner["task_kind"]))
    if not trace.result_text:
        trace.result_text = "".join(deltas)
    return trace


def _sessions_root() -> Path:
    override = os.environ.get("MUSE_SESSIONS_ROOT")
    if override:
        return Path(override)
    data = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(data) / "muse" / "sessions"


def augment_from_session_log(trace: MuseTrace, extra_root: Path | None = None) -> MuseTrace:
    """Corroborate dispatch targets from Muse's retained session log.

    Only a single log line that itself carries a subagent spawn and its own
    target field credits that target: harvesting every name in a log that
    merely mentions spawning (a tool catalog does) would certify a dispatch
    that never happened. Skill loads are NOT credited here — prose and
    catalog listings mention SKILL.md paths without reading them, so skill
    credit comes only from tool-carrying stdout events. Absence of a log is
    recorded (`session_log_found` stays False), never treated as absence of
    the action.
    """
    if not trace.session_id:
        return trace
    candidates: list[Path] = []
    for root in (_sessions_root(), extra_root):
        if root is not None and root.is_dir():
            candidates.extend(root.glob(f"**/{trace.session_id}/session.jsonl"))
    if not candidates:
        return trace
    candidates.sort()
    try:
        text = candidates[0].read_text(encoding="utf-8", errors="replace")
    except OSError:
        return trace
    trace.session_log_found = True
    for line in text.splitlines():
        if "subagent_spawn" not in line:
            continue
        trace.dispatch_targets.update(
            re.findall(r'"(?:subagent_type|agent)"\s*:\s*"([a-z0-9]+(?:-[a-z0-9]+)*)"', line)
        )
    return trace


def _canonical_body(spec: dict[str, Any]) -> tuple[str, str] | None:
    """(label, body) of the canonical definition a scenario pins, if any."""
    agent = spec.get("agent")
    if isinstance(agent, str) and agent:
        path = ROOT / "agents" / f"{agent}.md"
        if path.is_file():
            return f"agent `{agent}`", path.read_text(encoding="utf-8")
    skill = spec.get("skill")
    if isinstance(skill, str) and skill:
        path = ROOT / "skills" / skill / "SKILL.md"
        if path.is_file():
            return f"skill `{skill}`", path.read_text(encoding="utf-8")
    return None


def _scenario_skills(spec: dict[str, Any]) -> list[str]:
    """Fleet skills an agent-pinned scenario exercises, by id-token match.

    The shared catalog forbids pinning both `agent` and `skill`, and the
    temp workspace contains no fleet skills, so without this the candidate
    skill a scenario exists to measure never enters the trial. A skill is
    injected only when the pinned agent's own definition names it and the
    scenario id carries its leading token (``toil`` -> ``toil-reduction``);
    the record lists what was injected so the evidence stays auditable.
    """
    agent = spec.get("agent")
    if not isinstance(agent, str) or not agent:
        return []
    path = ROOT / "agents" / f"{agent}.md"
    if not path.is_file():
        return []
    body = path.read_text(encoding="utf-8")
    tokens = set(str(spec.get("id", "")).split("-"))
    return sorted(
        name for name in _fleet_skill_names()
        if name in body and name.split("-")[0] in tokens
    )


def injected_skills(spec: dict[str, Any]) -> list[str]:
    names = [str(spec["skill"])] if spec.get("skill") else []
    return names + [n for n in _scenario_skills(spec) if n not in names]


def build_prompt(spec: dict[str, Any], workspace: Path | None = None) -> str:
    """The prompt as sent on Muse: canonical pin injected, then the scenario prompt."""
    prompt = catalog.scenario_prompt(spec, ROOT)
    if workspace is not None:
        for reference in spec.get("references") or []:
            staged = (workspace / str(reference)).resolve().as_posix()
            prompt = prompt.replace((ROOT / str(reference)).resolve().as_posix(), staged)
    pinned = _canonical_body(spec)
    parts: list[str] = []
    if pinned is not None:
        label, body = pinned
        parts.append(
            f"You are acting as the {label} defined below. Follow it as your role definition. "
            "It was written for another host: where it names host tools you do not have, use your "
            "closest equivalent, and never claim a tool ran that did not.\n\n"
            f"<canonical-definition>\n{body}\n</canonical-definition>"
        )
    for name in _scenario_skills(spec):
        skill_path = ROOT / "skills" / name / "SKILL.md"
        parts.append(
            f"The method for this task is the `{name}` skill, reproduced exactly below.\n\n"
            f"<skill-definition name=\"{name}\">\n{skill_path.read_text(encoding='utf-8')}\n</skill-definition>"
        )
        for reference in sorted((ROOT / "skills" / name / "references").glob("*.md")):
            parts.append(
                f"<skill-reference skill=\"{name}\" name=\"{reference.name}\">\n"
                f"{reference.read_text(encoding='utf-8')}\n</skill-reference>"
            )
    parts.append(f"Task:\n{prompt}")
    return "\n\n".join(parts)


def _agent_has(spec: dict[str, Any], *tools: str) -> bool:
    """Whether the pinned canonical agent's frontmatter grants any of `tools`.

    Prompt injection must not widen a lane: a trial for an agent whose
    definition lacks a grant runs with Muse's equivalent disabled, just as
    the Claude runner's `--agent` would restrict it.
    """
    agent = spec.get("agent")
    if not isinstance(agent, str) or not agent:
        return False
    path = ROOT / "agents" / f"{agent}.md"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1] if text.startswith("---") else ""
    return any(f"{tool}," in frontmatter or f"{tool}\n" in frontmatter for tool in tools)


def _agent_shell_allowed(spec: dict[str, Any]) -> bool:
    return _agent_has(spec, "Bash", "PowerShell")


def muse_argv(executable: str) -> list[str]:
    """The argv prefix for the Muse binary (a Windows .cmd needs cmd /c)."""
    if Path(executable).suffix.lower() in {".cmd", ".bat"}:
        return ["cmd", "/c", executable]
    return [executable]


def build_command(
    executable: str,
    spec: dict[str, Any],
    workspace: Path,
    prompt_file: Path,
    session_id: str,
    model: str | None,
) -> list[str]:
    kind = catalog.scenario_kind(spec)
    tools = {str(t) for t in catalog.scenario_tools(spec)}
    command = muse_argv(executable) + [
        "exec", "--json",
        "--workspace", str(workspace),
        "--trust-workspace",
        "--session-id", session_id,
        "--approval-mode", "never",
        "--prompt-file", str(prompt_file),
    ]
    # Write access follows the same intersection as shell: a read-only lane
    # (repository-investigator) or a read-only scenario gets no write tools,
    # in build and native trials as much as in contract ones.
    if spec.get("agent"):
        declared_write = {str(t) for t in spec.get("tools") or []} & {"Write", "Edit"}
        write_allowed = _agent_has(spec, "Write", "Edit") and (
            spec.get("tools") is None or bool(declared_write)
        )
    else:
        write_allowed = bool(tools & {"Write", "Edit"})
    if not write_allowed:
        command.append("--disable-write")
    # Restrictions are the intersection of the scenario's declared tools and
    # the pinned agent's own grants: neither may widen the other. A contract
    # trial declaring only Read gets no shell even for a shell-holding agent,
    # exactly as the Claude catalog's minimal-tool trials intend.
    declared = {str(t) for t in spec["tools"]} if spec.get("tools") else None
    if spec.get("agent"):
        shell_allowed = _agent_shell_allowed(spec) and (declared is None or bool(declared & SHELL_TOOL_NAMES))
        web_allowed = bool((declared or tools) & WEB_TOOL_NAMES)
    else:
        shell_allowed = bool(tools & SHELL_TOOL_NAMES)
        web_allowed = bool(tools & WEB_TOOL_NAMES)
    if not shell_allowed:
        command.append("--disable-shell")
    if not web_allowed:
        command.append("--disable-web-tools")
    if model:
        command += ["--model", model]
    max_turns = spec.get("max_turns")
    if isinstance(max_turns, int) and max_turns > 0:
        command += ["--max-model-steps", str(max_turns)]
    return command


def _expectation(text: str, state: State, evidence: str) -> dict[str, str]:
    return {"text": text, "state": str(state), "evidence": evidence[:600]}


def grade_graders(spec: dict[str, Any], trace: MuseTrace) -> list[dict[str, str]]:
    expectations = []
    for index, grader in enumerate(spec.get("graders") or []):
        label = f"grader {grader.get('type', index)}"
        try:
            passed, evidence = fleet_graders.run_grader(dict(grader), trace.result_text)
        except Exception as exc:  # a rubric needs a judge this runner does not bind
            expectations.append(_expectation(label, State.INCONCLUSIVE, f"grader unmeasured on Muse: {exc}"))
            continue
        expectations.append(
            _expectation(label, State.PASS if passed else State.FAIL, str(evidence))
        )
    return expectations


def _reference_expectations(spec: dict[str, Any], trace: MuseTrace) -> list[dict[str, str]]:
    expectations = []
    evidence = "\n".join(trace.tool_evidence)
    for reference in spec.get("references") or []:
        filename = Path(str(reference)).name
        if filename in evidence:
            expectations.append(_expectation(f"reference {filename}", State.PASS, "read in tool evidence"))
        else:
            expectations.append(_expectation(
                f"reference {filename}", State.INCONCLUSIVE,
                "reference read not visible in a Muse trace"))
    return expectations


def grade_contract(spec: dict[str, Any], trace: MuseTrace) -> list[dict[str, str]]:
    expectations: list[dict[str, str]] = []
    if spec.get("skill"):
        # The canonical skill body is injected by construction on this host;
        # that is the pin, and the record says so.
        expectations.append(_expectation(
            f"skill {spec['skill']}", State.PASS, "canonical skill body prompt-injected"))
    expectations.extend(_reference_expectations(spec, trace))
    expectations.extend(grade_graders(spec, trace))
    return expectations


def grade_routing(spec: dict[str, Any], trace: MuseTrace, raw: str) -> list[dict[str, str]]:
    target = spec.get("target") or {}
    name = str(target.get("name") or "")
    expect = (spec.get("routing") or {}).get("expect")
    if not trace.completed:
        return [_expectation("routing", State.INCONCLUSIVE, "run did not complete; discovery unmeasured")]
    # Credit only a structural firing: a fleet SKILL.md read in tool-carrying
    # evidence for a skill target, or a same-line spawn target for an agent
    # target. A name merely mentioned in tool output is not a firing, and
    # absence of that evidence cannot prove a negative on this host, so a
    # `fire` expectation without it is INCONCLUSIVE, never a FAIL.
    if target.get("kind") == "agent":
        fired = bool(name) and name in trace.dispatch_targets
    else:
        fired = bool(name) and name in trace.skills_loaded
    if expect == "fire":
        if fired:
            return [_expectation("routing", State.PASS, f"target {name!r} fired in tool evidence")]
        return [_expectation(
            "routing", State.INCONCLUSIVE,
            f"no SKILL.md read or spawn target credits {name!r}; discovery unmeasured on Muse",
        )]
    if expect == "not_fire":
        if fired:
            return [_expectation("routing", State.FAIL, f"target {name!r} fired in tool evidence")]
        if not trace.completed:
            return [_expectation("routing", State.INCONCLUSIVE, "run did not complete; absence unmeasured")]
        # The contract also requires the declared alternative: an inline or
        # main-session answer, or the named component instead. A blank or
        # wrong-component reply is not a pass merely because the target stayed out.
        alternative = (spec.get("routing") or {}).get("expected_alternative")
        if alternative is None:
            return [_expectation("routing", State.PASS, f"target {name!r} not credited in a completed trace")]
        alternatives = alternative if isinstance(alternative, list) else [alternative]
        for item in alternatives:
            if item in {"inline", "main_session"} and trace.result_text.strip():
                return [_expectation("routing", State.PASS, "target stayed out; inline/main-session answer present")]
            if isinstance(item, dict) and item.get("name") in trace.skills_loaded | trace.dispatch_targets:
                return [_expectation("routing", State.PASS, f"alternative {item.get('name')!r} fired instead")]
            if isinstance(item, str) and item in trace.skills_loaded | trace.dispatch_targets:
                return [_expectation("routing", State.PASS, f"alternative {item!r} fired instead")]
        return [_expectation(
            "routing", State.INCONCLUSIVE,
            f"declared alternative {alternative!r} not established in a Muse trace")]
    return [_expectation("routing", State.INCONCLUSIVE, f"routing expectation {expect!r} not graded on Muse")]


def grade_build(spec: dict[str, Any], trace: MuseTrace, ws: Any) -> list[dict[str, str]]:
    ctx = checking.Context(
        spec=spec, ws=ws, trace=trace.to_summary(), git=workspaces.collect_git_facts(ws)
    )
    expectations = []
    for check in spec.get("checks") or []:
        name = str(check.get("check"))
        run = checking.CHECKS.get(name)
        if run is not None:
            # Gate by the evidence each check declares it reads: a Muse
            # summary cannot carry raw/ordered traces, a judge, or a backing
            # service, and grading those anyway manufactures verdicts.
            needs = run.needs_of(dict(check), spec)
            unmeasurable = needs & {
                checking.Need.RAW_TRACE, checking.Need.ORDERED_TRACE,
                checking.Need.JUDGE, checking.Need.SERVICE,
            }
            if unmeasurable:
                expectations.append(_expectation(
                    name, State.INCONCLUSIVE,
                    f"check needs {sorted(str(n) for n in unmeasurable)}; not visible in a Muse trace"))
                continue
        if name in {"bash_ran", "bash_did_not_run"}:
            # Muse traces carry the shell tool's name, never its arguments:
            # a pattern that names a command cannot be matched or excluded.
            pattern = str(check.get("pattern") or "")
            if pattern not in {"", ".+", ".*", "."}:
                expectations.append(_expectation(
                    name, State.INCONCLUSIVE,
                    f"shell arguments are not visible in a Muse trace; pattern {pattern!r} unmeasured"))
                continue
        if name in {"skill_loaded", "skill_not_loaded"}:
            # Skill credit comes only from a fleet SKILL.md read in
            # tool-carrying stdout evidence; load order is never visible.
            if not trace.skills_loaded:
                expectations.append(_expectation(
                    name, State.INCONCLUSIVE,
                    "no SKILL.md read in tool evidence; skill loads unmeasured"))
                continue
            if check.get("before_effects"):
                expectations.append(_expectation(
                    name, State.INCONCLUSIVE,
                    "skill load order relative to effects is not visible in a Muse trace"))
                continue
        if run is None:
            expectations.append(_expectation(name, State.INCONCLUSIVE, "unknown check on Muse runner"))
            continue
        try:
            outcome = run(ctx, dict(check))
        except Exception as exc:
            expectations.append(_expectation(name, State.INCONCLUSIVE, f"check unmeasured on Muse: {exc!r}"))
            continue
        expectations.append(_expectation(name, outcome.state, outcome.evidence))
    return expectations


def grade_native(
    spec: dict[str, Any], traces: list[MuseTrace], raw: str
) -> list[dict[str, str]]:
    helper = str(spec.get("helper") or "")
    expectations = []
    # Credit only a spawn record naming this helper. A spawn of any other
    # target, or a bare subagent tool count with no visible target, is
    # unmeasured — never a PASS for a dispatch that may not have happened.
    dispatched = bool(helper) and any(helper in t.dispatch_targets for t in traces)
    # A conversation that names no helper (an interview, say) has no dispatch
    # expectation; grading it for one would manufacture an inconclusive.
    if helper and dispatched:
        expectations.append(_expectation("helper dispatch", State.PASS, f"dispatch evidence for {helper!r}"))
    elif helper and traces and traces[0].completed:
        expectations.append(_expectation(
            "helper dispatch", State.INCONCLUSIVE,
            "Muse trace does not name dispatch targets; helper completion unmeasured",
        ))
    elif helper:
        expectations.append(_expectation("helper dispatch", State.INCONCLUSIVE, "first turn did not complete"))
    if traces:
        # The initial turn's own assertions (routing target, reference reads)
        # are part of the contract, not just the final reply's graders.
        if spec.get("routing"):
            expectations.extend(grade_routing(spec, traces[0], raw))
        expectations.extend(_reference_expectations(spec, traces[0]))
    if len(traces) > 1:
        last = traces[-1]
        expectations.append(_expectation(
            "parent continuation",
            State.PASS if last.completed and last.result_text else State.INCONCLUSIVE,
            "follow-up turn completed in the same session" if last.completed else "follow-up turn unmeasured",
        ))
        expectations.extend(grade_graders(spec, last))
    return expectations


def overall(expectations: list[dict[str, str]]) -> State:
    states = {e["state"] for e in expectations}
    if State.FAIL in states:
        return State.FAIL
    if State.INCONCLUSIVE in states or not states:
        return State.INCONCLUSIVE
    return State.PASS


def _run_exec(
    command: list[str], cwd: Path, timeout: int, env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    done = subprocess.run(
        command, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, env=env,
    )
    return done.returncode, done.stdout, done.stderr


_PROVENANCE: dict[str, str] | None = None


def _provenance(executable: str) -> dict[str, str]:
    """Candidate and host identity a record is bound to, computed once."""
    global _PROVENANCE
    if _PROVENANCE is not None:
        return _PROVENANCE

    def git(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args], cwd=str(ROOT), capture_output=True, text=True, timeout=30
            ).stdout.strip()
        except OSError:
            return ""

    try:
        version = subprocess.run(
            muse_argv(executable) + ["--version"], capture_output=True, text=True, timeout=30
        ).stdout.strip()
    except OSError:
        version = ""
    runner = Path(__file__).resolve()
    _PROVENANCE = {
        "candidate_commit": git("rev-parse", "HEAD"),
        "candidate_dirty": "true" if git("status", "--porcelain") else "false",
        "runner_sha256": hashlib.sha256(runner.read_bytes()).hexdigest(),
        "muse_cli_version": version,
    }
    return _PROVENANCE


def run_trial(
    spec: dict[str, Any], executable: str, model: str | None,
    out: Path, label: str, run_number: int, timeout: int,
) -> dict[str, Any]:
    kind = catalog.scenario_kind(spec)
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="muse-probe-") as tmp:
        root = Path(tmp)
        # Every trial is staged outside the source checkout: the seeded temp
        # workspace is the only workspace, and named references are copied
        # into it, so reads cannot reach the checkout's ignored private files.
        ws = workspaces.seed_workspace(spec, root / "ws")
        workspace = ws.repo
        for reference in spec.get("references") or []:
            source = ROOT / str(reference)
            if source.is_file():
                staged = workspace / str(reference)
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        env = workspaces.child_env(dict(os.environ), ws, spec)
        # PowerShell otherwise writes its module analysis cache into the
        # seeded repo, where change-boundary checks read it as candidate work.
        env["PSModuleAnalysisCachePath"] = str(ws.root / "home" / "ps-module-cache")
        # The isolated home has no Muse login; copy the credential file
        # byte-for-byte (never read here) so `muse exec` can authenticate,
        # exactly as the Claude probe copies its credential directory. The
        # file sits outside the trial workspace, which is the only tree the
        # agent's tools are rooted in.
        auth_source = Path.home() / ".config" / "muse" / "auth.json"
        if auth_source.is_file():
            auth_dest = ws.root / "home" / "muse" / "auth.json"
            auth_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(auth_source, auth_dest)
        run_dir = out / f"eval-{spec['id']}" / label / f"run-{run_number}"
        run_dir.mkdir(parents=True, exist_ok=True)
        session_id = str(uuid.uuid4())
        traces: list[MuseTrace] = []
        raws: list[str] = []
        runs: list[tuple[int, str, str]] = []
        prompts = [build_prompt(spec, workspace)] + [str(f) for f in spec.get("followups") or []]
        for index, prompt in enumerate(prompts):
            prompt_file = root / f"prompt-{index}.md"
            prompt_file.write_text(prompt, encoding="utf-8")
            command = build_command(executable, spec, workspace, prompt_file, session_id, model)
            try:
                code, stdout, stderr = _run_exec(command, workspace, timeout, env)
            except subprocess.TimeoutExpired:
                code, stdout, stderr = -1, "", "muse exec timed out"
            runs.append((code, stdout, stderr))
            (run_dir / f"trace-{index}.jsonl").write_text(stdout, encoding="utf-8")
            if stderr:
                (run_dir / f"stderr-{index}.txt").write_text(stderr, encoding="utf-8")
            trace = augment_from_session_log(parse_muse_trace(stdout), ws.root / "home")
            if code != 0 and not trace.completed:
                trace.completed = False
            traces.append(trace)
            raws.append(stdout)
        trace = traces[-1]
        raw = "\n".join(raws)
        codes = [code for code, _stdout, _stderr in runs]
        if not trace.completed or any(code != 0 for code in codes):
            expectations = [_expectation(
                "run", State.INCONCLUSIVE,
                "muse exec did not complete cleanly; nothing about the candidate was measured",
            )]
        elif spec.get("followups"):
            expectations = grade_native(spec, traces, raw)
        elif kind == "build" and ws is not None:
            expectations = grade_build(spec, trace, ws)
        elif kind == "routing":
            expectations = grade_routing(spec, trace, raw)
        else:
            expectations = grade_contract(spec, trace)
        status = overall(expectations)
        (run_dir / "response.md").write_text(trace.result_text, encoding="utf-8")
        (run_dir / "grading.json").write_text(
            json.dumps({"status": str(status), "expectations": expectations}, indent=2),
            encoding="utf-8",
        )
        record = {
            "schema": SCHEMA,
            "host": "muse",
            "pin": "prompt-injected" if _canonical_body(spec) else "none",
            "scenario": spec["id"],
            "kind": kind,
            "label": label,
            "run": run_number,
            "status": str(status),
            "model_id": trace.model_id or model or "default",
            "session_id": trace.session_id or session_id,
            "seconds": round(time.time() - started, 1),
            "tool_counts": dict(sum((t.tool_counts for t in traces), Counter())),
            "skills_loaded": sorted(trace.skills_loaded),
            "injected_skills": injected_skills(spec),
            "session_log_found": trace.session_log_found,
            "prompt_sha256": hashlib.sha256("\n".join(prompts).encode("utf-8")).hexdigest(),
            **_provenance(executable),
            "expectations": expectations,
        }
        (run_dir / "record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="job", required=True)
    sub.add_parser("validate")
    run = sub.add_parser("run")
    run.add_argument("--scenario", required=True, help="scenario id, comma list, or 'all'")
    run.add_argument("--label", required=True)
    run.add_argument("--model", default=None, help="Muse model id; default is the host's")
    run.add_argument("--trials", type=_positive_int, default=1)
    run.add_argument("--timeout", type=int, default=600)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--executable", default=shutil.which("muse") or "muse")
    args = parser.parse_args(argv)
    specs = catalog.load_all_scenarios()
    if args.job == "validate":
        counts = Counter(catalog.scenario_kind(s) for s in specs)
        print(f"scenarios OK -- {len(specs)} spec(s) ({dict(counts)}); Muse runner covers "
              "routing, contract, build and native kinds")
        return 0
    wanted = (
        specs if args.scenario == "all"
        else [s for s in specs if s["id"] in {x.strip() for x in args.scenario.split(",")}]
    )
    if not wanted:
        print(f"no scenario matched {args.scenario!r}", file=sys.stderr)
        return 2
    records = []
    for spec in wanted:
        for number in range(1, args.trials + 1):
            record = run_trial(spec, args.executable, args.model, args.out, args.label, number, args.timeout)
            records.append(record)
            print(json.dumps({k: record[k] for k in ("scenario", "kind", "status", "model_id")}))
    passed = sum(r["status"] == State.PASS for r in records)
    print(f"muse probe: {passed}/{len(records)} PASS "
          f"({sum(r['status'] == State.FAIL for r in records)} FAIL, "
          f"{sum(r['status'] == State.INCONCLUSIVE for r in records)} INCONCLUSIVE)")
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())

