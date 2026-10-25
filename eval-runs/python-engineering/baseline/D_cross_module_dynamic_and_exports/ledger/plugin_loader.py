"""Plugin loader for ledger hooks."""

import importlib

HOOK_TARGET = "ledger.reconciliation:reconcile_positions"


def load_reconciler():
    """Dynamically load and return the reconciler function targeted by HOOK_TARGET."""
    mod_name, attr = HOOK_TARGET.split(":")
    return getattr(importlib.import_module(mod_name), attr)
