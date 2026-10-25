"""Tests for symbols."""

import pytest

from symbols import parse_venue_symbol


def test_parse_venue_symbol_valid_standard() -> None:
    assert parse_venue_symbol("NASDAQ:AAPL") == ("NASDAQ", "AAPL")


def test_parse_venue_symbol_valid_with_digits() -> None:
    assert parse_venue_symbol("CME:ES1") == ("CME", "ES1")
    assert parse_venue_symbol("EX1:SYM2") == ("EX1", "SYM2")
    assert parse_venue_symbol("123:456") == ("123", "456")


def test_parse_venue_symbol_strips_surrounding_whitespace() -> None:
    assert parse_venue_symbol("  NYSE:AAPL  ") == ("NYSE", "AAPL")
    assert parse_venue_symbol("NYSE : AAPL") == ("NYSE", "AAPL")
    assert parse_venue_symbol(" \t NYSE \t : \t AAPL \t ") == ("NYSE", "AAPL")


def test_parse_venue_symbol_single_character() -> None:
    assert parse_venue_symbol("N:A") == ("N", "A")


@pytest.mark.parametrize(
    "invalid_input",
    [
        "",
        "   ",
        "NASDAQ",
        "NYSE:AAPL:EXTRA",
        "A:B:C",
        "::",
        ":AAPL",
        "  :AAPL",
        "NYSE:",
        "NYSE:  ",
        ":",
        " : ",
        "nyse:AAPL",
        "NYSE:aapl",
        "nyse:aapl",
        "NŸSE:AAPL",
        "NYSE:ÄPPL",
        "NYSE:BRK.A",
        "NYSE:BRK-A",
        "NY_SE:AAPL",
        "NY SE:AAPL",
        None,
        123,
    ],
)
def test_parse_venue_symbol_invalid_inputs(invalid_input: object) -> None:
    with pytest.raises(ValueError):
        parse_venue_symbol(invalid_input)  # type: ignore[arg-type]
