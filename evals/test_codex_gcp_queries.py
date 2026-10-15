"""Bounded GCP01 receipt preparation; no model, cloud connection or review answers."""

import re
import shlex
import shutil
import subprocess
from pathlib import Path

import codex_gcp_queries as queries
import pytest
from probe import workspaces
from probe_testkit import scenario_file

CASES = ("build-gcp01-startup-a", "build-gcp01-startup-b")
SCENARIOS = Path(__file__).parent / "build-scenarios"
SCOPE = "--project=synthetic-quotes-prod --region=us-central1"
LOG_READ = (
    "gcloud logging read 'resource.type=cloud_run_revision AND "
    "resource.labels.project_id=synthetic-quotes-prod AND "
    "resource.labels.location=us-central1 AND resource.labels.service_name=quote-service' "
    "--project=synthetic-quotes-prod --limit=100 --order=asc"
)
SERVICE_LOGS = f"gcloud run services logs read quote-service {SCOPE} --limit=100"
EXPECTED = {
    f"gcloud run services describe quote-service {SCOPE}": "describe",
    f"gcloud run revisions describe quote-service-00042-xom {SCOPE}": "describe",
    f"gcloud run revisions describe quote-service-00041-pav {SCOPE}": "describe",
    f"gcloud run revisions list --service=quote-service {SCOPE}": "inventory",
    LOG_READ: "logs",
    SERVICE_LOGS: "logs",
    "gcloud logging logs list --project=synthetic-quotes-prod": "inventory",
}


def seed(tmp_path, case_id):
    spec = scenario_file(SCENARIOS / f"{case_id}.yaml")
    return spec, workspaces.seed_workspace(spec, tmp_path)


@pytest.fixture
def posix_shell():
    if shutil.which("sh") is None:
        pytest.skip("GCP01 fixture execution requires an explicitly available POSIX sh")


def test_pair_preserves_the_decisive_variant_logs(tmp_path, posix_shell):
    receipts = [queries.prepare_queries(*seed(tmp_path / case_id, case_id)) for case_id in CASES]
    assert [set(rows) for rows in receipts] == [set(EXPECTED), set(EXPECTED)]
    for command, kind in EXPECTED.items():
        left, right = (rows[command] for rows in receipts)
        assert left.keys() == right.keys() == {"kind", "stdout", "stderr", "exit_code"}
        assert left["kind"] == right["kind"] == kind
        assert left["exit_code"] == right["exit_code"] == 0
        assert left["stderr"] == right["stderr"] == ""
        if kind == "logs":
            assert "http: listening on 127.0.0.1:8080" in left["stdout"]
            assert "cache warm-up: 17/40 batches after 232s" in right["stdout"]
            assert "http: listening on 127.0.0.1:8080" not in right["stdout"]
        else:
            assert left == right


@pytest.mark.parametrize("case_id", CASES)
def test_only_exact_scoped_queries_reach_the_fixture(tmp_path, posix_shell, case_id):
    spec, ws = seed(tmp_path, case_id)
    # Unrelated fields cannot add executable requests to this closed catalog.
    spec["commands"] = ["gcloud auth print-access-token", "gcloud run deploy other-service"]
    prepared = queries.prepare_queries(spec, ws)
    assert {command: row["kind"] for command, row in prepared.items()} == EXPECTED
    logged = (ws.state_dir / "gcloud-invocations.log").read_text(encoding="utf-8").splitlines()
    assert logged == [" ".join(shlex.split(command)[1:]) for command in EXPECTED]
    assert sorted(path.name for path in ws.state_dir.iterdir()) == ["gcloud-invocations.log"]
    assert not workspaces.collect_git_facts(ws).changed


@pytest.mark.parametrize("case_id", CASES)
def test_denied_log_receipts_keep_failure_status_and_error_output(tmp_path, posix_shell, case_id):
    spec = scenario_file(SCENARIOS / f"{case_id}.yaml")
    denied = "print_logs() {\n  printf '%s\\n' 'Fixture observation unavailable: logging read permission denied.' >&2\n  return 1\n}"
    spec["fixture"]["fake_bin"]["gcloud"], count = re.subn(
        r"(?ms)^print_logs\(\) \{.*?^}", lambda _: denied, spec["fixture"]["fake_bin"]["gcloud"]
    )
    assert count == 1
    ws = workspaces.seed_workspace(spec, tmp_path)
    prepared = queries.prepare_queries(spec, ws)
    assert set(prepared) == set(EXPECTED)
    for command in (LOG_READ, SERVICE_LOGS):
        assert prepared[command] == {
            "kind": "logs",
            "stdout": "",
            "stderr": "Fixture observation unavailable: logging read permission denied.\n",
            "exit_code": 1,
        }
    assert prepared[f"gcloud run services describe quote-service {SCOPE}"]["exit_code"] == 0
    assert not (ws.state_dir / "gcloud-change-requested").exists()


