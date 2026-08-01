"""Offline contracts for the isolated Codex/Sol conformance runner."""

from __future__ import annotations

import copy
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_codex_conformance as conformance


ROOT = Path(__file__).resolve().parents[1]


class CodexConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = conformance.load_manifest(conformance.DEFAULT_MANIFEST)
        self.lane = self.manifest["lanes"][0]

    def _reference_lane(self, lane_id: str = "codex-sol-backend-api-reference"):
        return next(lane for lane in self.manifest["lanes"] if lane["id"] == lane_id)

    def test_manifest_is_sol_only_and_preserves_runtime_boundaries(self) -> None:
        self.assertEqual("gpt-5.6-sol", self.lane["model"])
        self.assertEqual("high", self.lane["reasoning_effort"])
        self.assertEqual("read-only", self.lane["sandbox"])
        self.assertEqual("never", self.lane["approval_policy"])

        wrong_model = copy.deepcopy(self.manifest)
        wrong_model["lanes"][0]["model"] = "claude-opus-5"
        with self.assertRaisesRegex(conformance.ConformanceError, "gpt-5.6-sol"):
            conformance.validate_manifest(wrong_model)

        wrong_sandbox = copy.deepcopy(self.manifest)
        wrong_sandbox["lanes"][0]["sandbox"] = "workspace-write"
        with self.assertRaisesRegex(conformance.ConformanceError, "read-only"):
            conformance.validate_manifest(wrong_sandbox)

        wrong_effort = copy.deepcopy(self.manifest)
        wrong_effort["lanes"][0]["reasoning_effort"] = "medium"
        with self.assertRaisesRegex(conformance.ConformanceError, "high"):
            conformance.validate_manifest(wrong_effort)

        no_required = copy.deepcopy(self.manifest)
        no_required["lanes"][0]["required"] = False
        for lane in no_required["lanes"]:
            lane["required"] = False
        with self.assertRaisesRegex(conformance.ConformanceError, "required lane"):
            conformance.validate_manifest(no_required)

        traversal = copy.deepcopy(self.manifest)
        self._lane_from(traversal, "codex-sol-backend-api-reference")["references"] = [
            "../auth.json"
        ]
        with self.assertRaisesRegex(conformance.ConformanceError, "reference path"):
            conformance.validate_manifest(traversal)

        missing_read = copy.deepcopy(self.manifest)
        direct_lane = self._lane_from(missing_read, "codex-sol-release-gate-missing-rollback")
        direct_lane["prompt"] = "Use $release-gate. Return the gate verdict."
        with self.assertRaisesRegex(conformance.ConformanceError, "exact installed-skill read"):
            conformance.validate_manifest(missing_read)

        contradictory_read = copy.deepcopy(self.manifest)
        direct_lane = self._lane_from(
            contradictory_read, "codex-sol-release-gate-missing-rollback"
        )
        direct_lane["prompt"] += " Do not run a command."
        with self.assertRaisesRegex(conformance.ConformanceError, "must not forbid"):
            conformance.validate_manifest(contradictory_read)

    @staticmethod
    def _lane_from(manifest, lane_id):
        return next(lane for lane in manifest["lanes"] if lane["id"] == lane_id)

    def test_exec_command_places_approval_policy_before_subcommand(self) -> None:
        command = conformance.build_exec_command(
            "C:/tools/codex.exe", Path("C:/fixture"), self.lane
        )
        self.assertLess(command.index("--ask-for-approval"), command.index("exec"))
        self.assertEqual("never", command[command.index("--ask-for-approval") + 1])
        self.assertEqual("gpt-5.6-sol", command[command.index("--model") + 1])
        self.assertEqual("read-only", command[command.index("--sandbox") + 1])
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--strict-config", command)
        disabled = [
            command[index + 1]
            for index, argument in enumerate(command[:-1])
            if argument == "--disable"
        ]
        self.assertEqual(["multi_agent_v2", "multi_agent"], disabled)
        expected_config = {
            "agents.enabled=false",
            "features.rollout_budget.enabled=true",
            f"features.rollout_budget.limit_tokens={conformance.ROLLOUT_BUDGET_LIMIT_TOKENS}",
            "features.rollout_budget.reminder_at_remaining_tokens=[70000,35000,10000]",
            "features.rollout_budget.sampling_token_weight=1.0",
            "features.rollout_budget.prefill_token_weight=1.0",
        }
        self.assertTrue(expected_config.issubset(command))
        self.assertTrue(
            all(command.index(value) < command.index("exec") for value in expected_config)
        )
        self.assertTrue(
            all(
                reminder < conformance.ROLLOUT_BUDGET_LIMIT_TOKENS
                for reminder in conformance.ROLLOUT_BUDGET_REMINDER_TOKENS
            )
        )
        self.assertNotIn("--ignore-user-config", command)
        self.assertEqual("--", command[-2])
        self.assertEqual(self.lane["prompt"], command[-1])
        args = conformance._parser().parse_args(["--run"])
        self.assertFalse(args.allow_dirty_plugin)
        self.assertFalse(args.allow_dirty_harness)
        self.assertEqual(ROOT, args.target_root)

    def test_live_cli_refuses_without_trusted_broker_config(self) -> None:
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            status = conformance.main(["--run"])
        self.assertEqual(2, status)
        self.assertIn("--run requires --broker-config", stderr.getvalue())

    def test_live_cli_refuses_candidate_and_evaluator_in_same_checkout(self) -> None:
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            status = conformance.main(
                ["--run", "--broker-config", str(ROOT / "config.toml")]
            )
        self.assertEqual(2, status)
        self.assertIn("separate candidate checkout", stderr.getvalue())

    def test_live_candidate_reproves_exact_raw_materialization(self) -> None:
        marker = {
            "schema_version": 1,
            "repository_commit": "1" * 40,
            "repository_tree": "2" * 40,
            "paths": list(conformance.CANDIDATE_MATERIALIZATION_PATHS),
            "entry_count": 3,
            "byte_count": 100,
            "selection_sha256": "3" * 64,
            "filters_executed": False,
            "links_materialized": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary).resolve() / "candidate"
            with mock.patch.object(
                conformance.materialize_git_tree,
                "verify_materialization",
                return_value=marker,
            ) as verify:
                self.assertEqual(marker, conformance.validate_candidate_materialization(candidate))
                verify.assert_called_once_with(
                    candidate, conformance.CANDIDATE_MATERIALIZATION_PATHS
                )

            with mock.patch.object(
                conformance.materialize_git_tree,
                "verify_materialization",
                side_effect=conformance.materialize_git_tree.MaterializationError(
                    "materialized bytes differ from the Git blob"
                ),
            ):
                with self.assertRaisesRegex(conformance.ConformanceError, "bytes differ"):
                    conformance.validate_candidate_materialization(candidate)

    def test_windows_command_path_normalization_collapses_codex_escaping(self) -> None:
        escaped = r'C:\\isolated\\session\\resources\\skills\\stack-profile\\SKILL.md'
        normal = r'C:\isolated\session\resources\skills\stack-profile\SKILL.md'
        self.assertEqual(
            conformance._normalized_windows_pathish(normal),
            conformance._normalized_windows_pathish(escaped),
        )

    def test_parse_trace_captures_completed_skill_read_and_oracle(self) -> None:
        skill_path = Path(
            "C:/isolated/plugins/cache/latent-sre/sre-agents/1.0.0/"
            "skills/stack-profile/SKILL.md"
        )
        skill_text = "profile canary: sp_7c2e\n"
        trace = "\n".join(
            (
                json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-0",
                            "type": "command_execution",
                            "command": f"Get-Content -Raw '{skill_path}'",
                            # Codex's PowerShell command adapter appends one transport newline to
                            # output that already ends in LF. The content comparator must account
                            # for that framing without allowing arbitrary extra output.
                            "aggregated_output": skill_text + "\r\n",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item-1",
                            "type": "agent_message",
                            "text": json.dumps(self.lane["expected"]),
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {"input_tokens": 10, "output_tokens": 4},
                    }
                ),
            )
        )
        parsed = conformance.parse_codex_jsonl(trace)
        score = conformance.score_trace(
            parsed,
            lane=self.lane,
            installed_skill=skill_path,
            expected_skill_text=skill_text,
            returncode=0,
            stderr="",
            timed_out=False,
        )
        self.assertEqual("pass", score.verdict)
        self.assertTrue(score.skill_read_verified)
        self.assertEqual(self.lane["expected"], score.response)
        self.assertEqual(10, parsed["usage"]["input_tokens"])

    def test_oracle_without_verified_skill_read_fails(self) -> None:
        trace = "\n".join(
            (
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "agent_message",
                            "text": json.dumps(self.lane["expected"]),
                        },
                    }
                ),
                json.dumps({"type": "turn.completed", "usage": {}}),
            )
        )
        score = conformance.score_trace(
            conformance.parse_codex_jsonl(trace),
            lane=self.lane,
            installed_skill=Path("C:/cache/stack-profile/SKILL.md"),
            expected_skill_text="profile canary: sp_7c2e\n",
            returncode=0,
            stderr="",
            timed_out=False,
        )
        self.assertEqual("fail", score.verdict)
        self.assertFalse(score.skill_read_verified)

    def test_multiple_commands_fail_with_sanitized_per_command_diagnostics(self) -> None:
        skill_path = Path("C:/isolated/skills/stack-profile/SKILL.md")
        skill_text = "profile canary: sp_7c2e\n"
        command = {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": f"Get-Content -Raw '{skill_path}'",
                "aggregated_output": skill_text,
                "exit_code": 0,
                "status": "completed",
            },
        }
        trace = "\n".join(
            (
                json.dumps(command),
                json.dumps(command),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "agent_message",
                            "text": json.dumps(self.lane["expected"]),
                        },
                    }
                ),
                json.dumps({"type": "turn.completed", "usage": {}}),
            )
        )
        score = conformance.score_trace(
            conformance.parse_codex_jsonl(trace),
            lane=self.lane,
            installed_skill=skill_path,
            expected_skill_text=skill_text,
            returncode=0,
            stderr="",
            timed_out=False,
        )
        self.assertEqual("fail", score.verdict)
        self.assertEqual(2, score.skill_read_diagnostics["command_count"])
        diagnostics = score.skill_read_diagnostics["commands"]
        self.assertEqual(2, len(diagnostics))
        self.assertTrue(all(item["path_matched"] for item in diagnostics))
        self.assertTrue(all("command_sha256" in item for item in diagnostics))
        self.assertTrue(all("command" not in item for item in diagnostics))

    def test_windows_powershell_legacy_decode_is_an_exact_accepted_rendering(self) -> None:
        skill_path = Path("C:/isolated/plugins/cache/latent-sre/sre-agents/1.0.0/skills/stack-profile/SKILL.md")
        skill_text = "stack profile — profile canary: sp_7c2e\n"
        powershell_text = skill_text.encode("utf-8").decode("cp1252") + "\r\n"
        trace = "\n".join(
            (
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": f"Get-Content -Raw '\\\\?\\{skill_path}'",
                            "aggregated_output": powershell_text,
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
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
                json.dumps({"type": "turn.completed", "usage": {}}),
            )
        )
        score = conformance.score_trace(
            conformance.parse_codex_jsonl(trace),
            lane=self.lane,
            installed_skill=skill_path,
            expected_skill_text=skill_text,
            returncode=0,
            stderr="",
            timed_out=False,
        )
        self.assertEqual("pass", score.verdict)
        self.assertTrue(score.skill_read_verified)

    def test_windows_powershell_preserves_undefined_cp1252_bytes(self) -> None:
        skill_path = Path("C:/isolated/skills/stack-profile/SKILL.md")
        skill_text = "warning \u26a0\ufe0f profile canary: sp_7c2e\n"
        powershell_text = conformance._dotnet_windows_1252_decode(
            skill_text.encode("utf-8")
        ) + "\r\n"
        self.assertTrue(conformance._command_output_matches(powershell_text, skill_text))

        trace = "\n".join(
            (
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": f"Get-Content -Raw '{skill_path}'",
                            "aggregated_output": powershell_text,
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
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
                json.dumps({"type": "turn.completed", "usage": {}}),
            )
        )
        score = conformance.score_trace(
            conformance.parse_codex_jsonl(trace),
            lane=self.lane,
            installed_skill=skill_path,
            expected_skill_text=skill_text,
            returncode=0,
            stderr="",
            timed_out=False,
        )
        self.assertEqual("pass", score.verdict)

    def test_frozen_marketplace_source_is_allowed_but_unrelated_copy_is_not(self) -> None:
        installed = Path(
            "C:/isolated/codex-home/plugins/cache/latent-sre/sre-agents/1.0.0/"
            "skills/stack-profile/SKILL.md"
        )
        frozen = Path("C:/isolated/marketplace/plugins/sre-agents/skills/stack-profile/SKILL.md")
        staged = Path("C:/isolated/session/resources/skills/stack-profile/SKILL.md")
        unrelated = Path("C:/Users/operator/.codex/skills/stack-profile/SKILL.md")
        skill_text = "profile canary: sp_7c2e\n"

        def score_for(path: Path):
            trace = "\n".join(
                (
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "command_execution",
                                "command": f"Get-Content -Raw '{path}'",
                                "aggregated_output": skill_text,
                                "exit_code": 0,
                                "status": "completed",
                            },
                        }
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
                    json.dumps({"type": "turn.completed", "usage": {}}),
                )
            )
            return conformance.score_trace(
                conformance.parse_codex_jsonl(trace),
                lane=self.lane,
                allowed_skill_paths={"installed-cache": installed, "frozen-marketplace": frozen},
                isolated_root=Path("C:/isolated"),
                expected_skill_text=skill_text,
                returncode=0,
                stderr="",
                timed_out=False,
            )

        self.assertEqual("pass", score_for(frozen).verdict)
        self.assertEqual("frozen-marketplace", score_for(frozen).skill_read_diagnostics["matched_scope"])
        self.assertEqual("pass", score_for(staged).verdict)
        self.assertEqual("host-staged-isolated", score_for(staged).skill_read_diagnostics["matched_scope"])
        self.assertEqual("fail", score_for(unrelated).verdict)

    def test_chained_auth_read_cannot_pass_as_a_skill_read(self) -> None:
        skill_path = Path("C:/isolated/skills/stack-profile/SKILL.md")
        skill_text = "profile canary: sp_7c2e\n"
        trace = "\n".join(
            (
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": (
                                "Get-Content -Raw 'C:/isolated/codex-home/auth.json' > $null; "
                                f"Get-Content -Raw '{skill_path}'"
                            ),
                            "aggregated_output": skill_text,
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
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
                json.dumps({"type": "turn.completed", "usage": {}}),
            )
        )
        score = conformance.score_trace(
            conformance.parse_codex_jsonl(trace),
            lane=self.lane,
            installed_skill=skill_path,
            expected_skill_text=skill_text,
            returncode=0,
            stderr="",
            timed_out=False,
        )
        self.assertEqual("fail", score.verdict)
        self.assertFalse(score.skill_read_verified)

    def test_incomplete_or_malformed_trace_is_inconclusive(self) -> None:
        expected = json.dumps(self.lane["expected"])
        for trace in (
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": expected},
                }
            ),
            "not-json\n" + json.dumps({"type": "turn.completed", "usage": {}}),
            "\n".join(
                (
                    json.dumps(
                        {
                            "type": "item.started",
                            "item": {"id": "command-1", "type": "command_execution"},
                        }
                    ),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"type": "agent_message", "text": expected},
                        }
                    ),
                    json.dumps({"type": "turn.completed", "usage": {}}),
                )
            ),
        ):
            score = conformance.score_trace(
                conformance.parse_codex_jsonl(trace),
                lane=self.lane,
                installed_skill=Path("C:/cache/stack-profile/SKILL.md"),
                expected_skill_text="profile canary: sp_7c2e\n",
                returncode=0,
                stderr="",
                timed_out=False,
            )
            self.assertEqual("inconclusive", score.verdict)

    def test_exact_json_oracle_rejects_surrounding_prose(self) -> None:
        skill_path = Path("C:/cache/stack-profile/SKILL.md")
        skill_text = "profile canary: sp_7c2e\n"
        trace = "\n".join(
            (
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": f"Get-Content -Raw '{skill_path}'",
                            "aggregated_output": skill_text,
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "agent_message",
                            "text": "Result: " + json.dumps(self.lane["expected"]),
                        },
                    }
                ),
                json.dumps({"type": "turn.completed", "usage": {}}),
            )
        )
        score = conformance.score_trace(
            conformance.parse_codex_jsonl(trace),
            lane=self.lane,
            installed_skill=skill_path,
            expected_skill_text=skill_text,
            returncode=0,
            stderr="",
            timed_out=False,
        )
        self.assertEqual("fail", score.verdict)

    def test_nested_observed_model_is_not_missed(self) -> None:
        parsed = conformance.parse_codex_jsonl(
            json.dumps({"type": "thread.started", "metadata": {"model": "gpt-test-model"}})
        )
        self.assertEqual(["gpt-test-model"], parsed["observed_models"])

    def test_reference_lane_requires_full_skill_and_reference_reads(self) -> None:
        lane = self._reference_lane()
        installed_root = Path("C:/isolated/codex-home/plugins/cache/sre-agents")
        frozen_root = Path("C:/isolated/marketplace/plugins/sre-agents")
        artifact_texts = {
            "skills/backend-craft/SKILL.md": "backend skill\n",
            "skills/backend-craft/references/api-design.md": "api reference\n",
        }
        artifact_paths = {
            relative: {
                "installed-cache": installed_root / Path(relative),
                "frozen-marketplace": frozen_root / Path(relative),
            }
            for relative in artifact_texts
        }

        def trace(include_reference: bool) -> str:
            events = []
            selected = list(artifact_texts)
            if not include_reference:
                selected = selected[:1]
            for index, relative in enumerate(selected):
                events.append(
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "id": f"command-{index}",
                                "type": "command_execution",
                                "command": f"Get-Content -Raw '{artifact_paths[relative]['installed-cache']}'",
                                "aggregated_output": artifact_texts[relative],
                                "exit_code": 0,
                                "status": "completed",
                            },
                        }
                    )
                )
            events.extend(
                (
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "agent_message",
                                "text": json.dumps(lane["expected"]),
                            },
                        }
                    ),
                    json.dumps({"type": "turn.completed", "usage": {}}),
                )
            )
            return "\n".join(events)

        passed = conformance.score_reference_trace(
            conformance.parse_codex_jsonl(trace(True)),
            lane=lane,
            artifact_texts=artifact_texts,
            artifact_paths=artifact_paths,
            isolated_root=Path("C:/isolated"),
            returncode=0,
            stderr="",
            timed_out=False,
        )
        self.assertEqual("pass", passed.verdict)
        self.assertTrue(passed.skill_read_verified)
        self.assertEqual(2, passed.skill_read_diagnostics["verified_artifact_count"])

        missing = conformance.score_reference_trace(
            conformance.parse_codex_jsonl(trace(False)),
            lane=lane,
            artifact_texts=artifact_texts,
            artifact_paths=artifact_paths,
            isolated_root=Path("C:/isolated"),
            returncode=0,
            stderr="",
            timed_out=False,
        )
        self.assertEqual("fail", missing.verdict)

    def test_git_status_failure_is_not_clean(self) -> None:
        failed = type(
            "Result", (), {"returncode": 128, "stdout": "", "stderr": "not a repository"}
        )()
        with mock.patch.object(conformance.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(conformance.ConformanceError, "git status failed"):
                conformance._git_status(ROOT, ["evals/run_codex_conformance.py"])

    def test_bootstrap_rejects_disabled_plugin_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            codex_home = base / "codex-home"
            installed_path = codex_home / "plugins" / "cache" / "sre-agents"
            workspace = base / "workspace"
            installed_path.mkdir(parents=True)
            workspace.mkdir()
            env = {"CODEX_HOME": str(codex_home)}

            def runner(argv, cwd, timeout, child_env):
                if tuple(argv[-1:]) == ("--version",):
                    return conformance.CommandResult(0, "codex-cli 0.test\n", "")
                if tuple(argv[1:4]) == ("plugin", "marketplace", "add"):
                    return conformance.CommandResult(0, "{}", "")
                if tuple(argv[1:3]) == ("plugin", "add"):
                    return conformance.CommandResult(
                        0,
                        json.dumps(
                            {
                                "pluginId": "sre-agents@latent-sre",
                                "name": "sre-agents",
                                "version": "1.0.0",
                                "installedPath": str(installed_path),
                            }
                        ),
                        "",
                    )
                if tuple(argv[1:4]) == ("plugin", "list", "--json"):
                    return conformance.CommandResult(
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
                                        "enabled": False,
                                    }
                                ]
                            }
                        ),
                        "",
                    )
                self.fail(f"unexpected command: {argv}")

            with self.assertRaisesRegex(conformance.ConformanceError, "enabled"):
                conformance._bootstrap_plugin(
                    "codex",
                    base / "marketplace",
                    self.manifest["plugin"],
                    workspace,
                    env,
                    runner,
                )

    def test_instrument_failure_is_inconclusive(self) -> None:
        score = conformance.score_trace(
            conformance.parse_codex_jsonl(""),
            lane=self.lane,
            installed_skill=Path("C:/cache/stack-profile/SKILL.md"),
            expected_skill_text="profile canary: sp_7c2e\n",
            returncode=1,
            stderr="authentication failed",
            timed_out=False,
        )
        self.assertEqual("inconclusive", score.verdict)

    def test_child_environment_is_allowlisted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary).resolve()
            codex_home = temporary_root / "codex-home"
            neutral_profile = temporary_root / "user-profile"
            old = dict(os.environ)
            try:
                os.environ["GITHUB_TOKEN"] = "must-not-pass"
                os.environ["OPENAI_API_KEY"] = "must-not-pass"
                os.environ["HTTPS_PROXY"] = "http://proxy-user:proxy-password@example.invalid"
                os.environ["PATH"] = old.get("PATH", "")
                child = conformance.scrubbed_child_env(codex_home, neutral_profile)
            finally:
                os.environ.clear()
                os.environ.update(old)
        self.assertNotIn("GITHUB_TOKEN", child)
        self.assertNotIn("OPENAI_API_KEY", child)
        self.assertNotIn("HTTPS_PROXY", child)
        self.assertEqual(str(codex_home), child["CODEX_HOME"])
        self.assertEqual(str(neutral_profile), child["HOME"])
        self.assertEqual(str(neutral_profile), child["USERPROFILE"])
        self.assertTrue(Path(child["APPDATA"]).is_relative_to(neutral_profile))
        self.assertTrue(Path(child["LOCALAPPDATA"]).is_relative_to(neutral_profile))

    def test_broker_config_is_exact_tokenless_loopback_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "broker-home" / "config.toml"
            source.parent.mkdir()
            source.write_text(
                'model_provider = "codex-action-responses-proxy"\n\n'
                '[model_providers.codex-action-responses-proxy]\n'
                'name = "Codex Action Responses Proxy"\n'
                'base_url = "http://127.0.0.1:43123/v1"\n'
                'wire_api = "responses"\n',
                encoding="utf-8",
            )
            broker = conformance.load_broker_config(source)
            self.assertEqual("http://127.0.0.1:43123/v1", broker["base_url"])

            destination = root / "isolated-home"
            destination.mkdir()
            digest = conformance.stage_broker_config(source, destination)
            rendered = (destination / "config.toml").read_text(encoding="utf-8")
            self.assertEqual(64, len(digest))
            self.assertNotIn("env_key", rendered)
            self.assertNotIn("token", rendered.lower())
            self.assertFalse((destination / "auth.json").exists())

            source.write_text(
                rendered + 'env_key = "OPENAI_API_KEY"\n', encoding="utf-8"
            )
            with self.assertRaisesRegex(conformance.ConformanceError, "credential-bearing"):
                conformance.load_broker_config(source)

    def test_broker_config_rejects_auth_file_and_non_loopback_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "config.toml"
            template = (
                'model_provider = "codex-action-responses-proxy"\n\n'
                '[model_providers.codex-action-responses-proxy]\n'
                'name = "Codex Action Responses Proxy"\n'
                'base_url = "{}"\n'
                'wire_api = "responses"\n'
            )
            source.write_text(template.format("https://api.openai.com/v1"), encoding="utf-8")
            with self.assertRaisesRegex(conformance.ConformanceError, "tokenless"):
                conformance.load_broker_config(source)
            source.write_text(template.format("http://127.0.0.1:43123/v1"), encoding="utf-8")
            (root / "auth.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(conformance.ConformanceError, "must not contain auth.json"):
                conformance.load_broker_config(source)

    def test_broker_runtime_boundary_requires_linux_ci_non_root_and_no_sudo(self) -> None:
        broker = {
            "base_url": "http://127.0.0.1:43123/v1",
            "provider": conformance.BROKER_PROVIDER,
        }
        with tempfile.TemporaryDirectory() as temporary:
            clean_home = Path(temporary).resolve()
            with (
                mock.patch.object(conformance, "load_broker_config", return_value=broker),
                mock.patch.object(conformance.sys, "platform", "linux"),
                mock.patch.dict(
                    os.environ,
                    {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "CI": "true"},
                    clear=True,
                ),
                mock.patch.object(conformance.Path, "home", return_value=clean_home),
                mock.patch.object(conformance.os, "geteuid", return_value=1000, create=True),
                mock.patch.object(conformance.shutil, "which", return_value=None),
            ):
                self.assertEqual(
                    broker,
                    conformance.require_brokered_ci_boundary(clean_home / "config.toml"),
                )

            sudo_ok = type("Result", (), {"returncode": 0})()
            with (
                mock.patch.object(conformance, "load_broker_config", return_value=broker),
                mock.patch.object(conformance.sys, "platform", "linux"),
                mock.patch.dict(
                    os.environ,
                    {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "CI": "true"},
                    clear=True,
                ),
                mock.patch.object(conformance.Path, "home", return_value=clean_home),
                mock.patch.object(conformance.os, "geteuid", return_value=1000, create=True),
                mock.patch.object(conformance.shutil, "which", return_value="/usr/bin/sudo"),
                mock.patch.object(conformance.subprocess, "run", return_value=sudo_ok),
            ):
                with self.assertRaisesRegex(conformance.ConformanceError, "sudo to be removed"):
                    conformance.require_brokered_ci_boundary(clean_home / "config.toml")

    def test_broker_runtime_boundary_rejects_spoofable_local_default(self) -> None:
        with (
            mock.patch.object(
                conformance,
                "load_broker_config",
                return_value={"base_url": "http://127.0.0.1:43123/v1"},
            ),
            mock.patch.object(conformance.sys, "platform", "linux"),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            with self.assertRaisesRegex(conformance.ConformanceError, "trusted Linux"):
                conformance.require_brokered_ci_boundary(Path("config.toml"))

    def test_response_evidence_never_retains_model_text(self) -> None:
        marker = "model-controlled-private-marker"
        evidence = conformance.response_evidence(
            {"answer": marker}, {"answer": "expected"}
        )
        rendered = json.dumps(evidence, sort_keys=True)
        self.assertNotIn(marker, rendered)
        self.assertFalse(evidence["response_matched"])
        self.assertEqual(64, len(evidence["response_sha256"]))

    def test_usage_evidence_is_numeric_reduced_and_bounded(self) -> None:
        usage = conformance.bounded_usage_evidence(
            {
                "input_tokens": 42,
                "cached_input_tokens": 7,
                "output_tokens": 3,
                "reasoning_output_tokens": 2,
                "untrusted_extra": "not retained",
            }
        )
        self.assertEqual(set(conformance.MAX_LANE_USAGE_TOKENS), set(usage))
        self.assertNotIn("untrusted_extra", usage)

        too_large = {
            "input_tokens": conformance.MAX_LANE_USAGE_TOKENS["input_tokens"] + 1
        }
        with self.assertRaisesRegex(conformance.ConformanceError, "input_tokens limit"):
            conformance.bounded_usage_evidence(too_large)

        total = {key: 0 for key in conformance.MAX_SUITE_USAGE_TOKENS}
        lane = {key: 0 for key in conformance.MAX_LANE_USAGE_TOKENS}
        lane["input_tokens"] = 1
        conformance.add_suite_usage(total, lane)
        self.assertEqual(1, total["input_tokens"])

    def test_brokered_live_reduction_never_stages_auth_or_reports_model_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            broker_config = root / "broker-home" / "config.toml"
            broker_config.parent.mkdir()
            broker_config.write_text(
                'model_provider = "codex-action-responses-proxy"\n\n'
                '[model_providers.codex-action-responses-proxy]\n'
                'name = "Codex Action Responses Proxy"\n'
                'base_url = "http://127.0.0.1:43123/v1"\n'
                'wire_api = "responses"\n',
                encoding="utf-8",
            )
            manifest = copy.deepcopy(self.manifest)
            manifest["lanes"] = [copy.deepcopy(self.lane)]
            observed_homes: list[Path] = []

            def runner(argv, cwd, timeout, child_env):
                del cwd, timeout
                codex_home = Path(child_env["CODEX_HOME"])
                observed_homes.append(codex_home)
                self.assertFalse((codex_home / "auth.json").exists())
                if tuple(argv[-1:]) == ("--version",):
                    return conformance.CommandResult(0, "codex-cli 0.test\n", "")
                if tuple(argv[1:4]) == ("plugin", "marketplace", "add"):
                    return conformance.CommandResult(0, "{}", "")
                if tuple(argv[1:3]) == ("plugin", "add"):
                    installed = codex_home / "plugins" / "cache" / "sre-agents"
                    conformance.shutil.copytree(ROOT / conformance.PLUGIN_DIRECTORY, installed)
                    return conformance.CommandResult(
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
                    return conformance.CommandResult(
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
                installed_skill = (
                    codex_home
                    / "plugins"
                    / "cache"
                    / "sre-agents"
                    / "skills"
                    / self.lane["skill"]
                    / "SKILL.md"
                )
                skill_text = installed_skill.read_text(encoding="utf-8")
                trace = "\n".join(
                    (
                        json.dumps(
                            {
                                "type": "thread.started",
                                "thread_id": "thread-1",
                                "metadata": {"model": "gpt-5.6-sol"},
                            }
                        ),
                        json.dumps(
                            {
                                "type": "item.completed",
                                "item": {
                                    "type": "command_execution",
                                    "command": f"Get-Content -Raw '{installed_skill}'",
                                    "aggregated_output": skill_text,
                                    "exit_code": 0,
                                    "status": "completed",
                                },
                            }
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
                return conformance.CommandResult(0, trace, "")

            with mock.patch.object(
                conformance, "require_brokered_ci_boundary", return_value={"provider": "proxy"}
            ):
                report = conformance.run_live(
                    ROOT,
                    manifest,
                    executable="codex",
                    broker_config=broker_config,
                    require_clean_plugin=False,
                    require_clean_harness=False,
                    runner=runner,
                )

        self.assertTrue(observed_homes)
        self.assertEqual(
            conformance._git_value(ROOT, ["rev-parse", "HEAD"]),
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
        self.assertNotIn(json.dumps(self.lane["expected"]), json.dumps(report))

    def test_credential_detector_fails_closed_without_echoing_value(self) -> None:
        marker = "sk-proj-0123456789abcdefghijklmnop"
        with self.assertRaisesRegex(
            conformance.CredentialOutputError, "credential-shaped material detected"
        ) as raised:
            conformance.assert_no_credential_output(f"result={marker}")
        self.assertNotIn(marker, str(raised.exception))

    def test_plugin_snapshot_digest_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary).resolve() / "marketplace"
            before = conformance.codex_plugin_digest(ROOT)
            conformance.copy_codex_marketplace_snapshot(ROOT, snapshot)
            self.assertEqual(before, conformance.codex_plugin_digest(snapshot))
            manifest = snapshot / ".agents" / "plugins" / "marketplace.json"
            manifest.write_text(manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            self.assertNotEqual(before, conformance.codex_plugin_digest(snapshot))

    def test_local_marketplace_and_plugin_identity_match_manifest(self) -> None:
        conformance.validate_local_plugin_contract(ROOT, self.manifest)
        wrong = copy.deepcopy(self.manifest)
        wrong["plugin"]["version"] = "9.9.9"
        with self.assertRaisesRegex(conformance.ConformanceError, "version"):
            conformance.validate_local_plugin_contract(ROOT, wrong)

        stale_canary = copy.deepcopy(self.manifest)
        stale_canary["lanes"][0]["expected"]["canary"] = "missing_canary"
        with self.assertRaisesRegex(conformance.ConformanceError, "canary is absent"):
            conformance.validate_local_plugin_contract(ROOT, stale_canary)

    def test_candidate_plugin_metadata_and_active_components_are_not_self_authorizing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary).resolve() / "candidate"
            conformance.copy_codex_marketplace_snapshot(ROOT, candidate)
            conformance.validate_local_plugin_contract(candidate, self.manifest)

            plugin_manifest = (
                candidate / conformance.PLUGIN_DIRECTORY / ".codex-plugin" / "plugin.json"
            )
            document = json.loads(plugin_manifest.read_text(encoding="utf-8"))
            document["mcpServers"] = {"candidate": {"command": "candidate-code"}}
            plugin_manifest.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(conformance.ConformanceError, "differs from trusted main"):
                conformance.validate_local_plugin_contract(candidate, self.manifest)

        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary).resolve() / "candidate"
            conformance.copy_codex_marketplace_snapshot(ROOT, candidate)
            (candidate / conformance.PLUGIN_DIRECTORY / "hooks").mkdir()
            with self.assertRaisesRegex(conformance.ConformanceError, "active or unknown"):
                conformance.validate_local_plugin_contract(candidate, self.manifest)

    def test_runtime_report_reduces_to_typed_evidence(self) -> None:
        report = {
            "started_at": "2026-07-31T12:00:00Z",
            "generated_at": "2026-07-31T12:00:01Z",
            "repository_commit": "a" * 40,
            "evaluator_commit": "f" * 40,
            "plugin_inputs_dirty": False,
            "harness_inputs_dirty": False,
            "summary": {"pass": 1, "fail": 0, "inconclusive": 0},
            "manifest_sha256": "b" * 64,
            "runner_sha256": "c" * 64,
            "plugin_source_sha256": "d" * 64,
            "usage_limits": {
                "per_lane": dict(conformance.MAX_LANE_USAGE_TOKENS),
                "per_suite": dict(conformance.MAX_SUITE_USAGE_TOKENS),
            },
            "usage_totals": {key: 1 for key in conformance.MAX_SUITE_USAGE_TOKENS},
            "results": [
                {
                    "required": True,
                    "requested_model": "gpt-5.6-sol",
                    "observed_model_exposed": True,
                    "cli_version": "codex-cli test",
                    "reasoning_effort": "high",
                    "sandbox": "read-only",
                    "approval_policy": "never",
                }
            ],
        }
        envelope = conformance.build_conformance_evidence(
            report,
            producer="codex_skill_conformance",
            role="codex-skill-conformance",
            target_root=ROOT,
            tree_digest="e" * 64,
            criterion="required lanes pass",
        )
        conformance.evidence_envelope.validate_envelope(envelope)
        self.assertEqual("pass", envelope["status"])
        self.assertEqual(["gpt-5.6-sol"], envelope["environment"]["requested_models"])
        self.assertEqual("f" * 40, envelope["source"]["evaluator_revision"])

        report["summary"] = {"pass": 1, "fail": 0, "inconclusive": 1}
        inconclusive = conformance.build_conformance_evidence(
            report,
            producer="codex_skill_conformance",
            role="codex-skill-conformance",
            target_root=ROOT,
            tree_digest="e" * 64,
            criterion="required lanes pass",
        )
        self.assertEqual("inconclusive", inconclusive["status"])

        report["summary"] = {"pass": 1, "fail": 0, "inconclusive": 0}
        report["plugin_inputs_dirty"] = True
        dirty = conformance.build_conformance_evidence(
            report,
            producer="codex_skill_conformance",
            role="codex-skill-conformance",
            target_root=ROOT,
            tree_digest="e" * 64,
            criterion="required lanes pass",
        )
        self.assertEqual("inconclusive", dirty["status"])
        self.assertTrue(any("not exact-revision evidence" in item for item in dirty["limitations"]))


if __name__ == "__main__":
    unittest.main()
