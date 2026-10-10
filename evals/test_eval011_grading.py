"""No-model regressions for the remaining EVAL-011 grading contracts."""

from __future__ import annotations

import contextlib
import copy
import http.client
import http.server
import json
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import pytest
from probe import assessment, backing, checking, fingerprints, rescoring, tracing, trials
from probe_testkit import ROOT, context, saved_grade, saved_summary, tiny_spec, write_saved_run


@pytest.mark.parametrize("minimum", [0, 1])
@pytest.mark.parametrize("cut", [False, True])
@pytest.mark.parametrize("raw", [False, True])
def test_tool_count_regrade_measures_recorded_attempts(tmp_path: Path, minimum: int, cut: bool, raw: bool) -> None:
    spec = tiny_spec(checks=[{"check": "tool_call_count", "tool": "Read", "minimum": minimum,
                              "maximum": 1, "text": "at most one read"}])
    grade = saved_grade(spec, [{"text": "at most one read", "passed": True, "evidence": "older count was zero"}])
    if cut:
        grade.update(run_end="cut_short", run_stop="wall_clock", inconclusive="timed out after 900s")
    events = [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": str(i), "name": "Read", "input": {"file_path": "README.md"}}
        for i in range(2)]}}]
    run = write_saved_run(tmp_path / "run", response="", grading=grade,
                          summary=saved_summary(tool_counts={"Read": 2}), events=events if raw else None)
    result = rescoring.regrade_run(run, spec, write=False)
    assert result["status"] == "FAIL"
    assert result["expectations"][0]["state"] == "FAIL"
    assert "2 attempted" in result["expectations"][0]["evidence"]
    assert "kept" not in result["expectations"][0]["evidence"]


@pytest.mark.parametrize(("counts", "state"), [(None, "INCONCLUSIVE"), ({}, "PASS"), ({"Read": 1}, "FAIL")])
def test_tool_count_regrade_does_not_invent_absent_summary_evidence(tmp_path: Path, counts: object, state: str) -> None:
    spec = tiny_spec(checks=[{"check": "tool_call_count", "tool": "Read", "minimum": 0,
                              "maximum": 0, "text": "no reads"}])
    grade = saved_grade(spec, [{"text": "no reads", "passed": True, "evidence": "old verdict"}])
    summary = saved_summary(**({"tool_counts": counts} if counts is not None else {}))
    run = write_saved_run(tmp_path / "run", response="", grading=grade, summary=summary)
    assert rescoring.regrade_run(run, spec, write=False)["status"] == state


COUNT_INIT = json.dumps({"type": "system", "subtype": "init", "tools": ["Read"]})
COUNT_RESULT = json.dumps({"type": "result", "subtype": "success", "result": "done"})
COUNT_READ = json.dumps({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "id": "r1", "name": "Read", "input": {"file_path": "README.md"}}]}})


@pytest.mark.parametrize("raw", ["", "{not json", '{"type":', '{}\n[]\n"noise"', COUNT_INIT,
                                 COUNT_RESULT, "\n".join([COUNT_INIT, "{broken", COUNT_RESULT])])
@pytest.mark.parametrize(("counts", "expected"), [(None, "INCONCLUSIVE"), ({}, "PASS"), ({"Read": 1}, "FAIL")])
def test_incomplete_raw_counts_use_summary_or_remain_unknown(tmp_path: Path, raw: str, counts: object, expected: str) -> None:
    spec = tiny_spec(checks=[{"check": "tool_call_count", "tool": "Read", "minimum": 0,
                              "maximum": 0, "text": "no reads"}])
    grade = saved_grade(spec, [{"text": "no reads", "passed": False, "evidence": "Read: 1 attempted call(s)"}])
    summary = saved_summary(**({"tool_counts": counts} if counts is not None else {}))
    run = write_saved_run(tmp_path / "run", response="done", grading=grade, summary=summary)
    (run / "stdout.jsonl").write_text(raw, encoding="utf-8")
    original = (run / "grading.json").read_bytes()
    result = rescoring.regrade_run(run, spec, write=False)
    assert result["status"] == expected
    assert (run / "grading.json").read_bytes() == original


@pytest.mark.parametrize("counts", [{"Read": True}, {"Read": -1}, {"Read": 1.0}, {"Read": "1"}, {"": 1}, [1]])
def test_summary_count_fallback_requires_nonnegative_integer_counts(tmp_path: Path, counts: object) -> None:
    spec = tiny_spec(checks=[{"check": "tool_call_count", "tool": "Write", "minimum": 0,
                              "maximum": 0, "text": "no writes"}])
    grade = saved_grade(spec, [{"text": "no writes", "passed": True, "evidence": "old verdict"}])
    run = write_saved_run(tmp_path / "run", response="", grading=grade,
                          summary=saved_summary(tool_counts=counts), events=[])
    assert rescoring.regrade_run(run, spec, write=False)["status"] == "INCONCLUSIVE"


