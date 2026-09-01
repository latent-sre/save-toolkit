"""Tests for normalized multi-engine evidence emitted from legacy runner records."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_contract
import eval_evidence
import execution_profiles


DIGEST = "a" * 64
TRACE = "b" * 64
CONTEXT = "c" * 64
POLICY = "d" * 64
REVISION = "e" * 40
SCENARIO = "agent-direct-sre-first-response-untriaged-alert"
REFERENCE = "skills/incident-investigation/references/first-response.md"
CANARY = "q_first_response_20260825"


class EvalEvidenceTests(unittest.TestCase):
    def test_framed_digest_binds_value_multiplicity(self) -> None:
        self.assertNotEqual(
            eval_evidence._framed_digest("traces", [TRACE]),
            eval_evidence._framed_digest("traces", [TRACE, TRACE]),
        )

    def _profile(self, engine: str = "codex-cli") -> execution_profiles.ExecutionProfile:
        claims = [
            "candidate_snapshot_integrity",
            "reference_used",
            "behavioral_contract",
            "deterministic_grader_result",
        ]
        if engine == "claude-plugin":
            claims[1:1] = [
                "native_plugin_loaded",
                "native_component_invoked",
                "advertised_tool_inventory",
                "callable_tool_boundary",
            ]
        return execution_profiles.validate_profile(
            {
                "schema_version": "eval-execution-profile/v1",
                "id": f"{engine.replace('_', '-')}-profile",
                "comparison": {
                    "id": "sre-first-response-v1",
                    "models": {
                        "claude-plugin": "sonnet",
                        "codex-cli": "gpt-5.6-terra",
                    },
                },
                "engine": engine,
                "claims": claims,
                "scenario_ids": [SCENARIO],
                "required_references": {SCENARIO: [REFERENCE]},
                "model": "gpt-5.6-terra" if engine == "codex-cli" else "sonnet",
                "trials": 2,
                "timeout_s": 180,
                "total_timeout_s": 360,
                "cost_budget": {
                    "status": "unavailable" if engine == "codex-cli" else "available",
                    "max_usd": None if engine == "codex-cli" else 5.0,
                },
                "approval": {
                    "approved_by": "owner",
                    "approved_at": "2026-08-26T12:00:00Z",
                    "budget_id": "budget-1",
                },
            }
        )

    def _provenance(self, engine: str) -> dict[str, object]:
        return {
            "run_id": "20260826T120000Z-abcdef12",
            "started_at": "2026-08-26T12:00:00+00:00",
            "engine": engine,
            "runtime_cli_version": "test-cli 1",
            "auth_mode": "subscriber_session",
            "requested_model": "gpt-5.6-terra" if engine == "codex-cli" else "sonnet",
            "plugin_commit": REVISION,
            "plugin_inputs_dirty": False,
            "plugin_source_sha256": DIGEST,
            "eval_suite_sha256": DIGEST,
        }

    def _results(self, *, observed: tuple[str, ...] = (CANARY,)) -> list[dict[str, object]]:
        trial = {
            "state": "PASS",
            "model_executed": True,
            "duration_seconds": 1.5,
            "resolved_model": "resolved-model",
            "total_cost_usd": None,
            "trace_sha256": TRACE,
            "context_sha256": CONTEXT,
            "policy_sha256": POLICY,
            "canaries": {"expected": [CANARY], "observed": list(observed)},
            "completed_invocations": {"skills": [], "agents": []},
        }
        return [{
            "id": SCENARIO,
            "mode": "direct",
            "target": {"kind": "agent", "name": "sre"},
            "scenario_sha256": DIGEST,
            "verdict": "PASS",
            "trials": [dict(trial), dict(trial)],
        }]

    def test_codex_envelope_is_valid_and_does_not_claim_native_plugin_evidence(self) -> None:
        envelope = eval_evidence.build_envelope(
            provenance=self._provenance("codex-cli"),
            profile=self._profile(),
            scenario_results=self._results(),
            reference_canaries={SCENARIO: {REFERENCE: CANARY}},
            grader_sha256=DIGEST,
            ended_at="2026-08-26T12:00:04Z",
        )

        engine_contract.validate_envelope(envelope)
        self.assertEqual(envelope["cost"]["status"], "unavailable")
        self.assertFalse(envelope["artifacts"]["plugin_snapshot"]["applicable"])
        emitted = {claim["type"] for claim in envelope["scenarios"][0]["claims"]}
        self.assertNotIn("native_plugin_loaded", emitted)
        self.assertFalse(envelope["promotion_eligible"])

    def test_dirty_provenance_cannot_emit_a_clean_candidate(self) -> None:
        provenance = self._provenance("codex-cli")
        provenance["plugin_inputs_dirty"] = True
        envelope = eval_evidence.build_envelope(
            provenance=provenance,
            profile=self._profile(),
            scenario_results=self._results(),
            reference_canaries={SCENARIO: {REFERENCE: CANARY}},
            grader_sha256=DIGEST,
            ended_at="2026-08-26T12:00:04Z",
        )

        self.assertFalse(envelope["candidate"]["clean"])
        self.assertIn(
            "candidate inputs differ from the recorded Git revision",
            envelope["limitations"],
        )

    def test_missing_reference_canary_makes_result_inconclusive(self) -> None:
        envelope = eval_evidence.build_envelope(
            provenance=self._provenance("codex-cli"),
            profile=self._profile(),
            scenario_results=self._results(observed=()),
            reference_canaries={SCENARIO: {REFERENCE: CANARY}},
            grader_sha256=DIGEST,
            ended_at="2026-08-26T12:00:04Z",
        )

        engine_contract.validate_envelope(envelope)
        self.assertEqual(envelope["verdict"], "INCONCLUSIVE")
        self.assertEqual(envelope["canaries"][0]["status"], "MISSING")

    def test_unobserved_policy_is_null_and_inconclusive(self) -> None:
        results = self._results()
        for trial in results[0]["trials"]:
            trial["policy_sha256"] = None
        envelope = eval_evidence.build_envelope(
            provenance=self._provenance("codex-cli"),
            profile=self._profile(),
            scenario_results=results,
            reference_canaries={SCENARIO: {REFERENCE: CANARY}},
            grader_sha256=DIGEST,
            ended_at="2026-08-26T12:00:04Z",
        )

        self.assertEqual("INCONCLUSIVE", envelope["verdict"])
        self.assertIsNone(envelope["digests"]["policy"])

    def test_claude_envelope_emits_native_and_callable_claims_separately(self) -> None:
        results = self._results()
        for trial in results[0]["trials"]:
            trial["context_sha256"] = None
            trial["total_cost_usd"] = 0.25
        envelope = eval_evidence.build_envelope(
            provenance=self._provenance("claude-plugin"),
            profile=self._profile("claude-plugin"),
            scenario_results=results,
            reference_canaries={SCENARIO: {REFERENCE: CANARY}},
            grader_sha256=DIGEST,
            ended_at="2026-08-26T12:00:04Z",
        )

        engine_contract.validate_envelope(envelope)
        emitted = {claim["type"] for claim in envelope["scenarios"][0]["claims"]}
        self.assertIn("advertised_tool_inventory", emitted)
        self.assertIn("callable_tool_boundary", emitted)
        self.assertEqual(envelope["cost"]["amount"], 0.5)

    def test_claude_cost_ignores_trials_skipped_after_a_budget_stop(self) -> None:
        results = self._results()
        results[0]["verdict"] = "INCONCLUSIVE"
        first, second = results[0]["trials"]
        first["state"] = "INCONCLUSIVE"
        first["total_cost_usd"] = 0.75
        second.update({
            "state": "INCONCLUSIVE",
            "model_executed": False,
            "total_cost_usd": None,
            "policy_sha256": None,
            "resolved_model": None,
        })

        envelope = eval_evidence.build_envelope(
            provenance=self._provenance("claude-plugin"),
            profile=self._profile("claude-plugin"),
            scenario_results=results,
            reference_canaries={SCENARIO: {REFERENCE: CANARY}},
            grader_sha256=DIGEST,
            ended_at="2026-08-26T12:00:04Z",
        )

        self.assertEqual(envelope["cost"], {
            "status": "available",
            "amount": 0.75,
            "currency": "USD",
            "reason": None,
        })

    def test_claude_skill_does_not_claim_native_invocation_without_trace_evidence(self) -> None:
        profile = self._profile("claude-plugin")
        results = self._results()
        results[0]["target"] = {"kind": "skill", "name": "incident-investigation"}
        envelope = eval_evidence.build_envelope(
            provenance=self._provenance("claude-plugin"),
            profile=profile,
            scenario_results=results,
            reference_canaries={SCENARIO: {REFERENCE: CANARY}},
            grader_sha256=DIGEST,
            ended_at="2026-08-26T12:00:04Z",
        )

        native = next(
            claim for claim in envelope["scenarios"][0]["claims"]
            if claim["type"] == "native_component_invoked"
        )
        self.assertEqual(native["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
