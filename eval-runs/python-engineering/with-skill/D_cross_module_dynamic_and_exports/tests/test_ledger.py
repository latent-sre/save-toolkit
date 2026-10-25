"""Tests for ledger, reconciliation, and dynamic plugin loading."""

from __future__ import annotations

import ledger
import ledger.reconciliation as recon
from ledger import AccountLedger, Discrepancy, core, reconcile_positions
from ledger.plugin_loader import load_reconciler


def test_ledger_and_reconcile() -> None:
    acct = AccountLedger()
    acct.book("AAPL", 50)
    diffs = reconcile_positions(acct.snapshot(), {"AAPL": 40})
    assert diffs == [Discrepancy("AAPL", 50, 40)]
    assert load_reconciler() is ledger.reconcile_positions


def test_backward_compatibility_re_exports() -> None:
    # Verify symbols are accessible via ledger.core as well as ledger.reconciliation
    assert core.Discrepancy is recon.Discrepancy
    assert core.reconcile_positions is recon.reconcile_positions
    assert ledger.Discrepancy is recon.Discrepancy
    assert ledger.reconcile_positions is recon.reconcile_positions


def test_dynamic_plugin_loader() -> None:
    # Verifies dynamic import via HOOK_TARGET ('ledger.core:reconcile_positions')
    reconciler = load_reconciler()
    assert reconciler is recon.reconcile_positions
    diffs = reconciler({"MSFT": 10}, {"MSFT": 20})
    assert diffs == [recon.Discrepancy("MSFT", 10, 20)]


def test_reconciliation_details() -> None:
    internal = {"AAPL": 100, "GOOGL": 50, "MSFT": 20}
    external = {"AAPL": 100, "GOOGL": 60, "AMZN": 10}

    # Should report GOOGL (diff), AMZN (missing in internal), MSFT (missing in external)
    # Sorted alphabetically
    diffs = recon.reconcile_positions(internal, external)
    assert diffs == [
        recon.Discrepancy("AMZN", 0, 10),
        recon.Discrepancy("GOOGL", 50, 60),
        recon.Discrepancy("MSFT", 20, 0),
    ]


def test_reconciliation_identical_positions() -> None:
    positions = {"AAPL": 100, "GOOGL": 200}
    assert recon.reconcile_positions(positions, positions) == []


def test_account_ledger_booking() -> None:
    ledger_instance = core.AccountLedger()
    ledger_instance.book("AAPL", 100)
    ledger_instance.book("AAPL", -30)
    ledger_instance.book("TSLA", 25)

    snap = ledger_instance.snapshot()
    assert snap == {"AAPL": 70, "TSLA": 25}

    # Ensure snapshot is an isolated copy
    snap["AAPL"] = 999
    assert ledger_instance.snapshot()["AAPL"] == 70
