"""Small, nonpersisting output, wall-time and writable-layer execution bounds."""

from __future__ import annotations

import contextlib
import math
import os
import re
import signal
import subprocess
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from .windows_job import JobError, WindowsJob

_STDOUT_LIMIT = 64 * 1024 * 1024
_STDERR_LIMIT = 1024 * 1024
STORAGE_LIMIT = 10 * 1024**3  # Docker's size=10G uses binary units (10 GiB).
_STORAGE_INTERVAL = 60.0
_EXEC_TIMEOUT = 60.0
_MONITOR_TIMEOUT = 5.0
_PIPE_TIMEOUT = 1.0
_WINDOWS = os.name == "nt"


@dataclass(frozen=True)
class ProcessResult:
    stdout: bytes
    stderr: bytes
    returncode: int
    stop: str | None
    seconds: float
    cleanup_complete: bool = True
    pid: int | None = None


def _terminate(process: subprocess.Popen[bytes], job: WindowsJob | None = None) -> bool:
    clean = True
    if _WINDOWS:
        if job is not None:
            clean = job.close()
        else:
            try:
                process.kill()  # A startup failure can leave an unassigned suspended root.
            except OSError:
                clean = False
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError:
            clean = False
        try:
            process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass
        except OSError:
            clean = False
        # A parent may exit before its descendants. Kill the owned group even
        # when wait() already observed the parent's exit.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            clean = False
    try:
        process.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        clean = False
    return clean


def run_bounded(command: Sequence[str], *, cwd: Path, env: Mapping[str, str], timeout: float) -> ProcessResult:
    """Run one owned child tree, retaining bounded output in memory only."""
    started = time.monotonic()
    if not math.isfinite(timeout) or timeout <= 0:
        return ProcessResult(b"", b"", -1, "timeout", time.monotonic() - started)
    job = None
    if _WINDOWS:
        try:
            job = WindowsJob()
        except JobError:
            return ProcessResult(b"", b"", -1, "ownership_failure", time.monotonic() - started, False)
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=not _WINDOWS,
            creationflags=0x204 if _WINDOWS else 0,  # CREATE_SUSPENDED | CREATE_NEW_PROCESS_GROUP
        )
    except (OSError, ValueError):
        clean = job.close() if job is not None else True
        return ProcessResult(b"", b"", -1, "spawn_failure", time.monotonic() - started, clean)
    except KeyboardInterrupt:
        if job is not None:
            job.close()
        # Startup did not return an owned PID, so absence cannot be established.
        return ProcessResult(b"", b"", -1, "interrupted", time.monotonic() - started, False)
    if job is not None:
        try:
            job.assign_and_resume(process.pid)
        except (JobError, KeyboardInterrupt) as error:
            # Assignment itself may have failed, leaving the root outside the job.
            with contextlib.suppress(OSError):
                process.kill()
            clean = _terminate(process, job)
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
            return ProcessResult(
                b"",
                b"",
                process.returncode if process.returncode is not None else -1,
                "interrupted" if isinstance(error, KeyboardInterrupt) else "ownership_failure",
                time.monotonic() - started,
                clean,
                process.pid,
            )
    stdout, stderr = bytearray(), bytearray()
    exceeded, failed = threading.Event(), threading.Event()
    lock = threading.Lock()

    def drain(stream: BinaryIO, target: bytearray, limit: int) -> None:
        try:
            while chunk := stream.read1(65536):  # type: ignore[attr-defined]
                with lock:
                    available = max(0, limit - len(target))
                    target.extend(chunk[:available])
                if len(chunk) > available:
                    exceeded.set()
        except (OSError, ValueError):
            failed.set()

    assert process.stdout is not None and process.stderr is not None
    threads = [
        threading.Thread(target=drain, args=(stream, target, limit), daemon=True)
        for stream, target, limit in ((process.stdout, stdout, _STDOUT_LIMIT), (process.stderr, stderr, _STDERR_LIMIT))
    ]
    for thread in threads:
        thread.start()
    stop = None
    try:
        while True:
            if exceeded.is_set():
                stop = "output_limit"
                break
            if failed.is_set():
                stop = "capture_failure"
                break
            if time.monotonic() - started >= timeout:
                stop = "timeout"
                break
            if process.poll() is not None and not any(thread.is_alive() for thread in threads):
                break
            time.sleep(0.01)
    except KeyboardInterrupt:
        stop = "interrupted"
    finally:
        # This also covers a parent that exited but left descendants holding pipes.
        clean = _terminate(process, job)
        pipe_deadline = time.monotonic() + _PIPE_TIMEOUT
        for thread in threads:
            thread.join(max(0, pipe_deadline - time.monotonic()))
        for stream, thread in zip((process.stdout, process.stderr), threads, strict=True):
            if thread.is_alive():
                # BufferedReader.close() takes the reader's lock and can block
                # forever when a descendant retains the write end. The daemon
                # owns this stream until EOF; report unknown cleanup explicitly.
                clean = False
            else:
                stream.close()
    if exceeded.is_set() and stop is None:
        stop = "output_limit"
    if not clean and stop is None:
        stop = "cleanup_failure"
    with lock:
        return ProcessResult(
            bytes(stdout),
            bytes(stderr),
            process.returncode if process.returncode is not None else -1,
            stop,
            time.monotonic() - started,
            clean,
            process.pid,
        )


