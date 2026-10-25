"""Fee calculation engine for order fills."""

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

TIER_BPS: dict[str, Decimal] = {
    "STANDARD": Decimal(12),
    "PRO": Decimal(5),
    "VIP": Decimal(2),
}

BPS_DIVISOR = Decimal(10000)
CENT_QUANT = Decimal("0.01")
ZERO_FEE = Decimal("0.00")


def calculate_notional(qty: Decimal | str | float, price: Decimal | str | float) -> Decimal:
    """Calculate and round notional value for a fill.

    Raises:
        ValueError: If qty or price is non-positive.
    """
    qty_dec = Decimal(str(qty))
    price_dec = Decimal(str(price))
    if qty_dec <= 0 or price_dec <= 0:
        raise ValueError("qty and price must be positive")
    return (qty_dec * price_dec).quantize(CENT_QUANT, rounding=ROUND_HALF_EVEN)


def get_tier_bps(tier: str | None, default_tier: str = "STANDARD") -> Decimal:
    """Resolve the fee in basis points for a tier."""
    resolved_tier = tier or default_tier
    return TIER_BPS.get(resolved_tier, TIER_BPS["STANDARD"])


def calculate_fill_fee(
    fill: dict[str, Any],
    default_tier: str = "STANDARD",
    rebate_bps: Decimal = Decimal(1),
) -> Decimal:
    """Calculate net fee for a single valid fill."""
    notional = calculate_notional(fill["qty"], fill["price"])
    bps = get_tier_bps(fill.get("tier"), default_tier=default_tier)
    fee = (notional * bps / BPS_DIVISOR).quantize(CENT_QUANT, rounding=ROUND_HALF_EVEN)

    if fill.get("liquidity") == "MAKER":
        rebate = (notional * rebate_bps / BPS_DIVISOR).quantize(CENT_QUANT, rounding=ROUND_HALF_EVEN)
        fee -= rebate
        fee = max(fee, ZERO_FEE)

    return fee


def process_fills(
    fills: list[dict[str, Any]],
    audit_log: list[str],
    default_tier: str = "STANDARD",
    rebate_bps: Decimal = Decimal(1),
) -> dict[str, Any]:
    """Process a batch of fills, update audit log, and return summary."""
    total_fee = ZERO_FEE
    processed = 0

    for f in fills:
        if f.get("status") == "VOID":
            fill_id = f.get("id", "unknown")
            audit_log.append(f"SKIP:{fill_id}")
            continue

        fee = calculate_fill_fee(f, default_tier=default_tier, rebate_bps=rebate_bps)
        total_fee += fee
        processed += 1
        audit_log.append(f"OK:{f['id']}:{fee}")

    return {"processed": processed, "total_fee": total_fee}
