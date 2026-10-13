"""Offline tests for the Muse probe: trace parsing, prompt pinning and grading.

These never call a model. Live `muse exec` behavior is measured only by a real
`muse_probe.py run`, whose record states its own status.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import muse_probe
from probe.outcomes import State

ROOT = Path(__file__).resolve().parents[1]


def event(payload_type, payload):
    return json.dumps({"payload_type": payload_type, "payload": payload})


SAMPLE = "\n".join([
    event("run.model.configured", {"model_id": "muse-wonder-1.0"}),
    event("task.lifecycle.proposed", {"event": {"task_kind": "tool.search"}}),
    event("tool.result", {"correlation_facts": {"tool_name": "search", "outcome": "success"}}),
    event("run.output.delta", {"text": "{\"ok\":"}),
    event("run.output.delta", {"text": " true}"}),
    event("run.terminal.completed", {"terminal": "completed", "text": "{\"ok\": true}"}),
])


class ParseTests(unittest.TestCase):
    def test_terminal_text_wins_over_deltas(self):
        trace = muse_probe.parse_muse_trace(SAMPLE)
        self.assertEqual("muse-wonder-1.0", trace.model_id)
        self.assertEqual('{"ok": true}', trace.result_text)
        self.assertTrue(trace.completed)
        self.assertEqual({"search": 1}, dict(trace.tool_counts))
        self.assertEqual(["tool.search"], trace.task_kinds)

    def test_deltas_are_the_fallback_and_garbage_is_skipped(self):
        trace = muse_probe.parse_muse_trace("not json\n" + event("run.output.delta", {"text": "hi"}))
        self.assertEqual("hi", trace.result_text)
        self.assertFalse(trace.completed)

    def test_no_dispatch_tools_means_no_dispatches(self):
        trace = muse_probe.parse_muse_trace(SAMPLE)
        self.assertEqual([], trace.dispatches)


class PromptAndCommandTests(unittest.TestCase):
    SPEC = {
        "id": "agent-direct-reliability-engineer-toil-positive",
        "agent": "reliability-engineer",
        "prompt": "Assess the proposal.",
        "tools": ["Read"],
        "max_turns": 11,
    }

    def test_agent_body_is_injected_before_the_task(self):
        prompt = muse_probe.build_prompt(self.SPEC)
        self.assertIn("reliability-engineer", prompt)
        self.assertIn("canonical-definition", prompt)
        self.assertLess(prompt.index("canonical-definition"), prompt.index("Assess the proposal."))

    def test_contract_command_disables_shell_and_write(self):
        command = muse_probe.build_command(
            "muse", self.SPEC, ROOT, Path("prompt.md"), "session-1", None)
        self.assertIn("--disable-shell", command)
        self.assertIn("--disable-write", command)
        self.assertIn("--json", command)
        # A pinned session id requires retained logging; the two flags refuse to start together.
        self.assertNotIn("--no-session-log", command)

    def test_declared_tools_intersect_agent_grants(self):
        read_only = {"id": "x", "prompt": "Assess.", "tools": ["Read"]}
        for agent in ("software-engineer", "researcher"):
            command = muse_probe.build_command(
                "muse", read_only | {"agent": agent}, ROOT, Path("prompt.md"), "s-1", None)
            self.assertIn("--disable-shell", command, agent)
            self.assertIn("--disable-web-tools", command, agent)

    def test_build_shell_follows_the_pinned_agents_grants(self):
        base = {"id": "x", "prompt": "Do the task.", "fixture": {"files": {}}}
        for agent, disabled in (("reliability-engineer", True), ("software-engineer", False)):
            command = muse_probe.build_command(
                "muse", base | {"agent": agent}, ROOT, Path("prompt.md"), "s-1", None)
            self.assertEqual(disabled, "--disable-shell" in command, agent)

    def test_windows_cmd_shim_is_wrapped(self):
        self.assertEqual(["cmd", "/c", "muse.cmd"], muse_probe.muse_argv("muse.cmd"))
        self.assertEqual(["muse"], muse_probe.muse_argv("muse"))


class GradingTests(unittest.TestCase):
    def test_exact_json_grader_passes_and_fails(self):
        spec = {"graders": [{"type": "exact_json", "fields": {"a": 1}}]}
        good = muse_probe.parse_muse_trace(
            event("run.terminal.completed", {"terminal": "completed", "text": '{"a": 1}'}))
        bad = muse_probe.parse_muse_trace(
            event("run.terminal.completed", {"terminal": "completed", "text": '{"a": 2}'}))
        self.assertEqual(State.PASS, muse_probe.grade_graders(spec, good)[0]["state"])
        self.assertEqual(State.FAIL, muse_probe.grade_graders(spec, bad)[0]["state"])

    def test_rubric_without_a_judge_is_inconclusive(self):
        spec = {"graders": [{"type": "rubric", "name": "x", "params": {}}]}
        trace = muse_probe.parse_muse_trace(
            event("run.terminal.completed", {"terminal": "completed", "text": "anything"}))
        self.assertEqual(State.INCONCLUSIVE, muse_probe.grade_graders(spec, trace)[0]["state"])

    def test_shell_tools_are_visible_to_did_not_run_checks(self):
        for tool_name in ("powershell", "PowerShell"):
            trace = muse_probe.parse_muse_trace("\n".join([
                event("tool.result", {"correlation_facts": {"tool_name": tool_name, "outcome": "success"}}),
                event("run.terminal.completed", {"terminal": "completed", "text": "done"}),
            ]))
            self.assertEqual(1, len(trace.to_summary().bash_commands), tool_name)

    def test_prompt_echo_alone_does_not_credit_routing(self):
        spec = {"target": {"kind": "skill", "name": "toil-reduction"}, "routing": {"expect": "fire"}}
        raw = 'the prompt mentions toil-reduction\n' + event(
            "tool.result", {"correlation_facts": {"tool_name": "search", "outcome": "success"}})
        trace = muse_probe.parse_muse_trace(raw + "\n" + event(
            "run.terminal.completed", {"terminal": "completed", "text": "done"}))
        # A name in tool output is a mention, not a firing: unmeasured, not FAIL.
        self.assertEqual(State.INCONCLUSIVE, muse_probe.grade_routing(spec, trace, raw)[0]["state"])

    def test_session_log_credits_only_same_line_dispatch_targets(self):
        session_id = "01a10000-0000-7000-8000-000000000001"
        trace = muse_probe.parse_muse_trace(json.dumps({
            "stream": {"kind": "session", "id": session_id},
            "payload_type": "run.terminal.completed",
            "payload": {"terminal": "completed", "text": "done"},
        }))
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "2026" / "01" / "01" / session_id / "session.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text(
                'read skills/toil-reduction/SKILL.md\n'
                'catalog entry {"name": "sre-assistant"} in a tool listing\n'
                '{"tool": "subagent_spawn", "agent": "researcher"}\n',
                encoding="utf-8")
            with patch.dict(os.environ, {"MUSE_SESSIONS_ROOT": tmp}):
                muse_probe.augment_from_session_log(trace)
        self.assertTrue(trace.session_log_found)
        # Prose and catalog mentions credit nothing; only the spawn's own target counts.
        self.assertEqual(set(), trace.skills_loaded)
        self.assertEqual({"researcher"}, trace.dispatch_targets)
        spec = {"helper": "sre-assistant"}
        expectations = muse_probe.grade_native(spec, [trace], "")
        self.assertEqual(State.INCONCLUSIVE, expectations[0]["state"])

    def test_captured_real_trace_parses(self):
        fixture = Path(__file__).parent / "fixtures" / "muse-trace-sample.jsonl"
        trace = muse_probe.parse_muse_trace(fixture.read_text(encoding="utf-8"))
        self.assertEqual("muse-wonder-1.0", trace.model_id)
        self.assertTrue(trace.completed)
        self.assertEqual("grade_smoke.py", trace.result_text)
        self.assertEqual(1, trace.tool_counts.get("search"))

    def test_routing_without_tool_evidence_is_inconclusive(self):
        spec = {"target": {"kind": "skill", "name": "toil-reduction"}, "routing": {"expect": "fire"}}
        trace = muse_probe.parse_muse_trace(
            event("run.terminal.completed", {"terminal": "completed", "text": "an inline answer"}))
        self.assertEqual(State.INCONCLUSIVE, muse_probe.grade_routing(spec, trace, "")[0]["state"])

    def test_overall_prefers_fail_then_inconclusive(self):
        self.assertEqual(State.FAIL, muse_probe.overall(
            [{"state": "PASS"}, {"state": "INCONCLUSIVE"}, {"state": "FAIL"}]))
        self.assertEqual(State.INCONCLUSIVE, muse_probe.overall([{"state": "PASS"}, {"state": "INCONCLUSIVE"}]))
        self.assertEqual(State.PASS, muse_probe.overall([{"state": "PASS"}]))


if __name__ == "__main__":
    unittest.main()
