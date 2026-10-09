"""Offline request/response tests; no production access or real credentials."""
from __future__ import annotations

import base64
import io
import json
import os
import shlex
import shutil
import ssl
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError

import pytest

from testkit import load_path, require_shell

PATH = Path(__file__).resolve().parents[1] / "skills/grafana/scripts/grafana_read.py"
reader = load_path(PATH, "grafana_read")

UNAUTHENTICATED = {"GRAFANA_URL": "https://monitor.example/grafana", "GRAFANA_ORG_ID": "7"}
ENV = {**UNAUTHENTICATED, "GRAFANA_SA_TOKEN": "test-secret-token"}
DASHBOARD = ["dashboard", "--uid", "board"]
QUERY = ["query", "--datasource", "metrics-1", "--kind", "prometheus", "--from", "1000", "--to", "61000", "--expr", "up"]


class Transport:
    def __init__(self, *responses, org_response=None):
        self.responses = [(200, {"id": 7}) if org_response is None else org_response, *responses]
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        status, payload = response
        return status, payload if isinstance(payload, bytes) else json.dumps(payload).encode()


def invoke(args, transport, env=None):
    output = io.StringIO()
    code = reader.main(args, environ=ENV if env is None else env, transport=transport, output=output)
    return code, json.loads(output.getvalue()), output.getvalue()


REAL_SETTINGS_FILE = reader._settings_file
SETTINGS_TEXT = "# comment\r\nGRAFANA_URL=https://monitor.example/grafana\r\nGRAFANA_ORG_ID=7\r\nGRAFANA_SA_TOKEN=file-secret-token\r\n"


@pytest.fixture(autouse=True)
def no_settings_file(monkeypatch, tmp_path):
    """Never read the developer's real per-user settings file."""
    monkeypatch.setattr(reader, "_settings_file", lambda: tmp_path / "absent.env")


def use_settings(monkeypatch, tmp_path, content):
    path = tmp_path / "grafana.env"
    path.write_bytes(content if isinstance(content, bytes) else content.encode())
    path.chmod(0o600)
    monkeypatch.setattr(reader, "_settings_file", lambda: path)
    return path


@pytest.mark.parametrize("org", [None, "", "0", "-1", "+7", "07", "7.0", "7 ", " 7", "\uff17", "9223372036854775808", "7\r\nInjected: bad"])
def test_organization_must_be_explicit_positive_canonical_int64(org):
    env = dict(ENV)
    if org is None:
        env.pop("GRAFANA_ORG_ID")
    else:
        env["GRAFANA_ORG_ID"] = org
    transport = Transport()
    code, result, _ = invoke(DASHBOARD, transport, env)
    assert code == 2 and result["error"] == "invalid_organization_configuration"
    assert not transport.requests


@pytest.mark.parametrize("args", [DASHBOARD, QUERY, ["search", "--query", "edge"], ["silences"]])
@pytest.mark.parametrize("actual", [2, "7", True, None])
def test_organization_mismatch_stops_before_selected_operation(args, actual):
    transport = Transport(org_response=(200, {"id": actual}))
    code, result, _ = invoke(args, transport)
    assert code == 2 and result["error"] == "organization_mismatch"
    assert len(transport.requests) == 1
    assert transport.requests[0].full_url.endswith("/api/org")


@pytest.mark.parametrize("datasource_org", [2, "7", True, None])
def test_same_datasource_uid_from_other_organization_never_queries(datasource_org):
    transport = Transport((200, {"uid": "metrics-1", "type": "prometheus", "orgId": datasource_org}))
    code, result, _ = invoke(QUERY, transport)
    assert code == 2 and result["error"] == "organization_mismatch"
    assert len(transport.requests) == 2


