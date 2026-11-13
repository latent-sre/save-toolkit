"""Offline contracts for separating evidence extraction from interpretation, not model accuracy."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import graders
import pytest
import yaml
from probe import catalog, fingerprints

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "evidence-isolation" / "v1"


def load_pack() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = json.loads((PACK / "manifest.json").read_text())
    cases = {entry["arm"]: yaml.safe_load((ROOT.parent / entry["path"]).read_text()) for entry in manifest["profiles"]}
    return manifest, cases


def test_all_arms_are_bound_and_do_not_publish_review_answers() -> None:
    manifest, cases = load_pack()
    assert set(cases) == {"retrieval", "interpretation-direct", "interpretation-files"}
    assert manifest["partition"] == "development"
    assert manifest["human_calibration"] == "unmeasured"
    selection = json.loads((PACK / "report-selection.json").read_text())
    slots = {x["instance_id"]: x["case_sha256"] for x in selection["tasks"]}
    for entry in manifest["profiles"]:
        spec = cases[entry["arm"]]
        assert catalog.validate_scenario(spec) == []
        assert hashlib.sha256((ROOT.parent / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
        assert fingerprints.case_digest(spec) == entry["case_sha256"] == slots[spec["id"]]
        assert spec["agent"] == "sre-assistant"
        candidate = spec["prompt"] + json.dumps(spec["fixture"])
        assert "expected_claims" not in candidate
        assert "review.json" not in candidate
        assert "NOT_ACCEPTED" not in candidate
    for entry in manifest["artifacts"]:
        assert hashlib.sha256((PACK / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]


def test_interpretation_arms_change_only_direct_availability_of_identical_facts() -> None:
    _, cases = load_pack()
    direct, files = cases["interpretation-direct"], cases["interpretation-files"]
    facts = (PACK / "records.json").read_text()
    assert all(case["fixture"] == {"files": {"records.json": facts}} for case in cases.values())
    assert direct["prompt"] == files["prompt"] + "\n\nThe same released records are also supplied directly:\n```json\n" + facts + "```\n"
    lhs, rhs = copy.deepcopy(direct), copy.deepcopy(files)
    for spec in (lhs, rhs):
        spec.pop("id")
        spec.pop("prompt")
    assert lhs == rhs
    observations = {row["id"]: row for row in json.loads(facts)["observations"]}
    assert set(observations) == {"before", "after", "exposure", "listener", "alert", "workload"}
    assert observations["before"]["resource"] == observations["after"]["resource"]
    assert observations["before"]["uid"] == observations["after"]["uid"]
    assert observations["before"]["endpoint"] == "broker:9092"
    assert observations["after"]["endpoint"] == "broker:9999"
    assert observations["listener"]["port"] == 9092
    assert observations["alert"]["onset_at"] < observations["exposure"]["first_exposure_at"]


@pytest.mark.parametrize("damage", [None, "wrong-endpoint", "coerced-port", "scope", "extra"])
def test_retrieval_grade_rejects_value_type_and_scope_errors(damage: str | None) -> None:
    _, cases = load_pack()
    grader = next(c for c in cases["retrieval"]["checks"] if c["check"] == "fleet_grader")
    answer = copy.deepcopy(grader["fields"])
    if damage == "wrong-endpoint":
        answer["after_endpoint"] = "broker:9092"
    elif damage == "coerced-port":
        answer["listener_port"] = "9092"
    elif damage == "scope":
        answer["resource"] = "demo/Deployment/other"
    elif damage == "extra":
        answer["cause_proven"] = True
    passed, _ = graders.exact_json(json.dumps(answer), grader["fields"])
    assert passed is (damage is None)


def test_interpretation_requires_manual_review_and_future_run_is_not_authorized() -> None:
    _, cases = load_pack()
    for name in ("interpretation-direct", "interpretation-files"):
        manual = cases[name]["checks"][-1]
        assert manual["check"] == "command_exit_zero"
        assert manual["command"] == 'python -c "raise SystemExit(2)"'
        assert manual["inconclusive_exit_code"] == 2
    review = json.loads((PACK / "review.json").read_text())
    assert review["status"] == "NOT_ACCEPTED; AI-authored controls, human calibration unmeasured"
    assert review["expected_claims"]["current_configuration_mismatch"] is True
    assert review["expected_claims"]["mismatch_proven_cause_of_exit"] is False
    assert review["expected_claims"]["specific_change_initiated_earlier_alert"] is False
    assert review["expected_claims"]["sustained_user_recovery"] == "unknown"
    assert {x["changed_dimension"] for x in review["controls"]} >= {"none", "causal_certainty", "temporal_order", "blanket_uncertainty"}
    plan = json.loads((PACK / "run-plan.json").read_text())
    assert plan["approved_trials"] == 0 and plan["approved_spend_usd"] == 0
    assert plan["candidate_plugin_sha256"] is None and plan["model"] is None
    assert plan["automatic_retries"] == 0