@pytest.mark.parametrize(
    "script",
    [
        "#!/bin/sh\nmissing_gcp01_fixture_utility\n",
        "#!/bin/sh\nprintf '%s\\n' 'unrelated fixture failure' >&2\nexit 1\n",
        "#!/bin/sh\nprintf '%s\\n' 'fixture executable unavailable' >&2\nexit 126\n",
        "#!/bin/sh\nprintf '%s\\n' 'unsupported invocation' >&2\nexit 64\n",
        "#!/bin/sh\nprintf '%s\\n' 'partial output'\nprintf '%s\\n' 'Fixture observation unavailable: read denied.' >&2\nexit 1\n",
    ],
)
def test_unexpected_wrapper_failures_abort_preparation(tmp_path, posix_shell, script):
    spec = scenario_file(SCENARIOS / f"{CASES[0]}.yaml")
    # Authored broken fixtures exercise real shell statuses, including missing utilities.
    spec["fixture"]["fake_bin"]["gcloud"] = script
    ws = workspaces.seed_workspace(spec, tmp_path)
    with pytest.raises(RuntimeError, match="GCP01 fixture query failed"):
        queries.prepare_queries(spec, ws)


def test_missing_wrapper_aborts_preparation_without_gcloud_fallback(tmp_path, posix_shell):
    spec, ws = seed(tmp_path, CASES[0])
    (ws.bin_dir / "gcloud").unlink()
    with pytest.raises(RuntimeError, match="GCP01 fixture query failed"):
        queries.prepare_queries(spec, ws)
    assert list(ws.state_dir.iterdir()) == []


def test_missing_shell_fails_before_any_command_or_fallback(tmp_path, monkeypatch):
    spec, ws = seed(tmp_path, CASES[0])
    monkeypatch.setattr(queries.shutil, "which", lambda _: None)

    def unexpected_run(*args, **kwargs):
        pytest.fail("no subprocess or real gcloud fallback is allowed without sh")

    monkeypatch.setattr(queries.subprocess, "run", unexpected_run)
    with pytest.raises(RuntimeError, match=r"POSIX.*sh"):
        queries.prepare_queries(spec, ws)
    assert list(ws.state_dir.iterdir()) == []


@pytest.mark.parametrize("case_id", ["build-gcp02-revision-traffic-a", "build-gcp01-startup-c", "", None])
def test_other_case_ids_fail_before_execution(tmp_path, monkeypatch, case_id):
    spec, ws = seed(tmp_path, CASES[0])
    spec["id"] = case_id

    def unexpected_run(*args, **kwargs):
        pytest.fail("unsupported cases must never execute a fixture")

    monkeypatch.setattr(queries.subprocess, "run", unexpected_run)
    with pytest.raises(ValueError, match="GCP01"):
        queries.prepare_queries(spec, ws)
    assert list(ws.state_dir.iterdir()) == []


def test_preparation_uses_isolated_env_explicit_argv_and_a_timeout(tmp_path, posix_shell, monkeypatch):
    spec, ws = seed(tmp_path, CASES[0])
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "synthetic-must-not-inherit")
    monkeypatch.setenv("CLOUDSDK_AUTH_ACCESS_TOKEN", "synthetic-must-not-inherit")
    real_run = subprocess.run
    calls = []

    def inspected_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return real_run(argv, **kwargs)

    monkeypatch.setattr(queries.subprocess, "run", inspected_run)
    prepared = queries.prepare_queries(spec, ws)
    assert len(calls) == len(prepared) == len(EXPECTED)
    for (argv, options), command in zip(calls, EXPECTED, strict=True):
        assert argv == [shutil.which("sh"), str(ws.bin_dir / "gcloud"), *shlex.split(command)[1:]]
        assert options["timeout"] == 20
        assert options["encoding"] == "utf-8"
        assert options["capture_output"] is True
        assert not options.get("shell")
        assert options["cwd"] == ws.repo
        assert options["env"]["STATE_DIR"] == ws.state_dir.as_posix()
        assert "GOOGLE_APPLICATION_CREDENTIALS" not in options["env"]
        assert "CLOUDSDK_AUTH_ACCESS_TOKEN" not in options["env"]
    assert all(row["exit_code"] == 0 for row in prepared.values())
