#!/usr/bin/env python3
"""Error-budget and multi-window burn-rate calculator.

Pure stdlib, cross-platform.

Two SLI units are supported and never mixed:

* Time-based status (``--bad-minutes``) measures a probe/uptime SLI. Its budget is minutes.
* Request-based status (``--bad-events`` and ``--total-events``) measures a request-ratio SLI.
  Its budget is a count of failed requests; converting it to downtime assumes uniform traffic.

Burn-rate severity requires two measurements and one of three bound long/short window pairs. A
single window can show arithmetic but cannot emit PAGE or TICKET.

The calculations (``time_status``, ``request_status``, ``burn_verdict``) are pure functions that
return records; ``main`` validates the flags into ``Inputs`` and only renders those records.
"""

import argparse
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
import math
import sys
# Evaluated annotations that Python 3.8 understands: string annotations (`from __future__`) would
# make the dataclasses below require their module to be registered when loaded from a file path.
from typing import Optional, Tuple

# Google SRE Workbook: each long/short pair selects its own threshold and action. No pair lends its
# window or threshold to another.
WINDOW_PAIRS = {
    ("1h", "5m"): (14.4, "PAGE (fast burn)"),
    ("6h", "30m"): (6.0, "PAGE (slow burn)"),
    ("3d", "6h"): (1.0, "TICKET (slow leak)"),
}


def _decimal_percentage(text: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise argparse.ArgumentTypeError("must be a numeric percentage") from None
    if not value.is_finite():
        raise argparse.ArgumentTypeError("must be a finite percentage")
    return value


def _meets_burn_threshold(slo: Decimal, sli: Decimal, threshold: float) -> bool:
    """Compare the decimal SLI to the exact cutoff without rounding a burn-rate quotient."""
    with localcontext() as context:
        # Validated SLOs are between 0 and 100; eight extra digits cover 100 and the
        # fixed thresholds (at most 14.4) without losing the SLO's decimal places.
        context.prec = max(28, 8 - slo.as_tuple().exponent)
        cutoff = Decimal(100) - Decimal(str(threshold)) * (Decimal(100) - slo)
    return sli <= cutoff


def fmt_minutes(minutes: float) -> str:
    """Format a minute quantity without changing its unit semantics."""
    if minutes >= 1440:
        return f"{minutes / 1440:.2f} d ({minutes:.0f} min)"
    if minutes >= 60:
        return f"{minutes / 60:.2f} h ({minutes:.0f} min)"
    return f"{minutes:.1f} min"


def fmt_count(count: float) -> str:
    """Format a request count."""
    return f"{count:,.0f}"


def _finite(name, value, *, minimum=None, exclusive_min=None, maximum=None):
    """Reject NaN/inf and enforce a numeric argument's range on its float value, which is returned."""
    if value is None:
        return None
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number (got {value!r})")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum} (got {value:g})")
    if exclusive_min is not None and value <= exclusive_min:
        raise ValueError(f"{name} must be > {exclusive_min} (got {value:g})")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum} (got {value:g})")
    return value


@dataclass(frozen=True)
class Inputs:
    """Validated calculator inputs; construction raises ValueError naming the first unusable flag.

    Percentages stay exact Decimals so the alert boundary is inclusive without rounding. Range
    checks, budget arithmetic and display use their float values.
    """

    slo: Decimal
    window_days: float
    bad_minutes: Optional[float]
    bad_events: Optional[float]
    total_events: Optional[float]
    sli_long: Optional[Decimal]
    sli_short: Optional[Decimal]
    long_window: str
    short_window: str

    @property
    def request_mode(self) -> bool:
        return self.bad_events is not None or self.total_events is not None

    def __post_init__(self) -> None:
        if (self.long_window, self.short_window) not in WINDOW_PAIRS:
            raise ValueError("--long-window/--short-window must be one of: "
                             + ", ".join(f"{long}/{short}" for long, short in WINDOW_PAIRS))
        if _finite("--slo", self.slo, exclusive_min=0, maximum=100) >= 100:
            raise ValueError("--slo must be < 100 (a 100% SLO has a zero error budget)")
        _finite("--window-days", self.window_days, exclusive_min=0)
        _finite("--bad-minutes", self.bad_minutes, minimum=0)
        _finite("--bad-events", self.bad_events, minimum=0)
        _finite("--total-events", self.total_events, exclusive_min=0)
        _finite("--sli-long", self.sli_long, minimum=0, maximum=100)
        _finite("--sli-short", self.sli_short, minimum=0, maximum=100)

        if self.request_mode and self.bad_minutes is not None:
            raise ValueError("--bad-minutes (time-based SLI) cannot be combined with "
                             "--bad-events/--total-events (request-based SLI); pick one unit")
        if self.request_mode and (self.bad_events is None or self.total_events is None):
            raise ValueError("request-based status needs BOTH --bad-events and --total-events")
        if self.request_mode and self.bad_events > self.total_events:
            raise ValueError("--bad-events cannot exceed --total-events")
        if self.sli_short is not None and self.sli_long is None:
            raise ValueError("--sli-short requires --sli-long")


