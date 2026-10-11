#!/usr/bin/env python3
"""Run local pytest once per shared Git checkout and retain its timing evidence.

Usage: python scripts/local_tests.py [pytest arguments], adding --heavy for the whole suite.
Linked worktrees share an OS-held lease; direct pytest commands and separate clones do not.
Logs and receipts live in the common Git directory, outside the measured plugin tree.
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[1]


class SuiteBusy(RuntimeError):
    """Another cooperating runner owns the shared checkout's test lease."""


@contextlib.contextmanager
def suite_lease(path: Path) -> Iterator[None]:
    # Never unlink the lock file: another process could still hold its inode open.
    with path.open("a+b") as lease:
        try:
            if os.name == "nt":
                import msvcrt  # noqa: PLC0415 -- platform-only standard library

                lease.seek(0)
                msvcrt.locking(lease.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl  # noqa: PLC0415 -- platform-only standard library

                fcntl.flock(lease.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise
            raise SuiteBusy(f"another coordinated test run holds {path}; wait for its owner to finish") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                lease.seek(0)
                msvcrt.locking(lease.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lease.fileno(), fcntl.LOCK_UN)


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, timeout=30).stdout


def common_git_dir(root: Path) -> Path:
    return Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip())


def source_state(root: Path) -> dict[str, object]:
    status = git(root, "status", "--porcelain=v1", "--untracked-files=normal").decode("utf-8", errors="replace")
    return {
        "head": git(root, "rev-parse", "HEAD").decode().strip(),
        "dirty": bool(status),
        "status": status,
        # No patch contents or environment credentials enter the receipt. Untracked
        # paths mark it dirty; their contents are not claimed to be revision-bound.
        "tracked_diff_sha256": hashlib.sha256(git(root, "diff", "--binary", "HEAD")).hexdigest(),
    }


class RunSettings:
    def __init__(self) -> None:
        self.effective: dict[str, object] = {}
        self.results: dict[str, object] = {}

    def pytest_configure(self, config: pytest.Config) -> None:
        self.effective = {
            "workers": config.getoption("numprocesses", default=0),
            "distribution": config.getoption("dist", default="no"),
            "heavy": config.getoption("heavy", default=False),
            "marker": config.getoption("markexpr"),
            "keyword": config.getoption("keyword"),
            "collect_only": config.getoption("collectonly"),
            "ignored_paths": config.getoption("ignore"),
            "ignored_globs": config.getoption("ignore_glob"),
            "deselected_nodes": config.getoption("deselect"),
            "max_failures": config.getoption("maxfail"),
            "last_failed": config.getoption("lf", default=False),
            "last_failed_no_failures": config.getoption("last_failed_no_failures", default=None),
            "failed_first": config.getoption("failedfirst", default=False),
            "stepwise": config.getoption("stepwise", default=False),
            "stepwise_skip": config.getoption("stepwise_skip", default=False),
            "selected_paths": list(config.args),
        }

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        self.results = {"collected": session.testscollected, "failed": session.testsfailed}


def run(root: Path, arguments: list[str]) -> int:
    shared = common_git_dir(root)
    with suite_lease(shared / "local-tests.lock"):
        started = datetime.now(UTC)
        output = shared / "local-test-runs" / f"{started:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
        output.mkdir(parents=True)
        args = ["-q", "--durations=20", *arguments, f"--junitxml={output / 'junit.xml'}"]
        settings = RunSettings()
        record: dict[str, object] = {
            "started_utc": started.isoformat(), "pid": os.getpid(), "worktree": str(root),
            "source_before": source_state(root), "command": [sys.executable, "-m", "pytest", *args],
            "python": sys.version, "platform": platform.platform(),
            "versions": {name: importlib.metadata.version(name) for name in ("pytest", "pytest-xdist")},
            "exit_code": None,
        }
        receipt = output / "run.json"
        receipt.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"Local tests: {output}\nFollow pytest.log for progress.", flush=True)
        clock_start = time.monotonic()
        exit_code = 3
        try:
            import pytest  # noqa: PLC0415 -- only the lease owner initializes pytest

            with (output / "pytest.log").open("w", encoding="utf-8") as log, \
                    contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                exit_code = int(pytest.main(args, plugins=[settings]))
        finally:
            record.update({
                "finished_utc": datetime.now(UTC).isoformat(),
                "elapsed_seconds": round(time.monotonic() - clock_start, 3),
                "exit_code": exit_code, "effective": settings.effective, "results": settings.results,
                "source_after": source_state(root),
            })
            receipt.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            log_path = output / "pytest.log"
            if log_path.is_file():
                print("\n".join(log_path.read_text(encoding="utf-8").splitlines()[-50:]))
            print(f"Local tests: exit {exit_code} in {record['elapsed_seconds']}s; evidence {output}")
        return exit_code


def main() -> int:
    try:
        # The script's checkout owns configuration and discovery, regardless of launch cwd.
        os.chdir(ROOT)
        return run(ROOT, sys.argv[1:])
    except SuiteBusy as exc:
        print(f"Local tests: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
