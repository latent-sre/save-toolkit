"""Tests for order_schema module."""

import json
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from order_schema import Order, OrderPayload, OrderSchema, validate_order


@pytest.fixture
def valid_payload_dict():
    return {
        "order_id": "ord-12345",
        "symbol": "AAPL",
        "quantity": 100,
        "limit_price": "150.25",
        "submitted_at": "2026-10-25T14:30:00Z",
        "tags": ["retail", "algorithmic"],
    }


def test_valid_order_from_dict(valid_payload_dict):
    order = validate_order(valid_payload_dict)
    assert order.order_id == "ord-12345"
    assert order.symbol == "AAPL"
    assert order.quantity == 100
    assert order.limit_price == Decimal("150.25")
    assert order.submitted_at == datetime(2026, 10, 25, 14, 30, 0, tzinfo=UTC)
    assert order.tags == ["retail", "algorithmic"]


def test_valid_order_from_json(valid_payload_dict):
    json_str = json.dumps(valid_payload_dict)
    order = validate_order(json_str)
    assert order.order_id == "ord-12345"
    assert order.limit_price == Decimal("150.25")


def test_valid_order_direct_instantiation():
    tz = timezone(timedelta(hours=-5))
    dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=tz)
    order = OrderSchema(
        order_id="x1",
        symbol="GOOGL",
        quantity=1,
        limit_price=Decimal("2500.5"),
        submitted_at=dt,
        tags=[],
    )
    assert order.quantity == 1
    assert order.limit_price == Decimal("2500.5")
    assert order.submitted_at == dt
    assert order.tags == []
    # Test aliases
    assert Order is OrderSchema
    assert OrderPayload is OrderSchema


def test_invalid_quantity_zero_or_negative(valid_payload_dict):
    payload = valid_payload_dict.copy()
    payload["quantity"] = 0
    with pytest.raises(ValidationError) as exc:
        validate_order(payload)
    assert "quantity" in str(exc.value)

    payload["quantity"] = -5
    with pytest.raises(ValidationError) as exc:
        validate_order(payload)
    assert "quantity" in str(exc.value)


def test_invalid_quantity_non_int(valid_payload_dict):
    payload = valid_payload_dict.copy()
    payload["quantity"] = "not_an_int"
    with pytest.raises(ValidationError):
        validate_order(payload)


def test_invalid_limit_price_zero_or_negative(valid_payload_dict):
    payload = valid_payload_dict.copy()
    payload["limit_price"] = "0"
    with pytest.raises(ValidationError) as exc:
        validate_order(payload)
    assert "limit_price" in str(exc.value)

    payload["limit_price"] = "-10.50"
    with pytest.raises(ValidationError) as exc:
        validate_order(payload)
    assert "limit_price" in str(exc.value)


def test_invalid_limit_price_decimal_places(valid_payload_dict):
    payload = valid_payload_dict.copy()
    payload["limit_price"] = "150.255"  # 3 decimal places
    with pytest.raises(ValidationError) as exc:
        validate_order(payload)
    assert "limit_price" in str(exc.value)


def test_invalid_submitted_at_naive_datetime(valid_payload_dict):
    payload = valid_payload_dict.copy()
    payload["submitted_at"] = "2026-10-25T14:30:00"  # Missing timezone
    with pytest.raises(ValidationError) as exc:
        validate_order(payload)
    assert "submitted_at" in str(exc.value)


def test_invalid_submitted_at_malformed(valid_payload_dict):
    payload = valid_payload_dict.copy()
    payload["submitted_at"] = "not-a-datetime"
    with pytest.raises(ValidationError):
        validate_order(payload)


def test_invalid_tags_type(valid_payload_dict):
    payload = valid_payload_dict.copy()
    payload["tags"] = "not-a-list"
    with pytest.raises(ValidationError):
        validate_order(payload)

    payload["tags"] = [None]
    with pytest.raises(ValidationError):
        validate_order(payload)


def test_missing_required_fields(valid_payload_dict):
    for key in valid_payload_dict:
        payload = valid_payload_dict.copy()
        del payload[key]
        with pytest.raises(ValidationError) as exc:
            validate_order(payload)
        assert key in str(exc.value)


def test_extra_fields_forbidden(valid_payload_dict):
    payload = valid_payload_dict.copy()
    payload["extra_field"] = "unexpected"
    with pytest.raises(ValidationError):
        validate_order(payload)