@pytest.mark.parametrize("credentials", [{"GRAFANA_SA_TOKEN": "synthetic-token"}, {"GRAFANA_USERNAME": "synthetic-user", "GRAFANA_PASSWORD": "synthetic-pass"}])
@pytest.mark.parametrize("command", ["dashboard", "query"])
def test_all_requests_bind_verified_organization_and_report_it(credentials, command):
    env = {**UNAUTHENTICATED, **credentials}
    responses = [(200, {"dashboard": {"uid": "board"}, "meta": {}})] if command == "dashboard" else [
        (200, {"uid": "metrics-1", "type": "prometheus", "orgId": 7}),
        (200, {"results": {"A": {"frames": []}}}),
    ]
    transport = Transport(*responses)
    code, result, _ = invoke(DASHBOARD if command == "dashboard" else QUERY, transport, env)
    assert code == 0 and result["organization_id"] == 7
    assert transport.requests[0].full_url.endswith("/api/org")
    assert all(request.get_header("X-grafana-org-id") == "7" for request in transport.requests)


def test_dashboard_uses_fixed_get_and_masks_authentication():
    transport = Transport((200, {"dashboard": {"uid": "board-1", "title": "test-secret-token", "test-secret-token": "hidden"}, "meta": {}}))
    code, result, text = invoke(["dashboard", "--uid", "board-1"], transport)
    assert code == 0 and result["ok"]
    assert result["grafana_url"] == ENV["GRAFANA_URL"]
    assert datetime.fromisoformat(result["retrieved_at_utc"]).utcoffset() == UTC.utcoffset(None)
    assert "test-secret-token" not in text
    org_request, request = transport.requests
    assert org_request.full_url.endswith("/api/org")
    assert request.full_url == "https://monitor.example/grafana/api/dashboards/uid/board-1"
    assert request.method == "GET" and request.data is None
    assert request.get_header("Authorization") == "Bearer test-secret-token"


def test_basic_auth_values_and_encodings_masked_in_keys_and_nested_values():
    user, password = "test-person", "private-pass"
    encoded = base64.b64encode(f"{user}:{password}".encode()).decode()
    env = {**UNAUTHENTICATED, "GRAFANA_USERNAME": user, "GRAFANA_PASSWORD": password}
    transport = Transport((200, {"dashboard": {"uid": "board", user: [password, encoded]}, "meta": {}}))
    code, _, text = invoke(DASHBOARD, transport, env)
    assert code == 0
    assert all(value not in text for value in (user, password, encoded))
    assert transport.requests[0].get_header("Authorization") == "Basic " + encoded


def test_numeric_authentication_values_are_masked_when_echoed_as_json_numbers():
    env = {**UNAUTHENTICATED, "GRAFANA_USERNAME": "741829", "GRAFANA_PASSWORD": "928413"}
    transport = Transport((200, {"dashboard": {"uid": "board", "numeric_username": 741829,
                             "numeric_password": 928413.0}, "meta": {}}))
    code, result, text = invoke(DASHBOARD, transport, env)
    assert code == 0 and "741829" not in text and "928413" not in text
    assert result["dashboard"]["numeric_username"] == "[REDACTED]"


@pytest.mark.parametrize("credential,value", [("true", True), ("false", False), ("null", None)])
def test_authentication_matching_json_primitives_is_masked_even_in_metadata(credential, value):
    env = {**ENV, "GRAFANA_SA_TOKEN": credential}
    transport = Transport((200, {"dashboard": {"uid": "board", "echo": value}, "meta": {"echo": value}}))
    code, result, _ = invoke(DASHBOARD, transport, env)
    assert code == 0
    assert result["dashboard"]["echo"] == "[REDACTED]"
    assert result["meta"]["echo"] == "[REDACTED]"
    if credential == "true":
        assert result["ok"] == "[REDACTED]"


def test_query_checks_datasource_and_only_posts_to_query_endpoint():
    transport = Transport((200, {"uid": "metrics-1", "type": "prometheus"}), (200, {"results": {"A": {"frames": []}}}))
    code, result, _ = invoke(QUERY, transport)
    assert code == 0 and result["coverage"] == "not_established"
    assert [(r.method, r.full_url) for r in transport.requests] == [
        ("GET", "https://monitor.example/grafana/api/org"),
        ("GET", "https://monitor.example/grafana/api/datasources/uid/metrics-1?ds_type=prometheus"),
        ("POST", "https://monitor.example/grafana/api/ds/query"),
    ]
    body = json.loads(transport.requests[2].data)
    assert body["from"] == "1000" and body["to"] == "61000"
    assert body["queries"][0]["maxDataPoints"] == 1000
    assert body["queries"][0]["intervalMs"] >= 1000


