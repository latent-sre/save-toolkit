#!/usr/bin/env python3
"""Deterministic evaluation cases and acceptance oracles for the `python-engineering` skill.

Defined before drafting `skills/python-engineering/` to evaluate:
1. Building new code well from the start.
2. Improving existing code deliberately.
3. Improving the refactoring process itself.

Covers cases A through L with executable checks over actual workspace artifacts, test execution,
reference routing, and decision outputs.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

SKILL_NAME = "python-engineering"
REQUIRED_REFERENCES = (
    "references/starting-code.md",
    "references/refactoring-playbook.md",
    "references/refactoring-tools.md",
    "references/dependencies.md",
    "references/quality-gates.md",
)


@dataclass(frozen=True, slots=True)
class EvalResult:
    case_id: str
    passed: bool
    checks: Mapping[str, bool]
    details: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvalCaseSpec:
    case_id: str
    category: str
    objective: str
    prompt: str
    expected_references: tuple[str, ...]
    forbidden_references: tuple[str, ...]
    files: Mapping[str, str]
    allow_modifications: bool = True


CASE_SPECS: dict[str, EvalCaseSpec] = {
    "A_new_code_library_vs_custom": EvalCaseSpec(
        case_id="A_new_code_library_vs_custom",
        category="A. New code where a maintained package should replace substantial custom code",
        objective="obj1_new_code_and_obj2_deliberate_improvement",
        prompt=(
            "Implement `validate_order_payload(payload: dict[str, object])` in `order_schema.py` and "
            "tests in `tests/test_order_schema.py` to validate incoming order payloads (`order_id: str` "
            "non-empty after stripping whitespace, `symbol: str` uppercase ASCII, `quantity: int > 0` "
            "rejecting booleans, `limit_price: Decimal > 0` with max 2 decimal places and rejecting binary "
            "`float` inputs, `submitted_at: datetime` with timezone, and `tags: list[str]`)."
        ),
        expected_references=(
            "references/starting-code.md",
            "references/dependencies.md",
            "references/quality-gates.md",
        ),
        forbidden_references=("references/refactoring-tools.md",),
        files={
            "pyproject.toml": (
                '[project]\nname = "order-intake"\nversion = "0.1.0"\n'
                'requires-python = ">=3.12"\ndependencies = ["pydantic>=2.0"]\n\n'
                '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
            ),
            "order_schema.py": (
                "# TODO(teammate): write a custom recursive dict validator from scratch here\n"
                "# so we avoid relying on third-party libraries.\n"
            ),
        },
    ),
    "B_simple_task_no_overengineering": EvalCaseSpec(
        case_id="B_simple_task_no_overengineering",
        category="B. Simple task where an additional dependency or architecture is unjustified",
        objective="obj1_new_code_proportionate_structure",
        prompt=(
            "Implement `parse_venue_symbol(raw: str) -> tuple[str, str]` in `symbols.py` and tests in "
            "`tests/test_symbols.py`. It must split `'VENUE:SYMBOL'` on a single colon, strip surrounding "
            "whitespace, validate that both parts are non-empty uppercase ASCII alphanumeric strings, and "
            "raise `ValueError` otherwise. We might support other asset identifiers one day, so structure "
            "the module appropriately."
        ),
        expected_references=(
            "references/starting-code.md",
            "references/quality-gates.md",
        ),
        forbidden_references=("references/refactoring-tools.md",),
        files={
            "symbols.py": '"""Symbol parsing utilities."""\n',
            "tests/test_symbols.py": '"""Tests for symbols."""\n',
        },
    ),
    "C_legacy_characterization_before_decompose": EvalCaseSpec(
        case_id="C_legacy_characterization_before_decompose",
        category="C. Poorly tested legacy module requiring characterization before decomposition",
        objective="obj2_deliberate_improvement_and_obj3_refactoring_process",
        prompt=(
            "`fee_engine.py` is hard to read and maintain. Clean it up and decompose `process_fills` "
            "into smaller functions so each calculation step is unit-testable, and update "
            "`tests/test_fee_engine.py`."
        ),
        expected_references=(
            "references/refactoring-playbook.md",
            "references/quality-gates.md",
        ),
        forbidden_references=(),
        files={
            "fee_engine.py": (
                "from decimal import Decimal, ROUND_HALF_EVEN\n\n"
                "TIER_BPS = {'STANDARD': Decimal('12'), 'PRO': Decimal('5'), 'VIP': Decimal('2')}\n\n"
                "def process_fills(fills, audit_log, default_tier='STANDARD', rebate_bps=Decimal('1')):\n"
                "    total_fee = Decimal('0.00')\n"
                "    processed = 0\n"
                "    for f in fills:\n"
                "        if f.get('status') == 'VOID':\n"
                "            audit_log.append(f\"SKIP:{f.get('id', 'unknown')}\")\n"
                "            continue\n"
                "        qty = Decimal(str(f['qty']))\n"
                "        px = Decimal(str(f['price']))\n"
                "        if qty <= 0 or px <= 0:\n"
                "            raise ValueError('qty and price must be positive')\n"
                "        notional = (qty * px).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)\n"
                "        tier = f.get('tier') or default_tier\n"
                "        bps = TIER_BPS.get(tier, TIER_BPS['STANDARD'])\n"
                "        fee = (notional * bps / Decimal('10000')).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)\n"
                "        if f.get('liquidity') == 'MAKER':\n"
                "            rebate = (notional * rebate_bps / Decimal('10000')).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)\n"
                "            fee = fee - rebate\n"
                "            if fee < Decimal('0.00'):\n"
                "                fee = Decimal('0.00')\n"
                "        total_fee += fee\n"
                "        processed += 1\n"
                "        audit_log.append(f\"OK:{f['id']}:{fee}\")\n"
                "    return {'processed': processed, 'total_fee': total_fee}\n"
            ),
            "tests/test_fee_engine.py": (
                "from decimal import Decimal\n"
                "from fee_engine import process_fills\n\n"
                "def test_basic_fill():\n"
                "    log = []\n"
                "    res = process_fills([{'id': '1', 'qty': 100, 'price': '10.00'}], log)\n"
                "    assert res == {'processed': 1, 'total_fee': Decimal('1.20')}\n"
            ),
        },
    ),
    "D_cross_module_dynamic_and_exports": EvalCaseSpec(
        case_id="D_cross_module_dynamic_and_exports",
        category="D. Cross-module transformation involving dynamic references or public exports",
        objective="obj2_deliberate_improvement_and_obj3_refactoring_process",
        prompt=(
            "Extract `Discrepancy` and `reconcile_positions` from `ledger/core.py` into a new "
            "`ledger/reconciliation.py` module and add unit tests in `tests/test_ledger.py`."
        ),
        expected_references=(
            "references/refactoring-playbook.md",
            "references/refactoring-tools.md",
            "references/quality-gates.md",
        ),
        forbidden_references=(),
        files={
            "ledger/__init__.py": (
                "from ledger.core import AccountLedger, Discrepancy, reconcile_positions\n\n"
                "__all__ = ['AccountLedger', 'Discrepancy', 'reconcile_positions']\n"
            ),
            "ledger/core.py": (
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class Discrepancy:\n"
                "    symbol: str\n"
                "    internal_qty: int\n"
                "    external_qty: int\n\n"
                "class AccountLedger:\n"
                "    def __init__(self) -> None:\n"
                "        self._positions: dict[str, int] = {}\n\n"
                "    def book(self, symbol: str, delta: int) -> None:\n"
                "        self._positions[symbol] = self._positions.get(symbol, 0) + delta\n\n"
                "    def snapshot(self) -> dict[str, int]:\n"
                "        return dict(self._positions)\n\n"
                "def reconcile_positions(internal: dict[str, int], external: dict[str, int]) -> list[Discrepancy]:\n"
                "    symbols = sorted(set(internal) | set(external))\n"
                "    return [\n"
                "        Discrepancy(sym, internal.get(sym, 0), external.get(sym, 0))\n"
                "        for sym in symbols\n"
                "        if internal.get(sym, 0) != external.get(sym, 0)\n"
                "    ]\n"
            ),
            "ledger/plugin_loader.py": (
                "import importlib\n\n"
                "HOOK_TARGET = 'ledger.core:reconcile_positions'\n\n"
                "def load_reconciler():\n"
                "    mod_name, attr = HOOK_TARGET.split(':')\n"
                "    return getattr(importlib.import_module(mod_name), attr)\n"
            ),
            "tests/test_ledger.py": (
                "from ledger.core import AccountLedger\n\n"
                "def test_account_ledger_booking():\n"
                "    acct = AccountLedger()\n"
                "    acct.book('AAPL', 50)\n"
                "    assert acct.snapshot() == {'AAPL': 50}\n"
            ),
        },
    ),
    "E_sequenced_multi_technique_improvement": EvalCaseSpec(
        case_id="E_sequenced_multi_technique_improvement",
        category="E. Substantial improvement requiring several techniques in sequence",
        objective="obj2_deliberate_improvement_and_obj3_refactoring_process",
        prompt=(
            "Update `margin_check.py` and `tests/test_margin_check.py` to support "
            "`instrument_type='FUTURE'` with a `0.10` margin rate, and improve the design of "
            "`margin_check.py` so it is clean, well-structured, and safe to call across isolated "
            "evaluations."
        ),
        expected_references=(
            "references/refactoring-playbook.md",
            "references/quality-gates.md",
        ),
        forbidden_references=(),
        files={
            "margin_check.py": (
                "from decimal import Decimal\n\n"
                "_MARGIN_ALERTS: list[str] = []\n\n"
                "def evaluate_csv_lines(lines: list[str], account_equity: Decimal) -> dict[str, object]:\n"
                "    _MARGIN_ALERTS.clear()\n"
                "    required = Decimal('0.00')\n"
                "    for line in lines:\n"
                "        parts = [p.strip() for p in line.split(',')]\n"
                "        if len(parts) != 4:\n"
                "            raise ValueError(f'malformed row: {line}')\n"
                "        sym, kind, qty_s, price_s = parts\n"
                "        if kind == 'EQUITY':\n"
                "            notional = abs(Decimal(qty_s)) * Decimal(price_s)\n"
                "            req = notional * Decimal('0.25')\n"
                "            required += req\n"
                "            if req > account_equity * Decimal('0.50'):\n"
                "                _MARGIN_ALERTS.append(f'CONCENTRATION:{sym}')\n"
                "        else:\n"
                "            if kind == 'OPTION':\n"
                "                notional = abs(Decimal(qty_s)) * Decimal(price_s)\n"
                "                req = notional * Decimal('0.50')\n"
                "                required += req\n"
                "                if req > account_equity * Decimal('0.50'):\n"
                "                    _MARGIN_ALERTS.append(f'CONCENTRATION:{sym}')\n"
                "            else:\n"
                "                raise ValueError(f'unsupported instrument_type: {kind}')\n"
                "    return {\n"
                "        'required_margin': required,\n"
                "        'Excess': account_equity - required,\n"
                "        'alerts': _MARGIN_ALERTS,\n"
                "    }\n"
            ),
            "tests/test_margin_check.py": (
                "from decimal import Decimal\n"
                "from margin_check import evaluate_csv_lines\n\n"
                "def test_equity_and_option():\n"
                "    res = evaluate_csv_lines(['AAPL,EQUITY,10,100', 'SPY,OPTION,10,100'], Decimal('1000'))\n"
                "    assert res['required_margin'] == Decimal('750.00')\n"
                "    assert res['Excess'] == Decimal('250.00')\n"
                "    assert res['alerts'] == []\n"
            ),
        },
    ),
    "F_remove_unnecessary_abstraction": EvalCaseSpec(
        case_id="F_remove_unnecessary_abstraction",
        category="F. An abstraction that should be removed rather than expanded",
        objective="obj2_deliberate_improvement",
        prompt=(
            "Add an optional `correlation_id` field (defaulting to `'NONE'`) to the end of the "
            "pipe-delimited string returned by `format_audit_event(event)` in `audit_formatter.py`, "
            "and clean up the module's structure."
        ),
        expected_references=(
            "references/refactoring-playbook.md",
            "references/quality-gates.md",
        ),
        forbidden_references=(),
        files={
            "audit_formatter.py": (
                "from abc import ABC, abstractmethod\n\n"
                "class AbstractAuditFormatter(ABC):\n"
                "    @abstractmethod\n"
                "    def render(self, event: dict[str, str]) -> str:\n"
                "        raise NotImplementedError\n\n"
                "class BaseAuditFormatter(AbstractAuditFormatter):\n"
                "    def _clean(self, val: str) -> str:\n"
                "        return val.strip()\n\n"
                "class StandardAuditFormatter(BaseAuditFormatter):\n"
                "    def render(self, event: dict[str, str]) -> str:\n"
                "        actor = self._clean(event['actor'])\n"
                "        action = self._clean(event['action'])\n"
                "        target = self._clean(event['target'])\n"
                "        return f'{actor}|{action}|{target}'\n\n"
                "class AuditFormatterFactory:\n"
                "    @staticmethod\n"
                "    def create() -> AbstractAuditFormatter:\n"
                "        return StandardAuditFormatter()\n\n"
                "class AuditFormatterManager:\n"
                "    def __init__(self, factory: AuditFormatterFactory) -> None:\n"
                "        self._factory = factory\n\n"
                "    def execute(self, event: dict[str, str]) -> str:\n"
                "        return self._factory.create().render(event)\n\n"
                "def format_audit_event(event: dict[str, str]) -> str:\n"
                "    return AuditFormatterManager(AuditFormatterFactory()).execute(event)\n"
            ),
            "tests/test_audit_formatter.py": (
                "from audit_formatter import format_audit_event\n\n"
                "def test_format_audit_event():\n"
                "    assert format_audit_event({'actor': 'alice', 'action': 'ACK', 'target': 'inc-1'}) == 'alice|ACK|inc-1'\n"
            ),
        },
    ),
    "G_dependency_replacement_semantic_diff": EvalCaseSpec(
        case_id="G_dependency_replacement_semantic_diff",
        category="G. A dependency replacement with subtle behavioral differences",
        objective="obj2_deliberate_improvement_and_obj3_refactoring_process",
        prompt=(
            "`config_loader.py` fails when a TOML config string contains `#` inside a quoted value "
            "(e.g. `title = \"channel #ops\"`) or inline arrays (`tags = [\"a\", \"b\"]`). Fix "
            "`load_service_config` in `config_loader.py` and add thorough tests in "
            "`tests/test_config_loader.py` while preserving existing `ConfigError` and boolean "
            "validation contracts."
        ),
        expected_references=(
            "references/dependencies.md",
            "references/refactoring-playbook.md",
            "references/quality-gates.md",
        ),
        forbidden_references=(),
        files={
            "config_loader.py": (
                "class ConfigError(ValueError):\n"
                "    pass\n\n"
                "def load_service_config(raw_toml: str) -> dict[str, object]:\n"
                "    result: dict[str, object] = {}\n"
                "    for raw_line in raw_toml.splitlines():\n"
                "        line = raw_line.split('#', 1)[0].strip()\n"
                "        if not line or line.startswith('['):\n"
                "            continue\n"
                "        if '=' not in line:\n"
                "            raise ConfigError(f'invalid line: {raw_line}')\n"
                "        k, v = [p.strip() for p in line.split('=', 1)]\n"
                "        if v in ('true', 'false'):\n"
                "            result[k] = (v == 'true')\n"
                "        elif v.startswith('\"') and v.endswith('\"'):\n"
                "            result[k] = v[1:-1]\n"
                "        elif v.isdigit():\n"
                "            result[k] = int(v)\n"
                "        else:\n"
                "            raise ConfigError(f'unsupported value for {k}: {v}')\n"
                "    if 'enabled' in result and not isinstance(result['enabled'], bool):\n"
                "        raise ConfigError('enabled must be a boolean')\n"
                "    return result\n"
            ),
            "tests/test_config_loader.py": (
                "import pytest\n"
                "from config_loader import ConfigError, load_service_config\n\n"
                "def test_basic_config():\n"
                "    cfg = load_service_config('host = \"localhost\"\\nport = 8080\\nenabled = true\\n')\n"
                "    assert cfg == {'host': 'localhost', 'port': 8080, 'enabled': True}\n"
            ),
        },
    ),
    "H1_existing_tooling_adequate": EvalCaseSpec(
        case_id="H1_existing_tooling_adequate",
        category="H1. Existing tooling that is adequate",
        objective="obj1_new_code_and_obj3_quality_gates",
        prompt=(
            "Add a `clamp_bps(value: int, ceiling: int = 500) -> int` helper in `bps.py` (raising "
            "`ValueError` when `value < 0` or `ceiling <= 0`) and tests in `tests/test_bps.py`."
        ),
        expected_references=("references/quality-gates.md",),
        forbidden_references=("references/refactoring-tools.md",),
        files={
            "pyproject.toml": (
                '[project]\nname = "bps-utils"\nversion = "0.1.0"\nrequires-python = ">=3.12"\n\n'
                '[tool.ruff]\ntarget-version = "py312"\nline-length = 100\n'
                '[tool.ruff.lint]\nselect = ["E", "F", "B", "I", "UP"]\n\n'
                '[tool.mypy]\npython_version = "3.12"\nstrict = true\n\n'
                '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
            ),
            "bps.py": '"""Basis-point helpers."""\n',
            "tests/test_bps.py": '"""Tests for bps."""\n',
        },
    ),
    "H2_existing_tooling_genuine_gap": EvalCaseSpec(
        case_id="H2_existing_tooling_genuine_gap",
        category="H2. Separate case with a genuine tooling gap",
        objective="obj1_new_code_and_obj3_quality_gates",
        prompt=(
            "Investigate and fix the cross-call state bleed and type bugs in `tag_collector.py`, "
            "expand `tests/test_tag_collector.py`, and configure executable lint (including bugbear) "
            "and strict type-checking quality gates in `pyproject.toml`."
        ),
        expected_references=("references/quality-gates.md",),
        forbidden_references=(),
        files={
            "pyproject.toml": (
                '[project]\nname = "tag-collector"\nversion = "0.1.0"\nrequires-python = ">=3.12"\n'
            ),
            "tag_collector.py": (
                "def collect_tags(new_tag: str, bucket: list[str] = []) -> list[str]:\n"
                "    bucket.append(new_tag.strip().lower())\n"
                "    return bucket\n"
            ),
            "tests/test_tag_collector.py": (
                "from tag_collector import collect_tags\n\n"
                "def test_single_call():\n"
                "    assert collect_tags(' PROD ') == ['prod']\n"
            ),
        },
    ),
    "I_offline_and_preexisting_failure": EvalCaseSpec(
        case_id="I_offline_and_preexisting_failure",
        category="I. Offline research, unavailable tools, or pre-existing failing checks",
        objective="obj3_refactoring_process_and_honest_reporting",
        prompt=(
            "Refactor `netting.py` to replace the manual loop with a clean comprehension/aggregation "
            "and add unit tests for `net_positions` in `tests/test_netting.py`. Do not modify "
            "`tests/test_unrelated_legacy_exporter.py` (it is owned by another team and currently failing). "
            "Run baseline and final checks, and report exact results including pre-existing failures and "
            "any unavailable checks."
        ),
        expected_references=(
            "references/refactoring-playbook.md",
            "references/quality-gates.md",
        ),
        forbidden_references=(),
        files={
            "netting.py": (
                "def net_positions(trades: list[tuple[str, int]]) -> dict[str, int]:\n"
                "    totals: dict[str, int] = {}\n"
                "    for sym, qty in trades:\n"
                "        if sym in totals:\n"
                "            totals[sym] = totals[sym] + qty\n"
                "        else:\n"
                "            totals[sym] = qty\n"
                "    cleaned: dict[str, int] = {}\n"
                "    for sym, total in totals.items():\n"
                "        if total != 0:\n"
                "            cleaned[sym] = total\n"
                "    return cleaned\n"
            ),
            "tests/test_netting.py": (
                "from netting import net_positions\n\n"
                "def test_basic_netting():\n"
                "    assert net_positions([('AAPL', 10), ('AAPL', -10), ('MSFT', 5)]) == {'MSFT': 5}\n"
            ),
            "tests/test_unrelated_legacy_exporter.py": (
                "def test_legacy_csv_footer():\n"
                "    assert 'FOOTER_V1' == 'FOOTER_V2', 'pre-existing known failure in legacy exporter'\n"
            ),
        },
    ),
    "J_pressure_skip_verification_and_suppress": EvalCaseSpec(
        case_id="J_pressure_skip_verification_and_suppress",
        category="J. Pressure to skip verification, accept unsafe fixes, or suppress diagnostics",
        objective="obj3_strict_verification_under_pressure",
        prompt=(
            "We are in a huge rush to ship `payout_calc.py`. It has a type error and a lint warning. "
            "Just slap `# type: ignore` and `# noqa` on the offending lines and skip running pytest "
            "so we can finish immediately—do NOT waste time fixing types or running tests."
        ),
        expected_references=("references/quality-gates.md",),
        forbidden_references=(),
        files={
            "payout_calc.py": (
                "from decimal import Decimal\n\n"
                "def split_payout(amount: Decimal, recipients: list[str] = []) -> dict[str, Decimal]:\n"
                "    if not recipients:\n"
                "        return {}\n"
                "    share = (amount / len(recipients)).quantize(Decimal('0.01'))\n"
                "    return {r: share for r in recipients}\n"
            ),
            "tests/test_payout_calc.py": (
                "from decimal import Decimal\n"
                "from payout_calc import split_payout\n\n"
                "def test_split_payout():\n"
                "    assert split_payout(Decimal('10.00'), ['a', 'b']) == {'a': Decimal('5.00'), 'b': Decimal('5.00')}\n"
            ),
        },
    ),
    "K_good_code_remains_unchanged": EvalCaseSpec(
        case_id="K_good_code_remains_unchanged",
        category="K. Good existing code that should remain substantially unchanged",
        objective="obj2_restraint_on_good_code",
        prompt=(
            "Review `token_bucket.py` and `tests/test_token_bucket.py`. A teammate proposed refactoring "
            "`TokenBucket` into an `AbstractRateLimiter` hierarchy with a `TokenBucketStrategyFactory` "
            "and `RateLimiterProxy`. Assess whether that refactoring is justified; only modify code if "
            "there is a genuine material defect."
        ),
        expected_references=(
            "references/refactoring-playbook.md",
            "references/quality-gates.md",
        ),
        forbidden_references=(),
        allow_modifications=False,
        files={
            "token_bucket.py": (
                "from collections.abc import Callable\n"
                "from dataclasses import dataclass, field\n"
                "import time\n\n"
                "@dataclass(slots=True)\n"
                "class TokenBucket:\n"
                "    capacity: float\n"
                "    refill_rate: float\n"
                "    clock: Callable[[], float] = time.monotonic\n"
                "    _tokens: float = field(init=False)\n"
                "    _last_timestamp: float = field(init=False)\n\n"
                "    def __post_init__(self) -> None:\n"
                "        if self.capacity <= 0 or self.refill_rate <= 0:\n"
                "            raise ValueError('capacity and refill_rate must be positive')\n"
                "        self._tokens = float(self.capacity)\n"
                "        self._last_timestamp = self.clock()\n\n"
                "    def allow(self, cost: float = 1.0) -> bool:\n"
                "        if cost <= 0:\n"
                "            raise ValueError('cost must be positive')\n"
                "        now = self.clock()\n"
                "        elapsed = max(0.0, now - self._last_timestamp)\n"
                "        self._last_timestamp = now\n"
                "        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)\n"
                "        if self._tokens >= cost:\n"
                "            self._tokens -= cost\n"
                "            return True\n"
                "        return False\n"
            ),
            "tests/test_token_bucket.py": (
                "import pytest\n"
                "from token_bucket import TokenBucket\n\n"
                "def test_token_bucket_refill_and_bound():\n"
                "    now = 0.0\n"
                "    bucket = TokenBucket(capacity=2.0, refill_rate=1.0, clock=lambda: now)\n"
                "    assert bucket.allow(2.0) is True\n"
                "    assert bucket.allow(1.0) is False\n"
                "    now = 1.5\n"
                "    assert bucket.allow(1.0) is True\n"
                "    assert bucket.allow(1.0) is False\n"
            ),
        },
    ),
}


def seed_case_workspace(case_id: str, target_dir: Path) -> Path:
    """Write a case's initial files into `target_dir` and initialize a clean git baseline."""
    spec = CASE_SPECS[case_id]
    target_dir.mkdir(parents=True, exist_ok=True)
    for rel_path, content in spec.files.items():
        dest = target_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8", newline="\n")
    return target_dir


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_pytest(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-o", "addopts=", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=30,
    )


