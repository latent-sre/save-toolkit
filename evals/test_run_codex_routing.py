#!/usr/bin/env python3
"""Offline contract tests for the Codex/Terra ROUTE-001 canary."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_codex_routing  # noqa: E402
import run_evals  # noqa: E402
import codex_trial  # noqa: E402


class ManifestContractTests(unittest.TestCase):
    def test_stable_manifest_parser_hashes_the_exact_bytes_it_parses(self) -> None:
        approved = run_codex_routing.MANIFEST_PATH.read_bytes()
        malicious_value = json.loads(approved)
        malicious_value["model"] = "attacker-selected-model"
        malicious = json.dumps(malicious_value).encode("utf-8")
        changing_path = mock.Mock()
        changing_path.read_bytes.side_effect = [approved, malicious]

        with self.assertRaisesRegex(ValueError, "changed while it was loaded"):
            run_codex_routing.load_stable_manifest(changing_path)

        stable_path = mock.Mock()
        stable_path.read_bytes.side_effect = [approved, approved]
        raw, parsed = run_codex_routing.load_stable_manifest(stable_path)
        self.assertEqual(approved, raw)
        self.assertEqual("gpt-5.6-terra", parsed["model"])

    def test_manifest_states_the_canary_observability_and_tool_boundaries(self) -> None:
        manifest = run_codex_routing.load_manifest()
        self.assertEqual(
            "behavioral-only-codex-0.148", manifest["skill_activation_evidence"]
        )
        self.assertNotIn("agent_activation_evidence", manifest)
        self.assertEqual("no-model-tools-non-root", manifest["tool_policy"])
        self.assertEqual("0.148.0", manifest["codex_cli_version"])
        self.assertEqual("linux-x86_64", manifest["runtime_platform"])
        self.assertEqual("3.12.10", manifest["python_version"])
        self.assertEqual("/usr/local/bin/python3.12", manifest["python_executable_path"])
        self.assertEqual("2.39.5", manifest["git_cli_version"])
        self.assertEqual("/usr/bin/git", manifest["git_executable_path"])
        self.assertEqual(
            "ac2cfed85fb647d61e0150b8548102b330e4799d9d81ad5d354de701edf6b074",
            manifest["codex_executable_sha256"],
        )
        self.assertEqual(
            "3a934e842c9b6a813dfe04ec826da0b79dcfc9b3187696d4b2c1b7110cdb811c",
            manifest["source_model_entry_sha256"],
        )
        self.assertEqual(
            "b5122f71336f146cb6c656167e7f3258a9e4735583b95435f808261562bb646f",
            manifest["safe_model_catalog_sha256"],
        )
        self.assertEqual(
            {
                "7aef80aede95394f6c4237ed2aedb911e141c3c0": "b9167b5200994d8265a2c592c7730028e81aa6f3a7fb19646bce0ceffc052a10",
            },
            manifest["snapshot_tree_sha256"],
        )

    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = {item["id"]: item for item in run_evals.load_scenarios()}
        cls.manifest = run_codex_routing.load_manifest()

    def test_manifest_pins_exact_terra_canary(self) -> None:
        self.assertEqual(3, self.manifest["schema_version"])
        self.assertEqual(
            "route-001-codex-terra-canary-v1", self.manifest["instrument"]
        )
        self.assertEqual("gpt-5.6-terra", self.manifest["model"])
        self.assertEqual("medium", self.manifest["reasoning_effort"])
        self.assertEqual("read-only", self.manifest["sandbox"])
        self.assertEqual("never", self.manifest["approval_policy"])
        self.assertEqual(300, self.manifest["timeout_s"])
        self.assertEqual(
            "7aef80aede95394f6c4237ed2aedb911e141c3c0",
            self.manifest["current_revision"],
        )

    def test_embedded_canary_is_canonical_and_matches_the_yaml_source(self) -> None:
        self.assertEqual(
            "discovery-gcp-ops-cloud-run-startup",
            run_codex_routing.CANARY_SCENARIO_ID,
        )
        expected = self.scenarios[run_codex_routing.CANARY_SCENARIO_ID]
        self.assertEqual(expected, self.manifest["canary_scenario"])
        self.assertEqual(
            {
                "cloud_run_rollback_packet",
                "contains_all",
                "contains_any",
            },
            {
                spec["type"]
                for spec in self.manifest["canary_scenario"]["graders"]
            },
        )
        self.assertEqual(
            frozenset(
                {
                    "cloud_run_rollback_packet",
                    "contains_all",
                    "contains_any",
                }
            ),
            run_codex_routing.CANARY_LINEAR_GRADER_TYPES,
        )
        self.assertEqual([], run_codex_routing.validate_canary_scenario(self.manifest))

        mutated = copy.deepcopy(self.manifest)
        mutated["canary_scenario"]["prompt"] += " attacker-selected suffix"
        self.assertTrue(run_codex_routing.validate_canary_scenario(mutated))

    def test_canary_rejects_a_regex_grader_even_when_other_binding_checks_fail(self) -> None:
        mutated = copy.deepcopy(self.manifest)
        mutated["canary_scenario"]["graders"][0] = {
            "type": "regex",
            "pattern": "^unsafe$",
        }

        problems = run_codex_routing.validate_canary_scenario(mutated)

        self.assertTrue(
            any("linear-only grader allowlist" in problem for problem in problems),
            problems,
        )
        with self.assertRaisesRegex(ValueError, "canary scenario contract"):
            run_codex_routing.canary_spec(mutated)

    def test_manifest_rejects_weakened_runtime_conditions(self) -> None:
        mutations = {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "sandbox": "workspace-write",
            "approval_policy": "on-request",
            "python_executable_sha256": "0" * 64,
            "git_executable_sha256": "0" * 64,
            "snapshot_tree_sha256": {},
            "timeout_s": 299,
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                candidate = copy.deepcopy(self.manifest)
                candidate[key] = value
                self.assertTrue(run_codex_routing.validate_manifest(candidate))


class RuntimeCommandTests(unittest.TestCase):
    def test_command_is_stdin_driven_and_pins_the_runtime_boundary(self) -> None:
        codex_path = Path("/opt/route001/codex")
        command = run_codex_routing.build_command(
            codex_path,
            Path("/run/route001/project"),
        )
        self.assertEqual(str(codex_path), command[0])
        self.assertIn("gpt-5.6-terra", command)
        self.assertIn('model_reasoning_effort="medium"', command)
        self.assertIn('model_provider="openai"', command)
        self.assertIn('openai_base_url=""', command)
        self.assertIn('chatgpt_base_url="https://chatgpt.com/backend-api/"', command)
        self.assertIn("--sandbox", command)
        self.assertIn("read-only", command)
        self.assertFalse(any(value.startswith("default_permissions=") for value in command))
        self.assertIn("never", command)
        self.assertIn("--json", command)
        self.assertIn("--strict-config", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("--dangerously-bypass-hook-trust", command)
        self.assertNotIn("--ignore-user-config", command)
        self.assertLess(command.index("--dangerously-bypass-hook-trust"), command.index("exec"))
        self.assertEqual("-", command[-1])
        self.assertNotIn("--search", command)
        disabled = {
            command[index + 1]
            for index, value in enumerate(command[:-1])
            if value == "--disable"
        }
        self.assertEqual(
            {
                "apps",
                "auth_elicitation",
                "browser_use",
                "browser_use_external",
                "browser_use_full_cdp_access",
                "code_mode",
                "code_mode_host",
                "computer_use",
                "goals",
                "guardian_approval",
                "guardianv2",
                "image_generation",
                "in_app_browser",
                "memories",
                "multi_agent",
                "network_proxy",
                "plugin_sharing",
                "plugins",
                "remote_plugin",
                "request_permissions_tool",
                "respect_system_proxy",
                "shell_tool",
                "skill_mcp_dependency_install",
                "tool_call_mcp_elicitation",
                "tool_suggest",
                "unified_exec",
                "view_image",
                "workspace_dependencies",
            },
            disabled,
        )

    def test_generated_config_contains_only_the_trusted_receipt_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            python_executable = root / "python"
            recorder = root / "suite" / "codex_hook_recorder.py"
            receipts = root / "private" / "receipts"
            model_catalog = root / "private" / "route-models.json"
            config = run_codex_routing.render_config(
                python_executable,
                recorder,
                receipts,
                model_catalog,
                "a" * 32,
            )
        parsed = tomllib.loads(config)
        self.assertEqual(str(model_catalog), parsed["model_catalog_json"])
        self.assertNotIn("default_permissions", parsed)
        self.assertNotIn("permissions", parsed)
        self.assertNotIn("update_plan_enabled", parsed)
        self.assertNotIn("experimental_request_user_input_enabled", parsed)
        self.assertFalse(parsed["tools"]["update_plan"]["enabled"])
        self.assertFalse(
            parsed["tools"]["experimental_request_user_input"]["enabled"]
        )
        self.assertFalse(parsed["skills"]["bundled"]["enabled"])
        self.assertFalse(parsed["orchestrator"]["skills"]["enabled"])
        self.assertFalse(parsed["orchestrator"]["mcp"]["enabled"])
        self.assertTrue(parsed["features"]["hooks"])
        self.assertFalse(parsed["features"]["multi_agent"])
        self.assertTrue(parsed["features"]["skill_search"])
        self.assertFalse(parsed["features"]["shell_tool"])
        self.assertFalse(parsed["features"]["plugins"])
        self.assertEqual(2, sum(bool(value) for value in parsed["features"].values()))
        self.assertEqual(
            {"SessionStart", "SubagentStart", "PostToolUse"},
            set(parsed["hooks"]),
        )
        for event in parsed["hooks"].values():
            self.assertEqual(1, len(event))
            self.assertEqual(1, len(event[0]["hooks"]))
            handler = event[0]["hooks"][0]
            self.assertEqual("command", handler["type"])
            self.assertFalse(handler["async"])
            self.assertEqual(10, handler["timeout"])
            self.assertNotIn("command_windows", handler)
            self.assertIn("codex_hook_recorder.py", handler["command"])
            self.assertIn("a" * 32, handler["command"])
            self.assertIn(" -E -s -S -B ", f" {handler['command']} ")

    def test_hook_command_paths_reject_shell_metacharacters(self) -> None:
        for character in ("%", "!", "^", "&", "|", "<", ">", '"', "\n"):
            with self.subTest(character=repr(character)), self.assertRaisesRegex(
                ValueError, "safe-character"
            ):
                run_codex_routing.render_config(
                    Path("/usr/local/bin/python3.12"),
                    Path(f"/run/route001/unsafe{character}hook.py"),
                    Path("/run/route001/receipts"),
                    Path("/run/route001/route-models.json"),
                    "a" * 32,
                )


class CanaryContractTests(unittest.TestCase):
    def test_retired_campaign_flag_is_rejected_by_the_inner_cli(self) -> None:
        with mock.patch.object(run_codex_routing.sys, "stderr"), self.assertRaises(
            SystemExit
        ) as raised:
            run_codex_routing.main(["--campaign"])

        self.assertEqual(2, raised.exception.code)

    def test_canary_is_exactly_one_current_unscored_trial(self) -> None:
        manifest = run_codex_routing.load_manifest()

        spec = run_codex_routing.canary_spec(
            manifest, "discovery-gcp-ops-cloud-run-startup"
        )

        self.assertEqual(run_codex_routing.CURRENT_REVISION, spec.revision)
        self.assertEqual(1, spec.trial)

    def test_canary_requires_explicit_codex_and_auth_paths(self) -> None:
        self.assertEqual(3, run_codex_routing.main(["--canary"]))

    def test_preflight_is_isolated_credential_free_and_never_authorizes_live_use(self) -> None:
        result = SimpleNamespace(
            reason_codes=("credential-free-preflight-pass",),
            as_dict=lambda: {
                "state": "INCONCLUSIVE",
                "reason_codes": ["credential-free-preflight-pass"],
                "authority": {"release_granted": False},
            },
        )
        with (
            mock.patch.object(
                run_codex_routing, "require_isolated_canary_launch"
            ) as isolated,
            mock.patch.object(codex_trial, "run_preflight", return_value=result) as preflight,
            mock.patch("builtins.print") as printed,
        ):
            exit_code = run_codex_routing.main(
                [
                    "--preflight",
                    "--repo-root",
                    "/source",
                    "--codex-bin",
                    "/opt/route001/codex-runtime/bin/codex",
                    "--private-root",
                    "/run/route001",
                ]
            )

        self.assertEqual(0, exit_code)
        isolated.assert_called_once()
        preflight.assert_called_once()
        self.assertNotIn("auth_file", preflight.call_args.kwargs)
        self.assertEqual("body", preflight.call_args.kwargs["canary_probe_mode"])
        serialized = printed.call_args.args[0]
        self.assertIn('"authenticated_call_started":false', serialized)
        self.assertIn('"live_authorized":false', serialized)

    def test_preflight_rejects_auth_input_before_dispatch(self) -> None:
        with mock.patch.object(codex_trial, "run_preflight") as preflight:
            exit_code = run_codex_routing.main(
                [
                    "--preflight",
                    "--repo-root",
                    "/source",
                    "--codex-bin",
                    "/opt/route001/codex-runtime/bin/codex",
                    "--private-root",
                    "/run/route001",
                    "--auth-file",
                    "/run/secrets/auth.json",
                ]
            )

        self.assertEqual(3, exit_code)
        preflight.assert_not_called()

    def test_authenticated_canary_uses_the_explicit_body_probe(self) -> None:
        result = SimpleNamespace(
            state=SimpleNamespace(value="PASS"),
            as_dict=lambda: {"state": "PASS"},
        )
        with (
            mock.patch.object(run_codex_routing, "require_isolated_canary_launch"),
            mock.patch.object(codex_trial, "run_trial", return_value=result) as trial,
            mock.patch("builtins.print"),
        ):
            exit_code = run_codex_routing.main(
                [
                    "--canary",
                    "--repo-root",
                    "/source",
                    "--codex-bin",
                    "/opt/route001/codex-runtime/bin/codex",
                    "--private-root",
                    "/run/route001",
                    "--auth-file",
                    "/run/secrets/auth.json",
                ]
            )

        self.assertEqual(0, exit_code)
        trial.assert_called_once()
        self.assertEqual("body", trial.call_args.kwargs["canary_probe_mode"])

    def test_authenticated_canary_can_select_the_description_only_arm(self) -> None:
        result = SimpleNamespace(
            state=SimpleNamespace(value="PASS"),
            as_dict=lambda: {"state": "PASS"},
        )
        with (
            mock.patch.object(run_codex_routing, "require_isolated_canary_launch"),
            mock.patch.object(codex_trial, "run_trial", return_value=result) as trial,
            mock.patch("builtins.print"),
        ):
            exit_code = run_codex_routing.main(
                [
                    "--canary",
                    "--canary-arm",
                    "description",
                    "--repo-root",
                    "/source",
                    "--codex-bin",
                    "/opt/route001/codex-runtime/bin/codex",
                    "--private-root",
                    "/run/route001",
                    "--auth-file",
                    "/run/secrets/auth.json",
                ]
            )

        self.assertEqual(0, exit_code)
        self.assertEqual("description", trial.call_args.kwargs["canary_probe_mode"])

    def test_canary_arm_is_rejected_outside_the_development_canary(self) -> None:
        for arguments in (
            ["--canary-arm", "description"],
            [
                "--preflight",
                "--canary-arm",
                "description",
            ],
        ):
            with self.subTest(arguments=arguments), mock.patch(
                "builtins.print"
            ) as printed:
                exit_code = run_codex_routing.main(arguments)

            self.assertEqual(3, exit_code)
            self.assertIn("canary-only", printed.call_args.args[0])

    def test_canary_requires_the_isolated_staged_entrypoint(self) -> None:
        evaluator_root = Path(run_codex_routing.__file__).resolve().parent
        entrypoint = evaluator_root / "run_codex_routing.py"
        manifest = run_codex_routing.LINUX_MANIFEST_PATH
        isolated = SimpleNamespace(
            isolated=1,
            no_site=1,
            dont_write_bytecode=1,
            safe_path=True,
        )
        with (
            mock.patch.object(run_codex_routing.sys, "flags", isolated),
            mock.patch.object(run_codex_routing.sys, "argv", [str(entrypoint)]),
            mock.patch.object(run_codex_routing.sys, "path", [str(evaluator_root)]),
        ):
            run_codex_routing.require_isolated_canary_launch(manifest)

        for label, flags, manifest_path in (
            (
                "non-isolated",
                SimpleNamespace(
                    isolated=0,
                    no_site=1,
                    dont_write_bytecode=1,
                    safe_path=True,
                ),
                manifest,
            ),
            ("wrong-manifest", isolated, evaluator_root / "other.json"),
        ):
            with (
                self.subTest(label=label),
                mock.patch.object(run_codex_routing.sys, "flags", flags),
                mock.patch.object(run_codex_routing.sys, "argv", [str(entrypoint)]),
                mock.patch.object(run_codex_routing.sys, "path", [str(evaluator_root)]),
                self.assertRaises(ValueError),
            ):
                run_codex_routing.require_isolated_canary_launch(manifest_path)


class AuthorityBoundaryTests(unittest.TestCase):
    def test_reserved_authority_facts_cannot_be_overridden(self) -> None:
        facts = run_codex_routing.authority_facts(
            {
                "source_review": "verified",
                "independent_evaluator": True,
                "baseline_eligible": True,
                "release_granted": True,
                "exact_revision": True,
            },
            exact_revision=False,
        )
        self.assertEqual("not-verified-by-runner", facts["source_review"])
        self.assertFalse(facts["independent_evaluator"])
        self.assertFalse(facts["baseline_eligible"])
        self.assertFalse(facts["release_granted"])
        self.assertFalse(facts["exact_revision"])


if __name__ == "__main__":
    unittest.main()