@pytest.mark.parametrize("datasource", [{"uid": "metrics-1", "type": "mysql"}, {"uid": "other", "type": "prometheus"}, {}])
def test_datasource_mismatch_stops_before_post(datasource):
    transport = Transport((200, datasource))
    code, result, _ = invoke(QUERY, transport)
    assert code == 2 and not result["ok"]
    assert len(transport.requests) == 2


def test_loki_has_explicit_log_limit():
    args = [value if value != "prometheus" else "loki" for value in QUERY]
    transport = Transport((200, {"uid": "metrics-1", "type": "loki"}), (200, {"results": {"A": {"frames": []}}}))
    code, result, _ = invoke(args, transport)
    assert code == 0 and result["limits"]["maxLines"] == 500
    assert json.loads(transport.requests[2].data)["queries"][0]["maxLines"] == 500


@pytest.mark.parametrize("result", [{"error": "test-secret-token"}, {"status": 500}, {"status": "403"}])
def test_query_result_errors_cannot_be_reported_successfully(result):
    transport = Transport((200, {"uid": "metrics-1", "type": "prometheus"}), (200, {"results": {"A": result}}))
    code, response, text = invoke(QUERY, transport)
    assert code == 2 and response["error"] == "query_failed"
    assert "test-secret-token" not in text


@pytest.mark.parametrize("response", [(302, b"secret redirect"), (401, b"test-secret-token"), (200, b"not JSON"), (200, b"x" * (2 * 1024 * 1024 + 1))])
def test_http_json_and_size_failures_return_safe_errors(response):
    code, result, text = invoke(DASHBOARD, Transport(response))
    assert code == 2 and not result["ok"]
    assert "test-secret-token" not in text and "Traceback" not in text


@pytest.mark.parametrize("url", ["http://monitor.example", "https://user:password@monitor.example", "https://monitor.example?token=private", "https://monitor.example/#secret", "https://monitor.example/../else", "https://monitor.example/%2e%2e", "https://monitor.example\\bad", "https://monitor.example/\nfoo"])
def test_invalid_origins_make_no_requests(url):
    transport = Transport()
    code, result, text = invoke(DASHBOARD, transport, {**ENV, "GRAFANA_URL": url})
    assert code == 2 and not result["ok"] and not transport.requests
    assert url not in text


def test_raw_transport_error_is_never_exposed():
    code, result, text = invoke(DASHBOARD, Transport(URLError("user:private-password@secret-host")))
    assert code == 2 and result["error"] == "request_failed"
    assert "private-password" not in text and "secret-host" not in text


def test_url_userinfo_and_auth_headers_are_not_returned():
    transport = Transport((200, {"dashboard": {"uid": "board", "link": "https://another:unknown@host.example/path",
                             "Authorization": "arbitrary-header-value"}, "meta": {}}))
    code, _, text = invoke(DASHBOARD, transport)
    assert code == 0
    assert "another" not in text and "unknown" not in text and "arbitrary-header-value" not in text


@pytest.mark.parametrize("payload", [
    b'{"dashboard":{"uid":"board","value":NaN},"meta":{}}',
    b'{"dashboard":{"uid":"board","value":1e999},"meta":{}}',
    b'[' * 1500 + b']' * 1500,
])
def test_nonfinite_and_deep_json_return_safe_failure(payload):
    code, result, _ = invoke(DASHBOARD, Transport((200, payload)))
    assert code == 2 and not result["ok"]


@pytest.mark.parametrize("results", [{}, {"A": {}, "B": {"frames": []}}, {"A": {}}])
def test_incomplete_or_unexpected_query_results_fail(results):
    transport = Transport((200, {"uid": "metrics-1", "type": "prometheus"}), (200, {"results": results}))
    assert invoke(QUERY, transport)[0] == 2


RULES = {"status": "success", "data": {"groups": [{"name": "checkout", "folderUid": "payments", "rules": []}]}}


