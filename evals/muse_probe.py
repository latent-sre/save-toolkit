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
            if "subagent" in name or name in {"agent", "task"}
        )

    def to_summary(self) -> TraceSummary:
        shell = [
            f"<muse shell tool: {name}>" for name, count in self.tool_counts.items()
            if any(word in name for word in ("powershell", "bash", "shell")) for _ in range(count)
        ]
        return TraceSummary(
            result_text=self.result_text,
            tool_counts=dict(self.tool_counts),
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


def augment_from_session_log(trace: MuseTrace) -> MuseTrace:
    """Corroborate a trace from Muse's retained session log, when one exists.

    The stdout MSP stream names tools but carries no arguments; the session
    log is where a SKILL.md read or a subagent target is visible. Absence of a
    log is recorded (`session_log_found` stays False), never treated as
    absence of the action.
    """
    if not trace.session_id:
        return trace
    root = _sessions_root()
    if not root.is_dir():
        return trace
    candidates = sorted(root.glob(f"**/{trace.session_id}/session.jsonl"))
    if not candidates:
        return trace
    try:
        text = candidates[0].read_text(encoding="utf-8", errors="replace")
    except OSError:
        return trace
    trace.session_log_found = True
    trace.skills_loaded.update(_skill_names_in(text))
    for name in re.findall(r'"(?:agent|subagent_type|name)"\s*:\s*"([a-z0-9]+(?:-[a-z0-9]+)*)"', text):
        if "subagent_spawn" in text:
            trace.dispatch_targets.add(name)
    if "subagent_spawn" in text:
        trace.tool_counts.setdefault("subagent_spawn", 1)
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


def build_prompt(spec: dict[str, Any]) -> str:
    """The prompt as sent on Muse: canonical pin injected, then the scenario prompt."""
    prompt = catalog.scenario_prompt(spec, ROOT)
    pinned = _canonical_body(spec)
    if pinned is None:
        return prompt
    label, body = pinned
    return (
        f"You are acting as the {label} defined below. Follow it as your role definition. "
        "It was written for another host: where it names host tools you do not have, use your "
        "closest equivalent, and never claim a tool ran that did not.\n\n"
        f"<canonical-definition>\n{body}\n</canonical-definition>\n\nTask:\n{prompt}"
    )


def _agent_shell_allowed(spec: dict[str, Any]) -> bool:
    """Whether the pinned canonical agent itself holds a shell grant.

    Prompt injection must not widen a lane: a build trial for an agent whose
    definition has no Bash/PowerShell runs with Muse's shell disabled, just
    as the Claude runner's `--agent` would restrict it.
    """
    agent = spec.get("agent")
    if not isinstance(agent, str) or not agent:
        return False
    path = ROOT / "agents" / f"{agent}.md"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1] if text.startswith("---") else ""
    return any(f"{tool}," in frontmatter or f"{tool}\n" in frontmatter
               for tool in ("Bash", "PowerShell"))


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
        "--session-id", session_id,
        "--approval-mode", "never",
        "--prompt-file", str(prompt_file),
    ]
    if kind != "build" and not spec.get("followups"):
        command.append("--disable-write")
    # A pinned agent's own grants govern, over the scenario's default tool set:
    # the Claude runner's `--agent` restricts the same way.
    shell_allowed = (
        _agent_shell_allowed(spec) if spec.get("agent") else bool(tools & SHELL_TOOL_NAMES)
    )
    if not shell_allowed:
        command.append("--disable-shell")
    if not (tools & WEB_TOOL_NAMES) and spec.get("agent") != "researcher":
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


def grade_routing(spec: dict[str, Any], trace: MuseTrace, raw: str) -> list[dict[str, str]]:
    target = spec.get("target") or {}
    name = str(target.get("name") or "")
    expect = (spec.get("routing") or {}).get("expect")
    if not trace.completed:
        return [_expectation("routing", State.INCONCLUSIVE, "run did not complete; discovery unmeasured")]
    observable = bool(trace.tool_counts) or any(k.startswith("tool.") for k in trace.task_kinds)
    # Credit only tool-carrying evidence: the raw stream also echoes the
    # prompt, which may name the target without it ever firing.
    evidence_text = "\n".join(trace.tool_evidence)
    fired = bool(name) and name in evidence_text and observable
    if not observable:
        return [_expectation(
            "routing", State.INCONCLUSIVE,
            "Muse trace carries no tool evidence to credit a component firing; "
            "an inline answer neither proves nor disproves discovery",
        )]
    if expect == "fire":
        state = State.PASS if fired else State.FAIL
        return [_expectation("routing", state, f"target {name!r} {'fired' if fired else 'did not fire'} in tool evidence")]
    if expect == "not_fire":
        state = State.FAIL if fired else State.PASS
        return [_expectation("routing", state, f"target {name!r} {'fired' if fired else 'stayed out'} in tool evidence")]
    return [_expectation("routing", State.INCONCLUSIVE, f"routing expectation {expect!r} not graded on Muse")]


