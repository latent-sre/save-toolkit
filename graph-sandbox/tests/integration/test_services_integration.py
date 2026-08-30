"""Real internal-HTTP seams for the running Compose topology."""

from __future__ import annotations

import os
import unittest


INTEGRATION_ENABLED = (
    os.environ.get("GRAPH_SANDBOX_CONTAINER") == "1"
    and os.environ.get("GRAPH_SANDBOX_INTEGRATION") == "1"
)


@unittest.skipUnless(INTEGRATION_ENABLED, "requires the reviewed internal Compose topology")
class ServicesIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_services_expose_real_internal_livez(self) -> None:
        import httpx

        async with httpx.AsyncClient(timeout=2.0) as client:
            responses = [
                await client.get("http://checkout:8080/livez"),
                await client.get("http://payments:8081/livez"),
                await client.get("http://inventory:8082/livez"),
            ]

        self.assertTrue(all(response.status_code == 200 for response in responses))

    async def test_healthy_checkout_crosses_real_http_and_reads_full_receipt(self) -> None:
        import httpx

        case_id = os.environ["SANDBOX_CASE_ID"]
        self.assertEqual(case_id, "mission-healthy-001")
        body = {
            "order_id": "synthetic-order-integration-001",
            "amount_cents": 1299,
            "currency": "USD",
            "items": [{"sku": "synthetic-sku-001", "quantity": 1}],
        }
        request_headers = {
            "Idempotency-Key": "integration-checkout-key-001",
            "X-Request-ID": "integration-request-001",
            "X-Sandbox-Case": case_id,
        }
        async with httpx.AsyncClient(base_url="http://checkout:8080", timeout=5.0) as client:
            response = await client.post("/checkout", headers=request_headers, json=body)
            receipt = await client.get(
                "/checkout/receipt",
                params={"idempotency_key": "integration-checkout-key-001"},
                headers={"X-Sandbox-Case": case_id},
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["completion_class"], "COMPLETE")
        self.assertEqual(result["payment_receipt"]["effect_class"], "payment")
        self.assertEqual(result["inventory_receipt"]["effect_class"], "inventory")
        self.assertEqual(
            receipt.json()["authoritative_result_id"], result["authoritative_result_id"]
        )


if __name__ == "__main__":
    unittest.main()
