#!/usr/bin/env python3
"""Run local pytest once per shared Git checkout and retain its timing evidence.

Usage: python scripts/local_tests.py [pytest arguments], adding --heavy for the whole suite.
Linked worktrees share an OS-held lease; direct pytest commands and separate clones do not.
Logs and receipts live in the common Git directory, outside the measured plugin tree.
"""

from __future__ import annotations

import argparse
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
from typing import TYPE_CHECKING, Any

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
            if sys.platform == "win32":
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
            if sys.platform == "win32":
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
    def __init__(self, expected_paths: list[str] | None = None) -> None:
        self.effective: dict[str, object] = {}
        self.results: dict[str, object] = {}
        self.expected_paths = expected_paths

    def pytest_configure(self, config: pytest.Config) -> None:
        collection = {name: config.getini(name) for name in (
            "python_files", "python_classes", "python_functions", "testpaths", "norecursedirs")}
        collection_overrides = sorted({
            option.partition("=")[0].strip() for option in config.getoption("override_ini", default=[]) or []
            if option.partition("=")[0].strip() in collection
        })
        self.effective = {
            "collection": collection,
            "collection_overrides": collection_overrides,
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
        if self.expected_paths is not None:
            import pytest  # noqa: PLC0415 -- pytest is initialized only by the lease owner

            actual = [str((config.invocation_params.dir / arg).resolve()) for arg in config.args]
            expected = [str((config.invocation_params.dir / arg).resolve()) for arg in self.expected_paths]
            if actual != expected:
                raise pytest.UsageError("--suite cannot be combined with explicit test paths")
            filtered = bool(collection_overrides) or any(self.effective[key] for key in (
                "marker", "keyword", "collect_only", "ignored_paths", "ignored_globs", "deselected_nodes",
                "last_failed", "stepwise", "stepwise_skip"))
            self.effective["suite_filtered"] = filtered
            if filtered:
                print("Named suite run is filtered; this is not the complete suite.", flush=True)

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        self.results = {"collected": session.testscollected, "failed": session.testsfailed}


def run(root: Path, arguments: list[str], *, suite_selection: dict[str, Any] | None = None) -> int:
    shared = common_git_dir(root)
    with suite_lease(shared / "local-tests.lock"):
        started = datetime.now(UTC)
        output = shared / "local-test-runs" / f"{started:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
        output.mkdir(parents=True)
        args = ["-q", "--durations=20", *arguments, f"--junitxml={output / 'junit.xml'}"]
        settings = RunSettings([item["path"] for item in suite_selection["items"]] if suite_selection else None)
        record: dict[str, object] = {
            "started_utc": started.isoformat(), "pid": os.getpid(), "worktree": str(root),
            "source_before": source_state(root), "command": [sys.executable, "-m", "pytest", *args],
            "python": sys.version, "platform": platform.platform(),
            "versions": {name: importlib.metadata.version(name) for name in ("pytest", "pytest-xdist")},
            "exit_code": None,
        }
        if suite_selection is not None:
            record["suite_selection"] = suite_selection
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
            if settings.effective.get("suite_filtered"):
                print("Named suite run was filtered; inspect effective settings in run.json.")
            print(f"Local tests: exit {exit_code} in {record['elapsed_seconds']}s; evidence {output}")
        return exit_code


def resolve_suites(root: Path, arguments: list[str]) -> tuple[list[str], dict[str, Any] | None, bool]:
    """Resolve only our flags; let pytest parse its options and their values."""
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--suite", action="append", default=[])
    parser.add_argument("--list-suites", action="store_true")
    args, remainder = parser.parse_known_args(arguments)
    if not args.suite and not args.list_suites:
        return arguments, None, False
    if args.list_suites and (args.suite or remainder):
        raise ValueError("--list-suites cannot be combined with test arguments")
    names = sorted(set(args.suite))
    command = [sys.executable, str(root / "evals/catalog.py"), "suites" if args.list_suites else "tests", "--json"]
    for name in names:
        command.extend(["--suite", name])
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30)
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "catalog lookup failed")
    result = json.loads(completed.stdout)
    expected_view = "suites" if args.list_suites else "tests"
    if (not isinstance(result, dict) or type(result.get("schema_version")) is not int
            or result["schema_version"] != 1 or result.get("view") != expected_view
            or not isinstance(result.get("items"), list)):
        raise ValueError("unsupported catalog response")
    if args.list_suites:
        for suite in result["items"]:
            print(f"{suite['id']}: {suite['summary']}")
        return [], None, True
    paths: list[str] = []
    for item in result["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("invalid catalog test entry")
        relative = item["path"]
        path = Path(relative)
        if (path.is_absolute() or len(path.parts) != 2 or path.parts[0] not in {"scripts", "evals"}
                or not path.name.startswith("test_") or path.suffix != ".py" or "\\" in relative
                or ":" in relative or any((root / Path(*path.parts[:i])).is_symlink() for i in (1, 2))
                or not (root / path).is_file()):
            raise ValueError("invalid catalog test path")
        paths.append(relative)
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("suite must resolve to nonempty unique test paths")
    return [*paths, *remainder], {"names": names, "items": result["items"]}, False


def main() -> int:
    try:
        # The script's checkout owns configuration and discovery, regardless of launch cwd.
        os.chdir(ROOT)
        arguments, selection, listed = resolve_suites(ROOT, sys.argv[1:])
        return 0 if listed else run(ROOT, arguments, suite_selection=selection)
    except SuiteBusy as exc:
        print(f"Local tests: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Local tests: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
