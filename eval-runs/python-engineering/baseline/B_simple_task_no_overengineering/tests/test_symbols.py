"""Unit tests for parse_venue_symbol in symbols."""

import pytest

from symbols import parse_venue_symbol


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("NASDAQ:AAPL", ("NASDAQ", "AAPL")),
        ("  NASDAQ:AAPL  ", ("NASDAQ", "AAPL")),
        ("NASDAQ : AAPL", ("NASDAQ", "AAPL")),
        ("  XNYS  :  MSFT  ", ("XNYS", "MSFT")),
        ("XNYS:BTC1", ("XNYS", "BTC1")),
        ("CEX1:ETH2", ("CEX1", "ETH2")),
        ("A:B", ("A", "B")),
        ("123:456", ("123", "456")),
        ("BINANCE:BTCUSDT", ("BINANCE", "BTCUSDT")),
    ],
)
def test_parse_venue_symbol_valid(raw: str, expected: tuple[str, str]) -> None:
    assert parse_venue_symbol(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "NASDAQ_AAPL",
        "NASDAQ",
        "",
        "   ",
        "NASDAQ:AAPL:EXTRA",
        "A:B:C",
        "::",
        ":AAPL",
        "  :AAPL",
        " : AAPL",
        "NASDAQ:",
        "NASDAQ:  ",
        "NASDAQ : ",
        ":",
        "   :   ",
        "nasdaq:AAPL",
        "NASDAQ:aapl",
        "Nasdaq:AAPL",
        "NAS-DAQ:AAPL",
        "NASDAQ:AAPL-US",
        "NASDAQ:AAPL.US",
        "NASDAQ:BTC/USD",
        "NÄSDAQ:AAPL",
        "NASDAQ:ÄÄPL",
        "NASDAQ:ÉTH",
    ],
)
def test_parse_venue_symbol_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_venue_symbol(raw)


def test_parse_venue_symbol_non_string() -> None:
    for non_str in [None, 123, ["NASDAQ", "AAPL"], {"venue": "NASDAQ"}]:
        with pytest.raises(ValueError):
            parse_venue_symbol(non_str)  # type: ignore[arg-type]
