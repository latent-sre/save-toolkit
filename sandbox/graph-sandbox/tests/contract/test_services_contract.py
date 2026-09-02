"""Container-only contract tests for the durable synthetic services.

Host discovery intentionally skips this module before importing FastAPI application code. The
reviewed services image sets ``GRAPH_SANDBOX_CONTAINER=1`` and runs these tests in-container.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


CONTAINER_ONLY = os.environ.get("GRAPH_SANDBOX_CONTAINER") == "1"
CASE_ID = "mission-healthy-001"


def headers(key: str, *, case_id: str = CASE_ID) -> dict[str, str]:
    return {
        "Idempotency-Key": key,
        "X-Request-ID": f"request-{key}",
        "X-Sandbox-Case": case_id,
    }


@unittest.skipUnless(CONTAINER_ONLY, "synthetic application code executes only in its container")
class ServiceConfigurationTests(unittest.TestCase):
    def test_environment_contract_is_closed_and_required(self) -> None:
        from sandbox_services.common import ServiceConfig

        configured = ServiceConfig.from_values(
            service="payments",
            sandbox_case_id=CASE_ID,
            readiness_fixture="ready",
            effect_fixture="success",
            data_db="/data/payments.sqlite3",
        )

        self.assertEqual(configured.sandbox_case_id, CASE_ID)
        with patch.dict(
            os.environ,
            {
                "SANDBOX_CASE_ID": CASE_ID,
                "READINESS_FIXTURE": "ready",
                "EFFECT_FIXTURE": "success",
                "DATA_DB": "/data/payments.sqlite3",
            },
            clear=True,
        ):
            self.assertEqual(ServiceConfig.from_environment("payments"), configured)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "missing required service environment"):
                ServiceConfig.from_environment("payments")
        with self.assertRaisesRegex(ValueError, "SANDBOX_CASE_ID"):
            ServiceConfig.from_values(
                service="payments",
                sandbox_case_id="unknown-case-001",
                readiness_fixture="ready",
                effect_fixture="success",
                data_db="/data/payments.sqlite3",
            )
        with self.assertRaisesRegex(ValueError, "READINESS_FIXTURE"):
            ServiceConfig.from_values(
                service="payments",
                sandbox_case_id=CASE_ID,
                readiness_fixture="healthy",
                effect_fixture="success",
                data_db="/data/payments.sqlite3",
            )
        with self.assertRaisesRegex(ValueError, "EFFECT_FIXTURE"):
            ServiceConfig.from_values(
                service="payments",
                sandbox_case_id=CASE_ID,
                readiness_fixture="ready",
                effect_fixture="inventory_error",
                data_db="/data/payments.sqlite3",
            )


@unittest.skipUnless(CONTAINER_ONLY, "synthetic application code executes only in its container")
class DurableStoreTests(unittest.TestCase):
    def test_target_receipt_survives_reopen_and_changed_body_conflicts(self) -> None:
        from sandbox_services.common import IdempotencyConflict, ReceiptStore

        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "payments.sqlite3"
            first_store = ReceiptStore(database)
            first = first_store.commit(
                effect_class="payment",
                idempotency_key="payment-key-restart",
                request_digest="a" * 64,
            )

            reopened = ReceiptStore(database)
            stored = reopened.get("payment-key-restart")
            replay = reopened.commit(
                effect_class="payment",
                idempotency_key="payment-key-restart",
                request_digest="a" * 64,
            )

            self.assertIsNotNone(stored)
            self.assertEqual(stored.receipt_id, first.receipt_id)
            self.assertEqual(replay.receipt_id, first.receipt_id)
            self.assertTrue(replay.replayed)
            with self.assertRaises(IdempotencyConflict):
                reopened.commit(
                    effect_class="payment",
                    idempotency_key="payment-key-restart",
                    request_digest="b" * 64,
                )

    def test_checkout_record_survives_reopen_and_changed_body_conflicts(self) -> None:
        from sandbox_services.common import CheckoutRecordStore, IdempotencyConflict

        body = {"code": "payment_transport_failure", "outcome": "unknown", "known_receipts": {}}
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "checkout.sqlite3"
            first_store = CheckoutRecordStore(database)
            first_store.put("checkout-key-restart", "c" * 64, body)

            reopened = CheckoutRecordStore(database)
            self.assertEqual(reopened.get("checkout-key-restart", "c" * 64), body)
            with self.assertRaises(IdempotencyConflict):
                reopened.get("checkout-key-restart", "d" * 64)
            with self.assertRaises(IdempotencyConflict):
                reopened.put("checkout-key-restart", "d" * 64, body)


@unittest.skipUnless(CONTAINER_ONLY, "synthetic application code executes only in its container")
class TargetServiceContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_case_mismatch_is_rejected_before_store_access(self) -> None:
        import httpx

        from sandbox_services.common import ReceiptStore, ServiceConfig
        from sandbox_services.payments import create_app

        with tempfile.TemporaryDirectory() as temporary:
            store = ReceiptStore(Path(temporary) / "payments.sqlite3")
            app = create_app(
                config=ServiceConfig.for_test(
                    "payments", CASE_ID, Path(temporary) / "payments.sqlite3"
                ),
                store=store,
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://payments"
            ) as client:
                response = await client.post(
                    "/v1/authorizations",
                    headers=headers("payment-key-mismatch", case_id="payments-http-error-001"),
                    json={"order_id": "order-001", "amount_cents": 1299, "currency": "USD"},
                )

            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {"code": "invalid_sandbox_case"})
            self.assertIsNone(store.get("payment-key-mismatch"))

    async def test_livez_is_unfaulted_and_healthz_reports_projected_readiness(self) -> None:
        import httpx

        from sandbox_services.common import ServiceConfig
        from sandbox_services.payments import create_app

        with tempfile.TemporaryDirectory() as temporary:
            ready = create_app(
                config=ServiceConfig.for_test(
                    "payments", CASE_ID, Path(temporary) / "ready.sqlite3"
                )
            )
            unavailable = create_app(
                config=ServiceConfig.for_test(
                    "payments",
                    "checkout-readiness-failure-001",
                    Path(temporary) / "unavailable.sqlite3",
                    readiness_fixture="unavailable",
                )
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=ready), base_url="http://payments"
            ) as client:
                ready_response = await client.get("/livez")
                ready_health = await client.get(
                    "/healthz",
                    headers={"X-Sandbox-Case": CASE_ID},
                )
                missing_case_health = await client.get("/healthz")
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=unavailable), base_url="http://payments"
            ) as client:
                unavailable_response = await client.get("/livez")
                unavailable_health = await client.get(
                    "/healthz",
                    headers={"X-Sandbox-Case": "checkout-readiness-failure-001"},
                )

            self.assertEqual(ready_response.status_code, 200)
            self.assertEqual(ready_health.status_code, 200)
            self.assertEqual(ready_health.json(), {"status": "ready", "service": "payments"})
            self.assertEqual(missing_case_health.status_code, 422)
            self.assertEqual(unavailable_response.status_code, 200)
            self.assertEqual(unavailable_health.status_code, 503)

    async def test_payments_real_projected_faults_are_reachable(self) -> None:
        import time

        import httpx

        from sandbox_services.common import ReceiptStore, ServiceConfig
        from sandbox_services.payments import LATENCY_SECONDS, create_app

        body = {"order_id": "order-faults", "amount_cents": 1299, "currency": "USD"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            http_store = ReceiptStore(root / "http.sqlite3")
            http_app = create_app(
                config=ServiceConfig.for_test(
                    "payments", "payments-http-error-001", root / "http.sqlite3",
                    effect_fixture="http_error",
                ),
                store=http_store,
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=http_app), base_url="http://payments"
            ) as client:
                http_error = await client.post(
                    "/v1/authorizations",
                    headers=headers("payment-key-http", case_id="payments-http-error-001"),
                    json=body,
                )

            latency_app = create_app(
                config=ServiceConfig.for_test(
                    "payments", "payments-latency-001", root / "latency.sqlite3",
                    effect_fixture="latency",
                )
            )
            started = time.monotonic()
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=latency_app), base_url="http://payments"
            ) as client:
                latency = await client.post(
                    "/v1/authorizations",
                    headers=headers("payment-key-latency", case_id="payments-latency-001"),
                    json=body,
                )
            elapsed = time.monotonic() - started

            duplicate_app = create_app(
                config=ServiceConfig.for_test(
                    "payments", "duplicate-effect-001", root / "duplicate.sqlite3",
                    effect_fixture="duplicate",
                )
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=duplicate_app), base_url="http://payments"
            ) as client:
                duplicate = await client.post(
                    "/v1/authorizations",
                    headers=headers("payment-key-duplicate", case_id="duplicate-effect-001"),
                    json=body,
                )

            self.assertEqual(http_error.status_code, 503)
            self.assertIsNone(http_store.get("payment-key-http"))
            self.assertEqual(latency.status_code, 200)
            self.assertGreaterEqual(elapsed, LATENCY_SECONDS * 0.9)
            self.assertEqual(duplicate.status_code, 200)
            self.assertTrue(duplicate.json()["replayed"])

    async def test_payment_ambiguous_commit_survives_service_restart_and_full_lookup(self) -> None:
        import httpx

        from sandbox_services.common import ServiceConfig
        from sandbox_services.payments import create_app

        case_id = "payments-ambiguous-after-commit-001"
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "payments.sqlite3"
            config = ServiceConfig.for_test(
                "payments", case_id, database, effect_fixture="ambiguous_after_commit"
            )
            first_app = create_app(config=config)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=first_app), base_url="http://payments"
            ) as client:
                with self.assertRaisesRegex(RuntimeError, "synthetic_response_lost_after_commit"):
                    await client.post(
                        "/v1/authorizations",
                        headers=headers("payment-key-lost", case_id=case_id),
                        json={"order_id": "order-lost", "amount_cents": 1299, "currency": "USD"},
                    )

            restarted_app = create_app(config=config)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=restarted_app), base_url="http://payments"
            ) as client:
                receipt = await client.get(
                    "/v1/authorizations/receipt",
                    params={"idempotency_key": "payment-key-lost"},
                    headers={"X-Sandbox-Case": case_id},
                )
                conflict = await client.post(
                    "/v1/authorizations",
                    headers=headers("payment-key-lost", case_id=case_id),
                    json={"order_id": "order-lost", "amount_cents": 1300, "currency": "USD"},
                )

            self.assertEqual(receipt.status_code, 200)
            self.assertEqual(receipt.json()["status"], "committed")
            self.assertEqual(receipt.json()["idempotency_key"], "payment-key-lost")
            self.assertEqual(conflict.status_code, 409)

    async def test_inventory_receipt_survives_service_restart_and_conflict_detection(self) -> None:
        import httpx

        from sandbox_services.common import ServiceConfig
        from sandbox_services.inventory import create_app

        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "inventory.sqlite3"
            config = ServiceConfig.for_test("inventory", CASE_ID, database)
            first_app = create_app(config=config)
            request_body = {
                "order_id": "order-inventory-restart",
                "items": [{"sku": "sku-001", "quantity": 1}],
            }
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=first_app), base_url="http://inventory"
            ) as client:
                first = await client.post(
                    "/v1/reservations",
                    headers=headers("inventory-key-restart"),
                    json=request_body,
                )

            restarted_app = create_app(config=config)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=restarted_app), base_url="http://inventory"
            ) as client:
                receipt = await client.get(
                    "/v1/reservations/receipt",
                    params={"idempotency_key": "inventory-key-restart"},
                    headers={"X-Sandbox-Case": CASE_ID},
                )
                replay = await client.post(
                    "/v1/reservations",
                    headers=headers("inventory-key-restart"),
                    json=request_body,
                )
                conflict = await client.post(
                    "/v1/reservations",
                    headers=headers("inventory-key-restart"),
                    json={
                        "order_id": "order-inventory-restart",
                        "items": [{"sku": "sku-001", "quantity": 2}],
                    },
                )

            self.assertEqual(first.status_code, 200)
            self.assertEqual(receipt.json()["receipt_id"], first.json()["receipt_id"])
            self.assertTrue(replay.json()["replayed"])
            self.assertEqual(conflict.status_code, 409)

    async def test_inventory_failure_after_payment_keeps_payment_receipt(self) -> None:
        import httpx

        from sandbox_services.checkout import create_app as create_checkout
        from sandbox_services.common import ServiceConfig
        from sandbox_services.inventory import create_app as create_inventory
        from sandbox_services.payments import create_app as create_payments

        case_id = "inventory-http-error-after-payment-001"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payment_client = httpx.AsyncClient(
                transport=httpx.ASGITransport(
                    app=create_payments(
                        config=ServiceConfig.for_test(
                            "payments", case_id, root / "payments.sqlite3"
                        )
                    )
                ),
                base_url="http://payments",
            )
            inventory_client = httpx.AsyncClient(
                transport=httpx.ASGITransport(
                    app=create_inventory(
                        config=ServiceConfig.for_test(
                            "inventory", case_id, root / "inventory.sqlite3",
                            effect_fixture="http_error",
                        )
                    )
                ),
                base_url="http://inventory",
            )
            checkout_app = create_checkout(
                config=ServiceConfig.for_test("checkout", case_id, root / "checkout.sqlite3"),
                payments_client=payment_client,
                inventory_client=inventory_client,
            )
            try:
                async with checkout_app.router.lifespan_context(checkout_app):
                    async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=checkout_app),
                        base_url="http://checkout",
                    ) as client:
                        response = await client.post(
                            "/checkout",
                            headers=headers("checkout-key-partial", case_id=case_id),
                            json={
                                "order_id": "order-partial",
                                "amount_cents": 1299,
                                "currency": "USD",
                                "items": [{"sku": "sku-001", "quantity": 1}],
                            },
                        )
                        lookup = await client.get(
                            "/checkout/receipt",
                            params={"idempotency_key": "checkout-key-partial"},
                            headers={"X-Sandbox-Case": case_id},
                        )
            finally:
                await payment_client.aclose()
                await inventory_client.aclose()

            self.assertEqual(response.status_code, 502)
            self.assertEqual(response.json()["outcome"], "partial")
            self.assertEqual(set(response.json()["known_receipts"]), {"payment"})
            self.assertEqual(lookup.status_code, response.status_code)
            self.assertEqual(lookup.json(), response.json())


@unittest.skipUnless(CONTAINER_ONLY, "synthetic application code executes only in its container")
class CheckoutServiceContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_checkout_commit_survives_lost_response_without_redispatch(self) -> None:
        import httpx

        from sandbox_services.checkout import create_app
        from sandbox_services.common import ServiceConfig

        case_id = "checkout-ambiguous-after-commit-001"
        target_calls: list[str] = []

        def target(effect_class: str):
            def handle(request: httpx.Request) -> httpx.Response:
                target_calls.append(effect_class)
                return httpx.Response(
                    200,
                    json={
                        "receipt_version": "synthetic-receipt/v1",
                        "effect_class": effect_class,
                        "receipt_id": f"{effect_class}-receipt-lost",
                        "idempotency_key": request.headers["Idempotency-Key"],
                        "request_digest": "a" * 64,
                        "status": "committed",
                        "replayed": False,
                    },
                )

            return handle

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payment_client = httpx.AsyncClient(
                transport=httpx.MockTransport(target("payment")),
                base_url="http://payments",
            )
            inventory_client = httpx.AsyncClient(
                transport=httpx.MockTransport(target("inventory")),
                base_url="http://inventory",
            )
            config = ServiceConfig.for_test(
                "checkout",
                case_id,
                root / "checkout.sqlite3",
                effect_fixture="ambiguous_after_commit",
            )
            checkout_app = create_app(
                config=config,
                payments_client=payment_client,
                inventory_client=inventory_client,
            )
            request_headers = headers("checkout-key-lost", case_id=case_id)
            request_body = {
                "order_id": "order-checkout-lost",
                "amount_cents": 1299,
                "currency": "USD",
                "items": [{"sku": "sku-001", "quantity": 1}],
            }
            try:
                async with checkout_app.router.lifespan_context(checkout_app):
                    async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=checkout_app),
                        base_url="http://checkout",
                    ) as client:
                        with self.assertRaisesRegex(
                            RuntimeError,
                            "synthetic_checkout_response_lost_after_commit",
                        ):
                            await client.post(
                                "/checkout",
                                headers=request_headers,
                                json=request_body,
                            )
                        receipt = await client.get(
                            "/checkout/receipt",
                            params={"idempotency_key": "checkout-key-lost"},
                            headers={"X-Sandbox-Case": case_id},
                        )
                        replay = await client.post(
                            "/checkout",
                            headers=request_headers,
                            json=request_body,
                        )
            finally:
                await payment_client.aclose()
                await inventory_client.aclose()

            self.assertEqual(receipt.status_code, 200)
            self.assertEqual(receipt.json()["completion_class"], "COMPLETE")
            self.assertTrue(replay.json()["replayed"])
            self.assertEqual(target_calls, ["payment", "inventory"])

    async def test_checkout_forwards_case_and_persists_success_across_restart(self) -> None:
        import httpx

        from sandbox_services.checkout import create_app
        from sandbox_services.common import ServiceConfig

        observed: list[tuple[str, str]] = []

        def target(effect_class: str):
            def handle(request: httpx.Request) -> httpx.Response:
                observed.append(
                    (request.headers["X-Sandbox-Case"], request.headers["X-Request-ID"])
                )
                key = request.headers["Idempotency-Key"]
                return httpx.Response(
                    200,
                    json={
                        "receipt_version": "synthetic-receipt/v1",
                        "effect_class": effect_class,
                        "receipt_id": f"{effect_class}-receipt",
                        "idempotency_key": key,
                        "request_digest": "a" * 64,
                        "status": "committed",
                        "replayed": False,
                    },
                )

            return handle

        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "checkout.sqlite3"
            config = ServiceConfig.for_test("checkout", CASE_ID, database)
            payment_client = httpx.AsyncClient(
                transport=httpx.MockTransport(target("payment")), base_url="http://payments"
            )
            inventory_client = httpx.AsyncClient(
                transport=httpx.MockTransport(target("inventory")), base_url="http://inventory"
            )
            first_app = create_app(
                config=config,
                payments_client=payment_client,
                inventory_client=inventory_client,
            )
            request_headers = headers("checkout-key-restart")
            request_body = {
                "order_id": "order-restart",
                "amount_cents": 1299,
                "currency": "USD",
                "items": [{"sku": "sku-001", "quantity": 1}],
            }
            async with first_app.router.lifespan_context(first_app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=first_app), base_url="http://checkout"
                ) as client:
                    first = await client.post(
                        "/checkout", headers=request_headers, json=request_body
                    )

            restarted_app = create_app(
                config=config,
                payments_client=payment_client,
                inventory_client=inventory_client,
            )
            async with restarted_app.router.lifespan_context(restarted_app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=restarted_app), base_url="http://checkout"
                ) as client:
                    replay = await client.post(
                        "/checkout", headers=request_headers, json=request_body
                    )
                    lookup = await client.get(
                        "/checkout/receipt",
                        params={"idempotency_key": "checkout-key-restart"},
                        headers={"X-Sandbox-Case": CASE_ID},
                    )
                    conflict = await client.post(
                        "/checkout",
                        headers=request_headers,
                        json={**request_body, "amount_cents": 1300},
                    )

            await payment_client.aclose()
            await inventory_client.aclose()
            self.assertEqual(first.status_code, 200)
            self.assertTrue(replay.json()["replayed"])
            self.assertEqual(
                lookup.json()["authoritative_result_id"], first.json()["authoritative_result_id"]
            )
            self.assertEqual(conflict.status_code, 409)
            self.assertEqual(observed, [(CASE_ID, request_headers["X-Request-ID"])] * 2)


if __name__ == "__main__":
    unittest.main()