@pytest.mark.parametrize(("raw", "counts", "maximum", "cut", "expected"), [
    ("\n".join([COUNT_INIT, COUNT_RESULT]), None, 0, False, "PASS"),
    ("\n".join([COUNT_INIT, COUNT_RESULT]), {"Read": 1}, 0, False, "PASS"),
    (COUNT_READ, None, 0, False, "FAIL"),
    ("\n".join([COUNT_INIT, "{broken", COUNT_READ, COUNT_RESULT]), None, 0, False, "FAIL"),
    ("\n".join([COUNT_INIT, "{broken", COUNT_READ, COUNT_RESULT]), None, 2, False, "INCONCLUSIVE"),
    (COUNT_READ, {}, 0, False, "FAIL"),
    (COUNT_READ, {}, 2, False, "INCONCLUSIVE"),
    (COUNT_INIT, {"Read": 1}, 0, True, "FAIL"),
    (COUNT_INIT, {"Read": 1}, 2, True, "INCONCLUSIVE"),
    ("\n".join([COUNT_INIT, COUNT_READ]), None, 0, True, "FAIL"),
    ("\n".join([COUNT_INIT, COUNT_READ]), None, 2, True, "INCONCLUSIVE"),
])
def test_raw_count_completeness_does_not_erase_supported_violations(
    tmp_path: Path, raw: str, counts: object, maximum: int, cut: bool, expected: str,
) -> None:
    spec = tiny_spec(checks=[{"check": "tool_call_count", "tool": "Read", "minimum": 0,
                              "maximum": maximum, "text": "bounded reads"}])
    grade = saved_grade(spec, [{"text": "bounded reads", "passed": True, "evidence": "old verdict"}])
    if cut:
        grade.update(run_end="cut_short", run_stop="wall_clock", inconclusive="timed out after 900s")
    run = write_saved_run(tmp_path / "run", response="done", grading=grade,
                          summary=saved_summary(**({"tool_counts": counts} if counts is not None else {})))
    (run / "stdout.jsonl").write_text(raw, encoding="utf-8")
    assert rescoring.regrade_run(run, spec, write=False)["status"] == expected


@pytest.mark.parametrize(("observed", "state"), [(False, "INCONCLUSIVE"), (True, "FAIL")])
def test_cut_raw_damage_keeps_absent_count_unknown_and_observed_violation(tmp_path: Path, observed: bool, state: str) -> None:
    spec = tiny_spec(checks=[{"check": "tool_call_count", "tool": "Read", "minimum": 0,
                              "maximum": 0, "text": "no reads"}])
    grade = saved_grade(spec, [{"text": "no reads", "passed": True, "evidence": "old verdict"}])
    grade.update(run_end="cut_short", run_stop="wall_clock", inconclusive="timed out after 900s")
    run = write_saved_run(tmp_path / "run", response="", grading=grade, summary=saved_summary())
    raw = [COUNT_INIT, *([COUNT_READ] if observed else []), "{broken"]
    (run / "stdout.jsonl").write_text("\n".join(raw), encoding="utf-8")
    result = rescoring.regrade_run(run, spec, write=False)
    assert result["status"] == state
    evidence = result["expectations"][0]["evidence"]
    assert "1 attempted" in evidence if observed else "0 attempted" not in evidence


@pytest.mark.parametrize(("found", "expected", "state"), [
    (True, 1, "FAIL"), (False, 0, "FAIL"), (1, True, "FAIL"), (0, False, "FAIL"),
    (True, True, "PASS"), (False, False, "PASS"), (3.0, 3, "PASS"), (3, 3.0, "PASS"),
    ({"values": [True]}, {"values": [1]}, "FAIL"), ({"values": [3.0]}, {"values": [3]}, "PASS"),
    ([1, 2], [2, 1], "FAIL"), ({"a": 1}, {"a": 1, "b": 2}, "FAIL"),
])
@pytest.mark.parametrize("kind", ["service_get", "service_array_item"])
def test_service_json_equality_preserves_json_boolean_type(found: object, expected: object, state: str, kind: str) -> None:
    ctx = context(tiny_spec(), services=[backing.Service("api", "image", "container", "http://127.0.0.1:1")])
    if kind == "service_get":
        payload = {"value": found}
        params = {"path": "/", "pointer": "value", "equals": expected}
    else:
        payload = {"items": [{"value": found}]}
        params = {"path": "/", "pointer": "items", "matches": [{"pointer": "value", "equals": expected}]}
    with mock.patch.object(backing, "request", return_value=(200, payload)):
        assert checking.CHECKS[kind](ctx, params).state == state


