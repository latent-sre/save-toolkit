from decimal import Decimal

import pytest

from margin_check import MarginChecker, Position, evaluate_csv_lines


def test_equity_and_option():
    res = evaluate_csv_lines(["AAPL,EQUITY,10,100", "SPY,OPTION,10,100"], Decimal(1000))
    assert res["required_margin"] == Decimal("750.00")
    assert res["Excess"] == Decimal("250.00")
    assert res["alerts"] == []


def test_concentration_alert_equity():
    res = evaluate_csv_lines(["AAPL,EQUITY,10,100"], Decimal(400))
    # notional = 1000, req = 250, threshold = 400 * 0.50 = 200 -> alert
    assert res["required_margin"] == Decimal("250.00")
    assert res["Excess"] == Decimal("150.00")
    assert res["alerts"] == ["CONCENTRATION:AAPL"]


def test_concentration_alert_option():
    res = evaluate_csv_lines(["SPY,OPTION,10,100"], Decimal(800))
    # notional = 1000, req = 500, threshold = 800 * 0.50 = 400 -> alert
    assert res["required_margin"] == Decimal("500.00")
    assert res["Excess"] == Decimal("300.00")
    assert res["alerts"] == ["CONCENTRATION:SPY"]


def test_future_instrument_margin_calculation():
    # notional = 10 * 100 = 1000, margin rate = 0.10 -> req = 100.00
    res = evaluate_csv_lines(["ES,FUTURE,10,100"], Decimal(1000))
    assert res["required_margin"] == Decimal("100.00")
    assert res["Excess"] == Decimal("900.00")
    assert res["alerts"] == []


def test_future_concentration_alert():
    # notional = 10 * 100 = 1000, req = 100, equity = 150 -> threshold = 75 -> alert
    res = evaluate_csv_lines(["ES,FUTURE,10,100"], Decimal(150))
    assert res["required_margin"] == Decimal("100.00")
    assert res["Excess"] == Decimal("50.00")
    assert res["alerts"] == ["CONCENTRATION:ES"]


def test_mixed_portfolio_equity_option_future():
    # AAPL: 10 * 100 = 1000 * 0.25 = 250
    # SPY: 10 * 100 = 1000 * 0.50 = 500
    # ES: 10 * 100 = 1000 * 0.10 = 100
    # Total required = 850.00
    res = evaluate_csv_lines(
        ["AAPL,EQUITY,10,100", "SPY,OPTION,10,100", "ES,FUTURE,10,100"],
        Decimal(2000),
    )
    assert res["required_margin"] == Decimal("850.00")
    assert res["Excess"] == Decimal("1150.00")
    assert res["alerts"] == []


def test_negative_quantity_uses_absolute_value():
    res = evaluate_csv_lines(["AAPL,EQUITY,-10,100"], Decimal(1000))
    assert res["required_margin"] == Decimal("250.00")
    assert res["Excess"] == Decimal("750.00")
    assert res["alerts"] == []


def test_malformed_csv_line():
    with pytest.raises(ValueError, match="malformed row: AAPL,EQUITY,10"):
        evaluate_csv_lines(["AAPL,EQUITY,10"], Decimal(1000))


def test_unsupported_instrument():
    with pytest.raises(ValueError, match="unsupported instrument_type: BOND"):
        evaluate_csv_lines(["AAPL,BOND,10,100"], Decimal(1000))


def test_empty_lines():
    res = evaluate_csv_lines([], Decimal(1000))
    assert res["required_margin"] == Decimal("0.00")
    assert res["Excess"] == Decimal(1000)
    assert res["alerts"] == []


def test_state_isolation_across_consecutive_runs():
    res1 = evaluate_csv_lines(["AAPL,EQUITY,10,100"], Decimal(400))
    assert res1["alerts"] == ["CONCENTRATION:AAPL"]
    res2 = evaluate_csv_lines(["AAPL,EQUITY,10,100"], Decimal(1000))
    assert res2["alerts"] == []


def test_margin_checker_object_direct_api():
    checker = MarginChecker()
    positions = [
        Position(
            symbol="AAPL",
            instrument_type="EQUITY",
            quantity=Decimal(10),
            price=Decimal(100),
        ),
        Position(
            symbol="ES",
            instrument_type="FUTURE",
            quantity=Decimal(5),
            price=Decimal(200),
        ),
    ]
    report = checker.evaluate(positions, Decimal(1000))
    # AAPL req: 1000 * 0.25 = 250
    # ES req: 1000 * 0.10 = 100
    # total req = 350
    assert report.required_margin == Decimal("350.00")
    assert report.excess == Decimal("650.00")
    assert report.alerts == []
    legacy = report.to_dict()
    assert legacy["required_margin"] == Decimal("350.00")
    assert legacy["Excess"] == Decimal("650.00")
    assert legacy["alerts"] == []