@pytest.mark.parametrize("args,payload,path", [
    (["search", "--query", "checkout latency"], [{"uid": "board", "orgId": 7}], "/api/search?type=dash-db&limit=100&query=checkout%20latency"),
    (["alerts"], RULES, "/api/prometheus/grafana/api/v1/rules?group_limit=100&limit_alerts=20"),
    (["alerts", "--folder-uid", "payments"], RULES, "/api/prometheus/grafana/api/v1/rules?group_limit=100&limit_alerts=20&folder_uid=payments"),
    (["annotations", "--from", "1000", "--to", "61000"], [{"id": 1}], "/api/annotations?from=1000&to=61000&limit=100"),
    (["annotations", "--from", "1000", "--to", "61000", "--dashboard-uid", "board"], [], "/api/annotations?from=1000&to=61000&limit=100&dashboardUID=board"),
    (["silences"], [{"id": "s1", "status": {"state": "active"}}], "/api/alertmanager/grafana/api/v2/silences"),
])
def test_list_reads_use_one_fixed_get_and_report_permission_scope(args, payload, path):
    transport = Transport((200, payload))
    code, result, _ = invoke(args, transport)
    assert code == 0 and result["operation"] == args[0] and result["coverage"] == "permission_scoped"
    assert [(r.method, r.full_url, r.data) for r in transport.requests[1:]] == [("GET", ENV["GRAFANA_URL"] + path, None)]
    assert all(request.get_header("X-grafana-org-id") == "7" for request in transport.requests)


def test_alerts_reject_grafana_fallback_from_unknown_folder_to_all_folders():
    other = {"status": "success", "data": {"groups": [{"name": "edge", "folderUid": "other", "rules": []}]}}
    code, result, _ = invoke(["alerts", "--folder-uid", "payments"], Transport((200, other)))
    assert code == 2 and result["error"] == "folder_mismatch"


@pytest.mark.parametrize("payload", [{"status": "error", "error": "test-secret-token"}, {"status": "success", "data": {}},
                                     {"status": "success", "data": {"groups": ["text"]}}])
def test_alerts_rule_api_errors_cannot_be_reported_successfully(payload):
    code, result, text = invoke(["alerts"], Transport((200, payload)))
    assert code == 2 and not result["ok"] and "test-secret-token" not in text


@pytest.mark.parametrize("args,payload", [
    (["search", "--query", "edge"], [{"uid": "board", "orgId": 2}]),
    (["annotations", "--from", "1000", "--to", "61000"], [{"id": 1, "orgId": "7"}]),
    (["silences"], ["not-an-object"]),
    (["silences"], {"silences": []}),
])
def test_list_items_must_be_objects_from_the_verified_organization(args, payload):
    code, result, _ = invoke(args, Transport((200, payload)))
    assert code == 2 and result["error"] in {"organization_mismatch", "invalid_response"}


def test_list_truncation_and_masking_are_reported():
    code, result, text = invoke(["search", "--query", "edge"], Transport((200, [{"uid": f"b{n}", "title": "test-secret-token"} for n in range(100)])))
    assert code == 0 and result["truncated"] is True and "test-secret-token" not in text
    paged = {"status": "success", "data": {"groups": [], "groupNextToken": "next"}}
    assert invoke(["alerts"], Transport((200, paged)))[1]["truncated"] is True


def test_settings_file_is_per_user_not_workspace_relative():
    assert REAL_SETTINGS_FILE() == Path.home() / ".config" / "save-toolkit" / "grafana.env"
    assert REAL_SETTINGS_FILE().is_absolute()


def test_settings_file_supplies_credentials_when_environment_has_none(monkeypatch, tmp_path):
    use_settings(monkeypatch, tmp_path, b"\xef\xbb\xbf" + SETTINGS_TEXT.encode())
    transport = Transport((200, {"dashboard": {"uid": "board", "title": "file-secret-token"}, "meta": {}}))
    code, result, text = invoke(["dashboard", "--uid", "board"], transport, {"PATH": "unrelated"})
    assert code == 0 and result["organization_id"] == 7 and "file-secret-token" not in text
    assert transport.requests[0].get_header("Authorization") == "Bearer file-secret-token"


@pytest.mark.parametrize("env", [{"GRAFANA_URL": ENV["GRAFANA_URL"], "GRAFANA_ORG_ID": "7"}, {"GRAFANA_SA_TOKEN": ""}],
                         ids=["partial", "empty_override"])
