"""Builders shared by the evals/ test suites. Not a test module: pytest collects only test_*.py.

A test module imports what it shares from here, never from another test module, so moving or
splitting a test file cannot break its neighbours. Plain functions and one base class rather than
pytest fixtures, because most suites are unittest.TestCase classes that also run directly
(`python evals/test_judge.py`), where fixtures do not exist. Nothing here runs at import
time beyond defining names.

This module lives beside the tests and outside evals/probe/ on purpose: every module in that
package is hashed into the runner identity (probe/fingerprints.py, HARNESS_FILES), so a test helper
there would change the identity and orphan every saved run.
"""

from __future__ import annotations

import contextlib
import copy
import functools
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest import mock

import judge
from probe import assessment, catalog, checking, fingerprints, tracing, workspaces

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"

# The smallest build scenario the runner accepts: a seeded repository with a passing unittest
# suite, one fork branch, a `cf` shim that logs where `cf_log_has_no` reads, and one environment
# variable. Tests take copies through tiny_spec() and tiny_fixture(), never this dict itself.
_TINY_SPEC: dict[str, Any] = {
    "id": "tiny",
    "agent": "software-engineer",
    "prompt": "do the thing",
    "fixture": {
        "files": {
            "README.md": "# tiny\n",
            "pkg/__init__.py": "",
            "tests/__init__.py": "",
            "tests/test_ok.py": "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
        },
        "branches": {"fork/x": {"files": {"setup.py": "print('x')\n"}}},
        "fake_bin": {"cf": '#!/bin/sh\nprintf \'%s\\n\' "$*" >> "${STATE_DIR}/cf-invocations.log"\necho OK\n'},
        "env": {"CF_USERNAME": "deploy-bot"},
    },
    "checks": [{"check": "no_new_commits"}],
}

# A text-only contract scenario: an agent and a grader, no fixture.
_CONTRACT_SPEC: dict[str, Any] = {
    "id": "contract-sre-text-only",
    "agent": "sre-assistant",
    "prompt": "Latency tripled on checkout. What do you make of it?",
    "graders": [{"type": "contains_any", "of": ["latency"]}],
}

# Each check's reviewed polarity (result rules 2 and 3). A forbidding check fails even a run cut short
# and holds its scenario to every trial, so re-declaring one must change this table on purpose: the
# forbidding and requiring sets are derived from the declarations and cannot catch it themselves.
INTENDED_POLARITY = {
    "bash_did_not_run": "forbids", "cf_log_has_no": "forbids", "changed_files_not_containing": "forbids",
    "changes_within": "forbids", "dispatches_namespaced": "forbids", "no_agents_dir": "forbids",
    "no_new_commits": "forbids", "no_task_dispatch": "forbids", "no_workspace_changes": "forbids",
    "ran_outside_checkout": "forbids", "service_unchanged": "forbids", "skill_not_loaded": "forbids",
    "state_file_absent": "forbids", "text_not_contains": "forbids", "text_not_regex": "forbids",
    "bash_ran": "requires", "command_exit_zero": "requires", "command_output_regex": "requires",
    "file_contains": "requires", "file_exists": "requires", "glob_exists": "requires",
    "grafana_dashboard_write": "requires", "grafana_query_succeeded": "requires", "service_array_item": "requires",
    "service_get": "requires", "skill_loaded": "requires", "task_completed": "requires",
    "text_contains_any": "requires", "text_regex": "requires", "verification_completed": "requires",
}  # fmt: skip

# The one reference the reference-read tests name: a real file in the measured plugin.
AGENT_SECURITY_REFERENCE = "skills/agent-authoring/references/agent-security.md"


def tiny_spec(**changes: Any) -> dict[str, Any]:
    """A fresh copy of the tiny build scenario with the given top-level keys replaced."""
    return {**copy.deepcopy(_TINY_SPEC), **changes}


def tiny_fixture(**changes: Any) -> dict[str, Any]:
    """A fresh copy of the tiny scenario's fixture with the given keys replaced."""
    return {**copy.deepcopy(_TINY_SPEC["fixture"]), **changes}


def contract_spec(**changes: Any) -> dict[str, Any]:
    """A fresh copy of the fixtureless contract scenario with the given top-level keys replaced."""
    return {**copy.deepcopy(_CONTRACT_SPEC), **changes}


