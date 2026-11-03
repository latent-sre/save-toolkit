"""The evidence engine is the runner's one grading path (stage 4 of the runner rewrite, RUNNER-001):
a live attempt's probes are measured once and recorded as evidence, the grade is read from that
evidence, and a regrade of the same evidence reaches the same verdict."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest import mock

import golden_runs
import judge
import pytest
from probe import checks, engine, rescoring, workspaces
from probe.attempt import Phase
from probe.constants import ROOT
from probe.outcomes import EVIDENCE_LIMIT, CutShort, State, Stop
from probe_testkit import context, grade_trial, saved_grade, saved_summary, tiny_spec, write_saved_run, ws_context

CASES = [c for c in golden_runs.CASES if not c.raises]
IDS = [c.name for c in CASES]
_KEPT = re.compile(r"^\[kept: [\w-]+\] ")
# A regrade bounds a kept marker and its evidence together; the prefix both grades surely hold.
_COMMON_EVIDENCE = EVIDENCE_LIMIT - len("[kept: workspace-dependent] ")


def comparable(grading: Mapping[str, Any]) -> dict[str, Any]:
    """The verdict of a grade: everything but what is beside it (identities, the judge binding, the
    after-assessment record of rule 6, a regrade's kept markers and the tail of bounded evidence)."""
    return {
        "status": grading.get("status"),
        "inconclusive": grading.get("inconclusive"),
        "unmeasured": grading.get("unmeasured"),
        "void": grading.get("void"),
        "run_end": grading.get("run_end"),
        "run_stop": grading.get("run_stop"),
        "grader_error": grading.get("grader_error"),
        "expectations": [
            {
                "text": e.get("text"),
                "kind": e.get("kind"),
                "state": e.get("state"),
                "passed": e.get("passed"),
                "evidence": _KEPT.sub("", str(e.get("evidence") or ""))[:_COMMON_EVIDENCE],
            }
            for e in grading.get("expectations") or []
        ],
        "summary": {key: (grading.get("summary") or {}).get(key) for key in ("passed", "failed", "total")},
    }


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