def grade_build(spec: dict[str, Any], trace: MuseTrace, ws: Any) -> list[dict[str, str]]:
    ctx = checking.Context(
        spec=spec, ws=ws, trace=trace.to_summary(), git=workspaces.collect_git_facts(ws)
    )
    expectations = []
    for check in spec.get("checks") or []:
        name = str(check.get("check"))
        if name in {"skill_loaded", "skill_not_loaded"}:
            # Skill credit needs a SKILL.md read in tool evidence or the
            # retained session log, and load order is never visible here.
            if not trace.session_log_found and not trace.skills_loaded:
                expectations.append(_expectation(
                    name, State.INCONCLUSIVE,
                    "no session log or SKILL.md evidence; skill loads unmeasured"))
                continue
            if check.get("before_effects"):
                expectations.append(_expectation(
                    name, State.INCONCLUSIVE,
                    "skill load order relative to effects is not visible in a Muse trace"))
                continue
        run = checking.CHECKS.get(name)
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
    helper = str(spec.get("helper") or "helper")
    expectations = []
    dispatched = (
        any(t.dispatches for t in traces)
        or any(helper in t.dispatch_targets for t in traces)
    )
    if dispatched:
        expectations.append(_expectation("helper dispatch", State.PASS, f"dispatch evidence for {helper!r}"))
    elif traces and traces[0].completed:
        expectations.append(_expectation(
            "helper dispatch", State.INCONCLUSIVE,
            "Muse trace does not name dispatch targets; helper completion unmeasured",
        ))
    else:
        expectations.append(_expectation("helper dispatch", State.INCONCLUSIVE, "first turn did not complete"))
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


def _run_exec(command: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    done = subprocess.run(
        command, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    return done.returncode, done.stdout, done.stderr


def run_trial(
    spec: dict[str, Any], executable: str, model: str | None,
    out: Path, label: str, run_number: int, timeout: int,
) -> dict[str, Any]:
    kind = "native" if spec.get("followups") else catalog.scenario_kind(spec)
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="muse-probe-") as tmp:
        root = Path(tmp)
        ws = None
        if spec.get("fixture") or kind != "routing":
            ws = workspaces.seed_workspace(spec, root / "ws")
            workspace = ws.repo
        else:
            workspace = ROOT
        if kind == "contract" and spec.get("references"):
            workspace = ROOT
        run_dir = out / f"eval-{spec['id']}" / label / f"run-{run_number}"
        run_dir.mkdir(parents=True, exist_ok=True)
        session_id = str(uuid.uuid4())
        traces: list[MuseTrace] = []
        raws: list[str] = []
        prompts = [build_prompt(spec)] + [str(f) for f in spec.get("followups") or []]
        for index, prompt in enumerate(prompts):
            prompt_file = root / f"prompt-{index}.md"
            prompt_file.write_text(prompt, encoding="utf-8")
            command = build_command(executable, spec, workspace, prompt_file, session_id, model)
            try:
                code, stdout, stderr = _run_exec(command, workspace, timeout)
            except subprocess.TimeoutExpired:
                code, stdout, stderr = -1, "", "muse exec timed out"
            (run_dir / f"trace-{index}.jsonl").write_text(stdout, encoding="utf-8")
            if stderr:
                (run_dir / f"stderr-{index}.txt").write_text(stderr, encoding="utf-8")
            trace = augment_from_session_log(parse_muse_trace(stdout))
            if code != 0 and not trace.completed:
                trace.completed = False
            traces.append(trace)
            raws.append(stdout)
        trace = traces[-1]
        raw = "\n".join(raws)
        if not trace.completed:
            expectations = [_expectation(
                "run", State.INCONCLUSIVE,
                "muse exec did not complete a run; nothing about the candidate was measured",
            )]
        elif kind == "build" and ws is not None:
            expectations = grade_build(spec, trace, ws)
        elif kind == "native":
            expectations = grade_native(spec, traces, raw)
        elif kind == "routing":
            expectations = grade_routing(spec, trace, raw)
        else:
            expectations = grade_graders(spec, trace)
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
            "session_id": session_id,
            "seconds": round(time.time() - started, 1),
            "tool_counts": dict(trace.tool_counts),
            "skills_loaded": sorted(trace.skills_loaded),
            "session_log_found": trace.session_log_found,
            "expectations": expectations,
        }
        (run_dir / "record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="job", required=True)
    sub.add_parser("validate")
    run = sub.add_parser("run")
    run.add_argument("--scenario", required=True, help="scenario id, comma list, or 'all'")
    run.add_argument("--label", required=True)
    run.add_argument("--model", default=None, help="Muse model id; default is the host's")
    run.add_argument("--trials", type=int, default=1)
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

