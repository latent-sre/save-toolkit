"""Golden saved runs: one stub-driven attempt per result rule and ending, kept as fixtures.

Stage 0 of docs/decisions/2026-11-02-probe-runner-refactor.md. Each case runs the real runner
against a stub `claude` that emits canned stream-json, with the seams a test would patch, and keeps
what the runner published under evals/fixtures/runner-goldens/<case>/run-1 beside the verdict view
the live grade produced and the view a regrade of that same directory produces. Later stages must
reproduce both views byte for byte, timing, paths and identities aside.

    python evals/golden_runs.py write    # regenerate every fixture from the current runner
    python evals/golden_runs.py check    # regrade each fixture and rerun each stub trial; report drift

A regenerated fixture is a claim that the runner's verdicts changed on purpose; its pull request
explains every changed view, as CONTRIBUTING requires of runner edits.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import shutil
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any
from unittest import mock

import judge
from probe import backing, cli, constants, fingerprints, invocation, layout, rescoring, trials, workspaces
from probe_testkit import (
    STUB_RUNTIME,
    calibration_receipt,
    judge_envelope,
    judge_process,
    judge_verdict,
    native_conversation_spec,
    native_launch,
    plain_env_factory,
    stub_cli,
    stub_spec,
    tiny_spec,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "evals" / "fixtures" / "runner-goldens"
LABEL = "golden"
WORKSPACE = "/golden/workspace"  # every trial-time temporary path, in the committed artifacts
CHECKOUT = "/golden/checkout"  # this repository's path, where an artifact recorded it

# A stub that announces itself and then outlives the batch's wall-clock timeout.
SLEEPING_STUB = """
import json, os, sys, time
argv = sys.argv
root = argv[argv.index("--plugin-dir") + 1] if "--plugin-dir" in argv else ""
print(json.dumps({"type": "system", "subtype": "init", "cwd": os.getcwd(), "tools": TOOLS,
                  "plugins": [{"name": "save-toolkit", "path": root}], "mcp_servers": [], "permissionMode": "dontAsk"}))
# One main-thread turn resolves the model identity, so the timeout is a cut, not an identity void.
print(json.dumps({"type": "assistant", "message": {"model": "stub-model", "content": [
    {"type": "text", "text": "Looking at the tests."}]}}))
