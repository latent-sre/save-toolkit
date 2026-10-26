"""Unit tests for symbols module."""

import pytest

from symbols import parse_venue_symbol


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("NASDAQ:AAPL", ("NASDAQ", "AAPL")),
        ("BINANCE:BTC", ("BINANCE", "BTC")),
        ("  BINANCE : BTC  ", ("BINANCE", "BTC")),
        ("NYSE:GME", ("NYSE", "GME")),
        ("\tCME:ES\n", ("CME", "ES")),
        ("COINBASE:ETH2", ("COINBASE", "ETH2")),
        ("EXCHANGE1:SYM9", ("EXCHANGE1", "SYM9")),
        ("A:B", ("A", "B")),
    ],
)
def test_parse_venue_symbol_valid(raw: str, expected: tuple[str, str]) -> None:
    """Valid venue:symbol strings should parse into stripped uppercase tuple pairs."""
    assert parse_venue_symbol(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "NASDAQ",
        "AAPL",
        "A:B:C",
        "NASDAQ:AAPL:EXTRA",
        "::",
        ":AAPL",
        "  :AAPL",
        "NASDAQ:",
        "NASDAQ:  ",
        ":",
        "   :   ",
        "nasdaq:AAPL",
        "Nasdaq:AAPL",
        "NASDAQ:aapl",
        "NASDAQ:Aapl",
        "NASDAQ:AAPL-USD",
        "NAS_DAQ:AAPL",
        "NASDAQ:AAPL.US",
        "NYSE:BRK/A",
        "ＮAＳＤＡＱ:AAPL",
        "NASDAQ:AÄPL",
        "VENUE:ABC²",
        "123:AAPL",
        "NASDAQ:123",
    ],
)
def test_parse_venue_symbol_invalid_values(raw: str) -> None:
    """Invalid venue:symbol strings must raise ValueError."""
    with pytest.raises(ValueError):
        parse_venue_symbol(raw)


def test_parse_venue_symbol_non_string() -> None:
    """Non-string inputs must raise ValueError."""
    with pytest.raises(ValueError):
        parse_venue_symbol(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        parse_venue_symbol(12345)  # type: ignore[arg-type]
