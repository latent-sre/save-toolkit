#!/usr/bin/env python3
"""Offline contract tests for the Codex/Terra ROUTE-001 campaign."""
from __future__ import annotations

import copy
import json
import sys
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_codex_routing  # noqa: E402
import run_evals  # noqa: E402
import codex_trial  # noqa: E402


PAIRED_IDS = {
    "discovery-obs-alerting-splunk-saved-search",
    "discovery-obs-logs-cloud-logging",
    "discovery-obs-metrics-cloud-monitoring",
    "discovery-obs-traces-cloud-trace",
    "discovery-runbook-incident-update",
}

CURRENT_ONLY_IDS = {
    "discovery-akamai-edge-defers-active-incident",
    "discovery-akamai-edge-defers-obs-alerting",
    "discovery-akamai-edge-defers-obs-logs",
    "discovery-akamai-edge-defers-obs-metrics",
    "discovery-akamai-edge-defers-obs-traces",
    "discovery-akamai-edge-defers-pcf",
    "discovery-akamai-edge-reference-error",
    "discovery-gcp-ops-cloud-run-startup",
    "discovery-gcp-ops-defers-active-incident",
    "discovery-gcp-ops-defers-obs-alerting",
    "discovery-gcp-ops-defers-obs-logs",
    "discovery-gcp-ops-defers-obs-metrics",
    "discovery-gcp-ops-defers-obs-traces",
    "discovery-gcp-ops-defers-pcf",
}


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

    def test_manifest_states_the_host_observability_and_tool_boundaries(self) -> None:
        manifest = run_codex_routing.load_manifest()
        self.assertEqual(
            "behavioral-only-codex-0.147", manifest["skill_activation_evidence"]
        )
        self.assertEqual(
            "root-delegation-unobservable-v2", manifest["agent_activation_evidence"]
        )
        self.assertEqual(
            "no-model-tools-non-root-root-collaboration-unscored",
            manifest["tool_policy"],
        )
        self.assertEqual("0.147.0", manifest["codex_cli_version"])
        self.assertEqual("win32-amd64", manifest["runtime_platform"])
        self.assertEqual("3.12.10", manifest["python_version"])
        self.assertEqual(
            "4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a",
            manifest["python_executable_sha256"],
        )
        self.assertEqual("2.53.0.windows.2", manifest["git_cli_version"])
        self.assertEqual(
            r"C:\Program Files\Git\mingw64\bin\git.exe",
            manifest["git_executable_path"],
        )
        self.assertEqual(
            "c39b1b4f7a57935bbeadf246dc2466316619453a6a9da77c4a9c6bd6d8fb21d3",
            manifest["git_executable_sha256"],
        )
        self.assertEqual(
            "935a1911ed2556e4ffcec995f4886ac2ac425863ba26fed264df62e30272ad9d",
            manifest["codex_executable_sha256"],
        )
        self.assertEqual(
            "dd06f2ae3786e852ca884d6c189a364da38f7b7492fd960b05cdd2e3e232e443",
            manifest["source_model_entry_sha256"],
        )
        self.assertEqual(
            "2d23cea7bd13463424eca49df927a38f8480501820eec853e3789015c6a321b6",
            manifest["safe_model_catalog_sha256"],
        )
        self.assertEqual(
            {
                "a39a81f33f7ad7325c52d883822bbbdd80c7ed28": "195e5afad5ccd95f0aa3611b96cd31c8c1e9bc06818009603e2c4181240f62b5",
                "b459a5d3a209d384acb2b2b7ca325aa63697113b": "867f92cccb6eff6e994f27eff7301722ebb82da24b6f2adcd26be92fe2babf4a",
            },
            manifest["snapshot_tree_sha256"],
        )

    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = {item["id"]: item for item in run_evals.load_scenarios()}
        cls.manifest = run_codex_routing.load_manifest()

    def test_manifest_pins_exact_terra_campaign(self) -> None:
        self.assertEqual(1, self.manifest["schema_version"])
        self.assertEqual("gpt-5.6-terra", self.manifest["model"])
        self.assertEqual("medium", self.manifest["reasoning_effort"])
        self.assertEqual("read-only", self.manifest["sandbox"])
        self.assertEqual("never", self.manifest["approval_policy"])
        self.assertEqual(300, self.manifest["timeout_s"])
        self.assertEqual(2, self.manifest["trials"])
        self.assertEqual(
            "a39a81f33f7ad7325c52d883822bbbdd80c7ed28",
            self.manifest["before_revision"],
        )
        self.assertEqual(
            "b459a5d3a209d384acb2b2b7ca325aa63697113b",
            self.manifest["current_revision"],
        )

    def test_manifest_has_exact_five_paired_and_fourteen_current_only(self) -> None:
        cohorts = {row["id"]: row["cohort"] for row in self.manifest["scenarios"]}
        self.assertEqual(PAIRED_IDS, {key for key, value in cohorts.items() if value == "paired"})
        self.assertEqual(
            CURRENT_ONLY_IDS,
            {key for key, value in cohorts.items() if value == "current_only"},
        )
        self.assertEqual(19, len(cohorts))

    def test_manifest_digests_match_current_evaluator_scenarios(self) -> None:
        problems = run_codex_routing.validate_manifest(self.manifest, self.scenarios)
        self.assertEqual([], problems)

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

    def test_manifest_rejects_duplicate_or_drifted_scenario(self) -> None:
        duplicate = copy.deepcopy(self.manifest)
        duplicate["scenarios"].append(copy.deepcopy(duplicate["scenarios"][0]))
        drifted = copy.deepcopy(self.manifest)
        drifted["scenarios"][0]["sha256"] = "0" * 64
        self.assertTrue(any("duplicate" in item for item in run_codex_routing.validate_manifest(duplicate, self.scenarios)))
        self.assertTrue(any("digest" in item for item in run_codex_routing.validate_manifest(drifted, self.scenarios)))

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
            "trials": 1,
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                candidate = copy.deepcopy(self.manifest)
                candidate[key] = value
                self.assertTrue(run_codex_routing.validate_manifest(candidate, self.scenarios))