@dataclass(frozen=True)
class BudgetStatus:
    """Budget consumption in the SLI's own unit: minutes, or failed requests."""

    budget: float
    consumed: float
    remaining: float  # exactly 0.0 within floating-point residue of zero, so never "-0.0"
    percent: float  # of the budget consumed
    state: str  # "ok", "EXHAUSTED" or "OVER BUDGET"
    observed_availability: Optional[float] = None  # request-based status only


@dataclass(frozen=True)
class BurnVerdict:
    """One window pair's severity decision.

    ``outcome`` names the burn-rate.md verdict boundary that applied: "both", "long only",
    "short only" or "neither" window met the pair's threshold. ``severity`` is what to tell the reader.
    """

    action: str
    threshold: float
    burn_long: float
    burn_short: float
    outcome: str
    severity: str


def budget_fraction(slo: Decimal) -> float:
    """The share of the SLI that the SLO leaves as error budget: 0.001 for 99.9%."""
    return 1.0 - float(slo) / 100.0


def burn_rate(slo: Decimal, sli: Decimal) -> float:
    """How many times faster than the SLO allows a window measuring ``sli`` spends budget."""
    return (1.0 - float(sli) / 100.0) / budget_fraction(slo)


def _remaining(budget: float, consumed: float) -> Tuple[float, str]:
    """Remaining budget and its state, with tolerance for percentage floating-point arithmetic."""
    remaining = budget - consumed
    if abs(remaining) <= max(abs(budget) * 1e-12, 1e-12):
        return 0.0, "EXHAUSTED"
    return remaining, "OVER BUDGET" if remaining < 0 else "ok"


def time_status(slo: Decimal, window_days: float, bad_minutes: float) -> BudgetStatus:
    """A time-based SLI's budget: minutes of the status window."""
    budget = window_days * 24 * 60 * budget_fraction(slo)
    remaining, state = _remaining(budget, bad_minutes)
    return BudgetStatus(budget, bad_minutes, remaining, bad_minutes / budget * 100, state)


def request_status(slo: Decimal, total_events: float, bad_events: float) -> BudgetStatus:
    """A request-based SLI's budget: a count of failed requests."""
    budget = total_events * budget_fraction(slo)
    remaining, state = _remaining(budget, bad_events)
    percent = bad_events / budget * 100 if budget else float("inf")
    observed = (1 - bad_events / total_events) * 100
    return BudgetStatus(budget, bad_events, remaining, percent, state, observed)


def burn_verdict(slo: Decimal, sli_long: Decimal, sli_short: Decimal,
                 long_window: str, short_window: str) -> BurnVerdict:
    """Apply the pair's threshold to both windows: a page or ticket needs both (>=; AND, never OR)."""
    threshold, action = WINDOW_PAIRS[(long_window, short_window)]
    burn_long, burn_short = burn_rate(slo, sli_long), burn_rate(slo, sli_short)
    long_crossed = _meets_burn_threshold(slo, sli_long, threshold)
    short_crossed = _meets_burn_threshold(slo, sli_short, threshold)
    if long_crossed and short_crossed:
        outcome, severity = "both", f"{action} -- both windows >= {threshold}x"
    elif long_crossed:
        outcome, severity = "long only", (
            f"no page -- long window at {burn_long:.2f}x but the short window ({burn_short:.2f}x) has "
            "recovered. NOT an all-clear: budget status is unknown; some budget may already have been "
            "consumed. Run the budget-status mode."
        )
    elif short_crossed:
        outcome, severity = "short only", (
            f"no page -- short-window spike ({burn_short:.2f}x) the long window ({burn_long:.2f}x) hasn't "
            "confirmed. Re-check in minutes; a real burn trips both."
        )
    else:
        outcome, severity = "neither", (
            f"below the {threshold}x threshold for the {long_window}/{short_window} pair. This says nothing "
            "about the budget already consumed -- that is the budget-status mode's job."
        )
    return BurnVerdict(action, threshold, burn_long, burn_short, outcome, severity)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SLO error-budget and burn-rate calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--slo", type=_decimal_percentage, required=True, help="SLO target percent, e.g. 99.9")
    parser.add_argument(
        "--window-days", type=float, default=28.0,
        help="budget-status horizon in days (default 28); does not rescale fixed alert thresholds",
    )

    status = parser.add_argument_group("budget status — pick ONE kind of SLI")
    status.add_argument(
        "--bad-minutes", type=float,
        help="TIME-based: bad minutes consumed in the budget-status window",
    )
    status.add_argument(
        "--bad-events", type=float,
        help="REQUEST-based: failed requests in the window (needs --total-events)",
    )
    status.add_argument(
        "--total-events", type=float,
        help="REQUEST-based: total valid requests in the window",
    )

    burn = parser.add_argument_group("burn rate — BOTH windows required for a severity verdict")
    burn.add_argument(
        "--sli-long", "--sli", dest="sli_long", type=_decimal_percentage,
        help="availability percent measured over the selected long window",
    )
    burn.add_argument(
        "--sli-short", type=_decimal_percentage,
        help="availability percent measured over the selected short window",
    )
    burn.add_argument(
        "--long-window", default="1h", choices=[long for long, _ in WINDOW_PAIRS],
        help="long window of the pair; selects the alert threshold (1h/5m=14.4x page, "
             "6h/30m=6x page, 3d/6h=1x ticket)",
    )
    burn.add_argument(
        "--short-window", default="5m", choices=[short for _, short in WINDOW_PAIRS],
        help="short window of the pair; must match the long window's pair",
    )
    return parser


