"""No-model proof of the Go incidents oracle: a solution built on backend-craft's Go starter passes
every check, and a plausible solution without the skill fails the checks the skill exists for."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "evals/build-scenarios/build-software-engineer-go-incidents-api.yaml"
ORACLE = ROOT / "evals/oracles/go-incidents-api/probe_checks.py"
PROTOCOL = ROOT / "evals/oracles/oracle_protocol.py"
SOLUTIONS = ROOT / "evals/fixtures/go-incidents-api"
HOUSE = ROOT / "skills/backend-craft/assets/go/house.go"
HUMA = "github.com/danielgtaylor/huma/v2@v2.39.1"
ORACLE_CHECKS = ("auth", "pagination", "filter", "problem_json", "router_problems", "no_leak",
                 "document", "drift_gate", "server_timeouts")


def go() -> str:
    found = shutil.which("go")
    assert found, "go must be available to prove the Go incidents oracle"
    return found


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=900)
    assert result.returncode == 0, f"{command}\n{result.stdout[-3000:]}\n{result.stderr[-3000:]}"
    return result


def workspace(tmp_path: Path, solution: str) -> Path:
    for name, text in scenario_file(SCENARIO)["fixture"]["files"].items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    shutil.copytree(SOLUTIONS / solution, tmp_path, dirs_exist_ok=True)
    if solution == "good":
        shutil.copy(HOUSE, tmp_path / "house.go")
        run([go(), "get", HUMA], tmp_path)
    run([go(), "mod", "tidy"], tmp_path)
    if solution == "good":
        run([go(), "test", "-count=1", "-run", "TestOpenAPIDocument", ".", "-update"], tmp_path)
    shutil.copy(ORACLE, tmp_path / "probe_checks.py")
    shutil.copy(PROTOCOL, tmp_path / "oracle_protocol.py")
    return tmp_path


def verdicts(path: Path) -> dict[str, int]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    codes = {}
    for check in ORACLE_CHECKS:
        result = subprocess.run([sys.executable, "oracle_protocol.py", "probe_checks.py", check], cwd=path,
                                capture_output=True, text=True, timeout=900, env=env)
        codes[check] = result.returncode
        assert result.returncode in (0, 10), f"{check}: measurement unavailable\n{result.stdout}\n{result.stderr}"
    return codes


@pytest.fixture(scope="module")
def good(tmp_path_factory):
    return verdicts(workspace(tmp_path_factory.mktemp("good"), "good"))


@pytest.fixture(scope="module")
def naive(tmp_path_factory):
    return verdicts(workspace(tmp_path_factory.mktemp("naive"), "naive"))


def test_the_starter_solution_passes_every_check(good):
    assert good == dict.fromkeys(ORACLE_CHECKS, 0)


def test_a_solution_without_the_skill_fails_the_contract_checks(naive):
    assert naive == dict.fromkeys(ORACLE_CHECKS, 10)


def test_the_oracle_is_the_scenario_oracle():
    checks = scenario_file(SCENARIO)["checks"]
    graded = [c["command"].split()[-1] for c in checks if "probe_checks.py" in c.get("command", "")]
    assert graded == list(ORACLE_CHECKS)
    assert checks[0]["writes_from"]["probe_checks.py"] == "evals/oracles/go-incidents-api/probe_checks.py"
