from decimal import Decimal
from typing import Any

import pytest

from fee_engine import (
    calculate_base_fee,
    calculate_fill_fee,
    calculate_maker_rebate,
    calculate_notional,
    get_tier_bps,
    process_fills,
)


def test_calculate_notional_positive() -> None:
    assert calculate_notional(100, "10.00") == Decimal("1000.00")
    assert calculate_notional(Decimal("2.5"), Decimal("4.25")) == Decimal("10.62")
    # Banker's rounding test (ROUND_HALF_EVEN)
    # 2.5 * 0.025 = 0.0625 -> rounds to 0.06 (even)
    assert calculate_notional(Decimal("2.5"), Decimal("0.025")) == Decimal("0.06")


def test_calculate_notional_non_positive_raises() -> None:
    with pytest.raises(ValueError, match="qty and price must be positive"):
        calculate_notional(0, 10)
    with pytest.raises(ValueError, match="qty and price must be positive"):
        calculate_notional(10, 0)
    with pytest.raises(ValueError, match="qty and price must be positive"):
        calculate_notional(-1, 10)
    with pytest.raises(ValueError, match="qty and price must be positive"):
        calculate_notional(10, -5)


def test_get_tier_bps() -> None:
    assert get_tier_bps("STANDARD") == Decimal("12")
    assert get_tier_bps("PRO") == Decimal("5")
    assert get_tier_bps("VIP") == Decimal("2")
    assert get_tier_bps("NON_EXISTENT") == Decimal("12")
    assert get_tier_bps(None) == Decimal("12")
    assert get_tier_bps(None, default_tier="PRO") == Decimal("5")


def test_calculate_base_fee() -> None:
    # 10,000 * 12 / 10,000 = 12.00
    assert calculate_base_fee(Decimal("10000.00"), Decimal("12")) == Decimal("12.00")
    # 1,000 * 5 / 10,000 = 0.50
    assert calculate_base_fee(Decimal("1000.00"), Decimal("5")) == Decimal("0.50")


def test_calculate_maker_rebate() -> None:
    # 10,000 * 1 / 10,000 = 1.00
    assert calculate_maker_rebate(Decimal("10000.00"), Decimal("1")) == Decimal("1.00")
    # 5,000 * 2 / 10,000 = 1.00
    assert calculate_maker_rebate(Decimal("5000.00"), Decimal("2")) == Decimal("1.00")


def test_calculate_fill_fee() -> None:
    # Non-maker: 10,000 notional, PRO tier (5 bps) = 5.00
    fee = calculate_fill_fee(Decimal("10000.00"), tier="PRO", liquidity="TAKER")
    assert fee == Decimal("5.00")

    # Maker with rebate: 10,000 notional, VIP tier (2 bps = 2.00), rebate 1 bps = 1.00
    maker_fee = calculate_fill_fee(
        Decimal("10000.00"),
        tier="VIP",
        liquidity="MAKER",
        rebate_bps=Decimal("1"),
    )
    assert maker_fee == Decimal("1.00")

    # Maker rebate exceeds fee -> clamped to 0.00
    clamped_fee = calculate_fill_fee(
        Decimal("10000.00"),
        tier="VIP",
        liquidity="MAKER",
        rebate_bps=Decimal("5"),
    )
    assert clamped_fee == Decimal("0.00")


# --- Characterization integration tests for process_fills ---


def test_basic_fill() -> None:
    log: list[str] = []
    res = process_fills([{"id": "1", "qty": 100, "price": "10.00"}], log)
    assert res == {"processed": 1, "total_fee": Decimal("1.20")}
    assert log == ["OK:1:1.20"]


def test_void_fill_skipped_and_logged() -> None:
    log: list[str] = []
    fills: list[dict[str, Any]] = [
        {"id": "1", "status": "VOID"},
        {"status": "VOID"},  # no id -> 'unknown'
        {"id": "2", "qty": 50, "price": "20.00"},
    ]
    res = process_fills(fills, log)
    assert res == {"processed": 1, "total_fee": Decimal("1.20")}
    assert log == ["SKIP:1", "SKIP:unknown", "OK:2:1.20"]


def test_invalid_qty_or_price_raises_value_error() -> None:
    log: list[str] = []
    with pytest.raises(ValueError, match="qty and price must be positive"):
        process_fills([{"id": "1", "qty": 0, "price": "10.00"}], log)

    with pytest.raises(ValueError, match="qty and price must be positive"):
        process_fills([{"id": "1", "qty": -10, "price": "10.00"}], log)

    with pytest.raises(ValueError, match="qty and price must be positive"):
        process_fills([{"id": "1", "qty": 10, "price": "0.00"}], log)

    with pytest.raises(ValueError, match="qty and price must be positive"):
        process_fills([{"id": "1", "qty": 10, "price": "-5.00"}], log)


def test_tiers_and_custom_default() -> None:
    log: list[str] = []
    fills: list[dict[str, Any]] = [
        {"id": "1", "qty": 1000, "price": "10.00", "tier": "PRO"},
        {"id": "2", "qty": 1000, "price": "10.00", "tier": "VIP"},
        {"id": "3", "qty": 1000, "price": "10.00", "tier": "UNKNOWN"},
        {"id": "4", "qty": 1000, "price": "10.00"},
    ]
    res = process_fills(fills, log, default_tier="PRO")
    assert res["processed"] == 4
    assert res["total_fee"] == Decimal("24.00")
    assert log == ["OK:1:5.00", "OK:2:2.00", "OK:3:12.00", "OK:4:5.00"]


def test_maker_rebate_and_zero_clamping() -> None:
    log: list[str] = []
    res1 = process_fills(
        [
            {
                "id": "1",
                "qty": 1000,
                "price": "10.00",
                "tier": "VIP",
                "liquidity": "MAKER",
            }
        ],
        log,
        rebate_bps=Decimal("1"),
    )
    assert res1 == {"processed": 1, "total_fee": Decimal("1.00")}

    res2 = process_fills(
        [
            {
                "id": "2",
                "qty": 1000,
                "price": "10.00",
                "tier": "VIP",
                "liquidity": "MAKER",
            }
        ],
        log,
        rebate_bps=Decimal("5"),
    )
    assert res2 == {"processed": 1, "total_fee": Decimal("0.00")}
    assert log == ["OK:1:1.00", "OK:2:0.00"]