def _legacy_native_run(tmp_path: Path, *, followup: bool = False) -> tuple[Path, dict]:
    spec = tiny_spec(followups=["Continue"], helper="sre-assistant", expected_model="stub-model",
                     tools=["Skill", "Read", "Task"],
                     checks=[{"check": "tool_call_count", "tool": "Read", "minimum": 0,
                              "maximum": 0, "text": "no reads"}])
    timeout = "timed out after 900s"
    grade = saved_grade(spec, [{"text": label, "passed": False, "evidence": f"INCONCLUSIVE: {timeout}"}
                              for label in assessment.scenario_assertions(spec)])
    grade.update(status="INCONCLUSIVE", inconclusive=timeout)
    init = {"type": "system", "subtype": "init", "session_id": "s1", "model": "stub-model",
            "tools": spec["tools"], "plugins": [{"name": "save-toolkit", "path": str(ROOT)}], "mcp_servers": []}
    read = {"type": "assistant", "message": {"model": "stub-model", "content": [
        {"type": "tool_use", "id": "r1", "name": "Read", "input": {"file_path": "README.md"}}]}}
    complete = {"type": "result", "subtype": "success", "session_id": "s1", "result": "continuing",
                "total_cost_usd": 0.01, "num_turns": 1}
    run = write_saved_run(tmp_path / "run", response="", grading=grade,
                          summary=saved_summary(plugin={"plugin_root": str(ROOT),
                                                        "plugin_source_sha256": fingerprints.plugin_digest(ROOT)}),
                          events=[init, complete] if followup else [init, read])
    folders = [run]
    if followup:
        second = run / "followup"
        second.mkdir()
        (second / "stdout.jsonl").write_text("\n".join(json.dumps(e) for e in [init, read]), encoding="utf-8")
        folders.append(second)
    for index, folder in enumerate(folders):
        trace = tracing.parse_trace(folder / "stdout.jsonl")
        timed_out = not followup or index == 1
        (folder / "invocation.json").write_text(json.dumps({
            "argv": ["claude", "--agent", "save-toolkit:software-engineer"],
            "workspace": str(tmp_path / "workspace-gone"), "exit_code": None if timed_out else 0,
            "expected_model": "stub-model", "resume": "s1" if index else None,
            "session_id": trace.session_id, "main_models": trace.main_models,
            "init_session_ids": trace.init_session_ids, "inconclusive": timeout if timed_out else None,
        }), encoding="utf-8")
    return run, spec


@pytest.mark.parametrize("followup", [False, True])
def test_legacy_native_timeout_recovers_a_forbidden_action(tmp_path: Path, followup: bool) -> None:
    run, spec = _legacy_native_run(tmp_path, followup=followup)
    result = rescoring.regrade_run(run, spec, write=False)
    assert (result["status"], result.get("run_end"), result.get("run_stop")) == ("FAIL", "cut_short", "wall_clock")
    assert next(row for row in result["expectations"] if row["text"] == "no reads")["state"] == "FAIL"
    assert "void" not in result


@pytest.mark.parametrize("damage", ["digest-missing", "digest-drift", "root-missing", "trace", "tools", "model", "metadata",
                                    "pin", "stop", "explicit-void"])
def test_legacy_native_timeout_keeps_unproven_identity_void(tmp_path: Path, damage: str) -> None:
    run, spec = _legacy_native_run(tmp_path)
    metadata_path = run / "invocation.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if damage.startswith("digest") or damage == "root-missing":
        path = run / "outputs/trace-summary.json"
        summary = json.loads(path.read_text(encoding="utf-8"))
        if damage == "root-missing":
            summary["plugin"].pop("plugin_root")
        elif damage == "digest-missing":
            summary["plugin"].pop("plugin_source_sha256")
        else:
            summary["plugin"]["plugin_source_sha256"] = "0" * 64
        path.write_text(json.dumps(summary), encoding="utf-8")
    elif damage == "trace":
        (run / "stdout.jsonl").unlink()
    elif damage in ("tools", "model"):
        path = run / "stdout.jsonl"
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if damage == "tools":
            events[0]["tools"].append("Write")
        else:
            events[0]["model"] = "wrong-model"
        path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    elif damage == "metadata":
        metadata.pop("workspace")
    elif damage == "pin":
        metadata["argv"][-1] = "save-toolkit:researcher"
    elif damage == "stop":
        metadata["inconclusive"] = "unrecognized reason"
    else:
        metadata["cut_short"] = False
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    result = rescoring.regrade_run(run, spec, write=False)
    assert result["status"] == "INCONCLUSIVE"
    assert result.get("void")
    assert all(row["state"] == "INCONCLUSIVE" for row in result["expectations"])


