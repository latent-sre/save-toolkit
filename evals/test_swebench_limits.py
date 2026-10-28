"""Execution bounds with small real children and in-memory Docker API fakes."""

import ctypes
import importlib
import io
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

CONTAINER_ID = "a" * 64


def limits():
    return importlib.import_module("swebench_adapter.limits")


def test_process_captures_separate_small_outputs_and_exit_code(tmp_path):
    result = limits().run_bounded(
        [
            sys.executable,
            "-c",
            "import sys;sys.stdout.buffer.write(b'out\\n');sys.stderr.buffer.write(b'err\\n');sys.exit(7)",
        ],
        cwd=tmp_path,
        env=os.environ,
        timeout=3,
    )
    assert (result.stdout, result.stderr, result.returncode, result.stop) == (b"out\n", b"err\n", 7, None)
    assert 0 <= result.seconds < 3
    assert isinstance(result.pid, int) and result.pid > 0


@pytest.mark.parametrize("channel", ["stdout", "stderr"])
def test_process_output_limit_is_enforced_with_small_real_child(tmp_path, monkeypatch, channel):
    module = limits()
    monkeypatch.setattr(module, "_STDOUT_LIMIT", 16)
    monkeypatch.setattr(module, "_STDERR_LIMIT", 8)
    result = module.run_bounded(
        [sys.executable, "-c", f"import sys;sys.{channel}.write('x'*100);sys.{channel}.flush()"],
        cwd=tmp_path,
        env=os.environ,
        timeout=3,
    )
    assert result.stop == "output_limit"
    assert len(result.stdout) <= 16 and len(result.stderr) <= 8


def test_process_timeout_terminates_owned_child_tree(tmp_path):
    sentinel = tmp_path / "escaped"
    child = f"import time,pathlib;time.sleep(0.7);pathlib.Path({str(sentinel)!r}).write_text('alive')"
    parent = f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{child!r}]);time.sleep(10)"
    result = limits().run_bounded([sys.executable, "-c", parent], cwd=tmp_path, env=os.environ, timeout=0.15)
    assert result.stop == "timeout"
    assert result.seconds < 3
    threading.Event().wait(0.8)
    assert not sentinel.exists()


def test_process_interruption_is_returned_instead_of_escaping(tmp_path):
    # Schedule KeyboardInterrupt inside an isolated driver. Windows os.kill(SIGINT)
    # terminates the process instead of invoking Python's signal handler.
    source = Path(__file__).parent
    driver = (
        "import os,_thread,threading,sys,json;from pathlib import Path;"
        f"sys.path.insert(0,{str(source)!r});from swebench_adapter.limits import run_bounded;"
        "threading.Timer(.15,_thread.interrupt_main).start();"
        "r=run_bounded([sys.executable,'-c','import time;time.sleep(10)'],cwd=Path.cwd(),env=os.environ,timeout=3);"
        "print(json.dumps({'stop':r.stop,'seconds':r.seconds}))"
    )
    result = subprocess.run([sys.executable, "-c", driver], cwd=tmp_path, capture_output=True, timeout=5, check=True)
    measured = json.loads(result.stdout)
    assert measured["stop"] == "interrupted"
    assert measured["seconds"] < 3


def test_spawn_failure_returns_fixed_state_without_error_text(tmp_path):
    result = limits().run_bounded([str(tmp_path / "missing-secret-value")], cwd=tmp_path, env=os.environ, timeout=1)
    assert result.stop == "spawn_failure"
    assert result.stdout == result.stderr == b""


class DockerAPI:
    def __init__(self, chunks=(b"hello\n",), sizes=(0,), *, exit_code=0, blocked=False):
        self.chunks = chunks
        self.sizes = iter(sizes)
        self.last_size = 0
        self.exit_code = exit_code
        self.blocked = blocked
        self.killed = threading.Event()
        self.created = []
        self.inspections = 0

    def inspect_container(self, container):
        assert container == CONTAINER_ID
        return {"Id": CONTAINER_ID}

    def containers(
        self,
        quiet=False,
        all=False,
        trunc=False,
        latest=False,
        since=None,
        before=None,
        limit=-1,
        size=False,
        filters=None,
    ):
        assert all is True and size is True and filters == {"id": CONTAINER_ID}
        self.inspections += 1
        self.last_size = next(self.sizes, self.last_size)
        return [{"Id": CONTAINER_ID, "SizeRw": self.last_size}]

    def exec_create(self, container, cmd, **kwargs):
        self.created.append((container, cmd, kwargs))
        return {"Id": "owned-exec"}

    def exec_start(self, exec_id, **kwargs):
        assert exec_id == "owned-exec" and kwargs["stream"] is True
        yield from self.chunks
        if self.blocked:
            self.killed.wait(3)

    def exec_inspect(self, exec_id):
        assert exec_id == "owned-exec"
        return {"ExitCode": self.exit_code, "Running": False}


