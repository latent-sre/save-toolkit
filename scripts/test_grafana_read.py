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
RENDER = ["render", "--uid", "board", "--panel", "7", "--from", "1000", "--to", "61000"]
PNG = bytes((137, 80, 78, 71, 13, 10, 26, 10)) + (13).to_bytes(4, "big") + b"IHDR" + (1200).to_bytes(4, "big") + (600).to_bytes(4, "big") + bytes(5)
# Grafana v13.2.2 public/img/rendering_limit_dark.png is 526x202, served with HTTP 200 at its concurrency limit.
PLACEHOLDER = PNG[:16] + (526).to_bytes(4, "big") + (202).to_bytes(4, "big") + bytes(5)
BOARD = {"dashboard": {"uid": "board", "version": 3, "panels": [
    {"id": 1, "type": "row", "collapsed": True, "panels": [{"id": 7, "type": "timeseries", "title": "B70 temperatures"}]}]},
    "meta": {"slug": "cylon-ai"}}

SILENCE_ID = "12345678-1234-1234-1234-123456789abc"


class Transport:
    def __init__(self, *responses, org_response=None):
        self.responses = [(200, {"id": 7}) if org_response is None else org_response, *responses]
        self.requests = []
        self.bounds = []

    def __call__(self, request, **bounds):
        self.requests.append(request)
        self.bounds.append(bounds)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        status, payload = response
        return status, payload if isinstance(payload, bytes) else json.dumps(payload).encode()


def invoke(args, transport, env=None):
    output = io.StringIO()
    code = reader.main(args, environ=ENV if env is None else env, transport=transport, output=output)
    return code, json.loads(output.getvalue()), output.getvalue()


def test_selected_dashboard_panel_preserves_configuration_and_context():
    board = json.loads(json.dumps(BOARD))
    context = {"title": "Operations", "time": {"from": "now-1h", "to": "now"}, "timezone": "browser",
               "templating": {"list": [{"name": "region", "current": {"value": "west"}}]}}
    board["dashboard"].update(context)
    panel = board["dashboard"]["panels"][0]["panels"][0]
    panel.update({"datasource": {"uid": "$source"}, "targets": [{"expr": "up{region=\"$region\"}"}],
                  "transformations": [{"id": "reduce"}], "description": "test-secret-token"})
    transport = Transport((200, board))
    code, result, text = invoke([*DASHBOARD, "--panel", "7"], transport)
    assert code == 0 and result["coverage"] == "configuration_only"
    assert result["dashboard"] == {"uid": "board", "version": 3, **context}
    assert result["panel_id"] == 7 and result["panel"] == {**panel, "description": "[REDACTED]"}
    assert "test-secret-token" not in text
    assert len(transport.requests) == 2 and all(request.method == "GET" for request in transport.requests)


@pytest.mark.parametrize("panels,error", [
    (None, "invalid_panel_tree"), ([None], "invalid_panel_tree"),
    ([{"id": True, "type": "timeseries"}], "invalid_panel_tree"),
    ([{"id": 7, "type": "timeseries", "panels": []}], "invalid_panel_tree"),
    ([{"id": 1, "type": "row", "panels": {}}], "invalid_panel_tree"),
    ([{"id": 7, "type": "timeseries"}, {"id": 7, "type": "timeseries"}], "ambiguous_panel_id"),
    ([{"id": 7, "type": "timeseries"}, {"id": 1, "type": "row", "panels": [{"id": 7, "type": "timeseries"}]}], "ambiguous_panel_id"),
    ([{"id": 7, "type": "row", "panels": []}], "panel_not_found"), ([], "panel_not_found"),
])
@pytest.mark.parametrize("command", [[*DASHBOARD, "--panel", "7"], RENDER])
def test_panel_selection_rejects_malformed_ambiguous_or_missing_panels(panels, error, command):
    transport = Transport((200, {"dashboard": {"uid": "board", "panels": panels}, "meta": {}}))
    code, result, _ = invoke(command, transport)
    assert code == 2 and result["error"] == error and len(transport.requests) == 2


@pytest.mark.parametrize("model", [{"elements": {}, "layout": {}}, {"kind": "Dashboard", "spec": {} }])
def test_selected_panel_explicitly_refuses_v2(model):
    transport = Transport((200, {"dashboard": {"uid": "board", "panels": [], **model}, "meta": {}}))
    assert invoke([*DASHBOARD, "--panel", "7"], transport)[1]["error"] == "unsupported_dashboard_model"


