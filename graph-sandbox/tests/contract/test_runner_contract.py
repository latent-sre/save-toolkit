from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from unittest import mock
from datetime import UTC, datetime
from pathlib import Path

from runner.controls import BudgetExhausted, consume_budget
from runner.events import BoundaryEventStore, EventContractError
from runner.fixtures import load_case
from runner.gateway import (
    GatewayError,
    GatewayUnavailable,
    HttpGateway,
    ServiceOrigins,
    derive_child_idempotency_key,
    validate_checkout_receipt,
)
from runner.main import RunnerConfig
from runner.models import (
    CONTRACT_VERSION,
    merge_ordered_unique,
    merge_pending_effects,
    merge_unique_maps,
    new_run_state,
    remove_pending_effects,
)


REVISION = "1" * 40
CASE_DIGEST = "7" * 64
FIXED_TIME = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
SANDBOX_ROOT = Path(__file__).resolve().parents[2]
BASE_REFERENCE = (
    "python:3.12.10-slim-bookworm@"
    "sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4"
)


class RunnerImageContractTests(unittest.TestCase):
    def test_runner_dependencies_are_the_exact_approved_set(self) -> None:
        requirements = {
            line.strip()
            for line in (SANDBOX_ROOT / "runner" / "requirements.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertEqual(
            requirements,
            {
                "httpx==0.28.1",
                "langgraph==1.0.10",
                "langgraph-checkpoint-sqlite==3.1.1",
            },
        )
        self.assertFalse(any("pytest" in requirement.lower() for requirement in requirements))

    def test_runner_dockerfile_is_pinned_nonroot_and_has_no_implicit_authority(self) -> None:
        dockerfile = (SANDBOX_ROOT / "runner" / "Dockerfile").read_text(encoding="utf-8")
        instructions = [
            line.strip()
            for line in dockerfile.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertEqual(instructions[0], f"FROM {BASE_REFERENCE}")
        self.assertIn("USER 65532:65532", instructions)
        self.assertIn(
            "&& install -d --owner 65532 --group 65532 --mode 0750 /state /evidence",
            instructions,
        )
        self.assertIn('CMD ["python", "-m", "runner.main"]', instructions)
        self.assertFalse(any(line.upper().startswith("ENTRYPOINT") for line in instructions))
        self.assertFalse(any(line.upper().startswith("VOLUME") for line in instructions))
        self.assertFalse(any(line.upper().startswith("EXPOSE") for line in instructions))

    def test_runner_dockerfile_copies_only_runner_cases_and_exact_stdlib_tests(self) -> None:
        dockerfile = (SANDBOX_ROOT / "runner" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("COPY runner /app/runner", dockerfile)
        self.assertIn("COPY cases /app/cases", dockerfile)
        self.assertIn(
            "COPY tests/contract/test_runner_contract.py "
            "/app/tests/contract/test_runner_contract.py",
            dockerfile,
        )
        self.assertIn("COPY tests/recovery /app/tests/recovery", dockerfile)
        self.assertIn(
            "COPY tests/integration/test_runner_integration.py "
            "/app/tests/integration/test_runner_integration.py",
            dockerfile,
        )
        self.assertNotIn("COPY tests /app/tests", dockerfile)


class RunnerConfigurationContractTests(unittest.TestCase):
    def test_run_identity_is_independent_from_the_frozen_case_identity(self) -> None:
        config = RunnerConfig.from_environment(
            {
                "CHECKOUT_URL": "http://checkout:8080",
                "PAYMENTS_URL": "http://payments:8081",
                "INVENTORY_URL": "http://inventory:8082",
                "CHECKPOINT_DB": "/state/checkpoints.sqlite3",
                "EFFECT_LEDGER_DB": "/state/effects.sqlite3",
                "EVIDENCE_DIR": "/evidence",
                "RUN_ID": "run-healthy-001",
                "SOURCE_REVISION": REVISION,
                "CASE_ID": "mission-healthy-001",
                "CASE_DIGEST": CASE_DIGEST,
                "RUN_TIMEOUT_SECONDS": "300",
                "APPROVAL_FIXTURE": "APPROVED",
            }
        )

        self.assertEqual(config.run_id, "run-healthy-001")
        self.assertEqual(config.case_id, "mission-healthy-001")
        self.assertEqual(config.case_path, Path("/app/cases/mission-healthy-001.json"))


class ReducerContractTests(unittest.TestCase):
    def test_unique_map_accepts_identical_duplicate_without_mutating_inputs(self) -> None:
        left = {"task-1": {"status": "completed"}}
        right = {"task-1": {"status": "completed"}, "task-2": {"status": "started"}}
        before = (copy.deepcopy(left), copy.deepcopy(right))

        merged = merge_unique_maps(left, right)

        self.assertEqual(
            merged,
            {
                "task-1": {"status": "completed"},
                "task-2": {"status": "started"},
            },
        )
        self.assertEqual((left, right), before)

    def test_unique_map_rejects_conflicting_duplicate(self) -> None:
        with self.assertRaisesRegex(ValueError, "conflicting reducer value for task-1"):
            merge_unique_maps(
                {"task-1": {"status": "started"}},
                {"task-1": {"status": "completed"}},
            )

    def test_ordered_unique_reducer_preserves_first_seen_order(self) -> None:
        self.assertEqual(
            merge_ordered_unique(["payment", "inventory"], ["inventory", "checkout"]),
            ["payment", "inventory", "checkout"],
        )

    def test_pending_effect_reducer_removes_only_reconciled_effect(self) -> None:
        self.assertEqual(
            merge_pending_effects(
                ["effect-payment", "effect-inventory"],
                remove_pending_effects("effect-payment"),
            ),
            ["effect-inventory"],
        )


class StateAndBudgetContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = load_case(Path("/app/cases/mission-healthy-001.json"))

    def test_new_state_uses_stable_contract_and_lineage(self) -> None:
        state = new_run_state(
            self.case,
            run_id="run-healthy-001",
            source_revision=REVISION,
            case_digest=CASE_DIGEST,
        )

        self.assertEqual(state["contract_version"], CONTRACT_VERSION)
        self.assertEqual(
            state["thread_id"],
            "checkout-payments-timeout-drill-v1:run-healthy-001",
        )
        self.assertEqual(state["state_schema"], "graph-state/v2")
        self.assertEqual(state["case_id"], "mission-healthy-001")
        self.assertEqual(state["case_digest"], CASE_DIGEST)
        self.assertEqual(state["checkout_status"], "NOT_STARTED")
        self.assertEqual(state["replay_number"], 0)
        self.assertEqual(state["phase"], "ADMISSION")
        self.assertIsNone(state["outcome"])

    def test_budget_consumption_returns_partial_copy(self) -> None:
        state = new_run_state(
            self.case,
            run_id="run-healthy-001",
            source_revision=REVISION,
            case_digest=CASE_DIGEST,
        )
        original = copy.deepcopy(state["budgets"])

        updated = consume_budget(state["budgets"], "model_calls", 1)

        self.assertEqual(updated["model_calls"]["consumed"], 1)
        self.assertEqual(state["budgets"], original)

    def test_budget_exhaustion_names_the_budget_and_does_not_overconsume(self) -> None:
        state = new_run_state(
            self.case,
            run_id="run-healthy-001",
            source_revision=REVISION,
            case_digest=CASE_DIGEST,
        )

        with self.assertRaises(BudgetExhausted) as caught:
            consume_budget(state["budgets"], "model_calls", 2)

        self.assertEqual(caught.exception.kind, "model_calls")
        self.assertEqual(caught.exception.limit, 1)
        self.assertEqual(caught.exception.consumed, 0)
        self.assertEqual(caught.exception.requested, 2)


class BoundaryEventContractTests(unittest.TestCase):
    def test_event_has_complete_nullable_lineage_and_strict_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = BoundaryEventStore(
                Path(temp_dir) / "events.sqlite3",
                clock=lambda: FIXED_TIME,
            )
            state = {
                "run_id": "mission-healthy-001",
                "case_id": "mission-healthy-001",
                "case_digest": CASE_DIGEST,
                "thread_id": "checkout-payments-timeout-drill-v1:mission-healthy-001",
                "source_revision": REVISION,
                "replay_number": 0,
            }

            first = store.emit("run.accepted", state, {"result": "accepted"})
            second = store.emit("run.started", state, {"result": "started"})

            self.assertEqual(first["sequence"], 1)
            self.assertEqual(second["sequence"], 2)
            self.assertEqual(first["event_id"], "mission-healthy-001:00000001")
            self.assertEqual(first["time_utc"], "2026-08-29T12:00:00.000Z")
            self.assertEqual(
                set(first),
                {
                    "event_version",
                    "event_type",
                    "event_id",
                    "sequence",
                    "time_utc",
                    "contract_version",
                    "sandbox_version",
                    "source_revision",
                    "run_id",
                    "case_id",
                    "case_digest",
                    "thread_id",
                    "node_id",
                    "task_id",
                    "attempt_id",
                    "replay_id",
                    "checkpoint_id",
                    "effect_id",
                    "failure_plane",
                    "error_class",
                    "data",
                },
            )
            self.assertIsNone(first["effect_id"])

    def test_event_specific_data_rejects_unknown_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = BoundaryEventStore(Path(temp_dir) / "events.sqlite3")
            state = {
                "run_id": "mission-healthy-001",
                "case_id": "mission-healthy-001",
                "case_digest": CASE_DIGEST,
                "thread_id": "checkout-payments-timeout-drill-v1:mission-healthy-001",
                "source_revision": REVISION,
                "replay_number": 0,
            }

            with self.assertRaisesRegex(EventContractError, "unexpected data fields: raw_body"):
                store.emit(
                    "effect.unknown",
                    state,
                    {
                        "effect_class": "checkout",
                        "effect_state": "UNKNOWN",
                        "reason_class": "transport_ambiguous",
                        "raw_body": "must-not-leak",
                    },
                    effect_id="mission-healthy-001:checkout_effect:0:effect-checkout",
                )

            self.assertEqual(store.project(), [])

    def test_projected_events_are_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = BoundaryEventStore(Path(temp_dir) / "events.sqlite3")
            state = {
                "run_id": "mission-healthy-001",
                "case_id": "mission-healthy-001",
                "case_digest": CASE_DIGEST,
                "thread_id": "checkout-payments-timeout-drill-v1:mission-healthy-001",
                "source_revision": REVISION,
                "replay_number": 0,
            }
            store.emit("run.accepted", state, {"result": "accepted"})

            json.dumps(store.project(), sort_keys=True)


class CheckoutGatewayContractTests(unittest.TestCase):
    def test_health_accepts_service_ready_and_normalizes_graph_state_to_ok(self) -> None:
        gateway = HttpGateway(
            ServiceOrigins(
                checkout="http://checkout:8080",
                payments="http://payments:8081",
                inventory="http://inventory:8082",
            ),
            timeout_seconds=1.0,
        )
        with mock.patch.object(
            gateway,
            "_request",
            return_value=(200, {"status": "ready", "service": "checkout"}),
        ) as request:
            self.assertEqual(
                gateway.health("checkout", case_id="mission-healthy-001"),
                {"status": "ok", "service": "checkout"},
            )

        self.assertEqual(
            request.call_args.kwargs["headers"],
            {"X-Sandbox-Case": "mission-healthy-001"},
        )

    def test_health_rejects_old_ok_body_that_does_not_match_service_contract(self) -> None:
        gateway = HttpGateway(
            ServiceOrigins(
                checkout="http://checkout:8080",
                payments="http://payments:8081",
                inventory="http://inventory:8082",
            ),
            timeout_seconds=1.0,
        )
        with mock.patch.object(
            gateway,
            "_request",
            return_value=(200, {"status": "ok", "service": "checkout"}),
        ):
            with self.assertRaisesRegex(GatewayUnavailable, "health_contract_failure"):
                gateway.health("checkout", case_id="mission-healthy-001")

    def test_child_idempotency_key_matches_checkout_service_derivation(self) -> None:
        parent = "e" * 64
        expected = hashlib.sha256(
            f"{CONTRACT_VERSION}\n{parent}\npayment".encode("ascii")
        ).hexdigest()

        self.assertEqual(derive_child_idempotency_key(parent, "payment"), expected)

    def test_checkout_receipt_uses_service_closed_field_names(self) -> None:
        receipt = {
            "authoritative_result_id": "checkout-result-001",
            "order_id": "synthetic-order-001",
            "completion_class": "COMPLETE",
            "payment_receipt": self._target_receipt("payment", "a", "b"),
            "inventory_receipt": self._target_receipt("inventory", "c", "d"),
            "replayed": False,
        }

        self.assertEqual(validate_checkout_receipt(receipt), receipt)

    def test_checkout_mutation_carries_case_request_and_idempotency_headers(self) -> None:
        gateway = HttpGateway(
            ServiceOrigins(
                checkout="http://checkout:8080",
                payments="http://payments:8081",
                inventory="http://inventory:8082",
            ),
            timeout_seconds=1.0,
        )
        receipt = {
            "authoritative_result_id": "checkout-result-001",
            "order_id": "synthetic-order-001",
            "completion_class": "COMPLETE",
            "payment_receipt": self._target_receipt("payment", "a", "b"),
            "inventory_receipt": self._target_receipt("inventory", "c", "d"),
            "replayed": False,
        }
        with mock.patch.object(gateway, "_request", return_value=(200, receipt)) as request:
            gateway.dispatch_checkout(
                {
                    "order_id": "synthetic-order-001",
                    "amount_cents": 1299,
                    "currency": "USD",
                    "items": [{"sku": "synthetic-sku-001", "quantity": 1}],
                },
                idempotency_key="e" * 64,
                case_id="mission-healthy-001",
                request_id="request-001",
            )

        self.assertEqual(
            request.call_args.kwargs["headers"],
            {
                "Idempotency-Key": "e" * 64,
                "X-Sandbox-Case": "mission-healthy-001",
                "X-Request-ID": "request-001",
            },
        )

    def test_old_uncontracted_receipt_aliases_fail_closed(self) -> None:
        receipt = {
            "authoritative_result_id": "checkout-result-001",
            "order_id": "synthetic-order-001",
            "completion_class": "COMPLETE",
            "payment": self._target_receipt("payment", "a", "b"),
            "inventory": self._target_receipt("inventory", "c", "d"),
            "replayed": False,
        }

        with self.assertRaisesRegex(GatewayError, "checkout_receipt_contract_failure"):
            validate_checkout_receipt(receipt)

    @staticmethod
    def _target_receipt(effect_class: str, key: str, digest: str) -> dict[str, object]:
        return {
            "receipt_version": "synthetic-receipt/v1",
            "effect_class": effect_class,
            "receipt_id": f"{effect_class}-receipt-001",
            "idempotency_key": key * 64,
            "request_digest": digest * 64,
            "status": "committed",
            "replayed": False,
        }


if __name__ == "__main__":
    unittest.main()
