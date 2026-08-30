from __future__ import annotations

import json
import hashlib
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from runner.models import CONTRACT_VERSION
from runner.validation import require_closed_mapping, validate_atomic_id, validate_sha256


MAX_RESPONSE_BYTES = 16 * 1024


class GatewayError(RuntimeError):
    def __init__(self, error_class: str) -> None:
        super().__init__(error_class)
        self.error_class = error_class


class GatewayUnavailable(GatewayError):
    def __init__(self, service: str, error_class: str) -> None:
        super().__init__(error_class)
        self.service = service


class AmbiguousDispatch(GatewayError):
    pass


class CheckoutFailure(GatewayError):
    def __init__(
        self,
        error_class: str,
        *,
        outcome: str,
        known_receipts: Mapping[str, object],
    ) -> None:
        super().__init__(error_class)
        self.outcome = outcome
        self.known_receipts = dict(known_receipts)


@dataclass(frozen=True)
class ServiceOrigins:
    checkout: str
    payments: str
    inventory: str

    def __post_init__(self) -> None:
        for field, value in (
            ("checkout", self.checkout),
            ("payments", self.payments),
            ("inventory", self.inventory),
        ):
            if not value.startswith("http://") or value.count("://") != 1:
                raise ValueError(f"{field} URL must use internal plain HTTP")
            if value.endswith("/"):
                object.__setattr__(self, field, value[:-1])


