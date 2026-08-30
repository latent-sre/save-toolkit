from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path


SANDBOX_ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = SANDBOX_ROOT / "cases"
sys.path.insert(0, str(SANDBOX_ROOT))

from interop_sandbox.contracts import (  # noqa: E402
    CASE_IDS,
    ContractViolation,
    canonical_json_bytes,
    canonical_sha256,
    parse_analysis_request_json,
    to_plain_object,
    validate_analysis_request,
    validate_case,
    validate_decision_replay,
    validate_recommendation_artifact,
    validate_release_decision,
    verify_case_manifest,
)


SOURCE_REVISION = "0123456789abcdef0123456789abcdef01234567"


def _healthy_case_object() -> dict[str, object]:
    return {
        "case_version": "canary-evidence-case/v1",
        "case_id": "mission-healthy-001",
        "candidate": {
            "service": "synthetic-catalog-api",
            "candidate_revision": "1111111111111111111111111111111111111111",
            "rollback_revision": "0000000000000000000000000000000000000000",
        },
        "evidence": {
            "slo": {
                "observed_at": "2026-08-30T12:00:00Z",
                "age_seconds": 15,
                "freshness_limit_seconds": 60,
                "baseline_error_ppm": 1000,
                "canary_error_ppm": 1100,
                "burn_rate_milli": 800,
            },
            "deployment": {
                "observed_at": "2026-08-30T12:00:00Z",
                "age_seconds": 10,
                "freshness_limit_seconds": 60,
                "candidate_only_change": True,
                "rollback_ready": True,
                "configuration_drift": False,
            },
            "dependency": {
                "observed_at": "2026-08-30T12:00:00Z",
                "age_seconds": 10,
                "freshness_limit_seconds": 60,
                "baseline_impacted": False,
                "canary_impacted": False,
            },
        },
        "reconciliation": None,
        "fault": {"slow_analyzer": None, "checkpoint_pause": False},
        "expected": {
            "a2a_state": "completed",
            "recommendation": "ADVANCE_CANARY",
            "reconciliation_attempts": 0,
        },
    }


def _analysis_request_object() -> dict[str, object]:
    case = _healthy_case_object()
    return {
        "request_version": "canary-analysis-request/v1",
        "run_id": "mission-healthy-001",
        "source_revision": SOURCE_REVISION,
        "case_id": "mission-healthy-001",
        "case_digest": canonical_sha256(case),
        "candidate_revision": "1111111111111111111111111111111111111111",
        "case": case,
    }


def _recommendation_object() -> dict[str, object]:
    artifact: dict[str, object] = {
        "artifact_version": "release-recommendation/v1",
        "artifact_id": "release-recommendation:mission-healthy-001",
        "run_id": "mission-healthy-001",
        "case_id": "mission-healthy-001",
        "case_digest": canonical_sha256(_healthy_case_object()),
        "source_revision": SOURCE_REVISION,
        "candidate_revision": "1111111111111111111111111111111111111111",
        "a2a_task_id": "task-001",
        "a2a_context_id": "context-001",
        "recommendation": "ADVANCE_CANARY",
        "basis": [
            "slo.within_budget",
            "deployment.rollback_ready",
            "dependency.healthy",
        ],
        "resolved_contradictions": [],
        "unresolved_contradictions": [],
        "reconciliation_attempts": 0,
        "graph_state_sha256": "2" * 64,
        "packages": {
            "agent-framework-core": "1.0.0rc1",
            "agent-framework-a2a": "1.0.0b1",
            "autogen-agentchat": "0.7.5",
            "a2a-sdk": "0.3.0",
        },
    }
    artifact["artifact_digest"] = canonical_sha256(artifact)
    return artifact


def _decision_object() -> dict[str, object]:
    artifact = _recommendation_object()
    return {
        "decision_version": "release-decision-state/v1",
        "run_id": artifact["run_id"],
        "source_revision": artifact["source_revision"],
        "case_id": artifact["case_id"],
        "case_digest": artifact["case_digest"],
        "candidate_revision": artifact["candidate_revision"],
        "artifact_digest": artifact["artifact_digest"],
        "decision": "ACCEPT",
        "approver": "human-release-owner",
        "decided_at": "2030-01-01T00:00:00Z",
        "expires_at": "2030-01-01T00:05:00Z",
    }