def test_full_dashboard_still_returns_uninterpreted_model_and_metadata():
    board = {"dashboard": {"uid": "board", "elements": {}, "layout": {}}, "meta": {"slug": "board"}}
    code, result, _ = invoke(DASHBOARD, Transport((200, board)))
    assert code == 0 and result["dashboard"] == board["dashboard"] and result["meta"] == board["meta"]
    assert "panel" not in result


@pytest.mark.parametrize("page,count,next_page", [(1, 0, None), (2, 99, None), (2, 100, 3), (100, 100, None)])
def test_search_page_and_filters_are_bounded_and_permission_scoped(page, count, next_page):
    items = [{"uid": f"b{n}", "folderUid": "payments", "title": "test-secret-token"} for n in range(count)]
    transport = Transport((200, items))
    code, result, text = invoke(["search", "--query", "checkout latency", "--page", str(page),
                                 "--folder-uid", "payments", "--tag", "team ops"], transport)
    assert code == 0 and result["page"] == page and result["next_page"] == next_page
    assert result["truncated"] == (count == 100) and result["coverage"] == "permission_scoped"
    assert result["limits"] == {"limit": 100, "maxPage": 100}
    assert "test-secret-token" not in text
    assert transport.requests[-1].full_url.endswith(
        f"/api/search?type=dash-db&limit=100&query=checkout%20latency&page={page}&folderUIDs=payments&tag=team%20ops")
    assert len(transport.requests) == 2 and transport.requests[-1].method == "GET"


@pytest.mark.parametrize("items,error", [([{"uid": "board", "folderUid": "other"}], "folder_mismatch"),
    ([{"uid": "board"}], "folder_mismatch"), ([{"uid": "board", "folderUid": "payments"}] * 101, "invalid_search_response")])
def test_search_refuses_wrong_folder_and_server_limit_violation(items, error):
    code, result, _ = invoke(["search", "--query", "edge", "--folder-uid", "payments"], Transport((200, items)))
    assert code == 2 and result["error"] == error


@pytest.mark.parametrize("args,payload,path,key,coverage", [
    (["alerts", "--uid", "rule-1"], {"uid": "rule-1", "orgID": 7, "title": "test-secret-token"},
     "/api/v1/provisioning/alert-rules/rule-1", "rule", "configuration_only"),
    (["silences", "--id", SILENCE_ID], {"id": SILENCE_ID, "comment": "test-secret-token"},
     "/api/alertmanager/grafana/api/v2/silence/" + SILENCE_ID, "silence", "permission_scoped"),
])
def test_exact_alert_and_silence_reads_are_get_only_and_masked(args, payload, path, key, coverage):
    transport = Transport((200, payload))
    code, result, text = invoke(args, transport)
    assert code == 0 and result["coverage"] == coverage and key in result
    assert "test-secret-token" not in text and len(transport.requests) == 2
    assert transport.requests[-1].full_url == ENV["GRAFANA_URL"] + path
    assert all(request.method == "GET" and request.data is None for request in transport.requests)


@pytest.mark.parametrize("payload,error", [({}, "alert_rule_mismatch"), ({"uid": "other"}, "alert_rule_mismatch"),
    ({"uid": "rule-1", "orgID": 2}, "organization_mismatch"),
    ({"uid": "rule-1", "orgID": "7"}, "organization_mismatch"),
    ({"uid": "rule-1", "orgID": True}, "organization_mismatch"),
    ({"uid": "rule-1", "orgID": None}, "organization_mismatch")])
def test_exact_alert_rule_rejects_wrong_identity_and_organization(payload, error):
    code, result, _ = invoke(["alerts", "--uid", "rule-1"], Transport((200, payload)))
    assert code == 2 and result["error"] == error


def test_exact_alert_rule_organization_field_is_optional_after_org_preflight():
    payload = {"uid": "rule-1", "condition": "C", "data": [{"refId": "C", "model": {"expr": "up"}}]}
    code, result, _ = invoke(["alerts", "--uid", "rule-1"], Transport((200, payload)))
    assert code == 0 and result["rule"] == payload and result["organization_id"] == 7


@pytest.mark.parametrize("args", [[*DASHBOARD, "--panel", "7"], ["search", "--query", "x", "--page", "2"],
                                  ["alerts", "--uid", "rule-1"], ["silences", "--id", SILENCE_ID]])
@pytest.mark.parametrize("response,error", [((403, b"test-secret-token"), "http_error"),
    ((200, b" " * (reader.MAX_RESPONSE + 1)), "response_too_large")])
def test_new_read_options_preserve_http_and_response_bounds(args, response, error):
    code, result, text = invoke(args, Transport(response))
    assert code == 2 and result["error"] == error and "test-secret-token" not in text


