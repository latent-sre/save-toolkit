"""Plugin loader for ledger hooks."""

import importlib

HOOK_TARGET = "ledger.reconciliation:reconcile_positions"


def load_reconciler():
    """Load reconciler function dynamically from HOOK_TARGET."""
    mod_name, attr = HOOK_TARGET.split(":")
    return getattr(importlib.import_module(mod_name), attr)
