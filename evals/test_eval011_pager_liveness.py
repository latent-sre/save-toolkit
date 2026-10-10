"""Pager candidate death during a real request is failure; unowned transport defects stay unknown."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_pager_webhook_oracle import materialize

PROTOCOL = Path(__file__).resolve().parent / "oracles/oracle_protocol.py"


def run_supervised(workspace: Path, source_suffix: str = "") -> subprocess.CompletedProcess[str]:
    (workspace / "oracle_protocol.py").write_bytes(PROTOCOL.read_bytes())
    if source_suffix:
        oracle = workspace / "probe_checks.py"
        source = oracle.read_text(encoding="utf-8")
        source = source.replace('if __name__ == "__main__":', source_suffix + '\nif __name__ == "__main__":')
        oracle.write_text(source, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-B", "oracle_protocol.py", "probe_checks.py", "accepted"],
        cwd=workspace, capture_output=True, text=True, encoding="utf-8", timeout=30,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


@pytest.mark.parametrize("code", [0, 7])
def test_candidate_process_death_during_webhook_is_failure(tmp_path: Path, code: int) -> None:
    workspace = materialize(tmp_path, {"ACCEPT": f"import os; os._exit({code})"})
    result = run_supervised(workspace)
    assert result.returncode == 10, result.stdout + result.stderr
    assert "app exited" in result.stdout
    assert "webhook" in result.stdout


def test_good_candidate_reference_still_passes(tmp_path: Path) -> None:
    result = run_supervised(materialize(tmp_path, {}))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "202 Accepted" in result.stdout


def test_oracle_transport_defect_with_live_child_stays_inconclusive(tmp_path: Path) -> None:
    # Real app startup and process liveness; only the oracle's HTTP transport is defective.
    fault = '''def broken_post(*args, **kwargs):
    assert _PROCS[-1].poll() is None
    raise httpx.ConnectError("injected oracle transport failure")
httpx.post = broken_post
'''
    result = run_supervised(materialize(tmp_path, {}), fault)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "injected oracle transport failure" in result.stderr
    assert "FAIL:" not in result.stdout
