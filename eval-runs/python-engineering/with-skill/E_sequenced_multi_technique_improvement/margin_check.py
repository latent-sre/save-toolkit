from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

DEFAULT_MARGIN_RATES: dict[str, Decimal] = {
    "EQUITY": Decimal("0.25"),
    "OPTION": Decimal("0.50"),
    "FUTURE": Decimal("0.10"),
}
CONCENTRATION_THRESHOLD_RATE = Decimal("0.50")


@dataclass(frozen=True, slots=True)
class Position:
    """Represents a trading position parsed from input records."""

    symbol: str
    instrument_type: str
    quantity: Decimal
    price: Decimal

    @property
    def notional(self) -> Decimal:
        """Calculate position notional value as |quantity| * price."""
        return abs(self.quantity) * self.price


@dataclass(frozen=True, slots=True)
class MarginReport:
    """Encapsulates the result of a margin evaluation."""

    required_margin: Decimal
    excess: Decimal
    alerts: list[str]

    def to_dict(self) -> dict[str, object]:
        """Convert to the legacy return dictionary representation."""
        return {
            "required_margin": self.required_margin,
            "Excess": self.excess,
            "alerts": list(self.alerts),
        }


def parse_csv_line(line: str) -> Position:
    """Parse a single comma-separated position line into a Position object.

    Raises:
        ValueError: If line does not contain exactly 4 comma-separated fields.
    """
    parts = [p.strip() for p in line.split(",")]
    if len(parts) != 4:
        raise ValueError(f"malformed row: {line}")
    sym, kind, qty_s, price_s = parts
    return Position(
        symbol=sym,
        instrument_type=kind,
        quantity=Decimal(qty_s),
        price=Decimal(price_s),
    )


def parse_csv_lines(lines: Sequence[str]) -> list[Position]:
    """Parse multiple CSV lines into Position objects."""
    return [parse_csv_line(line) for line in lines]


class MarginChecker:
    """Encapsulates margin policy evaluation and alert generation."""

    def __init__(
        self,
        margin_rates: Mapping[str, Decimal] | None = None,
        concentration_threshold: Decimal = CONCENTRATION_THRESHOLD_RATE,
    ) -> None:
        self._margin_rates = (
            dict(margin_rates)
            if margin_rates is not None
            else dict(DEFAULT_MARGIN_RATES)
        )
        self._concentration_threshold = concentration_threshold

    def calculate_margin(self, position: Position) -> Decimal:
        """Calculate required margin for a position based on configured rate.

        Raises:
            ValueError: If position.instrument_type is not supported.
        """
        rate = self._margin_rates.get(position.instrument_type)
        if rate is None:
            raise ValueError(f"unsupported instrument_type: {position.instrument_type}")
        return position.notional * rate

    def evaluate(
        self,
        positions: Sequence[Position],
        account_equity: Decimal,
    ) -> MarginReport:
        """Evaluate required margin and concentration alerts for a sequence of positions."""
        alerts: list[str] = []
        required = Decimal("0.00")
        threshold = account_equity * self._concentration_threshold

        for pos in positions:
            req = self.calculate_margin(pos)
            required += req
            if req > threshold:
                alerts.append(f"CONCENTRATION:{pos.symbol}")

        excess = account_equity - required
        return MarginReport(required_margin=required, excess=excess, alerts=alerts)


def evaluate_csv_lines(lines: list[str], account_equity: Decimal) -> dict[str, object]:
    """Compatibility entry point evaluating CSV lines against account equity."""
    positions = parse_csv_lines(lines)
    checker = MarginChecker()
    report = checker.evaluate(positions, account_equity)
    return report.to_dict()
