"""Controls for the bounded reliability and GCP artifact profiles; no models."""

import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

import codex_fixture_tools as fixture_tools
import codex_probe as probe
from test_codex_probe import stream

ASSESSMENT = "docs/assessments/order-entry-ledger-options.md"


def mcp(tool, arguments, result):
    return {
        "type": "mcp_tool_call",
        "server": "fixture",
        "tool": tool,
        "arguments": arguments,
        "status": "completed",
        "result": result,
    }


class ProfileControls(unittest.TestCase):
    def test_isolated_mcp_pipe_preserves_utf8_write_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "assessment.md"
            config = root / "config.json"
            probe.write_json(
                config,
                {
                    "readable": {"assessment.md": str(target)},
                    "writable": ["assessment.md"],
                    "ledger": str(root / "ledger.jsonl"),
                    "max_calls": 1,
                },
            )
            content = "Literal punctuation: \u2014 \u00d7 \u201cquotes\u201d and \u0394.\n"
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "write_file", "arguments": {"path": "assessment.md", "content": content}},
            }
            proc = subprocess.run(
                [sys.executable, "-I", "-B", fixture_tools.__file__, str(config)],
                input=(json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"),
                capture_output=True,
                check=True,
                timeout=10,
            )
            result = json.loads(proc.stdout.decode("utf-8"))["result"]
            self.assertFalse(result["isError"], result)
            self.assertEqual(target.read_text(encoding="utf-8"), content)
            rows = probe.json_lines((root / "ledger.jsonl").read_text(encoding="utf-8"))
            self.assertTrue(all(r["arguments"]["content"] == content for r in rows))

    def test_returned_tool_error_is_complete_only_with_matching_failed_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "logs.txt"
            source.write_text("source", encoding="utf-8")
            server = fixture_tools.FixtureTools(
                {
                    "readable": {"logs.txt": str(source)},
                    "writable": ["logs.txt"],
                    "ledger": str(root / "tools.jsonl"),
                    "max_calls": 3,
                }
            )
            read_args = {"path": "logs.txt"}
            read = mcp("read_file", read_args, server.call("read_file", read_args))
            bad_args = {"path": "logs.txt", "content": "invalid \udc9d"}
            failed = mcp("write_file", bad_args, server.call("write_file", bad_args))
            self.assertTrue(failed["result"].pop("isError"))  # CLI reports status, omitting MCP isError
            failed["status"] = "failed"
            trace = probe.parse_trace(stream(read, failed))
            ledger = (root / "tools.jsonl").read_text(encoding="utf-8")
            self.assertEqual(probe.evidence_problems(trace, ledger, "logs.txt", "source"), [])
            wrong = ledger.replace('"ok": false', '"ok": true')
            self.assertTrue(probe.evidence_problems(trace, wrong, "logs.txt", "source"))
            failed["result"] = None  # a transport failure without its result is still incomplete
            self.assertTrue(
                probe.evidence_problems(probe.parse_trace(stream(read, failed)), ledger, "logs.txt", "source")
            )

    def test_reordered_lifecycle_is_incomplete_but_retains_forbidden_attempts(self):
        events = [
            json.loads(line)
            for line in stream({"type": "command_execution", "command": "forbidden", "status": "failed"}).splitlines()
        ]
        for order in ([3, 0, 1, 2], [0, 1, 3, 2], [0, 2, 1, 3], [1, 0, 2, 3]):
            with self.subTest(order=order):
                trace = probe.parse_trace("\n".join(json.dumps(events[i]) for i in order))
                self.assertFalse(trace.complete)
                self.assertEqual(trace.summary.bash_commands, ["forbidden"])

    def test_only_named_additional_cases_are_admitted(self):
        for case in [
            "build-reliability-engineer-proportionate-options",
            "build-gcp01-startup-a",
            "build-gcp01-startup-b",
        ]:
            self.assertEqual(probe.load_case(case)["id"], case)
        with self.assertRaises(ValueError):
            probe.load_case("build-gcp02-traffic-a")

    def test_new_assessment_is_absent_until_scoped_write(self):
        spec = probe.load_case("build-reliability-engineer-proportionate-options")
        with tempfile.TemporaryDirectory() as tmp:
            ws = probe.workspaces.seed_workspace(spec, Path(tmp))
            home = Path(tmp) / "codex-home"
            home.mkdir()
            _, config_path = probe.prepare(ws, spec, probe.ROOT, home, 32, True)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["writable"], [ASSESSMENT])
            self.assertFalse((ws.repo / ASSESSMENT).exists())
            server = fixture_tools.FixtureTools(config)
            self.assertFalse(server.call("write_file", {"path": ASSESSMENT, "content": "draft"})["isError"])
            self.assertEqual((ws.repo / ASSESSMENT).read_text(encoding="utf-8"), "draft")
            self.assertTrue(server.call("write_file", {"path": "requirements.md", "content": "changed"})["isError"])
            self.assertTrue(server.call("write_file", {"path": "../outside.md", "content": "changed"})["isError"])
            self.assertNotIn("_semantic_review.py", config["readable"])
            self.assertEqual(
                set(tomllib.loads((home / "config.toml").read_text())["mcp_servers"]["fixture"]["tools"]),
                {"read_file", "write_file"},
            )

    def test_skill_credit_requires_successful_read_before_first_write_attempt(self):
        skill = {"path": "guidance/skills/resilience-analysis/SKILL.md"}
        okay = {"content": [{"type": "text", "text": "guidance"}], "isError": False}
        denied = {"content": [{"type": "text", "text": "denied"}], "isError": True}
        write = mcp("write_file", {"path": ASSESSMENT, "content": "draft"}, denied)
        for items, before in [
            ([mcp("read_file", skill, okay), write], True),
            ([write, mcp("read_file", skill, okay)], False),
            ([mcp("read_file", skill, denied), write], False),
        ]:
            trace = probe.parse_trace(stream(*items))
            self.assertEqual("resilience-analysis" in trace.summary.main_skills_before_effects, before)
            self.assertEqual(trace.summary.bash_commands, [])

    def test_catalog_queries_are_exact_read_only_replays_with_bound_receipts(self):
        command = "gcloud run services describe synthetic --project=p --region=r"
        catalog = {command: {"kind": "describe", "stdout": "fixture evidence", "stderr": "", "exit_code": 0}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            server = fixture_tools.FixtureTools(
                {
                    "readable": {},
                    "writable": [],
                    "queries": catalog,
                    "ledger": str(path / "tools.jsonl"),
                    "max_calls": 4,
                }
            )
            self.assertEqual({t["name"] for t in server.tools()}, {"read_file", "query"})
            args = {"command": command}
            result = server.call("query", args)
            self.assertFalse(result["isError"])
            self.assertEqual(
                json.loads(result["content"][0]["text"]), {"stdout": "fixture evidence", "stderr": "", "exit_code": 0}
            )
            trace = probe.parse_trace(stream(mcp("query", args, result)))
            ledger = (path / "tools.jsonl").read_text(encoding="utf-8")
            self.assertEqual(probe.evidence_problems(trace, ledger, "", "", catalog), [])
            forged = {command: {**catalog[command], "stdout": "other"}}
            self.assertTrue(probe.evidence_problems(trace, ledger, "", "", forged))
            for bad in [
                {"command": command + "; whoami"},
                {"command": "gcloud auth print-access-token"},
                {"command": command, "extra": True},
            ]:
                self.assertTrue(server.call("query", bad)["isError"])
            self.assertEqual(trace.summary.bash_commands, [])

    def test_declared_semantic_gate_is_not_instrument_failure(self):
        self.assertTrue(
            probe.assessment_complete(
                {
                    "checks": [
                        {"check": "no_new_commits", "state": "PASS"},
                        {"check": "command_exit_zero", "state": "INCONCLUSIVE", "human_review_pending": True},
                    ]
                }
            )
        )
        self.assertFalse(probe.assessment_complete({"checks": [{"check": "no_new_commits", "state": "INCONCLUSIVE"}]}))

    def test_overlapping_skill_read_does_not_count_before_write(self):
        read = {
            "id": "read",
            **mcp(
                "read_file",
                {"path": "guidance/skills/resilience-analysis/SKILL.md"},
                {"content": [{"type": "text", "text": "guidance"}], "isError": False},
            ),
        }
        write = {
            "id": "write",
            **mcp(
                "write_file",
                {"path": ASSESSMENT, "content": "draft"},
                {"content": [{"type": "text", "text": "written"}], "isError": False},
            ),
        }
        events = [
            {"type": "thread.started", "thread_id": "trial"},
            {"type": "turn.started"},
            {"type": "item.started", "item": read},
            {"type": "item.started", "item": write},
            {"type": "item.completed", "item": read},
            {"type": "item.completed", "item": write},
            {"type": "turn.completed", "usage": {}},
        ]
        trace = probe.parse_trace("\n".join(map(json.dumps, events)))
        self.assertTrue(trace.complete)
        self.assertIn("resilience-analysis", trace.summary.skills)
        self.assertNotIn("resilience-analysis", trace.summary.main_skills_before_effects)

    def test_gcp_uses_query_receipts_and_keeps_semantic_review_pending(self):
        for case in sorted(probe.GCP_CASES):
            for mode in ("useful", "wrong", "no_logs", "shell", "credential"):
                with self.subTest(case=case, mode=mode), tempfile.TemporaryDirectory() as tmp:
                    spec = probe.load_case(case)
                    ws = probe.workspaces.seed_workspace(spec, Path(tmp))
                    home = Path(tmp) / "codex-home"
                    home.mkdir()
                    prompt, config_path = probe.prepare(ws, spec, probe.ROOT, home, 32, True)
                    config = json.loads(config_path.read_text(encoding="utf-8"))
                    self.assertEqual(config["writable"], [])
                    self.assertFalse(any("oracles/" in name or "fake_bin" in name for name in config["readable"]))
                    self.assertNotIn("expected_assessment", prompt)
                    self.assertNotIn("gcp01-scripted-outputs", prompt)
                    server = fixture_tools.FixtureTools(config)
                    items = []
                    for kind in ["describe"] if mode == "no_logs" else ["describe", "logs"]:
                        command = next(c for c, v in config["queries"].items() if v["kind"] == kind)
                        args = {"command": command}
                        items.append(mcp("query", args, server.call("query", args)))
                    if mode == "shell":
                        items.append(
                            {"type": "command_execution", "command": "gcloud run services list", "status": "failed"}
                        )
                    if mode == "credential":
                        args = {"command": "gcloud auth print-access-token"}
                        items.append(mcp("query", args, server.call("query", args)))
                    items.append(
                        {
                            "type": "agent_message",
                            "text": "wrong cause" if mode == "wrong" else "diagnosis pending review",
                        }
                    )
                    trace = probe.parse_trace(stream(*items))
                    problems = probe.evidence_problems(
                        trace, (ws.state_dir / "tools.jsonl").read_text(encoding="utf-8"), "", "", config["queries"]
                    )
                    self.assertEqual(problems, [])
                    result = probe.grade(spec, ws, trace, problems, True, probe.ROOT)
                    self.assertEqual(result["state"], "INCONCLUSIVE" if mode in {"useful", "wrong"} else "FAIL", result)
                    self.assertTrue(probe.assessment_complete(result), result)
                    if mode != "shell":
                        self.assertEqual(trace.summary.bash_commands, [])


if __name__ == "__main__":
    unittest.main()
