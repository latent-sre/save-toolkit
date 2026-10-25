"""Fee calculation engine for trade execution fills."""

from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

BPS_DIVISOR = Decimal("10000")
CENT = Decimal("0.01")
ZERO_FEE = Decimal("0.00")

TIER_BPS: dict[str, Decimal] = {
    "STANDARD": Decimal("12"),
    "PRO": Decimal("5"),
    "VIP": Decimal("2"),
}


def calculate_notional(
    qty: Decimal | int | float | str,
    price: Decimal | int | float | str,
) -> Decimal:
    """Calculate rounded notional value from quantity and price.

    Raises:
        ValueError: If quantity or price is non-positive.
    """
    d_qty = Decimal(str(qty))
    d_price = Decimal(str(price))
    if d_qty <= Decimal(0) or d_price <= Decimal(0):
        raise ValueError("qty and price must be positive")
    return (d_qty * d_price).quantize(CENT, rounding=ROUND_HALF_EVEN)


def get_tier_bps(tier: str | None, default_tier: str = "STANDARD") -> Decimal:
    """Resolve fee basis points for a tier with fallback to default tier or STANDARD."""
    effective_tier = tier or default_tier
    return TIER_BPS.get(effective_tier, TIER_BPS["STANDARD"])


def calculate_base_fee(notional: Decimal, bps: Decimal) -> Decimal:
    """Calculate rounded base fee before any liquidity adjustments."""
    return (notional * bps / BPS_DIVISOR).quantize(CENT, rounding=ROUND_HALF_EVEN)


def calculate_maker_rebate(notional: Decimal, rebate_bps: Decimal) -> Decimal:
    """Calculate rounded maker rebate."""
    return (notional * rebate_bps / BPS_DIVISOR).quantize(
        CENT, rounding=ROUND_HALF_EVEN
    )


def calculate_fill_fee(
    notional: Decimal,
    tier: str | None,
    liquidity: str | None = None,
    default_tier: str = "STANDARD",
    rebate_bps: Decimal = Decimal("1"),
) -> Decimal:
    """Calculate final net fee for a fill after applying tier and maker rebates."""
    bps = get_tier_bps(tier, default_tier=default_tier)
    fee = calculate_base_fee(notional, bps)
    if liquidity == "MAKER":
        rebate = calculate_maker_rebate(notional, rebate_bps)
        fee = max(ZERO_FEE, fee - rebate)
    return fee


def process_fills(
    fills: Iterable[Mapping[str, Any]],
    audit_log: list[str],
    default_tier: str = "STANDARD",
    rebate_bps: Decimal = Decimal("1"),
) -> dict[str, Any]:
    """Process a collection of trade fills, computing fees and writing to audit log."""
    total_fee = ZERO_FEE
    processed = 0

    for f in fills:
        if f.get("status") == "VOID":
            audit_log.append(f"SKIP:{f.get('id', 'unknown')}")
            continue

        notional = calculate_notional(f["qty"], f["price"])
        fee = calculate_fill_fee(
            notional=notional,
            tier=f.get("tier"),
            liquidity=f.get("liquidity"),
            default_tier=default_tier,
            rebate_bps=rebate_bps,
        )

        total_fee += fee
        processed += 1
        audit_log.append(f"OK:{f['id']}:{fee}")

    return {"processed": processed, "total_fee": total_fee}