@pytest.mark.parametrize("payload", [{}, {"id": "other"}, {"id": 7}])
def test_exact_silence_rejects_wrong_identity(payload):
    code, result, _ = invoke(["silences", "--id", SILENCE_ID], Transport((200, payload)))
    assert code == 2 and result["error"] == "silence_mismatch"


@pytest.mark.parametrize("args", [
    [*DASHBOARD, "--panel", "0"], [*DASHBOARD, "--panel", "2147483648"], [*DASHBOARD, "--panel=7"],
    [*DASHBOARD, "--panel", "7", "--panel", "7"], [*DASHBOARD, "--pan", "7"],
    ["search", "--query", "x", "--page", "0"], ["search", "--query", "x", "--page", "101"],
    ["search", "--query", "x", "--page", "1", "--page", "2"], ["search", "--query", "x", "--page=1"],
    ["search", "--query", "x", "--tag", ""], ["search", "--query", "x", "--tag", "  "],
    ["search", "--query", "x", "--tag", "a&b"], ["search", "--query", "x", "--tag", "x" * 101],
    ["search", "--query", "x", "--folder-uid", "../folder"],
    ["alerts", "--uid", "rule", "--folder-uid", "folder"], ["alerts", "--uid", "../rule"],
    ["alerts", "--uid", "rule", "--uid", "other"], ["alerts", "--uid=rule"],
    ["silences", "--id", "../silence"], ["silences", "--id", "123"],
    ["silences", "--id", SILENCE_ID, "--id", SILENCE_ID], ["silences", "--id=" + SILENCE_ID],
])
def test_new_read_options_reject_invalid_grammar_before_authentication(args):
    transport = Transport()
    code, result, _ = invoke(args, transport)
    assert code == 2 and result["error"] == "invalid_arguments" and not transport.requests


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


def query_frame(times, values=None, *, name="Value", labels=None):
    fields = [{"name": "Time", "type": "time"}]
    columns = [times]
    if values is not None:
        fields.append({"name": name, "type": "number", "labels": labels or {}})
        columns.append(values)
    return {"schema": {"fields": fields}, "data": {"values": columns}}


def invoke_query_frames(frames, options=(), *, kind="prometheus", extra=None):
    args = list(QUERY)
    args[4] = kind
    transport = Transport((200, {"uid": "metrics-1", "type": kind}),
                          (200, {"results": {"A": {"frames": frames, **(extra or {})}}}))
    code, result, text = invoke([*args, *options], transport)
    return code, result, text, transport


@pytest.mark.parametrize("kind", ["prometheus", "loki"])
def test_instant_query_explicitly_evaluates_at_window_end(kind):
    code, result, _, transport = invoke_query_frames([query_frame([61000], [0])], ["--mode", "instant"], kind=kind)
    assert code == 0 and result["mode"] == "instant" and result["evaluation_time_ms"] == 61000
    body = json.loads(transport.requests[-1].data)
    assert body["from"] == "1000" and body["to"] == "61000"
    query = body["queries"][0]
    if kind == "prometheus":
        assert query["instant"] is True and query["range"] is False
    else:
        assert query["queryType"] == "instant"
    assert result["summary"]["instant_timestamp_mismatch"] is False


@pytest.mark.parametrize("values,state,minimum,maximum,last,finite,nulls", [
    ([], "empty", None, None, None, 0, 0), ([None, None], "all_null", None, None, None, 0, 2),
    ([0, 0], "values", 0, 0, 0, 2, 0), ([8, 3, None], "values", 3, 8, None, 2, 1),
])
def test_summary_distinguishes_empty_null_zero_and_trailing_null(values, state, minimum, maximum, last, finite, nulls):
    frame = query_frame([1000 + n * 1000 for n in range(len(values))], values, labels={"job": "edge"})
    code, result, _, _ = invoke_query_frames([frame], ["--output", "summary"])
    assert code == 0 and "results" not in result and result["coverage"] == "not_established"
    summary = result["summary"]
    assert summary["status"] == "complete" and summary["row_count"] == len(values)
    assert summary["frame_count"] == 1 and summary["numeric_series_count"] == 1
    series = summary["series"][0]
    assert (series["state"], series["min"], series["max"], series["last"]) == (state, minimum, maximum, last)
    assert (series["finite_count"], series["null_count"], series["labels"]) == (finite, nulls, {"job": "edge"})
    assert series["maxDataPoints_exceeded"] is False


