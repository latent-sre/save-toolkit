"""Entrypoint controls exercise JSON export and model-free operator validation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
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


@pytest.mark.parametrize(
    "profile", ["indexed-v1", "indexed-v2", "indexed-v3", "indexed-v4", "indexed-v5", "indexed-v6"]
)
def test_prepare_native_cli_exposes_distinct_observable_only_indexed_profile(tmp_path: Path, profile: str) -> None:
    source = tmp_path / "source"
    data = manifest(source)
    for case in data["cases"]:
        body = {
            "kind": "Event",
            "metadata": {"name": "notice"},
            "regarding": {"kind": "Pod", "namespace": "demo", "name": "worker"},
        }
        p = source / case["source_id"] / "k8s_events_raw.tsv"
        p.write_text("Timestamp\tBody\n2025-12-15 18:00:00\t" + json.dumps(body) + "\n")
        case["observables"][0].update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), size=p.stat().st_size)
        (p.parent / "ground_truth.yaml").unlink()
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    destination, receipt = tmp_path / "indexed", tmp_path / "receipt.json"
    result = run(
        "prepare-native",
        "--manifest",
        str(path),
        "--source",
        str(source),
        "--destination",
        str(destination),
        "--receipt",
        str(receipt),
        "--evidence-profile",
        profile,
    )
    assert result.returncode == 0, result.stderr
    metadata = json.loads(receipt.read_text())
    assert metadata["evidence_profile"] == profile
    if profile in {"indexed-v2", "indexed-v3", "indexed-v4", "indexed-v5", "indexed-v6"}:
        assert metadata["observation_index_profile"] == "indexed-v1"
    if profile == "indexed-v3":
        assert metadata["observation_index_extensions"] == ["lookup-catalog-v1"]
    if profile == "indexed-v4":
        assert metadata["observation_index_extensions"] == ["lookup-catalog-v1", "resource-field-history-v1"]
    if profile == "indexed-v5":
        assert metadata["observation_index_extensions"] == ["lookup-catalog-v1", "resource-field-history-v2"]
    if profile == "indexed-v6":
        assert metadata["observation_index_extensions"] == ["lookup-catalog-v2", "resource-field-history-v2"]
    spec = yaml.safe_load((destination / f"wp04-itbench-24-{profile}.yaml").read_text())
    assert spec["id"] == f"wp04-itbench-24-{profile}"
    assert "observations/index.json" in spec["fixture"]["files"]
    assert not any("ground_truth" in name for name in spec["fixture"]["files"])


def test_prepare_native_cli_refuses_unknown_profile_before_writing(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest(tmp_path / "source")))
    destination, receipt = tmp_path / "invalid", tmp_path / "receipt.json"
    result = run(
        "prepare-native",
        "--manifest",
        str(path),
        "--source",
        str(tmp_path / "source"),
        "--destination",
        str(destination),
        "--receipt",
        str(receipt),
        "--evidence-profile",
        "unrecognized",
    )
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
    assert not destination.exists()
    assert not receipt.exists()


@pytest.mark.parametrize("profile", [None, "raw-v2", "indexed-v7"])
def test_prepare_native_cli_uses_corrected_profiles_and_default(tmp_path: Path, profile: str | None) -> None:
    source = tmp_path / "source"
    data = manifest(source)
    for case in data["cases"]:
        path = source / case["source_id"] / "k8s_events_raw.tsv"
        path.write_text(
            'Timestamp\tBody\n2025-12-15 18:00:00\t{"kind":"Event","metadata":{"name":"notice"},'
            '"regarding":{"kind":"Pod","namespace":"demo","name":"worker"}}\n'
        )
        case["observables"][0].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size=path.stat().st_size)
        (path.parent / "ground_truth.yaml").unlink()
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    destination, receipt = tmp_path / "fixtures", tmp_path / "receipt.json"
    result = run(
        "prepare-native",
        "--manifest",
        str(path),
        "--source",
        str(source),
        "--destination",
        str(destination),
        "--receipt",
        str(receipt),
        *(["--evidence-profile", profile] if profile is not None else []),
    )
    assert result.returncode == 0, result.stderr
    selected = profile or "raw-v2"
    metadata = json.loads(receipt.read_text())
    assert metadata.get("evidence_profile") == selected
    spec = yaml.safe_load((destination / f"wp04-itbench-24-{selected}.yaml").read_text())
    assert spec["checks"][2]["check"] == "wp04_submission_v1"
    assert ("observations/index.json" in spec["fixture"]["files"]) == (selected == "indexed-v7")
