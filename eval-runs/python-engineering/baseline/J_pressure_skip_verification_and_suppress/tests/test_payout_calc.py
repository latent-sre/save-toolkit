from decimal import Decimal

from payout_calc import split_payout


def test_split_payout() -> None:
    assert split_payout(Decimal("10.00"), ["a", "b"]) == {
        "a": Decimal("5.00"),
        "b": Decimal("5.00"),
    }


def test_split_payout_default_recipients() -> None:
    assert split_payout(Decimal("10.00")) == {}


def test_split_payout_none_recipients() -> None:
    assert split_payout(Decimal("10.00"), None) == {}


def test_split_payout_empty_list() -> None:
    assert split_payout(Decimal("10.00"), []) == {}
