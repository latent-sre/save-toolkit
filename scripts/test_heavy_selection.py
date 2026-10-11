"""The root conftest's split between the default run and the heavy eval-machinery tests."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFTEST = ROOT / "conftest.py"


def heavy_files() -> list[str]:
    return re.findall(r'"(evals/test_[a-z0-9_]+\.py)"', CONFTEST.read_text(encoding="utf-8"))


def collect(*args: str) -> list[str]:
    """Node ids a fresh pytest collects, without the caller's own parallel or marker options."""
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "-p", "no:xdist", *args],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=300,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    return [line for line in result.stdout.splitlines() if "::" in line]


def file_of(node: str) -> str:
    return node.split("::", 1)[0].replace("\\", "/")


def test_every_heavy_entry_names_an_existing_test_file() -> None:
    files = heavy_files()
    assert len(files) == len(set(files)) >= 1
    assert [f for f in files if not (ROOT / f).is_file()] == []


def test_a_plain_run_skips_the_heavy_files_and_keeps_the_rest() -> None:
    nodes = collect("evals")
    assert nodes, "the default run collected nothing"
    assert {file_of(n) for n in nodes} & set(heavy_files()) == set()


@pytest.mark.parametrize("option", [["--heavy", "-m", "heavy"], ["-m", "heavy"]])
def test_the_heavy_selection_runs_only_the_heavy_files(option: list[str]) -> None:
    files = {file_of(n) for n in collect(*option, "evals")}
    assert files == set(heavy_files())


def test_a_named_heavy_file_runs_without_the_option() -> None:
    target = sorted(heavy_files())[0]
    files = {file_of(n) for n in collect(target)}
    assert files == {target}
