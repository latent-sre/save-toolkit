"""Tests for netting module."""

from netting import net_positions


def test_basic_netting() -> None:
    assert net_positions([("AAPL", 10), ("AAPL", -10), ("MSFT", 5)]) == {"MSFT": 5}


def test_empty_trades() -> None:
    assert net_positions([]) == {}


def test_single_trade() -> None:
    assert net_positions([("GOOG", 42)]) == {"GOOG": 42}


def test_all_positions_net_to_zero() -> None:
    trades = [("AAPL", 100), ("AAPL", -50), ("AAPL", -50), ("TSLA", 25), ("TSLA", -25)]
    assert net_positions(trades) == {}


def test_mixed_positions_with_negative_net() -> None:
    trades = [("AAPL", 10), ("GOOG", -20), ("AAPL", -5), ("MSFT", 0), ("GOOG", 5)]
    assert net_positions(trades) == {"AAPL": 5, "GOOG": -15}
