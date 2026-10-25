from decimal import Decimal

import pytest

from margin_check import (
    _MARGIN_ALERTS,
    MarginEvaluator,
    Position,
    evaluate_csv_lines,
)


def test_equity_and_option():
    res = evaluate_csv_lines(['AAPL,EQUITY,10,100', 'SPY,OPTION,10,100'], Decimal(1000))
    assert res['required_margin'] == Decimal('750.00')
    assert res['Excess'] == Decimal('250.00')
    assert res['alerts'] == []
    assert _MARGIN_ALERTS == []


def test_future_instrument():
    res = evaluate_csv_lines(['ES,FUTURE,10,100'], Decimal(1000))
    # notional = 10 * 100 = 1000, req = 1000 * 0.10 = 100
    assert res['required_margin'] == Decimal('100.00')
    assert res['Excess'] == Decimal('900.00')
    assert res['alerts'] == []


def test_concentration_alert():
    # req = 10 * 100 * 0.10 = 100; equity = 150 -> 50% = 75; req > 75 -> alert
    res = evaluate_csv_lines(['ES,FUTURE,10,100'], Decimal(150))
    assert res['alerts'] == ['CONCENTRATION:ES']
    assert _MARGIN_ALERTS == ['CONCENTRATION:ES']


def test_malformed_csv_line():
    with pytest.raises(ValueError, match='malformed row'):
        evaluate_csv_lines(['INVALID,LINE'], Decimal(1000))


def test_unsupported_instrument():
    with pytest.raises(ValueError, match='unsupported instrument_type: CRYPTO'):
        evaluate_csv_lines(['BTC,CRYPTO,1,1000'], Decimal(1000))


def test_margin_evaluator_encapsulation():
    evaluator = MarginEvaluator()
    positions = [
        Position(symbol='AAPL', instrument_type='EQUITY', quantity=Decimal(10), price=Decimal(100)),
        Position(symbol='ES', instrument_type='FUTURE', quantity=Decimal(5), price=Decimal(200)),
    ]
    # equity = 2000; req = (1000 * 0.25) + (1000 * 0.10) = 250 + 100 = 350
    res = evaluator.evaluate_positions(positions, Decimal(2000))
    assert res['required_margin'] == Decimal('350.00')
    assert res['Excess'] == Decimal('1650.00')
    assert res['alerts'] == []
