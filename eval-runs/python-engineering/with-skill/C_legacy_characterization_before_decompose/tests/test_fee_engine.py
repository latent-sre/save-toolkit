"""Tests for fee_engine, including behavioral characterization tests."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from fee_engine import (
    TIER_BPS,
    calculate_fill_fee,
    calculate_notional,
    process_fills,
)


def test_basic_fill() -> None:
    log: list[str] = []
    res = process_fills([{"id": "1", "qty": 100, "price": "10.00"}], log)
    assert res == {"processed": 1, "total_fee": Decimal("1.20")}
    assert log == ["OK:1:1.20"]


def test_empty_fills() -> None:
    log: list[str] = []
    res = process_fills([], log)
    assert res == {"processed": 0, "total_fee": Decimal("0.00")}
    assert log == []


def test_void_fills_with_and_without_id() -> None:
    log: list[str] = []
    fills: list[dict[str, Any]] = [
        {"id": "v1", "status": "VOID", "qty": 10, "price": "5.00"},
        {"status": "VOID"},
        {"id": "ok1", "qty": 10, "price": "10.00"},
    ]
    res = process_fills(fills, log)
    assert res == {"processed": 1, "total_fee": Decimal("0.12")}
    assert log == ["SKIP:v1", "SKIP:unknown", "OK:ok1:0.12"]


@pytest.mark.parametrize(
    ("qty", "price"),
    [
        (0, "10.00"),
        (-5, "10.00"),
        (10, "0.00"),
        (10, "-1.00"),
        (-1, "-1.00"),
    ],
)
def test_reject_non_positive_qty_or_price(qty: int | str, price: str) -> None:
    log: list[str] = []
    fills: list[dict[str, Any]] = [
        {"id": "ok1", "qty": 10, "price": "10.00"},
        {"id": "bad", "qty": qty, "price": price},
    ]
    with pytest.raises(ValueError, match="qty and price must be positive"):
        process_fills(fills, log)
    # Observable side effect: earlier fills were already processed and recorded in audit_log
    assert log == ["OK:ok1:0.12"]


@pytest.mark.parametrize(
    ("tier", "expected_fee"),
    [
        ("STANDARD", Decimal("1.20")),
        ("PRO", Decimal("0.50")),
        ("VIP", Decimal("0.20")),
        ("UNKNOWN_TIER", Decimal("1.20")),  # falls back to STANDARD
    ],
)
def test_fee_by_tier(tier: str, expected_fee: Decimal) -> None:
    log: list[str] = []
    fills = [{"id": "t1", "qty": 100, "price": "10.00", "tier": tier}]
    res = process_fills(fills, log)
    assert res == {"processed": 1, "total_fee": expected_fee}
    assert log == [f"OK:t1:{expected_fee}"]


def test_custom_default_tier() -> None:
    log: list[str] = []
    fills = [{"id": "def1", "qty": 100, "price": "10.00"}]
    res = process_fills(fills, log, default_tier="PRO")
    assert res == {"processed": 1, "total_fee": Decimal("0.50")}
    assert log == ["OK:def1:0.50"]


def test_maker_rebate() -> None:
    log: list[str] = []
    fills = [
        {"id": "m1", "qty": 100, "price": "10.00", "tier": "VIP", "liquidity": "MAKER"}
    ]
    res = process_fills(fills, log)
    assert res == {"processed": 1, "total_fee": Decimal("0.10")}
    assert log == ["OK:m1:0.10"]


def test_maker_rebate_floored_at_zero() -> None:
    log: list[str] = []
    fills = [
        {"id": "m2", "qty": 100, "price": "10.00", "tier": "VIP", "liquidity": "MAKER"}
    ]
    res = process_fills(fills, log, rebate_bps=Decimal(5))
    assert res == {"processed": 1, "total_fee": Decimal("0.00")}
    assert log == ["OK:m2:0.00"]


def test_round_half_even_quantization() -> None:
    log: list[str] = []
    fills = [{"id": "rnd1", "qty": "12.345", "price": "1.00", "tier": "STANDARD"}]
    res = process_fills(fills, log)
    assert res == {"processed": 1, "total_fee": Decimal("0.01")}
    assert log == ["OK:rnd1:0.01"]


def test_mixed_batch_processing() -> None:
    log: list[str] = []
    fills: list[dict[str, Any]] = [
        {"id": "f1", "status": "VOID"},
        {"id": "f2", "qty": 100, "price": "10.00", "tier": "STANDARD"},
        {"id": "f3", "qty": 50, "price": "20.00", "tier": "PRO", "liquidity": "MAKER"},
    ]
    res = process_fills(fills, log)
    assert res == {"processed": 2, "total_fee": Decimal("1.60")}
    assert log == ["SKIP:f1", "OK:f2:1.20", "OK:f3:0.40"]


def test_tier_bps_constant_exported() -> None:
    assert TIER_BPS["STANDARD"] == Decimal(12)
    assert TIER_BPS["PRO"] == Decimal(5)
    assert TIER_BPS["VIP"] == Decimal(2)


# Direct unit tests for decomposed pure helpers
def test_calculate_notional_pure() -> None:
    assert calculate_notional(Decimal(10), Decimal("5.5")) == Decimal("55.00")
    with pytest.raises(ValueError, match="qty and price must be positive"):
        calculate_notional(Decimal(0), Decimal(10))


def test_calculate_fill_fee_pure() -> None:
    notional = Decimal("1000.00")
    # STANDARD tier 12 bps -> 1.20
    assert calculate_fill_fee(notional, tier="STANDARD") == Decimal("1.20")
    # VIP tier 2 bps with MAKER rebate 1 bps -> 0.10
    assert calculate_fill_fee(
        notional,
        tier="VIP",
        liquidity="MAKER",
        rebate_bps=Decimal(1),
    ) == Decimal("0.10")
    # MAKER rebate exceeding fee -> floored to 0.00
    assert calculate_fill_fee(
        notional,
        tier="VIP",
        liquidity="MAKER",
        rebate_bps=Decimal(5),
    ) == Decimal("0.00")
