from netting import net_positions


def test_basic_netting() -> None:
    assert net_positions([("AAPL", 10), ("AAPL", -10), ("MSFT", 5)]) == {"MSFT": 5}


def test_empty_trades() -> None:
    assert net_positions([]) == {}


def test_all_positions_net_to_zero() -> None:
    trades = [("AAPL", 10), ("MSFT", -20), ("AAPL", -10), ("MSFT", 20)]
    assert net_positions(trades) == {}


def test_multiple_symbols_and_cumulative_trades() -> None:
    trades = [
        ("AAPL", 100),
        ("GOOG", -50),
        ("AAPL", -25),
        ("TSLA", 10),
        ("GOOG", 20),
        ("TSLA", -10),
    ]
    assert net_positions(trades) == {"AAPL": 75, "GOOG": -30}


def test_short_positions() -> None:
    assert net_positions([("NVDA", -100), ("NVDA", -50)]) == {"NVDA": -150}
