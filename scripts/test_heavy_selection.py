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


def collect(root: Path, *args: str) -> set[str]:
    """Collect with pytest's own hooks, without inherited workers or unrelated plugins."""
    env = {k: v for k, v in os.environ.items() if k not in {"PYTEST_ADDOPTS", "PYTEST_PLUGINS"}}
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
         "-o", "addopts=", *args],
        cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=300,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    return {line.replace("\\", "/") for line in result.stdout.splitlines() if "::" in line}


def file_of(node: str) -> str:
    return node.split("::", 1)[0].replace("\\", "/")


def test_every_heavy_entry_collects_in_the_real_suite() -> None:
    files = heavy_files()
    assert len(files) == len(set(files)) >= 1
    assert [f for f in files if not (ROOT / f).is_file()] == []
    assert {file_of(n) for n in collect(ROOT, "-m", "heavy", "evals")} == set(files)


@pytest.fixture(scope="module")
def selection_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Copy the implementation unchanged; only the test payloads are smaller. A local config
    # prevents the outer repository's worker defaults or collection paths from leaking in.
    tmp_path = tmp_path_factory.mktemp("heavy-selection")
    (tmp_path / "conftest.py").write_bytes(CONFTEST.read_bytes())
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\ntestpaths = evals\nmarkers =\n"
        "    heavyweight: a different marker\n    not_heavy: another different marker\n",
        encoding="utf-8",
    )
    for relative in sorted(heavy_files())[:2]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("def test_first(): pass\ndef test_second(): pass\n", encoding="utf-8")
    (tmp_path / "evals/test_light.py").write_text(
        "import pytest\ndef test_plain(): pass\n"
        "@pytest.mark.heavyweight\ndef test_heavyweight(): pass\n"
        "@pytest.mark.not_heavy\ndef test_not_heavy(): pass\n", encoding="utf-8",
    )
    return tmp_path


@pytest.mark.parametrize("options,include_heavy,light_tests", [
    ([], False, ["plain", "heavyweight", "not_heavy"]),
    (["--heavy"], True, ["plain", "heavyweight", "not_heavy"]),
    (["-m", "heavy"], True, []),
    (["--heavy", "-m", "heavy"], True, []),
    (["-m", "not heavy"], False, ["plain", "heavyweight", "not_heavy"]),
    (["-m", "not heavyweight"], False, ["plain", "not_heavy"]),
    (["-m", "not not_heavy"], False, ["plain", "heavyweight"]),
    (["-m", "heavy or heavyweight"], True, ["heavyweight"]),
])
def test_selection_keeps_exactly_the_requested_tests(
    selection_repo: Path, options: list[str], include_heavy: bool, light_tests: list[str],
) -> None:
    expected = {f"evals/test_light.py::test_{name}" for name in light_tests}
    if include_heavy:
        expected.update(f"{path}::test_{name}" for path in sorted(heavy_files())[:2] for name in ("first", "second"))
    assert collect(selection_repo, *options) == expected


@pytest.mark.parametrize("node", ["", "::test_first"])
def test_a_named_heavy_file_or_node_runs_without_the_option(selection_repo: Path, node: str) -> None:
    target = sorted(heavy_files())[0]
    expected = {target + node} if node else {f"{target}::test_{name}" for name in ("first", "second")}
    assert collect(selection_repo, target + node) == expected
