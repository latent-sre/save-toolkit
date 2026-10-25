"""Fee calculation engine for order fills."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableSequence
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

__all__ = ["TIER_BPS", "calculate_fill_fee", "calculate_notional", "process_fills"]

TIER_BPS: dict[str, Decimal] = {
    "STANDARD": Decimal(12),
    "PRO": Decimal(5),
    "VIP": Decimal(2),
}

_BPS_DIVISOR = Decimal(10000)
_CENT = Decimal("0.01")
_ZERO = Decimal("0.00")


def calculate_notional(qty: Decimal, px: Decimal) -> Decimal:
    """Calculate and quantize notional value for a fill.

    Args:
        qty: Fill quantity.
        px: Fill price.

    Returns:
        Quantized notional Decimal to 2 decimal places using ROUND_HALF_EVEN.

    Raises:
        ValueError: If qty or px is non-positive.
    """
    if qty <= 0 or px <= 0:
        raise ValueError("qty and price must be positive")
    return (qty * px).quantize(_CENT, rounding=ROUND_HALF_EVEN)


def calculate_fill_fee(
    notional: Decimal,
    tier: str = "STANDARD",
    liquidity: str | None = None,
    rebate_bps: Decimal = Decimal(1),
) -> Decimal:
    """Calculate the net fee for a fill after applying tier rates and liquidity rebate.

    Args:
        notional: Quantized fill notional value.
        tier: Fee tier name ('STANDARD', 'PRO', 'VIP').
        liquidity: Liquidity indicator ('MAKER' or other).
        rebate_bps: Rebate in basis points applied to MAKER liquidity.

    Returns:
        Quantized fee Decimal to 2 decimal places, floored at 0.00.
    """
    bps = TIER_BPS.get(tier, TIER_BPS["STANDARD"])
    fee = (notional * bps / _BPS_DIVISOR).quantize(_CENT, rounding=ROUND_HALF_EVEN)

    if liquidity == "MAKER":
        rebate = (notional * rebate_bps / _BPS_DIVISOR).quantize(
            _CENT, rounding=ROUND_HALF_EVEN
        )
        fee = fee - rebate
        fee = max(fee, _ZERO)

    return fee


def process_fills(
    fills: Iterable[Mapping[str, Any]],
    audit_log: MutableSequence[str],
    default_tier: str = "STANDARD",
    rebate_bps: Decimal = Decimal(1),
) -> dict[str, Any]:
    """Process a batch of fills, computing total fees and appending to the audit log.

    Args:
        fills: Sequence of fill dictionaries.
        audit_log: Mutable sequence to receive audit log entries.
        default_tier: Fallback tier name if fill has no tier specified.
        rebate_bps: Rebate in basis points for maker fills.

    Returns:
        Dictionary with 'processed' count and 'total_fee' Decimal.
    """
    total_fee = _ZERO
    processed = 0

    for f in fills:
        if f.get("status") == "VOID":
            fill_id = f.get("id", "unknown")
            audit_log.append(f"SKIP:{fill_id}")
            continue

        qty = Decimal(str(f["qty"]))
        px = Decimal(str(f["price"]))
        notional = calculate_notional(qty, px)

        tier = f.get("tier") or default_tier
        liquidity = f.get("liquidity")
        fee = calculate_fill_fee(
            notional, tier=tier, liquidity=liquidity, rebate_bps=rebate_bps
        )

        total_fee += fee
        processed += 1
        audit_log.append(f"OK:{f['id']}:{fee}")

    return {"processed": processed, "total_fee": total_fee}
