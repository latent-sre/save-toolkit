from ledger.core import AccountLedger
from ledger.reconciliation import Discrepancy, reconcile_positions


def test_account_ledger_booking() -> None:
    acct = AccountLedger()
    acct.book("AAPL", 50)
    assert acct.snapshot() == {"AAPL": 50}


def test_reconcile_positions_matching() -> None:
    internal = {"AAPL": 100, "MSFT": 50}
    external = {"AAPL": 100, "MSFT": 50}
    assert reconcile_positions(internal, external) == []


def test_reconcile_positions_differing_quantities() -> None:
    internal = {"AAPL": 100, "MSFT": 50}
    external = {"AAPL": 90, "MSFT": 50}
    assert reconcile_positions(internal, external) == [Discrepancy("AAPL", 100, 90)]


def test_reconcile_positions_missing_symbols() -> None:
    internal = {"AAPL": 100}
    external = {"GOOG": 200}
    assert reconcile_positions(internal, external) == [
        Discrepancy("AAPL", 100, 0),
        Discrepancy("GOOG", 0, 200),
    ]


def test_reconcile_positions_sorting() -> None:
    internal = {"TSLA": 10, "AMZN": 20, "AAPL": 30}
    external = {"TSLA": 15, "AMZN": 25, "AAPL": 35}
    discrepancies = reconcile_positions(internal, external)
    assert [d.symbol for d in discrepancies] == ["AAPL", "AMZN", "TSLA"]


def test_reconcile_positions_empty() -> None:
    assert reconcile_positions({}, {}) == []


def test_reconciliation_module_exports_and_reexports() -> None:
    import ledger
    import ledger.core
    import ledger.reconciliation

    assert ledger.Discrepancy is ledger.reconciliation.Discrepancy
    assert ledger.reconcile_positions is ledger.reconciliation.reconcile_positions
    assert ledger.core.Discrepancy is ledger.reconciliation.Discrepancy
    assert ledger.core.reconcile_positions is ledger.reconciliation.reconcile_positions


def test_plugin_loader_resolves_reconciler() -> None:
    from ledger.plugin_loader import load_reconciler

    reconciler = load_reconciler()
    assert reconciler({"AAPL": 10}, {"AAPL": 20}) == [Discrepancy("AAPL", 10, 20)]
