"""Portable review packet integrity; no assertion measures reviewer calibration."""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
BASE = REPO / "evals" / "incident-conversations" / "review-v2"


def read_json(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def packet() -> dict[str, Any]:
    return read_json(BASE / "packet.json")


def test_packet_has_valid_strict_schema() -> None:
    schema = read_json(BASE / "schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(packet(), schema)


@pytest.mark.parametrize("mutation", ["unknown_status", "missing_source_hash", "extra_field"])
def test_schema_rejects_invalid_review_records(mutation: str) -> None:
    data = copy.deepcopy(packet())
    if mutation == "unknown_status":
        data["control_sets"][0]["cases"][0]["status"] = "calibrated"
    elif mutation == "missing_source_hash":
        del data["sources"][0]["source_sha256"]
    else:
        data["reassessments"][0]["accepted"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, read_json(BASE / "schema.json"))


def test_source_excerpts_are_bound_and_portable() -> None:
    """Private originals are provenance pointers, never required runtime dependencies."""
    data = packet()
    ids = [entry["id"] for entry in data["sources"]]
    assert len(ids) == len(set(ids))
    for entry in data["sources"]:
        excerpt = entry["excerpt"].encode("utf-8")
        assert digest(excerpt) == entry["excerpt_sha256"]
        assert entry["line_start"] <= entry["line_end"]
        assert len(excerpt.splitlines()) == entry["line_end"] - entry["line_start"] + 1
        path = Path(entry["original_path"])
        assert not path.is_absolute() and ".." not in path.parts
        assert "qualification-v1" not in str(path)
        if entry["availability"] == "private_historical":
            assert path.parts[0] == ".eval-runs"
            continue
        assert path.parts[0] == "evals"
        original = (REPO / path).read_bytes()
        assert digest(original) == entry["source_sha256"]
        lines = original.splitlines(keepends=True)
        assert b"".join(lines[entry["line_start"] - 1 : entry["line_end"]]) == excerpt
    for record in data["control_sets"] + data["reassessments"]:
        assert set(record["source_refs"]) <= set(ids)
    for record in data["reassessments"]:
        components = record["reply_refs"] + record["then_visible_refs"] + record["historical_review_refs"]
        assert set(components) <= set(record["source_refs"])
        assert not set(record["then_visible_refs"]) & set(record["reply_refs"] + record["historical_review_refs"])


def test_original_manifests_profiles_and_reviews_remain_byte_identical() -> None:
    for binding in packet()["historical_bindings"]:
        path = REPO / binding["path"]
        assert digest(path.read_bytes()) == binding["sha256"]
        if path.name != "manifest.json":
            continue
        manifest = read_json(path)
        for entry in manifest["profiles"] + manifest.get("reviews", []):
            assert "qualification-v1" not in entry["path"]
            assert digest((path.parent / entry["path"]).read_bytes()) == entry["sha256"]
            if "review_path" in entry:
                assert digest((path.parent / entry["review_path"]).read_bytes()) == entry["review_sha256"]


def test_contrasts_share_inputs_and_change_only_the_declared_response_span() -> None:
    """Mechanical contrast isolation; correctness of the labels still needs humans."""
    for group in packet()["control_sets"]:
        contexts = group["then_visible_inputs"]
        cases = {case["id"]: case for case in group["cases"]}
        assert len(cases) == len(group["cases"])
        assert len({case["response"] for case in cases.values()}) == len(cases)
        assert {case["input_id"] for case in cases.values()} <= set(contexts)
        for contrast in group["contrasts"]:
            left, right = cases[contrast["base"]], cases[contrast["changed"]]
            assert left["input_id"] == right["input_id"]
            before, after = contrast["before"], contrast["after"]
            assert before != after and left["response"].count(before) == 1
            assert left["response"].replace(before, after, 1) == right["response"]
            assert contrast["dimension"] == group["dimension"]
        negatives = {case["id"] for case in cases.values() if case["status"] == "violated"}
        assert negatives == {contrast["changed"] for contrast in group["contrasts"]}
        assert all(len(cases[key]["errors"]) == 1 for key in negatives)
        assert all(not case["errors"] for case in cases.values() if case["status"] != "violated")


def test_reused_scenarios_remain_separate_from_review_material() -> None:
    data = packet()
    forbidden = ["review-v2", "expected_status", "control_sets", "reassessments"]
    forbidden.extend(case["response"] for group in data["control_sets"] for case in group["cases"])
    for reference in data["reused_diagnostics"]:
        path = REPO / reference["path"]
        assert digest(path.read_bytes()) == reference["sha256"]
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert spec["id"] == reference["id"]
        candidate_context = json.dumps([spec["prompt"], spec.get("fixture", {}), spec.get("followups", [])])
        assert not any(value in candidate_context for value in forbidden)
    assert not list(BASE.glob("*.yaml"))
    assert not (BASE / "report-selection.json").exists()


def test_judgment_and_calibration_state_cannot_be_confused_with_measurement() -> None:
    data = packet()
    assert data["status"] == "AI_PROPOSAL"
    assert data["human_acceptance"] == data["reviewer_calibration"] == "UNMEASURED"
    assert data["model_calls"] == 0
    assert data["candidate_acceptance"] == "UNCHANGED"
    assert data["rewrite_historical_results"] is False
    assert all(item["judgment_status"] == "AI_PROPOSAL" for item in data["reassessments"])
    assert all(item["human_acceptance"] == "UNMEASURED" for item in data["reassessments"])
