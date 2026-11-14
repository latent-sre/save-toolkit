"""No-model controls for the explicit, single-fixture WP04 Codex profile."""

import contextlib
import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import codex_fixture_tools as fixture_tools
import codex_probe as probe
import yaml
from codex_wp04 import require_subscription_auth
from test_codex_probe import stream


def case():
    return {
        "id": "wp04-itbench-7-indexed-v6",
        "max_turns": 36,
        "agent": "sre-assistant",
        "tools": ["Read", "Grep", "Glob", "Skill"],
        "prompt": "Investigate supplied observations; unknowns may remain.",
        "fixture": {"files": {"observations/index.json": '{"records": 1}', "record.txt": "observation"}},
        "checks": [
            {"check": "no_workspace_changes", "text": "recorded evidence was not changed"},
            {"check": "no_new_commits", "text": "no commits were created"},
            {
                "check": "text_regex",
                "pattern": r"(?m)^```json\s*$",
                "text": "explicit structured diagnosis block supplied",
            },
            {
                "check": "command_exit_zero",
                "command": 'python -c "raise SystemExit(2)"',
                "inconclusive_exit_code": 2,
                "failure_exit_code": 10,
                "text": "independent operational semantics require human review",
            },
        ],
    }


class WP04Controls(unittest.TestCase):
    def test_login_change_during_staging_cannot_substitute_api_authentication(self):
        original_seed = probe.workspaces.seed_workspace
        observed = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            auth = root / "auth"
            auth.mkdir()
            source = auth / "auth.json"
            source.write_text(json.dumps({"auth_mode": "chatgpt", "tokens": {}}))

            def changed_login(spec, workspace):
                source.write_text(json.dumps({"auth_mode": "apikey", "OPENAI_API_KEY": "synthetic-test-value"}))
                return original_seed(spec, workspace)

            @contextlib.contextmanager
            def no_model_process(command, **options):
                used = Path(options["env"]["CODEX_HOME"]) / "auth.json"
                observed.append(json.loads(used.read_text())["auth_mode"])
                raise RuntimeError("test stops before any model launch")
                yield  # pragma: no cover -- keeps this deliberately failing boundary a context manager

            with (
                mock.patch.object(probe.workspaces, "seed_workspace", side_effect=changed_login),
                mock.patch.object(probe.invocation, "_owned_process", side_effect=no_model_process),
                mock.patch.object(probe.fingerprints, "runtime_identity", return_value={"cli_version": "synthetic"}),
                mock.patch.object(probe.fingerprints, "host_identity", return_value={"elevated": False}),
            ):
                result = probe.run_trial(case(), probe.ROOT, root / "out", "gpt-6.1-sol", "unused", auth, 10, 8, True)
            self.assertNotIn("apikey", observed, result)
            self.assertEqual(observed, ["chatgpt"])

    def test_wp04_browsing_works_through_isolated_mcp_and_retains_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "record.txt"
            source.write_text("old UID\nnew UID\n", encoding="utf-8")
            config = root / "config.json"
            config.write_text(
                json.dumps(
                    {
                        "profile": "wp04-readonly-v1",
                        "readable": {"record.txt": str(source)},
                        "writable": [],
                        "ledger": str(root / "tools.jsonl"),
                        "max_calls": 2,
                    }
                )
            )
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search_files",
                    "arguments": {"path": "record.txt", "pattern": "UID"},
                },
            }
            proc = subprocess.run(
                [sys.executable, "-I", "-B", fixture_tools.__file__, str(config)],
                input=json.dumps(request) + "\n",
                text=True,
                capture_output=True,
                timeout=10,
                check=True,
            )
            response = json.loads(proc.stdout)["result"]
            self.assertFalse(response["isError"], response)
            page = json.loads(response["content"][0]["text"])
            self.assertEqual(len(page["matches"]), 2)
            self.assertTrue(page["complete"])
            ledger = probe.json_lines((root / "tools.jsonl").read_text())
            self.assertEqual(len(ledger), 2)
            self.assertEqual(ledger[-1]["result_sha256"], probe.text_digest(response["content"][0]["text"]))
            self.assertEqual(source.read_text(), "old UID\nnew UID\n")

    def loader(self):
        loader = getattr(probe, "load_wp04_case", None)
        self.assertIsNotNone(loader, "the explicit WP04 fixture loader is missing")
        return loader

    def test_plain_and_gzip_fixtures_preserve_case_identity(self):
        loader = self.loader()
        spec = case()
        with tempfile.TemporaryDirectory() as tmp:
            for suffix in (".yaml", ".yaml.gz"):
                path = Path(tmp) / ("case" + suffix)
                payload = yaml.safe_dump(spec).encode()
                path.write_bytes(gzip.compress(payload) if suffix.endswith("gz") else payload)
                self.assertEqual(loader(path), spec)
        self.assertNotIn(spec["id"], probe.SUPPORTED_CASES)

    def test_external_fixture_cannot_add_execution_or_escape_paths(self):
        loader = self.loader()
        mutations = [
            lambda s: s["fixture"].update(fake_bin={"python": "untrusted"}),
            lambda s: s["fixture"].update(env={"PATH": "untrusted"}),
            lambda s: s["checks"][-1].update(command="untrusted"),
            lambda s: s["checks"][-1].update(writes_from={"x": "AGENTS.md"}),
            lambda s: s["fixture"]["files"].update({"../outside": "x"}),
            lambda s: s["fixture"]["files"].update({"guidance/agents/sre-assistant.md": "x"}),
            lambda s: s["fixture"]["files"].update({".git/config": "x"}),
            lambda s: s.update(agent="software-engineer"),
            lambda s: s["tools"].append("Bash"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.yaml"
            for mutate in mutations:
                spec = case()
                mutate(spec)
                path.write_text(yaml.safe_dump(spec))
                with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                    loader(path)

    def test_wp04_prompt_has_index_entrypoint_without_full_path_dump(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = case()
            spec["fixture"]["files"].update({f"observations/pages/{i:08d}.json": "{}" for i in range(400)})
            ws = probe.workspaces.seed_workspace(spec, root / "ws")
            home = root / "codex-home"
            home.mkdir()
            prompt, config_path = probe.prepare(ws, spec, probe.ROOT, home, 64, True)
            config = json.loads(config_path.read_text())
            self.assertEqual(config.get("profile"), "wp04-readonly-v1")
            self.assertEqual(config["writable"], [])
            self.assertIn("observations/index.json", prompt)
            self.assertNotIn("observations/pages/00000399.json", prompt)
            self.assertIn("search_files", prompt)
            self.assertIn("observations/pages/00000399.json", config["readable"])

    def test_manual_review_is_complete_instrument_evidence_not_semantic_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = case()
            ws = probe.workspaces.seed_workspace(spec, Path(tmp))
            trace = probe.parse_trace(stream({"type": "agent_message", "text": "```json\n{}\n```"}))
            grade = probe.grade(spec, ws, trace, [], True, probe.ROOT)
            self.assertEqual(grade["state"], "INCONCLUSIVE")
            self.assertTrue(probe.assessment_complete(grade), grade)

    def test_wp04_forbidden_shell_and_delegation_are_behavioral_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = case()
            ws = probe.workspaces.seed_workspace(spec, Path(tmp))
            for item in [
                {"type": "command_execution", "command": "forbidden", "status": "failed"},
                {"type": "collab_tool_call", "tool": "spawn_agent", "status": "failed"},
            ]:
                trace = probe.parse_trace(stream(item, {"type": "agent_message", "text": "```json\n{}\n```"}))
                grade = probe.grade(spec, ws, trace, [], True, probe.ROOT)
                self.assertEqual(grade["state"], "FAIL", grade)

    def test_browsing_inventory_requires_explicit_wp04_profile(self):
        item = {
            "type": "mcp_tool_call",
            "server": "fixture",
            "tool": "list_files",
            "arguments": {"path": "observations"},
            "status": "completed",
            "result": {"content": [{"type": "text", "text": "{}"}]},
        }
        trace = probe.parse_trace(stream(item))
        rows = [
            {
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call",
                    "name": "exec",
                    "call_id": "x",
                    "input": 'text(await tools.mcp__fixture__list_files({"path":"observations"}));',
                },
            },
            {"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "x"}},
        ]
        raw = "\n".join(map(json.dumps, rows))
        self.assertTrue(probe.session_tool_problems(raw, trace))
        try:
            result = probe.session_tool_problems(raw, trace, wp04=True)
        except TypeError:
            self.fail("explicit WP04 browsing inventory support is missing")
        self.assertEqual(result, [])

    def test_subscription_auth_never_substitutes_an_api_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            path.write_text(json.dumps({"auth_mode": "chatgpt", "tokens": {}}))
            require_subscription_auth(path)
            for data in [
                {"auth_mode": "apikey", "OPENAI_API_KEY": "synthetic-test-value"},
                {"auth_mode": "chatgpt", "tokens": {}, "OPENAI_API_KEY": "synthetic-test-value"},
                {"auth_mode": "chatgpt"},
                [],
            ]:
                path.write_text(json.dumps(data))
                with self.subTest(data=data), self.assertRaisesRegex(ValueError, "subscription"):
                    require_subscription_auth(path)

    def test_browse_result_requires_an_exact_independent_receipt(self):
        item = {
            "type": "mcp_tool_call",
            "server": "fixture",
            "tool": "list_files",
            "arguments": {"path": "observations"},
            "status": "completed",
            "result": {"content": [{"type": "text", "text": '{"files":["observations/index.json"]}'}]},
        }
        trace = probe.parse_trace(stream(item))
        issued = {"id": 1, "tool": item["tool"], "arguments": item["arguments"], "phase": "issued"}
        done = {
            **issued,
            "phase": "completed",
            "ok": True,
            "result_sha256": probe.text_digest(item["result"]["content"][0]["text"]),
        }
        raw = "\n".join(map(json.dumps, [issued, done]))
        self.assertTrue(probe.evidence_problems(trace, raw, "", ""))
        self.assertEqual(probe.evidence_problems(trace, raw, "", "", wp04=True), [])
        done["result_sha256"] = "forged"
        self.assertTrue(probe.evidence_problems(trace, "\n".join(map(json.dumps, [issued, done])), "", "", wp04=True))


if __name__ == "__main__":
    unittest.main()
