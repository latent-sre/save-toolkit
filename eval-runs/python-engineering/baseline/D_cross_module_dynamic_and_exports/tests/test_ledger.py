"""Tests for AccountLedger, position reconciliation, and dynamic loading."""

import importlib

import ledger
from ledger.core import AccountLedger
from ledger.core import Discrepancy as CoreDiscrepancy
from ledger.core import reconcile_positions as core_reconcile
from ledger.plugin_loader import HOOK_TARGET, load_reconciler
from ledger.reconciliation import Discrepancy, reconcile_positions


def test_account_ledger_booking():
    acct = AccountLedger()
    acct.book("AAPL", 50)
    acct.book("AAPL", -20)
    acct.book("MSFT", 10)
    assert acct.snapshot() == {"AAPL": 30, "MSFT": 10}


def test_reconcile_positions_matching():
    internal = {"AAPL": 100, "MSFT": 200}
    external = {"AAPL": 100, "MSFT": 200}
    assert reconcile_positions(internal, external) == []


def test_reconcile_positions_discrepancies():
    internal = {"AAPL": 100, "GOOG": 50, "CASH": 10}
    external = {"AAPL": 90, "MSFT": 30, "CASH": 10}

    diffs = reconcile_positions(internal, external)
    assert diffs == [
        Discrepancy(symbol="AAPL", internal_qty=100, external_qty=90),
        Discrepancy(symbol="GOOG", internal_qty=50, external_qty=0),
        Discrepancy(symbol="MSFT", internal_qty=0, external_qty=30),
    ]


def test_backward_compatibility_reexports():
    # Verify core re-exports
    assert core_reconcile is reconcile_positions
    assert CoreDiscrepancy is Discrepancy

    # Verify top-level package exports
    assert ledger.AccountLedger is AccountLedger
    assert ledger.Discrepancy is Discrepancy
    assert ledger.reconcile_positions is reconcile_positions


def test_plugin_loader_hook():
    loaded = load_reconciler()
    assert loaded is reconcile_positions
    assert HOOK_TARGET == "ledger.reconciliation:reconcile_positions"

    # Also verify legacy core hook target still resolves correctly
    mod_name, attr = ["ledger.core", "reconcile_positions"]
    legacy_loaded = getattr(importlib.import_module(mod_name), attr)
    assert legacy_loaded is reconcile_positions