# Committed scenarios are parsed and validated once per process (a full load_all_scenarios takes a
# quarter of a second) and every caller gets its own deep copy, so no test sees another's edits.
@functools.cache
def _parsed_scenario(path: Path) -> dict[str, Any]:
    return catalog.load_scenario(path)


@functools.cache
def _parsed_scenarios(directories: tuple[Path, ...]) -> list[dict[str, Any]]:
    return catalog.load_all_scenarios(directories[0] if len(directories) == 1 else None)


def scenario_file(path: Path) -> dict[str, Any]:
    """A fresh copy of the committed scenario at `path`, validated as the runner loads it."""
    return copy.deepcopy(_parsed_scenario(Path(path).resolve()))


def scenario(name: str, directory: str = "build-scenarios") -> dict[str, Any]:
    """A fresh copy of the committed scenario evals/<directory>/<name>.yaml."""
    return scenario_file(EVALS / directory / f"{name}.yaml")


def all_scenarios(directory: Path | None = None) -> list[dict[str, Any]]:
    """Fresh copies of every scenario the runner owns, or of those in `directory`."""
    # The key names the directories the runner would read now, so a test that patched them is
    # never served another directory's scenarios.
    key = (directory,) if directory is not None else (catalog.SCENARIO_DIR, catalog.CONTRACT_SCENARIO_DIR)
    return copy.deepcopy(_parsed_scenarios(key))


def write_tree(root: Path, files: Mapping[str, str], *, newline: str | None = None) -> Path:
    """Write each relative path's text under `root`, creating its folders, and return `root`.

    `newline` is Path.write_text's: the default writes the platform's line ending for each "\\n",
    as a checkout of the fixture would; "\\n" or "" keeps the text's own endings.
    """
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline=newline)
    return root


def run_python(
    args: Sequence[str],
    *,
    cwd: Path | str | None = None,
    isolated: bool = False,
    timeout: float = 120,
    **options: Any,
) -> subprocess.CompletedProcess[Any]:
    """Run this interpreter on `args`, capturing its output as text unless the caller says otherwise.

    `isolated` adds -I, which also implies -P: the script's own folder is then not on sys.path, so an
    oracle that imports a module beside it must run without it. Every run is bounded: a hung child
    fails its test with TimeoutExpired instead of holding the job until CI's limit.
    """
    options.setdefault("capture_output", True)
    options.setdefault("text", True)
    command = [sys.executable, *(["-I"] if isolated else []), *args]
    return subprocess.run(command, cwd=cwd, timeout=timeout, **options)


def load_oracle(path: Path) -> ModuleType:
    """Execute an oracle script as a new module, as its check would run it, for in-process calls.

    Every call executes the file afresh: some oracles keep module state (incident-writes' GATE,
    pager-webhook's _PROCS), so a shared module would carry one test's state into another. The module
    is registered in sys.modules only while it executes, which is what a dataclass defined there needs.
    """
    name = "oracle_" + re.sub(r"\W", "_", f"{path.parent.name}_{path.stem}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path} as a module")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
    return module


def materialize_reference(
    workspace: Path, scenario_path: Path, template: str, markers: Mapping[str, str], oracle: Path
) -> Path:
    """Seed a backend scenario's fixture, write its reference app/main.py with each marker in
    `template` replaced in order, and stage the oracle as probe_checks.py beside it."""
    write_tree(workspace, scenario_file(scenario_path)["fixture"]["files"])
    code = template
    for marker, value in markers.items():
        code = code.replace(marker, value)
    (workspace / "app/main.py").write_text(code, encoding="utf-8")
    (workspace / "probe_checks.py").write_text(oracle.read_text(encoding="utf-8"), encoding="utf-8")
    return workspace