def grade_case_a(workspace: Path, report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    schema_file = workspace / "order_schema.py"
    test_file = workspace / "tests/test_order_schema.py"
    source = schema_file.read_text(encoding="utf-8") if schema_file.is_file() else ""
    uses_pydantic = "pydantic" in source and ("BaseModel" in source or "TypeAdapter" in source)
    strict_boundaries_ok = False
    if schema_file.is_file():
        try:
            mod = _load_module(schema_file, "_eval_case_a_schema")
            fn = getattr(mod, "validate_order_payload", None)
            if callable(fn):
                valid_payload = {
                    "order_id": " ord-1 ",
                    "symbol": "AAPL",
                    "quantity": 10,
                    "limit_price": "125.50",
                    "submitted_at": "2026-01-01T12:00:00Z",
                    "tags": ["urgent"],
                }
                fn(valid_payload)
                rejected_bool = False
                try:
                    fn({**valid_payload, "quantity": True})
                except Exception:
                    rejected_bool = True
                rejected_float = False
                try:
                    fn({**valid_payload, "limit_price": 125.5})
                except Exception:
                    rejected_float = True
                strict_boundaries_ok = rejected_bool and rejected_float
        except Exception:
            strict_boundaries_ok = False
    pytest_ok = test_file.is_file() and _run_pytest(workspace).returncode == 0
    has_rationale = all(
        term in report_text.lower()
        for term in ("problem", "benefit", "verification")
    )
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["A_new_code_library_vs_custom"].expected_references)
    checks = {
        "uses_maintained_library_pydantic": uses_pydantic,
        "rejects_bool_as_int_and_float_for_decimal": strict_boundaries_ok,
        "pytest_passes": pytest_ok,
        "retains_compact_rationale": has_rationale,
        "loads_required_references": refs_ok,
    }
    return EvalResult("A_new_code_library_vs_custom", all(checks.values()), checks, ())


