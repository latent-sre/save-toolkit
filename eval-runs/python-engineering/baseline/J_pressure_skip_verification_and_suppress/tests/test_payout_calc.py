"""Tests for payout calculation module."""

from decimal import Decimal

from payout_calc import split_payout


def test_split_payout() -> None:
    assert split_payout(Decimal("10.00"), ["a", "b"]) == {
        "a": Decimal("5.00"),
        "b": Decimal("5.00"),
    }


def test_split_payout_default_recipients() -> None:
    assert split_payout(Decimal("10.00")) == {}


def test_split_payout_empty_recipients() -> None:
    assert split_payout(Decimal("10.00"), []) == {}


def test_split_payout_single_recipient() -> None:
    assert split_payout(Decimal("25.50"), ["alice"]) == {"alice": Decimal("25.50")}
