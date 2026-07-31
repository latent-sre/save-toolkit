"""Offline contracts for the isolated Codex/Sol conformance runner."""

from __future__ import annotations

import copy
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
        self.assertNotIn("--ignore-user-config", command)
        self.assertEqual("--", command[-2])
        self.assertEqual(self.lane["prompt"], command[-1])
        args = conformance._parser().parse_args(["--run"])
        self.assertFalse(args.allow_dirty_plugin)
        self.assertFalse(args.allow_dirty_harness)

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
            base = Path(temporary)
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
            temporary_root = Path(temporary)
            codex_home = temporary_root / "codex-home"
            neutral_profile = temporary_root / "user-profile"
            old = dict(os.environ)
            try:
                os.environ["GITHUB_TOKEN"] = "must-not-pass"
                os.environ["OPENAI_API_KEY"] = "must-not-pass"
                os.environ["PATH"] = old.get("PATH", "")
                child = conformance.scrubbed_child_env(codex_home, neutral_profile)
            finally:
                os.environ.clear()
                os.environ.update(old)
        self.assertNotIn("GITHUB_TOKEN", child)
        self.assertNotIn("OPENAI_API_KEY", child)
        self.assertEqual(str(codex_home), child["CODEX_HOME"])
        self.assertEqual(str(neutral_profile), child["HOME"])
        self.assertEqual(str(neutral_profile), child["USERPROFILE"])
        self.assertTrue(Path(child["APPDATA"]).is_relative_to(neutral_profile))
        self.assertTrue(Path(child["LOCALAPPDATA"]).is_relative_to(neutral_profile))

    def test_plugin_snapshot_digest_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "marketplace"
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


if __name__ == "__main__":
    unittest.main()
