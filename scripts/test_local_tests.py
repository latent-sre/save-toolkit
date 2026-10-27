"""Real process/lock and pytest-exit contracts for the coordinated local runner."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import local_tests

ROOT = Path(__file__).resolve().parents[1]


def child(code: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", "-c", code, *args], capture_output=True,
                          text=True, encoding="utf-8", timeout=30,
                          env={**os.environ, "PYTHONPATH": str(ROOT / "scripts")})


def test_another_process_cannot_take_a_live_lease(tmp_path):
    lock = tmp_path / "suite.lock"
    code = "from pathlib import Path; from local_tests import suite_lease; " \
           "import sys;\nwith suite_lease(Path(sys.argv[1])): print('acquired')"
    with local_tests.suite_lease(lock):
        result = child(code, str(lock))
        assert result.returncode != 0
        assert "another coordinated test run" in result.stderr
        assert "acquired" not in result.stdout
    assert child(code, str(lock)).returncode == 0


def test_process_exit_releases_the_lease_without_deleting_a_stale_file(tmp_path):
    lock = tmp_path / "suite.lock"
    code = "from pathlib import Path; from local_tests import suite_lease; import sys;\n" \
           "with suite_lease(Path(sys.argv[1])):\n print('locked', flush=True); sys.stdin.read()"
    proc = subprocess.Popen([sys.executable, "-B", "-c", code, str(lock)],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env={**os.environ, "PYTHONPATH": str(ROOT / "scripts")})
    try:
        assert proc.stdout.readline().strip() == "locked"
        with pytest.raises(local_tests.SuiteBusy), local_tests.suite_lease(lock):
            pytest.fail("live lease was acquired twice")
    finally:
        proc.kill()
        proc.communicate(timeout=15)
    assert lock.is_file()
    with local_tests.suite_lease(lock):
        pass


@pytest.fixture
def repository(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts/local_tests.py", repo / "scripts/local_tests.py")
    (repo / "pytest.ini").write_text("[pytest]\naddopts = -n 2 --dist loadfile\n", encoding="utf-8")
    (repo / "test_sample.py").write_text("def test_sample():\n    assert True\n", encoding="utf-8")
    for args in (("init", "-q", "-b", "main"), ("add", "."),
                 ("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    return repo


def invoke(repo: Path, *args: str, inherited_options: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS")}
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    if inherited_options is not None:
        env["PYTEST_ADDOPTS"] = inherited_options
    return subprocess.run([sys.executable, "-B", str(repo / "scripts/local_tests.py"), "-p", "xdist.plugin", *args],
                          cwd=repo, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)


@pytest.mark.parametrize("source, arguments, expected", [
    ("def test_sample():\n    assert True\n", ["-n", "0"], 0),
    ("def test_sample():\n    assert False\n", ["-n", "0"], 1),
    ("def test_sample(:\n", ["-n", "0"], 2),
    ("def test_sample():\n    assert True\n", ["--invalid-local-test-option"], 4),
])
def test_records_actual_pytest_result_and_source_identity(repository, source, arguments, expected):
    (repository / "test_sample.py").write_text(source, encoding="utf-8")
    result = invoke(repository, *arguments)
    assert result.returncode == expected, result.stdout + result.stderr
    receipts = list((repository / ".git/local-test-runs").glob("*/run.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["exit_code"] == expected
    assert receipt["elapsed_seconds"] > 0
    assert receipt["source_before"]["head"] == subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
    assert receipt["source_after"] == receipt["source_before"]
    assert receipt["source_before"]["dirty"] == (expected in (1, 2))
    assert receipt["command"][:3] == [sys.executable, "-m", "pytest"]
    assert receipt["versions"]["pytest"]
    log = receipts[0].parent / "pytest.log"
    assert log.is_file() and log.stat().st_size
    if expected != 4:
        assert (receipts[0].parent / "junit.xml").is_file()
        assert receipt["effective"]["workers"] == 0
    with local_tests.suite_lease(repository / ".git/local-tests.lock"):
        pass


def test_inherited_narrowing_and_collection_only_cannot_look_like_a_full_execution(repository):
    (repository / "test_sample.py").write_text(
        "def test_sample(): assert False\ndef test_excluded(): assert False\n", encoding="utf-8")
    (repository / "test_ignored.py").write_text("def test_sample(): assert False\n", encoding="utf-8")
    result = invoke(repository, "-n", "0", inherited_options=(
        "-k test_sample --ignore=test_ignored.py --deselect=test_sample.py::test_excluded "
        "--maxfail=1 --collect-only --last-failed-no-failures=none"))
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(next((repository / ".git/local-test-runs").glob("*/run.json")).read_text())
    settings = receipt["effective"]
    assert settings["keyword"] == "test_sample"
    assert settings["collect_only"] is True
    assert settings["ignored_paths"] == ["test_ignored.py"]
    assert settings["deselected_nodes"] == ["test_sample.py::test_excluded"]
    assert settings["max_failures"] == 1
    assert settings["last_failed_no_failures"] == "none"
    assert receipt["results"]["collected"] == 1


def test_linked_worktrees_share_one_lease_and_busy_runs_do_not_start_pytest(repository, tmp_path):
    linked = tmp_path / "linked"
    subprocess.run(["git", "worktree", "add", "--detach", str(linked), "HEAD"],
                   cwd=repository, check=True, capture_output=True)
    assert local_tests.common_git_dir(repository) == local_tests.common_git_dir(linked)
    with local_tests.suite_lease(repository / ".git/local-tests.lock"):
        result = invoke(linked, "-n", "0")
        assert result.returncode == 2
        assert "another coordinated test run" in result.stderr
        assert not (repository / ".git/local-test-runs").exists()


@pytest.fixture
def suite_repository(repository):
    (repository / "evals/suites").mkdir(parents=True)
    shutil.copyfile(ROOT / "evals/catalog.py", repository / "evals/catalog.py")
    (repository / "scripts/test_named.py").write_text(
        "def test_good(): pass\ndef test_other(): pass\n", encoding="utf-8")
    (repository / "test_sample.py").write_text("def test_outside(): assert False\n", encoding="utf-8")
    (repository / "evals/suites/named.json").write_text(json.dumps({
        "schema_version": 1, "id": "named", "summary": "named fixture", "tests": ["scripts/test_named.py"],
        "native_scenarios": [], "campaigns": [], "guides": [],
    }), encoding="utf-8")
    return repository


def test_named_suite_runs_only_its_paths_and_records_resolution(suite_repository):
    result = invoke(suite_repository, "--suite", "named", "--suite", "named", "-n", "0")
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(next((suite_repository / ".git/local-test-runs").glob("*/run.json")).read_text())
    assert receipt["results"] == {"collected": 2, "failed": 0}
    assert receipt["suite_selection"]["names"] == ["named"]
    assert receipt["suite_selection"]["items"] == [{"path": "scripts/test_named.py", "selected_by": ["named"]}]
    assert receipt["effective"]["selected_paths"] == ["scripts/test_named.py"]


def test_suite_narrowing_is_visible_and_pytest_values_are_not_extra_paths(suite_repository):
    result = invoke(suite_repository, "--suite", "named", "-n", "0", "-k", "good")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "filtered" in result.stdout.lower()
    receipt = json.loads(next((suite_repository / ".git/local-test-runs").glob("*/run.json")).read_text())
    assert receipt["results"]["collected"] == 1
    assert receipt["effective"]["keyword"] == "good"


def test_extra_positional_paths_are_refused_before_collection(suite_repository):
    result = invoke(suite_repository, "--suite", "named", "-n", "0", "test_sample.py")
    assert result.returncode == 4, result.stdout + result.stderr
    assert "explicit test paths" in result.stdout + result.stderr
    assert "test_outside" not in result.stdout


def test_unknown_suite_does_not_acquire_lease_or_create_run_receipt(suite_repository):
    result = invoke(suite_repository, "--suite", "missing", "-n", "0")
    assert result.returncode == 3, result.stdout + result.stderr
    assert not (suite_repository / ".git/local-test-runs").exists()
    assert not (suite_repository / ".git/local-tests.lock").exists()


def test_inherited_filter_and_zero_collection_remain_visible(suite_repository):
    result = invoke(suite_repository, "--suite", "named", "-n", "0", inherited_options="-k nonexistent")
    assert result.returncode == 5, result.stdout + result.stderr
    assert "filtered" in result.stdout.lower()


@pytest.mark.parametrize("source, override", [
    ("def test_good(): pass\ndef test_other(): pass\n", "python_functions=test_good"),
    ("class TestKeep:\n def test_good(self): pass\nclass TestDrop:\n def test_other(self): pass\n",
     "python_classes=TestKeep"),
])
def test_inherited_collection_overrides_are_recorded_as_filtered(suite_repository, source, override):
    (suite_repository / "scripts/test_named.py").write_text(source, encoding="utf-8")
    result = invoke(suite_repository, "--suite", "named", "-n", "0", inherited_options=f"-o {override}")
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(next((suite_repository / ".git/local-test-runs").glob("*/run.json")).read_text())
    assert receipt["results"]["collected"] == 1
    assert receipt["effective"]["suite_filtered"] is True
    assert "filtered" in result.stdout.lower()
    key, value = override.split("=", 1)
    assert receipt["effective"]["collection"][key] == [value]
    assert key in receipt["effective"]["collection_overrides"]
