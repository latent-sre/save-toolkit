"""The evidence engine grades every golden the way the authoritative engine does, in shadow (stage 3
of the runner rewrite, RUNNER-001): on each live attempt and on each regrade of a saved run."""

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
from probe import cli, engine, rescoring, shadow
from probe.attempt import Phase
from probe.outcomes import State
from probe_testkit import saved_grade, saved_summary, write_saved_run

CASES = [c for c in golden_runs.CASES if not c.raises]
IDS = [c.name for c in CASES]


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


@contextlib.contextmanager
def _the_judge_that_graded(copy: Path):
    binding = json.loads((copy / "grading.json").read_text("utf-8")).get("judge_binding")
    if binding is None:
        yield
        return
    with mock.patch.object(judge, "execution_identity", return_value=binding["execution"]):
        yield


@pytest.mark.parametrize("item", CASES, ids=IDS)
def test_the_shadow_agrees_with_every_live_grade(item: golden_runs.Case, tmp_path: Path) -> None:
    run_dir, _grading, summary = _live(item, tmp_path)
    result = json.loads((run_dir / shadow.FILE).read_text("utf-8"))
    assert result["engine"] == shadow.ENGINE and result["source"] == "live"
    assert result.get("error") is None
    assert result["differences"] == [] and result["agrees"] is True
    assert "shadow_disagreements" not in summary and "shadow_error" not in summary


@pytest.mark.parametrize("item", CASES, ids=IDS)
def test_the_shadow_agrees_with_every_regrade(item: golden_runs.Case, tmp_path: Path) -> None:
    copy = _saved_copy(item, tmp_path)
    with _the_judge_that_graded(copy):
        grading, result = rescoring.regrade_run_shadow(
            copy, golden_runs.scenario(item), write=False, relax_identity=True
        )
    assert result is not None and result.get("error") is None
    assert result["differences"] == [] and result["agrees"] is True
    assert shadow.comparable(result["verdict"]) == shadow.comparable(grading)


def test_a_lapsed_judgment_lapses_in_the_shadow_too(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "rubric_kept")
    copy = _saved_copy(item, tmp_path)
    binding = json.loads((copy / "grading.json").read_text("utf-8"))["judge_binding"]
    other = {**binding["execution"], "source_sha256": "0" * 64}
    with mock.patch.object(judge, "execution_identity", return_value=other):
        grading, result = rescoring.regrade_run_shadow(
            copy, golden_runs.scenario(item), write=False, relax_identity=True
        )
    assert grading["status"] == "INCONCLUSIVE" and "re-run under the current judge" in grading["inconclusive"]
    assert result is not None and result["agrees"] is True, result.get("differences")


def test_a_written_regrade_keeps_its_shadow_beside_its_assessment(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "pass")
    copy = _saved_copy(item, tmp_path)
    rescoring.regrade_run(copy, golden_runs.scenario(item), write=True, relax_identity=True)
    assert not (copy / shadow.FILE).exists(), "the live attempt's folder is never rewritten"
    result = json.loads((copy / "assessments" / "1" / shadow.FILE).read_text("utf-8"))
    assert result["source"] == "regrade" and result["agrees"] is True


def test_the_comparable_grade_leaves_out_what_is_beside_the_verdict() -> None:
    grading = {
        "status": "PASS",
        "after_assessment": "cleanup failed",
        "scenario_sha256": "a" * 64,
        "judge_binding": {"x": 1},
        "assessed_at": "now",
        "expectations": [
            {"text": "t", "kind": "requires", "state": "PASS", "passed": True, "evidence": "[kept: live-judge] ok"}
        ],
        "summary": {"passed": 1, "failed": 0, "total": 1, "pass_rate": 1.0},
    }
    view = shadow.comparable(grading)
    assert view["expectations"][0]["evidence"] == "ok"
    assert not {"after_assessment", "scenario_sha256", "judge_binding", "assessed_at"} & set(view)
    changed = {**grading, "status": "FAIL", "expectations": [{**grading["expectations"][0], "state": "FAIL"}]}
    assert shadow.differences(grading, changed) == [
        "expectations[0].state: 'PASS' != 'FAIL'",
        "status: 'PASS' != 'FAIL'",
    ]


def test_a_kept_outcome_bounded_with_its_marker_compares_equal_to_its_recorded_evidence() -> None:
    long = "x" * 600
    marker = "[kept: live-judge] "
    authoritative = {
        "status": "PASS",
        "expectations": [
            {
                "text": "t",
                "kind": "requires",
                "state": "PASS",
                "passed": True,
                "evidence": (marker + long)[:600],
                "evidence_truncated": True,
            }
        ],
        "summary": {},
    }
    shadowed = {
        "status": "PASS",
        "expectations": [{"text": "t", "kind": "requires", "state": "PASS", "passed": True, "evidence": long}],
        "summary": {},
    }
    assert shadow.differences(authoritative, shadowed) == []