def test_proxy_stops_admission_drains_inflight_and_keeps_backing_service(tmp_path: Path) -> None:
    admitted, release, stopped = threading.Event(), threading.Event(), threading.Event()

    class Upstream(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/slow":
                admitted.set()
                release.wait(10)
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    upstream = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    server_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    server_thread.start()
    service = backing.Service("api", "image", "container", f"http://127.0.0.1:{upstream.server_port}")
    backing._start_service_proxy(service)
    connection = http.client.HTTPConnection(service.agent_url.removeprefix("http://"), timeout=5)
    failure: list[Exception] = []

    def stop() -> None:
        try:
            backing.stop_proxies([service])
        except Exception as exc:
            failure.append(exc)
        finally:
            stopped.set()

    try:
        connection.request("GET", "/slow")
        assert admitted.wait(5)
        stop_thread = threading.Thread(target=stop, daemon=True)
        stop_thread.start()
        assert not stopped.wait(0.7), "a request is still in flight: grading cannot read the audit yet"
        release.set()
        response = connection.getresponse()
        assert response.will_close, "a persistent connection must not admit another request during grading"
        assert response.read() == b'{"ok": true}'
        assert stopped.wait(5)
        assert not failure
        assert service.requests == [{"method": "GET", "path": "/slow", "status": 200,
                                     "request": None, "response": {"ok": True}}]
        before = copy.deepcopy(service.requests)
        with pytest.raises((urllib.error.URLError, OSError)):
            urllib.request.urlopen(service.agent_url + "/late", timeout=1)
        assert backing.request(service, "/health") == (200, {"ok": True})
        assert service.requests == before
        backing.stop_proxies([service])  # final cleanup can repeat it without reopening admission
    finally:
        release.set()
        connection.close()
        service.proxy.shutdown()
        service.proxy.server_close()
        upstream.shutdown()
        upstream.server_close()


@pytest.mark.parametrize("settle_failure", [False, True])
def test_trial_settles_proxy_before_grading_and_preserves_independent_failure(tmp_path: Path, settle_failure: bool) -> None:
    events: list[str] = []

    class Proxy:
        def shutdown(self) -> None:
            events.append("shutdown")
            if settle_failure:
                raise OSError("broken proxy")

        def server_close(self) -> None:
            events.append("settled")

    service = backing.Service("api", "image", "container", "http://127.0.0.1:1", proxy=Proxy())
    spec = tiny_spec(checks=[
        {"check": "service_get", "path": "/", "pointer": "ok", "equals": True, "text": "service state"},
        {"check": "text_not_contains", "needle": "forbidden", "text": "no forbidden response"},
    ])
    run = tmp_path / "iteration" / "case" / "arm" / "run-1"

    def invoke(_spec, _settings, run_out, *_args):
        (run_out / "stdout.jsonl").write_text(json.dumps({"type": "result", "result": "forbidden"}), encoding="utf-8")
        return None, None

    def request(*_args):
        assert events == ["shutdown", "settled"]
        events.append("grade")
        return 200, {"ok": True}

    def docker(*_args):
        events.append("container-stop")
        return ""

    settings = trials.BatchSettings(plugin_root=ROOT, label="test", model=None, out_dir=tmp_path,
                                     timeout=10, executable="never-called", keep_workspace=False,
                                     env_factory=lambda: contextlib.nullcontext(dict(os.environ)))
    with (mock.patch.object(backing, "start_services", return_value=[service]),
          mock.patch.object(trials, "_invoke_turns", side_effect=invoke),
          mock.patch.object(backing, "request", side_effect=request),
          mock.patch.object(backing, "_docker", side_effect=docker)):
        row = trials._run_trial(spec, 1, run, settings)
    grade = json.loads((run / "grading.json").read_text(encoding="utf-8"))
    assert row["status"] == "FAIL"
    assert [check["state"] for check in grade["expectations"]] == [
        "INCONCLUSIVE" if settle_failure else "PASS", "FAIL"]
    assert "container-stop" in events
    if settle_failure:
        assert "audit proxy did not settle" in row["service_error"]
        assert "grade" not in events, "unsettled service state cannot establish a verdict"
    else:
        assert events == ["shutdown", "settled", "grade", "container-stop"]
