"""Calibrate the Python project-baseline oracle and the dependency judgment grader offline.

Correct artifacts must pass and each named counterexample must fail as a contract failure (exit 10)
through the same supervised command the build scenarios run. These establish what the oracle
rejects; they do not establish live model behavior.
"""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from graders import exact_json
from probe_testkit import load_oracle, run_python, scenario, scenario_file, write_tree

ROOT = Path(__file__).resolve().parent
ORACLE = ROOT / "oracles/python-craft/check_project_baseline.py"
PROTOCOL = ROOT / "oracles/oracle_protocol.py"
NEW = scenario("build-python-new-project-baseline")
NARROW = scenario("build-python-narrow-fix-keeps-toolchain")
JUDGMENT = ROOT / "scenarios/python-dependency-judgment.yaml"

PYPROJECT = """\
[project]
name = "quota"
version = "0.1.0"
description = "Quota arithmetic"
requires-python = ">=3.14"
dependencies = []

[project.scripts]
quota-check = "quota.cli:main"

[dependency-groups]
dev = ["pytest>=9", "ruff>=0.16", "mypy>=1.18"]

[build-system]
requires = ["uv_build>=0.13,<0.14"]
build-backend = "uv_build"

[tool.mypy]
python_version = "3.14"
strict = true
"""
CI = """\
#!/usr/bin/env bash
set -euo pipefail
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src tests
uv run --locked pytest
"""
PACKAGE = '''\
"""Quota arithmetic."""


def remaining(limit: int, used: int) -> int:
    for value in (limit, used):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("limit and used must be integers")
    if not 0 <= used <= limit:
        raise ValueError("used must be between 0 and limit")
    return limit - used
'''
CLI = """\
import sys
from collections.abc import Sequence

from quota import remaining


def main(argv: Sequence[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else list(argv)
    if len(arguments) != 2:
        print("usage: quota-check LIMIT USED", file=sys.stderr)
        return 2
    try:
        limit, used = (int(value) for value in arguments)
        print(remaining(limit, used))
    except ValueError as exc:
        print(f"quota-check: {exc}", file=sys.stderr)
        return 2
    return 0
"""
TESTS = """\
from quota import remaining


def test_remaining() -> None:
    assert remaining(10, 3) == 7
"""
GOOD_NEW = {
    "pyproject.toml": PYPROJECT,
    "ci.sh": CI,
    "src/quota/__init__.py": PACKAGE,
    "src/quota/cli.py": CLI,
    "tests/test_quota.py": TESTS,
}
PYRIGHT_PROJECT = PYPROJECT.replace('"mypy>=1.18"', '"pyright>=1.1.400"').replace(
    '[tool.mypy]\npython_version = "3.14"\nstrict = true\n',
    '[tool.pyright]\npythonVersion = "3.14"\ntypeCheckingMode = "strict"\n',
)
TY_PROJECT = PYPROJECT.replace('"mypy>=1.18"', '"ty>=0.0.100"').replace(
    '[tool.mypy]\npython_version = "3.14"\nstrict = true\n', ""
)
SEED_NARROW = dict(NARROW["fixture"]["files"])
FIXED_WINDOWS = SEED_NARROW["windows.py"].replace("([1-9][0-9]*)([mhd])", "(0|[1-9][0-9]*)([mhd])")
GOOD_NARROW = SEED_NARROW | {"windows.py": FIXED_WINDOWS}


def run_oracle(root: Path, files: dict[str, str], mode: str) -> subprocess.CompletedProcess[str]:
    """Stage `files` and both oracle programs in `root`, then run the scenario's own command."""
    write_tree(root, files, newline="\n")
    (root / "_python_baseline_oracle.py").write_bytes(ORACLE.read_bytes())
    (root / "oracle_protocol.py").write_bytes(PROTOCOL.read_bytes())
    command = ["-B", "oracle_protocol.py", "_python_baseline_oracle.py", mode]
    return run_python(command, cwd=root, isolated=True, encoding="utf-8", timeout=60)


def assert_rejected(root: Path, files: dict[str, str], mode: str, diagnostic: str) -> None:
    result = run_oracle(root, files, mode)
    assert result.returncode == 10, result.stdout + result.stderr
    assert diagnostic in result.stderr, result.stderr


