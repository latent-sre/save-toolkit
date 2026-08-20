#!/usr/bin/env python3
"""Contract tests for the sanitized Codex CLI JSONL trace primitives."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_harness  # noqa: E402


def _blob(events: list[dict[str, object]]) -> str:
    return "\n".join(json.dumps(event, separators=(",", ":")) for event in events)


def _usage() -> dict[str, int]:
    return {
        "input_tokens": 11,
        "cached_input_tokens": 2,
        "cache_write_input_tokens": 0,
        "output_tokens": 5,
        "reasoning_output_tokens": 3,
    }


def _agent_message(item_id: str, text: str) -> dict[str, object]:
    return {
        "type": "item.completed",
        "item": {"id": item_id, "type": "agent_message", "text": text},
    }


def _completed_trace(
    *items: dict[str, object],
    thread_id: str = "thread-private-123",
) -> list[dict[str, object]]:
    return [
        {"type": "thread.started", "thread_id": thread_id},
        {"type": "turn.started"},
        *items,
        {"type": "turn.completed", "usage": _usage()},
    ]


def _command_events(
    *,
    item_id: str = "cmd-private-1",
    command: str = "Get-Content C:\\private\\SKILL.md",
    output: str = "safe output from C:\\private\\SKILL.md",
    exit_code: int = 0,
    status: str = "completed",
) -> list[dict[str, object]]:
    started_item = {
        "id": item_id,
        "type": "command_execution",
        "command": command,
        "aggregated_output": "",
        "exit_code": None,
        "status": "in_progress",
    }
    completed_item = {
        "id": item_id,
        "type": "command_execution",
        "command": command,
        "aggregated_output": output,
        "exit_code": exit_code,
        "status": status,
    }
    return [
        {"type": "item.started", "item": started_item},
        {"type": "item.completed", "item": completed_item},
    ]


def _collab_events(
    *,
    item_id: str = "collab-private-1",
    prompt: str = "Inspect the routing boundary.",
) -> list[dict[str, object]]:
    started_item = {
        "id": item_id,
        "type": "collab_tool_call",
        "tool": "spawn_agent",
        "sender_thread_id": "thread-private-123",
        "receiver_thread_ids": ["child-private-456"],
        "prompt": prompt,
        "agents_states": {"child-private-456": "running"},
        "status": "in_progress",
    }
    completed_item = {
        **started_item,
        "agents_states": {"child-private-456": "completed"},
        "status": "completed",
    }
    return [
        {"type": "item.started", "item": started_item},
        {"type": "item.completed", "item": completed_item},
    ]


def _session_start(
    *,
    session_id: str = "session-private-root",
    model: str = "gpt-5.6-terra",
    permission_mode: str = "bypassPermissions",
) -> dict[str, object]:
    return {
        "session_id": session_id,
        "transcript_path": "C:\\private\\root-rollout.jsonl",
        "cwd": "C:\\private\\root-workspace",
        "hook_event_name": "SessionStart",
        "model": model,
        "permission_mode": permission_mode,
        "source": "startup",
    }


def _subagent_start(
    *,
    session_id: str = "session-private-root",
    turn_id: str = "turn-private-child-start",
    agent_id: str = "agent-private-1",
    agent_type: str = "save-toolkit-sre",
    model: str = "gpt-5.6-terra",
    permission_mode: str = "bypassPermissions",
) -> dict[str, object]:
    return {
        "session_id": session_id,
        "transcript_path": f"C:\\private\\{agent_id}-rollout.jsonl",
        "cwd": f"C:\\private\\{agent_id}-workspace",
        "hook_event_name": "SubagentStart",
        "model": model,
        "permission_mode": permission_mode,
        "turn_id": turn_id,
        "agent_id": agent_id,
        "agent_type": agent_type,
    }


def _post_tool_use(
    *,
    session_id: str = "session-private-root",
    turn_id: str = "turn-private-root",
    agent_id: str | None = None,
    agent_type: str | None = None,
    tool_name: str = "shell_command",
    tool_input: object = None,
    tool_response: object = None,
    tool_use_id: str = "tool-private-1",
    model: str = "gpt-5.6-terra",
    permission_mode: str = "bypassPermissions",
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "session_id": session_id,
        "transcript_path": "C:\\private\\tool-rollout.jsonl",
        "cwd": "C:\\private\\tool-workspace",
        "hook_event_name": "PostToolUse",
        "model": model,
        "permission_mode": permission_mode,
        "turn_id": turn_id,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_response": tool_response,
        "tool_use_id": tool_use_id,
    }
    if agent_id is not None:
        receipt["agent_id"] = agent_id
    if agent_type is not None:
        receipt["agent_type"] = agent_type
    return receipt


class FixedConfigurationTests(unittest.TestCase):
    def test_terra_campaign_configuration_is_exact(self) -> None:
        self.assertEqual(codex_harness.CODEX_CLI_VERSION, "0.148.0")
        self.assertEqual(codex_harness.MODEL, "gpt-5.6-terra")
        self.assertEqual(codex_harness.REASONING_EFFORT, "medium")
        self.assertEqual(codex_harness.SANDBOX_MODE, "read-only")
        self.assertEqual(codex_harness.APPROVAL_POLICY, "never")
        self.assertEqual(codex_harness.HOOK_PERMISSION_MODE, "bypassPermissions")
        self.assertEqual(codex_harness.TIMEOUT_SECONDS, 300)
        self.assertEqual(codex_harness.TRIALS, 2)


class JsonlParserTests(unittest.TestCase):
    def test_extracts_last_message_and_completed_command_and_collab_facts(self) -> None:
        command = "Get-Content C:\\private\\SKILL.md"
        output = "safe output from C:\\private\\SKILL.md"
        prompt = "Inspect the routing boundary."
        events = _completed_trace(
            *_command_events(command=command, output=output),
            *_collab_events(prompt=prompt),
            _agent_message("message-1", "first answer"),
            _agent_message("message-2", "final answer"),
        )

        trace = codex_harness.parse_jsonl(_blob(events), process_exit_code=0)

        self.assertEqual(trace.last_agent_message, "final answer")
        self.assertEqual(trace.terminal, "completed")
        self.assertEqual(trace.usage, _usage())
        self.assertEqual(len(trace.command_facts), 1)
        self.assertEqual(trace.command_facts[0].status, "completed")
        self.assertEqual(trace.command_facts[0].exit_code, 0)
        self.assertEqual(
            trace.command_facts[0].command_sha256,
            hashlib.sha256(command.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            trace.command_facts[0].output_sha256,
            hashlib.sha256(output.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(len(trace.collab_tool_facts), 1)
        self.assertEqual(trace.collab_tool_facts[0].tool, "spawn_agent")
        self.assertEqual(trace.collab_tool_facts[0].receiver_count, 1)
        self.assertEqual(trace.collab_tool_facts[0].agent_state_counts, {"completed": 1})
        self.assertEqual(
            trace.collab_tool_facts[0].prompt_sha256,
            hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        )

    def test_malformed_jsonl_fails_closed(self) -> None:
        cases = {
            "invalid-json": "{not json}",
            "non-object": "[]",
            "non-string-event-type": _blob([
                {"type": ["thread.started"]},
            ]),
            "missing-thread-id": _blob([
                {"type": "thread.started"},
                {"type": "turn.started"},
                _agent_message("message-1", "answer"),
                {"type": "turn.completed", "usage": _usage()},
            ]),
            "unknown-event": _blob([
                {"type": "thread.started", "thread_id": "thread-1"},
                {"type": "turn.started"},
                {"type": "turn.paused"},
                _agent_message("message-1", "answer"),
                {"type": "turn.completed", "usage": _usage()},
            ]),
        }
        for label, payload in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(codex_harness.TraceError):
                    codex_harness.parse_jsonl(payload, process_exit_code=0)

    def test_unknown_item_type_fails_closed(self) -> None:
        events = _completed_trace(
            {
                "type": "item.started",
                "item": {"id": "file-change-1", "type": "file_change"},
            },
            {
                "type": "item.completed",
                "item": {"id": "file-change-1", "type": "file_change"},
            },
            _agent_message("message-1", "answer"),
        )

        with self.assertRaisesRegex(codex_harness.TraceError, "unsupported item type"):
            codex_harness.parse_jsonl(_blob(events), process_exit_code=0)

    def test_event_order_and_item_lifecycle_fail_closed(self) -> None:
        valid_message = _agent_message("message-1", "answer")
        cases = {
            "turn-before-thread": [
                {"type": "turn.started"},
                {"type": "thread.started", "thread_id": "thread-1"},
                valid_message,
                {"type": "turn.completed", "usage": _usage()},
            ],
            "item-before-turn": [
                {"type": "thread.started", "thread_id": "thread-1"},
                valid_message,
                {"type": "turn.started"},
                {"type": "turn.completed", "usage": _usage()},
            ],
            "duplicate-thread": [
                {"type": "thread.started", "thread_id": "thread-1"},
                {"type": "thread.started", "thread_id": "thread-2"},
                {"type": "turn.started"},
                valid_message,
                {"type": "turn.completed", "usage": _usage()},
            ],
            "duplicate-turn-start": [
                {"type": "thread.started", "thread_id": "thread-1"},
                {"type": "turn.started"},
                {"type": "turn.started"},
                valid_message,
                {"type": "turn.completed", "usage": _usage()},
            ],
            "completed-command-without-start": _completed_trace(
                _command_events()[1],
                valid_message,
            ),
            "event-after-terminal": [
                *_completed_trace(valid_message),
                {"type": "error", "message": "late error"},
            ],
        }
        for label, events in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(codex_harness.TraceError):
                    codex_harness.parse_jsonl(_blob(events), process_exit_code=0)

    def test_duplicate_terminal_fails_closed(self) -> None:
        events = [
            *_completed_trace(_agent_message("message-1", "answer")),
            {"type": "turn.failed", "error": {"message": "late failure"}},
        ]

        with self.assertRaises(codex_harness.TraceError):
            codex_harness.parse_jsonl(_blob(events), process_exit_code=0)

    def test_terminal_must_match_process_exit_code(self) -> None:
        completed = _completed_trace(_agent_message("message-1", "answer"))
        failed = [
            {"type": "thread.started", "thread_id": "thread-1"},
            {"type": "turn.started"},
            {"type": "turn.failed", "error": {"message": "model unavailable"}},
        ]

        with self.assertRaises(codex_harness.TraceError):
            codex_harness.parse_jsonl(_blob(completed), process_exit_code=1)
        with self.assertRaises(codex_harness.TraceError):
            codex_harness.parse_jsonl(_blob(failed), process_exit_code=0)

        parsed = codex_harness.parse_jsonl(_blob(failed), process_exit_code=1)
        self.assertEqual(parsed.terminal, "failed")
        self.assertIsNone(parsed.last_agent_message)

    def test_credential_shaped_raw_values_fail_closed(self) -> None:
        secret_samples = {
            "openai-key": "sk-proj-abcdefghijklmnopqrstuvwxyz012345",
            "authorization": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
            "password": "password=hunter2",
            "aws-key": "AKIAABCDEFGHIJKLMNOP",
            "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature123",
        }
        for label, secret in secret_samples.items():
            locations = {
                "agent-message": _completed_trace(_agent_message("message-1", secret)),
                "command-output": _completed_trace(
                    *_command_events(output=secret),
                    _agent_message("message-1", "answer"),
                ),
                "collab-prompt": _completed_trace(
                    *_collab_events(prompt=secret),
                    _agent_message("message-1", "answer"),
                ),
            }
            for location, events in locations.items():
                with self.subTest(credential=label, location=location):
                    with self.assertRaises(codex_harness.CredentialExposureError):
                        codex_harness.parse_jsonl(_blob(events), process_exit_code=0)


class SanitizedEvidenceTests(unittest.TestCase):
    def test_persistable_facts_omit_raw_message_prompt_output_paths_and_ids(self) -> None:
        thread_id = "thread-private-123"
        child_id = "child-private-456"
        private_path = "C:\\Users\\private\\save-toolkit\\SKILL.md"
        command = f"Get-Content {private_path}"
        output = f"read {private_path} successfully"
        collab_prompt = "Inspect the private routing boundary."
        response = "The private routing result is complete."
        events = _completed_trace(
            *_command_events(command=command, output=output),
            *_collab_events(prompt=collab_prompt),
            _agent_message("message-private-1", response),
            thread_id=thread_id,
        )
        # Exercise a distinct child identifier without changing the lifecycle shape.
        for event_index, state in ((4, "running"), (5, "completed")):
            events[event_index]["item"]["receiver_thread_ids"] = [child_id]  # type: ignore[index]
            events[event_index]["item"]["agents_states"] = {child_id: state}  # type: ignore[index]

        trace = codex_harness.parse_jsonl(_blob(events), process_exit_code=0)
        facts = trace.persistable_facts()
        serialized = json.dumps(facts, sort_keys=True)

        for raw_value in (
            thread_id,
            child_id,
            private_path,
            command,
            output,
            collab_prompt,
            response,
            "message-private-1",
        ):
            self.assertNotIn(raw_value, serialized)
        self.assertEqual(
            facts["last_agent_message_sha256"],
            hashlib.sha256(response.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            facts["thread_sha256"],
            hashlib.sha256(thread_id.encode("utf-8")).hexdigest(),
        )

    def test_path_fact_contains_a_normalized_digest_without_the_raw_path(self) -> None:
        private_path = Path("C:/Users/private/save-toolkit/SKILL.md")

        fact = codex_harness.sanitized_path_fact("installed_skill", private_path)
        serialized = json.dumps(fact, sort_keys=True)

        self.assertEqual(set(fact), {"label", "path_sha256"})
        self.assertEqual(fact["label"], "installed_skill")
        self.assertRegex(fact["path_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn(str(private_path), serialized)
        self.assertNotIn("SKILL.md", serialized)
        self.assertEqual(
            fact["path_sha256"],
            hashlib.sha256(
                codex_harness.normalized_path_bytes(private_path)
            ).hexdigest(),
        )


class CredentialScannerTests(unittest.TestCase):
    def test_public_scanner_rejects_nested_credentials_before_recording(self) -> None:
        with self.assertRaises(codex_harness.CredentialExposureError):
            codex_harness.reject_credentials(
                {"tool_response": {"details": "password=hunter2"}},
                location="hook-receipt",
            )

    def test_public_scanner_accepts_safe_structured_values(self) -> None:
        result = codex_harness.reject_credentials(
            {"tool_response": {"status": "completed", "count": 2}},
            location="hook-receipt",
        )
        self.assertIsNone(result)

    def test_public_scanner_diagnostic_does_not_echo_untrusted_mapping_keys(self) -> None:
        untrusted_key = "forged-field\nforged-diagnostic"
        with self.assertRaises(codex_harness.CredentialExposureError) as caught:
            codex_harness.reject_credentials(
                {untrusted_key: {"payload": "password=hunter2"}},
                location="hook-receipt",
            )
        self.assertNotIn(untrusted_key, str(caught.exception))


class HookReceiptTests(unittest.TestCase):
    def _valid_receipts(self) -> list[dict[str, object]]:
        return [
            _session_start(),
            _subagent_start(),
            _subagent_start(
                turn_id="turn-private-second-child",
                agent_id="agent-private-2",
                agent_type="save-toolkit-researcher",
            ),
            _post_tool_use(
                tool_input={"command": "Get-Location"},
                tool_response={"exit_code": 0, "output": "safe root output"},
                tool_use_id="tool-private-root",
            ),
            _post_tool_use(
                turn_id="turn-private-child-later",
                agent_id="agent-private-1",
                agent_type="save-toolkit-sre",
                tool_name="view_image",
                tool_input={"path": "C:\\private\\diagram.png"},
                tool_response={"detail": "high", "image": "safe-digest-placeholder"},
                tool_use_id="tool-private-child",
            ),
        ]

    def test_reduces_valid_receipts_and_retains_raw_tool_values_only_transiently(self) -> None:
        receipts = self._valid_receipts()

        parsed = codex_harness.parse_hook_receipts(_blob(receipts))

        self.assertEqual(len(parsed.tool_receipts), 2)
        self.assertEqual(parsed.tool_receipts[0].tool_input, {"command": "Get-Location"})
        self.assertEqual(
            parsed.tool_receipts[0].tool_response,
            {"exit_code": 0, "output": "safe root output"},
        )
        self.assertIsNone(parsed.tool_receipts[0].agent_type)
        self.assertEqual(parsed.tool_receipts[1].agent_type, "save-toolkit-sre")
        self.assertEqual(parsed.tool_receipts[1].tool_name, "view_image")
        self.assertNotIn("Get-Location", repr(parsed))
        self.assertNotIn("safe root output", repr(parsed))

        facts = parsed.persistable_facts()
        self.assertEqual(
            facts["hook_event_counts"],
            {"PostToolUse": 2, "SessionStart": 1, "SubagentStart": 2},
        )
        self.assertEqual(facts["model_counts"], {"gpt-5.6-terra": 5})
        self.assertEqual(
            facts["agent_type_counts"],
            {"save-toolkit-researcher": 1, "save-toolkit-sre": 1},
        )
        self.assertEqual(
            facts["tool_name_counts"],
            {"shell_command": 1, "view_image": 1},
        )
        root_input = {"command": "Get-Location"}
        expected_input_hash = hashlib.sha256(
            json.dumps(
                root_input,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(facts["post_tool_use_facts"][0]["tool_input_sha256"], expected_input_hash)

    def test_nullable_transcript_path_matches_codex_0148_schema(self) -> None:
        receipts = self._valid_receipts()
        for receipt in receipts:
            receipt["transcript_path"] = None

        parsed = codex_harness.parse_hook_receipts(_blob(receipts))

        self.assertEqual(parsed.hook_event_counts["SessionStart"], 1)
        for invalid in ({}, {"transcript_path": ""}, {"transcript_path": []}):
            malformed = _session_start()
            malformed.update(invalid)
            if not invalid:
                del malformed["transcript_path"]
            with self.subTest(invalid=invalid):
                with self.assertRaises(codex_harness.HookReceiptError):
                    codex_harness.parse_hook_receipts(_blob([malformed]))

    def test_persistable_hook_facts_omit_all_raw_ids_paths_inputs_and_responses(self) -> None:
        parsed = codex_harness.parse_hook_receipts(_blob(self._valid_receipts()))

        serialized = json.dumps(parsed.persistable_facts(), sort_keys=True)

        for raw_value in (
            "session-private-root",
            "turn-private-root",
            "turn-private-child-start",
            "turn-private-child-later",
            "agent-private-1",
            "agent-private-2",
            "tool-private-root",
            "tool-private-child",
            "C:\\private\\root-rollout.jsonl",
            "C:\\private\\root-workspace",
            "C:\\private\\diagram.png",
            "Get-Location",
            "safe root output",
            "safe-digest-placeholder",
        ):
            self.assertNotIn(raw_value, serialized)
        self.assertIn("save-toolkit-sre", serialized)
        self.assertIn("gpt-5.6-terra", serialized)
        self.assertIn("view_image", serialized)

    def test_root_session_receipt_is_required_once_and_first(self) -> None:
        cases = {
            "missing": [_subagent_start()],
            "duplicate": [_session_start(), _session_start()],
            "late": [_subagent_start(), _session_start()],
        }
        for label, receipts in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(codex_harness.HookReceiptError):
                    codex_harness.parse_hook_receipts(_blob(receipts))

    def test_wrong_or_mixed_model_and_permission_fail_closed(self) -> None:
        cases = {
            "wrong-root-model": [_session_start(model="gpt-5.6-sol")],
            "mixed-child-model": [
                _session_start(),
                _subagent_start(model="gpt-5.6-sol"),
            ],
            "wrong-root-permission": [_session_start(permission_mode="workspace-write")],
            "sandbox-label-is-not-hook-mode": [_session_start(permission_mode="read-only")],
            "mixed-child-permission": [
                _session_start(),
                _subagent_start(permission_mode="workspace-write"),
            ],
        }
        for label, receipts in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(codex_harness.HookReceiptError):
                    codex_harness.parse_hook_receipts(_blob(receipts))

    def test_duplicate_or_conflicting_subagent_identity_fails_closed(self) -> None:
        duplicate = [
            _session_start(),
            _subagent_start(),
            _subagent_start(turn_id="turn-private-repeated"),
        ]
        conflicting = [
            _session_start(),
            _subagent_start(),
            _subagent_start(
                turn_id="turn-private-repeated",
                agent_type="save-toolkit-researcher",
            ),
        ]
        for label, receipts in (("duplicate", duplicate), ("conflicting", conflicting)):
            with self.subTest(label=label):
                with self.assertRaises(codex_harness.HookReceiptError):
                    codex_harness.parse_hook_receipts(_blob(receipts))

    def test_post_tool_use_agent_identity_and_tool_use_id_must_be_consistent(self) -> None:
        cases = {
            "unknown-agent": [
                _session_start(),
                _post_tool_use(
                    agent_id="agent-private-unknown",
                    agent_type="save-toolkit-sre",
                ),
            ],
            "wrong-agent-type": [
                _session_start(),
                _subagent_start(),
                _post_tool_use(
                    agent_id="agent-private-1",
                    agent_type="save-toolkit-researcher",
                ),
            ],
            "partial-agent-identity": [
                _session_start(),
                _post_tool_use(agent_id="agent-private-1"),
            ],
            "duplicate-tool-use": [
                _session_start(),
                _post_tool_use(tool_use_id="tool-private-duplicate"),
                _post_tool_use(tool_use_id="tool-private-duplicate"),
            ],
            "wrong-session": [
                _session_start(),
                _post_tool_use(session_id="session-private-other"),
            ],
        }
        for label, receipts in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(codex_harness.HookReceiptError):
                    codex_harness.parse_hook_receipts(_blob(receipts))

    def test_unknown_event_malformed_fields_and_raw_credentials_fail_closed(self) -> None:
        unknown = _session_start()
        unknown["hook_event_name"] = "PreToolUse"
        missing_turn = _post_tool_use()
        del missing_turn["turn_id"]
        missing_response = _post_tool_use()
        del missing_response["tool_response"]
        credential = _post_tool_use(tool_response={"authorization": "Bearer abcdefghijklmnop"})
        path_agent_type = _subagent_start(agent_type="C:\\private\\agent")
        path_tool_name = _post_tool_use(tool_name="../private/tool")
        cases = {
            "unknown-event": [_session_start(), unknown],
            "missing-turn": [_session_start(), missing_turn],
            "missing-response": [_session_start(), missing_response],
            "credential": [_session_start(), credential],
            "path-agent-type": [_session_start(), path_agent_type],
            "path-tool-name": [_session_start(), path_tool_name],
        }
        for label, receipts in cases.items():
            expected_error = (
                codex_harness.CredentialExposureError
                if label == "credential"
                else codex_harness.HookReceiptError
            )
            with self.subTest(label=label):
                with self.assertRaises(expected_error):
                    codex_harness.parse_hook_receipts(_blob(receipts))


if __name__ == "__main__":
    unittest.main(verbosity=2)
