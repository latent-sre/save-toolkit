"""Grading commands own their ordinary process tree, including on timeout."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

import pytest
from probe import checking, fingerprints, invocation, workspaces
from probe.checks import checkout
from probe_testkit import tiny_spec, ws_context
from swebench_adapter import windows_job


def _exiting_parent(tmp_path: Path, *, inherited_pipes: bool = False) -> tuple[Path, Path, Path, Path]:
    release, ready, marker = (tmp_path / name for name in ("release", "ready", "escaped"))
    descendant = tmp_path / "descendant.py"
    descendant.write_text(
        "import time\nfrom pathlib import Path\n"
        f"release, ready, marker = map(Path, {list(map(str, (release, ready, marker)))!r})\n"
        "ready.touch()\ndeadline = time.monotonic() + 6\n"
        "while not release.exists() and time.monotonic() < deadline: time.sleep(0.01)\n"
        "if release.exists(): marker.touch()\n", encoding="utf-8")
    parent = tmp_path / "parent.py"
    streams = "" if inherited_pipes else ", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL"
    parent.write_text(
        "import subprocess, sys, time\nfrom pathlib import Path\n"
        f"subprocess.Popen([sys.executable, {str(descendant)!r}]{streams})\n"
        f"ready = Path({str(ready)!r})\ndeadline = time.monotonic() + 5\n"
        "while not ready.exists() and time.monotonic() < deadline: time.sleep(0.01)\n"
        "assert ready.exists()\n", encoding="utf-8")
    return parent, release, ready, marker


def test_windows_ownership_helper_is_bound_to_runner_identity() -> None:
    helper = Path(windows_job.__file__).resolve()
    assert helper in fingerprints.HARNESS_FILES
    assert helper.parent / "__init__.py" in fingerprints.HARNESS_FILES


@pytest.mark.skipif(sys.platform != "win32", reason="Windows job ownership")
@pytest.mark.parametrize("kind", ["cli", "grading"])
def test_windows_completion_stops_descendants_after_root_exit(tmp_path: Path, kind: str) -> None:
    parent, release, ready, marker = _exiting_parent(tmp_path)
    command = [sys.executable, str(parent)]
    try:
        if kind == "cli":
            with (tmp_path / "stdout").open("w") as out, (tmp_path / "stderr").open("w") as err:
                status = invocation.run_cli(command, cwd=str(tmp_path), env=dict(os.environ), stdout=out, stderr=err, timeout=10)
        else:
            status = invocation.run_command(subprocess.list2cmdline(command), cwd=str(tmp_path), env=dict(os.environ), timeout=10).returncode
        assert status == 0
        assert ready.exists(), "the descendant must start before its parent exits"
    finally:
        release.touch()  # bounded survivor exits even on the failing implementation
    deadline = time.monotonic() + 0.5
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not marker.exists(), "a descendant continued after successful Windows completion"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows job ownership")
def test_windows_grading_timeout_owns_pipes_after_root_exit(tmp_path: Path) -> None:
    parent, release, ready, marker = _exiting_parent(tmp_path, inherited_pipes=True)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            invocation.run_command(subprocess.list2cmdline([sys.executable, str(parent)]), cwd=str(tmp_path), env=dict(os.environ), timeout=2)
        assert ready.exists(), "the pipe-holding descendant must start before the timeout"
    finally:
        release.touch()
    assert not marker.exists()


def test_grading_timeout_stops_descendants_before_returning(tmp_path: Path) -> None:
    spec = tiny_spec()
    ws = workspaces.seed_workspace(spec, tmp_path)
    ctx = ws_context(spec, ws)
    release, ready, marker = (ws.repo / name for name in ("release", "ready", "escaped"))
    (ws.repo / "descendant.py").write_text(
        "import time\nfrom pathlib import Path\n"
        "Path('ready').touch()\ndeadline = time.monotonic() + 10\n"
        "while not Path('release').exists() and time.monotonic() < deadline: time.sleep(0.01)\n"
        "if Path('release').exists(): Path('escaped').touch()\n",
        encoding="utf-8",
    )
    (ws.repo / "parent.py").write_text(
        "import subprocess, sys\nsubprocess.run([sys.executable, 'descendant.py'], check=True)\n", encoding="utf-8"
    )
    try:
        result = checking.check_command_exit_zero(ctx, {"command": "python parent.py", "timeout": 2})
        assert ready.exists(), "the descendant must start before the timeout"
        assert result.state == "FAIL"
        assert "timed out" in result.evidence
    finally:
        # Even the failing baseline releases its surviving process instead of leaking it.
        release.touch()
    deadline = time.monotonic() + 0.5
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not marker.exists(), "a grading child continued after its timeout was reported"


def test_grading_commands_preserve_shell_streams_and_exit_status(tmp_path: Path) -> None:
    spec = tiny_spec()
    ws = workspaces.seed_workspace(spec, tmp_path)
    ctx = ws_context(spec, ws)
    (ws.repo / "output.py").write_text(
        "import sys\nsys.stdout.buffer.write(b'answer\\xff\\r\\n')\nsys.stderr.write('diagnostic\\n')\nsys.exit(7)\n",
        encoding="utf-8",
    )
    result = checkout._run(ctx, "python output.py", timeout=10)
    assert result.returncode == 7
    assert result.stdout == "answer\ufffd\n"
    assert result.stderr == "diagnostic\n"
    shell = checkout._run(ctx, "echo first&& echo second", timeout=10)
    assert shell.returncode == 0
    assert shell.stdout.splitlines() == ["first", "second"]


def test_grading_waits_for_output_inherited_by_a_child(tmp_path: Path) -> None:
    spec = tiny_spec()
    ws = workspaces.seed_workspace(spec, tmp_path)
    ctx = ws_context(spec, ws)
    (ws.repo / "parent.py").write_text(
        "import subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', "
        "\"import time; time.sleep(0.05); print('x' * 100000)\"])\n",
        encoding="utf-8",
    )
    result = checkout._run(ctx, "python parent.py", timeout=10)
    assert result.returncode == 0
    assert result.stdout == "x" * 100000 + "\n"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process-group cleanup")
def test_grading_cleanup_failure_is_not_an_ordinary_timeout(tmp_path: Path) -> None:
    spec = tiny_spec()
    ctx = ws_context(spec, workspaces.seed_workspace(spec, tmp_path))
    with (
        mock.patch.object(subprocess, "Popen") as launch,
        mock.patch.object(invocation, "_stop_cli", side_effect=OSError("cleanup unavailable")),
    ):
        process = launch.return_value
        process.__enter__.return_value = process
        process.wait.side_effect = subprocess.TimeoutExpired("stub", 1)
        process.communicate.side_effect = subprocess.TimeoutExpired("stub", 1)
        with pytest.raises(RuntimeError, match="process-tree cleanup failed"):
            checking.check_command_exit_zero(ctx, {"command": "stub", "timeout": 1})
