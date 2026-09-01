"""Validation tests for versioned, approval-gated eval execution profiles."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import execution_profiles


class ExecutionProfileTests(unittest.TestCase):
    CONSUMED_V1_PROFILES = (
        "grader-005-frontend-posture-sonnet.json",
        "grader-008-sre-progressive-object-sonnet.json",
        "grader-009-defers-current-sonnet.json",
        "grader-009-defers-incumbent-sonnet.json",
        "route-003-discovery-reliability-sonnet.json",
    )
    def _valid(self) -> dict[str, object]:
        return {
            "schema_version": "eval-execution-profile/v1",
            "id": "codex-sre-first-response-v1",
            "comparison": {
                "id": "sre-first-response-v1",
                "models": {
                    "claude-plugin": "sonnet",
                    "codex-cli": "gpt-5.6-terra",
                },
            },
            "engine": "codex-cli",
            "claims": [
                "candidate_snapshot_integrity",
                "reference_used",
                "behavioral_contract",
                "deterministic_grader_result",
            ],
            "scenario_ids": ["agent-direct-sre-first-response-untriaged-alert"],
            "required_references": {
                "agent-direct-sre-first-response-untriaged-alert": [
                    "skills/incident-investigation/references/first-response.md"
                ]
            },
            "model": "gpt-5.6-terra",
            "trials": 2,
            "timeout_s": 180,
            "total_timeout_s": 360,
            "cost_budget": {"status": "unavailable", "max_usd": None},
            "approval": {
                "approved_by": "Save Toolkit maintainers",
                "approved_at": "2026-08-26T12:00:00Z",
                "budget_id": "budget-1",
            },
        }

    def _valid_v2(self) -> dict[str, object]:
        value = self._valid()
        value["schema_version"] = "eval-execution-profile/v2"
        value["comparison"] = {
            **value["comparison"],
            "resolved_models": {
                "claude-plugin": "claude-sonnet-5",
                "codex-cli": "gpt-5.6-terra",
            },
            "reasoning_efforts": {
                "claude-plugin": "high",
                "codex-cli": "high",
            },
        }
        value["resolved_model"] = "gpt-5.6-terra"
        value["reasoning_effort"] = "high"
        value["stop_condition"] = "first-inconclusive"
        return value

    def test_valid_profile_is_digest_bound(self) -> None:
        profile = execution_profiles.validate_profile(self._valid_v2(), require_approval=True)
        self.assertRegex(profile.sha256, r"^[0-9a-f]{64}$")
        changed = self._valid_v2()
        changed["timeout_s"] = 181
        self.assertNotEqual(
            profile.sha256,
            execution_profiles.validate_profile(changed, require_approval=True).sha256,
        )
        self.assertNotEqual(
            profile.comparison_sha256,
            execution_profiles.validate_profile(changed, require_approval=True).comparison_sha256,
        )

    def test_profile_model_must_match_comparison_matrix(self) -> None:
        value = self._valid()
        value["model"] = "different-model"
        with self.assertRaisesRegex(execution_profiles.ProfileError, "model matrix"):
            execution_profiles.validate_profile(value)

    def test_live_profile_requires_explicit_approval(self) -> None:
        value = self._valid_v2()
        value["approval"] = None
        execution_profiles.validate_profile(value, require_approval=False)
        with self.assertRaisesRegex(execution_profiles.ProfileError, "approval"):
            execution_profiles.validate_profile(value, require_approval=True)

    def test_v1_remains_readable_but_cannot_authorize_new_live_execution(self) -> None:
        execution_profiles.validate_profile(self._valid(), require_approval=False)
        with self.assertRaisesRegex(execution_profiles.ProfileError, "v2"):
            execution_profiles.validate_profile(self._valid(), require_approval=True)

    def test_v2_binds_requested_resolved_model_and_reasoning_effort(self) -> None:
        profile = execution_profiles.validate_profile(self._valid_v2(), require_approval=True)
        self.assertEqual("gpt-5.6-terra", profile.model)
        self.assertEqual("gpt-5.6-terra", profile.resolved_model)
        self.assertEqual("high", profile.reasoning_effort)
        for field, value in (
            ("resolved_model", "gpt-5.6-sol"),
            ("reasoning_effort", "low"),
        ):
            changed = self._valid_v2()
            changed[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                execution_profiles.ProfileError, "matrix entry"
            ):
                execution_profiles.validate_profile(changed)

        unsafe = self._valid_v2()
        unsafe["reasoning_effort"] = 'high" --config unsafe=true'
        unsafe["comparison"]["reasoning_efforts"]["codex-cli"] = unsafe["reasoning_effort"]
        with self.assertRaisesRegex(execution_profiles.ProfileError, "bounded lowercase"):
            execution_profiles.validate_profile(unsafe)

    def test_v2_stop_condition_is_required_bounded_and_digest_bound(self) -> None:
        value = self._valid_v2()
        profile = execution_profiles.validate_profile(value)
        self.assertEqual("first-inconclusive", profile.stop_condition)

        changed = self._valid_v2()
        changed["stop_condition"] = "declared-trials-or-budget-boundary"
        changed_profile = execution_profiles.validate_profile(changed)
        self.assertNotEqual(profile.sha256, changed_profile.sha256)
        self.assertNotEqual(profile.comparison_sha256, changed_profile.comparison_sha256)

        invalid = self._valid_v2()
        invalid["stop_condition"] = "keep-going-forever"
        with self.assertRaisesRegex(execution_profiles.ProfileError, "stop_condition"):
            execution_profiles.validate_profile(invalid)

    def test_approval_timestamp_must_be_a_real_utc_instant(self) -> None:
        value = self._valid()
        value["approval"]["approved_at"] = "2026-99-99T99:99:99Z"
        with self.assertRaisesRegex(execution_profiles.ProfileError, "valid timestamp"):
            execution_profiles.validate_profile(value, require_approval=True)

    def test_claude_references_require_a_direct_scenario_of_either_target_kind(self) -> None:
        """Reference reads are scoped to the plugin snapshot, so target kind is irrelevant.

        What is not irrelevant is `mode`. Enabling references prepends a boundary preflight to the
        prompt, and a discovery scenario must reach the model byte-for-byte, so a discovery profile
        would silently measure a different prompt than the one authored.
        """
        value = self._valid_v2()
        value["engine"] = "claude-plugin"
        value["model"] = "sonnet"
        value["resolved_model"] = "claude-sonnet-5"
        profile = execution_profiles.validate_profile(value, require_approval=True)

        for target in (
            {"kind": "agent", "name": "sre"},
            {"kind": "agent", "name": "software-engineer"},
            {"kind": "skill", "name": "incident-investigation"},
            {"kind": "skill", "name": "incident-command"},
        ):
            with self.subTest(target=target):
                execution_profiles.validate_scenario_bindings(
                    profile,
                    [{"id": value["scenario_ids"][0], "mode": "direct", "target": target}],
                )

        discovery = [{
            "id": value["scenario_ids"][0],
            "mode": "discovery",
            "target": {"kind": "skill", "name": "incident-investigation"},
        }]
        with self.assertRaisesRegex(execution_profiles.ProfileError, "direct"):
            execution_profiles.validate_scenario_bindings(profile, discovery)

    def test_unsupported_claim_is_rejected(self) -> None:
        value = self._valid()
        value["claims"].append("native_plugin_loaded")
        with self.assertRaisesRegex(execution_profiles.ProfileError, "unsupported claim"):
            execution_profiles.validate_profile(value)

    def test_deterministic_behavioral_gate_claims_are_mandatory(self) -> None:
        for missing in ("behavioral_contract", "deterministic_grader_result"):
            value = self._valid()
            value["claims"].remove(missing)
            with self.subTest(missing=missing), self.assertRaisesRegex(
                execution_profiles.ProfileError,
                "automated gate",
            ):
                execution_profiles.validate_profile(value)

    def test_discovery_scenario_is_rejected_for_codex(self) -> None:
        value = self._valid()
        value["scenario_ids"] = ["discovery-active-alert-stays-with-sre"]
        value["required_references"] = {}
        with self.assertRaisesRegex(execution_profiles.ProfileError, "direct scenarios"):
            execution_profiles.validate_profile(value)

    def test_reference_traversal_is_rejected(self) -> None:
        value = self._valid()
        value["required_references"] = {
            value["scenario_ids"][0]: ["skills/incident-investigation/../../secret"]
        }
        with self.assertRaisesRegex(execution_profiles.ProfileError, "reference path"):
            execution_profiles.validate_profile(value)

    def test_subscription_cost_is_unavailable_not_zero(self) -> None:
        value = self._valid()
        value["cost_budget"] = {"status": "unavailable", "max_usd": 0}
        with self.assertRaisesRegex(execution_profiles.ProfileError, "max_usd"):
            execution_profiles.validate_profile(value)

    def test_load_rejects_duplicate_json_keys(self) -> None:
        rendered = json.dumps(self._valid()).replace(
            '"trials": 2',
            '"trials": 99, "trials": 2',
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "profile.json"
            path.write_text(rendered, encoding="utf-8")
            with self.assertRaisesRegex(execution_profiles.ProfileError, "duplicate"):
                execution_profiles.load_profile(path)

    def test_schema_and_catalog_publish_the_semantic_validator(self) -> None:
        root = Path(__file__).resolve().parents[1]
        schema = json.loads(
            (root / "schemas/eval-execution-profile-v1.schema.json").read_text(encoding="utf-8")
        )
        catalog = json.loads((root / "schemas/catalog-v1.json").read_text(encoding="utf-8"))
        entry = next(item for item in catalog["schemas"] if item["id"] == "eval-execution-profile-v1")
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            execution_profiles.SCHEMA_VERSION_V1,
        )
        self.assertEqual(entry["validator"], "evals/execution_profiles.py")

        schema_v2 = json.loads(
            (root / "schemas/eval-execution-profile-v2.schema.json").read_text(encoding="utf-8")
        )
        entry_v2 = next(item for item in catalog["schemas"] if item["id"] == "eval-execution-profile-v2")
        self.assertEqual(
            schema_v2["properties"]["schema_version"]["const"],
            execution_profiles.SCHEMA_VERSION_V2,
        )
        self.assertEqual(entry_v2["validator"], "evals/execution_profiles.py")
        self.assertEqual("supported", entry["status"])
        self.assertEqual("current", entry_v2["status"])

    def test_consumed_profiles_remain_readable_v1_evidence_not_live_authority(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for filename in self.CONSUMED_V1_PROFILES:
            with self.subTest(filename=filename):
                path = root / "evals" / "profiles" / filename
                profile = execution_profiles.load_profile(
                    path,
                    require_approval=False,
                )
                self.assertEqual(execution_profiles.SCHEMA_VERSION_V1, profile.schema_version)
                self.assertIsNotNone(profile.approval)
                with self.assertRaisesRegex(execution_profiles.ProfileError, "v2"):
                    execution_profiles.load_profile(path, require_approval=True)


if __name__ == "__main__":
    unittest.main()
