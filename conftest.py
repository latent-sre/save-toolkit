"""Repository-wide pytest setup: tests must not change the trees they measure or pick another Python.

The eval runner digests every file under `skills/` as the plugin's identity, so a `__pycache__` that
an in-process import writes there reads as plugin drift (CI sets PYTHONDONTWRITEBYTECODE for the
same reason). Scenario checks and fixture suites shell out to a bare `python`; resolve it to the
interpreter running the tests, as an activated environment would, rather than whatever PATH holds.

The eval-machinery files in HEAVY spawn real processes and hold most of the suite's run time. A
plain run skips them; `--heavy` adds them, `-m heavy` runs only them, and a file named on the
command line always runs. CI's eval-tests job runs `-m heavy`.
"""

import atexit
import os
import re
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

HEAVY = frozenset({
    "evals/test_agent_injection_pairs.py",
    "evals/test_eval011_fingerprints.py",
    "evals/test_eval011_oracles.py",
    "evals/test_gcp_cases.py",
    "evals/test_incident_writes_oracle.py",
    "evals/test_maintenance_banner_oracle.py",
    "evals/test_natural_injection.py",
    "evals/test_openapi_document_oracle.py",
    "evals/test_operator_cli_oracle.py",
    "evals/test_pager_webhook_mutants.py",
    "evals/test_pager_webhook_mutants_durable.py",
    "evals/test_pager_webhook_mutants_redelivery.py",
    "evals/test_pager_webhook_oracle.py",
    "evals/test_probe_checking.py",
    "evals/test_probe_trials.py",
    "evals/test_python_craft_oracle.py",
    "evals/test_python_index_probe.py",
    "evals/test_python_library_selection_oracle.py",
    "evals/test_python_new_code_probe.py",
    "evals/test_python_package_refactor.py",
    "evals/test_reliability_cases.py",
})


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--heavy", action="store_true",
                     help="include the heavy eval-machinery tests (CI's eval-tests job runs them)")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "heavy: an eval-machinery test that spawns real processes")


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:
    """Avoid importing the other shard; mixed marker expressions still use pytest's evaluator."""
    root = config.rootpath
    if collection_path.suffix != ".py" or not collection_path.is_relative_to(root):
        return None
    heavy = collection_path.relative_to(root).as_posix() in HEAVY
    expression = (config.getoption("markexpr") or "").strip()
    if expression == "heavy":
        return not heavy
    if expression == "not heavy":
        return heavy
    if heavy and not config.getoption("--heavy") and "heavy" not in re.findall(r"\w+", expression):
        named = {(config.invocation_params.dir / arg.split("::", 1)[0]).resolve() for arg in config.args}
        return collection_path not in named
    return None


@pytest.hookimpl(tryfirst=True)  # mark before `-m` selects, so `-m heavy` sees the marker
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    root = config.rootpath.resolve()
    named = {(config.invocation_params.dir / arg.split("::", 1)[0]).resolve() for arg in config.args}
    # A marker name as a whole word, so `-m "not heavyweight"` does not pull the heavy files in.
    include = config.getoption("--heavy") or "heavy" in re.findall(r"\w+", config.getoption("markexpr") or "")
    keep, skipped = [], []
    for item in items:
        path = item.path.resolve()
        if path.is_relative_to(root) and path.relative_to(root).as_posix() in HEAVY:
            item.add_marker(pytest.mark.heavy)
            if not include and path not in named:
                skipped.append(item)
                continue
        keep.append(item)
    if skipped:
        config.hook.pytest_deselected(items=skipped)
        items[:] = keep


sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def _python_on_path() -> None:
    directory = str(Path(sys.executable).parent)
    if not shutil.which("python", path=directory):
        # A bare system interpreter may ship only `python3`. A wrapper rather than a symlink keeps
        # the interpreter's own path, which is how a virtual environment finds its pyvenv.cfg.
        directory = tempfile.mkdtemp(prefix="pytest-python-")
        atexit.register(shutil.rmtree, directory, ignore_errors=True)
        shim = Path(directory, "python")
        shim.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
    os.environ["PATH"] = os.pathsep.join((directory, os.environ.get("PATH", "")))


_python_on_path()