@pytest.mark.parametrize(
    "files",
    [
        GOOD_NEW,
        GOOD_NEW | {"pyproject.toml": PYRIGHT_PROJECT, "ci.sh": CI.replace("mypy src tests", "pyright")},
        GOOD_NEW | {"pyproject.toml": TY_PROJECT, "ci.sh": CI.replace("mypy src tests", "ty check")},
        GOOD_NEW | {"ci.sh": CI.replace("uv sync --locked", "uv sync --locked  # never --frozen")},
        GOOD_NEW | {"pyproject.toml": PYPROJECT.replace(">=3.14", ">=3.15")},
    ],
    ids=["mypy", "pyright", "ty", "comment-names-frozen", "higher-floor"],
)
def test_correct_new_project_passes(tmp_path: Path, files: dict[str, str]) -> None:
    result = run_oracle(tmp_path, files, "new")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "contract passed: new" in result.stdout


NEW_DEFECTS = [
    ("floor 3.12", {"pyproject.toml": PYPROJECT.replace(">=3.14", ">=3.12")}, "requires-python floor is below 3.14"),
    ("no floor", {"pyproject.toml": PYPROJECT.replace('requires-python = ">=3.14"\n', "")}, "declares no '>=3.N' floor"),
    (
        "no build backend",
        {"pyproject.toml": PYPROJECT.replace('[build-system]\nrequires = ["uv_build>=0.13,<0.14"]\nbuild-backend = "uv_build"\n', "")},
        "no build backend declared",
    ),
    ("no entry point", {"pyproject.toml": PYPROJECT.replace('quota-check = "quota.cli:main"', 'quota = "quota.cli:main"')}, "quota-check console script is not declared"),
    (
        "dev tool published",
        {"pyproject.toml": PYPROJECT.replace("dependencies = []", 'dependencies = ["pytest>=9"]')},
        "pytest is a development tool but is published",
    ),
    (
        "dev tools as an extra",
        {"pyproject.toml": PYPROJECT.replace("[dependency-groups]", "[project.optional-dependencies]")},
        "is a development tool but is published",
    ),
    ("no ruff", {"pyproject.toml": PYPROJECT.replace('"ruff>=0.16", ', "")}, "ruff is missing from [dependency-groups]"),
    ("two type checkers", {"pyproject.toml": PYPROJECT.replace('"mypy>=1.18"', '"mypy>=1.18", "pyright>=1.1"')}, "expected exactly one type checker"),
    ("no type checker", {"pyproject.toml": PYPROJECT.replace(', "mypy>=1.18"', "")}, "expected exactly one type checker"),
    ("mypy on a stale version", {"pyproject.toml": PYPROJECT.replace('python_version = "3.14"', 'python_version = "3.12"')}, "mypy python_version is not set to the floor"),
    ("mypy version unset", {"pyproject.toml": PYPROJECT.replace('python_version = "3.14"\n', "")}, "mypy python_version is not set to the floor"),
    ("mypy not strict", {"pyproject.toml": PYPROJECT.replace("strict = true\n", "")}, "mypy is not strict"),
    ("stale ruff target", {"pyproject.toml": PYPROJECT + '\n[tool.ruff]\ntarget-version = "py312"\n'}, "ruff target-version is below the floor"),
    ("poetry metadata", {"pyproject.toml": PYPROJECT + '\n[tool.poetry]\nname = "quota"\n'}, "standard [project] table"),
    ("requirements file", {"requirements.txt": "pytest\n"}, "requirements.txt duplicates"),
    ("setup.py", {"setup.py": "from setuptools import setup\nsetup()\n"}, "setup.py duplicates"),
    ("frozen sync", {"ci.sh": CI.replace("uv sync --locked", "uv sync --frozen")}, "ci.sh uses --frozen"),
    ("unlocked sync", {"ci.sh": CI.replace("uv sync --locked", "uv sync")}, "ci.sh command is not locked"),
    ("unlocked run", {"ci.sh": CI.replace("uv run --locked pytest", "uv run pytest")}, "ci.sh command is not locked"),
    ("no sync", {"ci.sh": CI.replace("uv sync --locked\n", "")}, "ci.sh never runs uv sync"),
    ("stale environment", {"ci.sh": CI.replace("uv run --locked pytest", "uv run --locked --no-sync pytest")}, "ci.sh uses --no-sync"),
    ("pip install", {"ci.sh": CI.replace("uv sync --locked", "uv sync --locked\npip install -e .")}, "ci.sh installs with pip"),
    ("bare pytest", {"ci.sh": CI.replace("uv run --locked pytest", "pytest")}, "ci.sh runs a check outside uv run"),
    ("no lint", {"ci.sh": CI.replace("uv run --locked ruff check .\n", "")}, "ci.sh does not run ruff check"),
    ("no tests in ci", {"ci.sh": CI.replace("uv run --locked pytest\n", "")}, "ci.sh does not run pytest"),
    ("no type check in ci", {"ci.sh": CI.replace("uv run --locked mypy src tests\n", "")}, "ci.sh does not run the type checker"),
    ("formatter rewrites", {"ci.sh": CI.replace("ruff format --check .", "ruff format .")}, "ci.sh does not check formatting"),
    ("no ci script", {"ci.sh": None}, "ci.sh is missing"),
    ("future annotations", {"src/quota/cli.py": "from __future__ import annotations\n" + CLI}, "imports annotations from __future__"),
    ("no tests", {"tests/test_quota.py": "VALUE = 1\n"}, "no test functions under tests/"),
    ("bool accepted", {"src/quota/__init__.py": PACKAGE.replace("isinstance(value, bool) or ", "")}, "remaining(True, 0) must raise ValueError"),
    ("overuse allowed", {"src/quota/__init__.py": PACKAGE.replace("0 <= used <= limit", "0 <= used")}, "remaining(5, 6) must raise ValueError"),
    ("untyped parameter", {"src/quota/__init__.py": PACKAGE.replace("limit: int, used: int", "limit, used: int")}, "remaining parameter limit is not annotated"),
    ("no return type", {"src/quota/cli.py": CLI.replace(" -> int:", ":")}, "main has no return annotation"),
    ("wrong output", {"src/quota/cli.py": CLI.replace("print(remaining(limit, used))", 'print("remaining:", remaining(limit, used))')}, "quota-check 10 3"),
    ("usage error exits", {"src/quota/cli.py": CLI.replace("        return 2\n    try:", "        raise SystemExit(2)\n    try:")}, "candidate exited before contract checks completed"),
    ("invalid toml", {"pyproject.toml": PYPROJECT + "[project\n"}, "pyproject.toml is not valid TOML"),
]


