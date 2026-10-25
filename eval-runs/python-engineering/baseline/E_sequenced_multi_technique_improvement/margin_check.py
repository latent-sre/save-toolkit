from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

_MARGIN_ALERTS: list[str] = []

MARGIN_RATES: dict[str, Decimal] = {
    'EQUITY': Decimal('0.25'),
    'OPTION': Decimal('0.50'),
    'FUTURE': Decimal('0.10'),
}


@dataclass(frozen=True)
class Position:
    symbol: str
    instrument_type: str
    quantity: Decimal
    price: Decimal

    @property
    def notional(self) -> Decimal:
        return abs(self.quantity) * self.price


def parse_csv_line(line: str) -> Position:
    parts = [p.strip() for p in line.split(',')]
    if len(parts) != 4:
        raise ValueError(f'malformed row: {line}')
    sym, kind, qty_s, price_s = parts
    return Position(
        symbol=sym,
        instrument_type=kind,
        quantity=Decimal(qty_s),
        price=Decimal(price_s),
    )


def parse_csv_lines(lines: Sequence[str]) -> list[Position]:
    return [parse_csv_line(line) for line in lines]


class MarginEvaluator:
    def __init__(self) -> None:
        self.alerts: list[str] = []

    def evaluate_positions(
        self, positions: Sequence[Position], account_equity: Decimal
    ) -> dict[str, object]:
        self.alerts.clear()
        required = Decimal('0.00')
        concentration_threshold = account_equity * Decimal('0.50')

        for pos in positions:
            rate = MARGIN_RATES.get(pos.instrument_type)
            if rate is None:
                raise ValueError(f'unsupported instrument_type: {pos.instrument_type}')
            req = pos.notional * rate
            required += req
            if req > concentration_threshold:
                self.alerts.append(f'CONCENTRATION:{pos.symbol}')

        return {
            'required_margin': required,
            'Excess': account_equity - required,
            'alerts': list(self.alerts),
        }


def evaluate_csv_lines(lines: list[str], account_equity: Decimal) -> dict[str, object]:
    positions = parse_csv_lines(lines)
    evaluator = MarginEvaluator()
    result = evaluator.evaluate_positions(positions, account_equity)
    _MARGIN_ALERTS.clear()
    _MARGIN_ALERTS.extend(evaluator.alerts)
    return result