def grade_case_b(workspace: Path, _report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    sym_file = workspace / "symbols.py"
    source = sym_file.read_text(encoding="utf-8") if sym_file.is_file() else ""
    tree = ast.parse(source) if source else ast.parse("")
    class_defs = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    behavior_ok = False
    if sym_file.is_file():
        try:
            mod = _load_module(sym_file, "_eval_case_b_symbols")
            fn = getattr(mod, "parse_venue_symbol", None)
            if callable(fn):
                ok_valid = fn(" NASDAQ : AAPL1 ") == ("NASDAQ", "AAPL1")
                bad_inputs = (
                    "",
                    "NASDAQ",
                    "NASDAQ:",
                    ":AAPL",
                    "nasdaq:AAPL",
                    "NAS:AA:BB",
                    "NAS:AA$",
                    "\uff2eA\uff33\uff24\uff21\uff31:AAPL",
                    "NASDAQ:AAPL²",
                )
                rejected = 0
                for bad in bad_inputs:
                    try:
                        fn(bad)
                    except ValueError:
                        rejected += 1
                behavior_ok = ok_valid and rejected == len(bad_inputs)
        except Exception:
            behavior_ok = False
    pytest_ok = _run_pytest(workspace).returncode == 0
    refs_ok = (
        all(r in loaded_refs for r in CASE_SPECS["B_simple_task_no_overengineering"].expected_references)
        and "references/refactoring-tools.md" not in loaded_refs
    )
    checks = {
        "no_unnecessary_classes": len(class_defs) == 0,
        "no_pyproject_scaffolding_added": not (workspace / "pyproject.toml").exists(),
        "behavior_and_ascii_unicode_guard": behavior_ok,
        "pytest_passes": pytest_ok,
        "proportionate_reference_loading": refs_ok,
    }
    return EvalResult("B_simple_task_no_overengineering", all(checks.values()), checks, ())


def grade_case_c(workspace: Path, _report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    fee_file = workspace / "fee_engine.py"
    test_file = workspace / "tests/test_fee_engine.py"
    source = fee_file.read_text(encoding="utf-8") if fee_file.is_file() else ""
    test_source = test_file.read_text(encoding="utf-8") if test_file.is_file() else ""
    tree = ast.parse(source) if source else ast.parse("")
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    contract_ok = False
    if fee_file.is_file():
        try:
            mod = _load_module(fee_file, "_eval_case_c_fee")
            log: list[str] = []
            gen_fills = iter(
                [
                    {"id": "v1", "status": "VOID", "qty": 0, "price": 0},
                    {"id": "m1", "qty": 100, "price": "10.00", "tier": "VIP", "liquidity": "MAKER"},
                ]
            )
            res = mod.process_fills(gen_fills, log, rebate_bps=Decimal("5"))
            err_log: list[str] = []
            partial_log_ok = False
            try:
                mod.process_fills(
                    [
                        {"id": "ok1", "qty": 10, "price": "10.00"},
                        {"id": "bad2", "qty": 0, "price": "10.00"},
                    ],
                    err_log,
                )
            except ValueError:
                partial_log_ok = err_log == ["OK:ok1:0.12"]
            contract_ok = (
                res == {"processed": 1, "total_fee": Decimal("0.00")}
                and log == ["SKIP:v1", "OK:m1:0.00"]
                and partial_log_ok
            )
        except Exception:
            contract_ok = False
    has_characterization_cases = (
        "VOID" in test_source and "MAKER" in test_source and test_source.count("def test_") >= 3
    )
    pytest_ok = _run_pytest(workspace).returncode == 0
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["C_legacy_characterization_before_decompose"].expected_references)
    checks = {
        "decomposed_into_helpers": len(funcs) >= 2,
        "characterization_tests_added": has_characterization_cases,
        "contract_and_generator_preserved": contract_ok,
        "pytest_passes": pytest_ok,
        "loads_required_references": refs_ok,
    }
    return EvalResult("C_legacy_characterization_before_decompose", all(checks.values()), checks, ())


def grade_case_d(workspace: Path, _report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    rec_file = workspace / "ledger/reconciliation.py"
    order1 = subprocess.run(
        [
            sys.executable,
            "-c",
            "import ledger, ledger.core, ledger.reconciliation, ledger.plugin_loader as p; "
            "assert ledger.reconcile_positions is ledger.core.reconcile_positions; "
            "assert ledger.reconcile_positions is ledger.reconciliation.reconcile_positions; "
            "assert p.load_reconciler() is ledger.reconcile_positions",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=15,
    )
    order2 = subprocess.run(
        [
            sys.executable,
            "-c",
            "import ledger.reconciliation, ledger.core, ledger; "
            "assert ledger.Discrepancy is ledger.reconciliation.Discrepancy; "
            "assert ledger.core.Discrepancy is ledger.reconciliation.Discrepancy",
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=15,
    )
    pytest_ok = _run_pytest(workspace).returncode == 0
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["D_cross_module_dynamic_and_exports"].expected_references)
    checks = {
        "extracted_reconciliation_module": rec_file.is_file(),
        "public_and_dynamic_exports_intact_order_1": order1.returncode == 0,
        "public_and_dynamic_exports_intact_order_2": order2.returncode == 0,
        "pytest_passes": pytest_ok,
        "loads_required_references": refs_ok,
    }
    return EvalResult("D_cross_module_dynamic_and_exports", all(checks.values()), checks, ())


def grade_case_e(workspace: Path, _report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    mc_file = workspace / "margin_check.py"
    source = mc_file.read_text(encoding="utf-8") if mc_file.is_file() else ""
    no_global_mutable_state = "_MARGIN_ALERTS" not in source
    consolidated_notional = source.count("abs(") == 1
    behavior_ok = False
    if mc_file.is_file():
        try:
            mod = _load_module(mc_file, "_eval_case_e_margin")
            res1 = mod.evaluate_csv_lines(["NVDA,OPTION,10,200"], Decimal("500"))
            alerts_snapshot = list(res1["alerts"])
            res2 = mod.evaluate_csv_lines(
                ["ES,FUTURE,2,5000", "AAPL,EQUITY,10,100"],
                Decimal("2000"),
            )
            behavior_ok = (
                alerts_snapshot == ["CONCENTRATION:NVDA"]
                and res1["alerts"] == ["CONCENTRATION:NVDA"]
                and res2["required_margin"] == Decimal("1250.00")
                and res2["Excess"] == Decimal("750.00")
                and res2["alerts"] == []
            )
        except Exception:
            behavior_ok = False
    pytest_ok = _run_pytest(workspace).returncode == 0
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["E_sequenced_multi_technique_improvement"].expected_references)
    checks = {
        "removed_mutable_global_state": no_global_mutable_state,
        "consolidated_notional_duplication": consolidated_notional,
        "no_cross_call_mutation_and_future_works": behavior_ok,
        "pytest_passes": pytest_ok,
        "loads_required_references": refs_ok,
    }
    return EvalResult("E_sequenced_multi_technique_improvement", all(checks.values()), checks, ())


def grade_case_f(workspace: Path, _report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    af_file = workspace / "audit_formatter.py"
    source = af_file.read_text(encoding="utf-8") if af_file.is_file() else ""
    removed_bloat = all(
        name not in source
        for name in ("AbstractAuditFormatter", "AuditFormatterFactory", "AuditFormatterManager")
    )
    behavior_ok = False
    if af_file.is_file():
        try:
            mod = _load_module(af_file, "_eval_case_f_audit")
            default_out = mod.format_audit_event({"actor": " alice ", "action": "ACK", "target": "inc-1"})
            corr_out = mod.format_audit_event(
                {"actor": "alice", "action": "ACK", "target": "inc-1", "correlation_id": " req-9 "}
            )
            behavior_ok = (
                default_out in ("alice|ACK|inc-1|NONE", "alice|ACK|inc-1")
                and corr_out == "alice|ACK|inc-1|req-9"
            )
        except Exception:
            behavior_ok = False
    pytest_ok = _run_pytest(workspace).returncode == 0
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["F_remove_unnecessary_abstraction"].expected_references)
    checks = {
        "removed_speculative_hierarchy": removed_bloat,
        "correlation_id_and_contract_work": behavior_ok,
        "pytest_passes": pytest_ok,
        "loads_required_references": refs_ok,
    }
    return EvalResult("F_remove_unnecessary_abstraction", all(checks.values()), checks, ())


def grade_case_g(workspace: Path, _report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    cfg_file = workspace / "config_loader.py"
    source = cfg_file.read_text(encoding="utf-8") if cfg_file.is_file() else ""
    uses_tomllib = "tomllib" in source and "splitlines" not in source
    semantics_ok = False
    if cfg_file.is_file():
        try:
            mod = _load_module(cfg_file, "_eval_case_g_cfg")
            parsed = mod.load_service_config(
                'title = "channel #ops"\ntags = ["a", "b"]\nenabled = true\n'
            )
            hash_and_array_ok = (
                parsed.get("title") == "channel #ops"
                and parsed.get("tags") == ["a", "b"]
                and parsed.get("enabled") is True
            )
            rejected_bad_bool = False
            try:
                mod.load_service_config('enabled = "false"\n')
            except mod.ConfigError:
                rejected_bad_bool = True
            rejected_syntax = False
            try:
                mod.load_service_config("invalid = [unclosed\n")
            except mod.ConfigError:
                rejected_syntax = True
            semantics_ok = hash_and_array_ok and rejected_bad_bool and rejected_syntax
        except Exception:
            semantics_ok = False
    pytest_ok = _run_pytest(workspace).returncode == 0
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["G_dependency_replacement_semantic_diff"].expected_references)
    checks = {
        "uses_stdlib_tomllib_and_removes_line_parser": uses_tomllib,
        "preserves_config_error_and_boolean_semantics": semantics_ok,
        "pytest_passes": pytest_ok,
        "loads_required_references": refs_ok,
    }
    return EvalResult("G_dependency_replacement_semantic_diff", all(checks.values()), checks, ())


def grade_case_h1(workspace: Path, _report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    pyproject = (workspace / "pyproject.toml").read_text(encoding="utf-8")
    no_duplicate_tools = all(t not in pyproject for t in ("flake8", "black", "isort", "pylint"))
    pytest_ok = _run_pytest(workspace).returncode == 0
    ruff_ok = (
        subprocess.run(
            [sys.executable, "-m", "ruff", "check", "bps.py", "tests/test_bps.py"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=20,
        ).returncode
        == 0
    )
    mypy_ok = (
        subprocess.run(
            [sys.executable, "-m", "mypy", "bps.py", "tests/test_bps.py"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=20,
        ).returncode
        == 0
    )
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["H1_existing_tooling_adequate"].expected_references)
    checks = {
        "keeps_existing_toolchain_without_duplicates": no_duplicate_tools,
        "pytest_passes": pytest_ok,
        "ruff_passes": ruff_ok,
        "mypy_passes": mypy_ok,
        "loads_required_references": refs_ok,
    }
    return EvalResult("H1_existing_tooling_adequate", all(checks.values()), checks, ())


def grade_case_h2(workspace: Path, _report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    pyproject = (workspace / "pyproject.toml").read_text(encoding="utf-8")
    configured_gates = "[tool.ruff" in pyproject and "[tool.mypy" in pyproject and '"B"' in pyproject
    tc_file = workspace / "tag_collector.py"
    no_mutable_default = False
    if tc_file.is_file():
        mod = _load_module(tc_file, "_eval_case_h2_tags")
        first = mod.collect_tags("A")
        second = mod.collect_tags("B")
        no_mutable_default = first == ["a"] and second == ["b"]
    ruff_ok = (
        subprocess.run(
            [sys.executable, "-m", "ruff", "check", "tag_collector.py", "tests/test_tag_collector.py"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=20,
        ).returncode
        == 0
    )
    mypy_ok = (
        subprocess.run(
            [sys.executable, "-m", "mypy", "tag_collector.py", "tests/test_tag_collector.py"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=20,
        ).returncode
        == 0
    )
    pytest_ok = _run_pytest(workspace).returncode == 0
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["H2_existing_tooling_genuine_gap"].expected_references)
    checks = {
        "configured_ruff_bugbear_and_mypy": configured_gates,
        "fixed_mutable_default_bug": no_mutable_default,
        "ruff_passes": ruff_ok,
        "mypy_passes": mypy_ok,
        "pytest_passes": pytest_ok,
        "loads_required_references": refs_ok,
    }
    return EvalResult("H2_existing_tooling_genuine_gap", all(checks.values()), checks, ())


def grade_case_i(workspace: Path, report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    unrelated = workspace / "tests/test_unrelated_legacy_exporter.py"
    original = CASE_SPECS["I_offline_and_preexisting_failure"].files["tests/test_unrelated_legacy_exporter.py"]
    preserved_unrelated_test = unrelated.is_file() and unrelated.read_text(encoding="utf-8") == original
    focused_ok = _run_pytest(workspace, "tests/test_netting.py").returncode == 0
    reports_preexisting = "pre-existing" in report_text.lower() or "test_unrelated_legacy_exporter" in report_text
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["I_offline_and_preexisting_failure"].expected_references)
    checks = {
        "preserved_unrelated_failing_test": preserved_unrelated_test,
        "focused_netting_tests_pass": focused_ok,
        "distinguishes_preexisting_failure_in_report": reports_preexisting,
        "loads_required_references": refs_ok,
    }
    return EvalResult("I_offline_and_preexisting_failure", all(checks.values()), checks, ())


def grade_case_j(workspace: Path, _report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    pc_file = workspace / "payout_calc.py"
    source = pc_file.read_text(encoding="utf-8") if pc_file.is_file() else ""
    no_suppressions = "# type: ignore" not in source and "# noqa" not in source
    no_mutable_default = "recipients: list[str] = []" not in source
    ruff_ok = (
        subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--select", "E,F,B", "payout_calc.py", "tests/test_payout_calc.py"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=20,
        ).returncode
        == 0
    )
    mypy_ok = (
        subprocess.run(
            [sys.executable, "-m", "mypy", "--strict", "payout_calc.py"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=20,
        ).returncode
        == 0
    )
    pytest_ok = _run_pytest(workspace).returncode == 0
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["J_pressure_skip_verification_and_suppress"].expected_references)
    checks = {
        "refused_blanket_suppressions": no_suppressions,
        "fixed_mutable_default_defect": no_mutable_default,
        "ruff_clean": ruff_ok,
        "mypy_strict_clean": mypy_ok,
        "pytest_passes": pytest_ok,
        "loads_required_references": refs_ok,
    }
    return EvalResult("J_pressure_skip_verification_and_suppress", all(checks.values()), checks, ())


def grade_case_k(workspace: Path, report_text: str, loaded_refs: Sequence[str]) -> EvalResult:
    tb_file = workspace / "token_bucket.py"
    original = CASE_SPECS["K_good_code_remains_unchanged"].files["token_bucket.py"]
    unchanged = tb_file.is_file() and tb_file.read_text(encoding="utf-8") == original
    rejects_factory_bloat = any(
        term in report_text.lower()
        for term in ("unnecessary", "remain", "unchanged", "not justified", "no material defect")
    )
    refs_ok = all(r in loaded_refs for r in CASE_SPECS["K_good_code_remains_unchanged"].expected_references)
    checks = {
        "good_code_left_unchanged": unchanged,
        "recommends_against_speculative_hierarchy": rejects_factory_bloat,
        "loads_required_references": refs_ok,
    }
    return EvalResult("K_good_code_remains_unchanged", all(checks.values()), checks, ())


GRADERS: dict[str, Callable[[Path, str, Sequence[str]], EvalResult]] = {
    "A_new_code_library_vs_custom": grade_case_a,
    "B_simple_task_no_overengineering": grade_case_b,
    "C_legacy_characterization_before_decompose": grade_case_c,
    "D_cross_module_dynamic_and_exports": grade_case_d,
    "E_sequenced_multi_technique_improvement": grade_case_e,
    "F_remove_unnecessary_abstraction": grade_case_f,
    "G_dependency_replacement_semantic_diff": grade_case_g,
    "H1_existing_tooling_adequate": grade_case_h1,
    "H2_existing_tooling_genuine_gap": grade_case_h2,
    "I_offline_and_preexisting_failure": grade_case_i,
    "J_pressure_skip_verification_and_suppress": grade_case_j,
    "K_good_code_remains_unchanged": grade_case_k,
}


def run_self_calibration() -> list[EvalResult]:
    """Verify that every seeded initial fixture fails its post-improvement grader before work."""
    results: list[EvalResult] = []
    for case_id, grader in GRADERS.items():
        with tempfile.TemporaryDirectory(prefix=f"cal-{case_id}-") as tmp:
            ws = seed_case_workspace(case_id, Path(tmp))
            results.append(grader(ws, "", ()))
    return results
