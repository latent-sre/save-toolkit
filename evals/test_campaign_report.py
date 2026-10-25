"""Read real v1 records through the report's public API; never run an evaluator."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import campaign_report
import pytest
from probe.records import RecordV1
from swebench_adapter import artifacts

BASE = Path(__file__).parent / "fixtures/v1-bundle/runs/eval-synthetic-gain/incumbent/run-1/record.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def attempt(bundle, case="good", *, slot=1, number=1, state="final", verdict="PASS", ending="completed", hidden=False):
    label = bundle / f"eval-{case}" / "claude"
    folder = label / (f".run-{slot}-attempt-offline" if hidden else f"run-{slot}" if state == "final" else f"attempts/run-{slot}/{number}")
    value = json.loads(BASE.read_text())
    value["case"]["id"] = case
    value["conditions"]["execution_profile"] = {"name": "offline", "authentication": "synthetic"}
    value["attempt"].update(label="claude", slot=slot, number=number, state=state)
    value["verdict"]["status"] = verdict
    value["checks"][0]["state"] = verdict or "INCONCLUSIVE"
    value["checks"][0]["reason"] = "unavailable" if verdict in (None, "INCONCLUSIVE") else None
    value["run_end"].update(kind=ending, stop="spend_guard" if ending == "cut_short" else None)
    if state == "incomplete":
        value["run_end"].update(kind="incomplete", stop=None)
        value["verdict"]["status"] = None
    value = RecordV1.model_validate_json(json.dumps(value)).model_dump(mode="json")
    dump(folder / "record.json", value)
    (folder / "outputs").mkdir(exist_ok=True)
    (folder / "outputs/response.md").write_text("synthetic response")
    return folder, value


def selection(*cases, **extra):
    return {"schema_version": 1, "tasks": [{"instance_id": case} for case in cases], **extra}


def test_coverage_kept_attempts_original_verdict_and_independent_dimensions(tmp_path):
    folder, value = attempt(tmp_path)
    dump(folder / "billing.json", {"before": {"usage": 2.0}, "after": {"usage": 2.4}, "measured_usd": 0.4, "complete": True})
    dump(folder / "cleanup.json", [{"kind": "container", "present": True, "removed": False}])
    dump(folder / "policy-review.json", {"status": "unreviewed"})
    dump(folder / "verifier/verifier-receipt.json", {"outcome": "PASS", "instance_id": "good"})
    value["assessments"] = [{"revision": 1, "status": "FAIL", "reason": None, "grading": "assessments/1/grading.json", "runner_source_sha256": "f" * 64, "assessed_at": "2026-10-01T00:01:00Z"}]
    dump(folder / "record.json", value)
    dump(folder / "assessments/1/grading.json", {})
    attempt(tmp_path, "failed", verdict="FAIL")
    attempt(tmp_path, "unknown", verdict="INCONCLUSIVE")
    kept, _ = attempt(tmp_path, number=2, state="incomplete")
    dump(kept / "billing.json", {"before": None, "after": None, "measured_usd": None, "complete": False})
    report = campaign_report.build_report(tmp_path, selection("good", "failed", "unknown", "missing"), "claude")
    assert report["counts"] == {"selected_cases": 4, "expected_slots": 4, "started_slots": 3, "completed_slots": 3, "recorded_verdicts": 3, "measured_slots": 2, "missing_slots": 1, "invalid_slots": 0, "failures_to_measure_slots": 2, "kept_attempts": 1, "incomplete_attempts": 1}
    row = report["cases"]["good"]["slots"][0]
    final = row["attempts"][0]
    assert final["verdict"]["status"] == "PASS"
    assert final["assessments"][0]["status"] == "FAIL"
    assert final["dimensions"]["independent_verifier"]["outcome"] == "PASS"
    assert final["dimensions"]["cleanup"]["status"] == "unresolved"
    assert final["dimensions"]["policy_review"]["status"] == "unreviewed"
    assert report["human_acceptance"] == report["key_disablement"] == "unknown"
    assert report["cost"]["provider_measured_usd"] == {"known_usd": 0.4, "unknown_attempts": 3, "complete": False}
    assert report["cost"]["cli_estimated_usd"]["known_usd"] == 0.4
    assert row["measured"] is True


@pytest.mark.parametrize("damage", ["missing-record", "malformed", "unsupported", "case", "evidence-missing", "evidence-escape", "evidence-symlink", "record-symlink", "billing", "binding", "identity"])
def test_broken_evidence_is_visible_and_never_a_measured_pass(tmp_path, damage):
    folder, value = attempt(tmp_path)
    if damage == "missing-record":
        (folder / "record.json").unlink()
    elif damage == "malformed":
        (folder / "record.json").write_text("{")
    elif damage == "unsupported":
        value["format"]["version"] = 2
        dump(folder / "record.json", value)
    elif damage == "case":
        value["case"]["id"] = "copied"
        dump(folder / "record.json", value)
    elif damage.startswith("evidence"):
        response = folder / "outputs/response.md"
        response.unlink()
        if damage == "evidence-escape":
            value["evidence"]["outputs/response.md"] = "../../outside"
            dump(folder / "record.json", value)
        if damage == "evidence-symlink":
            response.symlink_to(tmp_path / "outside")
            (tmp_path / "outside").write_text("must not read")
    elif damage == "record-symlink":
        (folder / "record.json").rename(tmp_path / "outside.json")
        (folder / "record.json").symlink_to(tmp_path / "outside.json")
    elif damage == "billing":
        dump(folder / "billing.json", {"before": {"usage": 0}, "after": {"usage": 1}, "measured_usd": -1, "complete": True})
    elif damage == "binding":
        dump(folder / "binding.json", {"selection_sha256": "a" * 64})
    elif damage == "identity":
        dump(folder / "identity.json", {"instance_id": "copied"})
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    assert report["counts"]["measured_slots"] == 0
    assert report["counts"]["invalid_slots"] == 1
    assert report["counts"]["started_slots"] == 1
    assert report["cases"]["good"]["slots"][0]["problems"]
    assert report["cost"]["provider_measured_usd"]["unknown_attempts"] == 1


def test_sidecar_binding_to_manifest_case_candidate_and_runtime(tmp_path):
    folder, value = attempt(tmp_path)
    manifest = selection("good", dataset="SWE-bench/SWE-bench_Verified", revision="e" * 40)
    identity = {"dataset": manifest["dataset"], "revision": manifest["revision"], "instance_id": "good", "base_commit": "f" * 40, "problem_statement_sha256": "a" * 64, "fail_to_pass_sha256": "b" * 64, "pass_to_pass_sha256": "c" * 64, "image_digest": "sha256:" + "d" * 64}
    value["case"]["case_sha256"] = digest(identity)
    dump(folder / "record.json", value)
    dump(folder / "identity.json", identity)
    binding = {"selection_sha256": digest(manifest), "plugin_sha256": value["candidate"]["plugin_source_sha256"], "adapter_sha256": value["runner"]["runner_source_sha256"], "cli_version": value["conditions"]["runtime"]["cli_version"], "model": value["conditions"]["requested_model"]}
    dump(folder / "binding.json", binding)
    assert campaign_report.build_report(tmp_path, manifest, "claude")["counts"]["measured_slots"] == 1
    binding["plugin_sha256"] = "9" * 64
    dump(folder / "binding.json", binding)
    assert campaign_report.build_report(tmp_path, manifest, "claude")["counts"]["measured_slots"] == 0


def test_duplicate_attempt_identity_and_unpublished_attempts_do_not_double_count_slots(tmp_path):
    attempt(tmp_path)
    attempt(tmp_path, number=1, state="superseded")
    hidden, _ = attempt(tmp_path, "interrupted", state="incomplete", hidden=True)
    (hidden / "record.json").unlink()
    report = campaign_report.build_report(tmp_path, selection("good", "interrupted"), "claude")
    assert report["counts"]["started_slots"] == 2
    assert report["counts"]["measured_slots"] == 0
    assert report["counts"]["invalid_slots"] == 2
    assert "duplicate" in str(report["cases"]["good"]["slots"][0]["problems"])
    assert len(report["cases"]["interrupted"]["slots"][0]["attempts"]) == 1


def test_budget_failure_stays_fail_while_execution_and_spend_are_independent(tmp_path):
    attempt(tmp_path, verdict="FAIL", ending="cut_short")
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    assert report["verdict_counts"] == {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 0}
    assert report["counts"]["completed_slots"] == 0
    assert report["counts"]["measured_slots"] == 1


def test_unknown_and_incompatible_identities_never_pool_and_relocation_is_stable(tmp_path):
    bundle = tmp_path / "one"
    for name in ("a", "b", "c", "d"):
        folder, value = attempt(bundle, name)
        if name == "b":
            value["conditions"]["observed_models"] = ["different-model"]
        if name in ("c", "d"):
            value["conditions"]["runtime"]["host_identity"] = None
        dump(folder / "record.json", value)
    manifest = selection("a", "b", "c", "d")
    before = {p.relative_to(bundle): p.read_bytes() for p in bundle.rglob("*") if p.is_file()}
    report = campaign_report.build_report(bundle, manifest, "claude")
    assert len(report["groups"]) == 4
    assert sum(group["identity_complete"] for group in report["groups"]) == 2
    moved = tmp_path / "moved"
    shutil.copytree(bundle, moved)
    assert campaign_report.build_report(moved, manifest, "claude") == report
    markdown = campaign_report.render_markdown(report)
    assert str(bundle) not in markdown
    assert "eval-a/claude/run-1/record.json" in markdown
    assert before == {p.relative_to(bundle): p.read_bytes() for p in bundle.rglob("*") if p.is_file()}


@pytest.mark.parametrize("amount", [True, "1", float("nan"), float("inf"), -0.1])
def test_invalid_provider_billing_never_means_zero(tmp_path, amount):
    folder, _ = attempt(tmp_path)
    dump(folder / "billing.json", {"before": {"usage": 0}, "after": {"usage": amount}, "measured_usd": amount, "complete": True})
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    assert report["cost"]["provider_measured_usd"] == {"known_usd": None, "unknown_attempts": 1, "complete": False}
    assert report["counts"]["invalid_slots"] == 1


def test_selection_duplicates_invalid_paths_and_extra_slots_remain_visible(tmp_path):
    attempt(tmp_path, slot=2)
    attempt(tmp_path, "unselected")
    report = campaign_report.build_report(tmp_path, selection("good", "good", "../escape"), "claude")
    assert report["selection"]["problems"]
    assert report["counts"]["selected_cases"] == 1
    assert report["counts"]["expected_slots"] == 1
    assert report["counts"]["missing_slots"] == 1
    assert "unselected" in report["unselected_cases"]


def test_cli_json_and_markdown_are_stdout_only(tmp_path):
    attempt(tmp_path)
    manifest = tmp_path / "selection.json"
    dump(manifest, selection("good"))
    command = [sys.executable, str(Path(campaign_report.__file__)), str(tmp_path), "--selection", str(manifest), "--label", "claude"]
    result = subprocess.run([*command, "--json"], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["counts"]["recorded_verdicts"] == 1
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "Provider-measured" in result.stdout
    assert "Human acceptance: unknown" in result.stdout


@pytest.mark.parametrize("sidecar", ["billing.json", "identity.json", "binding.json", "policy-review.json", "cleanup.json"])
def test_present_null_sidecars_are_invalid_evidence(tmp_path, sidecar):
    folder, _ = attempt(tmp_path)
    dump(folder / sidecar, None)
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    assert report["counts"]["invalid_slots"] == 1
    assert report["counts"]["measured_slots"] == 0


def test_malformed_record_still_accounts_for_known_provider_spend(tmp_path):
    folder, _ = attempt(tmp_path)
    dump(folder / "billing.json", {"before": {"usage": 2}, "after": {"usage": 2.7}, "measured_usd": 0.7, "complete": True})
    (folder / "record.json").write_text("{")
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    assert report["cost"]["provider_measured_usd"]["known_usd"] == 0.7
    assert report["counts"]["invalid_slots"] == 1


def test_symlinked_case_folder_is_reported_without_reading_target(tmp_path):
    outside = tmp_path / "outside"
    attempt(outside)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "eval-good").symlink_to(outside / "eval-good", target_is_directory=True)
    report = campaign_report.build_report(bundle, selection("good"), "claude")
    assert report["counts"]["invalid_slots"] == 1
    assert report["counts"]["measured_slots"] == 0
    assert report["cost"]["cli_estimated_usd"]["known_usd"] is None


def test_native_cleanup_receipt_stays_separate_from_original_verdict(tmp_path):
    folder, _ = attempt(tmp_path)
    dump(folder / "cleanup.json", {"removed": True, "retained": False})
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    assert report["cases"]["good"]["slots"][0]["attempts"][0]["dimensions"]["cleanup"]["status"] == "complete"


@pytest.mark.parametrize("damage", ["nonfinite-binding", "nonfinite-billing", "boolean-version"])
def test_malformed_numeric_values_do_not_crash_or_enter_valid_results(tmp_path, damage):
    folder, value = attempt(tmp_path)
    if damage == "boolean-version":
        value["format"]["version"] = True
        dump(folder / "record.json", value)
    else:
        dump(folder / ("binding.json" if damage.endswith("binding") else "billing.json"), {"untrusted": float("nan")})
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    assert report["counts"]["invalid_slots"] == 1
    json.dumps(report, allow_nan=False)


def test_current_wp08_artifact_writer_is_compatible_without_runner_or_host_calls(tmp_path):
    identity = {"dataset": "SWE-bench/SWE-bench_Verified", "revision": "e" * 40, "instance_id": "good", "base_commit": "f" * 40, "problem_statement_sha256": "a" * 64, "fail_to_pass_sha256": "b" * 64, "pass_to_pass_sha256": "c" * 64, "image_digest": "sha256:" + "d" * 64}
    folder, old = attempt(tmp_path)
    value = artifacts.make_record(identity=identity, candidate=old["candidate"], runner=old["runner"], model="offline-model", runtime=old["conditions"]["runtime"], label="claude", started=old["attempt"]["started_at"], ended=old["attempt"]["ended_at"], state="INCONCLUSIVE", reason="cleanup unresolved", ending="completed", stop=None, estimated_cost=0.12, evidence={"identity": "identity.json", "cleanup": "cleanup.json", "verifier": "verifier/verifier-receipt.json"})
    dump(folder / "record.json", value)
    dump(folder / "identity.json", identity)
    dump(folder / "cleanup.json", [{"present": True, "removed": False}])
    dump(folder / "verifier/verifier-receipt.json", {"instance_id": "good", "outcome": "PASS"})
    report = campaign_report.build_report(tmp_path, selection("good", dataset=identity["dataset"], revision=identity["revision"]), "claude")
    final = report["cases"]["good"]["slots"][0]["attempts"][0]
    assert final["verdict"]["status"] == "INCONCLUSIVE"
    assert final["dimensions"]["independent_verifier"]["outcome"] == "PASS"
    assert final["dimensions"]["cleanup"]["status"] == "unresolved"
    assert final["cli_estimated_usd"] == 0.12
    assert report["groups"][0]["identity"]["conditions"]["execution_profile"] == artifacts.PROFILE


def test_late_instrument_problem_stays_visible_without_erasing_supported_result(tmp_path):
    folder, value = attempt(tmp_path)
    value["verdict"]["after_assessment"] = "provider usage is unavailable after verification"
    dump(folder / "record.json", value)
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    row = report["cases"]["good"]["slots"][0]["attempts"][0]
    assert row["verdict"]["status"] == "PASS"
    assert row["verdict"]["after_assessment"] == value["verdict"]["after_assessment"]
    assert report["counts"]["measured_slots"] == 1
    assert value["verdict"]["after_assessment"] in campaign_report.render_markdown(report)


def test_native_conversation_semantics_remain_separate_from_structural_pass(tmp_path):
    folder, _value = attempt(tmp_path)
    dump(folder / "conversation.json", {"profile": "incident-v1", "invocations": 6})
    dump(folder / "outputs/trace-summary.json", {"semantic_assessment": "UNVERIFIED"})
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    row = report["cases"]["good"]["slots"][0]["attempts"][0]
    assert row["verdict"]["status"] == "PASS"
    assert row["dimensions"]["semantic_assessment"] == "UNVERIFIED"
    assert "semantic: UNVERIFIED" in campaign_report.render_markdown(report)


@pytest.mark.parametrize("trial,judge,floor,complete", [
    (0.1, None, 0.12, False),
    (0.1000004, 0.0200004, 0.120001, True),
    (None, None, 0.02, False),
])
def test_native_known_spend_floor_and_writer_rounding_are_preserved(tmp_path, trial, judge, floor, complete):
    folder, value = attempt(tmp_path)
    value["cost"].update(trial_usd=trial, judge_usd=judge, known_usd=floor, complete=complete,
                         judge_calls=2, judge_live_calls=2, judge_unknown_cost_calls=0 if complete else 1)
    dump(folder / "record.json", value)
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    assert report["counts"]["invalid_slots"] == 0
    assert report["counts"]["measured_slots"] == 1
    assert report["cost"]["cli_estimated_usd"] == {"known_usd": floor, "complete": complete,
                                                 "unknown_attempts": 0 if complete else 1}


def test_extra_trials_cannot_improve_selected_coverage_but_keep_their_cost(tmp_path):
    for slot in range(2, 11):
        attempt(tmp_path, slot=slot)
    report = campaign_report.build_report(tmp_path, selection("good"), "claude")
    assert report["counts"]["expected_slots"] == 1
    assert report["counts"]["measured_slots"] == 0
    assert report["counts"]["started_slots"] == 0
    assert report["counts"]["missing_slots"] == 1
    assert report["counts"]["recorded_verdicts"] == 0
    assert report["groups"] == []
    assert report["verdict_counts"]["PASS"] == 0
    assert len(report["cases"]["good"]["slots"]) == 10
    for slot in report["cases"]["good"]["slots"][1:]:
        assert slot["selected"] is False and slot["measured"] is False
        assert "unselected trial slot" in slot["problems"]
    assert report["cost"]["cli_estimated_usd"]["known_usd"] == 0.9
