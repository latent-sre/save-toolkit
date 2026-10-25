"""Margin calculation and concentration check utilities."""

from decimal import Decimal
from typing import Any

MARGIN_RATES: dict[str, Decimal] = {
    "EQUITY": Decimal("0.25"),
    "OPTION": Decimal("0.50"),
    "FUTURE": Decimal("0.10"),
}

CONCENTRATION_THRESHOLD = Decimal("0.50")

# Kept for backward compatibility; calls to evaluate_csv_lines remain isolated.
_MARGIN_ALERTS: list[str] = []


def evaluate_csv_lines(lines: list[str], account_equity: Decimal) -> dict[str, Any]:
    """Evaluate CSV position lines and calculate margin requirements.

    Args:
        lines: List of CSV lines formatted as 'symbol,instrument_type,quantity,price'.
        account_equity: Total account equity as Decimal.

    Returns:
        dict containing 'required_margin', 'Excess', and 'alerts'.

    Raises:
        ValueError: If a row is malformed or an instrument type is unsupported.
    """
    alerts: list[str] = []
    required = Decimal("0.00")

    for line in lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 4:
            raise ValueError(f"malformed row: {line}")

        sym, kind, qty_s, price_s = parts

        rate = MARGIN_RATES.get(kind)
        if rate is None:
            raise ValueError(f"unsupported instrument_type: {kind}")

        notional = abs(Decimal(qty_s)) * Decimal(price_s)
        req = notional * rate
        required += req

        if req > account_equity * CONCENTRATION_THRESHOLD:
            alerts.append(f"CONCENTRATION:{sym}")

    return {
        "required_margin": required,
        "Excess": account_equity - required,
        "alerts": alerts,
    }
