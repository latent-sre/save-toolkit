"""Tests for fee_engine including legacy characterization and unit tests for decomposed functions."""

from decimal import Decimal

import pytest

from fee_engine import (
    TIER_BPS,
    calculate_fee_amount,
    calculate_fill_fee,
    calculate_notional,
    calculate_rebate,
    get_tier_bps,
    process_fills,
)

# --- Legacy Characterization Tests ---


def test_basic_fill():
    """Characterization test: verifies baseline single fill behavior."""
    log = []
    res = process_fills([{"id": "1", "qty": 100, "price": "10.00"}], log)
    assert res == {"processed": 1, "total_fee": Decimal("1.20")}
    assert log == ["OK:1:1.20"]


def test_void_status_skipped():
    """Characterization test: VOID fills are skipped and logged as SKIP."""
    log = []
    fills = [
        {"id": "1", "qty": 100, "price": "10.00"},
        {"id": "2", "status": "VOID"},
        {"status": "VOID"},  # missing id defaults to 'unknown'
        {"id": "3", "qty": 50, "price": "20.00"},
    ]
    res = process_fills(fills, log)
    assert res == {"processed": 2, "total_fee": Decimal("2.40")}
    assert log == ["OK:1:1.20", "SKIP:2", "SKIP:unknown", "OK:3:1.20"]


def test_maker_rebate_applied():
    """Characterization test: MAKER liquidity deducts rebate."""
    log = []
    # Notional: 1000.00; STANDARD 12 bps -> fee 1.20; MAKER rebate 1 bps -> rebate 0.10; net fee = 1.10
    fills = [{"id": "m1", "qty": 100, "price": "10.00", "liquidity": "MAKER"}]
    res = process_fills(fills, log)
    assert res == {"processed": 1, "total_fee": Decimal("1.10")}
    assert log == ["OK:m1:1.10"]


def test_maker_rebate_floored_at_zero():
    """Characterization test: MAKER rebate cannot make fee negative."""
    log = []
    # VIP tier is 2 bps; with rebate_bps=5 bps, fee would be negative without floor
    fills = [{"id": "m2", "qty": 100, "price": "10.00", "tier": "VIP", "liquidity": "MAKER"}]
    res = process_fills(fills, log, rebate_bps=Decimal(5))
    assert res == {"processed": 1, "total_fee": Decimal("0.00")}
    assert log == ["OK:m2:0.00"]


def test_tier_resolution():
    """Characterization test: PRO (5 bps), VIP (2 bps), unknown fallback (12 bps)."""
    log = []
    fills = [
        {"id": "p1", "qty": 100, "price": "10.00", "tier": "PRO"},      # 1000 * 5/10000 = 0.50
        {"id": "v1", "qty": 100, "price": "10.00", "tier": "VIP"},      # 1000 * 2/10000 = 0.20
        {"id": "u1", "qty": 100, "price": "10.00", "tier": "UNKNOWN"},  # fallback: 1.20
    ]
    res = process_fills(fills, log)
    assert res == {"processed": 3, "total_fee": Decimal("1.90")}
    assert log == ["OK:p1:0.50", "OK:v1:0.20", "OK:u1:1.20"]


def test_invalid_qty_and_price_raises():
    """Characterization test: Non-positive qty or price raises ValueError."""
    log = []
    for invalid_fill in [
        {"id": "e1", "qty": 0, "price": "10.00"},
        {"id": "e2", "qty": -5, "price": "10.00"},
        {"id": "e3", "qty": 10, "price": "0.00"},
        {"id": "e4", "qty": 10, "price": "-1.00"},
    ]:
        with pytest.raises(ValueError, match="qty and price must be positive"):
            process_fills([invalid_fill], log)


# --- Unit Tests for Decomposed Functions ---


def test_calculate_notional_valid():
    assert calculate_notional(10, "15.50") == Decimal("155.00")
    assert calculate_notional(Decimal("3.5"), Decimal("2.105")) == Decimal("7.37")


def test_calculate_notional_invalid():
    with pytest.raises(ValueError, match="qty and price must be positive"):
        calculate_notional(0, 10)
    with pytest.raises(ValueError, match="qty and price must be positive"):
        calculate_notional(10, -1)


def test_get_tier_bps():
    assert get_tier_bps("STANDARD") == Decimal(12)
    assert get_tier_bps("PRO") == Decimal(5)
    assert get_tier_bps("VIP") == Decimal(2)
    assert get_tier_bps(None) == Decimal(12)
    assert get_tier_bps("", default_tier="PRO") == Decimal(5)
    assert get_tier_bps("NONEXISTENT") == TIER_BPS["STANDARD"]


def test_calculate_fee_amount():
    notional = Decimal("1000.00")
    assert calculate_fee_amount(notional, Decimal(12)) == Decimal("1.20")
    assert calculate_fee_amount(notional, Decimal(5)) == Decimal("0.50")
    assert calculate_fee_amount(notional, Decimal(2)) == Decimal("0.20")


def test_calculate_rebate():
    notional = Decimal("1000.00")
    assert calculate_rebate(notional, Decimal(1)) == Decimal("0.10")
    assert calculate_rebate(notional, Decimal("2.5")) == Decimal("0.25")


def test_calculate_fill_fee_taker_and_maker():
    taker_fill = {"qty": 100, "price": "10.00", "tier": "STANDARD"}
    maker_fill = {"qty": 100, "price": "10.00", "tier": "STANDARD", "liquidity": "MAKER"}

    assert calculate_fill_fee(taker_fill) == Decimal("1.20")
    assert calculate_fill_fee(maker_fill) == Decimal("1.10")
