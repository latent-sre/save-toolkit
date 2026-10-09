"""Repository-wide pytest setup: tests must not change the trees they measure or pick another Python.

The eval runner digests every file under `skills/` as the plugin's identity, so a `__pycache__` that
an in-process import writes there reads as plugin drift (CI sets PYTHONDONTWRITEBYTECODE for the
same reason). Scenario checks and fixture suites shell out to a bare `python`; resolve it to the
interpreter running the tests, as an activated environment would, rather than whatever PATH holds.
"""

import atexit
import os
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

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