def test_any_environment_setting_even_empty_disables_the_settings_file(monkeypatch, tmp_path, env):
    use_settings(monkeypatch, tmp_path, SETTINGS_TEXT)
    transport = Transport()
    code, result, _ = invoke(["dashboard", "--uid", "board"], transport, env)
    assert code == 2 and not result["ok"] and not transport.requests


def test_relative_home_never_selects_a_workspace_settings_file(monkeypatch):
    monkeypatch.setenv("HOME", "relative-home")
    monkeypatch.setenv("USERPROFILE", "relative-home")
    assert REAL_SETTINGS_FILE() is None


@pytest.mark.parametrize("mode,owner,private", [(0o100600, 1000, True), (0o100400, 1000, True), (0o100644, 1000, False),
                                                (0o100640, 1000, False), (0o100606, 1000, False), (0o100600, 0, False)])
def test_posix_settings_file_must_be_owner_only(mode, owner, private):
    info = os.stat_result((mode, 0, 0, 1, owner, 0, 0, 0, 0, 0))
    assert reader._private(info, 1000) is private


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits")
def test_group_or_world_readable_settings_file_is_refused(monkeypatch, tmp_path):
    use_settings(monkeypatch, tmp_path, SETTINGS_TEXT).chmod(0o644)
    transport = Transport()
    code, result, _ = invoke(["dashboard", "--uid", "board"], transport, {})
    assert code == 2 and result["error"] == "insecure_settings_file" and not transport.requests


def test_settings_values_are_used_verbatim(monkeypatch, tmp_path):
    use_settings(monkeypatch, tmp_path, "GRAFANA_URL=https://monitor.example/grafana\nGRAFANA_ORG_ID=7\n"
                 "GRAFANA_USERNAME=person\nGRAFANA_PASSWORD= spaced pass \n")
    transport = Transport((200, {"dashboard": {"uid": "board"}, "meta": {}}))
    assert invoke(["dashboard", "--uid", "board"], transport, {})[0] == 0
    assert transport.requests[0].get_header("Authorization") == "Basic " + base64.b64encode(b"person: spaced pass ").decode()


@pytest.mark.parametrize("content", [
    "GRAFANA_SA_TOKEN file-secret-token\n",
    "GRAFANA_TOKEN=file-secret-token\n",
    "GRAFANA_SA_TOKEN=a\nGRAFANA_SA_TOKEN=file-secret-token\n",
    "GRAFANA_SA_TOKEN=file-secret-token\n" + "#" * 4096,
    b"GRAFANA_SA_TOKEN=\xff file-secret-token\n",
], ids=["no_separator", "unknown_name", "duplicate", "oversized", "not_utf8"])
def test_malformed_settings_file_fails_without_echo_or_requests(monkeypatch, tmp_path, content):
    use_settings(monkeypatch, tmp_path, content)
    transport = Transport()
    code, result, text = invoke(["dashboard", "--uid", "board"], transport, {})
    assert code == 2 and result["error"] == "invalid_settings_file"
    assert "file-secret-token" not in text and not transport.requests


def test_unreadable_settings_path_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(reader, "_settings_file", lambda: tmp_path)
    code, result, _ = invoke(["dashboard", "--uid", "board"], Transport(), {})
    assert code == 2 and result["error"] == "invalid_settings_file"


def test_missing_settings_file_keeps_environment_errors():
    code, result, _ = invoke(["dashboard", "--uid", "board"], Transport(), {})
    assert code == 2 and result["error"] == "invalid_organization_configuration"


def test_token_preferred_and_all_configured_auth_values_masked():
    env = {**ENV, "GRAFANA_USERNAME": "test-person", "GRAFANA_PASSWORD": "basic-password"}
    transport = Transport((200, {"dashboard": {"uid": "board", "text": "test-person basic-password"}, "meta": {}}))
    code, _, text = invoke(DASHBOARD, transport, env)
    assert code == 0 and "test-person" not in text and "basic-password" not in text
    assert transport.requests[0].get_header("Authorization") == "Bearer test-secret-token"


