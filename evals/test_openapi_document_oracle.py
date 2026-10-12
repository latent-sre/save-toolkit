"""No-model proof of the FastAPI document oracle on each backend scenario's own fixture: the fixture
as shipped fails both checks, and the fixture plus a committed document and a drift test passes."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "evals/oracles/openapi-document/probe_checks.py"
PROTOCOL = ROOT / "evals/oracles/oracle_protocol.py"
SCENARIOS = ("incidents-api", "incident-writes", "pager-webhook")
CHECKS = ("document", "drift_gate")

DRIFT_TEST = '''\
import json
from pathlib import Path

from app.main import create_app


def test_document_matches_the_code():
    committed = json.loads((Path(__file__).parents[1] / "openapi.json").read_text(encoding="utf-8"))
    assert committed == create_app().openapi()
'''


def workspace(path: Path, scenario: str) -> Path:
    spec = scenario_file(ROOT / f"evals/build-scenarios/build-software-engineer-{scenario}.yaml")
    for name, text in spec["fixture"]["files"].items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    shutil.copy(ORACLE, path / "probe_checks.py")
    shutil.copy(PROTOCOL, path / "oracle_protocol.py")
    return path


def add_gate(path: Path) -> None:
    (path / "tests/test_openapi_document.py").write_text(DRIFT_TEST, encoding="utf-8", newline="\n")
    env = {**os.environ, "DB_PATH": str(path.parent / "gen.db"), "PYTHONDONTWRITEBYTECODE": "1"}
    code = "import json, sys; sys.path.insert(0, '.'); from app.main import create_app; print(json.dumps(create_app().openapi()))"
    result = subprocess.run([sys.executable, "-c", code], cwd=path, capture_output=True, text=True, env=env, timeout=120)
    assert result.returncode == 0, result.stderr
    (path / "openapi.json").write_text(json.dumps(json.loads(result.stdout), indent=2) + "\n", encoding="utf-8")


def verdict(path: Path, check: str) -> int:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "oracle_protocol.py", "probe_checks.py", check], cwd=path,
                            capture_output=True, text=True, timeout=900, env=env)
    assert result.returncode in (0, 10), f"{check}: measurement unavailable\n{result.stdout}\n{result.stderr}"
    return result.returncode


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_a_service_without_a_committed_document_fails(tmp_path, scenario):
    path = workspace(tmp_path / "ws", scenario)
    assert [verdict(path, check) for check in CHECKS] == [10, 10]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_a_committed_document_with_a_drift_test_passes(tmp_path, scenario):
    path = workspace(tmp_path / "ws", scenario)
    add_gate(path)
    assert [verdict(path, check) for check in CHECKS] == [0, 0]
    assert sorted(p.name for p in path.iterdir() if p.suffix == ".db") == []


def test_a_document_without_a_drift_test_fails_only_the_gate(tmp_path):
    path = workspace(tmp_path / "ws", "incidents-api")
    add_gate(path)
    (path / "tests/test_openapi_document.py").unlink()
    assert [verdict(path, check) for check in CHECKS] == [0, 10]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_each_scenario_grades_the_document(scenario):
    checks = scenario_file(ROOT / f"evals/build-scenarios/build-software-engineer-{scenario}.yaml")["checks"]
    commands = [c.get("command", "") for c in checks]
    for check in CHECKS:
        assert f"python oracle_protocol.py openapi_checks.py {check}" in commands
    assert any(c.get("writes_from", {}).get("openapi_checks.py") == "evals/oracles/openapi-document/probe_checks.py"
               for c in checks)