def test_summary_reports_backend_exceeding_point_hint_and_window_without_dropping_full_data():
    frame = query_frame([400 + 61 * n for n in range(1002)], list(range(1002)))
    code, result, _, _ = invoke_query_frames([frame])
    assert code == 0 and result["results"]["A"]["frames"] == [frame]
    summary = result["summary"]
    assert summary["row_count"] == 1002 and summary["timestamp_min_ms"] == 400 and summary["timestamp_max_ms"] == 61461
    assert summary["out_of_window"] is True and summary["series"][0]["maxDataPoints_exceeded"] is True
    assert result["limits"]["maxDataPoints"] == 1000 and result["limits"]["maxDataPointsEnforced"] is False
    assert result["limits"]["maxResponseBytes"] == 2 * 1024 * 1024


@pytest.mark.parametrize("bad_frame", [{}, None, {"schema": {"fields": []}},
    {"schema": {"fields": [{"type": "number"}]}, "data": {"values": []}},
    {"schema": {"fields": [{"type": "time"}, {"type": "number"}]}, "data": {"values": [[1000], []]}}])
def test_unknown_frame_shape_is_not_reported_as_empty_success(bad_frame):
    code, result, _, _ = invoke_query_frames([bad_frame])
    assert code == 0 and result["results"]["A"]["frames"] == [bad_frame]
    summary = result["summary"]
    assert summary["status"] == "unsupported" and summary["row_count"] is None
    assert summary["numeric_series_count"] is None and summary["unsupported_frame_count"] == 1
    assert summary["out_of_window"] is None


@pytest.mark.parametrize("encoding,value", [
    ("entities", [None, {"NaN": [0]}]), ("entities", [None, {"Inf": [0], "NegInf": [1]}]),
    ("entities", [None, {"Undef": [0]}]), ("bases", [62000, 0]), ("factors", [1000, 1]),
    ("nanos", [[500000], []]), ("enums", [None, ["down", "up"]]),
])
@pytest.mark.parametrize("placeholder", [0, None])
def test_summary_does_not_treat_encoded_wire_placeholders_as_measurements(encoding, value, placeholder):
    frame = query_frame([1000], [placeholder])
    frame["data"][encoding] = value
    code, result, _, _ = invoke_query_frames([frame])
    assert code == 0 and result["results"]["A"]["frames"] == [frame]
    summary = result["summary"]
    assert summary["status"] == "unsupported" and summary["row_count"] is None and summary["numeric_series_count"] is None
    assert summary["series"] == [] and summary["out_of_window"] is None and summary["timestamp_min_ms"] is None


def test_empty_wire_encoding_containers_do_not_obscure_real_zero_measurement():
    frame = query_frame([1000], [0])
    frame["data"].update({"entities": {}, "bases": [], "factors": None, "nanos": []})
    code, result, _, _ = invoke_query_frames([frame])
    assert code == 0 and result["summary"]["status"] == "complete"
    assert result["summary"]["series"][0]["state"] == "values" and result["summary"]["series"][0]["min"] == 0


@pytest.mark.parametrize("format_type", ["numeric-long", "timeseries-long", None])
def test_summary_does_not_merge_row_labelled_clients_into_one_numeric_series(format_type):
    frame = query_frame([61000, 61000], [0, 100])
    frame["schema"]["fields"].append({"name": "client", "type": "string"})
    frame["data"]["values"].append(["client-a", "client-b"])
    if format_type:
        frame["schema"]["meta"] = {"type": format_type}
    code, result, _, _ = invoke_query_frames([frame], ["--mode", "instant"])
    assert code == 0 and result["results"]["A"]["frames"] == [frame]
    assert result["summary"]["status"] == "unsupported" and result["summary"]["numeric_series_count"] is None
    assert result["summary"]["series"] == []


@pytest.mark.parametrize("format_type", ["numeric-long", "timeseries-long"])
def test_long_frame_metadata_is_respected_even_without_string_label_columns(format_type):
    frame = query_frame([61000, 61000], [0, 100])
    frame["schema"]["meta"] = {"type": format_type}
    _, result, _, _ = invoke_query_frames([frame])
    assert result["summary"]["status"] == "unsupported"


def test_encoded_enum_fields_are_not_summarized_as_plain_rows():
    frame = query_frame([1000])
    frame["schema"]["fields"].append({"name": "state", "type": "enum", "config": {"type": {"enum": {"text": ["down", "up"]}}}})
    frame["data"]["values"].append([0])
    _, result, _, _ = invoke_query_frames([frame])
    assert result["summary"]["status"] == "unsupported" and result["summary"]["row_count"] is None


