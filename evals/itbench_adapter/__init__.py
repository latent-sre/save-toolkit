"""WP04 recorded-evidence adaptation; no candidate or judge execution."""

from .bindings import build_bindings
from .core import assess_local, binding_candidates, export_submission, fetch_sources, stage_case, validate_manifest
from .native import collect_submission, prepare_ground_truth, prepare_native

__all__ = [
    "assess_local",
    "binding_candidates",
    "build_bindings",
    "collect_submission",
    "export_submission",
    "fetch_sources",
    "prepare_ground_truth",
    "prepare_native",
    "stage_case",
    "validate_manifest",
]
