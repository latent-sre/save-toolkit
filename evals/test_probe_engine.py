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