def test_summary_caps_details_but_preserves_accurate_counts_and_notices():
    frames = [query_frame([1000], [n]) for n in range(105)]
    frames[-1]["schema"]["meta"] = {"notices": [{"severity": "warning", "text": "Backend returned partial data"}]}
    code, result, _, _ = invoke_query_frames(frames, ["--output", "summary"])
    summary = result["summary"]
    assert code == 0 and summary["numeric_series_count"] == 105 and summary["row_count"] == 105
    assert len(summary["series"]) == 100 and summary["series_truncated"] is True
    assert summary["notices"][0]["notice"]["text"] == "Backend returned partial data"


def test_summary_continues_observations_past_detail_caps():
    frames = [query_frame([1000], [n]) for n in range(100)] + [query_frame([62000] * 1001, [0] * 1001)]
    notices = [{"severity": "warning", "text": f"notice {n}"} for n in range(101)]
    code, result, _, _ = invoke_query_frames(frames, ["--output", "summary"], extra={"notices": notices})
    summary = result["summary"]
    assert code == 0 and summary["row_count"] == 1101 and summary["numeric_series_count"] == 101
    assert summary["series_over_point_hint"] == 1 and summary["out_of_window"] is True
    assert summary["series_truncated"] is True and summary["notices_truncated"] is True
    assert len(summary["notices"]) == 100 and summary["notice_count"] == 101


def test_empty_query_result_is_distinct_from_an_unsupported_frame():
    code, result, _, _ = invoke_query_frames([], ["--output", "summary"])
    summary = result["summary"]
    assert code == 0 and summary["status"] == "complete" and summary["frame_count"] == 0
    assert summary["row_count"] == summary["numeric_series_count"] == 0 and summary["out_of_window"] is None


def test_mixed_known_and_unknown_frames_retain_observed_counts_without_claiming_totals():
    code, result, _, _ = invoke_query_frames([query_frame([1000], [0]), {}])
    summary = result["summary"]
    assert code == 0 and summary["status"] == "partial" and summary["row_count"] is None
    assert summary["observed_row_count"] == summary["observed_numeric_series_count"] == 1
    assert summary["timestamp_min_ms"] == 1000 and summary["timestamp_status"] == "partial"
    assert summary["out_of_window"] is None


@pytest.mark.parametrize("values", [["NaN", 0], [True, 0], [{"unknown": 1}, 0]])
def test_unsupported_numeric_values_remain_explicitly_partial(values):
    code, result, _, _ = invoke_query_frames([query_frame([1000, 2000], values)])
    summary = result["summary"]
    series = summary["series"][0]
    assert code == 0 and summary["status"] == "partial" and series["state"] == "unsupported"
    assert series["invalid_count"] == 1 and series["finite_count"] == 1 and series["min"] == series["max"] == 0


def test_missing_timestamps_remain_unknown_and_instant_misalignment_is_observed():
    frame = {"schema": {"fields": [{"name": "value", "type": "number"}]}, "data": {"values": [[1, 2]]}}
    _, result, _, _ = invoke_query_frames([frame], ["--mode", "instant"])
    assert result["summary"]["out_of_window"] is None and result["summary"]["instant_timestamp_mismatch"] is None
    _, result, _, _ = invoke_query_frames([query_frame([60000, None], [1, 2])], ["--mode", "instant"])
    summary = result["summary"]
    assert summary["instant_timestamp_mismatch"] is True and summary["timestamp_invalid_count"] == 1
    assert summary["status"] == "partial" and summary["out_of_window"] is None


def test_log_summary_observes_rows_and_times_without_outputting_log_lines():
    frame = query_frame([900, 62000])
    frame["schema"]["fields"].append({"name": "Line", "type": "string"})
    frame["data"]["values"].append(["private-log-one", "private-log-two"])
    code, result, text, _ = invoke_query_frames([frame], ["--output", "summary"], kind="loki")
    assert code == 0 and "private-log" not in text
    summary = result["summary"]
    assert summary["row_count"] == 2 and summary["numeric_series_count"] == 0
    assert summary["timestamp_min_ms"] == 900 and summary["timestamp_max_ms"] == 62000 and summary["out_of_window"] is True


def test_log_only_frames_exceeding_point_hint_have_an_observed_warning():
    frame = query_frame([1000] * 1002)
    frame["schema"]["fields"].append({"name": "Line", "type": "string"})
    frame["data"]["values"].append(["private log"] * 1002)
    code, result, text, _ = invoke_query_frames([frame], ["--output", "summary"], kind="loki")
    summary = result["summary"]
    assert code == 0 and "private log" not in text and summary["status"] == "complete"
    assert summary["row_count"] == 1002 and summary["numeric_series_count"] == 0
    assert summary["frames_over_point_hint"] == 1 and summary["series_over_point_hint"] == 0
    assert "observed_frames_exceed_requested_point_hint" in summary["warnings"]


