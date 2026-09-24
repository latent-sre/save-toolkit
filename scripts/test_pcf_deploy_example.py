"""Run the documented deploy/recovery Bash against a local CF fixture, never a foundation."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "skills/ci-actions/references/pcf-deploy-job.md"
CF_FIXTURE = r'''
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
log = Path(os.environ["CF_CALLS"])
previous = log.read_text() if log.exists() else ""
with log.open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(args) + "\n")
mode = os.environ["CF_CASE"]
app_guid = "11111111-1111-4111-8111-111111111111"
space_guid = "22222222-2222-4222-8222-222222222222"

def response(resources, total=None, next_page=None):
    print(json.dumps({"pagination": {"total_results": len(resources) if total is None else total,
                                    "next": next_page}, "resources": resources}))

if args[0] in {"api", "auth", "target"}:
    pass
elif args[0] == "push":
    recovery = dict(line.split("=", 1) for line in Path(os.environ["GITHUB_OUTPUT"]).read_text().splitlines())
    expected = {"first_deploy": "true", "previous_revision": ""} if mode == "absent" else {
        "first_deploy": "false", "previous_revision": "12"}
    assert recovery == expected, "recovery evidence must be recorded before push"
elif args[0] == "space":
    if mode == "space_error":
        raise SystemExit(1)
    print(space_guid)
elif args[0] == "app":
    if '"push"' not in previous and mode in {"absent", "discovery_error"}:
        raise SystemExit(1)
elif args[0] == "revisions":  # Baseline uses the human-readable command.
    if mode == "revision_error":
        raise SystemExit(1)
    print("unreadable" if mode == "malformed_revision" else "12 deployed")
elif args[0] == "curl":
    assert "--fail" in args, "HTTP errors must fail the discovery request"
    endpoint = next(arg for arg in args if arg.startswith("/v3/"))
    if endpoint.startswith("/v3/apps?"):
        from urllib.parse import parse_qs, urlsplit
        query = parse_qs(urlsplit(endpoint).query)
        assert query["names"] == [os.environ["APP_NAME"]]
        assert query["space_guids"] == [space_guid]
        if mode == "discovery_error":
            raise SystemExit(22)
        if mode == "malformed_apps":
            print("{}")
        elif mode == "absent":
            response([])
        elif mode == "incomplete_apps":
            response([], total=1)
        else:
            app = {"guid": app_guid, "name": os.environ["APP_NAME"]}
            response([app, app] if mode == "ambiguous_apps" else [app])
    elif endpoint == f"/v3/apps/{app_guid}/revisions/deployed":
        if mode == "revision_error":
            raise SystemExit(22)
        if mode == "malformed_revision":
            print("not JSON")
        else:
            revision = {"version": 12, "deployable": mode != "undeployable_revision"}
            if mode == "invalid_revision_version":
                revision["version"] = "12; echo bad"
            resources = [] if mode == "missing_revision" else [revision]
            if mode == "multiple_revisions":
                resources.append({"version": 13, "deployable": True})
            response(resources, total=2 if mode == "incomplete_revisions" else None,
                     next_page={"href": "/v3/next"} if mode == "continued_revisions" else None)
    else:
        raise AssertionError(f"unexpected endpoint: {endpoint}")
else:
    raise AssertionError(f"unexpected CF command: {args}")
'''


@pytest.fixture
def example_steps():
    text = REFERENCE.read_text(encoding="utf-8")
    block = re.search(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    assert block is not None, "deployment example must have a YAML block"
    document = yaml.safe_load(block[1])
    return {step["name"]: step for step in document["deploy-prod"]["steps"] if "name" in step}


@pytest.fixture
def shell():
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    executable = str(git_bash) if os.name == "nt" and git_bash.is_file() else shutil.which("bash")
    if not executable:
        pytest.skip("Bash is required to exercise the documented shell")
    return executable


def run_example(tmp_path, shell, script, mode, *, outputs=None):
    fake = tmp_path / "fake_cf.py"
    fake.write_text(CF_FIXTURE, encoding="utf-8")
    calls = tmp_path / "calls.jsonl"
    output = tmp_path / "github-output"
    output.write_text("", encoding="utf-8")
    environment = {
        **os.environ,
        "CF_CASE": mode,
        "CF_CALLS": calls.as_posix(),
        "CF_FIXTURE": fake.as_posix(),
        "TEST_PYTHON": Path(sys.executable).as_posix(),
        "CF_API": "https://fixture.invalid",
        "CF_USERNAME": "fixture",
        "CF_PASSWORD": "fixture",
        "CF_ORG": "fixture-org",
        "CF_SPACE": "fixture-space",
        "APP_NAME": "order-router",
        "RUNNER_TEMP": tmp_path.as_posix(),
        "RELEASE_DIR": (tmp_path / "release").as_posix(),
        "GITHUB_OUTPUT": output.as_posix(),
        **(outputs or {}),
    }
    environment.pop("BASH_ENV", None)
    # Every cf call is intercepted; no foundation calls are made. Preserve CAPI path arguments
    # when the fixture runs via native Windows Python under Git Bash's MSYS translation.
    wrapper = 'cf() { MSYS2_ARG_CONV_EXCL="*" "$TEST_PYTHON" -I -B "$CF_FIXTURE" "$@"; }\n'
    wrapper += 'python3() { "$TEST_PYTHON" "$@"; }\n'
    result = subprocess.run(
        [shell, "--noprofile", "--norc", "-c", wrapper + script],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=20,
    )
    observed = [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
    recorded = dict(line.split("=", 1) for line in output.read_text().splitlines())
    assert "Traceback" not in result.stderr, "fixture or parser setup failed: " + result.stderr
    return result, observed, recorded


@pytest.mark.parametrize("mode", [
    "discovery_error", "space_error", "malformed_apps", "incomplete_apps", "ambiguous_apps",
    "revision_error", "malformed_revision", "missing_revision", "undeployable_revision",
    "invalid_revision_version", "multiple_revisions", "incomplete_revisions", "continued_revisions",
])
def test_failed_or_ambiguous_discovery_never_pushes(tmp_path, shell, example_steps, mode):
    result, calls, _ = run_example(tmp_path, shell, example_steps["Deploy"]["run"], mode)
    assert not any(call[0] == "push" for call in calls), (mode, calls, result.stdout, result.stderr)
    assert result.returncode != 0


@pytest.mark.parametrize("mode, expected", [
    ("absent", {"first_deploy": "true", "previous_revision": ""}),
    ("existing", {"first_deploy": "false", "previous_revision": "12"}),
])
def test_confirmed_target_records_recovery_before_push(tmp_path, shell, example_steps, mode, expected):
    result, calls, outputs = run_example(tmp_path, shell, example_steps["Deploy"]["run"], mode)
    assert result.returncode == 0, result.stderr
    assert sum(call[0] == "push" for call in calls) == 1
    assert outputs == expected
    assert any(call[0] == "curl" for call in calls)


@pytest.mark.parametrize("first, revision, expected, forbidden", [
    ("true", "", "no previous revision", "cf rollback"),
    ("false", "12", "cf rollback order-router --version 12", "<deployed revision"),
    ("", "", "Discovery incomplete", "cf rollback"),
])
def test_recovery_handoff_uses_discovery_result(
    tmp_path, shell, example_steps, first, revision, expected, forbidden
):
    result, calls, _ = run_example(
        tmp_path, shell, example_steps["Recovery handoff"]["run"], "existing",
        outputs={"FIRST_DEPLOY": first, "PREVIOUS_REVISION": revision},
    )
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout
    assert forbidden not in result.stdout
    assert not calls, "recovery is advice, never a CF mutation"