def test_the_shadow_engine_never_breaks_the_grade_it_shadows(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "pass")
    with mock.patch.object(engine, "grade", side_effect=RuntimeError("engine defect")):
        run_dir, grading, summary = _live(item, tmp_path)
    assert grading["status"] == "PASS"
    result = json.loads((run_dir / shadow.FILE).read_text("utf-8"))
    assert result["agrees"] is False and result["error"] == "RuntimeError: engine defect"
    assert summary["shadow_error"] == "RuntimeError: engine defect"


def test_the_attempt_log_shows_each_phase_and_where_a_failure_left_it(tmp_path: Path) -> None:
    phases = {}
    for name in ("pass", "void_identity", "machinery_failure", "service_unavailable"):
        item = next(c for c in CASES if c.name == name)
        run_dir, _, _ = _live(item, tmp_path / name)
        phases[name] = [p["phase"] for p in json.loads((run_dir / "attempt.json").read_text("utf-8"))["phases"]]
    assert phases["pass"] == ["prepared", "served", "seeded", "invoked", "observed", "graded", "published"]
    assert phases["void_identity"][-2:] == [Phase.VOID, Phase.PUBLISHED]
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


def test_the_shadow_report_counts_attempts_coverage_and_the_gate(tmp_path: Path) -> None:
    iteration = tmp_path / "iteration"
    specs = []
    for name in ("pass", "machinery_failure", "wall_clock", "native_pass"):
        item = next(c for c in CASES if c.name == name)
        root = tmp_path / name
        root.mkdir()
        run_dir, _, _ = _live(item, root)
        spec = item.spec()
        target = iteration / f"eval-{spec['id']}" / "golden" / "run-1"
        if target.exists():
            target = iteration / f"eval-{spec['id']}" / name / "run-1"
        shutil.copytree(run_dir, target)
        specs.append(spec)
    seen = {s["id"]: s for s in specs}
    report = rescoring.shadow_report(iteration, list(seen.values()))
    assert report["attempts"] == 4 and report["disagreeing"] == 0 and report["agreeing"] == 4
    assert report["coverage"] == {"native": 1, "cut_short": 1, "machinery_failure": 1}
    assert report["gate"] == {"count": shadow.GATE_COUNT, "met": False}, "four attempts do not meet the owner's count"
    with mock.patch.object(cli.catalog, "load_all_scenarios", return_value=list(seen.values())):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert cli.main(["shadow", str(iteration)]) == 0
        assert "4 attempt(s), 4 grade(s) agree, 0 disagree" in out.getvalue()
        broken = next(iteration.rglob(shadow.FILE))
        result = json.loads(broken.read_text("utf-8"))
        broken.write_text(json.dumps({**result, "agrees": False, "differences": ["status: 'PASS' != 'FAIL'"]}))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert cli.main(["shadow", str(iteration)]) == 1
        assert "disagrees: status: 'PASS' != 'FAIL'" in out.getvalue()


# --- the Codex findings on PR #460, each a regression the shadow must not show ----------------


def test_a_strict_regrade_that_rejects_a_changed_identity_voids_the_shadow_too(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "pass")
    copy = _saved_copy(item, tmp_path)
    grading, result = rescoring.regrade_run_shadow(copy, golden_runs.scenario(item), write=False, relax_identity=False)
    assert grading["status"] == "INCONCLUSIVE" and "saved scenario identity" in str(grading["inconclusive"])
    assert result is not None and result["agrees"] is True, result.get("differences")


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


def test_a_summary_without_valid_counts_leaves_a_count_check_unmeasured_in_both_engines(tmp_path: Path) -> None:
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
    grading, result = rescoring.regrade_run_shadow(run, spec, write=False, relax_identity=True)
    count = next(e for e in grading["expectations"] if e["text"] == text)
    assert count["state"] == "INCONCLUSIVE" and "count evidence is missing" in count["evidence"]
    assert result is not None and result["agrees"] is True, result.get("differences")


def test_the_shadow_report_counts_kept_attempts_too(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "pass")
    root = tmp_path / "live"
    root.mkdir()
    run_dir, _, _ = _live(item, root)
    spec = item.spec()
    iteration = tmp_path / "iteration"
    published = iteration / f"eval-{spec['id']}" / "golden" / "run-1"
    shutil.copytree(run_dir, published)
    kept = iteration / f"eval-{spec['id']}" / "golden" / "attempts" / "run-1" / "1"
    shutil.copytree(run_dir, kept)
    result = json.loads((kept / shadow.FILE).read_text("utf-8"))
    (kept / shadow.FILE).write_text(
        json.dumps({**result, "agrees": False, "differences": ["status: 'PASS' != 'FAIL'"]})
    )
    report = rescoring.shadow_report(iteration, [spec])
    assert report["attempts"] == 2 and report["disagreeing"] == 1 and report["gate"]["met"] is False
    assert [r.get("attempt") for r in report["runs"] if not r["agrees"]] == [1]
