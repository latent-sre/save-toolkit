"""Run the documented deploy/recovery Bash against a local CF fixture, never a foundation."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from threading import Thread

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

if args[0] == "version":
    print("cf version 8.0.0+fixture")
elif args[0] in {"api", "auth", "target"}:
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


def run_example(tmp_path, shell, script, mode, *, outputs=None, manifest=None, timeout=20):
    fake = tmp_path / "fake_cf.py"
    fake.write_text(CF_FIXTURE, encoding="utf-8")
    calls = tmp_path / "calls.jsonl"
    output = tmp_path / "github-output"
    output.write_text("", encoding="utf-8")
    release = tmp_path / "release"
    release.mkdir()
    app_bytes = b"fixture application"
    manifest_bytes = yaml.safe_dump(
        {"applications": [{"name": "order-router"}]} if manifest is None else manifest
    ).encode()
    (release / "app.zip").write_bytes(app_bytes)
    (release / "manifest.yml").write_bytes(manifest_bytes)
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
        "APP_SHA256": hashlib.sha256(app_bytes).hexdigest(),
        "MANIFEST_SHA256": hashlib.sha256(manifest_bytes).hexdigest(),
        "RUNNER_TEMP": tmp_path.as_posix(),
        "RELEASE_DIR": release.as_posix(),
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
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=timeout,
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
    push = next(call for call in calls if call[0] == "push")
    assert push[1] == "order-router", "deployment must use the discovery/recovery identity"


@pytest.mark.parametrize("manifest", [
    {"applications": [{"name": "quotes"}]},
    {"applications": [{"name": "order-router"}, {"name": "quotes"}]},
    {"applications": []},
    {"applications": [{"memory": "256M"}]},
    {"applications": {"name": "order-router"}},
    [],
])
def test_inconsistent_manifest_stops_before_credentials(tmp_path, shell, example_steps, manifest):
    script = (example_steps["Verify release bytes and cf CLI v8"]["run"]
              + "\n" + example_steps["Deploy"]["run"])
    result, calls, _ = run_example(tmp_path, shell, script, "existing", manifest=manifest)
    assert result.returncode != 0, (result.stdout, calls)
    assert not any(call[0] in {"api", "auth", "target", "push"} for call in calls), calls


def test_missing_pyyaml_stops_with_a_named_requirement(tmp_path, shell, example_steps):
    import venv

    bare = tmp_path / "python-without-pyyaml"
    venv.create(bare, with_pip=False)
    python = bare / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    script = (example_steps["Verify release bytes and cf CLI v8"]["run"]
              + "\n" + example_steps["Deploy"]["run"])
    # run_example also fails on any Traceback, which an unguarded import would print.
    result, calls, _ = run_example(tmp_path, shell, script, "existing",
                                   outputs={"TEST_PYTHON": python.as_posix()})
    assert result.returncode != 0
    assert "PyYAML" in result.stderr, result.stderr
    assert not any(call[0] in {"api", "auth", "target", "push"} for call in calls), calls


def test_matching_manifest_reaches_bound_deploy(tmp_path, shell, example_steps):
    script = (example_steps["Verify release bytes and cf CLI v8"]["run"]
              + "\n" + example_steps["Deploy"]["run"])
    result, calls, _ = run_example(tmp_path, shell, script, "existing")
    assert result.returncode == 0, result.stderr
    assert next(call for call in calls if call[0] == "push")[1] == "order-router"


HEALTH_BODY = "readiness-body-marker"


@contextmanager
def health_endpoint(statuses):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/login":  # a followed redirect would find a healthy-looking page
                status, headers = 200, {}
            else:
                entry = statuses[min(len(requests), len(statuses) - 1)]
                status, headers = entry if isinstance(entry, tuple) else (entry, {})
            requests.append(self.path)
            self.send_response(status)
            if status == 302:
                self.send_header("Location", "/login")
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(HEALTH_BODY)))
            self.end_headers()
            self.wfile.write(HEALTH_BODY.encode())

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/readyz", requests
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.mark.parametrize("statuses, succeeds, attempts", [
    ([200], True, 1),
    ([302], False, 1),
    ([401], False, 1),
    ([503, 200], True, 2),
    ([503], False, 6),
    # A Retry-After past --retry-max-time ends the retries; without that bound curl sleeps it out.
    ([(503, {"Retry-After": "65"}), 200], False, 1),
])
def test_health_requires_ready_status_and_preserves_bounded_retries(
    tmp_path, shell, example_steps, statuses, succeeds, attempts
):
    curl_home = tmp_path / "curl-home"
    curl_home.mkdir()
    (curl_home / ".curlrc").write_text("location\n", encoding="utf-8")  # a runner's curl config
    with health_endpoint(statuses) as (url, requests):
        result, calls, _ = run_example(
            tmp_path, shell, example_steps["Verify health"]["run"], "existing",
            outputs={"HEALTH_URL": url, "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1",
                     "CURL_HOME": curl_home.as_posix()},
            timeout=40,
        )
    assert (result.returncode == 0) is succeeds, (result.stdout, result.stderr)
    assert requests == ["/readyz"] * attempts
    assert HEALTH_BODY not in result.stdout + result.stderr
    if not succeeds:
        last = statuses[min(attempts, len(statuses)) - 1]
        final = last[0] if isinstance(last, tuple) else last
        annotation = f"::error::Expected HTTP 200 from readiness endpoint; received {final}"
        assert annotation in result.stdout, result.stdout
    assert not calls


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
