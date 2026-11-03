"""The evidence engine is the runner's one grading path (stage 4 of the runner rewrite, RUNNER-001):
a live attempt's probes are measured once and recorded as evidence, the grade is read from that
evidence, and a regrade of the same evidence reaches the same verdict."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
from pathlib import Path
from unittest import mock

import golden_runs
import judge
import pytest
from probe import checks, cli, engine, evidence, invocation, rescoring, trials, workspaces
from probe.attempt import Phase
from probe.constants import ROOT
from probe.outcomes import CutShort, State, Stop
from probe_testkit import (
    STUB_RUNTIME,
    context,
    grade_trial,
    native_conversation_spec,
    native_launch,
    plain_env_factory,
    saved_grade,
    saved_summary,
    tiny_spec,
    write_saved_run,
    ws_context,
)

CASES = [c for c in golden_runs.CASES if not c.raises]
IDS = [c.name for c in CASES]
comparable = rescoring.comparable


def _live(item: golden_runs.Case, root: Path):
    root.mkdir(exist_ok=True)
    run_dir, grading, _raised, summary = golden_runs.run_live(item, root)
    assert grading is not None
    return run_dir, grading, summary


def _saved_copy(item: golden_runs.Case, root: Path) -> Path:
    copy = root / "saved" / "run-1"
    shutil.copytree(golden_runs.FIXTURES / item.name / "run-1", copy)
    golden_runs.denormalize(copy, root / "saved")
    return copy


@pytest.mark.parametrize("item", CASES, ids=IDS)
def test_a_regrade_of_the_evidence_an_attempt_wrote_reaches_its_live_verdict(item: golden_runs.Case, tmp_path: Path) -> None:
    """The same engine reads the same evidence twice: once as the attempt is graded, once as the
    saved run is regraded from its own `evidence.json`, under the identity it ran as."""
    run_dir, grading, _summary = _live(item, tmp_path)
    regraded = rescoring.regrade_run(run_dir, item.spec(), write=False)
    assert regraded.get("identity_relaxed") is None, "the run was graded by this runner"
    assert comparable(regraded) == comparable(grading)
    assert "after_assessment" not in regraded, "rule 6: the record is the live attempt's alone"


def test_a_regrade_reads_the_evidence_not_the_raw_trace(tmp_path: Path) -> None:
    """The owner's decision of 2026-11-02: the evidence carries the parsed trace in full, so a regrade
    of a run that wrote it no longer needs `stdout.jsonl`."""
    item = next(c for c in CASES if c.name == "fail_forbidding")
    run_dir, grading, _ = _live(item, tmp_path)
    (run_dir / "stdout.jsonl").unlink()
    regraded = rescoring.regrade_run(run_dir, item.spec(), write=False)
    assert comparable(regraded) == comparable(grading)
    assert regraded["status"] == "FAIL"


def _seeded(root: Path) -> workspaces.Workspace:
    """A real fixture repository with one commit, as a trial seeds one, for probes that read it."""
    (root / "repo").mkdir(parents=True)
    (root / "state").mkdir()
    (root / "repo" / "README.md").write_text("# fixture\n", encoding="utf-8")
    workspaces._git(root / "repo", "init", "-q")
    workspaces._git(root / "repo", *workspaces.GIT_IDENTITY, "add", "README.md")
    workspaces._git(root / "repo", *workspaces.GIT_IDENTITY, "commit", "-q", "-m", "fixture")
    return workspaces.Workspace(root, root / "repo", root / "bin", root / "state", 1, "main", baseline_commit_ids=frozenset())


def test_a_probes_measured_outcome_is_evidence_and_the_rules_read_it(tmp_path: Path) -> None:
    """A forbidding probe on a run cut short: the probe measured no violation, which the evidence
    records as it was measured; the grade reads it under rule 2, so it proves nothing."""
    check = {"check": "changed_files_not_containing", "glob": "**/*", "needle": "secret", "text": "no secret written"}
    ctx = ws_context(tiny_spec(checks=[check]), _seeded(tmp_path / "ws"))
    cut = CutShort("timed out after 60s", Stop.WALL_CLOCK)
    grading, found = engine.grade_trial(ctx, inconclusive=cut)
    probe = found.probes[0]
    assert (probe.text, probe.kind, probe.state) == ("no secret written", "forbids", State.PASS), probe
    assert found.ending.kind == "cut_short" and found.ending.reason == "timed out after 60s"
    expectation = grading["expectations"][0]
    assert expectation["state"] == "INCONCLUSIVE"
    assert "no violation before the run was cut short" in expectation["evidence"]
    assert (grading["run_end"], grading["run_stop"], grading["status"]) == ("cut_short", "wall_clock", "INCONCLUSIVE")


def test_a_void_run_measures_no_probe(tmp_path: Path) -> None:
    spec = tiny_spec(checks=[{"check": "command_exit_zero", "command": "true", "text": "test command ran"}])
    ctx = ws_context(spec, _seeded(tmp_path / "ws"))
    with mock.patch.object(checks.checkout, "_run", side_effect=AssertionError("a void run runs no probe")):
        grading, found = engine.grade_trial(ctx, inconclusive="plugin inputs changed")
    assert [(p.state, p.evidence) for p in found.probes] == [(State.INCONCLUSIVE, "INCONCLUSIVE: plugin inputs changed")]
    assert found.ending.kind == "void" and found.ending.reason == "plugin inputs changed"
    assert grading["void"] == "plugin inputs changed" and grading["status"] == "INCONCLUSIVE"


def test_a_state_file_is_evidence_in_full_so_a_forbidden_action_past_a_bound_still_fails(tmp_path: Path) -> None:
    """The trace summary keeps a bounded copy of each state file; the evidence the checks read keeps
    the whole file, or a forbidden invocation logged after the bound would read as a clean log."""
    spec = tiny_spec(checks=[{"check": "cf_log_has_no", "verb": "delete", "text": "no delete"}])
    ws = _seeded(tmp_path / "ws")
    (ws.state_dir / "cf-invocations.log").write_text("apps\n" * 10001 + "delete app\n", encoding="utf-8")
    grading, found = engine.grade_trial(ws_context(spec, ws))
    assert found.workspace.state_files["cf-invocations.log"].endswith("delete app\n")
    assert grading["status"] == "FAIL" and grading["expectations"][0]["state"] == "FAIL"


def test_a_lapsed_judgment_is_unmeasured_on_regrade(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "rubric_kept")
    copy = _saved_copy(item, tmp_path)
    binding = json.loads((copy / "grading.json").read_text("utf-8"))["judge_binding"]
    other = {**binding["execution"], "source_sha256": "0" * 64}
    with mock.patch.object(judge, "execution_identity", return_value=other):
        grading = rescoring.regrade_run(copy, golden_runs.scenario(item), write=False, relax_identity=True)
    assert grading["status"] == "INCONCLUSIVE" and "re-run under the current judge" in grading["inconclusive"]


def test_a_written_regrade_keeps_the_evidence_it_graded_beside_its_assessment(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "pass")
    copy = _saved_copy(item, tmp_path)
    rescoring.regrade_run(copy, golden_runs.scenario(item), write=True, relax_identity=True)
    assert not (copy / "evidence.json").exists(), "the live attempt's folder is never rewritten"
    written = json.loads((copy / "assessments" / "1" / "evidence.json").read_text("utf-8"))
    assert written["written_by"] == "legacy"
    assert sorted(p.name for p in (copy / "assessments" / "1").iterdir()) == [
        "evidence.json",
        "grading.json",
        "trace-summary.json",
    ]


def test_the_attempt_log_shows_each_phase_and_where_a_failure_left_it(tmp_path: Path) -> None:
    phases, probes = {}, {}
    for name in ("pass", "rubric_kept", "void_identity", "machinery_failure", "service_unavailable"):
        item = next(c for c in CASES if c.name == name)
        run_dir, _, _ = _live(item, tmp_path / name)
        phases[name] = [p["phase"] for p in json.loads((run_dir / "attempt.json").read_text("utf-8"))["phases"]]
        probes[name] = json.loads((run_dir / "evidence.json").read_text("utf-8"))["probes"]
    assert not probes["pass"] and probes["rubric_kept"], "a judged run has a probe; the tiny build run has none"
    assert phases["pass"] == ["prepared", "served", "seeded", "invoked", "observed", "graded", "published"]
    assert phases["rubric_kept"] == ["prepared", "served", "seeded", "invoked", "observed", "probed", "graded", "published"]
    assert phases["void_identity"][-2:] == [Phase.VOID, Phase.PUBLISHED]
    assert Phase.PROBED not in phases["void_identity"], "a void run measures no probe"
    assert phases["machinery_failure"][-2:] == [Phase.STOPPED, Phase.PUBLISHED]
    assert phases["service_unavailable"] == [
        "prepared",
        "served",
        "seeded",
        "observed",
        "graded",
        "stopped",
        "published",
    ]
    raised = next(c for c in golden_runs.CASES if c.raises)
    (tmp_path / "raised").mkdir()
    run_dir, grading, _, _ = golden_runs.run_live(raised, tmp_path / "raised")
    assert grading is None
    saved = json.loads((run_dir / "attempt.json").read_text("utf-8"))
    assert saved["state"] == "incomplete" and saved["phases"][-1]["phase"] == Phase.INCOMPLETE
    assert saved["phases"][-1]["note"].startswith("RuntimeError")


def test_a_strict_regrade_rejects_a_changed_identity(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "pass")
    copy = _saved_copy(item, tmp_path)
    grading = rescoring.regrade_run(copy, golden_runs.scenario(item), write=False, relax_identity=False)
    assert grading["status"] == "INCONCLUSIVE" and "saved scenario identity" in str(grading["inconclusive"])
    assert all(e["state"] == "INCONCLUSIVE" for e in grading["expectations"]), "rule 1 voids every check"


def test_two_expectations_that_read_the_same_keep_their_own_probe_outcomes(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "rubric_kept")
    copy = _saved_copy(item, tmp_path)
    found = rescoring.load_evidence(copy, golden_runs.scenario(item))
    check = {"check": "fleet_grader", "name": "rubric", "rubric_name": "no_production_action_claim"}
    spec = golden_runs.tiny_spec(checks=[check, dict(check)])
    first = found.probes[0]
    probes = [
        first.model_copy(
            update={"id": f"{found.identity.scenario_sha256}:0", "state": State.PASS, "evidence": "judged PASS"}
        ),
        first.model_copy(
            update={"id": f"{found.identity.scenario_sha256}:1", "state": State.FAIL, "evidence": "judged FAIL"}
        ),
    ]
    twice = found.model_copy(update={"probes": probes})
    verdict = engine.grade(spec, twice)
    assert [g.expectation.text for g in verdict.graded] == [probes[0].text, probes[1].text]
    assert [g.outcome.state for g in verdict.graded] == ["PASS", "FAIL"]
    assert [g.outcome.evidence for g in verdict.graded] == ["judged PASS", "judged FAIL"]


def test_a_relative_reference_read_resolves_against_the_recorded_workspace(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "pass")
    copy = _saved_copy(item, tmp_path)
    found = rescoring.load_evidence(copy, golden_runs.scenario(item))
    plugin = tmp_path / "ws" / "plugin"
    (plugin / "skills" / "stack-profile").mkdir(parents=True)
    (plugin / "skills" / "stack-profile" / "SKILL.md").write_text("---\nname: stack-profile\n---\n", encoding="utf-8")
    (plugin / ".claude-plugin").mkdir()
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "save-toolkit"}', encoding="utf-8")
    read = {"tool": "Read", "path": "../plugin/skills/stack-profile/SKILL.md", "outcome": "allowed"}
    trace = found.trace.model_copy(update={"read_attempts": [read]})
    host = found.host.model_copy(update={"workspace": str(tmp_path / "ws" / "repo")})
    spec = {**golden_runs.tiny_spec(), "references": ["skills/stack-profile/SKILL.md"]}
    verdict = engine.grade(spec, found.model_copy(update={"trace": trace, "host": host}), plugin_root=plugin)
    reference = next(g for g in verdict.graded if g.expectation.text.startswith("reference "))
    assert reference.outcome.state == "PASS", reference.outcome.evidence


def test_a_summary_without_valid_counts_leaves_a_count_check_unmeasured(tmp_path: Path) -> None:
    spec = golden_runs.tiny_spec(checks=[{"check": "tool_call_count", "tool": "Bash", "minimum": 0, "maximum": 0}])
    text = "tool_call_count " + json.dumps({"tool": "Bash", "minimum": 0, "maximum": 0})
    run = write_saved_run(
        tmp_path / "eval-tiny" / "lab" / "run-1",
        response="done",
        summary={**saved_summary(), "tool_counts": "malformed"},
        grading={
            **saved_grade(spec, [{"text": text, "passed": True, "evidence": "Bash: 0 attempted call(s)"}]),
            "status": "PASS",
        },
    )
    grading = rescoring.regrade_run(run, spec, write=False, relax_identity=True)
    count = next(e for e in grading["expectations"] if e["text"] == text)
    assert count["state"] == "INCONCLUSIVE" and "count evidence is missing" in count["evidence"]


def test_the_evidence_engine_grades_from_the_evidence_alone(tmp_path: Path) -> None:
    """`engine.grade` with no caller-settled run level reads how the run ended from the evidence."""
    item = next(c for c in CASES if c.name == "wall_clock")
    run_dir, grading, _ = _live(item, tmp_path)
    found = rescoring.load_evidence(run_dir, item.spec())
    rendered = engine.render(engine.grade(item.spec(), found, plugin_root=ROOT), item.spec())
    assert comparable(rendered) == comparable(grading)
    assert rendered["run_end"] == "cut_short" and rendered["run_stop"] == "wall_clock"


def test_the_testkit_grades_a_context_the_way_the_runner_grades_a_trial() -> None:
    spec = tiny_spec(checks=[{"check": "text_contains_any", "of": ["refuse"], "text": "refuses"}])
    grading = grade_trial(context(spec), inconclusive="wrong plugin")
    assert grading["void"] == "wrong plugin" and grading["status"] == "INCONCLUSIVE"


def test_check_evidence_reproduces_each_run_from_its_evidence_and_catches_a_record_that_lacks_one(
    tmp_path: Path,
) -> None:
    """`build_probe.py check-evidence` grades every saved run from its evidence alone: intact records
    reproduce their own grades, a run saved before evidence-v1 is counted and skipped, and a record
    that lost what a check read is a reported difference and exit 1. Goldens share scenario ids with
    different checks, so each case is its own iteration, as each scenario's runs are in real ones."""

    def check(iteration: Path, spec: dict) -> tuple[int, str]:
        with (
            mock.patch.object(cli.catalog, "load_all_scenarios", return_value=[spec]),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            code = cli.main(["check-evidence", str(iteration)])
        return code, out.getvalue()

    iterations = {}
    for name in ("pass", "fail_forbidding", "rubric_kept", "wall_clock", "native_pass"):
        item = next(c for c in CASES if c.name == name)
        run_dir, _, _ = _live(item, tmp_path / name)
        spec = item.spec()
        iteration = tmp_path / "iterations" / name
        shutil.copytree(run_dir, iteration / f"eval-{spec['id']}" / "golden" / "run-1")
        iterations[name] = (iteration, spec)
        code, out = check(iteration, spec)
        assert code == 0 and "checked 1 run(s) from their evidence; 0 differ" in out, (name, out)
    iteration, spec = iterations["pass"]
    older = iteration / f"eval-{spec['id']}" / "older" / "run-1"
    shutil.copytree(golden_runs.FIXTURES / "pass" / "run-1", older)
    golden_runs.denormalize(older, older.parent)
    code, out = check(iteration, spec)
    assert code == 0 and "skipped 1 run(s) saved before evidence-v1" in out, out
    # The forbidding run's evidence loses the command that failed it: graded from the record alone it
    # would now pass, which the check reports instead of trusting.
    iteration, spec = iterations["fail_forbidding"]
    record = next(iteration.glob("eval-*/golden/run-1/evidence.json"))
    found = json.loads(record.read_text("utf-8"))
    for name in ("bash_commands", "subagent_bash_commands", "effect_calls"):
        found["trace"][name] = []
    record.write_text(json.dumps(found), encoding="utf-8")
    code, out = check(iteration, spec)
    assert code == 1 and "golden/run-1: differs" in out and "status: 'FAIL' != " in out, out
    assert "the scenario changed" not in out, "the case is unchanged; only the record lost evidence"
    # A saved grade of the wrong shape is that run's error; the rest of the iteration is still checked.
    iteration, spec = iterations["pass"]
    for shape in ("null", "[]", '{"expectations": [null]}'):
        broken = iteration / f"eval-{spec['id']}" / "broken" / "run-1"
        shutil.rmtree(broken.parent, ignore_errors=True)
        shutil.copytree(iteration / f"eval-{spec['id']}" / "golden" / "run-1", broken)
        (broken / "grading.json").write_text(shape, encoding="utf-8")
        code, out = check(iteration, spec)
        assert code == 1 and "broken/run-1: not checked:" in out and "checked 2 run(s)" in out, (shape, out)
    shutil.rmtree(broken.parent)
    # A run that lost its trace summary is still checked from its evidence; one that lost both was
    # never read, so the iteration is not clean.
    published = iteration / f"eval-{spec['id']}" / "golden" / "run-1"
    (published / "outputs" / "trace-summary.json").unlink()
    code, out = check(iteration, spec)
    assert code == 0 and "checked 1 run(s) from their evidence; 0 differ" in out, out
    (published / "evidence.json").unlink()
    code, out = check(iteration, spec)
    assert code == 1 and "1 run(s) not checked: neither evidence.json nor a trace summary" in out, out


# --- item 4: a run with its own evidence regrades from evidence.json alone ---------------------


def _evidence_only(run_dir: Path, root: Path) -> Path:
    """A copy of the run that keeps its evidence.json and nothing else."""
    alone = root / "alone" / "run-1"
    alone.mkdir(parents=True)
    shutil.copy2(run_dir / "evidence.json", alone / "evidence.json")
    return alone


@pytest.mark.parametrize("item", CASES, ids=IDS)
def test_a_run_regrades_to_its_live_verdict_from_its_evidence_alone(item: golden_runs.Case, tmp_path: Path) -> None:
    run_dir, grading, _summary = _live(item, tmp_path)
    alone = _evidence_only(run_dir, tmp_path)
    regraded = rescoring.regrade_run(alone, item.spec(), write=False)
    assert comparable(regraded) == comparable(grading)
    written = rescoring.regrade_run(alone, item.spec(), write=True)
    assert comparable(written) == comparable(grading)
    assert sorted(p.name for p in (alone / "assessments" / "1").iterdir()) == [
        "evidence.json",
        "grading.json",
        "trace-summary.json",
    ]
    assert sorted(p.name for p in alone.iterdir()) == ["assessments", "evidence.json"], "nothing else was read or made"


@pytest.mark.parametrize("item", [c for c in CASES if c.native is not None], ids=[c.name for c in CASES if c.native is not None])
def test_the_native_replay_reads_the_same_from_files_and_from_evidence(item: golden_runs.Case, tmp_path: Path) -> None:
    run_dir, _grading, _summary = _live(item, tmp_path)
    found = rescoring.load_evidence(run_dir, item.spec())
    assert rescoring.self_sufficient(found, item.spec())
    # Replayed against the image the trial was served, restaged where the run recorded it.
    with rescoring._served_plugin_root(rescoring.summary_of(found)) as (served, _):
        from_files = rescoring.native_regrade_problem(run_dir, item.spec(), served)
        from_evidence = rescoring.native_evidence_problem(found, item.spec(), served)
    assert (str(from_evidence), type(from_evidence)) == (str(from_files), type(from_files))
    expected = {"native_pass": None, "native_wrong_session": "session", "native_incomplete_followup": "no result"}
    assert (from_evidence is None) if expected[item.name] is None else (expected[item.name] in str(from_evidence))


def test_a_damaged_native_turn_in_the_evidence_is_named_by_the_replay(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "native_pass")
    run_dir, _grading, _summary = _live(item, tmp_path)
    found = rescoring.load_evidence(run_dir, item.spec())
    second = found.turns[1]

    def replay(record: evidence.EvidenceV1) -> str | None:
        with rescoring._served_plugin_root(rescoring.summary_of(record)) as (served, _):
            return rescoring.native_evidence_problem(record, item.spec(), served)

    assert replay(found) is None
    resumed_elsewhere = found.model_copy(
        update={"turns": [found.turns[0], second.model_copy(update={"resume": "another-session"})]}
    )
    assert "session, workspace, or model binding changed" in str(replay(resumed_elsewhere))
    leaked = found.model_copy(
        update={"turns": [found.turns[0], second.model_copy(update={"credential_markers": ["sk-ant-"]})]}
    )
    assert "credential marker" in str(replay(leaked))
    untraced = found.model_copy(update={"turns": [found.turns[0], second.model_copy(update={"trace": None})]})
    assert "boundary evidence missing or invalid" in str(replay(untraced))


def test_an_older_native_record_without_its_turns_regrades_from_its_files(tmp_path: Path) -> None:
    """A native run whose evidence was written before turns carried their traces is not self-sufficient,
    so its regrade still reads the run's files, and still reaches its live verdict."""
    item = next(c for c in CASES if c.name == "native_pass")
    run_dir, grading, _summary = _live(item, tmp_path)
    record = run_dir / "evidence.json"
    older = json.loads(record.read_text("utf-8"))
    older.pop("conversation", None)
    for turn in older["turns"]:
        for field in ("invoked", "workspace", "trace", "credential_markers", "input_sha256", "release",
                      "judge_context_sha256", "response_text_sha256"):
            turn.pop(field, None)
    record.write_text(json.dumps(older), encoding="utf-8")
    found = rescoring.load_evidence(run_dir, item.spec())
    assert not rescoring.self_sufficient(found, item.spec())
    assert comparable(rescoring.regrade_run(run_dir, item.spec(), write=False)) == comparable(grading)


def test_a_raw_trace_changed_beside_the_evidence_is_refused(tmp_path: Path) -> None:
    """The evidence is all a regrade needs; a raw trace still beside it must be the one it recorded."""
    item = next(c for c in CASES if c.name == "pass")
    run_dir, grading, _ = _live(item, tmp_path)
    assert comparable(rescoring.regrade_run(run_dir, item.spec(), write=False)) == comparable(grading)
    with (run_dir / "stdout.jsonl").open("a", encoding="utf-8") as trace:
        trace.write("\n")
    regraded = rescoring.regrade_run(run_dir, item.spec(), write=False)
    assert regraded["status"] == "INCONCLUSIVE"
    assert "saved raw trace stdout.jsonl differs from the run's evidence" in str(regraded["void"])


@pytest.mark.parametrize("ending", ["turn_limit", "error_result"])
def test_a_conversation_that_ended_before_its_follow_up_regrades_from_its_evidence_alone(
    tmp_path: Path, ending: str
) -> None:
    """A native conversation whose first invocation spent the turn budget, or ended in an error, never
    creates its follow-up folder; its evidence still records that turn, so it regrades alone."""
    spec = native_conversation_spec()
    flags = {"turns": (spec["max_turns"], 2)} if ending == "turn_limit" else {"initial_subtype": "error_during_execution"}
    settings = trials.BatchSettings(
        plugin_root=ROOT, label="native", model="stub-model", out_dir=tmp_path / "it", timeout=60,
        executable="native-stub", keep_workspace=False, env_factory=plain_env_factory(), runtime=STUB_RUNTIME,
    )  # fmt: skip
    with mock.patch.object(invocation, "run_cli", side_effect=native_launch(spec, [], **flags)):
        trials.run_trial(spec, run_number=1, settings=settings)
    run_dir = tmp_path / "it" / f"eval-{spec['id']}" / "native" / "run-1"
    assert not (run_dir / "followup").exists(), "the follow-up never ran"
    grading = json.loads((run_dir / "grading.json").read_text("utf-8"))
    found = rescoring.load_evidence(run_dir, spec)
    assert [t.invoked for t in found.turns] == [True, False]
    assert rescoring.self_sufficient(found, spec)
    alone = _evidence_only(run_dir, tmp_path)
    assert comparable(rescoring.regrade_run(alone, spec, write=False)) == comparable(grading)