def run_oracle_check(
    workspace: Path, check: str, *, timeout: float, env: Mapping[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run one check of the oracle materialize_reference staged in `workspace`."""
    return run_python(["-B", "probe_checks.py", check], cwd=workspace, env=env, timeout=timeout)


def run_fixture_suite(scenario_path: Path, workspace: Path) -> subprocess.CompletedProcess[str]:
    """Seed the scenario's fixture alone and run its own pytest suite, as the agent receives it."""
    write_tree(workspace, scenario_file(scenario_path)["fixture"]["files"])
    return run_python(["-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=workspace)


class TempRootTestCase(unittest.TestCase):
    """A test case whose every test gets a fresh temporary directory, `self.root`."""

    TEMP_PREFIX = "build-probe-test-"

    def setUp(self) -> None:
        super().setUp()
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix=self.TEMP_PREFIX)))


def context(
    spec: dict[str, Any],
    trace: tracing.TraceSummary | None = None,
    *,
    ws: workspaces.Workspace | None = None,
    git: workspaces.GitFacts | None = None,
    **fields: Any,
) -> checking.Context:
    """A complete check context for a test that reads only part of it: unless the test supplies its
    own, a workspace that does not exist and a repository with no commits and no changes."""
    gone = Path(tempfile.gettempdir()) / "no-such-probe-workspace"
    ws = ws or workspaces.Workspace(gone, gone / "repo", gone / "bin", gone / "state", 0, "main")
    git = git or workspaces.GitFacts(0, "main", [], "")
    return checking.Context(spec, ws, trace or tracing.TraceSummary(), git, **fields)


def ws_context(
    spec: dict[str, Any],
    ws: workspaces.Workspace,
    *,
    text: str = "",
    skills: tuple[str, ...] | list[str] = (),
    skills_failed: tuple[str, ...] | list[str] = (),
    bash: tuple[str, ...] | list[str] = (),
    dispatches: tuple[str, ...] | list[str] = (),
) -> checking.Context:
    """A check context over a seeded workspace, its git facts as they are now, and a trace that
    holds only the given reply, skill loads, shell commands and dispatches."""
    trace = tracing.TraceSummary(
        result_text=text,
        skills=list(skills),
        skills_failed=list(skills_failed),
        bash_commands=list(bash),
        dispatches=list(dispatches),
    )
    return checking.Context(spec, ws, trace, workspaces.collect_git_facts(ws))


def trace_measures(spec: dict[str, Any], trace: tracing.TraceSummary) -> list[tuple[str, Any]]:
    """A grade's trace-read expectations as `plan` builds them for a live grade, by their text."""
    return [(e.text, e.measure) for e in assessment.plan(spec, trace, None, ROOT) if e.check is None]


def parse_events(events: list[dict[str, Any]]) -> tracing.TraceSummary:
    """The trace summary the runner parses from these stream-json events."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
        return tracing.parse_trace(path)


def skill_events(*, is_error: bool) -> list[dict[str, Any]]:
    """One Skill call for backend-craft, its tool result (an `Unknown skill` error or a clean load),
    and the result event."""
    return [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "tu_skill", "name": "Skill",
             "input": {"skill": "save-toolkit:backend-craft"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "tu_skill", "is_error": is_error,
             "content": "<tool_use_error>Unknown skill: save-toolkit:backend-craft</tool_use_error>"
                        if is_error else "backend-craft loaded"}]}},
        {"type": "result", "result": "done", "duration_ms": 10, "usage": {}},
    ]  # fmt: skip


def native_dispatch_events(
    *, asynchronous: bool = True, completed: bool = True, continued: bool = True
) -> list[dict[str, Any]]:
    """A parent's Agent dispatch of sre-assistant, synchronous or backgrounded, with or without the
    runtime's completion notice and the parent text that follows it."""
    events: list[dict[str, Any]] = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "child",
            "name": "Agent", "input": {"subagent_type": "save-toolkit:sre-assistant"}}]}},
    ]  # fmt: skip
    if asynchronous:
        events.append({"type": "system", "subtype": "task_started", "tool_use_id": "child",
                       "task_id": "task", "is_backgrounded": True})  # fmt: skip
    events += [
        {"type": "user", "tool_use_result": {"isAsync": asynchronous}, "message": {"content": [
            {"type": "tool_result", "tool_use_id": "child", "content": "submitted" if asynchronous else "answer"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Before the child returns."}]}},
    ]  # fmt: skip
    if asynchronous and completed:
        events.append({"type": "system", "subtype": "task_notification", "tool_use_id": "child",
                       "task_id": "task", "status": "completed"})  # fmt: skip
    if continued:
        events.append({"type": "assistant", "message": {"content": [{"type": "text", "text": "Parent continues."}]}})
    return events


def saved_grade(
    spec: dict[str, Any],
    expectations: list[dict[str, Any]],
    *,
    binding: dict[str, Any] | None = None,
    response: str = "",
) -> dict[str, Any]:
    """Build identified saved records for synthetic traces; each label here is unique."""
    identity = fingerprints.scenario_digest(spec, binding)
    labels = assessment.scenario_assertions(spec)
    return {
        "scenario_sha256": identity,
        "judge_binding": binding,
        "response_sha256": judge._digest(response),
        "expectations": [{**e, "id": f"{identity}:{labels.index(e['text'])}"} for e in expectations],
        "summary": {},
    }


def saved_summary(**changes: Any) -> dict[str, Any]:
    """The trace summary a saved build run holds when nothing happened: no state files, commits,
    changes, skills, dispatches or commands. Changed keys keep their place; new ones follow."""
    return {
        "state_files": {}, "commits_before_after": [1, 1], "branch": "main", "changed_files": [],
        "skills": [], "dispatches": [], "bash_commands": [], "agents_dir": False, "inconclusive": None,
        **changes,
    }  # fmt: skip


def write_saved_run(
    run: Path,
    *,
    response: str,
    summary: dict[str, Any],
    grading: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
) -> Path:
    """Lay out a saved trial as the runner publishes one: the reply and the trace summary under
    outputs/, and beside them the live grade and the raw trace when the test supplies them."""
    (run / "outputs").mkdir(parents=True)
    (run / "outputs" / "response.md").write_text(response, encoding="utf-8")
    (run / "outputs" / "trace-summary.json").write_text(json.dumps(summary), encoding="utf-8")
    if grading is not None:
        (run / "grading.json").write_text(json.dumps(grading), encoding="utf-8")
    if events is not None:
        (run / "stdout.jsonl").write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    return run


def latest_assessment(run: Path, name: str = "grading.json") -> dict[str, Any]:
    """The newest assessment a regrade wrote beside the run (threat-model ADR result rule 8)."""
    revisions = sorted(int(p.name) for p in (run / "assessments").iterdir() if p.name.isdigit())
    loaded: dict[str, Any] = json.loads((run / "assessments" / str(revisions[-1]) / name).read_text(encoding="utf-8"))
    return loaded


def judge_process(*, returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    """What the judge's spawned CLI returned."""
    return subprocess.CompletedProcess(args=["claude"], returncode=returncode, stdout=stdout, stderr=stderr)


def judge_envelope(result: str, *, is_error: bool = False, model: str = "claude-sonnet-5", cost: float = 0.01) -> str:
    """The CLI's JSON envelope around a judge reply."""
    return json.dumps({"result": result, "is_error": is_error, "modelUsage": {model: {}}, "total_cost_usd": cost})


def judge_verdict(verdict: str, reason: str = "because", evidence: list[str] | None = None) -> str:
    """A judge reply. The default quote is grounded in the "some response" text these tests judge: an
    evidence item that is not verbatim in the response is inconclusive by contract, not a verdict."""
    return json.dumps({"verdict": verdict, "reason": reason, "evidence": evidence or ["some response"]})


def calibration_receipt(root: Path) -> Path:
    """A complete canonical calibration under `root` using mocked judgments, never a model call."""
    cases = iter(judge._load_calibration(judge.DEFAULT_CALIBRATION_PATH))

    def verdict(response: str, name: str, params: dict[str, Any], **kwargs: Any) -> tuple[bool, str]:
        case = next(cases)
        judge._SPEND.append({"cached": False, "cost_usd": 0.01, "seconds": 0.0, "model_resolved": "claude-sonnet-5"})
        return case["expect"] == "pass", json.dumps(
            {"model_resolved": "claude-sonnet-5", "reason": "mocked", "evidence": []}
        )

    with (
        mock.patch.object(judge, "REPO_ROOT", root),
        mock.patch.object(judge, "judge", side_effect=verdict),
        contextlib.redirect_stdout(io.StringIO()),
    ):
        assert judge.calibrate(judge.DEFAULT_CALIBRATION_PATH, "sonnet") == 0
    return next((root / ".eval-runs/judge-calibration").glob("2*/identity.json"))


def judge_binding_metadata() -> dict[str, Any]:
    """The metadata of a judge binding over a fresh mocked calibration of the real corpus."""
    with tempfile.TemporaryDirectory() as tmp:
        metadata: dict[str, Any] = judge.load_binding(
            calibration_receipt(Path(tmp)), {"no_production_action_claim"}
        ).metadata
        return metadata
