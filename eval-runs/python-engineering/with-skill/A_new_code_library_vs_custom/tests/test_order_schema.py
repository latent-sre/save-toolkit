"""Tests for order_schema."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from order_schema import Order, validate_order


def test_valid_order_from_dict() -> None:
    data = {
        "order_id": "ORD-001",
        "symbol": "AAPL",
        "quantity": 100,
        "limit_price": "185.50",
        "submitted_at": "2026-10-25T14:30:00+00:00",
        "tags": ["equity", "nasdaq"],
    }
    order = validate_order(data)
    assert order.order_id == "ORD-001"
    assert order.symbol == "AAPL"
    assert order.quantity == 100
    assert order.limit_price == Decimal("185.50")
    assert order.submitted_at.tzinfo is not None
    assert order.tags == ["equity", "nasdaq"]


def test_valid_order_from_json_string() -> None:
    raw_json = json.dumps(
        {
            "order_id": "ORD-002",
            "symbol": "GOOGL",
            "quantity": 50,
            "limit_price": "175.00",
            "submitted_at": "2026-10-25T14:30:00Z",
            "tags": [],
        }
    )
    order = validate_order(raw_json)
    assert order.order_id == "ORD-002"
    assert order.quantity == 50
    assert order.limit_price == Decimal("175.00")
    assert order.tags == []


def test_valid_order_direct_model_instantiation() -> None:
    now = datetime.now(UTC)
    order = Order(
        order_id="ORD-003",
        symbol="MSFT",
        quantity=10,
        limit_price=Decimal("420.15"),
        submitted_at=now,
        tags=["core"],
    )
    assert order.order_id == "ORD-003"
    assert order.quantity == 10
    assert order.limit_price == Decimal("420.15")
    assert order.submitted_at == now


@pytest.mark.parametrize(
    "invalid_quantity",
    [0, -1, -100],
)
def test_reject_quantity_non_positive(invalid_quantity: int) -> None:
    data = {
        "order_id": "ORD-1",
        "symbol": "AAPL",
        "quantity": invalid_quantity,
        "limit_price": "100.00",
        "submitted_at": "2026-10-25T12:00:00Z",
        "tags": [],
    }
    with pytest.raises(ValidationError):
        validate_order(data)


def test_reject_boolean_quantity() -> None:
    data = {
        "order_id": "ORD-1",
        "symbol": "AAPL",
        "quantity": True,
        "limit_price": "100.00",
        "submitted_at": "2026-10-25T12:00:00Z",
        "tags": [],
    }
    with pytest.raises(ValidationError):
        validate_order(data)


@pytest.mark.parametrize(
    "invalid_price",
    ["0.00", "-5.00", "100.999", "10.1234"],
)
def test_reject_invalid_limit_price(invalid_price: str) -> None:
    data = {
        "order_id": "ORD-1",
        "symbol": "AAPL",
        "quantity": 10,
        "limit_price": invalid_price,
        "submitted_at": "2026-10-25T12:00:00Z",
        "tags": [],
    }
    with pytest.raises(ValidationError):
        validate_order(data)


def test_reject_naive_datetime() -> None:
    data = {
        "order_id": "ORD-1",
        "symbol": "AAPL",
        "quantity": 10,
        "limit_price": "100.00",
        "submitted_at": "2026-10-25T12:00:00",  # No timezone
        "tags": [],
    }
    with pytest.raises(ValidationError):
        validate_order(data)


def test_reject_invalid_tags() -> None:
    data = {
        "order_id": "ORD-1",
        "symbol": "AAPL",
        "quantity": 10,
        "limit_price": "100.00",
        "submitted_at": "2026-10-25T12:00:00Z",
        "tags": [123],  # Not strings
    }
    with pytest.raises(ValidationError):
        validate_order(data)


def test_reject_missing_fields() -> None:
    data = {
        "order_id": "ORD-1",
        "symbol": "AAPL",
    }
    with pytest.raises(ValidationError):
        validate_order(data)
