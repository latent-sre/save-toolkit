"""Grading commands own their ordinary process tree, including on timeout."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

import pytest
from probe import checking, invocation, workspaces
from probe_testkit import tiny_spec, ws_context


def test_grading_timeout_stops_descendants_before_returning(tmp_path: Path) -> None:
    spec = tiny_spec()
    ws = workspaces.seed_workspace(spec, tmp_path)
    ctx = ws_context(spec, ws)
    release, ready, marker = (ws.repo / name for name in ("release", "ready", "escaped"))
    (ws.repo / "descendant.py").write_text(
        "import time\nfrom pathlib import Path\n"
        "Path('ready').touch()\ndeadline = time.monotonic() + 10\n"
        "while not Path('release').exists() and time.monotonic() < deadline: time.sleep(0.01)\n"
        "if Path('release').exists(): Path('escaped').touch()\n", encoding="utf-8")
    (ws.repo / "parent.py").write_text(
        "import subprocess, sys\nsubprocess.run([sys.executable, 'descendant.py'], check=True)\n",
        encoding="utf-8")
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
        "import sys\nsys.stdout.buffer.write(b'answer\\xff\\r\\n')\n"
        "sys.stderr.write('diagnostic\\n')\nsys.exit(7)\n", encoding="utf-8")
    result = checking._run(ctx, "python output.py", timeout=10)
    assert result.returncode == 7
    assert result.stdout == "answer\ufffd\n"
    assert result.stderr == "diagnostic\n"
    shell = checking._run(ctx, 'echo first && echo second', timeout=10)
    assert shell.returncode == 0
    assert shell.stdout.splitlines() == ["first", "second"]


def test_grading_waits_for_output_inherited_by_a_child(tmp_path: Path) -> None:
    spec = tiny_spec()
    ws = workspaces.seed_workspace(spec, tmp_path)
    ctx = ws_context(spec, ws)
    (ws.repo / "parent.py").write_text(
        "import subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', "
        "\"import time; time.sleep(0.05); print('x' * 100000)\"])\n", encoding="utf-8")
    result = checking._run(ctx, "python parent.py", timeout=10)
    assert result.returncode == 0
    assert result.stdout == "x" * 100000 + "\n"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process-group cleanup")
def test_grading_cleanup_failure_is_not_an_ordinary_timeout(tmp_path: Path) -> None:
    spec = tiny_spec()
    ctx = ws_context(spec, workspaces.seed_workspace(spec, tmp_path))
    with mock.patch.object(subprocess, "Popen") as launch, \
            mock.patch.object(invocation, "_stop_cli", side_effect=OSError("cleanup unavailable")):
        process = launch.return_value
        process.__enter__.return_value = process
        process.wait.side_effect = subprocess.TimeoutExpired("stub", 1)
        process.communicate.side_effect = subprocess.TimeoutExpired("stub", 1)
        with pytest.raises(RuntimeError, match="process-tree cleanup failed"):
            checking.check_command_exit_zero(ctx, {"command": "stub", "timeout": 1})
