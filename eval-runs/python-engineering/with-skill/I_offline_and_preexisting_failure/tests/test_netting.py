from netting import net_positions


def test_basic_netting() -> None:
    assert net_positions([("AAPL", 10), ("AAPL", -10), ("MSFT", 5)]) == {"MSFT": 5}


def test_empty_trades() -> None:
    assert net_positions([]) == {}


def test_all_positions_net_to_zero() -> None:
    trades = [("AAPL", 100), ("AAPL", -100), ("TSLA", 50), ("TSLA", -50)]
    assert net_positions(trades) == {}


def test_negative_net_position() -> None:
    trades = [("NVDA", -20), ("NVDA", -5), ("NVDA", 10)]
    assert net_positions(trades) == {"NVDA": -15}


def test_multiple_symbols_and_interleaved_trades() -> None:
    trades = [
        ("AAPL", 10),
        ("GOOG", 20),
        ("AAPL", 15),
        ("MSFT", 5),
        ("GOOG", -10),
        ("MSFT", -5),
    ]
    assert net_positions(trades) == {"AAPL": 25, "GOOG": 10}


def test_ordering_preserved() -> None:
    trades = [("GOOG", 10), ("AAPL", 20)]
    assert list(net_positions(trades).keys()) == ["GOOG", "AAPL"]
