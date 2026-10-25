"""Tests for symbols module."""

import pytest

from symbols import parse_venue_symbol


@pytest.mark.parametrize(
    ("raw", "expected_venue", "expected_symbol"),
    [
        ("NYSE:AAPL", "NYSE", "AAPL"),
        ("  NASDAQ:MSFT  ", "NASDAQ", "MSFT"),
        ("CBOE : SPX500", "CBOE", "SPX500"),
        ("\tLSE:VOD\n", "LSE", "VOD"),
        ("V1:S2", "V1", "S2"),
        ("123:456", "123", "456"),
    ],
)
def test_parse_venue_symbol_valid(raw, expected_venue, expected_symbol):
    assert parse_venue_symbol(raw) == (expected_venue, expected_symbol)


@pytest.mark.parametrize(
    "invalid_input",
    [
        "",
        "   ",
        "NYSEAAPL",
        "NYSE:AAPL:EXTRA",
        ":AAPL",
        "NYSE:",
        ":",
        "   :   ",
        "nyse:AAPL",
        "NYSE:aapl",
        "Nyse:Aapl",
        "NY-SE:AAPL",
        "NYSE:AA.PL",
        "NY SE:AAPL",
        "NYSE:AA PL",
        "NYSE:AAPL!",
        "NŸSE:AAPL",
        "NYSE:AÁPL",
    ],
)
def test_parse_venue_symbol_invalid(invalid_input):
    with pytest.raises(ValueError):
        parse_venue_symbol(invalid_input)


def test_parse_venue_symbol_non_string():
    with pytest.raises(ValueError):
        parse_venue_symbol(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        parse_venue_symbol(12345)  # type: ignore[arg-type]