class Container:
    id = CONTAINER_ID

    def __init__(self, api):
        self.client = SimpleNamespace(api=api)
        self.detached = []

    def kill(self):
        self.client.api.killed.set()

    def exec_run(self, cmd, **kwargs):
        self.detached.append((cmd, kwargs))
        return SimpleNamespace(exit_code=None, output=b"")


def test_bounded_docker_exec_preserves_text_timeout_shape_and_kwargs():
    api = DockerAPI((b"one", b"two"), sizes=(1, 2))
    output, timed_out, seconds = limits().bounded_exec(
        Container(api), ["test"], 2, workdir="/testbed", user="1000", environment={"SAFE": "value"}
    )
    assert (output, timed_out) == ("onetwo", False)
    assert 0 <= seconds < 2
    assert api.inspections >= 2
    assert api.created[0][2]["workdir"] == "/testbed"
    assert api.created[0][2]["user"] == "1000"
    assert api.created[0][2]["environment"] == {"SAFE": "value"}
    assert not api.killed.is_set()


def test_bounded_docker_output_overflow_kills_container(monkeypatch):
    module = limits()
    monkeypatch.setattr(module, "_STDOUT_LIMIT", 16)
    api = DockerAPI((b"x" * 10, b"y" * 10))
    with pytest.raises(module.ExecutionLimit) as error:
        module.bounded_exec(Container(api), "test")
    assert error.value.kind == "output_limit"
    assert api.killed.is_set()


@pytest.mark.parametrize(
    "sizes,kind",
    [
        ((10_737_418_241,), "storage_limit"),
        ((None,), "monitor_failure"),
        ((True,), "monitor_failure"),
        ((-1,), "monitor_failure"),
        ((0, 10_737_418_241), "storage_limit"),
    ],
)
def test_container_storage_is_checked_before_and_after_exec(sizes, kind):
    module = limits()
    api = DockerAPI(sizes=sizes)
    with pytest.raises(module.ExecutionLimit) as error:
        module.bounded_exec(Container(api), "test")
    assert error.value.kind == kind
    assert api.killed.is_set()


def test_container_watchdog_checks_storage_during_blocked_output(monkeypatch):
    module = limits()
    monkeypatch.setattr(module, "_STORAGE_INTERVAL", 0.02)
    api = DockerAPI(sizes=(0, 10_737_418_241), blocked=True)
    with pytest.raises(module.ExecutionLimit) as error:
        module.bounded_exec(Container(api), "test", 2)
    assert error.value.kind == "storage_limit"
    assert api.killed.is_set()


def test_docker_exec_timeout_kills_container_and_returns_timed_out():
    api = DockerAPI((b"partial",), blocked=True)
    output, timed_out, seconds = limits().bounded_exec(Container(api), "test", 0.1)
    assert output == "partial"
    assert timed_out is True
    assert seconds < 2
    assert api.killed.is_set()


def test_container_wrapper_bounds_nonstream_calls_and_preserves_raw_bytes():
    api = DockerAPI((b"\xffdiff\n",), exit_code=7)
    raw = Container(api)
    wrapped = limits().BoundedContainer(raw, storage_quota=False)
    assert wrapped.id == CONTAINER_ID
    result = wrapped.exec_run("git diff", workdir="/testbed", user="1000", environment={"X": "1"})
    assert result.exit_code == 7
    assert result.output == b"\xffdiff\n"
    assert api.inspections >= 2
    detached = wrapped.exec_run("kill -9 123", detach=True)
    assert detached.exit_code is None and detached.output == b""
    assert raw.detached == [("kill -9 123", {"detach": True})]


