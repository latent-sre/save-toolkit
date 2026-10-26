import importlib
from typing import Any

HOOK_TARGET = "ledger.reconciliation:reconcile_positions"


def load_reconciler() -> Any:
    mod_name, attr = HOOK_TARGET.split(":")
    return getattr(importlib.import_module(mod_name), attr)
