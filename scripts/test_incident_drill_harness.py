#!/usr/bin/env python3
"""Focused regressions for the incident-drill lane launcher boundary."""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUN_LANE_PATH = ROOT / "skills/incident-drill/scripts/run_lane.py"
SPEC = importlib.util.spec_from_file_location("incident_drill_run_lane", RUN_LANE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery failure
    raise RuntimeError(f"cannot load {RUN_LANE_PATH}")
run_lane = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_lane)

DRILL_REPORT_PATH = ROOT / "skills/incident-drill/scripts/drill_report.py"
REPORT_SPEC = importlib.util.spec_from_file_location("incident_drill_report", DRILL_REPORT_PATH)
if REPORT_SPEC is None or REPORT_SPEC.loader is None:  # pragma: no cover - import machinery failure
    raise RuntimeError(f"cannot load {DRILL_REPORT_PATH}")
drill_report = importlib.util.module_from_spec(REPORT_SPEC)
REPORT_SPEC.loader.exec_module(drill_report)


class IncidentDrillHarnessTests(unittest.TestCase):
    def test_usage_examples_include_required_lineage_and_runtime_confirmation(self) -> None:
        self.assertEqual(2, run_lane.__doc__.count("--run-id"))
        self.assertEqual(2, run_lane.__doc__.count("--attempt-id"))
        self.assertEqual(2, run_lane.__doc__.count("--credential-free-runtime"))

    def test_tool_boundary_is_normalized_nonempty_and_applied_twice(self) -> None:
        tools = run_lane.normalize_tools(" Read, Bash,Read , Skill ")
        self.assertEqual(("Read", "Bash", "Skill"), tools)

        command = run_lane.build_command(
            claude="claude",
            plugin_dir=Path("C:/fleet"),
            service_root=Path("C:/drill/service"),
            model="sonnet",
            tools=tools,
            agent="save-toolkit:software-engineer",
        )

        self.assertEqual("Read,Bash,Skill", command[command.index("--tools") + 1])
        self.assertEqual("Read,Bash,Skill", command[command.index("--allowedTools") + 1])
        self.assertEqual("", command[command.index("--setting-sources") + 1])
        self.assertEqual(
            Path("C:/drill/service"),
            Path(command[command.index("--add-dir") + 1]),
        )
        self.assertIn("--append-system-prompt", command)
        with self.assertRaisesRegex(SystemExit, "at least one tool"):
            run_lane.normalize_tools(" , ")

    def test_child_environment_drops_non_claude_credentials_and_overrides(self) -> None:
        host = {
            "PATH": "C:/host-tools",
            "SYSTEMROOT": "C:/Windows",
            "TEMP": "C:/Temp",
            "LANG": "en_US.UTF-8",
            "HTTPS_PROXY": "https://proxy.example",
            "ANTHROPIC_API_KEY": "required-claude-auth",
            "GITHUB_TOKEN": "must-not-cross",
            "AWS_SECRET_ACCESS_KEY": "must-not-cross",
            "GOOGLE_APPLICATION_CREDENTIALS": "must-not-cross",
            "CF_HOME": "must-not-cross",
            "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD": "1",
            "REPOSITORY_SPECIFIC_SECRET": "must-not-cross",
        }
        with mock.patch.dict(os.environ, host, clear=True):
            child = run_lane.scrubbed_child_env(
                config_dir=Path("C:/isolated-claude"),
                python_dir=Path("C:/Python312"),
            )

        self.assertEqual("required-claude-auth", child["ANTHROPIC_API_KEY"])
        self.assertEqual(Path("C:/isolated-claude"), Path(child["CLAUDE_CONFIG_DIR"]))
        # The property is that the isolated interpreter comes FIRST on PATH, so a drill cannot
        # pick up a host toolchain. Compare the first entry as a Path: the previous assertion
        # hardcoded a Windows-normalised prefix, so it passed on Windows and failed everywhere
        # else -- invisible until CI actually ran it.
        first_on_path = child["PATH"].split(os.pathsep)[0]
        self.assertEqual(Path("C:/Python312"), Path(first_on_path))
        for key in (
            "GITHUB_TOKEN",
            "AWS_SECRET_ACCESS_KEY",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "CF_HOME",
            "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD",
            "REPOSITORY_SPECIFIC_SECRET",
        ):
            self.assertNotIn(key, child)

    def test_main_uses_neutral_cwd_real_service_root_and_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = root / "service"
            plugin = root / "plugin"
            launch = root / "neutral"
            config = root / "config"
            runs = root / "runs"
            for path in (service, plugin, launch, config):
                path.mkdir()
            (service / "CLAUDE.md").write_text("untrusted fixture instruction", encoding="utf-8")
            prompt = root / "prompt.md"
            prompt.write_text("inspect the synthetic service", encoding="utf-8")
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(
                    {
                        "result": "done",
                        "total_cost_usd": 0.1,
                        "num_turns": 2,
                        "is_error": False,
                        "session_id": "session-1",
                    }
                ),
                stderr="",
            )

            @contextlib.contextmanager
            def fake_config():
                yield config

            @contextlib.contextmanager
            def fake_neutral():
                yield launch

            environment = {
                "PATH": "C:/host-tools",
                "SYSTEMROOT": "C:/Windows",
                "ANTHROPIC_API_KEY": "required-claude-auth",
                "GITHUB_TOKEN": "must-not-cross",
            }
            with (
                mock.patch.dict(os.environ, environment, clear=True),
                mock.patch.object(run_lane, "isolated_config", fake_config),
                mock.patch.object(run_lane, "neutral_workspace", fake_neutral),
                mock.patch.object(run_lane.subprocess, "run", return_value=completed) as invoked,
            ):
                status = run_lane.main(
                    [
                        "--run-id", "graph-001-canary",
                        "--attempt-id", "attempt-2",
                        "--step", "01",
                        "--lane", "builder",
                        "--agent", "save-toolkit:software-engineer",
                        "--prompt-file", str(prompt),
                        "--allowed-tools", "Read,Bash",
                        "--plugin-dir", str(plugin),
                        "--cwd", str(service),
                        "--runs-dir", str(runs),
                        "--claude", "claude",
                        "--python-dir", "C:/Python312",
                        "--credential-free-runtime",
                    ]
                )
                self.assertEqual(0, status)
                call = invoked.call_args
                command = call.args[0]
                self.assertEqual(launch.resolve(), Path(call.kwargs["cwd"]).resolve())
                self.assertEqual(str(service.resolve()), command[command.index("--add-dir") + 1])
                self.assertEqual("", command[command.index("--setting-sources") + 1])
                self.assertNotIn("GITHUB_TOKEN", call.kwargs["env"])
                metadata_path = runs / "graph-001-canary" / "01-builder" / "attempt-2" / "result.meta.json"
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual("graph-001-canary", metadata["run_id"])
        self.assertEqual("attempt-2", metadata["attempt_id"])
        self.assertEqual(["Read", "Bash"], metadata["available_tools"])
        self.assertEqual(["Read", "Bash"], metadata["allowed_tools"])

    def test_attempt_outputs_are_distinct_recursive_and_collision_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runs = Path(temporary) / "runs"
            first = run_lane.reserve_attempt_output(runs, "run-1", "01", "builder", "attempt-1")
            second = run_lane.reserve_attempt_output(runs, "run-1", "01", "builder", "attempt-2")
            first.with_suffix(".meta.json").write_text(
                json.dumps({"run_id": "run-1", "attempt_id": "attempt-1"}), encoding="utf-8"
            )
            second.with_suffix(".meta.json").write_text(
                json.dumps({"run_id": "run-1", "attempt_id": "attempt-2"}), encoding="utf-8"
            )

            rows = drill_report.load(runs)

            self.assertEqual({"attempt-1", "attempt-2"}, {row["attempt_id"] for row in rows})
            with self.assertRaisesRegex(SystemExit, "already exists"):
                run_lane.reserve_attempt_output(runs, "run-1", "01", "builder", "attempt-1")
            with self.assertRaisesRegex(SystemExit, "safe path component"):
                run_lane.reserve_attempt_output(runs, "../escape", "01", "builder", "attempt-3")
            with self.assertRaisesRegex(SystemExit, "safe path component"):
                run_lane.reserve_attempt_output(runs, "..", "01", "builder", "attempt-3")

    def test_timeout_is_unknown_and_does_not_claim_descendant_termination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = root / "service"
            plugin = root / "plugin"
            launch = root / "neutral"
            config = root / "config"
            runs = root / "runs"
            for path in (service, plugin, launch, config):
                path.mkdir()
            prompt = root / "prompt.md"
            prompt.write_text("inspect the synthetic service", encoding="utf-8")

            @contextlib.contextmanager
            def fake_config():
                yield config

            @contextlib.contextmanager
            def fake_neutral():
                yield launch

            with (
                mock.patch.dict(os.environ, {"PATH": "C:/host-tools"}, clear=True),
                mock.patch.object(run_lane, "isolated_config", fake_config),
                mock.patch.object(run_lane, "neutral_workspace", fake_neutral),
                mock.patch.object(
                    run_lane.subprocess,
                    "run",
                    side_effect=subprocess.TimeoutExpired(cmd=["claude"], timeout=10),
                ),
            ):
                status = run_lane.main(
                    [
                        "--run-id", "run-timeout",
                        "--attempt-id", "attempt-1",
                        "--step", "01",
                        "--lane", "builder",
                        "--prompt-file", str(prompt),
                        "--plugin-dir", str(plugin),
                        "--cwd", str(service),
                        "--runs-dir", str(runs),
                        "--claude", "claude",
                        "--python-dir", "C:/Python312",
                        "--timeout", "10",
                        "--credential-free-runtime",
                    ]
                )

            metadata_path = runs / "run-timeout" / "01-builder" / "attempt-1" / "result.meta.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(124, status)
            self.assertEqual("UNKNOWN", metadata["outcome"])
            self.assertEqual("TIMEOUT", metadata["failure_class"])
            self.assertEqual("UNVERIFIED", metadata["descendant_termination"])


if __name__ == "__main__":
    unittest.main()
