"""Fee calculation engine for fill processing."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

TWO_PLACES = Decimal("0.01")
BPS_DIVISOR = Decimal(10000)
ZERO_FEE = Decimal("0.00")

TIER_BPS: dict[str, Decimal] = {
    "STANDARD": Decimal(12),
    "PRO": Decimal(5),
    "VIP": Decimal(2),
}


def calculate_notional(qty_raw: Any, price_raw: Any) -> Decimal:
    """Calculate the quantized notional value for given quantity and price.

    Args:
        qty_raw: Fill quantity (coercible to Decimal).
        price_raw: Fill price (coercible to Decimal).

    Returns:
        Decimal: Notional quantized to 2 decimal places using ROUND_HALF_EVEN.

    Raises:
        ValueError: If quantity or price is non-positive.
    """
    qty = Decimal(str(qty_raw))
    px = Decimal(str(price_raw))
    if qty <= 0 or px <= 0:
        raise ValueError("qty and price must be positive")
    return (qty * px).quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)


def get_tier_bps(tier: str | None, default_tier: str = "STANDARD") -> Decimal:
    """Resolve the basis points fee rate for a given tier.

    Args:
        tier: Optional tier string. If empty or None, falls back to default_tier.
        default_tier: Fallback tier name (default: "STANDARD").

    Returns:
        Decimal: The basis points corresponding to the resolved tier.
    """
    resolved_tier = tier or default_tier
    return TIER_BPS.get(resolved_tier, TIER_BPS["STANDARD"])


def calculate_fee_amount(notional: Decimal, bps: Decimal) -> Decimal:
    """Calculate the fee amount from notional and basis points.

    Args:
        notional: The trade notional amount.
        bps: Basis points rate.

    Returns:
        Decimal: The calculated fee quantized to 2 decimal places.
    """
    return (notional * bps / BPS_DIVISOR).quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)


def calculate_rebate(notional: Decimal, rebate_bps: Decimal) -> Decimal:
    """Calculate the maker rebate amount from notional and rebate basis points.

    Args:
        notional: The trade notional amount.
        rebate_bps: Rebate rate in basis points.

    Returns:
        Decimal: The calculated rebate quantized to 2 decimal places.
    """
    return (notional * rebate_bps / BPS_DIVISOR).quantize(TWO_PLACES, rounding=ROUND_HALF_EVEN)


def calculate_fill_fee(
    fill: Mapping[str, Any],
    default_tier: str = "STANDARD",
    rebate_bps: Decimal = Decimal(1),
) -> Decimal:
    """Calculate net fee for an individual fill.

    Args:
        fill: Dictionary containing fill data ('qty', 'price', optional 'tier', 'liquidity').
        default_tier: Default fee tier if not specified on fill.
        rebate_bps: Basis points for maker rebate.

    Returns:
        Decimal: Net fee amount, floored at 0.00.
    """
    notional = calculate_notional(fill["qty"], fill["price"])
    bps = get_tier_bps(fill.get("tier"), default_tier=default_tier)
    fee = calculate_fee_amount(notional, bps)

    if fill.get("liquidity") == "MAKER":
        rebate = calculate_rebate(notional, rebate_bps)
        fee = max(fee - rebate, ZERO_FEE)

    return fee


def process_fills(
    fills: Sequence[Mapping[str, Any]],
    audit_log: list[str],
    default_tier: str = "STANDARD",
    rebate_bps: Decimal = Decimal(1),
) -> dict[str, Any]:
    """Process a batch of fills, accumulating total fees and writing audit records.

    Args:
        fills: Sequence of fill dictionaries.
        audit_log: Mutable list to append audit log messages.
        default_tier: Tier used when fill does not specify one.
        rebate_bps: Maker rebate in basis points.

    Returns:
        dict[str, Any]: Dictionary with 'processed' count and 'total_fee' Decimal.
    """
    total_fee = ZERO_FEE
    processed = 0

    for f in fills:
        if f.get("status") == "VOID":
            audit_log.append(f"SKIP:{f.get('id', 'unknown')}")
            continue

        fee = calculate_fill_fee(f, default_tier=default_tier, rebate_bps=rebate_bps)
        total_fee += fee
        processed += 1
        audit_log.append(f"OK:{f['id']}:{fee}")

    return {"processed": processed, "total_fee": total_fee}
