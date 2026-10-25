from decimal import Decimal

import pytest

from margin_check import evaluate_csv_lines


def test_equity_and_option():
    res = evaluate_csv_lines(["AAPL,EQUITY,10,100", "SPY,OPTION,10,100"], Decimal(1000))
    assert res["required_margin"] == Decimal("750.00")
    assert res["Excess"] == Decimal("250.00")
    assert res["alerts"] == []


def test_concentration_alert():
    res = evaluate_csv_lines(["AAPL,EQUITY,30,100"], Decimal(1000))
    assert res["required_margin"] == Decimal("750.00")
    assert res["Excess"] == Decimal("250.00")
    assert res["alerts"] == ["CONCENTRATION:AAPL"]


def test_malformed_row():
    with pytest.raises(ValueError, match="malformed row: AAPL,EQUITY,10"):
        evaluate_csv_lines(["AAPL,EQUITY,10"], Decimal(1000))


def test_unsupported_instrument():
    with pytest.raises(ValueError, match="unsupported instrument_type: BOND"):
        evaluate_csv_lines(["GOVT,BOND,10,100"], Decimal(1000))


def test_future_instrument():
    # 10 contracts @ $100 = $1,000 notional. At 0.10 margin rate -> $100 req margin.
    res = evaluate_csv_lines(["ES,FUTURE,10,100"], Decimal(1000))
    assert res["required_margin"] == Decimal("100.00")
    assert res["Excess"] == Decimal("900.00")
    assert res["alerts"] == []


def test_future_concentration_alert():
    # 60 contracts @ $100 = $6,000 notional. At 0.10 rate -> $600 req margin.
    # $600 > 0.50 * 1000 ($500), so triggers CONCENTRATION:ES
    res = evaluate_csv_lines(["ES,FUTURE,60,100"], Decimal(1000))
    assert res["required_margin"] == Decimal("600.00")
    assert res["Excess"] == Decimal("400.00")
    assert res["alerts"] == ["CONCENTRATION:ES"]


def test_isolation_no_shared_mutable_alerts():
    res1 = evaluate_csv_lines(["AAPL,EQUITY,30,100"], Decimal(1000))
    assert res1["alerts"] == ["CONCENTRATION:AAPL"]

    res2 = evaluate_csv_lines(["AAPL,EQUITY,10,100"], Decimal(1000))
    assert res2["alerts"] == []

    # Prior evaluation result must not be mutated by subsequent evaluation
    assert res1["alerts"] == ["CONCENTRATION:AAPL"]