def test_query_macros_are_resolved_before_request_and_receipt_records_exact_substitutions():
    expr = "$__range ${__range_s} $__range_ms $__interval ${__interval_ms} $__rate_interval"
    transport = Transport((200, {"uid": "metrics-1", "type": "prometheus"}), (200, {"results": {"A": {"frames": []}}}))
    code, result, _ = invoke([*QUERY[:-1], expr, "--interval-ms", "2000", "--rate-interval-ms", "15000"], transport)
    assert code == 0
    assert result["expression"] == {"original": expr, "resolved": "60s 60 60000 2000ms 2000 15000ms", "substitutions": {
        "$__range": "60s", "${__range_s}": "60", "$__range_ms": "60000", "$__interval": "2000ms",
        "${__interval_ms}": "2000", "$__rate_interval": "15000ms"}}
    query = json.loads(transport.requests[-1].data)["queries"][0]
    assert query["expr"] == result["expression"]["resolved"] and query["intervalMs"] == 2000


def test_fractional_range_macro_and_base64_transport_preserve_exact_window():
    args = list(QUERY)
    args[8] = "61001"
    expr = "$__range + $__range_s + ${__range_ms}"
    args[-2:] = ["--expr-base64", base64.b64encode(expr.encode()).decode()]
    transport = Transport((200, {"uid": "metrics-1", "type": "prometheus"}), (200, {"results": {"A": {"frames": []}}}))
    code, result, _ = invoke(args, transport)
    assert code == 0 and result["expression"]["original"] == expr
    assert result["expression"]["resolved"] == "60001ms + 60.001 + 60001"


def test_explicit_intervals_cannot_increase_request_density_or_guess_loki_scrape_rate():
    args = list(QUERY)
    args[8] = "86401000"
    transport = Transport()
    assert invoke([*args, "--interval-ms", "1000"], transport)[0] == 2 and not transport.requests
    args = list(QUERY)
    args[4] = "loki"
    assert invoke([*args, "--rate-interval-ms", "2000"], transport)[0] == 2 and not transport.requests


def test_expression_receipt_and_summary_mask_authentication_values():
    expr = 'up{job="test-secret-token"}'
    frame = query_frame([1000], [0], name="test-secret-token", labels={"job": "test-secret-token"})
    transport = Transport((200, {"uid": "metrics-1", "type": "prometheus"}), (200, {"results": {"A": {"frames": [frame]}}}))
    code, result, text = invoke([*QUERY[:-1], expr, "--output", "summary"], transport)
    assert code == 0 and "test-secret-token" not in text
    assert result["expression"]["original"] == result["expression"]["resolved"] == 'up{job="[REDACTED]"}'


@pytest.mark.parametrize("expr,options", [("$__range_bad", []), ("${__range:raw}", []), ("$service", []),
    ("$__interval", []), ("$__interval_ms", []), ("$__rate_interval", []), ("[[service]]", []),
    ("$__interval_bad", ["--interval-ms", "2000"]), ("${__rate_interval_bad}", ["--rate-interval-ms", "2000"])])
def test_unknown_or_unconfigured_macros_are_refused_before_authentication(expr, options):
    transport = Transport()
    code, result, _ = invoke([*QUERY[:-1], expr, *options], transport)
    assert code == 2 and result["error"] == "unresolved_or_invalid_expression" and not transport.requests


@pytest.mark.parametrize("options", [["--mode", "wrong"], ["--output", "wrong"], ["--interval-ms", "999"],
    ["--interval-ms", "86400001"], ["--rate-interval-ms", "999"], ["--rate-interval-ms", "86400001"],
    ["--mode=instant"], ["--mode", "instant", "--mode", "range"], ["--inter", "2000"]])
def test_query_new_option_grammar_and_bounds_fail_before_authentication(options):
    transport = Transport()
    assert invoke([*QUERY, *options], transport)[0] == 2 and not transport.requests


@pytest.mark.parametrize("width,height", [(400, 200), (2400, 1600), (1600, 900)])
def test_render_uses_and_verifies_requested_dimensions(capture_dir, width, height):
    png = PNG[:16] + width.to_bytes(4, "big") + height.to_bytes(4, "big") + PNG[24:]
    transport = Transport((200, BOARD), (200, png))
    code, result, _ = invoke([*RENDER, "--width", str(width), "--height", str(height)], transport)
    assert code == 0 and (result["width"], result["height"]) == (width, height)
    assert f"&width={width}&height={height}&" in transport.requests[-1].full_url
    assert result["limits"]["minWidth"] == 400 and result["limits"]["maxHeight"] == 1600


