from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from order_schema import OrderPayload, validate_order_payload


def test_valid_order_payload() -> None:
    now = datetime.now(UTC)
    payload = {
        "order_id": "  ORD-123  ",
        "symbol": "AAPL",
        "quantity": 50,
        "limit_price": Decimal("145.50"),
        "submitted_at": now,
        "tags": ["retail", "urgent"],
    }
    result = validate_order_payload(payload)
    assert isinstance(result, OrderPayload)
    assert result.order_id == "ORD-123"
    assert result.symbol == "AAPL"
    assert result.quantity == 50
    assert result.limit_price == Decimal("145.50")
    assert result.submitted_at == now
    assert result.tags == ["retail", "urgent"]
    # Dict-like access
    assert result["order_id"] == "ORD-123"
    assert result.get("symbol") == "AAPL"
    assert "order_id" in result


def test_order_id_empty_or_whitespace_rejected() -> None:
    now = datetime.now(UTC)
    base = {
        "order_id": "   ",
        "symbol": "AAPL",
        "quantity": 10,
        "limit_price": Decimal("10.00"),
        "submitted_at": now,
        "tags": [],
    }
    with pytest.raises(ValidationError):
        validate_order_payload(base)

    base["order_id"] = ""
    with pytest.raises(ValidationError):
        validate_order_payload(base)


def test_symbol_uppercase_ascii() -> None:
    now = datetime.now(UTC)
    base = {
        "order_id": "ORD-1",
        "symbol": "aapl",
        "quantity": 10,
        "limit_price": Decimal("10.00"),
        "submitted_at": now,
        "tags": [],
    }
    # Lowercase rejected
    with pytest.raises(ValidationError):
        validate_order_payload(base)

    # Non-ASCII rejected
    base["symbol"] = "ÉÉÉ"
    with pytest.raises(ValidationError):
        validate_order_payload(base)


def test_quantity_int_greater_than_zero_rejects_bool() -> None:
    now = datetime.now(UTC)
    base = {
        "order_id": "ORD-1",
        "symbol": "AAPL",
        "quantity": 0,
        "limit_price": Decimal("10.00"),
        "submitted_at": now,
        "tags": [],
    }
    # 0 rejected
    with pytest.raises(ValidationError):
        validate_order_payload(base)

    # negative rejected
    base["quantity"] = -5
    with pytest.raises(ValidationError):
        validate_order_payload(base)

    # bool True rejected
    base["quantity"] = True
    with pytest.raises(ValidationError):
        validate_order_payload(base)

    # bool False rejected
    base["quantity"] = False
    with pytest.raises(ValidationError):
        validate_order_payload(base)


def test_limit_price_decimal_greater_than_zero_rejects_float() -> None:
    now = datetime.now(UTC)
    base = {
        "order_id": "ORD-1",
        "symbol": "AAPL",
        "quantity": 10,
        "limit_price": 10.50,  # float rejected
        "submitted_at": now,
        "tags": [],
    }
    with pytest.raises(ValidationError):
        validate_order_payload(base)

    # Zero rejected
    base["limit_price"] = Decimal(0)
    with pytest.raises(ValidationError):
        validate_order_payload(base)

    # Negative rejected
    base["limit_price"] = Decimal("-1.00")
    with pytest.raises(ValidationError):
        validate_order_payload(base)

    # More than 2 decimal places rejected
    base["limit_price"] = Decimal("10.125")
    with pytest.raises(ValidationError):
        validate_order_payload(base)


def test_submitted_at_requires_timezone() -> None:
    naive_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=None)
    base = {
        "order_id": "ORD-1",
        "symbol": "AAPL",
        "quantity": 10,
        "limit_price": Decimal("10.00"),
        "submitted_at": naive_now,
        "tags": [],
    }
    with pytest.raises(ValidationError):
        validate_order_payload(base)


def test_tags_must_be_list_of_strings() -> None:
    now = datetime.now(UTC)
    base = {
        "order_id": "ORD-1",
        "symbol": "AAPL",
        "quantity": 10,
        "limit_price": Decimal("10.00"),
        "submitted_at": now,
        "tags": ["good", 123],
    }
    with pytest.raises(ValidationError):
        validate_order_payload(base)


def test_payload_not_dict_rejected() -> None:
    with pytest.raises(TypeError):
        validate_order_payload("not a dict")  # type: ignore[arg-type]