class ExecutionLimit(RuntimeError):
    """A fixed, credential-free reason for refusing verifier execution."""

    def __init__(self, kind: str):
        if kind not in {"storage_limit", "output_limit", "monitor_failure"}:
            kind = "monitor_failure"
        self.kind = kind
        super().__init__(f"verifier execution stopped: {kind}")


def _api_call(action: Callable[[], Any], timeout: float) -> Any:
    done = threading.Event()
    result: list[Any] = []

    def invoke() -> None:
        try:
            result.append(action())
        except Exception:
            pass
        finally:
            done.set()

    threading.Thread(target=invoke, daemon=True).start()
    if not done.wait(max(0, timeout)) or not result:
        raise ExecutionLimit("monitor_failure") from None
    return result[0]


def _kill(container: Any) -> None:
    _api_call(container.kill, _MONITOR_TIMEOUT)


def _storage(container: Any, timeout: float = _MONITOR_TIMEOUT) -> None:
    try:
        identity = container.id
        if not isinstance(identity, str) or re.fullmatch(r"[0-9a-f]{64}", identity) is None:
            raise ExecutionLimit("monitor_failure")
        rows = _api_call(
            lambda: container.client.api.containers(all=True, filters={"id": identity}, size=True),
            min(timeout, _MONITOR_TIMEOUT),
        )
        if (
            not isinstance(rows, list)
            or len(rows) != 1
            or not isinstance(rows[0], Mapping)
            or rows[0].get("Id") != identity
        ):
            raise ExecutionLimit("monitor_failure")
        size = rows[0].get("SizeRw")
        if type(size) is not int or size < 0:
            raise ExecutionLimit("monitor_failure")
        if size > STORAGE_LIMIT:
            raise ExecutionLimit("storage_limit")
    except Exception as error:
        _kill(container)
        raise ExecutionLimit(error.kind if isinstance(error, ExecutionLimit) else "monitor_failure") from None


@dataclass(frozen=True)
class _Outcome:
    output: bytes
    exit_code: int | None
    timed_out: bool
    seconds: float