def test_render_refuses_valid_png_with_wrong_requested_dimensions(capture_dir):
    transport = Transport((200, BOARD), (200, PNG))
    code, result, _ = invoke([*RENDER, "--width", "1600"], transport)
    assert code == 2 and result["error"] == "renderer_placeholder" and not list(capture_dir.iterdir())


def test_render_refuses_known_placeholder_even_if_requested_dimensions_match(capture_dir):
    transport = Transport((200, BOARD), (200, PLACEHOLDER))
    code, result, _ = invoke([*RENDER, "--width", "526", "--height", "202"], transport)
    assert code == 2 and result["error"] == "renderer_placeholder" and not list(capture_dir.iterdir())


@pytest.mark.parametrize("options", [["--width", "399"], ["--width", "2401"], ["--height", "199"],
    ["--height", "1601"], ["--width=1600"], ["--wid", "1600"], ["--height", "900", "--height", "1000"]])
def test_render_dimensions_reject_invalid_bounds_and_grammar(options):
    transport = Transport()
    assert invoke([*RENDER, *options], transport)[0] == 2 and not transport.requests


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


@pytest.fixture
def capture_dir(monkeypatch, tmp_path):
    captures = tmp_path / "captures"
    captures.mkdir()
    monkeypatch.setattr(reader, "_render_dir", lambda: captures)
    return captures


REAL_RENDER_DIR = reader._render_dir


