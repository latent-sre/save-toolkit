"""Run a reviewed Python oracle with explicit completion and failure evidence.

This is measurement bookkeeping on a trusted host, not containment of hostile code.
Only contract assertions, explicit exit 10, and errors attributed to candidate code
are failures. An unexpected oracle error remains exit 1 (measurement unavailable).
"""

import json
import mmap
from pathlib import Path
import runpy
import secrets
import subprocess
import sys
import tempfile
import traceback
from types import ModuleType


FAILURE = 10
_ACTIVE_ORACLE = None
_CANDIDATE_STATE = None


def candidate_call(function, *args, **kwargs):
    """Attribute an escaping candidate error without changing expected exceptions."""
    previous = _CANDIDATE_STATE[0] if _CANDIDATE_STATE is not None else 0
    if _CANDIDATE_STATE is not None:
        _CANDIDATE_STATE[0] = 1
    try:
        return function(*args, **kwargs)
    except (Exception, SystemExit) as exc:
        # A callback supplied by the oracle can itself be defective. Do not
        # charge its crash to the candidate simply because the candidate called it.
        exc._oracle_candidate_error = _origin(exc, _ACTIVE_ORACLE) != "oracle"
        raise
    finally:
        if _CANDIDATE_STATE is not None:
            _CANDIDATE_STATE[0] = previous


def _candidate_path(filename, oracle):
    if not filename or str(filename).startswith("<"):
        return False
    path = Path(filename).resolve()
    return path.is_relative_to(Path.cwd()) and path not in (oracle, Path(__file__).resolve())


def _origin(exc, oracle):
    origin = None
    tb = exc.__traceback__
    while tb:
        filename = tb.tb_frame.f_code.co_filename
        if oracle is not None and Path(filename).resolve() == oracle:
            origin = "oracle"
        elif _candidate_path(filename, oracle):
            origin = "candidate"
        tb = tb.tb_next
    return origin


def candidate_error(exc, oracle):
    if getattr(exc, "_oracle_candidate_error", False):
        return True
    if isinstance(exc, SyntaxError) and _candidate_path(getattr(exc, "filename", None), oracle):
        return True
    if isinstance(exc, AttributeError) and isinstance(exc.obj, ModuleType):
        if _candidate_path(getattr(exc.obj, "__file__", None), oracle):
            return True
    return _origin(exc, oracle) == "candidate"


def _child(receipt, state, nonce, argv):
    global _ACTIVE_ORACLE, _CANDIDATE_STATE
    oracle = Path(argv[0]).resolve(strict=True)
    _ACTIVE_ORACLE = oracle
    with open(state, "r+b") as stream:
        _CANDIDATE_STATE = mmap.mmap(stream.fileno(), 1)
    sys.argv = [str(oracle), *argv[1:]]
    # Equivalent to a normal script import path; isolated commands still require
    # the oracle to opt into candidate imports from the working directory.
    sys.path.insert(0, str(oracle.parent))
    sys.modules["oracle_protocol"] = sys.modules[__name__]
    code = 0
    try:
        runpy.run_path(str(oracle), run_name="__main__")
    except SystemExit as exc:
        if candidate_error(exc, oracle):
            traceback.print_exception(exc)
            code = FAILURE
        elif exc.code is None or type(exc.code) is int:
            code = exc.code or 0
        else:
            traceback.print_exception(exc)
            code = 1
    except AssertionError as exc:
        traceback.print_exception(exc)
        code = FAILURE
    except Exception as exc:
        traceback.print_exception(exc)
        code = FAILURE if candidate_error(exc, oracle) else 1
    # Reached only after assessment; stdout text and preexisting workspace files
    # are never completion evidence. A fresh per-launch nonce prevents stale reuse.
    Path(receipt).write_text(json.dumps({"nonce": nonce, "code": code}), encoding="utf-8")
    return code


def supervise(argv):
    with tempfile.TemporaryDirectory(prefix="oracle-completion-") as directory:
        receipt = Path(directory) / "result.json"
        state = Path(directory) / "candidate-state"
        state.write_bytes(b"\0")
        nonce = secrets.token_hex(24)
        command = [sys.executable, "-B"]
        if sys.flags.isolated:
            command.append("-I")
        command += [str(Path(__file__).resolve()), "--child", str(receipt), str(state), nonce, *argv]
        with state.open("r+b") as stream, mmap.mmap(stream.fileno(), 1) as phase:
            result = subprocess.run(command)
            candidate_active = phase[0] == 1
        if not receipt.is_file():
            if candidate_active and 0 <= result.returncode <= 255:
                print("FAIL: candidate exited before oracle completion", file=sys.stderr)
                return FAILURE
            print("INCONCLUSIVE: oracle process stopped without assessment", file=sys.stderr)
            return 1
        data = json.loads(receipt.read_text(encoding="utf-8"))
        if data != {"nonce": nonce, "code": result.returncode}:
            raise RuntimeError("oracle completion does not match this invocation")
        return result.returncode


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        raise SystemExit(_child(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:]))
    if len(sys.argv) < 2:
        raise SystemExit("usage: oracle_protocol.py <oracle.py> [args ...]")
    raise SystemExit(supervise(sys.argv[1:]))
