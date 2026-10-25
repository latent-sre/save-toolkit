"""Tests for ledger modules."""

import ledger
from ledger.core import (
    AccountLedger,
)
from ledger.core import (
    Discrepancy as LegacyDiscrepancy,
)
from ledger.core import (
    reconcile_positions as legacy_reconcile_positions,
)
from ledger.plugin_loader import load_reconciler
from ledger.reconciliation import Discrepancy, reconcile_positions


def test_ledger_and_reconcile():
    acct = AccountLedger()
    acct.book("AAPL", 50)
    diffs = reconcile_positions(acct.snapshot(), {"AAPL": 40})
    assert diffs == [Discrepancy("AAPL", 50, 40)]
    assert load_reconciler() is ledger.reconcile_positions


def test_backward_compatibility():
    # Ensure legacy imports from ledger.core remain functional and identical
    assert LegacyDiscrepancy is Discrepancy
    assert legacy_reconcile_positions is reconcile_positions
    assert ledger.reconcile_positions is reconcile_positions
    assert ledger.Discrepancy is Discrepancy
