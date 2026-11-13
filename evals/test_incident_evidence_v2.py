"""Versioned diagnostic data contracts; these tests do not grade model reasoning."""

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from probe import catalog, fingerprints

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "incident-conversations" / "diagnostics-v2"


def manifest() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((BASE / "manifest.json").read_text())
    return data


def test_diagnostics_are_bound_and_review_never_enters_candidate_input() -> None:
    data = manifest()
    assert data["semantic_assessment"] == "manual; not calibrated or accepted"
    assert data["partition"] == "development"
    assert len(data["profiles"]) == 14
    selection = json.loads((BASE / "report-selection.json").read_text())
    selected = {x["instance_id"]: x["case_sha256"] for x in selection["tasks"]}
    for entry in data["profiles"]:
        path = BASE / entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        spec = yaml.safe_load(path.read_text())
        assert catalog.validate_scenario(spec) == []
        assert selected[spec["id"]] == fingerprints.case_digest(spec)
        candidate_input = spec["prompt"] + json.dumps(spec.get("fixture", {}))
        assert "expected_claims" not in candidate_input and "diagnostics-v2/review" not in candidate_input
        if spec.get("followups"):
            assert spec["conversation"]["manual_review"] == "pending"
            assert not spec.get("graders") and not spec["conversation"].get("turn_graders")
        review = BASE / entry["review_path"]
        assert hashlib.sha256(review.read_bytes()).hexdigest() == entry["review_sha256"]


def test_original_cases_and_review_contracts_are_preserved() -> None:
    data = manifest()
    originals = json.loads((ROOT / "incident-conversations" / "manifest.json").read_text())
    for entry in originals["profiles"] + originals["reviews"]:
        path = ROOT / "incident-conversations" / entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
    disposition = data["original_review_disposition"]
    assert disposition["original"] == "review/INC-02.json"
    assert disposition["original_sha256"] == next(x["sha256"] for x in originals["reviews"] if x["family"] == "INC-02")
    assert disposition["rewrite_historical_results"] is False


def test_measurement_pair_allows_valid_arithmetic_and_retains_unknown_occupancy() -> None:
    review = json.loads((BASE / "review" / "measurement.json").read_text())
    assert review["variants"]["waiters"]["expected_claims"]["occupancy_fraction"] is None
    assert review["variants"]["active"]["expected_claims"]["occupancy_fraction"] == 34 / 40
    assert review["variants"]["active"]["expected_claims"]["cause_established"] is False
    for variant in ("waiters", "active"):
        spec = catalog.load_scenario(ROOT / "scenarios" / f"incident-evidence-v2-measurement-{variant}.yaml")
        assert "34" in spec["prompt"] and "40" in spec["prompt"]
        assert "capacity" in spec["prompt"]
        assert spec["followups"]


def test_completion_is_not_first_exposure_and_negative_evidence_is_not_missing() -> None:
    rollout = json.loads((BASE / "review" / "rollout.json").read_text())["variants"]
    assert rollout["completion"]["expected_claims"]["rollout_excluded_as_initiator"] is False
    assert rollout["first-exposure"]["expected_claims"]["rollout_excluded_as_initiator"] is True
    readback = json.loads((BASE / "review" / "readback.json").read_text())["variants"]
    assert readback["missing"]["expected_claims"]["readback_performed"] == "unknown"
    assert readback["negative"]["expected_claims"]["readback_performed"] == "reported_no"


def test_population_and_recovery_controls_change_only_supported_state() -> None:
    population = json.loads((BASE / "review" / "population.json").read_text())["variants"]
    assert population["one"]["expected_claims"]["fleet_observed_at"] == "10:10"
    assert population["all"]["expected_claims"]["fleet_observed_at"] == "10:13"
    recovery = json.loads((BASE / "review" / "recovery.json").read_text())["variants"]
    assert recovery["sustained"]["expected_claims"]["recovery_established"] is True
    assert recovery["incomplete"]["expected_claims"]["recovery_established"] is False
    assert all(v["expected_claims"]["mitigation_caused_recovery"] == "unknown" for v in recovery.values())


def test_controls_include_rejection_and_unavailable_examples_without_an_auto_semantic_judge() -> None:
    paths = list((BASE / "review").glob("*.json"))
    assert len(paths) == 6
    for path in paths:
        review = json.loads(path.read_text())
        for variant in review["variants"].values():
            controls = variant["controls"]
            assert set(controls) == {"acceptable", "unacceptable", "unavailable"}
            assert len(set(controls.values())) == 3
            assert variant["expected_claims"]


def test_role_probes_pin_sre_and_keep_advisor_discovery_unpinned() -> None:
    for caller in ("direct", "delegated"):
        spec = catalog.load_scenario(ROOT / "scenarios" / f"incident-evidence-v2-role-sre-{caller}.yaml")
        assert spec["agent"] == "sre-assistant"
        assert "routing" not in spec
        checks = {c["check"]: c for c in spec["checks"]}
        assert checks["skill_loaded"]["skill"] == "root-cause"
        assert checks["skill_not_loaded"]["skill"] == "incident-investigation"
    drill = catalog.load_scenario(ROOT / "scenarios" / "incident-evidence-v2-role-advisor-drill.yaml")
    assert "agent" not in drill and "skill" not in drill
    assert drill["routing"]["expect"] == "fire"
    explicit = catalog.load_scenario(ROOT / "scenarios" / "incident-evidence-v2-role-advisor-explicit.yaml")
    assert "agent" not in explicit and "routing" not in explicit
    assert explicit["skill"] == "incident-investigation"


def test_reserved_qualification_binds_sources_reviews_and_separate_selection() -> None:
    base = ROOT / "incident-conversations" / "qualification-v1"
    data = json.loads((base / "manifest.json").read_text())
    assert data["partition"] == "held-out"
    assert len(data["reserved_candidate_plugin_sha256"]) == 64
    assert len(data["profiles"]) == 4
    selection = json.loads((base / "report-selection.json").read_text())
    selected = {x["instance_id"]: x["case_sha256"] for x in selection["tasks"]}
    for entry in data["profiles"]:
        path = ROOT.parent / entry["path"]
        review = ROOT.parent / entry["review_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        assert hashlib.sha256(review.read_bytes()).hexdigest() == entry["review_sha256"]
        spec = yaml.safe_load(path.read_text())
        assert catalog.validate_scenario(spec) == []
        assert fingerprints.case_digest(spec) == entry["case_sha256"] == selected[spec["id"]]
        assert spec["conversation"]["partition"] == "held-out"
        assert spec["conversation"]["manual_review"] == "pending"
        assert len(spec["followups"]) == 1
        assert not spec.get("graders") and not spec["conversation"].get("turn_graders")
        released = spec["prompt"] + json.dumps(spec["fixture"])
        assert entry["review_path"] not in released and "expected_claims" not in released