def test_renders_go_to_a_per_user_directory_that_drops_day_old_images(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("TMPDIR", str(tmp_path / "workspace"))
    monkeypatch.setenv("TEMP", str(tmp_path / "workspace"))
    target = tmp_path / ".cache" / "save-toolkit" / "grafana-renders"
    target.mkdir(parents=True)
    old, fresh, other = target / "grafana-render-old.png", target / "grafana-render-new.png", target / "notes.txt"
    for path in (old, fresh, other):
        path.write_bytes(b"x")
    os.utime(old, (1, 1))
    assert REAL_RENDER_DIR() == target and not (tmp_path / "workspace").exists()
    assert not old.exists() and fresh.exists() and other.exists()


def test_relative_home_never_selects_a_workspace_render_directory(monkeypatch):
    monkeypatch.setenv("HOME", "relative-home")
    monkeypatch.setenv("USERPROFILE", "relative-home")
    with pytest.raises(reader.SafeError, match="capture_directory_unavailable"):
        REAL_RENDER_DIR()


def test_render_fails_rather_than_report_a_masked_image_path(capture_dir):
    env = {"GRAFANA_URL": ENV["GRAFANA_URL"], "GRAFANA_ORG_ID": "7", "GRAFANA_USERNAME": "captures",
           "GRAFANA_PASSWORD": "private-pass"}
    code, result, _ = invoke(RENDER, Transport((200, BOARD), (200, PNG)), env)
    assert code == 2 and result["error"] == "image_path_masked"
    assert not list(capture_dir.iterdir())


def test_render_checks_the_panel_then_saves_one_bounded_png(capture_dir):
    transport = Transport((200, BOARD), (200, PNG))
    code, result, _ = invoke([*RENDER, "--var", "host=host-a", "--var", "host=host-b"], transport)
    assert code == 0 and result["operation"] == "render" and result["coverage"] == "image_uninspected"
    assert [r.full_url for r in transport.requests[1:]] == [
        ENV["GRAFANA_URL"] + "/api/dashboards/uid/board",
        ENV["GRAFANA_URL"] + "/render/d-solo/board/cylon-ai?orgId=7&panelId=7&from=1000&to=61000&width=1200"
        "&height=600&scale=1&tz=UTC&timeout=40&var-host=host-a&var-host=host-b"]
    assert transport.requests[2].method == "GET" and transport.bounds[2] == {"limit": 8 * 1024 * 1024, "timeout": 45}
    saved = Path(result["image_path"])
    assert saved.parent == capture_dir and saved.read_bytes() == PNG
    assert (result["width"], result["height"], result["panel_title"]) == (1200, 600, "B70 temperatures")


def test_render_encoded_scalar_preserves_literal_paths_quotes_and_repeated_order(capture_dir):
    value = 'host=node.example/path "quoted" & other=value'
    encoded = base64.b64encode(value.encode()).decode()
    transport = Transport((200, BOARD), (200, PNG))
    code, result, _ = invoke([*RENDER, '--var', 'host=first', '--var-base64', encoded,
                              '--var', 'host=last'], transport)
    assert code == 0
    assert result['variables'] == ['host=first', value, 'host=last']
    assert transport.requests[-1].full_url.endswith(
        '&var-host=first&var-host=node.example%2Fpath+%22quoted%22+%26+other%3Dvalue&var-host=last')


@pytest.mark.parametrize('raw', [b'host=', b'=value', b'bad name=value', b'host=a\nline',
                                 b'host=\x7f', b'host=\xff', b'host=' + b'a' * 101])
def test_render_encoded_variable_rejects_invalid_values_before_network(raw):
    transport = Transport()
    code, result, _ = invoke([*RENDER, '--var-base64', base64.b64encode(raw).decode()], transport)
    assert code == 2 and result['error'] == 'invalid_arguments'
    assert not transport.requests


@pytest.mark.parametrize('encoded', ['!', 'aG9zdD14===', 'aG9zdD14\n', 'a' * 625])
def test_render_encoded_variable_requires_canonical_bounded_base64(encoded):
    with pytest.raises(reader.SafeError, match='invalid_arguments'):
        reader.parse_args([*RENDER, '--var-base64', encoded])


def test_render_variable_budget_is_shared_across_transports():
    encoded = base64.b64encode(b'host=a/b').decode()
    with pytest.raises(reader.SafeError, match='invalid_arguments'):
        reader.parse_args([*RENDER, *['--var', 'host=a'] * 5, '--var-base64', encoded])
    assert len(reader.parse_args([*RENDER, *['--var-base64', encoded] * 5]).variables) == 5


@pytest.mark.parametrize("panel", ["1", "99"], ids=["row", "absent"])
def test_render_refuses_rows_and_unknown_panels_before_rendering(capture_dir, panel):
    transport = Transport((200, BOARD))
    code, result, _ = invoke([*RENDER[:4], panel, *RENDER[5:]], transport)
    assert code == 2 and result["error"] == "panel_not_found" and len(transport.requests) == 2
    assert not list(capture_dir.iterdir())


@pytest.mark.parametrize("response,error", [((200, b"<html>login</html>"), "invalid_image"), ((429, b""), "renderer_busy"),
                                            ((200, PLACEHOLDER), "renderer_placeholder"),
                                            ((302, b""), "redirect_rejected"), ((200, PNG + bytes(8 * 1024 * 1024)), "response_too_large")])
def test_render_failures_save_nothing(capture_dir, response, error):
    code, result, _ = invoke(RENDER, Transport((200, BOARD), response))
    assert code == 2 and result["error"] == error
    assert not list(capture_dir.iterdir())


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


def test_settings_file_is_checked_and_read_through_one_open(monkeypatch, tmp_path):
    use_settings(monkeypatch, tmp_path, SETTINGS_TEXT)
    def resolved_again(*args, **kwargs):
        raise AssertionError("path resolved again after it was opened")
    monkeypatch.setattr(Path, "stat", resolved_again)
    monkeypatch.setattr(Path, "read_bytes", resolved_again)
    transport = Transport((200, {"dashboard": {"uid": "board"}, "meta": {}}))
    assert invoke(["dashboard", "--uid", "board"], transport, {})[0] == 0


@pytest.mark.skipif(os.name != "posix", reason="POSIX symlinks and O_NOFOLLOW")
def test_symlinked_settings_file_is_refused(monkeypatch, tmp_path):
    target = tmp_path / "elsewhere.env"
    target.write_text(SETTINGS_TEXT)
    target.chmod(0o600)
    link = tmp_path / "grafana.env"
    link.symlink_to(target)
    monkeypatch.setattr(reader, "_settings_file", lambda: link)
    transport = Transport()
    code, result, _ = invoke(["dashboard", "--uid", "board"], transport, {})
    assert code == 2 and result["error"] == "invalid_settings_file" and not transport.requests


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
    reader.http_transport(reader.Request("https://monitor.example"), limit=8 * 1024 * 1024, timeout=45)
    assert captured["timeout"] == 45 and captured["read_bound"] == 8 * 1024 * 1024 + 1


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
    [*RENDER[:-2], "--to", str(1000 + 7 * 86400000 + 1)], [*RENDER[:4], "0", *RENDER[5:]], [*RENDER[:4], "x", *RENDER[5:]],
    [*RENDER, "--var", "bad name=1"], [*RENDER, "--var", "host=a b"], [*RENDER, "--var", "host=$(id)"],
    [*RENDER, "--var", "host"], [*RENDER, *["--var", "host=a"] * 6], [*RENDER, "--uid", "other"],
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