@pytest.mark.parametrize("name,change,diagnostic", NEW_DEFECTS, ids=[defect[0] for defect in NEW_DEFECTS])
def test_new_project_defects_are_contract_failures(tmp_path: Path, name: str, change: dict[str, str | None], diagnostic: str) -> None:
    files = {path: text for path, text in (GOOD_NEW | change).items() if text is not None}
    assert files != GOOD_NEW, name
    assert_rejected(tmp_path, files, "new", diagnostic)


def test_empty_new_project_seed_fails(tmp_path: Path) -> None:
    assert_rejected(tmp_path, dict(NEW["fixture"]["files"]), "new", "pyproject.toml is missing")


def test_narrow_seed_fails_and_the_minimal_fix_passes(tmp_path: Path) -> None:
    assert_rejected(tmp_path / "seed", SEED_NARROW, "narrow", "parse_window('0m')")
    result = run_oracle(tmp_path / "fixed", GOOD_NARROW, "narrow")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "contract passed: narrow" in result.stdout


NARROW_DEFECTS = [
    (
        "floor raised with the fix",
        {"pyproject.toml": SEED_NARROW["pyproject.toml"].replace('python = "^3.10"', 'python = "^3.14"')},
        "pyproject.toml changed although the fix did not need it",
    ),
    ("lock regenerated", {"poetry.lock": SEED_NARROW["poetry.lock"] + "# relocked\n"}, "poetry.lock changed although the fix did not need it"),
    ("lint config removed", {".flake8": None}, ".flake8 was removed although the fix did not need it"),
    ("migrated to uv", {"uv.lock": "version = 1\n"}, "uv.lock added: a narrow fix must not migrate the toolchain"),
    ("ruff adopted", {"ruff.toml": 'target-version = "py314"\n'}, "ruff.toml added"),
    (
        "newer syntax than the floor",
        {"windows.py": FIXED_WINDOWS.replace("_UNITS =", "type Unit = str\n_UNITS =")},
        "syntax the project's Python 3.10 floor lacks",
    ),
    ("leading zeros accepted", {"windows.py": SEED_NARROW["windows.py"].replace("[1-9][0-9]*", "[0-9]+")}, "parse_window('05m') must still raise ValueError"),
    ("only minutes fixed", {"windows.py": FIXED_WINDOWS.replace("(0|[1-9][0-9]*)([mhd])", "(0(?=m)|[1-9][0-9]*)([mhd])")}, "parse_window('0h')"),
    ("case folded", {"windows.py": FIXED_WINDOWS.replace("fullmatch(text)", "fullmatch(text.lower())")}, "parse_window('5M') must still raise ValueError"),
    ("zero returns none", {"windows.py": FIXED_WINDOWS.replace("    amount, unit = match.groups()\n", "    amount, unit = match.groups()\n    if amount == \"0\":\n        return None\n")}, "parse_window('0m')"),
]


