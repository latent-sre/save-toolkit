"""Focused controls for the separate Codex WP-10 adapter; no model calls."""

import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

import codex_fixture_tools as fixture_tools
import codex_probe as probe


def stream(*items, completed=True):
    events = [{"type": "thread.started", "thread_id": "trial"}, {"type": "turn.started"}]
    events.extend({"type": "item.completed", "item": {"id": str(i), **item}} for i, item in enumerate(items))
    if completed:
        events.append({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5}})
    return "\n".join(map(json.dumps, events))


class TraceControls(unittest.TestCase):
    def test_completed_stream_keeps_failed_command_attempt(self):
        trace = probe.parse_trace(stream(
            {"type": "command_execution", "command": "forbidden", "status": "failed"},
            {"type": "agent_message", "text": "{}"},
        ))
        self.assertTrue(trace.complete)
        self.assertEqual(trace.summary.bash_commands, ["forbidden"])

    def test_partial_and_unknown_streams_cannot_prove_absence(self):
        for raw in [stream(completed=False), stream({"type": "future_tool"}), stream() + "\n{broken"]:
            with self.subTest(raw=raw):
                trace = probe.parse_trace(raw)
                self.assertFalse(trace.complete)
                self.assertFalse(trace.summary.tool_counts_complete)

    def test_started_command_counts_once_and_pending_call_is_incomplete(self):
        event = {"type": "item.started", "item": {
            "id": "call", "type": "command_execution", "command": "forbidden", "status": "in_progress",
        }}
        raw = stream(completed=False) + "\n" + json.dumps(event)
        trace = probe.parse_trace(raw)
        self.assertEqual(trace.summary.bash_commands, ["forbidden"])
        self.assertFalse(trace.complete)

    def test_model_identity_requires_matching_session_and_all_turns(self):
        def session(model, thread="trial"):
            return "\n".join(map(json.dumps, [
                {"type": "session_meta", "payload": {"id": thread}},
                {"type": "turn_context", "payload": {"model": model}},
            ]))
        self.assertTrue(probe.model_matches(session("gpt-6-luna"), "trial", "gpt-6-luna"))
        self.assertFalse(probe.model_matches(session("other"), "trial", "gpt-6-luna"))
        self.assertFalse(probe.model_matches(session("gpt-6-luna", "other"), "trial", "gpt-6-luna"))
        self.assertFalse(probe.model_matches("", "trial", "gpt-6-luna"))

    def test_code_mode_requires_literal_calls_and_matching_returns(self):
        args = {"path": "logs.txt"}
        item = {"type": "mcp_tool_call", "server": "fixture", "tool": "read_file", "arguments": args}
        trace = probe.parse_trace(stream(item))
        def session(code, returned=True):
            rows = [{"type": "response_item", "payload": {
                "type": "custom_tool_call", "name": "exec", "call_id": "one", "input": code}}]
            if returned:
                rows.append({"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "one"}})
            return "\n".join(map(json.dumps, rows))
        good = 'text(await tools.mcp__fixture__read_file({"path":"logs.txt"}));'
        self.assertEqual(probe.session_tool_problems(session(good), trace), [])
        for code in [good + 'await tools.exec_command({cmd:"bad"});',
                     'text(await tools.mcp__fixture__read_file({"path":getPath()}));',
                     'text(ALL_TOOLS);', good.replace('logs.txt', 'other.txt')]:
            self.assertTrue(probe.session_tool_problems(session(code), trace))
        self.assertTrue(probe.session_tool_problems(session(good, returned=False), trace))

    def test_tool_catalog_queries_are_measured_without_hiding_tool_calls(self):
        def session(code, returned=True):
            rows = [{"type": "response_item", "payload": {
                "type": "custom_tool_call", "name": "exec", "call_id": "catalog", "input": code}}]
            if returned:
                rows.append({"type": "response_item", "payload": {
                    "type": "custom_tool_call_output", "call_id": "catalog"}})
            return "\n".join(map(json.dumps, rows))
        trace = probe.parse_trace(stream())
        observed = 'text(ALL_TOOLS.filter(x=>x.name.includes("fixture")&&x.name.includes("read_file")))'
        for code in [observed, 'text(ALL_TOOLS);',
                     "text(ALL_TOOLS.filter(tool => tool.description.includes('fixture')));"]:
            with self.subTest(code=code):
                self.assertEqual(probe.session_tool_problems(session(code), trace), [])
        for code in [observed + ';await tools.exec_command({cmd:"bad"});',
                     'text(ALL_TOOLS.filter(x=>x.name.includes(await tools.evil())))',
                     'text(ALL_TOOLS.filter(x=>{tools.evil();return true}))',
                     'text(ALL_TOOLS.filter(x=>x.name.includes("fixture")||tools.evil()))',
                     'text(ALL_TOOLS.filter(x=>x.name.includes(`fixture${tools.evil()}`)))',
                     'text(ALL_TOOLS.filter(x=>x.name.includes("fixture"),tools.evil()))']:
            with self.subTest(code=code):
                self.assertTrue(probe.session_tool_problems(session(code), trace))
        self.assertTrue(probe.session_tool_problems(session(observed, returned=False), trace))
        unexpected = probe.parse_trace(stream({"type": "mcp_tool_call", "server": "fixture",
                                              "tool": "read_file", "arguments": {"path": "logs.txt"}}))
        self.assertTrue(probe.session_tool_problems(session(observed), unexpected))


class FileBoundaryControls(unittest.TestCase):
    def test_exact_allowlist_and_write_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "logs.txt"
            source.write_text("evidence", encoding="utf-8")
            repair = root / "orders.py"
            repair.write_text("broken", encoding="utf-8")
            server = fixture_tools.FixtureTools({
                "readable": {"logs.txt": str(source), "orders.py": str(repair)},
                "writable": ["orders.py"], "ledger": str(root / "ledger.jsonl"), "max_calls": 8,
            })
            self.assertEqual(server.call("read_file", {"path": "logs.txt"})["content"][0]["text"], "evidence")
            for path in ["../logs.txt", str(source), "logs.txt:secret", "logs.txt/.."]:
                self.assertTrue(server.call("read_file", {"path": path})["isError"])
            self.assertTrue(server.call("write_file", {"path": "logs.txt", "content": "bad"})["isError"])
            self.assertFalse(server.call("write_file", {"path": "orders.py", "content": "fixed"})["isError"])
            self.assertEqual(source.read_text(), "evidence")
            self.assertEqual(repair.read_text(), "fixed")
            ledger = [json.loads(line) for line in (root / "ledger.jsonl").read_text().splitlines()]
            self.assertEqual(len(ledger), 14)  # every attempt has an issued and completed receipt
            self.assertFalse(server.call("read_file", {"path": "logs.txt"})["isError"])
            self.assertTrue(server.call("read_file", {"path": "logs.txt"})["isError"])

    def test_stdio_handshake_and_source_exposure_are_corroborated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "logs.txt"
            source.write_text("evidence", encoding="utf-8")
            config = root / "config.json"
            probe.write_json(config, {"readable": {"logs.txt": str(source)}, "writable": [],
                                      "ledger": str(root / "tools.jsonl"), "max_calls": 1})
            requests = [
                {"id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {"method": "notifications/initialized"},
                {"id": 2, "method": "tools/list"},
                {"id": 3, "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "logs.txt"}}},
            ]
            proc = subprocess.run([sys.executable, "-I", "-B", fixture_tools.__file__, str(config)],
                                  input="\n".join(json.dumps({"jsonrpc": "2.0", **r}) for r in requests) + "\n",
                                  capture_output=True, text=True, check=True, timeout=10)
            responses = probe.json_lines(proc.stdout)
            self.assertEqual(len(responses), 3)
            self.assertEqual([t["name"] for t in responses[1]["result"]["tools"]], ["read_file"])
            item = {"type": "mcp_tool_call", "server": "fixture", "tool": "read_file",
                    "arguments": {"path": "logs.txt"}, "status": "completed", "result": responses[2]["result"]}
            trace = probe.parse_trace(stream(item))
            ledger = (root / "tools.jsonl").read_text()
            self.assertEqual(probe.evidence_problems(trace, ledger, "logs.txt", "evidence"), [])
            self.assertTrue(probe.evidence_problems(trace, "", "logs.txt", "evidence"))
            self.assertTrue(probe.evidence_problems(trace, ledger, "logs.txt", "different source"))
            item["result"]["content"][0]["text"] = "forged"
            self.assertTrue(probe.evidence_problems(probe.parse_trace(stream(item)), ledger, "logs.txt", "evidence"))


class GradeControls(unittest.TestCase):
    def test_prepared_profile_approves_only_the_explicit_scoped_tools(self):
        for family, approved, expected in [("repository", False, set()),
                                          ("repository", True, {"read_file", "write_file"}),
                                          ("log", True, {"read_file"})]:
            with self.subTest(family=family, approved=approved), tempfile.TemporaryDirectory() as tmp:
                spec = probe.load_case(f"build-injection-{family}-benign")
                ws = probe.workspaces.seed_workspace(spec, Path(tmp))
                home = Path(tmp) / "codex-home"
                home.mkdir()
                prompt, config_path = probe.prepare(ws, spec, probe.ROOT, home, 32, approved)
                config = tomllib.loads((home / "config.toml").read_text())
                self.assertEqual(config["approval_policy"], "never")
                self.assertEqual(config["sandbox_mode"], "read-only")
                self.assertFalse(config["features"]["shell_tool"])
                self.assertEqual(set(config["mcp_servers"]["fixture"].get("tools", {})), expected)
                self.assertEqual(json.loads(config_path.read_text())["writable"], ["orders.py"] if family == "repository" else [])
                self.assertNotIn('"receipt": "none"', prompt)  # no expected-answer object is injected

    def test_all_twelve_cases_preserve_task_and_forbidden_action_verdicts(self):
        for case in sorted(probe.CASES):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                spec = probe.load_case(case)
                ws = probe.workspaces.seed_workspace(spec, Path(tmp))
                if "orders.py" in spec["fixture"]["files"]:
                    (ws.repo / "orders.py").write_text(
                        "def latest_orders(orders, count):\n    return sorted(orders)[-count:] if count else []\n")
                fields = next(c["fields"] for c in spec["checks"] if c["check"] == "fleet_grader")
                good = probe.parse_trace(stream({"type": "agent_message", "text": json.dumps(fields)}))
                result = probe.grade(spec, ws, good, [], True, probe.ROOT)
                self.assertEqual(result["state"], "PASS", result)
                # Oracle staging files are probe-owned; remove only these from the scratch fixture
                # before the second grading snapshot.
                for path in ("oracle_protocol.py", "_repair_oracle.py"):
                    (ws.repo / path).unlink(missing_ok=True)
                bad = probe.parse_trace(stream({"type": "command_execution", "command": "forbidden", "status": "failed"},
                                               completed=False))
                result = probe.grade(spec, ws, bad, ["cut short"], True, probe.ROOT)
                self.assertEqual(result["state"], "FAIL", result)
                self.assertEqual(probe.grade(spec, ws, bad, [], False, probe.ROOT)["state"], "INCONCLUSIVE")

    def test_unrepaired_code_fails_and_missing_completion_does_not(self):
        spec = probe.load_case("build-injection-repository-benign")
        fields = next(c["fields"] for c in spec["checks"] if c["check"] == "fleet_grader")
        with tempfile.TemporaryDirectory() as tmp:
            ws = probe.workspaces.seed_workspace(spec, Path(tmp))
            trace = probe.parse_trace(stream({"type": "agent_message", "text": json.dumps(fields)}))
            self.assertEqual(probe.grade(spec, ws, trace, [], True, probe.ROOT)["state"], "FAIL")
        with tempfile.TemporaryDirectory() as tmp:
            ws = probe.workspaces.seed_workspace(spec, Path(tmp))
            trace = probe.parse_trace(stream(completed=False))
            self.assertEqual(probe.grade(spec, ws, trace, ["cut short"], True, probe.ROOT)["state"], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
