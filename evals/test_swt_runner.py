"""Native author identity and report integration without model calls."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import campaign_report
import pytest
from probe.records import RecordV1
from swt_adapter import core, runner


def test_native_author_prompt_contains_no_hidden_fields():
    command = runner.author_command(
        {"model": "anthropic/claude-sonnet-5.5"},
        {"problem_statement": "VISIBLE ISSUE", "patch": "HIDDEN_CODE", "test_patch": "HIDDEN_TEST"},
    )
    assert "save-toolkit:software-engineer" in command
    assert "VISIBLE ISSUE" in command[command.index("-p") + 1]
    assert "HIDDEN" not in json.dumps(command)
    assert "static" in command[command.index("-p") + 1]
    assert command[command.index("--max-turns") + 1] == "64"


def approved_smoke(tmp_path, binding=None):
    binding = binding or {"instance_id": "org__repo-1", "task_sha256": "row"}
    checks = dict.fromkeys(runner.SMOKE_CHECKS, True)
    smoke = {
        "format": "wp09-swt-smoke",
        "schema_version": 1,
        "instance_id": binding["instance_id"],
        "binding": binding,
        "checks": checks,
        "error": None,
        "model_calls": 0,
        "cleanup": [{"present": False, "removed": True}],
        "observations": {},
    }
    for name in ("gold", "always-fail", "pass-both", "unrelated-import"):
        run_id = "wp09-smoke-" + name
        smoke["observations"][name] = {
            "supervisor": {
                "process_cleanup_complete": True,
                "run_id": run_id,
                "cleanup": [{"name": name, "removed": True} for name in runner.verifier.container_names(run_id)],
                "receipt_available": True,
                "stop": None,
                "exit_code": 0,
            },
            "verifier": {
                "instance_id": binding["instance_id"],
                "row_sha256": binding["task_sha256"],
                "mechanical": "PASS" if name == "gold" else "FAIL",
            },
        }
    smoke_path = tmp_path / "smoke.json"
    smoke_path.write_text(json.dumps(smoke))
    approval = {
        "accepted": True,
        "owner": "human",
        "binding": binding,
        "smoke": checks,
        "smoke_receipt": "smoke.json",
        "smoke_sha256": hashlib.sha256(smoke_path.read_bytes()).hexdigest(),
    }
    path = tmp_path / "admission.json"
    path.write_text(json.dumps(approval))
    return path, binding, smoke, approval


def test_live_admission_rejects_missing_or_stale_binding(tmp_path):
    path, binding, _, approval = approved_smoke(tmp_path)
    runner.require_admission(path, binding)
    with pytest.raises(ValueError, match="acceptance"):
        runner.require_admission(path, {**binding, "changed": True})
    approval.pop("smoke_receipt")
    path.write_text(json.dumps(approval))
    with pytest.raises(ValueError, match="smoke"):
        runner.require_admission(path, binding)


@pytest.mark.parametrize(
    "damage",
    [
        "delete",
        "mutate",
        "case",
        "binding",
        "error",
        "calls",
        "cleanup",
        "empty-cleanup",
        "worker-cleanup",
        "missing-control",
        "control-case",
        "control-row",
        "control-outcome",
        "checks",
        "escape",
        "symlink",
    ],
)
def test_admission_reopens_digest_bound_actual_smoke(tmp_path, damage):
    path, binding, smoke, approval = approved_smoke(tmp_path)
    smoke_path = tmp_path / "smoke.json"
    if damage == "delete":
        smoke_path.unlink()
    elif damage == "mutate":
        smoke_path.write_text("{}")
    elif damage == "escape":
        approval["smoke_receipt"] = "../smoke.json"
    elif damage == "symlink":
        smoke_path.rename(tmp_path / "real.json")
        smoke_path.symlink_to(tmp_path / "real.json")
    else:
        if damage == "case":
            smoke["instance_id"] = "other"
        if damage == "binding":
            smoke["binding"] = {"wrong": True}
        if damage == "error":
            smoke["error"] = "failure"
        if damage == "calls":
            smoke["model_calls"] = True
        if damage == "cleanup":
            smoke["cleanup"][0]["present"] = True
        if damage == "empty-cleanup":
            smoke["cleanup"] = []
        if damage == "worker-cleanup":
            smoke["observations"]["gold"]["supervisor"]["process_cleanup_complete"] = False
        if damage == "missing-control":
            del smoke["observations"]["always-fail"]
        if damage == "control-case":
            smoke["observations"]["gold"]["verifier"]["instance_id"] = "other"
        if damage == "control-row":
            smoke["observations"]["gold"]["verifier"]["row_sha256"] = "other"
        if damage == "control-outcome":
            smoke["observations"]["pass-both"]["verifier"]["mechanical"] = "INCONCLUSIVE"
        if damage == "checks":
            smoke["checks"]["storage_cap"] = False
        smoke_path.write_text(json.dumps(smoke))
        approval["smoke_sha256"] = hashlib.sha256(smoke_path.read_bytes()).hexdigest()
    path.write_text(json.dumps(approval))
    with pytest.raises(ValueError, match="smoke"):
        runner.require_admission(path, binding)


def test_combined_binding_keeps_shared_and_dependency_identity(tmp_path, monkeypatch):
    shared = {"adapter_sha256": "shared-v1", "host_runtime": {"identity": {"elevated": False}}}
    monkeypatch.setattr(runner, "runtime_binding", lambda *a: copy.deepcopy(shared))
    monkeypatch.setattr(runner, "adapter_digest", lambda: "swt")
    requirements = tmp_path / "requirements-swt.txt"
    requirements.write_text("dependency==1")
    monkeypatch.setattr(runner, "SWT_REQUIREMENTS", requirements)
    first = runner.live_binding({}, {}, {"instance_id": "org__repo-1"}, None)
    assert first["shared_adapter_sha256"] == "shared-v1"
    path, _, _, _ = approved_smoke(tmp_path, first)
    shared["adapter_sha256"] = "shared-v2"
    second = runner.live_binding({}, {}, {"instance_id": "org__repo-1"}, None)
    assert first["adapter_sha256"] != second["adapter_sha256"]
    with pytest.raises(ValueError):
        runner.require_admission(path, second)
    requirements.write_text("dependency==2")
    third = runner.live_binding({}, {}, {"instance_id": "org__repo-1"}, None)
    assert second["adapter_sha256"] != third["adapter_sha256"]
    with pytest.raises(ValueError):
        runner.require_admission(path, third)
    assert runner.bound_provenance(third)["runner_source_sha256"] == third["adapter_sha256"]


def test_v1_record_keeps_mechanical_and_human_relevance_separate(tmp_path):
    fixture = Path(__file__).parent / "fixtures/v1-bundle/runs/eval-synthetic-gain/incumbent/run-1/record.json"
    old = json.loads(fixture.read_text())
    author = {
        "candidate": old["candidate"],
        "runner": old["runner"],
        "model": "offline-model",
        "runtime": old["conditions"]["runtime"],
        "started": old["attempt"]["started_at"],
        "ended": old["attempt"]["ended_at"],
        "ending": "completed",
        "stop": None,
        "estimate": None,
    }
    verified = {
        "instance_id": "org__repo-1",
        "mechanical": "PASS",
        "verdict": "INCONCLUSIVE",
        "reason": "semantic relevance pending",
    }
    value = runner.make_record({"instance_id": "org__repo-1"}, author, verified, {})
    RecordV1.model_validate_json(json.dumps(value))
    assert value["verdict"]["status"] == "INCONCLUSIVE"
    assert value["checks"][0]["state"] == "PASS"
    assert value["checks"][1]["state"] == "INCONCLUSIVE"
    assert value["conditions"]["execution_profile"]["name"] == "static-tests-independently-verified-dec13"
    assert value["cost"]["known_usd"] is None


def test_campaign_report_consumes_swt_record_and_independent_dimensions(tmp_path):

    old = json.loads(
        (Path(__file__).parent / "fixtures/v1-bundle/runs/eval-synthetic-gain/incumbent/run-1/record.json").read_text()
    )
    author = {
        "candidate": old["candidate"],
        "runner": old["runner"],
        "model": "offline-model",
        "runtime": old["conditions"]["runtime"],
        "started": old["attempt"]["started_at"],
        "ended": old["attempt"]["ended_at"],
        "ending": "completed",
        "stop": None,
        "estimate": None,
    }
    verified = {
        "instance_id": "org__repo-1",
        "mechanical": "PASS",
        "verdict": "INCONCLUSIVE",
        "reason": "semantic relevance pending",
    }
    record = runner.make_record({"instance_id": "org__repo-1"}, author, verified, {})
    selection = {"schema_version": 1, "tasks": [{"instance_id": "org__repo-1"}]}
    run = tmp_path / "eval-org__repo-1/claude/run-1"
    run.mkdir(parents=True)
    (run / "record.json").write_text(json.dumps(record))
    (run / "binding.json").write_text(
        json.dumps(
            {"selection_sha256": core.digest(selection), "adapter_sha256": record["runner"]["runner_source_sha256"]}
        )
    )
    (run / "cleanup.json").write_text(json.dumps({"complete": False}))
    (run / "policy-review.json").write_text(json.dumps({"status": "unreviewed"}))
    (run / "verifier").mkdir()
    (run / "verifier/verifier-receipt.json").write_text(json.dumps({**verified, "outcome": "PASS"}))
    report = campaign_report.build_report(tmp_path, selection, "claude")
    attempt = report["cases"]["org__repo-1"]["slots"][0]["attempts"][0]
    assert attempt["valid"], attempt["problems"]
    assert attempt["verdict"]["status"] == "INCONCLUSIVE"
    assert attempt["dimensions"]["independent_verifier"]["outcome"] == "PASS"
    assert attempt["dimensions"]["cleanup"]["status"] == "unresolved"
    assert attempt["dimensions"]["policy_review"]["status"] == "unreviewed"


def test_missing_smoke_is_refused_before_key_or_container_setup(tmp_path, monkeypatch):
    path, binding, _, _ = approved_smoke(tmp_path)
    (tmp_path / "smoke.json").unlink()
    row = {"instance_id": binding["instance_id"]}
    monkeypatch.setattr(core, "select", lambda *args: [row])
    monkeypatch.setattr(runner.verifier, "check_source", lambda p: None)
    monkeypatch.setattr(runner.verifier, "runtime_problems", lambda: [])
    monkeypatch.setattr(runner, "live_binding", lambda *args: binding)
    monkeypatch.setattr(runner, "read_key", lambda *args: pytest.fail("key read before smoke proof"))
    monkeypatch.setattr(runner, "image_identity", lambda *args: pytest.fail("container setup before smoke proof"))
    with pytest.raises(ValueError, match="smoke"):
        runner.run_trial(
            {}, {}, [row], set(), row["instance_id"], tmp_path / "runs", tmp_path / "key", tmp_path / "source", path
        )
    assert not (tmp_path / "runs").exists()


def test_bound_provenance_flows_unchanged_into_record():
    old = json.loads(
        (Path(__file__).parent / "fixtures/v1-bundle/runs/eval-synthetic-gain/incumbent/run-1/record.json").read_text()
    )
    binding = {"adapter_sha256": "d" * 64}
    author = {
        "candidate": old["candidate"],
        "runner": runner.bound_provenance(binding),
        "model": "offline",
        "runtime": old["conditions"]["runtime"],
        "started": old["attempt"]["started_at"],
        "ended": old["attempt"]["ended_at"],
        "ending": "completed",
        "stop": None,
        "estimate": None,
    }
    record = runner.make_record(
        {"instance_id": "id"},
        author,
        {"verdict": "INCONCLUSIVE", "mechanical": "INCONCLUSIVE", "reason": "unavailable"},
        {},
    )
    assert record["runner"]["runner_source_sha256"] == binding["adapter_sha256"]


def test_trial_publishes_the_exact_accepted_binding(tmp_path, monkeypatch):
    old = json.loads(
        (Path(__file__).parent / "fixtures/v1-bundle/runs/eval-synthetic-gain/incumbent/run-1/record.json").read_text()
    )
    binding = {
        "instance_id": "org__repo-1",
        "task_sha256": "row",
        "adapter_sha256": "d" * 64,
        "shared_adapter_sha256": "a" * 64,
        "swt_requirements_sha256": "b" * 64,
    }
    admission, _, _, _ = approved_smoke(tmp_path, binding)
    row = {"instance_id": binding["instance_id"]}
    monkeypatch.setattr(core, "select", lambda *args: [row])
    monkeypatch.setattr(runner.verifier, "check_source", lambda p: None)
    monkeypatch.setattr(runner.verifier, "runtime_problems", lambda: [])
    monkeypatch.setattr(runner, "live_binding", lambda *args: copy.deepcopy(binding))
    monkeypatch.setattr(runner, "image_identity", lambda *args: "sha256:" + "f" * 64)
    monkeypatch.setattr(runner.fingerprints, "plugin_provenance", lambda *args: old["candidate"])

    class Resources:
        def __init__(self, *args):
            pass

        def cleanup(self):
            return [{"present": False, "removed": True}]

    def stopped_before_key(*args):
        raise RuntimeError("offline staging boundary")

    monkeypatch.setattr(runner, "DockerResources", Resources)
    monkeypatch.setattr(runner.fingerprints, "stage_plugin", stopped_before_key)
    monkeypatch.setattr(runner, "read_key", lambda *args: pytest.fail("model credential was read"))
    runner.run_trial(
        {"plugin_root": str(tmp_path), "model": "offline"},
        {},
        [row],
        set(),
        row["instance_id"],
        tmp_path / "runs",
        tmp_path / "key",
        tmp_path / "source",
        admission,
    )
    folder = tmp_path / "runs/eval-org__repo-1/claude/run-1"
    published = json.loads((folder / "binding.json").read_text())
    record = json.loads((folder / "record.json").read_text())
    assert published == binding
    assert record["runner"]["runner_source_sha256"] == binding["adapter_sha256"]


@pytest.mark.parametrize("elevated", [True, None, 0, "false"])
def test_live_binding_refuses_elevated_or_unknown_accounts_before_adapter_setup(monkeypatch, elevated):
    monkeypatch.setattr(runner, "runtime_binding", lambda *args: {
        "adapter_sha256": "shared", "host_runtime": {"identity": {"elevated": elevated}}})
    monkeypatch.setattr(runner, "adapter_digest", lambda: pytest.fail("unsafe host reached adapter setup"))
    with pytest.raises(ValueError, match="unelevated"):
        runner.live_binding({}, {}, {"instance_id": "org__repo-1"}, None)
