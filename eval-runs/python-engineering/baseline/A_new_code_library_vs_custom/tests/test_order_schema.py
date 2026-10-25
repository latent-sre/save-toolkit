"""Unit tests for validate_order_payload in order_schema."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from order_schema import OrderPayload, validate_order_payload


@pytest.fixture
def valid_payload() -> dict[str, object]:
    return {
        "order_id": "ORD-12345",
        "symbol": "AAPL",
        "quantity": 100,
        "limit_price": Decimal("150.25"),
        "submitted_at": datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC),
        "tags": ["retail", "urgent"],
    }


def test_valid_payload_success(valid_payload):
    result = validate_order_payload(valid_payload)
    assert isinstance(result, OrderPayload)
    assert result.order_id == "ORD-12345"
    assert result.symbol == "AAPL"
    assert result.quantity == 100
    assert result.limit_price == Decimal("150.25")
    assert result.submitted_at == datetime(2026, 10, 25, 12, 0, 0, tzinfo=UTC)
    assert result.tags == ["retail", "urgent"]

    # Mapping / item access compatibility
    assert result["order_id"] == "ORD-12345"
    assert result["symbol"] == "AAPL"
    assert "quantity" in result
    assert result.get("limit_price") == Decimal("150.25")
    assert list(result.keys()) == ["order_id", "symbol", "quantity", "limit_price", "submitted_at", "tags"]


def test_order_id_stripping_and_non_empty(valid_payload):
    valid_payload["order_id"] = "   ORD-999   "
    result = validate_order_payload(valid_payload)
    assert result.order_id == "ORD-999"

    for invalid_id in ["", "   ", "\t\n", None, 12345]:
        valid_payload["order_id"] = invalid_id
        with pytest.raises((ValueError, TypeError, ValidationError)):
            validate_order_payload(valid_payload)


def test_symbol_uppercase_ascii(valid_payload):
    for valid_symbol in ["AAPL", "MSFT", "GOOGL", "SPY"]:
        valid_payload["symbol"] = valid_symbol
        assert validate_order_payload(valid_payload).symbol == valid_symbol

    for invalid_symbol in ["aapl", "Aapl", "AAPL ", " AAPL", "ÄÄPL", "", 123, None]:
        valid_payload["symbol"] = invalid_symbol
        with pytest.raises((ValueError, TypeError, ValidationError)):
            validate_order_payload(valid_payload)


def test_quantity_positive_int_rejecting_booleans(valid_payload):
    for valid_qty in [1, 50, 10_000]:
        valid_payload["quantity"] = valid_qty
        assert validate_order_payload(valid_payload).quantity == valid_qty

    # Reject booleans specifically
    for bool_val in [True, False]:
        valid_payload["quantity"] = bool_val
        with pytest.raises((ValueError, TypeError, ValidationError)):
            validate_order_payload(valid_payload)

    # Reject non-positive ints and non-integers
    for invalid_qty in [0, -1, -100, 10.5, "100", None]:
        valid_payload["quantity"] = invalid_qty
        with pytest.raises((ValueError, TypeError, ValidationError)):
            validate_order_payload(valid_payload)


def test_limit_price_decimal_constraints_and_rejecting_float(valid_payload):
    # Valid Decimal inputs
    for valid_price in [Decimal("0.01"), Decimal("10.5"), Decimal("10.50"), Decimal(100), "150.25"]:
        valid_payload["limit_price"] = valid_price
        res = validate_order_payload(valid_payload)
        assert res.limit_price > Decimal(0)

    # Reject binary floats
    for float_price in [150.25, 0.01, 10.0, 1.0]:
        valid_payload["limit_price"] = float_price
        with pytest.raises((ValueError, TypeError, ValidationError)):
            validate_order_payload(valid_payload)

    # Reject zero or negative
    for non_positive in [Decimal("0.00"), Decimal("-1.00"), Decimal("-0.01")]:
        valid_payload["limit_price"] = non_positive
        with pytest.raises((ValueError, TypeError, ValidationError)):
            validate_order_payload(valid_payload)

    # Reject more than 2 decimal places
    for too_precise in [Decimal("10.555"), Decimal("0.001"), "99.999"]:
        valid_payload["limit_price"] = too_precise
        with pytest.raises((ValueError, TypeError, ValidationError)):
            validate_order_payload(valid_payload)

    # Reject booleans as price
    for bool_val in [True, False]:
        valid_payload["limit_price"] = bool_val
        with pytest.raises((ValueError, TypeError, ValidationError)):
            validate_order_payload(valid_payload)


def test_submitted_at_with_timezone(valid_payload):
    # Aware datetime is accepted
    valid_payload["submitted_at"] = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    res = validate_order_payload(valid_payload)
    assert res.submitted_at.tzinfo is not None

    # ISO string with timezone is accepted
    valid_payload["submitted_at"] = "2026-10-25T12:00:00Z"
    res = validate_order_payload(valid_payload)
    assert res.submitted_at.tzinfo is not None

    # Naive datetime must be rejected
    valid_payload["submitted_at"] = datetime(2026, 1, 1, 9, 30)  # noqa: DTZ001
    with pytest.raises((ValueError, TypeError, ValidationError)):
        validate_order_payload(valid_payload)

    # Naive ISO string must be rejected
    valid_payload["submitted_at"] = "2026-10-25T12:00:00"
    with pytest.raises((ValueError, TypeError, ValidationError)):
        validate_order_payload(valid_payload)


def test_tags_list_of_strings(valid_payload):
    valid_payload["tags"] = []
    assert validate_order_payload(valid_payload).tags == []

    valid_payload["tags"] = ["single"]
    assert validate_order_payload(valid_payload).tags == ["single"]

    # Reject non-list or list with non-strings
    for invalid_tags in ["urgent", 123, None, ["ok", 123], [True]]:
        valid_payload["tags"] = invalid_tags
        with pytest.raises((ValueError, TypeError, ValidationError)):
            validate_order_payload(valid_payload)


def test_payload_envelope_and_extra_fields(valid_payload):
    # Non-dict payload
    for non_dict in ["not a dict", 123, None, ["list"]]:
        with pytest.raises((ValueError, TypeError)):
            validate_order_payload(non_dict)  # type: ignore[arg-type]

    # Extra fields rejected
    valid_payload["unexpected_field"] = "malicious"
    with pytest.raises((ValueError, TypeError, ValidationError)):
        validate_order_payload(valid_payload)