def main(argv=None) -> int:
    """Run the calculator and return a process exit code."""
    parser = _parser()
    try:
        inputs = Inputs(**vars(parser.parse_args(argv)))
    except ValueError as exc:
        parser.error(str(exc))

    print(f"SLO {float(inputs.slo)}%  ->  error budget = {budget_fraction(inputs.slo) * 100:.4g}% of the SLI")

    # Budget status: the unit follows the SLI.
    if inputs.bad_minutes is not None:
        status = time_status(inputs.slo, inputs.window_days, inputs.bad_minutes)
        print(
            f"  [time-based SLI] over {inputs.window_days:g}d the budget is "
            f"{fmt_minutes(status.budget)}"
        )
        print(
            f"  consumed:  {fmt_minutes(status.consumed)}  "
            f"({status.percent:.1f}% of budget)  [{status.state}]"
        )
        print(f"  remaining: {fmt_minutes(status.remaining)}")

    if inputs.request_mode:
        status = request_status(inputs.slo, inputs.total_events, inputs.bad_events)
        print(
            f"  [request-based SLI] {fmt_count(inputs.total_events)} requests  ->  "
            f"budget = {fmt_count(status.budget)} failed requests"
        )
        print(
            f"  consumed:  {fmt_count(status.consumed)} bad  "
            f"({status.percent:.1f}% of budget)  [{status.state}]"
        )
        print(f"  remaining: {fmt_count(status.remaining)} bad requests")
        print(f"  observed availability: {status.observed_availability:.4f}%")

    # Burn rate: a pair selects one threshold, and both windows must cross it.
    if inputs.sli_long is not None:
        print("  alert policy: fixed 30-day example thresholds; --window-days does not rescale them")
        burn_long = burn_rate(inputs.slo, inputs.sli_long)
        print(f"  burn ({inputs.long_window}):  SLI {float(inputs.sli_long)}%  ->  {burn_long:.2f}x")

        if inputs.sli_short is None:
            print(
                "  severity: NOT EVALUATED -- pass --sli-short; one window cannot emit "
                "PAGE or TICKET"
            )
        else:
            verdict = burn_verdict(inputs.slo, inputs.sli_long, inputs.sli_short,
                                   inputs.long_window, inputs.short_window)
            print(
                f"  burn ({inputs.short_window}): SLI {float(inputs.sli_short)}%  ->  "
                f"{verdict.burn_short:.2f}x"
            )
            print(f"  severity: {verdict.severity}")

            if burn_long > 0:
                exhaustion_days = inputs.window_days / burn_long
                print(
                    f"  at the {inputs.long_window} rate, the full {inputs.window_days:g}d budget "
                    f"is gone in {fmt_minutes(exhaustion_days * 24 * 60)} "
                    "(projection assumes steady eligible volume; not remaining budget)"
                )

    if inputs.bad_minutes is None and not inputs.request_mode and inputs.sli_long is None:
        print(
            "  (pass --bad-minutes OR --bad-events/--total-events for status; "
            "--sli-long + --sli-short for burn rate)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