def _execute(container: Any, cmd: Any, timeout: float | None, kwargs: Mapping[str, Any]) -> _Outcome:
    started = time.monotonic()
    if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
        _kill(container)
        return _Outcome(b"", None, True, time.monotonic() - started)
    try:
        _storage(container, min(_MONITOR_TIMEOUT, timeout) if timeout is not None else _MONITOR_TIMEOUT)
    except KeyboardInterrupt:
        with contextlib.suppress(ExecutionLimit):
            _kill(container)
        raise
    output = bytearray()
    done = threading.Event()
    lock = threading.Lock()
    failure: list[str] = []
    exit_codes: list[int] = []
    options = dict(kwargs)
    # The public wrapper owns capture and the deadline; an SDK socket would
    # bypass both. Detached control calls are handled by the wrapper separately.
    if options.pop("socket", False) or options.pop("demux", False):
        _kill(container)
        raise ExecutionLimit("monitor_failure")
    options.pop("stream", None)
    options.pop("detach", None)
    tty = bool(options.pop("tty", False))
    options.setdefault("stdout", True)
    options.setdefault("stderr", True)

    def collect() -> None:
        try:
            api = container.client.api
            created = api.exec_create(container.id, cmd, tty=tty, **options)
            exec_id = created["Id"]
            for chunk in api.exec_start(exec_id, stream=True, tty=tty):
                if not isinstance(chunk, bytes):
                    raise ExecutionLimit("monitor_failure")
                with lock:
                    available = max(0, _STDOUT_LIMIT - len(output))
                    output.extend(chunk[:available])
                if len(chunk) > available:
                    raise ExecutionLimit("output_limit")
            state = api.exec_inspect(exec_id)
            code = state.get("ExitCode")
            if state.get("Running") is not False or type(code) is not int:
                raise ExecutionLimit("monitor_failure")
            exit_codes.append(code)
        except Exception as error:
            failure.append(error.kind if isinstance(error, ExecutionLimit) else "monitor_failure")
        finally:
            done.set()

    worker = threading.Thread(target=collect, daemon=True)
    worker.start()
    next_storage = started + _STORAGE_INTERVAL
    timed_out = False
    try:
        while not done.wait(0.01):
            now = time.monotonic()
            if timeout is not None and now - started >= timeout:
                timed_out = True
                _kill(container)
                break
            if now >= next_storage:
                _storage(
                    container,
                    min(_MONITOR_TIMEOUT, timeout - (now - started)) if timeout is not None else _MONITOR_TIMEOUT,
                )
                next_storage = now + _STORAGE_INTERVAL
        if failure:
            _kill(container)
            raise ExecutionLimit(failure[0])
        if not timed_out:
            elapsed = time.monotonic() - started
            if timeout is not None and elapsed >= timeout:
                timed_out = True
                _kill(container)
            else:
                _storage(
                    container, min(_MONITOR_TIMEOUT, timeout - elapsed) if timeout is not None else _MONITOR_TIMEOUT
                )
    except KeyboardInterrupt:
        with contextlib.suppress(ExecutionLimit):
            _kill(container)
        raise
    finally:
        worker.join(0.2)
    with lock:
        return _Outcome(bytes(output), exit_codes[0] if exit_codes else None, timed_out, time.monotonic() - started)


def bounded_exec(container: Any, cmd: Any, timeout: int | float | None = 60, **kwargs: Any) -> tuple[str, bool, float]:
    """Pinned harness exec_run_with_timeout shape, with bounded capture and storage."""
    result = _execute(container, cmd, timeout, kwargs)
    return result.output.decode("utf-8", errors="replace"), result.timed_out, result.seconds


@dataclass(frozen=True)
class _ExecResult:
    exit_code: int | None
    output: bytes | Iterator[bytes]


class BoundedContainer:
    """Delegate the SDK surface while bounding ordinary exec_run collection."""

    def __init__(self, raw: Any, *, storage_quota: bool = False):
        self._raw = raw
        self.storage_quota = storage_quota

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw, name)

    def exec_run(self, cmd: Any, **kwargs: Any) -> Any:
        if kwargs.get("detach") is True:
            return self._raw.exec_run(cmd, **kwargs)
        options = dict(kwargs)
        timeout = options.pop("timeout", _EXEC_TIMEOUT)
        result = _execute(self._raw, cmd, timeout, options)
        if result.timed_out:
            raise ExecutionLimit("monitor_failure")
        output: bytes | Iterator[bytes] = result.output
        if kwargs.get("stream") is True:
            output = iter((result.output,))
        return _ExecResult(result.exit_code, output)
