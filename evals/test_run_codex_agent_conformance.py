"""Offline contract tests for the Codex/Sol custom-agent conformance runner."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import run_codex_agent_conformance as conformance


class CodexAgentConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = conformance.load_manifest(conformance.DEFAULT_MANIFEST)
        self.lane = self.manifest["lanes"][0]
        self.instructions = (
            "Reviewer rules.\n"
            "Zero noise over perfect coverage: a review with three real findings beats one with "
            "twenty theoretical ones.\n"
        )
        self.parent_thread = "parent-thread"

    def _context(self, *, model: str = "gpt-5.6-sol") -> dict[str, object]:
        return {
            "model": model,
            "effort": "high",
            "approval_policy": "never",
            "sandbox_policy": {"type": "read-only"},
            "collaboration_mode": {
                "mode": "default",
                "settings": {"model": model, "reasoning_effort": "high"},
            },
        }

    def _parent(self, *, successful_output: bool = True) -> list[dict[str, object]]:
        call_id = "spawn-call"
        wait_call_id = "wait-call"
        output = (
            {"task_name": "/root/reviewer_canary"}
            if successful_output
            else {"error": "spawn failed"}
        )
        return [
            {
                "type": "session_meta",
                "payload": {"session_id": self.parent_thread, "parent_thread_id": None},
            },
            {"type": "turn_context", "payload": self._context()},
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "spawn_agent",
                    "call_id": call_id,
                    "arguments": json.dumps(
                        {
                            "agent_type": "reviewer",
                            "fork_turns": "none",
                            "task_name": "reviewer_canary",
                            "message": "encrypted",
                        }
                    ),
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(output),
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "wait_agent",
                    "call_id": wait_call_id,
                    "arguments": json.dumps({"timeout_ms": 60000}),
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": wait_call_id,
                    "output": json.dumps({"message": "Wait completed.", "timed_out": False}),
                },
            },
        ]

    def _child(self, *, model: str = "gpt-5.6-sol", instructions: str | None = None) -> list[dict[str, object]]:
        return [
            {
                "type": "session_meta",
                "payload": {
                    "session_id": "child-thread",
                    "parent_thread_id": self.parent_thread,
                    "agent_role": "reviewer",
                    "agent_path": "/root/reviewer_canary",
                    "source": {
                        "subagent": {
                            "thread_spawn": {
                                "parent_thread_id": self.parent_thread,
                                "agent_role": "reviewer",
                            }
                        }
                    },
                },
            },
            {"type": "turn_context", "payload": self._context(model=model)},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "developer",
                    "content": [
                        {"type": "input_text", "text": instructions or self.instructions}
                    ],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "phase": "final_answer",
                    "content": [
                        {"type": "output_text", "text": self.lane["child_expected"]}
                    ],
                },
            },
        ]

    def _stdout(self) -> dict[str, object]:
        return {
            "last_message": json.dumps(self.lane["expected"]),
            "thread_id": self.parent_thread,
            "turn_completed_count": 1,
            "malformed_line_count": 0,
            "unfinished_command_count": 0,
        }

    def _score(
        self,
        parent: list[dict[str, object]] | None = None,
        child: list[dict[str, object]] | None = None,
        *,
        stderr: str = "",
    ) -> conformance.AgentScore:
        return conformance.score_agent_evidence(
            stdout_trace=self._stdout(),
            rollouts=[parent if parent is not None else self._parent(), child if child is not None else self._child()],
            lane=self.lane,
            expected_instructions=self.instructions,
            returncode=0,
            stderr=stderr,
            timed_out=False,
        )

    def test_manifest_is_sol_only_and_canary_is_not_disclosed(self) -> None:
        conformance.validate_manifest(self.manifest)
        self.assertEqual("gpt-5.6-sol", self.lane["model"])
        self.assertNotIn(self.lane["child_expected"], self.lane["prompt"])

    def test_manifest_rejects_prompt_that_discloses_child_canary(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["lanes"][0]["prompt"] += " " + self.lane["child_expected"]
        with self.assertRaises(conformance.base.ConformanceError):
            conformance.validate_manifest(manifest)

    def test_manifest_requires_bound_task_name(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["lanes"][0]["prompt"] = manifest["lanes"][0]["prompt"].replace(
            "reviewer_canary", "the child task"
        )
        with self.assertRaises(conformance.base.ConformanceError):
            conformance.validate_manifest(manifest)

    def test_valid_parent_child_delegation_passes(self) -> None:
        score = self._score()
        self.assertEqual("pass", score.verdict)
        self.assertEqual(("gpt-5.6-sol",), score.observed_models)
        self.assertTrue(score.diagnostics["spawn_succeeded"])
        self.assertTrue(score.diagnostics["wait_succeeded"])
        self.assertTrue(score.diagnostics["agent_instructions_loaded"])

    def test_self_report_without_spawn_cannot_pass(self) -> None:
        parent = self._parent()
        parent[:] = [row for row in parent if row.get("type") != "response_item"]
        score = self._score(parent=parent)
        self.assertEqual("fail", score.verdict)
        self.assertFalse(score.diagnostics["spawn_succeeded"])

    def test_failed_spawn_output_cannot_pass(self) -> None:
        score = self._score(parent=self._parent(successful_output=False))
        self.assertEqual("fail", score.verdict)
        self.assertFalse(score.diagnostics["spawn_succeeded"])

    def test_child_tool_call_cannot_pass_text_only_canary(self) -> None:
        child = self._child()
        child.append(
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "spawn_agent",
                    "call_id": "unexpected-child-call",
                    "arguments": "{}",
                },
            }
        )
        score = self._score(child=child)
        self.assertEqual("fail", score.verdict)
        self.assertEqual(1, score.diagnostics["child_tool_call_count"])

    def test_parent_must_wait_for_child(self) -> None:
        parent = self._parent()
        parent[:] = [
            row
            for row in parent
            if not (
                row.get("type") == "response_item"
                and isinstance(row.get("payload"), dict)
                and (
                    row["payload"].get("name") == "wait_agent"
                    or row["payload"].get("call_id") == "wait-call"
                )
            )
        ]
        score = self._score(parent=parent)
        self.assertEqual("fail", score.verdict)
        self.assertFalse(score.diagnostics["wait_succeeded"])

    def test_child_must_run_the_requested_sol_contract(self) -> None:
        score = self._score(child=self._child(model="gpt-5.6-terra"))
        self.assertEqual("fail", score.verdict)
        self.assertFalse(score.diagnostics["child_runtime_contract_matched"])
        self.assertEqual(("gpt-5.6-sol", "gpt-5.6-terra"), score.observed_models)

    def test_child_must_load_exact_agent_instructions(self) -> None:
        score = self._score(child=self._child(instructions="lookalike reviewer"))
        self.assertEqual("fail", score.verdict)
        self.assertFalse(score.diagnostics["agent_instructions_loaded"])

    def test_runtime_error_is_not_hidden_by_correct_oracles(self) -> None:
        score = self._score(stderr="2026-07-31 ERROR router: error=spawn rejected")
        self.assertEqual("fail", score.verdict)
        self.assertEqual(1, score.diagnostics["runtime_error_count"])

    def test_exec_command_persists_rollout_and_pins_no_history_capability(self) -> None:
        command = conformance.build_exec_command("codex", Path("C:/neutral"), self.lane)
        self.assertNotIn("--ephemeral", command)
        self.assertIn("multi_agent", command)
        self.assertIn("gpt-5.6-sol", command)
        self.assertLess(command.index("--ask-for-approval"), command.index("exec"))

    def test_rollout_reader_rejects_malformed_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sessions" / "bad.jsonl"
            path.parent.mkdir()
            path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaises(conformance.base.ConformanceError):
                conformance._read_rollouts(path.parent)


if __name__ == "__main__":
    unittest.main()
