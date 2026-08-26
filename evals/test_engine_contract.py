"""Contract tests for claim-scoped multi-engine eval evidence."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_contract


ROOT = Path(__file__).resolve().parents[1]
DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64
REVISION = "c" * 40


class EvalEngineContractTests(unittest.TestCase):
    def _scenario(self, *, verdict: str = "PASS") -> dict[str, object]:
        return {
            "id": "agent-direct-sre-readonly-triage",
            "sha256": DIGEST,
            "verdict": verdict,
            "claims": [
                {
                    "type": "behavioral_contract",
                    "status": "PASS",
                    "evidence": [OTHER_DIGEST],
                    "limitations": [],
                },
                {
                    "type": "deterministic_grader_result",
                    "status": "PASS",
                    "evidence": [OTHER_DIGEST],
                    "limitations": [],
                },
            ],
        }

    def _valid(self, engine: str = "codex-cli") -> dict[str, object]:
        is_claude = engine == "claude-plugin"
        requested = ["behavioral_contract", "deterministic_grader_result"]
        envelope = {
            "schema_version": "eval-result-envelope/v1",
            "run_id": "20260826T120000Z-abcdef12",
            "engine": {
                "name": engine,
                "adapter_version": "1",
                "runtime_version": "codex-cli 0.149.1" if not is_claude else "2.1.246",
                "requested_model": "gpt-5.6-terra" if not is_claude else "sonnet",
                "resolved_model": "gpt-5.6-terra" if not is_claude else "claude-sonnet-5",
                "auth_mode": "subscriber_session",
            },
            "candidate": {
                "git_sha": REVISION,
                "clean": True,
                "input_sha256": DIGEST,
            },
            "artifacts": {
                "plugin_snapshot": {
                    "applicable": is_claude,
                    "sha256": DIGEST if is_claude else None,
                },
                "resolved_context": {
                    "applicable": not is_claude,
                    "sha256": DIGEST if not is_claude else None,
                },
            },
            "digests": {
                "scenario_suite": DIGEST,
                "graders": DIGEST,
                "execution_profile": DIGEST,
                "comparison": DIGEST,
                "policy": DIGEST,
            },
            "canaries": [],
            "claims_requested": requested,
            "claims_supported": sorted(engine_contract.ENGINE_CLAIMS[engine]),
            "scenarios": [self._scenario()],
            "verdict": "PASS",
            "timing": {
                "started_at": "2026-08-26T12:00:00Z",
                "ended_at": "2026-08-26T12:00:02Z",
                "duration_seconds": 2.0,
            },
            "cost": {
                "status": "unavailable",
                "amount": None,
                "currency": None,
                "reason": "subscriber session does not expose per-run cost",
            },
            "trace": {"complete": True, "sha256": OTHER_DIGEST},
            "promotion_eligible": True,
            "limitations": [],
        }
        engine_contract.validate_envelope(envelope)
        return envelope

    def test_schema_and_catalog_publish_the_semantic_validator(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/eval-result-envelope-v1.schema.json").read_text(encoding="utf-8")
        )
        catalog = json.loads((ROOT / "schemas/catalog-v1.json").read_text(encoding="utf-8"))
        entry = next(item for item in catalog["schemas"] if item["id"] == "eval-result-envelope-v1")
        self.assertEqual(schema["properties"]["schema_version"]["const"], engine_contract.SCHEMA_VERSION)
        self.assertEqual(entry["validator"], "evals/engine_contract.py")

    def test_valid_codex_and_claude_envelopes(self) -> None:
        for engine in engine_contract.ENGINE_CLAIMS:
            with self.subTest(engine=engine):
                engine_contract.validate_envelope(self._valid(engine))

    def test_engine_support_registry_is_the_claim_ceiling(self) -> None:
        envelope = self._valid()
        envelope["claims_requested"].append("native_plugin_loaded")
        envelope["scenarios"][0]["claims"].append(
            {
                "type": "native_plugin_loaded",
                "status": "PASS",
                "evidence": [DIGEST],
                "limitations": [],
            }
        )
        with self.assertRaisesRegex(engine_contract.ContractError, "unsupported claim"):
            engine_contract.validate_envelope(envelope)

    def test_engine_mislabel_cannot_reuse_the_other_artifact_shape(self) -> None:
        envelope = self._valid("claude-plugin")
        envelope["engine"]["name"] = "codex-cli"
        envelope["claims_supported"] = sorted(engine_contract.ENGINE_CLAIMS["codex-cli"])
        with self.assertRaisesRegex(engine_contract.ContractError, "plugin_snapshot"):
            engine_contract.validate_envelope(envelope)

    def test_claude_candidate_digest_must_match_the_plugin_snapshot(self) -> None:
        envelope = self._valid("claude-plugin")
        envelope["artifacts"]["plugin_snapshot"]["sha256"] = OTHER_DIGEST
        with self.assertRaisesRegex(engine_contract.ContractError, "candidate.*plugin snapshot"):
            engine_contract.validate_envelope(envelope)

    def test_every_digest_is_exact_sha256(self) -> None:
        envelope = self._valid()
        envelope["digests"]["policy"] = "short"
        with self.assertRaisesRegex(engine_contract.ContractError, "digests.policy"):
            engine_contract.validate_envelope(envelope)

    def test_incomplete_trace_cannot_report_a_decisive_verdict(self) -> None:
        envelope = self._valid()
        envelope["trace"]["complete"] = False
        with self.assertRaisesRegex(engine_contract.ContractError, "incomplete trace"):
            engine_contract.validate_envelope(envelope)

    def test_unobserved_policy_cannot_report_a_decisive_verdict(self) -> None:
        envelope = self._valid()
        envelope["digests"]["policy"] = None
        with self.assertRaisesRegex(engine_contract.ContractError, "unobserved policy"):
            engine_contract.validate_envelope(envelope)

    def test_missing_canary_cannot_report_pass(self) -> None:
        envelope = self._valid()
        envelope["canaries"] = [
            {
                "scenario_id": "agent-direct-sre-readonly-triage",
                "path": "skills/incident-investigation/references/first-response.md",
                "expected": "q_first_1234",
                "observed": None,
                "status": "MISSING",
            }
        ]
        with self.assertRaisesRegex(engine_contract.ContractError, "canary"):
            engine_contract.validate_envelope(envelope)

    def test_unavailable_subscription_cost_is_null_not_zero(self) -> None:
        envelope = self._valid()
        envelope["cost"]["amount"] = 0
        with self.assertRaisesRegex(engine_contract.ContractError, "unavailable cost"):
            engine_contract.validate_envelope(envelope)

    def test_dirty_candidate_is_never_promotion_eligible(self) -> None:
        envelope = self._valid()
        envelope["candidate"]["clean"] = False
        with self.assertRaisesRegex(engine_contract.ContractError, "dirty candidate"):
            engine_contract.validate_envelope(envelope)

    def test_schema_shape_tracks_the_semantic_validator(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/eval-result-envelope-v1.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual("eval-result-envelope/v1", schema["properties"]["schema_version"]["const"])
        self.assertEqual(engine_contract.TOP_LEVEL_FIELDS, set(schema["properties"]))
        self.assertEqual(engine_contract.TOP_LEVEL_FIELDS, set(schema["required"]))
        self.assertFalse(schema["additionalProperties"])

    def test_comparison_refuses_different_candidate_or_grader(self) -> None:
        claude = self._valid("claude-plugin")
        codex = self._valid("codex-cli")
        for path in (("candidate", "git_sha"), ("digests", "graders")):
            changed = copy.deepcopy(codex)
            changed[path[0]][path[1]] = ("d" * 40 if path[1] == "git_sha" else OTHER_DIGEST)
            with self.subTest(path=path):
                result = engine_contract.compare_envelopes(claude, changed)
                self.assertEqual("incomparable", result["classification"])

    def test_comparison_refuses_different_approved_comparison_contract(self) -> None:
        claude = self._valid("claude-plugin")
        codex = self._valid("codex-cli")
        codex["digests"]["comparison"] = OTHER_DIGEST

        result = engine_contract.compare_envelopes(claude, codex)

        self.assertEqual("incomparable", result["classification"])
        self.assertIn("digests.comparison differs", result["reasons"])

    def test_comparison_never_returns_an_average(self) -> None:
        claude = self._valid("claude-plugin")
        codex = self._valid("codex-cli")
        codex["scenarios"][0]["claims"][0]["status"] = "FAIL"
        codex["scenarios"][0]["verdict"] = "FAIL"
        codex["verdict"] = "FAIL"
        codex["promotion_eligible"] = False
        result = engine_contract.compare_envelopes(claude, codex)
        self.assertEqual("behavioral_divergence", result["classification"])
        self.assertNotIn("score", result)
        self.assertNotIn("average", result)

    def test_engine_specific_policy_digests_do_not_block_portable_comparison(self) -> None:
        claude = self._valid("claude-plugin")
        codex = self._valid("codex-cli")
        codex["digests"]["policy"] = OTHER_DIGEST

        result = engine_contract.compare_envelopes(claude, codex)

        self.assertEqual("agreement", result["classification"])


if __name__ == "__main__":
    unittest.main()
