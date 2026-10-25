"""Discovery is read-only; suites and exported selections name exact work."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import campaign_report
import catalog as discovery
import pytest
from probe import catalog as native_catalog
from probe import fingerprints

ROOT = Path(__file__).resolve().parents[1]


def invoke(*arguments: str, root: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(root / "evals/catalog.py"), *arguments],
                          cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30,
                          env={**os.environ, "PYTHONPATH": ""})


def output(*arguments: str, root: Path = ROOT) -> dict:
    result = invoke(*arguments, "--json", root=root)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_native_inventory_matches_the_runner_and_keeps_conversation_profile_separate():
    rows = output("list")["items"]
    assert [row["id"] for row in rows] == sorted(s["id"] for s in native_catalog.load_all_scenarios())
    conversation = next(row for row in rows if row["id"] == "incident-session-01-a")
    assert conversation["kind"] == "routing"
    assert conversation["profile"] == "incident-v1"
    assert conversation["partition"] == "development"
    assert conversation["manual_review"] == "pending"
    assert "prompt" not in conversation and "fixture" not in conversation


def test_filters_distinguish_primary_component_from_cross_cutting_suite():
    primary = output("list", "--component", "skill:python-craft")["items"]
    assert primary and all(row["component"] == "skill:python-craft" for row in primary)
    assert "build-python-package-refactor" not in {row["id"] for row in primary}
    suite = output("list", "--suite", "python-craft", "--kind", "build", "--kind", "contract")["items"]
    assert "build-python-package-refactor" in {row["id"] for row in suite}
    assert all(row["kind"] in {"build", "contract"} for row in suite)
    negatives = [row for row in primary if row["routing_expectation"] == "not_fire"]
    assert negatives
    assert output("list", "--profile", "incident-v1")["items"]
    assert output("list", "--component", "skill:python-craft", "--profile", "incident-v1")["items"] == []
    assert invoke("list", "--kind", "typo").returncode == 3
    assert invoke("list", "--component", "skill:typo").returncode == 3


@pytest.fixture
def minimal(tmp_path):
    (tmp_path / "evals/suites").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    shutil.copyfile(ROOT / "evals/catalog.py", tmp_path / "evals/catalog.py")
    (tmp_path / "scripts/test_alpha.py").write_text("raise AssertionError('must not import tests')\n")
    (tmp_path / "evals/test_beta.py").write_text("raise AssertionError('must not import tests')\n")
    for name, tests in (("first", ["scripts/test_alpha.py"]),
                        ("second", ["scripts/test_alpha.py", "evals/test_beta.py"])):
        (tmp_path / f"evals/suites/{name}.json").write_text(json.dumps({
            "schema_version": 1, "id": name, "summary": "Fixture suite", "tests": tests,
            "native_scenarios": ["deliberately-missing"], "campaigns": [], "guides": [],
        }))
    return tmp_path


def test_test_projection_needs_neither_native_modules_nor_test_imports(minimal):
    envelope = output("tests", "--suite", "first", "--suite", "second", "--suite", "first", root=minimal)
    assert envelope == {"schema_version": 1, "view": "tests", "items": [
        {"path": "evals/test_beta.py", "selected_by": ["second"]},
        {"path": "scripts/test_alpha.py", "selected_by": ["first", "second"]},
    ]}
    (minimal / "scripts/test_unrelated.py").write_text("def test_new(): pass\n")
    assert output("tests", "--suite", "first", root=minimal)["items"] == [
        {"path": "scripts/test_alpha.py", "selected_by": ["first"]}]
    assert len(output("tests", root=minimal)["items"]) == 3


@pytest.mark.parametrize("change", [
    {"schema_version": 2}, {"schema_version": True}, {"unknown": 1}, {"id": "other"},
    {"tests": ["../outside.py"]}, {"tests": ["scripts/*.py"]}, {"tests": ["scripts"]},
    {"tests": ["scripts/test_alpha.py::test_one"]}, {"tests": ["scripts/missing.py"]},
    {"tests": ["scripts/test_alpha.py", "scripts/test_alpha.py"]},
])
def test_invalid_suite_fails_without_broadening_selection(minimal, change):
    path = minimal / "evals/suites/first.json"
    data = json.loads(path.read_text())
    data.update(change)
    path.write_text(json.dumps(data))
    result = invoke("tests", "--suite", "first", root=minimal)
    assert result.returncode == 3, result.stdout + result.stderr


def test_duplicate_json_keys_and_linked_test_are_refused(minimal):
    path = minimal / "evals/suites/first.json"
    original = path.read_text()
    path.write_text(original.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'))
    assert invoke("tests", "--suite", "first", root=minimal).returncode == 3
    path.write_text(original)
    target = minimal / "scripts/test_alpha.py"
    target.unlink()
    target.symlink_to(minimal / "evals/test_beta.py")
    assert invoke("tests", "--suite", "first", root=minimal).returncode == 3


def test_committed_suites_validate_and_external_campaigns_are_links():
    assert invoke("check").returncode == 0
    assert {row["id"] for row in output("suites")["items"]} >= {
        "readonly-guard", "eval-harness", "python-craft", "incident-conversations", "swebench"}
    campaign = output("campaigns")["items"]
    assert any(row["entrypoint"] == "evals/swebench_repair.py" for row in campaign)
    assert invoke("tests", "--suite", "missing").returncode == 3


def test_export_binds_final_cases_is_exclusive_and_feeds_existing_reporter(tmp_path):
    target = tmp_path / "selection.json"
    case = "build-python-package-refactor"
    result = invoke("select", "--scenario", case, "--trials", "3", "--out", str(target))
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(target.read_text())
    spec = next(s for s in native_catalog.load_all_scenarios() if s["id"] == case)
    assert data["profile"] == "native-selection-v1"
    assert data["trials"] == 3
    assert data["tasks"] == [{"instance_id": case, "case_sha256": fingerprints.case_digest(spec)}]
    assert hashlib.sha256(target.read_bytes()).hexdigest() in result.stdout
    original = target.read_bytes()
    assert invoke("select", "--scenario", case, "--trials", "3", "--out", str(target)).returncode == 3
    assert target.read_bytes() == original
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    report = campaign_report.build_report(bundle, data, "candidate")
    assert report["counts"]["selected_cases"] == 1
    assert len(report["cases"][case]["slots"]) == 3


@pytest.mark.parametrize("arguments", [
    ["--scenario", "missing", "--trials", "1"],
    ["--scenario", "build-python-package-refactor", "--trials", "0"],
    ["--scenario", "build-python-package-refactor", "--trials", "10001"],
    ["--suite", "readonly-guard", "--trials", "1"],
    ["--suite", "python-craft", "--suite", "readonly-guard", "--trials", "1"],
    ["--suite", "swebench", "--trials", "1"],
])
def test_invalid_or_non_native_export_creates_nothing(tmp_path, arguments):
    target = tmp_path / "selection.json"
    assert invoke("select", *arguments, "--out", str(target)).returncode == 3
    assert not target.exists()


def test_coverage_accounts_for_every_current_case_and_test_without_claiming_quality():
    result = output("coverage")
    summary = result["summary"]
    assert summary["native_cases"] == len(native_catalog.load_all_scenarios())
    assert summary["test_files"] == sum(len(list((ROOT / folder).glob("test_*.py"))) for folder in ("scripts", "evals"))
    assert summary["unassigned_native_cases"] == []
    assert summary["unassigned_test_files"] == []
    python = next(row for row in result["items"] if row["id"] == "python-craft")
    assert python["kinds"]["build"] > 0 and python["kinds"]["routing"] > 0
    assert "exact_json" in python["grader_types"]
    assert "PASS" not in result and "acceptance" not in summary
    assert "inventory" in result["meaning"].lower()


def test_every_existing_execution_track_is_discoverable_and_plans_stay_separate():
    tracks = output("tracks")["items"]
    by_id = {row["id"]: row for row in tracks}
    assert set(by_id) >= {"native", "codex", "muse", "inspect", "itbench", "swebench", "swt",
                         "harbor", "multi-model", "graph-sandbox", "interop-sandbox",
                         "principal-judgment", "sregym", "aiopslab", "coder-eval", "judge-comparison"}
    assert by_id["native"]["implementation"] == "present"
    assert by_id["principal-judgment"]["implementation"] == "proposal"
    assert by_id["sregym"]["implementation"] == "planned"
    assert by_id["sregym"]["entrypoints"] == []
    assert by_id["graph-sandbox"]["kind"] == "sandbox"
    assert {row["entrypoint"] for row in output("campaigns")["items"]} >= {
        "evals/swebench_repair.py", "evals/itbench_pilot.py", "evals/swt_pilot.py", "evals/harbor_pilot.py",
        "evals/testing_block.py"}


def write_tracks(root: Path, **change):
    item = {"id": "planned", "summary": "Future experiment; not implemented", "kind": "benchmark",
            "implementation": "planned", "entrypoints": [], "suites": [], "guides": ["guide.md"]}
    item.update(change)
    (root / "guide.md").write_text("# Guide\n")
    (root / "evals/tracks.json").write_text(json.dumps({"schema_version": 1, "tracks": [item]}))


def test_track_listing_is_read_only_and_does_not_need_optional_modules(minimal):
    write_tracks(minimal)
    result = output("tracks", root=minimal)
    assert result["items"][0]["implementation"] == "planned"
    assert result["items"][0]["entrypoints"] == []
    assert output("tracks", "--suite", "first", root=minimal)["items"] == []


@pytest.mark.parametrize("change", [
    {"implementation": "accepted"}, {"kind": "unknown"}, {"suites": ["missing"]},
    {"guides": ["../outside"]}, {"entrypoints": ["scripts/test_alpha.py"]},
    {"implementation": "present", "entrypoints": []}, {"extra": True},
])
def test_invalid_track_references_or_readiness_claims_are_refused(minimal, change):
    write_tracks(minimal, **change)
    assert invoke("tracks", root=minimal).returncode == 3


def test_coverage_reports_new_unassigned_items_and_turn_graders(minimal, monkeypatch, capsys):
    write_tracks(minimal)
    (minimal / "scripts/test_new.py").write_text("def test_new(): pass\n")
    rows = [{"id": name, "kind": "contract", "component": "skill:example", "profile": None,
             "manual_review": None} for name in ("deliberately-missing", "unassigned")]
    specs = {row["id"]: {"id": row["id"], "conversation": {"turn_graders": [[{"type": "exact_fields"}]]}}
             for row in rows}
    monkeypatch.setattr(discovery, "ROOT", minimal)
    monkeypatch.setattr(discovery, "native_inventory", lambda: (rows, specs))
    assert discovery.main(["coverage", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["unassigned_native_cases"] == ["unassigned"]
    assert data["summary"]["unassigned_test_files"] == ["scripts/test_new.py"]
    assert data["summary"]["assigned_native_cases"] == 1
    assert data["items"][0]["grader_types"] == ["exact_fields"]


def test_duplicate_track_ids_are_refused(minimal):
    write_tracks(minimal)
    path = minimal / "evals/tracks.json"
    data = json.loads(path.read_text())
    data["tracks"].append(data["tracks"][0])
    path.write_text(json.dumps(data))
    assert invoke("tracks", root=minimal).returncode == 3