@pytest.mark.parametrize("name,change,diagnostic", NARROW_DEFECTS, ids=[defect[0] for defect in NARROW_DEFECTS])
def test_narrow_fix_defects_are_contract_failures(tmp_path: Path, name: str, change: dict[str, str | None], diagnostic: str) -> None:
    files = {path: text for path, text in (GOOD_NARROW | change).items() if text is not None}
    assert files != GOOD_NARROW, name
    assert_rejected(tmp_path, files, "narrow", diagnostic)


@pytest.mark.parametrize("candidate", ["raise SystemExit(0)\n", "import os\nos._exit(0)\n"])
@pytest.mark.parametrize("mode,path,good", [("new", "src/quota/__init__.py", GOOD_NEW), ("narrow", "windows.py", GOOD_NARROW)])
def test_candidate_cannot_pass_by_exiting_early(tmp_path: Path, mode: str, path: str, good: dict[str, str], candidate: str) -> None:
    result = run_oracle(tmp_path, good | {path: candidate}, mode)
    assert result.returncode == 10, result.stdout + result.stderr
    assert "contract passed" not in result.stdout


def test_oracle_digests_match_the_narrow_fixture() -> None:
    oracle = load_oracle(ORACLE)
    expected = {name: hashlib.sha256(SEED_NARROW[name].encode("utf-8")).hexdigest() for name in oracle.NARROW_TOOLCHAIN}
    assert expected == oracle.NARROW_TOOLCHAIN


@pytest.mark.parametrize("spec,mode,allowed", [
    (NEW, "new", ["pyproject.toml", "ci.sh", "src/", "tests/", ".gitignore", ".python-version", "README.md"]),
    (NARROW, "narrow", ["windows.py", "tests/"]),
])
def test_build_checks_bind_the_oracle_and_the_change_scope(spec: dict[str, object], mode: str, allowed: list[str]) -> None:
    checks = spec["checks"]
    assert isinstance(checks, list)
    outcome = [check for check in checks if "writes_from" in check]
    assert len(outcome) == 1
    assert outcome[0]["command"] == "python -I -B oracle_protocol.py _python_baseline_oracle.py " + mode
    assert outcome[0]["failure_exit_code"] == 10
    assert outcome[0]["writes_from"] == {
        "_python_baseline_oracle.py": "evals/oracles/python-craft/check_project_baseline.py",
        "oracle_protocol.py": "evals/oracles/oracle_protocol.py",
    }
    assert [check["allowed"] for check in checks if check["check"] == "changes_within"] == [allowed]
    assert any(check["check"] == "skill_loaded" and check["skill"] == "python-craft" for check in checks)
    assert any(check["check"] == "no_new_commits" for check in checks)


def test_narrow_prompt_does_not_tell_the_agent_which_files_to_leave_alone() -> None:
    prompt = str(NARROW["prompt"])
    for hint in ("Only change", "pyproject", "poetry.lock", "flake8", "uv", "3.14", "migrat"):
        assert hint not in prompt, hint


def test_dependency_judgment_grader_rejects_each_wrong_or_missing_decision() -> None:
    expected = {
        "case_a": "fix_only_and_report_stale_dependencies",
        "case_b": "upgrade_lock_keep_published_minimum",
        "case_c": "raise_published_minimum_to_needed_release",
        "case_d": "upgrade_and_raise_application_bounds",
        "case_e": "remove_unexplained_cap_and_upgrade",
        "case_f": "readd_with_its_group_flag",
        "case_g": "add_current_release_and_check_advisories",
        "case_h": "verify_with_locked_not_frozen",
        "case_i": "upgrade_the_modules_dependencies_and_report_the_rest",
    }
    spec = scenario_file(JUDGMENT)
    fields = spec["graders"][0]["fields"]
    assert exact_json(json.dumps(expected), fields)[0]
    for key in expected:
        assert not exact_json(json.dumps(expected | {key: "incorrect"}), fields)[0], key
        assert not exact_json(json.dumps({k: v for k, v in expected.items() if k != key}), fields)[0], key
    offered = str(spec["prompt"])
    for choice in expected.values():
        assert choice in offered, choice