class CanonicalJsonTests(unittest.TestCase):
    def test_canonical_json_and_digest_ignore_mapping_insertion_order(self) -> None:
        left = {"z": [3, 2, 1], "a": {"second": 2, "first": 1}}
        right = {"a": {"first": 1, "second": 2}, "z": [3, 2, 1]}

        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))
        self.assertEqual(canonical_sha256(left), canonical_sha256(right))
        self.assertEqual(
            canonical_json_bytes(left),
            b'{"a":{"first":1,"second":2},"z":[3,2,1]}',
        )


class CaseContractTests(unittest.TestCase):
    def test_all_six_manifest_bound_cases_validate_and_are_immutable(self) -> None:
        cases = verify_case_manifest(CASES_ROOT)

        self.assertEqual(tuple(case.case_id for case in cases), CASE_IDS)
        self.assertEqual(len(cases), 6)
        with self.assertRaises(FrozenInstanceError):
            cases[0].case_id = "changed"  # type: ignore[misc]

    def test_cases_encode_the_six_required_routes(self) -> None:
        cases = {case.case_id: case for case in verify_case_manifest(CASES_ROOT)}

        self.assertEqual(
            (
                cases["mission-healthy-001"].expected.a2a_state,
                cases["mission-healthy-001"].expected.recommendation,
            ),
            ("completed", "ADVANCE_CANARY"),
        )
        self.assertEqual(
            cases["confirmed-regression-001"].expected.recommendation,
            "HALT_CANARY",
        )
        self.assertEqual(
            cases["stale-evidence-reconciled-001"].expected.reconciliation_attempts,
            1,
        )
        self.assertIsNotNone(cases["stale-evidence-reconciled-001"].reconciliation)
        self.assertEqual(
            cases["unresolved-contradiction-001"].expected.a2a_state,
            "input-required",
        )
        self.assertIsNone(
            cases["unresolved-contradiction-001"].expected.recommendation
        )
        self.assertEqual(
            cases["slow-analysis-cancel-001"].fault.slow_analyzer,
            "dependency_analyzer",
        )
        self.assertEqual(
            cases["slow-analysis-cancel-001"].expected.a2a_state,
            "canceled",
        )
        self.assertTrue(cases["checkpoint-resume-001"].fault.checkpoint_pause)
        self.assertEqual(
            cases["checkpoint-resume-001"].expected.recommendation,
            "ADVANCE_CANARY",
        )

    def test_manifest_detects_case_byte_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copied_cases = Path(temporary) / "cases"
            shutil.copytree(CASES_ROOT, copied_cases)
            case_path = copied_cases / "mission-healthy-001.json"
            case_path.write_bytes(case_path.read_bytes() + b" ")

            with self.assertRaisesRegex(ContractViolation, "byte digest"):
                verify_case_manifest(copied_cases)

    def test_case_rejects_unknown_and_missing_fields_at_nested_boundaries(self) -> None:
        unknown = _healthy_case_object()
        unknown["evidence"]["slo"]["confidence"] = 0  # type: ignore[index]
        missing = _healthy_case_object()
        del missing["candidate"]["rollback_revision"]  # type: ignore[index]

        with self.assertRaisesRegex(ContractViolation, "unknown fields"):
            validate_case(unknown)
        with self.assertRaisesRegex(ContractViolation, "missing fields"):
            validate_case(missing)

    def test_case_rejects_bool_as_int_and_invalid_ranges(self) -> None:
        mutations = []
        bool_age = _healthy_case_object()
        bool_age["evidence"]["slo"]["age_seconds"] = True  # type: ignore[index]
        mutations.append(bool_age)
        zero_limit = _healthy_case_object()
        zero_limit["evidence"]["deployment"]["freshness_limit_seconds"] = 0  # type: ignore[index]
        mutations.append(zero_limit)
        invalid_ppm = _healthy_case_object()
        invalid_ppm["evidence"]["slo"]["canary_error_ppm"] = 1_000_001  # type: ignore[index]
        mutations.append(invalid_ppm)
        same_revision = _healthy_case_object()
        same_revision["candidate"]["rollback_revision"] = "1" * 40  # type: ignore[index]
        mutations.append(same_revision)

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(ContractViolation):
                    validate_case(mutation)

    def test_case_rejects_invalid_version_id_and_time(self) -> None:
        mutations = []
        invalid_version = _healthy_case_object()
        invalid_version["case_version"] = "canary-evidence-case/v2"
        mutations.append(invalid_version)
        invalid_id = _healthy_case_object()
        invalid_id["case_id"] = "../mission-healthy-001"
        mutations.append(invalid_id)
        invalid_time = _healthy_case_object()
        invalid_time["evidence"]["dependency"]["observed_at"] = "2026-08-30 12:00:00"  # type: ignore[index]
        mutations.append(invalid_time)

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(ContractViolation):
                    validate_case(mutation)

    def test_case_reconciliation_presence_matches_attempt_count(self) -> None:
        case = _healthy_case_object()
        case["expected"]["reconciliation_attempts"] = 1  # type: ignore[index]

        with self.assertRaisesRegex(ContractViolation, "reconciliation"):
            validate_case(case)

    def test_case_reconciliation_cannot_move_backward_or_change_freshness_policy(self) -> None:
        backward = _healthy_case_object()
        backward["reconciliation"] = copy.deepcopy(backward["evidence"])
        backward["reconciliation"]["slo"]["observed_at"] = "2026-08-30T11:59:59Z"  # type: ignore[index]
        backward["expected"]["reconciliation_attempts"] = 1  # type: ignore[index]
        changed_limit = _healthy_case_object()
        changed_limit["reconciliation"] = copy.deepcopy(changed_limit["evidence"])
        changed_limit["reconciliation"]["dependency"]["freshness_limit_seconds"] = 120  # type: ignore[index]
        changed_limit["expected"]["reconciliation_attempts"] = 1  # type: ignore[index]

        with self.assertRaisesRegex(ContractViolation, "move backward"):
            validate_case(backward)
        with self.assertRaisesRegex(ContractViolation, "freshness limit"):
            validate_case(changed_limit)