def test_wrapper_nonstream_calls_have_a_deadline(monkeypatch):
    module = limits()
    monkeypatch.setattr(module, "_EXEC_TIMEOUT", 0.05)
    api = DockerAPI(blocked=True)
    with pytest.raises(module.ExecutionLimit) as error:
        module.BoundedContainer(Container(api)).exec_run("sleep 100")
    assert error.value.kind == "monitor_failure"
    assert api.killed.is_set()


def test_stalled_storage_monitor_is_bounded_and_kills_container(monkeypatch):
    module = limits()
    monkeypatch.setattr(module, "_MONITOR_TIMEOUT", 0.05, raising=False)
    release = threading.Event()
    api = DockerAPI()

    def stalled(*_args, **_kwargs):
        release.wait(2)
        return [{"Id": CONTAINER_ID, "SizeRw": 0}]

    api.containers = stalled
    started = time.monotonic()
    try:
        with pytest.raises(module.ExecutionLimit) as error:
            module.bounded_exec(Container(api), "test", 0.1)
        assert error.value.kind == "monitor_failure"
        assert api.killed.is_set()
        assert time.monotonic() - started < 1
    finally:
        release.set()


@pytest.mark.parametrize("during_execution", [False, True])
def test_docker_interrupt_kills_owned_container_and_reaches_caller(monkeypatch, during_execution):
    module = limits()
    api = DockerAPI(blocked=True)
    calls = 0

    def interrupt(_container, _timeout):
        nonlocal calls
        calls += 1
        if not during_execution or calls > 1:
            raise KeyboardInterrupt

    monkeypatch.setattr(module, "_storage", interrupt)
    monkeypatch.setattr(module, "_STORAGE_INTERVAL", 0)
    with pytest.raises(KeyboardInterrupt):
        module.bounded_exec(Container(api), "test", 1)
    assert api.killed.is_set()


def test_exact_output_and_storage_bounds_are_allowed(monkeypatch):
    module = limits()
    monkeypatch.setattr(module, "_STDOUT_LIMIT", 16)
    api = DockerAPI((b"x" * 16,), sizes=(10_737_418_240,))
    assert module.bounded_exec(Container(api), "test")[0] == "x" * 16
    assert not api.killed.is_set()


def test_docker_api_failures_are_sanitized_and_kill_owned_container(capsys):
    module = limits()
    api = DockerAPI()

    def fail(*_args, **_kwargs):
        raise RuntimeError("synthetic-secret-never-log")

    api.exec_create = fail
    with pytest.raises(module.ExecutionLimit) as error:
        module.bounded_exec(Container(api), "test")
    assert error.value.kind == "monitor_failure"
    assert "synthetic-secret-never-log" not in str(error.value)
    captured = capsys.readouterr()
    assert "synthetic-secret-never-log" not in captured.out + captured.err
    assert api.killed.is_set()


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [{"Id": "b" * 64, "SizeRw": 0}],
        [{"Id": CONTAINER_ID[:12], "SizeRw": 0}],
        [{"Id": CONTAINER_ID, "SizeRw": 0}] * 2,
        [{"SizeRw": 0}],
        [{"Id": CONTAINER_ID}],
        None,
    ],
)
def test_storage_requires_one_exact_full_id_row(rows):
    module = limits()
    api = DockerAPI()
    api.containers = lambda **_kwargs: rows
    with pytest.raises(module.ExecutionLimit) as error:
        module.bounded_exec(Container(api), "test")
    assert error.value.kind == "monitor_failure"
    assert api.killed.is_set()


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group regression")
def test_exited_parent_cannot_leave_descendant_holding_pipes(tmp_path):
    sentinel = tmp_path / "descendant-survived"
    child = f"import time,pathlib;time.sleep(.7);pathlib.Path({str(sentinel)!r}).write_text('alive')"
    parent = f"import subprocess,sys;subprocess.Popen([sys.executable,'-c',{child!r}])"
    result = limits().run_bounded([sys.executable, "-c", parent], cwd=tmp_path, env=os.environ, timeout=0.15)
    assert result.returncode == 0 and result.stop == "timeout"
    assert result.cleanup_complete is True
    threading.Event().wait(0.8)
    assert not sentinel.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX disposable child cleanup")
