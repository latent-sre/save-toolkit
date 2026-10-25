"""Entrypoint controls exercise JSON export and model-free operator validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from itbench_testkit import diagnosis, manifest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "evals" / "itbench_pilot.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, check=False)


def test_validate_and_export_cli(tmp_path: Path) -> None:
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps(manifest(tmp_path / "source")))
    check = run("validate", "--manifest", str(m))
    assert check.returncode == 0, check.stderr
    assert json.loads(check.stdout)["cases"] == 5
    sub = tmp_path / "submission.json"
    sub.write_text(json.dumps(diagnosis()))
    result = run("export", "--submission", str(sub), "--output", str(tmp_path / "output.json"))
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "output.json").read_text())["entities"][0]["contributing_factor"] is True


def test_cli_rejects_metadata_written_inside_candidate_boundary(tmp_path: Path) -> None:
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps(manifest(tmp_path / "source")))
    dest = tmp_path / "candidate"
    result = run(
        "stage",
        "--manifest",
        str(m),
        "--case",
        "wp04-24",
        "--source",
        str(tmp_path / "source"),
        "--destination",
        str(dest),
        "--receipt",
        str(dest / "receipt.json"),
    )
    assert result.returncode == 2
    assert not dest.exists()


def test_failed_export_does_not_overwrite_existing_evidence(tmp_path: Path) -> None:
    sub = tmp_path / "submission.json"
    sub.write_text(json.dumps(diagnosis()))
    out = tmp_path / "output.json"
    out.write_text("preserved")
    result = run("export", "--submission", str(sub), "--output", str(out))
    assert result.returncode == 2
    assert out.read_text() == "preserved"


def test_assessment_refuses_ground_truth_not_bound_to_selected_case(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps(manifest(source)))
    sub = tmp_path / "submission.json"
    sub.write_text(json.dumps(diagnosis()))
    bindings = tmp_path / "bindings.json"
    bindings.write_text(
        json.dumps({"otel-demo/Deployment/checkout": ["deployment"], "otel-demo/Service/checkout": ["service"]})
    )
    gt = tmp_path / "wrong.yaml"
    gt.write_text(
        "groups: [{id: deployment, root_cause: true}, {id: service}]\npropagations: [{source: deployment, target: service}]\n"
    )
    out = tmp_path / "assessment.json"
    result = run(
        "assess",
        "--manifest",
        str(m),
        "--submission",
        str(sub),
        "--bindings",
        str(bindings),
        "--ground-truth",
        str(gt),
        "--output",
        str(out),
    )
    assert result.returncode == 2
    assert not out.exists()
    assert "ground truth differs from selected case" in result.stderr
