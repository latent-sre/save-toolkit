"""A disposable native fixture must contain evidence only and keep semantics unavailable."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
import yaml
from itbench_adapter import collect_submission, prepare_ground_truth, prepare_native
from itbench_testkit import diagnosis, manifest
from probe.catalog import validate_scenario
from probe.checking import check_command_exit_zero
from probe.outcomes import State
from probe.workspaces import Workspace
from probe_testkit import context


def test_native_prep_is_bounded_observed_only_and_validates_existing_runner_contract(tmp_path: Path) -> None:
    source = tmp_path / "cache"
    m = manifest(source)
    destination = tmp_path / "runner-fixtures"
    receipt = prepare_native(m, source, destination, max_prepared_bytes=1_000_000)
    assert len(receipt["scenarios"]) == 5
    assert receipt["live_execution"] is False
    for item in receipt["scenarios"]:
        p = destination / item["path"]
        spec = yaml.safe_load(p.read_text())
        assert validate_scenario(spec, where=str(p)) == []
        assert spec["tools"] == ["Read", "Grep", "Glob", "Skill"]
        assert spec["agent"] == "sre-assistant"
        assert set(spec["fixture"]["files"]) == {"k8s_events_raw.tsv"}
        serialized = p.read_text()
        assert "ANSWER_CANARY" not in serialized
        assert "recommended_actions" not in serialized
        assert "ground_truth.yaml" not in serialized
        assert "aliases" not in serialized
        assert spec["checks"][-1]["inconclusive_exit_code"] == 2


def test_prep_refuses_before_output_when_raw_budget_too_small(tmp_path: Path) -> None:
    source = tmp_path / "cache"
    m = manifest(source)
    with pytest.raises(ValueError, match="budget"):
        prepare_native(m, source, tmp_path / "fixtures", max_prepared_bytes=1)
    assert not (tmp_path / "fixtures").exists()


def test_collect_preserves_claims_and_rejects_case_mismatch_or_ambiguity() -> None:
    d = diagnosis()
    response = "Returning to: human requester\n```json\n" + json.dumps(d) + "\n```\nCaller next step: review."
    assert collect_submission(response, "wp04-24") == d
    with pytest.raises(ValueError, match="case"):
        collect_submission(response, "wp04-29")
    with pytest.raises(ValueError, match="one"):
        collect_submission(response + "\n```json\n" + json.dumps(d) + "\n```", "wp04-24")


def test_native_manual_check_is_unavailable_and_missing_interpreter_is_instrument_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "cache"
    m = manifest(source)
    dest = tmp_path / "prepared"
    prepare_native(m, source, dest, max_prepared_bytes=1_000_000)
    spec = yaml.safe_load((dest / "wp04-itbench-24.yaml").read_text())
    check = spec["checks"][-1]
    ws = Workspace(tmp_path, tmp_path, tmp_path / "bin", tmp_path / "state", 0, "main")
    ctx = context(spec, ws=ws)
    monkeypatch.setenv("PATH", str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""))
    outcome = check_command_exit_zero(ctx, check)
    assert outcome.state == State.INCONCLUSIVE
    assert outcome.machinery is False
    missing = {**check, "command": 'wp04-no-such-interpreter -c "raise SystemExit(2)"'}
    outcome = check_command_exit_zero(ctx, missing)
    assert outcome.state == State.INCONCLUSIVE
    assert outcome.machinery is True


def test_upstream_ground_truth_projection_preserves_source_entities_edges_and_aliases(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = manifest(source)
    raw_truth = {
        "groups": [{"id": "original-root", "kind": "JVMChaos", "root_cause": True}],
        "fault": [{"entity": {"kind": "Service", "group_id": "original-root"}}],
        "propagations": [{"source": "original-root", "target": "dangling-original"}],
        "aliases": [["original-root", "original-alias"]],
    }
    originals = {}
    for case in m["cases"]:
        body = (
            {"apiVersion": "itbench.io/v1", "kind": "GroundTruth", "spec": raw_truth}
            if case["source_id"] == "Scenario-102"
            else raw_truth
        )
        p = source / case["source_id"] / "ground_truth.yaml"
        p.write_text(yaml.safe_dump(body))
        originals[case["source_id"]] = p.read_bytes()
        case["hidden"][0].update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), size=p.stat().st_size)
    result = prepare_ground_truth(m, source)
    assert len(result["ground_truths"]) == 5
    assert {v["id"] for v in result["ground_truths"]} == {"7", "21", "24", "80", "102"}
    for value in result["ground_truths"]:
        assert {k: v for k, v in value.items() if k != "id"} == raw_truth
    assert result["receipt"]["wrapper_unwrapped"] == ["Scenario-102"]
    assert all((source / case / "ground_truth.yaml").read_bytes() == data for case, data in originals.items())


def test_upstream_truth_preparation_rejects_tampered_hidden_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = manifest(source)
    (source / m["cases"][0]["source_id"] / "ground_truth.yaml").write_text("changed answer")
    with pytest.raises(ValueError, match="mismatch"):
        prepare_ground_truth(m, source)


def test_native_prompt_describes_actual_per_case_log_availability(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = manifest(source)
    case = next(c for c in m["cases"] if c["id"] == "wp04-7")
    log = source / "Scenario-7" / "otel_logs_raw.tsv"
    log.write_text("Timestamp\tBody\n2025-12-15 18:00:00\tobserved application event\n")
    case["observables"].append(
        {
            "path": "otel_logs_raw.tsv",
            "sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            "size": log.stat().st_size,
        }
    )
    prepare_native(m, source, tmp_path / "native", max_prepared_bytes=1_000_000)
    with_logs = yaml.safe_load((tmp_path / "native/wp04-itbench-7.yaml").read_text())
    without_logs = yaml.safe_load((tmp_path / "native/wp04-itbench-24.yaml").read_text())
    assert "Application logs are supplied" in with_logs["prompt"]
    assert "Application logs are unavailable" in without_logs["prompt"]
    assert "Traces and metrics are unavailable" in with_logs["prompt"]