def test_alive_reader_never_blocks_pipe_close_or_claims_clean_cleanup(tmp_path, monkeypatch):
    module = limits()
    real_popen = module.subprocess.Popen
    children = []

    def launch(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        children.append(process)
        return process

    monkeypatch.setattr(module.subprocess, "Popen", launch)
    monkeypatch.setattr(module, "_terminate", lambda *_args: False)
    monkeypatch.setattr(module, "_PIPE_TIMEOUT", 0.05, raising=False)
    try:
        result = module.run_bounded(
            [sys.executable, "-c", "import time;time.sleep(2)"], cwd=tmp_path, env=os.environ, timeout=0.05
        )
        assert result.seconds < 0.5
        assert result.cleanup_complete is False
        assert result.stop == "timeout"
    finally:
        for child in children:
            os.killpg(child.pid, 9)
            child.wait(timeout=2)


class FakeWinCall:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


class FakeWinKernel:
    def __init__(self, windows, *, failure=None):
        self.events = []
        self.failure = failure
        self.windows = windows
        for name in (
            "CreateJobObjectW",
            "SetInformationJobObject",
            "OpenProcess",
            "AssignProcessToJobObject",
            "CreateToolhelp32Snapshot",
            "Thread32First",
            "Thread32Next",
            "OpenThread",
            "ResumeThread",
            "TerminateJobObject",
            "CloseHandle",
            "GetLastError",
        ):
            setattr(self, name, FakeWinCall(lambda *args, _name=name: self.call(_name, *args)))

    def call(self, name, *args):
        self.events.append((name, args))
        if name == self.failure:
            return 0xFFFFFFFF if name == "ResumeThread" else 0
        if name == "CreateJobObjectW":
            assert args == (None, None), "job handle must be private and noninheritable"
            return 101
        if name == "SetInformationJobObject":
            info = ctypes.cast(args[2], ctypes.POINTER(self.windows._ExtendedLimits)).contents
            assert args[1] == 9
            assert info.BasicLimitInformation.LimitFlags == 0x2000
            return 1
        if name == "OpenProcess":
            assert args == (0x101, False, 42)
            return 102
        if name == "CreateToolhelp32Snapshot":
            assert args == (4, 0)
            return 103
        if name == "Thread32First":
            entry = ctypes.cast(args[1], ctypes.POINTER(self.windows._ThreadEntry)).contents
            assert entry.dwSize == ctypes.sizeof(self.windows._ThreadEntry)
            entry.th32OwnerProcessID = 42
            entry.th32ThreadID = 43
            return 1
        if name == "Thread32Next":
            return 0
        if name == "GetLastError":
            return 18
        if name == "OpenThread":
            assert args == (2, False, 43)
            return 104
        if name == "ResumeThread":
            return 1
        return 1


def fake_windows_process(kernel):
    kernel.events.append(("Popen", ()))
    return SimpleNamespace(
        pid=42,
        stdout=io.BytesIO(b"out"),
        stderr=io.BytesIO(),
        returncode=0,
        poll=lambda: 0,
        wait=lambda **_kwargs: 0,
        kill=lambda: kernel.events.append(("kill_root", ())),
    )


def test_windows_job_assigns_suspended_child_before_resume_and_owns_after_parent_exit(tmp_path, monkeypatch):
    module = limits()
    windows = importlib.import_module("swebench_adapter.windows_job")
    kernel = FakeWinKernel(windows)
    monkeypatch.setattr(module, "_WINDOWS", True)
    monkeypatch.setattr(module, "WindowsJob", lambda: windows.WindowsJob(kernel=kernel))

    def spawn(*_args, **kwargs):
        assert kwargs["creationflags"] & 4
        return fake_windows_process(kernel)

    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    result = module.run_bounded(["synthetic.exe"], cwd=tmp_path, env={}, timeout=1)
    events = [name for name, _args in kernel.events]
    assert events.index("SetInformationJobObject") < events.index("Popen")
    assert events.index("Popen") < events.index("AssignProcessToJobObject") < events.index("ResumeThread")
    assert events.index("ResumeThread") < events.index("TerminateJobObject")
    assert ("CloseHandle", (101,)) in kernel.events
    assert {args[0] for name, args in kernel.events if name == "CloseHandle"} == {101, 102, 103, 104}
    assert result.stdout == b"out" and result.stop is None and result.cleanup_complete
    assert result.pid == 42


@pytest.mark.parametrize(
    "failure",
    [
        "SetInformationJobObject",
        "OpenProcess",
        "AssignProcessToJobObject",
        "CreateToolhelp32Snapshot",
        "Thread32First",
        "OpenThread",
        "ResumeThread",
    ],
)
def test_windows_job_failure_never_runs_unowned_child(tmp_path, monkeypatch, failure):
    module = limits()
    windows = importlib.import_module("swebench_adapter.windows_job")
    kernel = FakeWinKernel(windows, failure=failure)
    monkeypatch.setattr(module, "_WINDOWS", True)
    monkeypatch.setattr(module, "WindowsJob", lambda: windows.WindowsJob(kernel=kernel))
    monkeypatch.setattr(module.subprocess, "Popen", lambda *_args, **_kwargs: fake_windows_process(kernel))
    result = module.run_bounded(["synthetic.exe"], cwd=tmp_path, env={}, timeout=1)
    assert result.stop == "ownership_failure"
    events = [name for name, _args in kernel.events]
    if failure == "SetInformationJobObject":
        assert "Popen" not in events
    if failure == "AssignProcessToJobObject":
        assert "ResumeThread" not in events
    assert ("CloseHandle", (101,)) in kernel.events


def test_windows_job_failed_termination_cannot_claim_clean_cleanup(tmp_path, monkeypatch):
    module = limits()
    windows = importlib.import_module("swebench_adapter.windows_job")
    kernel = FakeWinKernel(windows, failure="TerminateJobObject")
    monkeypatch.setattr(module, "_WINDOWS", True)
    monkeypatch.setattr(module, "WindowsJob", lambda: windows.WindowsJob(kernel=kernel))
    monkeypatch.setattr(module.subprocess, "Popen", lambda *_args, **_kwargs: fake_windows_process(kernel))
    result = module.run_bounded(["synthetic.exe"], cwd=tmp_path, env={}, timeout=1)
    assert result.stop == "cleanup_failure" and result.cleanup_complete is False
    assert ("CloseHandle", (101,)) in kernel.events


def test_windows_native_layout_uses_fixed_width_fields_and_pointer_sized_handles():
    windows = importlib.import_module("swebench_adapter.windows_job")
    assert ctypes.sizeof(windows._ThreadEntry) == 28
    assert ctypes.sizeof(windows._IOCounters) == 48
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        assert ctypes.sizeof(windows._BasicLimits) == 64
        assert ctypes.sizeof(windows._ExtendedLimits) == 144
    kernel = FakeWinKernel(windows)
    job = windows.WindowsJob(kernel=kernel)
    assert kernel.CreateJobObjectW.restype is ctypes.c_void_p
    assert kernel.OpenProcess.restype is ctypes.c_void_p
    assert kernel.OpenThread.restype is ctypes.c_void_p
    assert kernel.ResumeThread.restype is ctypes.c_uint32
    assert job.close()


@pytest.mark.parametrize("count", [0, 2, 0xFFFFFFFF])
def test_windows_resumption_requires_exactly_one_initial_suspend(count):
    windows = importlib.import_module("swebench_adapter.windows_job")
    kernel = FakeWinKernel(windows)
    kernel.ResumeThread = FakeWinCall(lambda *_args: count)
    job = windows.WindowsJob(kernel=kernel)
    try:
        with pytest.raises(windows.JobError):
            job.assign_and_resume(42)
    finally:
        assert job.close()


@pytest.mark.parametrize("during_assignment", [False, True])
def test_windows_startup_interrupt_preserves_stop_and_closes_job(tmp_path, monkeypatch, during_assignment):
    module = limits()
    windows = importlib.import_module("swebench_adapter.windows_job")
    kernel = FakeWinKernel(windows)
    monkeypatch.setattr(module, "_WINDOWS", True)
    monkeypatch.setattr(module, "WindowsJob", lambda: windows.WindowsJob(kernel=kernel))

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    if during_assignment:
        kernel.AssignProcessToJobObject = FakeWinCall(interrupt)
        monkeypatch.setattr(module.subprocess, "Popen", lambda *_args, **_kwargs: fake_windows_process(kernel))
    else:
        monkeypatch.setattr(module.subprocess, "Popen", interrupt)
    try:
        result = module.run_bounded(["synthetic.exe"], cwd=tmp_path, env={}, timeout=1)
    except KeyboardInterrupt:
        pytest.fail("startup interruption must return a bounded result and close the job")
    assert result.stop == "interrupted"
    if not during_assignment:
        assert result.cleanup_complete is False
    assert ("CloseHandle", (101,)) in kernel.events
