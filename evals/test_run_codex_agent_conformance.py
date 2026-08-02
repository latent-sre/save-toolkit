"""Offline contract tests for the Codex/Sol custom-agent conformance runner."""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_codex_agent_conformance as conformance


class CodexAgentConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = conformance.load_manifest(conformance.DEFAULT_MANIFEST)
        self.lane = next(
            lane for lane in self.manifest["lanes"] if lane["agent"] == "reviewer"
        )
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
                    "type": "agent_message",
                    "author": "/root/reviewer_canary",
                    "recipient": "/root",
                    "content": [
                        {"type": "input_text", "text": self.lane["child_expected"]}
                    ],
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
        self.assertEqual(
            set(self.manifest["agents"]),
            {lane["agent"] for lane in self.manifest["lanes"]},
        )
        self.assertGreaterEqual(len(self.manifest["lanes"]), len(self.manifest["agents"]))
        self.assertEqual(
            {"repository-investigator", "researcher", "reviewer", "scribe"},
            {
                lane["agent"]
                for lane in self.manifest["lanes"]
                if lane["kind"] == "agent-behavior"
            },
        )
        self.assertTrue(all(lane["model"] == "gpt-5.6-sol" for lane in self.manifest["lanes"]))
        self.assertTrue(
            all(lane["child_expected"] not in lane["prompt"] for lane in self.manifest["lanes"])
        )
        reviewer_behavior = next(
            lane
            for lane in self.manifest["lanes"]
            if lane["id"] == "codex-sol-reviewer-authz-review"
        )
        self.assertEqual("agent-behavior", reviewer_behavior["kind"])
        self.assertEqual(
            {
                "verdict": "REQUEST CHANGES",
                "finding": "missing_object_level_authorization",
                "executed": False,
                "delegated": False,
            },
            reviewer_behavior["expected"]["child_result"],
        )
        scribe_behavior = next(
            lane
            for lane in self.manifest["lanes"]
            if lane["id"] == "codex-sol-scribe-unverified-command"
        )
        self.assertEqual("agent-behavior", scribe_behavior["kind"])
        self.assertEqual(
            {
                "disposition": "document_unverified",
                "command_evidence": "unverified",
                "executed": False,
                "delegated": False,
            },
            scribe_behavior["expected"]["child_result"],
        )

    def test_manifest_rejects_prompt_that_discloses_child_canary(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        lane = next(lane for lane in manifest["lanes"] if lane["agent"] == "reviewer")
        lane["prompt"] += " " + lane["child_expected"]
        with self.assertRaises(conformance.base.ConformanceError):
            conformance.validate_manifest(manifest)

    def test_behavior_lane_requires_matching_structured_parent_oracle(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        lane = next(lane for lane in manifest["lanes"] if lane["kind"] == "agent-behavior")
        lane["expected"]["child_result"] = {"disposition": "comply"}
        with self.assertRaisesRegex(
            conformance.base.ConformanceError, "behavioral parent and child oracles differ"
        ):
            conformance.validate_manifest(manifest)

    def test_manifest_requires_bound_task_name(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        lane = next(lane for lane in manifest["lanes"] if lane["agent"] == "reviewer")
        lane["prompt"] = lane["prompt"].replace("reviewer_canary", "the child task")
        with self.assertRaises(conformance.base.ConformanceError):
            conformance.validate_manifest(manifest)

    def test_valid_parent_child_delegation_passes(self) -> None:
        score = self._score()
        self.assertEqual("pass", score.verdict)
        self.assertEqual(("gpt-5.6-sol",), score.observed_models)
        self.assertTrue(score.diagnostics["spawn_succeeded"])
        self.assertTrue(score.diagnostics["wait_succeeded"])
        self.assertEqual(1, score.diagnostics["parent_child_delivery_count"])
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

    def test_explicit_wait_is_optional_after_direct_child_delivery(self) -> None:
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
        self.assertEqual("pass", score.verdict)
        self.assertFalse(score.diagnostics["wait_succeeded"])

    def test_parent_must_receive_child_completion(self) -> None:
        parent = self._parent()
        parent[:] = [
            row
            for row in parent
            if not (
                row.get("type") == "response_item"
                and isinstance(row.get("payload"), dict)
                and row["payload"].get("type") == "agent_message"
            )
        ]
        score = self._score(parent=parent)
        self.assertEqual("fail", score.verdict)
        self.assertEqual(0, score.diagnostics["parent_child_delivery_count"])

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
        self.assertNotIn("--ignore-user-config", command)
        self.assertIn("multi_agent", command)
        self.assertIn("--strict-config", command)
        expected_config = {
            "agents.max_concurrent_threads_per_session=1",
            "agents.max_depth=1",
            "features.multi_agent_v2.max_concurrent_threads_per_session=2",
            "features.rollout_budget.enabled=true",
            f"features.rollout_budget.limit_tokens={conformance.base.ROLLOUT_BUDGET_LIMIT_TOKENS}",
            "features.rollout_budget.reminder_at_remaining_tokens=[70000,35000,10000]",
            "features.rollout_budget.sampling_token_weight=1.0",
            "features.rollout_budget.prefill_token_weight=1.0",
        }
        self.assertTrue(expected_config.issubset(command))
        self.assertTrue(
            all(command.index(value) < command.index("exec") for value in expected_config)
        )
        self.assertIn("gpt-5.6-sol", command)
        self.assertLess(command.index("--ask-for-approval"), command.index("exec"))
        self.assertFalse(hasattr(conformance._parser().parse_args(["--run"]), "target_root"))

    def test_live_agent_cli_requires_local_codex_authentication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary).resolve() / "missing-auth.json"
            stderr = io.StringIO()
            with (
                mock.patch("sys.stderr", stderr),
                mock.patch.object(conformance.shutil, "which", return_value="codex"),
            ):
                status = conformance.main(
                    [
                        "--run",
                        "--auth-file",
                        str(missing),
                        "--allow-dirty-plugin",
                        "--allow-dirty-agents",
                        "--allow-dirty-harness",
                    ]
                )
        self.assertEqual(2, status)
        self.assertIn("run `codex login`", stderr.getvalue())

    def test_live_agent_runner_refuses_an_external_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary).resolve() / "candidate"
            auth = Path(temporary).resolve() / "auth.json"
            candidate.mkdir()
            auth.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(
                conformance.base.ConformanceError, "local repository checkout"
            ):
                conformance.run_live(
                    candidate,
                    self.manifest,
                    executable="codex",
                    auth_file=auth,
                    require_clean_plugin=False,
                    require_clean_agents=False,
                    require_clean_harness=False,
                )

    def test_live_agent_cli_never_overwrites_auth_with_report_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            auth = Path(temporary).resolve() / "auth.json"
            original = b'{"session":"keep-me"}'
            auth.write_bytes(original)
            stderr = io.StringIO()
            with mock.patch("sys.stderr", stderr):
                status = conformance.main(
                    ["--run", "--auth-file", str(auth), "--output", str(auth)]
                )
            self.assertEqual(original, auth.read_bytes())
        self.assertEqual(2, status)
        self.assertIn("output path already exists", stderr.getvalue())

    def test_agent_snapshot_rejects_unknown_runtime_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary).resolve() / "candidate"
            (candidate / conformance.base.MARKETPLACE_MANIFEST.parent).mkdir(parents=True)
            conformance.shutil.copy2(
                conformance.REPO_ROOT / conformance.base.MARKETPLACE_MANIFEST,
                candidate / conformance.base.MARKETPLACE_MANIFEST,
            )
            conformance.shutil.copytree(
                conformance.REPO_ROOT / conformance.base.PLUGIN_DIRECTORY,
                candidate / conformance.base.PLUGIN_DIRECTORY,
            )
            conformance.shutil.copytree(
                conformance.REPO_ROOT / conformance.AGENT_SOURCE_DIRECTORY,
                candidate / conformance.AGENT_SOURCE_DIRECTORY,
            )
            conformance.validate_local_contract(candidate, self.manifest)

            reviewer = candidate / conformance.AGENT_SOURCE_DIRECTORY / "reviewer.toml"
            reviewer.write_text(
                reviewer.read_text(encoding="utf-8") + '\nmodel = "untrusted-model"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(conformance.base.ConformanceError, "active or unknown"):
                conformance.validate_local_contract(candidate, self.manifest)

    def test_local_live_agent_reduction_deletes_auth_and_model_text(self) -> None:
        root = conformance.REPO_ROOT
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary).resolve()
            auth_file = temporary_root / "auth.json"
            auth_marker = "local-agent-auth-marker"
            auth_file.write_text(
                json.dumps({"session": auth_marker}), encoding="utf-8"
            )
            manifest = copy.deepcopy(self.manifest)
            manifest["lanes"] = [copy.deepcopy(self.lane)]
            observed_homes: list[Path] = []

            def runner(argv, cwd, timeout, child_env):
                del cwd, timeout
                codex_home = Path(child_env["CODEX_HOME"])
                observed_homes.append(codex_home)
                if "exec" in argv:
                    self.assertEqual(
                        auth_file.read_bytes(), (codex_home / "auth.json").read_bytes()
                    )
                else:
                    self.assertFalse((codex_home / "auth.json").exists())
                if tuple(argv[-1:]) == ("--version",):
                    return conformance.base.CommandResult(0, "codex-cli 0.test\n", "")
                if tuple(argv[1:4]) == ("plugin", "marketplace", "add"):
                    return conformance.base.CommandResult(0, "{}", "")
                if tuple(argv[1:3]) == ("plugin", "add"):
                    installed = codex_home / "plugins" / "cache" / "sre-agents"
                    conformance.shutil.copytree(
                        root / conformance.base.PLUGIN_DIRECTORY, installed
                    )
                    return conformance.base.CommandResult(
                        0,
                        json.dumps(
                            {
                                "pluginId": "sre-agents@latent-sre",
                                "name": "sre-agents",
                                "version": "1.0.0",
                                "installedPath": str(installed),
                            }
                        ),
                        "",
                    )
                if tuple(argv[1:4]) == ("plugin", "list", "--json"):
                    return conformance.base.CommandResult(
                        0,
                        json.dumps(
                            {
                                "installed": [
                                    {
                                        "pluginId": "sre-agents@latent-sre",
                                        "name": "sre-agents",
                                        "version": "1.0.0",
                                        "marketplaceName": "latent-sre",
                                        "installed": True,
                                        "enabled": True,
                                    }
                                ]
                            }
                        ),
                        "",
                    )

                instructions = conformance._agent_document(
                    codex_home / "agents" / "reviewer.toml"
                )["developer_instructions"]
                session_root = codex_home / "sessions"
                session_root.mkdir()
                for name, rows in (
                    ("parent.jsonl", self._parent()),
                    ("child.jsonl", self._child(instructions=instructions)),
                ):
                    (session_root / name).write_text(
                        "\n".join(json.dumps(row) for row in rows) + "\n",
                        encoding="utf-8",
                    )
                stdout = "\n".join(
                    (
                        json.dumps(
                            {"type": "thread.started", "thread_id": self.parent_thread}
                        ),
                        json.dumps(
                            {
                                "type": "item.completed",
                                "item": {
                                    "type": "agent_message",
                                    "text": json.dumps(self.lane["expected"]),
                                },
                            }
                        ),
                        json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}),
                    )
                )
                return conformance.base.CommandResult(0, stdout, "")

            report = conformance.run_live(
                root,
                manifest,
                executable="codex",
                auth_file=auth_file,
                require_clean_plugin=False,
                require_clean_agents=False,
                require_clean_harness=False,
                runner=runner,
            )

        self.assertTrue(observed_homes)
        self.assertTrue(all(not home.exists() for home in observed_homes))
        self.assertEqual("local-same-user", report["execution_trust"])
        self.assertEqual("not-proven", report["auth_isolation"])
        self.assertEqual("not-verified-by-runner", report["source_review"])
        self.assertFalse(report["independent_evaluator"])
        self.assertFalse(report["baseline_eligible"])
        self.assertFalse(report["release_granted"])
        self.assertEqual(
            not (
                report["plugin_inputs_dirty"]
                or report["agent_inputs_dirty"]
                or report["harness_inputs_dirty"]
            ),
            report["exact_revision"],
        )
        self.assertEqual(
            conformance.base._git_value(root, ["rev-parse", "HEAD^{tree}"]),
            report["repository_tree"],
        )
        self.assertEqual(
            conformance.base._git_value(conformance.REPO_ROOT, ["rev-parse", "HEAD"]),
            report["evaluator_commit"],
        )
        self.assertEqual(
            report["evaluator_commit"], report["evidence"]["source"]["evaluator_revision"]
        )
        result = report["results"][0]
        self.assertTrue(result["response_matched"])
        self.assertEqual(64, len(result["response_sha256"]))
        for forbidden in ("response", "expected", "observed_models", "usage"):
            self.assertNotIn(forbidden, result)
        rendered = json.dumps(report)
        self.assertNotIn(json.dumps(self.lane["expected"]), rendered)
        self.assertNotIn(auth_marker, rendered)
        self.assertNotIn(str(auth_file), rendered)

    def test_rollout_reader_rejects_malformed_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "sessions" / "bad.jsonl"
            path.parent.mkdir()
            path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaises(conformance.base.ConformanceError):
                conformance._read_rollouts(path.parent)

    def test_rollout_reader_rejects_credential_shaped_output_without_echoing_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "sessions" / "leak.jsonl"
            path.parent.mkdir()
            marker = "sk-proj-0123456789abcdefghijklmnop"
            path.write_text(json.dumps({"payload": marker}) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(
                conformance.base.CredentialOutputError, "credential-shaped material detected"
            ) as raised:
                conformance._read_rollouts(path.parent)
            self.assertNotIn(marker, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