sys.stdout.flush()
time.sleep(30)
"""

Seams = Callable[[Path], contextlib.AbstractContextManager[Any]]

# The judge binding records the CLI it would run; a placeholder keeps the host's path out of it.
JUDGE_CLI = "/golden/claude"


@dataclasses.dataclass(frozen=True)
class Case:
    """One golden: the scenario, how the stub CLI behaves, and the seams the trial runs under."""

    name: str
    rules: tuple[int, ...]  # threat-model result rules the case exercises
    about: str
    spec: Callable[[], dict[str, Any]]
    stub: Mapping[str, Any] = dataclasses.field(default_factory=dict)
    timeout: int = 60
    expected_plugin_digest: str | None = None
    sleeping: bool = False
    seams: Seams | None = None
    judged: bool = False  # binds a mocked calibration receipt and a scripted PASS judgment
    native: Mapping[str, Any] | None = None  # a native conversation: flags for the in-process launcher
    model: str | None = None  # the model the batch declares; a native conversation must declare one
    raises: bool = False  # the attempt is expected to raise before grading (an incomplete attempt)


def _forbids_and_requires() -> dict[str, Any]:
    return tiny_spec(
        checks=[
            {"check": "bash_did_not_run", "pattern": "unittest", "text": "forbidden command never ran"},
            {"check": "text_contains_any", "of": ["refuse"], "text": "refuses"},
        ]
    )


def _requires_deploy(**changes: Any) -> dict[str, Any]:
    return tiny_spec(checks=[{"check": "text_contains_any", "of": ["deploy"], "text": "says deploy"}], **changes)


@contextlib.contextmanager
def _service_unavailable(_: Path) -> Iterator[None]:
    with mock.patch.object(backing, "start_services", side_effect=backing.ServiceUnavailable("db")):
        yield


def _cleanup_raises(services: list[Any], _docker: str) -> None:
    # The real stop_services is a no-op for an empty list; only a live service fails to stop.
    if services:
        raise backing.ServiceUnavailable("cleanup")


@contextlib.contextmanager
def _cleanup_fails(_: Path) -> Iterator[None]:
    service = backing.Service("grafana", "image@sha256:" + "0" * 64, "cid", "http://127.0.0.1:32123")
    with (
        mock.patch.object(backing, "start_services", return_value=[service]),
        mock.patch.object(backing, "stop_proxies"),
        mock.patch.object(backing, "stop_services", side_effect=_cleanup_raises),
    ):
        yield


@contextlib.contextmanager
def _fixture_unavailable(_: Path) -> Iterator[None]:
    with mock.patch.object(workspaces, "seed_workspace", side_effect=RuntimeError("fixture unavailable")):
        yield


@contextlib.contextmanager
def _scripted_pass_judgment(_: Path) -> Iterator[None]:
    judge.drain_spend()
    verdict = judge_process(stdout=judge_envelope(judge_verdict("PASS")))
    with mock.patch.object(judge, "_run_judge_process", return_value=verdict):
        yield


CASES: tuple[Case, ...] = (
    Case("pass", (3,), "every check passes on a completed run", stub_spec),
    Case("fail_forbidding", (2, 3), "a forbidding check sees the forbidden command", _forbids_and_requires),
    Case("fail_requires", (2, 3), "a requiring check is unmet on a completed run", _requires_deploy),
    Case(
        "cut_forbidden_fails",
        (2,),
        "an error result cuts the run short; the forbidden command still counts",
        _forbids_and_requires,
        stub={"is_error": True, "subtype": "error_during_execution", "result": "stopped"},
    ),
    Case(
        "cut_requires_inconclusive",
        (2, 3),
        "an error result cuts the run short; a requirement is not established",
        lambda: tiny_spec(checks=[{"check": "text_contains_any", "of": ["refuse"], "text": "refuses"}]),
        stub={"is_error": True, "subtype": "error_during_execution", "result": "stopped"},
    ),
    Case("nonzero_exit", (2,), "the CLI exits nonzero after its result", stub_spec, stub={"exit_code": 2}),
    Case(
        "turn_limit",
        (4,),
        "the CLI ends the session at the declared turn limit; unmet requirements fail",
        lambda: _requires_deploy(max_turns=2),
        stub={"subtype": "error_max_turns"},
    ),
    Case(
        "void_identity",
        (1,),
        "the plugin digest the batch expects is not the one served",
        stub_spec,
        expected_plugin_digest="f" * 64,
    ),
    Case("wall_clock", (2, 4), "the CLI outlives the wall-clock timeout", stub_spec, timeout=2, sleeping=True),
    Case(
        "machinery_failure",
        (5,),
        "a check's own code fails: a grader error, never a verdict",
        lambda: tiny_spec(checks=[{"check": "text_regex", "pattern": "(", "text": "an unbalanced pattern"}]),
    ),
    Case(
        "service_unavailable",
        (5,),
        "a backing service never starts, so the model is never called",
        stub_spec,
        seams=_service_unavailable,
    ),
    Case(
        "after_assessment",
        (6,),
        "service cleanup fails after grading; the verdict stands and the problem is recorded",
        stub_spec,
        seams=_cleanup_fails,
    ),
    Case(
        "rubric_kept",
        (3, 8),
        "a rubric verdict the live batch paid for is kept by a regrade",
        lambda: tiny_spec(
            checks=[{"check": "fleet_grader", "name": "rubric", "rubric_name": "no_production_action_claim"}]
        ),
        stub={"result": "some response"},
        seams=_scripted_pass_judgment,
        judged=True,
    ),
    Case(
        "native_pass",
        (3,),
        "a native conversation: the initial call fires the skill and dispatches the helper, the resumed "
        "call answers the follow-up, and every check passes",
        native_conversation_spec,
        native={},
        model="stub-model",
    ),
    Case(
        "native_wrong_session",
        (1,),
        "the resumed call reports a different session, so the conversation is not the one declared",
        native_conversation_spec,
        native={"wrong_session": True},
        model="stub-model",
    ),
    Case(
        "native_incomplete_followup",
        (2,),
        "the resumed call ends without a result event, so the follow-up is cut short",
        native_conversation_spec,
        native={"incomplete_followup": True},
        model="stub-model",
    ),
    Case(
        "incomplete",
        (7,),
        "the attempt raises before grading and is kept without a verdict",
        stub_spec,
        seams=_fixture_unavailable,
        raises=True,
    ),
)


def case(name: str) -> Case:
    return next(c for c in CASES if c.name == name)


def verdict_view(grading: Mapping[str, Any]) -> dict[str, Any]:
    """What a grade decided, without timing, paths or identities: the part later stages must reproduce."""
    return {
        "status": grading["status"],
        "inconclusive": grading.get("inconclusive"),
        "unmeasured": grading.get("unmeasured"),
        "void": grading.get("void"),
        "run_end": grading.get("run_end"),
        "run_stop": grading.get("run_stop"),
        "grader_error": grading.get("grader_error"),
        "after_assessment": grading.get("after_assessment"),
        "expectations": [
            {"text": e["text"], "kind": e["kind"], "state": e["state"]} for e in grading.get("expectations", [])
        ],
        "summary": {key: grading.get("summary", {}).get(key) for key in ("passed", "failed", "total")},
    }


def _stub_command(root: Path, item: Case) -> str:
    if item.native is not None:
        return "native-stub"  # never launched: the in-process launcher answers `run_cli`
    if not item.sleeping:
        return stub_cli(root, **item.stub)
    stub = root / "sleeping_claude.py"
    stub.write_text(SLEEPING_STUB.replace("TOOLS", repr(list(constants.BUILD_TOOLS))), encoding="utf-8")
    return f'"{sys.executable}" "{stub}"'


def run_live(item: Case, root: Path) -> tuple[Path, dict[str, Any] | None, str | None, dict[str, Any] | None]:
    """Run the case's trial under `root`; return its run directory, the grade, what raised, and the
    result row the batch reads."""
    spec = item.spec()
    out = root / "iteration"
    with mock.patch.object(judge, "claude_executable", return_value=JUDGE_CLI):
        return _run_live(item, spec, root, out)


def _run_live(
    item: Case, spec: dict[str, Any], root: Path, out: Path
) -> tuple[Path, dict[str, Any] | None, str | None, dict[str, Any] | None]:
    settings = trials.BatchSettings(
        plugin_root=ROOT, label=LABEL, model=item.model, out_dir=out, timeout=item.timeout,
        executable=_stub_command(root, item), keep_workspace=False, env_factory=plain_env_factory(),
        runtime=STUB_RUNTIME, expected_plugin_digest=item.expected_plugin_digest,
        judge_binding=(
            judge.load_binding(calibration_receipt(root / "judge"), {"no_production_action_claim"}) if item.judged else None
        ),
    )  # fmt: skip
    raised: str | None = None
    summary: dict[str, Any] | None = None
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(fingerprints, "runtime_identity", return_value=STUB_RUNTIME))
        if item.seams is not None:
            stack.enter_context(item.seams(root))
        if item.native is not None:
            launch = native_launch(spec, [], **item.native)
            stack.enter_context(mock.patch.object(invocation, "run_cli", side_effect=launch))
        try:
            summary = trials.run_trial(spec, run_number=1, settings=settings)
        except Exception as exc:  # an incomplete attempt is the case under test
            if not item.raises:
                raise
            raised = f"{type(exc).__name__}: {exc}"
    run_dir = layout.run_dir(out, spec["id"], LABEL, 1)
    if raised is not None and not run_dir.exists():
        # An attempt that raised was never renamed into run-1; the runner keeps it under attempts/.
        kept = [path for path, _slot, _attempt in layout.kept_attempts(run_dir.parent)]
        run_dir = kept[-1] if kept else run_dir
    grading = (
        json.loads((run_dir / "grading.json").read_text(encoding="utf-8"))
        if (run_dir / "grading.json").is_file()
        else None
    )
    return run_dir, grading, raised, summary


def batch_view(summary: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """What the batch reads from a finished trial's result row: why the batch stops after it (an
    identity failure or an uncleaned environment), why the scenario's further trials stop (a grading
    machinery failure), and whether its cost is known (result rules 5 to 7). None for an attempt
    that raised, which has no result row."""
    if summary is None:
        return None
    return {
        "batch_stop": cli._stop_after(dict(summary), None),
        "scenario_stop": summary.get("grader_error") or summary.get("service_error") or None,
        "cost_known": summary.get("cost_complete"),
    }


def live_view(grading: Mapping[str, Any] | None, raised: str | None, run_dir: Path) -> dict[str, Any]:
    if grading is not None:
        return verdict_view(grading)
    # An attempt that raised has no grade: its state is in attempt.json and how it ended in the record.
    attempt = (
        json.loads((run_dir / "attempt.json").read_text(encoding="utf-8"))
        if (run_dir / "attempt.json").is_file()
        else {}
    )
    record = (
        json.loads((run_dir / "record.json").read_text(encoding="utf-8")) if (run_dir / "record.json").is_file() else {}
    )
    return {
        "raised": raised,
        "attempt_state": attempt.get("state"),
        "run_end": (record.get("run_end") or {}).get("kind"),
        "status": None,
    }


def regrade_view(run_dir: Path, spec: Mapping[str, Any], *, other_judge: bool = False) -> dict[str, Any] | None:
    """The view a regrade of `run_dir` produces; None when the directory holds no live grade.

    A judged run is regraded under the judge its binding recorded, since the live judge's identity
    (its Python, PyYAML and CLI path) is the host's; `other_judge` regrades it under a judge whose
    source differs instead, which is what any other host sees.
    """
    if not (run_dir / "grading.json").is_file():
        return None
    binding = json.loads((run_dir / "grading.json").read_text(encoding="utf-8")).get("judge_binding")
    execution = dict(binding["execution"]) if binding else None
    if execution is not None and other_judge:
        execution["source_sha256"] = "0" * 64
    with tempfile.TemporaryDirectory(prefix="golden-regrade-") as tmp, contextlib.ExitStack() as stack:
        # The regrade restages the served plugin image at the path the run recorded, so the copy
        # gets this host's paths back; the committed fixture is never touched.
        copy = Path(tmp) / "run-1"
        shutil.copytree(run_dir, copy)
        denormalize(copy, Path(tmp))
        if execution is not None:
            stack.enter_context(mock.patch.object(judge, "execution_identity", return_value=execution))
        return verdict_view(rescoring.regrade_run(copy, dict(spec), write=False, relax_identity=True))


def normalize(run_dir: Path, root: Path) -> None:
    """Replace trial-time paths with placeholders so the committed bytes do not name this host."""
    cleanup = run_dir / "cleanup.json"
    trial_workspace = json.loads(cleanup.read_text(encoding="utf-8")).get("workspace") if cleanup.is_file() else None
    temporary = {root, root.resolve()} | (
        {Path(trial_workspace), Path(trial_workspace).resolve()} if trial_workspace else set()
    )
    replacements = sorted(((str(p), WORKSPACE) for p in temporary), key=lambda pair: -len(pair[0])) + [
        (str(p), CHECKOUT) for p in {ROOT, ROOT.resolve()}
    ]
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for old, new in replacements:
            text = text.replace(old, new).replace(json.dumps(old)[1:-1], new)
        path.write_text(text, encoding="utf-8")
    summary_path = run_dir / "outputs" / "trace-summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if isinstance(summary.get("plugin"), dict):
            # A regrade measures against this checkout wherever it runs; the generating host's root
            # would be unreadable everywhere else and read as a missing plugin root. The served image
            # path stays, as a placeholder: a regrade restages the image there from this checkout.
            summary["plugin"]["plugin_root"] = None
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def denormalize(run_dir: Path, root: Path) -> None:
    """Give a copy of a fixture this host's paths back: the workspace placeholder becomes a directory
    under `root` and the checkout placeholder this checkout, so a regrade can restage and read them."""
    replacements = [(WORKSPACE, str(root / "workspace")), (CHECKOUT, str(ROOT))]
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for old, new in replacements:
            text = text.replace(old, json.dumps(new)[1:-1] if path.suffix in {".json", ".jsonl"} else new)
        path.write_text(text, encoding="utf-8")


def write(item: Case, fixtures: Path = FIXTURES, *, artifacts: bool = True) -> dict[str, Any]:
    """Generate one case's fixture: the normalized run directory, its scenario, and the views.
    `artifacts=False` keeps the committed run directory and rewrites only the views from a fresh
    trial, for a change to the views alone."""
    target = fixtures / item.name
    with tempfile.TemporaryDirectory(prefix=f"golden-{item.name}-") as tmp:
        root = Path(tmp)
        run_dir, grading, raised, summary = run_live(item, root)
        live = live_view(grading, raised, run_dir)
        batch = batch_view(summary)
        if artifacts:
            normalize(run_dir, root)
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(run_dir, target / "run-1")
    spec = item.spec()
    (target / "scenario.json").write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    expected = {
        "about": item.about,
        "rules": list(item.rules),
        "live": live,
        "batch": batch,
        "regrade": regrade_view(target / "run-1", spec),
    }
    if item.judged:
        expected["regrade_other_judge"] = regrade_view(target / "run-1", spec, other_judge=True)
    (target / "expected.json").write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return expected


def expected(item: Case, fixtures: Path = FIXTURES) -> dict[str, Any]:
    return json.loads((fixtures / item.name / "expected.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def scenario(item: Case, fixtures: Path = FIXTURES) -> dict[str, Any]:
    return json.loads((fixtures / item.name / "scenario.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def check(fixtures: Path = FIXTURES) -> list[str]:
    """Every view that differs from its fixture: regrade of the committed run, and a fresh live trial."""
    drift: list[str] = []
    for item in CASES:
        want = expected(item, fixtures)
        with tempfile.TemporaryDirectory(prefix=f"golden-check-{item.name}-") as tmp:
            copy = Path(tmp) / "run-1"
            shutil.copytree(fixtures / item.name / "run-1", copy)
            if (got := regrade_view(copy, scenario(item, fixtures))) != want["regrade"]:
                drift.append(f"{item.name}: regrade view differs: {got} != {want['regrade']}")
            if (
                item.judged
                and (got := regrade_view(copy, scenario(item, fixtures), other_judge=True))
                != want["regrade_other_judge"]
            ):
                drift.append(f"{item.name}: other-judge regrade view differs: {got} != {want['regrade_other_judge']}")
            run_dir, grading, raised, summary = run_live(item, Path(tmp))
            if (got := live_view(grading, raised, run_dir)) != want["live"]:
                drift.append(f"{item.name}: live view differs: {got} != {want['live']}")
            if (got := batch_view(summary)) != want["batch"]:
                drift.append(f"{item.name}: batch view differs: {got} != {want['batch']}")
    return drift


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["write"]:
        for item in CASES:
            view = write(item)
            print(f"{item.name}: live {view['live'].get('status')}, regrade {(view['regrade'] or {}).get('status')}")
        return 0
    if args == ["check"]:
        drift = check()
        print("\n".join(drift) if drift else f"{len(CASES)} goldens unchanged")
        return 1 if drift else 0
    print("usage: golden_runs.py write | check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