@pytest.mark.parametrize("field,value", [("GRAFANA_SA_TOKEN", "token\r\nInjected: header"), ("GRAFANA_USERNAME", "name\n"), ("GRAFANA_PASSWORD", "pass\r")])
def test_authentication_control_characters_rejected(field, value):
    transport = Transport()
    assert invoke(DASHBOARD, transport, {**ENV, field: value})[0] == 2
    assert not transport.requests


def test_real_transport_configures_tls_no_proxy_no_redirect_and_response_bound(monkeypatch):
    captured = {}

    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, count):
            captured["read_bound"] = count
            return b'{}'

    class Opener:
        def open(self, request, timeout):
            captured["timeout"] = timeout
            return Response()

    def build(*handlers):
        captured["handlers"] = handlers
        return Opener()

    monkeypatch.setattr(reader, "build_opener", build)
    monkeypatch.setenv("HTTPS_PROXY", "http://secret-user:secret-pass@untrusted-proxy")
    assert reader.http_transport(reader.Request("https://monitor.example")) == (200, b'{}')
    proxy, tls, redirect = captured["handlers"]
    assert proxy.proxies == {}
    assert tls._context.verify_mode == ssl.CERT_REQUIRED and tls._context.check_hostname
    with pytest.raises(reader.SafeError, match="redirect_rejected"):
        redirect.redirect_request(None, None, 302, "secret-location", {}, "https://monitor.example/another")
    assert captured["timeout"] == 20 and captured["read_bound"] == 2 * 1024 * 1024 + 1


@pytest.mark.parametrize("env", [UNAUTHENTICATED, {**UNAUTHENTICATED, "GRAFANA_USERNAME": "test-person"}])
def test_missing_or_incomplete_auth_never_calls_network(env):
    transport = Transport()
    code, result, _ = invoke(DASHBOARD, transport, env)
    assert code == 2 and result["error"] == "authentication_unavailable"
    assert not transport.requests


@pytest.mark.parametrize("args", [
    ["dashboard", "--uid", "../other"], ["dashboard", "--uid", "ok", "--uid", "other"],
    ["dashboard", "--uid", "ok", "--url", "https://secret"],
    [*QUERY[:-1], "$__interval"], [*QUERY[:-1], "[[service]]"], [*QUERY[:-1], ""],
    ["query", "--datasource", "metrics-1", "--kind", "prometheus", "--from", "0", "--to", "86400001", "--expr", "up"],
    ["search"], ["search", "--query", 'edge"; x'], ["search", "--query", "   "], ["search", "--query", "x" * 101],
    ["search", "--query", "edge", "--query", "other"], ["alerts", "--folder-uid", "../other"], ["alerts", "--folder-uid", ""],
    ["alerts", "extra"], ["annotations", "--from", "0", "--to", "86400001"], ["annotations", "--from", "5", "--to", "5"],
    ["annotations", "--from", "0", "--to", "1000", "--dashboard-uid", "a/b"], ["silences", "--uid", "board"],
])
def test_parser_rejects_unsafe_input_without_echo(args, capsys):
    with pytest.raises(reader.SafeError):
        reader.parse_args(args)
    assert capsys.readouterr() == ("", "")


def test_literal_regex_anchor_is_not_an_unresolved_grafana_variable():
    expression = 'up{job=~"checkout$"}'
    assert reader.parse_args([*QUERY[:-1], expression]).expr == expression


def _request_probe(tmp_path):
    # The disposable entry point injects only a fake HTTP transport. It exercises
    # the real shell -> Python argv -> parser -> request-body construction seam.
    probe = tmp_path / "request_probe.py"
    probe.write_text(
        "import json, runpy, sys\n"
        f"helper = runpy.run_path({str(PATH)!r})\n"
        "def transport(request):\n"
        "    if request.full_url.endswith('/api/org'): payload = {'id': 7}\n"
        "    elif '/api/datasources/uid/' in request.full_url: payload = {'uid':'metrics-1','type':'prometheus','orgId':7}\n"
        "    else: payload = {'results': {'A': {'frames': [json.loads(request.data)['queries'][0]]}}}\n"
        "    return 200, json.dumps(payload).encode()\n"
        f"raise SystemExit(helper['main'](sys.argv[1:], environ={ENV!r}, transport=transport))\n"
    )
    return probe