class AnalysisRequestTests(unittest.TestCase):
    def test_valid_request_binds_the_exact_nested_case(self) -> None:
        request = validate_analysis_request(_analysis_request_object())

        self.assertEqual(request.case_digest, canonical_sha256(request.case))
        self.assertEqual(request.case_id, request.case.case_id)
        self.assertEqual(
            request.candidate_revision, request.case.candidate.candidate_revision
        )

    def test_request_rejects_unknown_fields_and_bool_like_or_bad_digests(self) -> None:
        unknown = _analysis_request_object()
        unknown["extra"] = "forbidden"
        bad_digest = _analysis_request_object()
        bad_digest["case_digest"] = "A" * 64

        with self.assertRaisesRegex(ContractViolation, "unknown fields"):
            validate_analysis_request(unknown)
        with self.assertRaises(ContractViolation):
            validate_analysis_request(bad_digest)

    def test_request_rejects_each_mismatched_nested_identity(self) -> None:
        mutations = {
            "case_id": "confirmed-regression-001",
            "candidate_revision": "3" * 40,
            "case_digest": "4" * 64,
        }

        for field, value in mutations.items():
            request = _analysis_request_object()
            request[field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(ContractViolation, "does not match"):
                    validate_analysis_request(request)

    def test_text_part_requires_canonical_json(self) -> None:
        request = _analysis_request_object()

        parsed = parse_analysis_request_json(canonical_json_bytes(request))
        self.assertEqual(parsed.run_id, "mission-healthy-001")
        with self.assertRaisesRegex(ContractViolation, "not canonical JSON"):
            parse_analysis_request_json(json.dumps(request, indent=2))


class RecommendationArtifactTests(unittest.TestCase):
    def test_valid_artifact_is_immutable_and_digest_bound(self) -> None:
        artifact = validate_recommendation_artifact(_recommendation_object())

        self.assertEqual(
            artifact.artifact_digest,
            canonical_sha256(to_plain_object(artifact), omit_keys={"artifact_digest"}),
        )
        with self.assertRaises(FrozenInstanceError):
            artifact.run_id = "changed"  # type: ignore[misc]

    def test_artifact_rejects_unknown_missing_and_package_shape_drift(self) -> None:
        unknown = _recommendation_object()
        unknown["confidence"] = 1
        missing = _recommendation_object()
        del missing["basis"]
        package_drift = _recommendation_object()
        package_drift["packages"]["a2a"] = "wrong"  # type: ignore[index]

        for mutation in (unknown, missing, package_drift):
            with self.subTest(mutation=mutation):
                with self.assertRaises(ContractViolation):
                    validate_recommendation_artifact(mutation)

    def test_artifact_rejects_digest_mismatch(self) -> None:
        artifact = _recommendation_object()
        artifact["artifact_digest"] = "f" * 64

        with self.assertRaisesRegex(ContractViolation, "artifact_digest"):
            validate_recommendation_artifact(artifact)

    def test_artifact_rejects_unresolved_or_unstable_contradictions(self) -> None:
        unresolved = _recommendation_object()
        unresolved["unresolved_contradictions"] = ["dependency.canary_impacted"]
        unresolved["artifact_digest"] = canonical_sha256(
            unresolved, omit_keys={"artifact_digest"}
        )
        unstable = _recommendation_object()
        unstable["resolved_contradictions"] = ["z.last", "a.first"]
        unstable["reconciliation_attempts"] = 1
        unstable["artifact_digest"] = canonical_sha256(
            unstable, omit_keys={"artifact_digest"}
        )

        with self.assertRaisesRegex(ContractViolation, "unresolved"):
            validate_recommendation_artifact(unresolved)
        with self.assertRaisesRegex(ContractViolation, "stable-sorted"):
            validate_recommendation_artifact(unstable)

    def test_artifact_rejects_request_lineage_mismatch(self) -> None:
        request = validate_analysis_request(_analysis_request_object())
        artifact = _recommendation_object()
        artifact["source_revision"] = "7" * 40
        artifact["artifact_digest"] = canonical_sha256(
            artifact, omit_keys={"artifact_digest"}
        )

        with self.assertRaisesRegex(ContractViolation, "does not match"):
            validate_recommendation_artifact(artifact, request=request)


class ReleaseDecisionTests(unittest.TestCase):
    def test_valid_decision_binds_the_exact_artifact(self) -> None:
        artifact = validate_recommendation_artifact(_recommendation_object())
        decision = validate_release_decision(
            _decision_object(),
            artifact=artifact,
            at_time=datetime(2029, 12, 31, tzinfo=timezone.utc),
        )

        self.assertEqual(decision.artifact_digest, artifact.artifact_digest)
        self.assertEqual(decision.run_id, artifact.run_id)

    def test_decision_rejects_every_artifact_lineage_mismatch(self) -> None:
        artifact = validate_recommendation_artifact(_recommendation_object())
        replacements = {
            "artifact_digest": "3" * 64,
            "run_id": "checkpoint-resume-001",
            "case_id": "confirmed-regression-001",
            "case_digest": "4" * 64,
            "source_revision": "5" * 40,
            "candidate_revision": "6" * 40,
        }

        for field, value in replacements.items():
            decision = _decision_object()
            decision[field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(ContractViolation, "does not match"):
                    validate_release_decision(
                        decision,
                        artifact=artifact,
                        at_time=datetime(2029, 12, 31, tzinfo=timezone.utc),
                    )

    def test_decision_rejects_non_utc_reversed_and_expired_times(self) -> None:
        artifact = validate_recommendation_artifact(_recommendation_object())
        non_utc = _decision_object()
        non_utc["decided_at"] = "2030-01-01T01:00:00+01:00"
        reversed_window = _decision_object()
        reversed_window["expires_at"] = reversed_window["decided_at"]
        expired = _decision_object()

        with self.assertRaisesRegex(ContractViolation, "UTC"):
            validate_release_decision(non_utc, artifact=artifact)
        with self.assertRaisesRegex(ContractViolation, "later"):
            validate_release_decision(reversed_window, artifact=artifact)
        with self.assertRaisesRegex(ContractViolation, "expired"):
            validate_release_decision(
                expired,
                artifact=artifact,
                at_time=datetime(2030, 1, 2, tzinfo=timezone.utc),
            )

    def test_replay_accepts_exact_record_and_rejects_changed_value(self) -> None:
        artifact = validate_recommendation_artifact(_recommendation_object())
        existing = validate_release_decision(
            _decision_object(),
            artifact=artifact,
            at_time=datetime(2029, 12, 31, tzinfo=timezone.utc),
        )
        changed = copy.deepcopy(_decision_object())
        changed["decision"] = "REJECT"
        candidate = validate_release_decision(
            changed,
            artifact=artifact,
            at_time=datetime(2029, 12, 31, tzinfo=timezone.utc),
        )

        self.assertIs(validate_decision_replay(existing, existing), existing)
        with self.assertRaisesRegex(ContractViolation, "different value"):
            validate_decision_replay(existing, candidate)

    def test_decision_rejects_unknown_or_missing_fields(self) -> None:
        artifact = validate_recommendation_artifact(_recommendation_object())
        unknown = _decision_object()
        unknown["release_effect"] = "promote"
        missing = _decision_object()
        del missing["approver"]

        for mutation in (unknown, missing):
            with self.subTest(mutation=mutation):
                with self.assertRaises(ContractViolation):
                    validate_release_decision(mutation, artifact=artifact)


if __name__ == "__main__":
    unittest.main()
