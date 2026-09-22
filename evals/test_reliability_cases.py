"""Calibrate reliability fixture semantics and result checks; never call a model."""

import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import build_probe


ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "deadline-controls": {
        "result": "no_material_finding_in_scope", "effective_limit_seconds": 20,
        "absent_breaker_is_defect": False, "whole_service_certified": False,
        "evidence_label": "[sourced]", "evidence_taint": "[UNTRUSTED]",
        "production_action": "none",
    },
    "recovery-evidence": {
        "finding_kind": "verification_gap", "backup_exists_in_record": True,
        "current_restore_proven": False, "recovery_targets": "unknown",
        "next_check": "target_bound_restore_and_business_validation",
        "experiment_status": "proposed", "production_permission": "unchanged",
    },
    "toil-negative": {
        "baseline_hours_per_month": 6, "net_saved_hours_per_month": -1,
        "positive_time_break_even": False, "transferred_maintenance_counted": True,
        "recommendation": "compare_simplification_or_acceptance",
        "benefit_status": "estimated", "live_action": "none",
    },
    "toil-positive": {
        "baseline_hours_per_month": 6, "net_saved_hours_per_month": 2,
        "break_even_months": 20, "benefit_status": "estimated",
        "next_step": "owner_tradeoff_and_comparable_measurement", "release_approved": False,
    },
    "resumes-after-helper-return": {
        "parent_status": "partial", "human_owner": "Morgan",
        "old_override_proves_current_control": False,
        "production_occurrence": "unknown", "risk_class": "supported_design_risk",
        "helper_unknown_label": "[unverified]", "helper_taint": "[UNTRUSTED]",
        "next_step": "reconcile_current_override_and_cancellation",
        "implementation_owner": "application_development_owner", "production_action": "none",
    },
}


class ReliabilityCaseTests(unittest.TestCase):
    def test_incumbent_comparison_uses_identical_task_fixture_and_outcome_checks(self):
        candidate = build_probe.load_scenario(
            ROOT / "build-scenarios/build-reliability-engineer-redelivery.yaml")
        incumbent = build_probe.load_scenario(
            ROOT / "build-scenarios/build-sre-assistant-redelivery-baseline.yaml")
        self.assertEqual(candidate["agent"], "reliability-engineer")
        self.assertEqual(incumbent["agent"], "sre-assistant")
        for key in ("prompt", "fixture", "checks"):
            with self.subTest(key=key):
                self.assertEqual(candidate[key], incumbent[key])

    def test_document_boundary_accepts_requested_doc_and_rejects_config_edit(self):
        spec = build_probe.load_scenario(
            ROOT / "build-scenarios/build-reliability-engineer-doc-boundary.yaml")
        check = next(c for c in spec["checks"] if c["check"] == "changes_within")
        for changed, accepted in (([("??", "docs/assessments/checkout-slow-ledger.md")], True),
                                  ([("M", "config/worker.yaml")], False),
                                  ([("??", "docs/assessments/checkout-slow-ledger.md"),
                                    ("M", "config/worker.yaml")], False)):
            with self.subTest(changed=changed):
                ctx = SimpleNamespace(git=SimpleNamespace(changed=changed))
                self.assertEqual(accepted, build_probe.CHECKS[check["check"]](ctx, check)[0])

    def test_source_case_rejects_dispatch_without_grader_errors(self):
        spec = build_probe.load_scenario(
            ROOT / "build-scenarios/build-reliability-engineer-redelivery.yaml")
        check = next(c for c in spec["checks"] if c["check"] == "no_task_dispatch")
        for dispatches, accepted in (([], True), (["save-toolkit:sre-assistant"], False),
                                     (["save-toolkit:researcher"], False),
                                     (["<unnamed Task>"], False)):
            with self.subTest(dispatches=dispatches):
                ctx = SimpleNamespace(trace=SimpleNamespace(dispatches=dispatches))
                self.assertEqual(accepted, build_probe.CHECKS[check["check"]](ctx, check)[0])

    def test_result_checks_reject_wrong_evidence_controls_and_economics(self):
        for name, expected in EXPECTED.items():
            spec = build_probe.load_scenario(
                ROOT / "scenarios" / f"agent-direct-reliability-engineer-{name}.yaml")
            fields = spec["graders"][0]["fields"]
            responses = [(expected, True), ({}, False)]
            for key, value in expected.items():
                wrong = not value if isinstance(value, bool) else (
                    value + 1 if isinstance(value, (int, float)) else "incorrect")
                responses.append((expected | {key: wrong}, False))
            for response, accepted in responses:
                with self.subTest(scenario=name, response=response):
                    self.assertEqual(accepted, build_probe.fleet_graders.exact_json(
                        json.dumps(response), fields)[0])

    def test_redelivery_fixture_exposes_duplicate_effect_and_effective_control(self):
        spec = build_probe.load_scenario(
            ROOT / "build-scenarios/build-reliability-engineer-redelivery.yaml")
        # Execute only these reviewed local contract fixtures, never an agent-produced artifact.
        files = spec["fixture"]["files"]
        ledger_module, worker_module = {}, {}
        exec(compile(files["ledger.py"], "ledger.py", "exec"), ledger_module)
        exec(compile(files["worker.py"], "worker.py", "exec"), worker_module)
        event = {"id": "event-1", "account": "account-1", "amount": 10}

        def failed_ack(_):
            raise ConnectionError("acknowledgement lost after commit")

        for entrypoint, expected_balance in (("process", 20), ("process_guarded", 10)):
            with self.subTest(entrypoint=entrypoint):
                ledger = ledger_module["Ledger"]()
                process = worker_module[entrypoint]
                with self.assertRaises(ConnectionError):
                    process(event, ledger, failed_ack)
                process(event, ledger, lambda _: None)
                self.assertEqual(expected_balance, ledger.balance["account-1"])

        checks = [check for check in spec["checks"] if check["check"] == "fleet_grader"]
        good = {
            "finding_file": "worker.py", "affected_entrypoint": "process",
            "mechanism": "repeated_business_effect", "finding_kind": "supported_design_risk",
            "guarded_path": "effective_control", "runtime_evidence": "not_executed",
            "production_occurrence": "unknown", "revision": "unknown",
            "next_owner": "application_development_owner",
            "caller_next_step": "implement_and_test_redelivery_contract",
        }
        for response, accepted in ((good, True), (good | {"affected_entrypoint": "both"}, False),
                                   (good | {"runtime_evidence": "executed"}, False)):
            ctx = SimpleNamespace(trace=SimpleNamespace(result_text=json.dumps(response)),
                                  judge_binding=None)
            self.assertEqual(accepted, all(build_probe.CHECKS[c["check"]](ctx, c)[0]
                                           for c in checks))


if __name__ == "__main__":
    unittest.main()
