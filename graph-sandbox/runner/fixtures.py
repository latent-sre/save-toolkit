from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from runner.models import SandboxCase
from runner.validation import require_closed_mapping, validate_atomic_id


CASE_KEYS = {
    "case_version",
    "case_id",
    "service_fixtures",
    "checkout",
    "model_fixture",
    "budgets",
}
BUDGET_KINDS = {
    "attempts",
    "wall_time_ms",
    "model_calls",
    "tokens",
    "spend_micro_usd",
}
SERVICES = {"checkout", "payments", "inventory"}
ALLOWED_EFFECTS = {
    "checkout": {"success"},
    "payments": {"success", "latency", "http_error", "ambiguous_after_commit", "duplicate"},
    "inventory": {"success", "http_error", "duplicate"},
}


def load_case(path: Path) -> SandboxCase:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to load sandbox case {path.name}") from exc

    case = require_closed_mapping(raw, field="case", required=CASE_KEYS)
    if case["case_version"] != "graph-sandbox-case/v2":
        raise ValueError("unsupported case_version")
    validate_atomic_id(case["case_id"], "case_id")

    fixtures = require_closed_mapping(
        case["service_fixtures"],
        field="service_fixtures",
        required=SERVICES,
    )
    for service in sorted(SERVICES):
        fixture = require_closed_mapping(
            fixtures[service],
            field=f"service_fixtures.{service}",
            required={"readiness", "effect"},
        )
        if fixture["readiness"] not in {"ready", "unavailable"}:
            raise ValueError(f"service_fixtures.{service}.readiness is unknown")
        if fixture["effect"] not in ALLOWED_EFFECTS[service]:
            raise ValueError(f"service_fixtures.{service}.effect is unknown")

    checkout = require_closed_mapping(
        case["checkout"],
        field="checkout",
        required={"order_id", "amount_cents", "currency", "items"},
    )
    validate_atomic_id(checkout["order_id"], "order_id")
    if not isinstance(checkout["amount_cents"], int) or not 1 <= checkout["amount_cents"] <= 1_000_000:
        raise ValueError("amount_cents must be an integer from 1 through 1000000")
    currency = checkout["currency"]
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isupper():
        raise ValueError("currency must be three uppercase ASCII letters")
    items = checkout["items"]
    if not isinstance(items, list) or not 1 <= len(items) <= 16:
        raise ValueError("items must contain from 1 through 16 entries")
    for index, item in enumerate(items):
        parsed = require_closed_mapping(
            item,
            field=f"items[{index}]",
            required={"sku", "quantity"},
        )
        validate_atomic_id(parsed["sku"], f"items[{index}].sku")
        if not isinstance(parsed["quantity"], int) or not 1 <= parsed["quantity"] <= 100:
            raise ValueError(f"items[{index}].quantity must be from 1 through 100")

    model = require_closed_mapping(
        case["model_fixture"],
        field="model_fixture",
        required={"plan_class", "token_count"},
    )
    if model["plan_class"] != "checkout":
        raise ValueError("model_fixture.plan_class must be checkout")
    if not isinstance(model["token_count"], int) or model["token_count"] < 0:
        raise ValueError("model_fixture.token_count must be a non-negative integer")

    budgets = require_closed_mapping(case["budgets"], field="budgets", required=BUDGET_KINDS)
    for kind, counter in budgets.items():
        parsed = require_closed_mapping(
            counter,
            field=f"budgets.{kind}",
            required={"limit", "consumed"},
        )
        limit = parsed["limit"]
        consumed = parsed["consumed"]
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 0
            or not isinstance(consumed, int)
            or isinstance(consumed, bool)
            or consumed < 0
            or consumed > limit
        ):
            raise ValueError(f"budgets.{kind} must have 0 <= consumed <= limit")

    return cast(SandboxCase, raw)
