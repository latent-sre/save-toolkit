"""Plugin loader for reconciliation hooks."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

__all__ = ["HOOK_TARGET", "load_reconciler"]

HOOK_TARGET: str = "ledger.core:reconcile_positions"


def load_reconciler() -> Callable[..., Any]:
    """Dynamically load the reconciler hook target."""
    mod_name, attr = HOOK_TARGET.split(":")
    return getattr(importlib.import_module(mod_name), attr)  # type: ignore[no-any-return]
