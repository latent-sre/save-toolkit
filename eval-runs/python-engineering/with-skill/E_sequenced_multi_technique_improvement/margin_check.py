from decimal import Decimal
from typing import Final

MARGIN_RATES: Final[dict[str, Decimal]] = {
    "EQUITY": Decimal("0.25"),
    "OPTION": Decimal("0.50"),
    "FUTURE": Decimal("0.10"),
}
CONCENTRATION_THRESHOLD: Final[Decimal] = Decimal("0.50")


def evaluate_csv_lines(lines: list[str], account_equity: Decimal) -> dict[str, object]:
    """Evaluate margin requirements and concentration alerts for CSV position lines.

    Each line must follow the format 'symbol,instrument_type,quantity,price'.
    Evaluations are reentrant and isolated with no shared mutable module state.
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