class CampaignPlanTests(unittest.TestCase):
    def test_plan_has_twenty_paired_and_twenty_eight_current_trials(self) -> None:
        plan = run_codex_routing.campaign_plan(
            run_codex_routing.load_manifest(), run_codex_routing.CURRENT_REVISION
        )
        before = [trial for trial in plan if trial.revision == run_codex_routing.BEFORE_REVISION]
        current = [trial for trial in plan if trial.revision == run_codex_routing.CURRENT_REVISION]
        self.assertEqual(10, len(before))
        self.assertEqual(38, len(current))
        self.assertEqual(48, len(plan))
        self.assertEqual(PAIRED_IDS, {trial.scenario_id for trial in before})
        scenario_digests = {
            row["id"]: row["sha256"] for row in run_codex_routing.load_manifest()["scenarios"]
        }
        self.assertTrue(
            all(
                trial.scenario_sha256 == scenario_digests[trial.scenario_id]
                for trial in plan
            )
        )

    def test_plan_rejects_a_caller_selected_current_revision(self) -> None:
        with self.assertRaises(ValueError):
            run_codex_routing.campaign_plan(run_codex_routing.load_manifest(), "f" * 40)

    def test_command_is_stdin_driven_and_pins_the_runtime_boundary(self) -> None:
        command = run_codex_routing.build_command(
            Path(r"C:\Codex\codex.exe"), Path(r"C:\neutral"), enable_multi_agent=True
        )
        self.assertEqual(r"C:\Codex\codex.exe", command[0])
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
        config = run_codex_routing.render_config(
            Path(r"C:\Python\python.exe"),
            Path(r"C:\suite\codex_hook_recorder.py"),
            Path(r"C:\private\receipts"),
            Path(r"C:\private\route-models.json"),
            "a" * 32,
        )
        parsed = tomllib.loads(config)
        self.assertEqual(
            r"C:\private\route-models.json", parsed["model_catalog_json"]
        )
        self.assertNotIn("default_permissions", parsed)
        self.assertNotIn("permissions", parsed)
        self.assertFalse(parsed["update_plan_enabled"])
        self.assertFalse(parsed["experimental_request_user_input_enabled"])
        self.assertFalse(parsed["skills"]["bundled"]["enabled"])
        self.assertFalse(parsed["orchestrator"]["skills"]["enabled"])
        self.assertFalse(parsed["orchestrator"]["mcp"]["enabled"])
        self.assertTrue(parsed["features"]["hooks"])
        self.assertTrue(parsed["features"]["multi_agent"])
        self.assertTrue(parsed["features"]["skill_search"])
        self.assertFalse(parsed["features"]["shell_tool"])
        self.assertFalse(parsed["features"]["plugins"])
        self.assertEqual(3, sum(bool(value) for value in parsed["features"].values()))
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
            self.assertIn("codex_hook_recorder.py", handler["command_windows"])
            self.assertIn("a" * 32, handler["command_windows"])
            self.assertIn(" -E -s -S -B ", f" {handler['command']} ")
            self.assertIn(" -E -s -S -B ", f" {handler['command_windows']} ")

    def test_hook_command_paths_reject_shell_metacharacters(self) -> None:
        for character in ("%", "!", "^", "&", "|", "<", ">", '"', "\n"):
            with self.subTest(character=repr(character)), self.assertRaisesRegex(
                ValueError, "safe-character"
            ):
                run_codex_routing.render_config(
                    Path(r"C:\Python\python.exe"),
                    Path(f"C:/private/unsafe{character}hook.py"),
                    Path(r"C:\private\receipts"),
                    Path(r"C:\private\route-models.json"),
                    "a" * 32,
                )


class CanaryContractTests(unittest.TestCase):
    def test_canary_is_exactly_one_current_unscored_trial(self) -> None:
        manifest = run_codex_routing.load_manifest()

        spec = run_codex_routing.canary_spec(
            manifest, "discovery-gcp-ops-cloud-run-startup"
        )

        self.assertEqual("current_only", spec.cohort)
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
                    "C:/repo",
                    "--codex-bin",
                    "C:/codex.exe",
                    "--private-root",
                    "C:/private",
                ]
            )

        self.assertEqual(0, exit_code)
        isolated.assert_called_once()
        preflight.assert_called_once()
        self.assertNotIn("auth_file", preflight.call_args.kwargs)
        serialized = printed.call_args.args[0]
        self.assertIn('"authenticated_call_started":false', serialized)
        self.assertIn('"live_authorized":false', serialized)

    def test_preflight_rejects_auth_input_before_dispatch(self) -> None:
        with mock.patch.object(codex_trial, "run_preflight") as preflight:
            exit_code = run_codex_routing.main(
                [
                    "--preflight",
                    "--repo-root",
                    "C:/repo",
                    "--codex-bin",
                    "C:/codex.exe",
                    "--private-root",
                    "C:/private",
                    "--auth-file",
                    "C:/auth.json",
                ]
            )

        self.assertEqual(3, exit_code)
        preflight.assert_not_called()

    def test_canary_requires_the_isolated_staged_entrypoint(self) -> None:
        evaluator_root = Path(run_codex_routing.__file__).resolve().parent
        entrypoint = evaluator_root / "run_codex_routing.py"
        manifest = evaluator_root / "conformance" / "codex-terra-routing-v1.json"
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
