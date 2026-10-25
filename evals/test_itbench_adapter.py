"""Offline controls for the WP04 source boundary and explicit assessment adaptation."""

from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path

import pytest
from itbench_adapter import assess_local, export_submission, fetch_sources, stage_case, validate_manifest
from itbench_testkit import BINDINGS, PREFIX, SHA, diagnosis, manifest, truth


def test_staging_copies_only_reviewed_observations(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = manifest(source)
    future = source / "Scenario-24" / "alerts" / "alerts_at_2099-01-01T00-00-00.json"
    future.parent.mkdir()
    future.write_text('{"observation": "UNRELEASED_FUTURE_CANARY"}')
    dest = tmp_path / "candidate"
    receipt = stage_case(m, "wp04-24", source, dest)
    assert [p.name for p in dest.iterdir()] == ["k8s_events_raw.tsv"]
    assert b"ANSWER_CANARY" not in b"".join(p.read_bytes() for p in dest.rglob("*") if p.is_file())
    assert b"UNRELEASED_FUTURE_CANARY" not in b"".join(p.read_bytes() for p in dest.rglob("*") if p.is_file())
    with pytest.raises(FileNotFoundError):
        (dest / "ground_truth.yaml").read_bytes()
    assert receipt["source_id"] == "Scenario-24"
    assert receipt["candidate_files"][0]["sha256"] == m["cases"][0]["observables"][0]["sha256"]


@pytest.mark.parametrize("change", ["escape", "hidden", "url", "duplicate", "revision", "hiddenhash"])
def test_manifest_rejects_unsafe_or_unbound_sources(tmp_path: Path, change: str) -> None:
    m = manifest(tmp_path / "source")
    asset = m["cases"][0]["observables"][0]
    if change == "escape":
        asset["path"] = "../k8s_events_raw.tsv"
    if change == "hidden":
        asset["path"] = "ground_truth.yaml"
    if change == "url":
        m["cases"][0]["source_path"] = "https://evil.invalid/data"
    if change == "duplicate":
        m["cases"][1]["source_id"] = m["cases"][0]["source_id"]
    if change == "revision":
        m["revision"] = "main"
    if change == "hiddenhash":
        asset["sha256"] = m["cases"][0]["hidden"][0]["sha256"]
    with pytest.raises(ValueError):
        validate_manifest(m)


@pytest.mark.parametrize("mode", ["symlink", "parentlink", "tamper", "overlap", "existing", "answerbytes"])
def test_staging_fails_closed_without_partial_publication(tmp_path: Path, mode: str) -> None:
    source = tmp_path / "source"
    m = manifest(source)
    dest = tmp_path / "candidate"
    asset = source / "Scenario-24" / "k8s_events_raw.tsv"
    if mode == "symlink":
        asset.unlink()
        asset.symlink_to(source / "Scenario-24" / "ground_truth.yaml")
    if mode == "parentlink":
        moved = source / "moved"
        (source / "Scenario-24").rename(moved)
        (source / "Scenario-24").symlink_to(moved, target_is_directory=True)
    if mode == "tamper":
        asset.write_text("tampered")
    if mode == "answerbytes":
        asset.write_text("recommended_actions: [ANSWER_CANARY]")
        m["cases"][0]["observables"][0].update(
            sha256=hashlib.sha256(asset.read_bytes()).hexdigest(), size=asset.stat().st_size
        )
    if mode == "overlap":
        dest = source / "candidate"
    if mode == "existing":
        dest.mkdir()
        (dest / "existing.txt").write_text("keep")
    with pytest.raises(ValueError):
        stage_case(m, "wp04-24", source, dest)
    if mode == "existing":
        assert (dest / "existing.txt").read_text() == "keep"
    else:
        assert not dest.exists()


def test_export_preserves_rank_and_raw_names_without_ground_truth_invention() -> None:
    d = diagnosis()
    d["entities"].reverse()
    result = export_submission(d)
    assert result["entities"][0]["name"] == "otel-demo/Deployment/checkout"
    assert result["entities"][0]["contributing_factor"] is True
    assert result["entities"][1]["contributing_factor"] is False
    assert result["propagations"] == d["edges"]
    assert "group_id" not in json.dumps(result)
    assert d["entities"][0]["id"] == "b"


def test_correct_wrong_unavailable_are_separate_from_upstream_and_semantics() -> None:
    upstream = {"scores": {"root_cause_entity": {"calculation": 0.75}}, "extra": ["preserve"]}
    original = copy.deepcopy(upstream)
    correct = assess_local(diagnosis(), BINDINGS, truth(), upstream)
    assert correct["adapted_local"]["root_entity_at_1"] == 1
    assert correct["adapted_local"]["edge_precision"] == 1.0
    assert correct["adapted_local"]["edge_recall"] == 1.0
    assert correct["upstream_result"] == original == upstream
    assert correct["manual_semantics"]["verdict"] == "INCONCLUSIVE"
    wrong = diagnosis()
    wrong["entities"][0]["rank"] = None
    wrong["entities"][1]["rank"] = 1
    result = assess_local(wrong, BINDINGS, truth())
    assert result["adapted_local"]["root_entity_at_1"] == 0
    assert result["upstream_result"] is None
    unavailable = assess_local(
        {"case_id": "wp04-24", "status": "unavailable", "reason": "collector lost"}, BINDINGS, truth()
    )
    assert unavailable["adapted_local"]["verdict"] == "INCONCLUSIVE"
    assert unavailable["adapted_local"]["root_entity_at_1"] is None


@pytest.mark.parametrize("binding", [{}, {"otel-demo/Deployment/checkout": ["deployment", "service"]}])
def test_missing_or_ambiguous_mapping_is_unavailable(binding: dict) -> None:
    result = assess_local(diagnosis(), binding, truth())
    assert result["adapted_local"]["verdict"] == "INCONCLUSIVE"
    assert result["adapted_local"]["root_entity_at_1"] is None
    assert result["mapping_gaps"]


def test_dangling_ground_truth_edge_is_not_repaired() -> None:
    gt = truth()
    gt["propagations"][0]["target"] = "frontend-proxy-1"
    result = assess_local(diagnosis(), BINDINGS, gt)
    assert result["adapted_local"]["verdict"] == "INCONCLUSIVE"
    assert "frontend-proxy-1" in json.dumps(result["mapping_gaps"])


@pytest.mark.parametrize("kind", ["duplicate-rank", "duplicate-id", "edge", "boolean-rank", "missing-reason"])
def test_submission_rejects_invented_or_ambiguous_claims(kind: str) -> None:
    d = diagnosis()
    if kind == "duplicate-rank":
        d["entities"][1]["rank"] = 1
    if kind == "duplicate-id":
        d["entities"][1]["id"] = "a"
    if kind == "edge":
        d["edges"][0]["target"] = "unknown"
    if kind == "boolean-rank":
        d["entities"][0]["rank"] = True
    if kind == "missing-reason":
        del d["entities"][0]["reason"]
    with pytest.raises(ValueError):
        export_submission(d)


def test_frozen_pilot_is_pinned_with_five_original_case_identities() -> None:
    m = json.loads((Path(__file__).parent / "manifests" / "wp04-itbench-five.json").read_text())
    validate_manifest(m)
    assert {c["source_id"] for c in m["cases"]} == {
        "Scenario-24",
        "Scenario-7",
        "Scenario-80",
        "Scenario-102",
        "Scenario-21",
    }
    assert sum(a["size"] for c in m["cases"] for a in c["observables"]) == 441911602
    assert sum(len(c["observables"]) for c in m["cases"]) == 458
    assert all(c["coherence_gaps"] for c in m["cases"])


def test_submission_requires_original_case_binding_for_local_assessment() -> None:
    malformed = {"groups": [None], "propagations": []}
    result = assess_local(diagnosis(), BINDINGS, malformed)
    assert result["adapted_local"]["verdict"] == "INCONCLUSIVE"
    assert result["mapping_gaps"]


def test_unavailable_edge_mapping_retains_supported_root_measurement() -> None:
    result = assess_local(diagnosis(), {"otel-demo/Deployment/checkout": ["deployment"]}, truth())
    assert result["adapted_local"]["root_entity_at_1"] == 1
    assert result["adapted_local"]["edge_precision"] is None
    assert result["adapted_local"]["verdict"] == "INCONCLUSIVE"


def test_no_submitted_root_is_a_measured_failure_not_an_instrument_gap() -> None:
    d = diagnosis()
    d["entities"][0]["rank"] = None
    result = assess_local(d, BINDINGS, truth())
    assert result["adapted_local"]["root_entity_at_1"] == 0
    assert result["adapted_local"]["verdict"] == "FAIL"


def test_fetch_uses_only_pinned_observables_and_checks_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "origin"
    m = manifest(source)
    calls = []

    def open_pinned(url: str, *, timeout: int) -> io.BytesIO:
        assert timeout == 120
        calls.append(url)
        assert f"/resolve/{SHA}/{PREFIX}/Scenario-" in url
        assert url.endswith("/k8s_events_raw.tsv")
        case = url.split("/")[-2]
        return io.BytesIO((source / case / "k8s_events_raw.tsv").read_bytes())

    monkeypatch.setattr("itbench_adapter.core.urllib.request.urlopen", open_pinned)
    dest = tmp_path / "cache"
    receipt = fetch_sources(m, dest)
    assert len(calls) == 5
    assert len(receipt["fetched"]) == 5
    assert not list(dest.rglob("ground_truth.yaml"))
    assert receipt["executed"] is False
    assert fetch_sources(m, dest)["fetched"] == []
    assert len(calls) == 5


def test_bad_download_is_not_published(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    m = manifest(tmp_path / "origin")
    monkeypatch.setattr("itbench_adapter.core.urllib.request.urlopen", lambda *a, **kw: io.BytesIO(b"wrong"))
    with pytest.raises(ValueError, match="download differs"):
        fetch_sources(m, tmp_path / "cache")
    assert not list((tmp_path / "cache").rglob("*"))


def test_each_selected_case_has_an_actual_root_binding_and_excluded_cases_stay_excluded() -> None:
    base = Path(__file__).parent / "manifests"
    selected = json.loads((base / "wp04-itbench-five.json").read_text())
    bindings = json.loads((base / "wp04-bindings.json").read_text())["cases"]
    roots = {
        "wp04-7": "flagd-config",
        "wp04-21": "otel-demo-valkey-memory-stress",
        "wp04-24": "checkout-deployment",
        "wp04-80": "otel-demo-checkout-kafka-network-partition",
        "wp04-102": "otel-demo-namespace-1",
    }
    assert {case["id"] for case in selected["cases"]} == set(roots)
    for case_id, root in roots.items():
        assert any(matches == [root] for matches in bindings[case_id].values()), case_id
    assert bindings["wp04-7"]["otel-demo/ConfigMap/flagd-config"] == ["flagd-config"]
    assert bindings["wp04-7"]["otel-demo/Service/frontend-proxy"] == ["frontend-proxy-service-1"]
    exclusions = json.loads((base / "wp04-exclusions.json").read_text())["excluded"]
    assert {"Scenario-29", "Scenario-31", "Scenario-105"} <= {case["source_id"] for case in exclusions}
    assert not {"wp04-29", "wp04-31", "wp04-105"} & set(bindings)
