"""Tests for margin_check module."""

from decimal import Decimal

import pytest

from margin_check import evaluate_csv_lines


def test_equity_and_option():
    res = evaluate_csv_lines(["AAPL,EQUITY,10,100", "SPY,OPTION,10,100"], Decimal(1000))
    assert res["required_margin"] == Decimal("750.00")
    assert res["Excess"] == Decimal("250.00")
    assert res["alerts"] == []


def test_future_instrument():
    res = evaluate_csv_lines(["ES,FUTURE,10,100"], Decimal(1000))
    # notional = 10 * 100 = 1000; req = 1000 * 0.10 = 100.00
    assert res["required_margin"] == Decimal("100.00")
    assert res["Excess"] == Decimal("900.00")
    assert res["alerts"] == []


def test_concentration_alert():
    # req = 10 * 600 * 0.10 = 600.00, which exceeds 1000 * 0.50 (500)
    res = evaluate_csv_lines(["ES,FUTURE,10,600"], Decimal(1000))
    assert res["required_margin"] == Decimal("600.00")
    assert res["alerts"] == ["CONCENTRATION:ES"]


def test_isolated_evaluations():
    res1 = evaluate_csv_lines(["ES,FUTURE,10,600"], Decimal(1000))
    assert res1["alerts"] == ["CONCENTRATION:ES"]

    res2 = evaluate_csv_lines(["AAPL,EQUITY,1,100"], Decimal(1000))
    assert res2["alerts"] == []
    # Ensure res1's alerts list was not mutated
    assert res1["alerts"] == ["CONCENTRATION:ES"]


def test_malformed_row():
    with pytest.raises(ValueError, match="malformed row"):
        evaluate_csv_lines(["INVALID,ROW"], Decimal(1000))


def test_unsupported_instrument():
    with pytest.raises(ValueError, match="unsupported instrument_type"):
        evaluate_csv_lines(["BTC,CRYPTO,1,100"], Decimal(1000))
