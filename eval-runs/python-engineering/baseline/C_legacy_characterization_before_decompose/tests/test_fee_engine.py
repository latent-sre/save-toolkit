"""Characterization and unit tests for fee_engine module."""

from decimal import Decimal

import pytest

from fee_engine import (
    TIER_BPS,
    calculate_fill_fee,
    calculate_notional,
    get_tier_bps,
    process_fills,
)


def test_basic_fill():
    log = []
    res = process_fills([{"id": "1", "qty": 100, "price": "10.00"}], log)
    assert res == {"processed": 1, "total_fee": Decimal("1.20")}
    assert log == ["OK:1:1.20"]


def test_empty_fills():
    log = []
    res = process_fills([], log)
    assert res == {"processed": 0, "total_fee": Decimal("0.00")}
    assert log == []


def test_void_status_skips():
    log = []
    fills = [
        {"id": "fill-1", "status": "VOID"},
        {"id": "fill-2", "status": "VOID"},
        {"status": "VOID"},  # missing id
        {"id": "fill-3", "qty": "50", "price": "2.00"},
    ]
    res = process_fills(fills, log)
    assert res == {"processed": 1, "total_fee": Decimal("0.12")}
    assert log == [
        "SKIP:fill-1",
        "SKIP:fill-2",
        "SKIP:unknown",
        "OK:fill-3:0.12",
    ]


@pytest.mark.parametrize(
    ("qty", "price"),
    [
        (0, "10.00"),
        (-10, "10.00"),
        (10, 0),
        (10, -5),
    ],
)
def test_invalid_qty_or_price_raises(qty, price):
    log = []
    with pytest.raises(ValueError, match="qty and price must be positive"):
        process_fills([{"id": "err", "qty": qty, "price": price}], log)


def test_tiers():
    log = []
    fills = [
        {"id": "std", "qty": 1000, "price": "10.00", "tier": "STANDARD"},  # 10000 * 12 / 10000 = 12.00
        {"id": "pro", "qty": 1000, "price": "10.00", "tier": "PRO"},       # 10000 * 5 / 10000 = 5.00
        {"id": "vip", "qty": 1000, "price": "10.00", "tier": "VIP"},       # 10000 * 2 / 10000 = 2.00
        {"id": "unk", "qty": 1000, "price": "10.00", "tier": "UNKNOWN"},   # fallback to STANDARD = 12.00
        {"id": "def", "qty": 1000, "price": "10.00"},                      # default tier = 12.00
    ]
    res = process_fills(fills, log)
    assert res == {"processed": 5, "total_fee": Decimal("43.00")}
    assert log == [
        "OK:std:12.00",
        "OK:pro:5.00",
        "OK:vip:2.00",
        "OK:unk:12.00",
        "OK:def:12.00",
    ]


def test_custom_default_tier():
    log = []
    fills = [{"id": "1", "qty": 1000, "price": "10.00"}]
    res = process_fills(fills, log, default_tier="PRO")
    assert res == {"processed": 1, "total_fee": Decimal("5.00")}
    assert log == ["OK:1:5.00"]


def test_maker_liquidity_rebate():
    log = []
    # Notional: 10,000. Tier VIP (2 bps) -> base fee = 2.00
    # Maker rebate (default 1 bps) -> rebate = 1.00 -> final fee = 1.00
    fills = [
        {"id": "maker1", "qty": 1000, "price": "10.00", "tier": "VIP", "liquidity": "MAKER"},
        {"id": "taker1", "qty": 1000, "price": "10.00", "tier": "VIP", "liquidity": "TAKER"},
    ]
    res = process_fills(fills, log)
    assert res == {"processed": 2, "total_fee": Decimal("3.00")}
    assert log == ["OK:maker1:1.00", "OK:taker1:2.00"]


def test_maker_rebate_cannot_make_fee_negative():
    log = []
    # Notional: 10,000. Tier VIP (2 bps) -> base fee = 2.00. Rebate 5 bps -> rebate = 5.00 -> fee capped at 0.00
    fills = [{"id": "maker_cap", "qty": 1000, "price": "10.00", "tier": "VIP", "liquidity": "MAKER"}]
    res = process_fills(fills, log, rebate_bps=Decimal(5))
    assert res == {"processed": 1, "total_fee": Decimal("0.00")}
    assert log == ["OK:maker_cap:0.00"]


def test_rounding_half_even():
    log = []
    fills = [{"id": "round1", "qty": 1, "price": "0.015", "tier": "STANDARD"}]
    res = process_fills(fills, log)
    assert res == {"processed": 1, "total_fee": Decimal("0.00")}


# Unit tests for decomposed functions
def test_calculate_notional_valid():
    assert calculate_notional("100", "12.345") == Decimal("1234.50")
    assert calculate_notional(10, 5) == Decimal("50.00")


def test_calculate_notional_invalid():
    with pytest.raises(ValueError, match="qty and price must be positive"):
        calculate_notional(0, 10)
    with pytest.raises(ValueError, match="qty and price must be positive"):
        calculate_notional(10, -1)


def test_get_tier_bps():
    assert get_tier_bps("PRO") == Decimal(5)
    assert get_tier_bps(None, default_tier="VIP") == Decimal(2)
    assert get_tier_bps("NON_EXISTENT") == TIER_BPS["STANDARD"]


def test_calculate_fill_fee_isolated():
    fill = {"qty": 100, "price": "50.00", "tier": "PRO", "liquidity": "TAKER"}
    # 5000 * 5 / 10000 = 2.50
    assert calculate_fill_fee(fill) == Decimal("2.50")