@pytest.mark.parametrize("shell", ["powershell.exe", "pwsh"])
@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows argument transfer")
@pytest.mark.parametrize("expression", ['{service="edge"} |= "error"', 'up{job=~"checkout$"}', 'up{job="caf\u00e9"}'])
def test_native_powershell_preserves_expression_into_request_body(tmp_path, shell, expression):
    executable = shutil.which(shell)
    if not executable:
        pytest.skip(f"{shell} unavailable")
    probe = _request_probe(tmp_path)
    # The shim only substitutes the offline entrypoint for the fixed Python
    # helper. The wrapper and actual native Python argv transfer are exercised.
    script = (
        f"function python {{ & '{sys.executable}' -I -S '{probe}' @($args[3..($args.Count-1)]) }}\n"
        f"& '{PATH.with_suffix('.ps1')}' -Datasource metrics-1 -Kind prometheus -From 1000 -To 61000 -Expr '" + expression + "'\nexit $LASTEXITCODE"
    )
    result = subprocess.run([executable, "-NoProfile", "-NonInteractive", "-EncodedCommand", base64.b64encode(script.encode("utf-16le")).decode()],
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["results"]["A"]["frames"][0]["expr"] == expression


@pytest.mark.parametrize("expression", ['{service="edge"} |= "error"', 'up{job=~"checkout$"}'])
def test_native_bash_preserves_expression_into_request_body(tmp_path, expression):
    executable = require_shell("bash")  # Git Bash on Windows, never System32's WSL launcher
    probe = _request_probe(tmp_path)
    command = " ".join(shlex.quote(value) for value in [Path(sys.executable).as_posix(), "-I", "-S", probe.as_posix(), *QUERY[:-1], expression])
    result = subprocess.run([executable, "--noprofile", "--norc", "-c", command],
                            env={**os.environ, "BASH_ENV": ""}, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["results"]["A"]["frames"][0]["expr"] == expression


@pytest.mark.parametrize("shell", ["powershell.exe", "pwsh"])
@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows wrapper status")
@pytest.mark.parametrize("failure", ["launch", "helper"])
def test_powershell_wrapper_returns_static_launch_failure_or_helper_exit(tmp_path, shell, failure):
    executable = shutil.which(shell)
    if not executable:
        pytest.skip(f"{shell} unavailable")
    probe = _request_probe(tmp_path)
    shim = "throw 'synthetic-secret-launch-error'" if failure == "launch" else f"& '{sys.executable}' -I -S '{probe}' dashboard --uid ../invalid"
    script = (
        f"function python {{ {shim} }}\n"
        f"& '{PATH.with_suffix('.ps1')}' -Datasource metrics-1 -Kind prometheus -From 1000 -To 61000 -Expr 'up'\nexit $LASTEXITCODE"
    )
    result = subprocess.run([executable, "-NoProfile", "-NonInteractive", "-EncodedCommand", base64.b64encode(script.encode("utf-16le")).decode()],
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 2
    assert json.loads(result.stdout) == {"ok": False, "error": "helper_launch_failed" if failure == "launch" else "invalid_arguments"}
    assert "synthetic-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize("expression", ['{service="edge"} |= "error"', 'up{job=~"checkout$"}', 'up{job="caf\u00e9"}'])
def test_base64_preserves_exact_utf8_expression(expression):
    encoded = base64.b64encode(expression.encode()).decode()
    assert reader.parse_args([*QUERY[:-2], "--expr-base64", encoded]).expr == expression


@pytest.mark.parametrize("encoded", ["!", "dXA", "dXA=\n", "dXB=", "/w==", "", "QQ==" * 22000,
                                     base64.b64encode(b"$__interval").decode(), base64.b64encode(b"up\n").decode()],
                         ids=["alphabet", "padding", "whitespace", "noncanonical", "invalid_utf8", "empty", "oversized", "template", "control"])
def test_encoded_expression_keeps_validation_and_static_errors(encoded):
    transport = Transport()
    code, result, _ = invoke([*QUERY[:-2], "--expr-base64", encoded], transport)
    assert code == 2 and not result["ok"] and not transport.requests
