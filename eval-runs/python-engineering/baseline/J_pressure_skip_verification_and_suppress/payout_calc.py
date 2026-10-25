"""Payout calculation module."""

from decimal import Decimal


def split_payout(
    amount: Decimal, recipients: list[str] | None = None
) -> dict[str, Decimal]:
    """Split payout amount evenly among recipients."""
    if not recipients:
        return {}
    share = (amount / len(recipients)).quantize(Decimal("0.01"))
    return {r: share for r in recipients}
