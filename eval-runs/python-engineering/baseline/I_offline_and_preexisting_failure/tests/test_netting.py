from netting import net_positions


def test_basic_netting() -> None:
    assert net_positions([("AAPL", 10), ("AAPL", -10), ("MSFT", 5)]) == {"MSFT": 5}


def test_empty_trades() -> None:
    assert net_positions([]) == {}


def test_all_positions_net_to_zero() -> None:
    trades = [("AAPL", 100), ("AAPL", -100), ("TSLA", 25), ("TSLA", -25)]
    assert net_positions(trades) == {}


def test_negative_net_positions() -> None:
    trades = [("GOOG", -50), ("GOOG", 20)]
    assert net_positions(trades) == {"GOOG": -30}


def test_multiple_symbols_mixed() -> None:
    trades = [
        ("AAPL", 50),
        ("MSFT", 100),
        ("AAPL", -30),
        ("AMZN", 10),
        ("MSFT", -100),
        ("AMZN", -15),
    ]
    assert net_positions(trades) == {"AAPL": 20, "AMZN": -5}
