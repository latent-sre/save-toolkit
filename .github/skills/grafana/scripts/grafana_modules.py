"""Load fixed, bundled Grafana modules under isolated Python without sys.path edits.

Entrypoints bootstrap this stdlib-only file with runpy.run_path. The module cache
is private to its resolved bundle directory, so another checkout or generated
adapter cannot silently supply a sibling from an earlier import.
"""

import hashlib
import importlib.util
import os
import sys
from pathlib import Path

_DIRECTORY = Path(__file__).resolve().parent
_PREFIX = '_save_toolkit_grafana_' + hashlib.sha256(os.path.normcase(str(_DIRECTORY)).encode()).hexdigest() + '_'
_MODULES = frozenset({
    'dashboard_hygiene', 'grafana_alert_preview', 'grafana_analyze', 'grafana_capture',
    'grafana_dependencies', 'grafana_evidence', 'grafana_frames', 'grafana_plan',
    'grafana_promql', 'grafana_read', 'grafana_vscode',
})


def load_module(name):
    """Load one allowed sibling once; never accept paths or search-path modules."""
    if not isinstance(name, str) or name not in _MODULES:
        raise ValueError('unsupported_grafana_module')
    path = _DIRECTORY / (name + '.py')
    key = _PREFIX + name
    existing = sys.modules.get(key)
    if existing is not None:
        if getattr(existing, '__file__', None) != str(path):
            raise ValueError('unexpected_grafana_module')
        return existing
    spec = importlib.util.spec_from_file_location(key, path)
    if spec is None or spec.loader is None:
        raise ImportError('grafana_module_unavailable')
    module = importlib.util.module_from_spec(spec)
    # Dataclasses and other registries need the module registered during execution.
    sys.modules[key] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(key, None)
        raise
    return module