class HttpGateway:
    def __init__(self, origins: ServiceOrigins, *, timeout_seconds: float) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 30:
            raise ValueError("HTTP timeout must be greater than zero and at most 30 seconds")
        self.origins = origins
        self.timeout_seconds = timeout_seconds

    def health(self, service: str, *, case_id: str) -> dict[str, str]:
        validate_atomic_id(service, "service")
        validate_atomic_id(case_id, "case_id")
        if service not in {"checkout", "payments", "inventory"}:
            raise ValueError(f"unknown readiness service: {service}")
        origin = getattr(self.origins, service)
        try:
            status, body = self._request(
                "GET",
                urljoin(f"{origin}/", "healthz"),
                headers={"X-Sandbox-Case": case_id},
            )
        except (GatewayError, OSError, TimeoutError, URLError) as exc:
            raise GatewayUnavailable(service, "health_transport_failure") from exc
        if status != 200:
            raise GatewayUnavailable(service, "health_http_failure")
        try:
            parsed = require_closed_mapping(
                body,
                field="health response",
                required={"status", "service"},
            )
        except ValueError as exc:
            raise GatewayUnavailable(service, "health_contract_failure") from exc
        if parsed["status"] != "ready" or parsed["service"] != service:
            raise GatewayUnavailable(service, "health_contract_failure")
        return {"status": "ok", "service": service}

    def dispatch_checkout(
        self,
        checkout: Mapping[str, object],
        *,
        idempotency_key: str,
        case_id: str,
        request_id: str,
    ) -> dict[str, object]:
        validate_sha256(idempotency_key, "idempotency_key")
        validate_atomic_id(case_id, "case_id")
        validate_atomic_id(request_id, "request_id")
        request_body = {
            "order_id": checkout["order_id"],
            "amount_cents": checkout["amount_cents"],
            "currency": checkout["currency"],
            "items": checkout["items"],
        }
        try:
            status, body = self._request(
                "POST",
                urljoin(f"{self.origins.checkout}/", "checkout"),
                body=request_body,
                headers={
                    "Idempotency-Key": idempotency_key,
                    "X-Sandbox-Case": case_id,
                    "X-Request-ID": request_id,
                },
            )
        except (GatewayError, socket.timeout, TimeoutError, URLError, OSError) as exc:
            raise AmbiguousDispatch("checkout_transport_ambiguous") from exc

        if status == 200:
            return validate_checkout_receipt(body)
        failure = parse_checkout_failure(body)
        outcome = failure.outcome
        if outcome == "unknown":
            raise AmbiguousDispatch("checkout_target_reported_unknown")
        raise failure

    def get_checkout_receipt(
        self,
        idempotency_key: str,
        *,
        case_id: str,
    ) -> dict[str, object] | None:
        validate_sha256(idempotency_key, "idempotency_key")
        validate_atomic_id(case_id, "case_id")
        target = urljoin(
            f"{self.origins.checkout}/",
            f"checkout/receipt?idempotency_key={quote(idempotency_key, safe='')}",
        )
        try:
            status, body = self._request(
                "GET",
                target,
                headers={"X-Sandbox-Case": case_id},
            )
        except (GatewayError, socket.timeout, TimeoutError, URLError, OSError) as exc:
            raise GatewayUnavailable("checkout", "receipt_transport_failure") from exc
        if status == 404:
            if body != {"code": "not_found"}:
                raise GatewayUnavailable("checkout", "receipt_contract_failure")
            return None
        if status in {502, 504}:
            raise parse_checkout_failure(body)
        if status != 200:
            raise GatewayUnavailable("checkout", "receipt_http_failure")
        return validate_checkout_receipt(body)

    def get_target_receipt(
        self,
        effect_class: str,
        checkout_idempotency_key: str,
        *,
        case_id: str,
    ) -> dict[str, object] | None:
        validate_sha256(checkout_idempotency_key, "checkout idempotency_key")
        validate_atomic_id(case_id, "case_id")
        if effect_class == "payment":
            origin = self.origins.payments
            path = "v1/authorizations/receipt"
        elif effect_class == "inventory":
            origin = self.origins.inventory
            path = "v1/reservations/receipt"
        else:
            raise ValueError("effect_class must be payment or inventory")
        child_key = derive_child_idempotency_key(checkout_idempotency_key, effect_class)
        target = urljoin(
            f"{origin}/",
            f"{path}?idempotency_key={quote(child_key, safe='')}",
        )
        try:
            status, body = self._request(
                "GET",
                target,
                headers={"X-Sandbox-Case": case_id},
            )
        except (GatewayError, socket.timeout, TimeoutError, URLError, OSError) as exc:
            raise GatewayUnavailable(effect_class, "receipt_transport_failure") from exc
        if status == 404:
            if body != {"code": "not_found"}:
                raise GatewayUnavailable(effect_class, "receipt_contract_failure")
            return None
        if status != 200:
            raise GatewayUnavailable(effect_class, "receipt_http_failure")
        return validate_target_receipt(body, effect_class, child_key)

    def _request(
        self,
        method: str,
        url: str,
        *,
        body: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[int, object]:
        encoded = None
        request_headers = {"Accept": "application/json", **(headers or {})}
        if body is not None:
            encoded = json.dumps(
                dict(body),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
            if len(encoded) > MAX_RESPONSE_BYTES:
                raise ValueError("checkout request exceeds 16 KiB")
            request_headers["Content-Type"] = "application/json"
        request = Request(url, data=encoded, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status = response.status
                payload = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            status = exc.code
            payload = exc.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise GatewayError("response_too_large")
        try:
            return status, json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise GatewayError("invalid_json_response") from exc

def validate_checkout_receipt(body: object) -> dict[str, object]:
    try:
        parsed = require_closed_mapping(
            body,
            field="checkout receipt",
            required={
                "authoritative_result_id",
                "order_id",
                "completion_class",
                "payment_receipt",
                "inventory_receipt",
                "replayed",
            },
        )
    except ValueError as exc:
        raise GatewayError("checkout_receipt_contract_failure") from exc
    try:
        if parsed["completion_class"] != "COMPLETE":
            raise GatewayError("checkout_receipt_incomplete")
        validate_atomic_id(parsed["authoritative_result_id"], "authoritative_result_id")
        validate_atomic_id(parsed["order_id"], "order_id")
        if not isinstance(parsed["replayed"], bool):
            raise GatewayError("checkout_receipt_contract_failure")
        for effect_class, field_name in (
            ("payment", "payment_receipt"),
            ("inventory", "inventory_receipt"),
        ):
            receipt = validate_target_receipt(parsed[field_name], effect_class)
    except ValueError as exc:
        raise GatewayError("checkout_receipt_contract_failure") from exc
    return dict(parsed)


def validate_target_receipt(
    body: object,
    effect_class: str,
    expected_key: str | None = None,
) -> dict[str, object]:
    try:
        receipt = require_closed_mapping(
            body,
            field=f"{effect_class} receipt",
            required={
                "receipt_version",
                "effect_class",
                "receipt_id",
                "idempotency_key",
                "request_digest",
                "status",
                "replayed",
            },
        )
        if (
            receipt["receipt_version"] != "synthetic-receipt/v1"
            or receipt["effect_class"] != effect_class
            or receipt["status"] != "committed"
            or not isinstance(receipt["replayed"], bool)
        ):
            raise GatewayError(f"{effect_class}_receipt_contract_failure")
        validate_atomic_id(receipt["receipt_id"], f"{effect_class}.receipt_id")
        validate_sha256(receipt["idempotency_key"], f"{effect_class}.idempotency_key")
        validate_sha256(receipt["request_digest"], f"{effect_class}.request_digest")
        if expected_key is not None and receipt["idempotency_key"] != expected_key:
            raise GatewayError(f"{effect_class}_receipt_key_conflict")
    except ValueError as exc:
        raise GatewayError(f"{effect_class}_receipt_contract_failure") from exc
    return dict(receipt)


def parse_checkout_failure(body: object) -> CheckoutFailure:
    try:
        failure = require_closed_mapping(
            body,
            field="checkout failure",
            required={"code", "outcome", "known_receipts"},
        )
        outcome = failure["outcome"]
        if outcome not in {"not_committed", "partial", "unknown"}:
            raise ValueError("checkout failure outcome is unknown")
        code = validate_atomic_id(failure["code"], "checkout failure code")
        raw_known = failure["known_receipts"]
        if not isinstance(raw_known, Mapping):
            raise ValueError("known_receipts must be an object")
        if set(raw_known) - {"payment", "inventory"}:
            raise ValueError("known_receipts contains an unknown effect class")
        known = {
            effect_class: validate_target_receipt(receipt, effect_class)
            for effect_class, receipt in raw_known.items()
        }
    except (GatewayError, ValueError) as exc:
        raise AmbiguousDispatch("checkout_failure_contract_unknown") from exc
    return CheckoutFailure(code, outcome=outcome, known_receipts=known)


def derive_child_idempotency_key(parent_key: str, effect_class: str) -> str:
    validate_sha256(parent_key, "checkout idempotency_key")
    if effect_class not in {"payment", "inventory"}:
        raise ValueError("effect_class must be payment or inventory")
    material = f"{CONTRACT_VERSION}\n{parent_key}\n{effect_class}".encode("ascii")
    return hashlib.sha256(material).hexdigest()
