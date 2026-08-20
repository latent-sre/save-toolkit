#!/usr/bin/env python3
"""Fail-closed contracts for the Linux-container ROUTE-001 executor."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_campaign  # noqa: E402
import codex_container  # noqa: E402
import run_codex_routing  # noqa: E402


# The mutation guard derives subjects from exact path literals when a test spans several modules.
MUTATION_SUBJECTS = (
    "evals/codex_campaign.py",
    "evals/codex_container.py",
    "evals/run_codex_routing.py",
)


IMAGE_ID = "sha256:" + "a" * 64
MANIFEST_SHA256 = "b" * 64


def _plan():
    return run_codex_routing.campaign_plan(
        run_codex_routing.load_manifest(run_codex_routing.LINUX_MANIFEST_PATH),
        run_codex_routing.CURRENT_REVISION,
    )


def _result(spec, *, state: str = "PASS") -> dict[str, object]:
    return {
        "schema_version": 1,
        "scenario": {
            "id": spec.scenario_id,
            "cohort": spec.cohort,
            "revision": spec.revision,
            "trial": spec.trial,
            "manifest_sha256": MANIFEST_SHA256,
            "scenario_sha256": spec.scenario_sha256,
            "prompt_sha256": "c" * 64,
        },
        "state": state,
        "authority": {
            "source_review": "not-verified-by-runner",
            "independent_evaluator": False,
            "baseline_eligible": False,
            "release_granted": False,
            "exact_revision": True,
        },
    }


class LinuxManifestTests(unittest.TestCase):
    def test_linux_manifest_is_the_canonical_exact_48_trial_shape(self) -> None:
        manifest = run_codex_routing.load_manifest(
            run_codex_routing.LINUX_MANIFEST_PATH
        )
        self.assertEqual("linux-x86_64", manifest["runtime_platform"])
        self.assertEqual("linux-container", manifest["runtime_kind"])
        self.assertEqual("65532:65532", manifest["container_user"])
        self.assertEqual(48, len(_plan()))
        self.assertEqual([], run_codex_routing.validate_manifest(manifest, None))

    def test_historical_windows_manifest_remains_explicitly_valid(self) -> None:
        manifest = run_codex_routing.load_manifest(
            run_codex_routing.WINDOWS_MANIFEST_PATH
        )
        self.assertEqual("win32-amd64", manifest["runtime_platform"])
        self.assertEqual("0.147.0", manifest["codex_cli_version"])
        self.assertEqual([], run_codex_routing.validate_manifest(manifest, None))


class CampaignJournalTests(unittest.TestCase):
    def test_plan_cannot_exceed_or_differ_from_the_fixed_48_calls(self) -> None:
        plan = _plan()
        codex_campaign.validate_campaign_plan(plan)
        for candidate in (plan[:-1], [*plan, plan[-1]], [plan[1], plan[0], *plan[2:]]):
            with self.subTest(length=len(candidate)), self.assertRaises(
                codex_campaign.CampaignContractError
            ):
                codex_campaign.validate_campaign_plan(candidate)

    def test_started_record_is_fsynced_before_dispatch(self) -> None:
        plan = _plan()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal = codex_campaign.CampaignJournal.create(
                root, plan=plan, manifest_sha256=MANIFEST_SHA256
            )
            events: list[str] = []

            def fsync(fd: int) -> None:
                self.assertGreaterEqual(fd, 0)
                events.append("fsync")

            with mock.patch.object(codex_campaign.os, "fsync", side_effect=fsync):
                journal.run_next(
                    lambda spec: events.append("dispatch") or _result(spec)
                )

        self.assertIn("dispatch", events)
        self.assertIn("fsync", events)
        self.assertLess(events.index("fsync"), events.index("dispatch"))

    def test_unfinished_started_record_is_unknown_and_never_replayed(self) -> None:
        plan = _plan()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal = codex_campaign.CampaignJournal.create(
                root, plan=plan, manifest_sha256=MANIFEST_SHA256
            )
            journal.begin(plan[0])
            resumed = codex_campaign.CampaignJournal.open(
                root, plan=plan, manifest_sha256=MANIFEST_SHA256
            )
            dispatched = mock.Mock()
            with self.assertRaises(codex_campaign.UnknownOutcomeError):
                resumed.run_next(dispatched)
            dispatched.assert_not_called()

    def test_resume_verifies_finished_result_bytes_and_digest(self) -> None:
        plan = _plan()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal = codex_campaign.CampaignJournal.create(
                root, plan=plan, manifest_sha256=MANIFEST_SHA256
            )
            journal.run_next(lambda spec: _result(spec))
            result_path = next((root / "results").glob("*.json"))
            result_path.write_text("{}\n", encoding="utf-8")

            with self.assertRaisesRegex(
                codex_campaign.CampaignContractError, "result digest"
            ):
                codex_campaign.CampaignJournal.open(
                    root, plan=plan, manifest_sha256=MANIFEST_SHA256
                )

    def test_campaign_runs_strictly_sequential_and_stops_on_inconclusive(self) -> None:
        plan = _plan()
        with tempfile.TemporaryDirectory() as raw:
            journal = codex_campaign.CampaignJournal.create(
                Path(raw), plan=plan, manifest_sha256=MANIFEST_SHA256
            )
            active = 0
            maximum = 0
            dispatched: list[object] = []

            def runner(spec):
                nonlocal active, maximum
                active += 1
                maximum = max(maximum, active)
                dispatched.append(spec)
                result = _result(spec, state="INCONCLUSIVE")
                active -= 1
                return result

            summary = codex_campaign.run_campaign(journal, runner)

        self.assertEqual(1, maximum)
        self.assertEqual([plan[0]], dispatched)
        self.assertEqual("blocked", summary["status"])
        self.assertEqual(1, summary["completed_trials"])


class ContainerCommandTests(unittest.TestCase):
    def _inputs(self, root: Path, *, auth: bool) -> codex_container.ContainerInputs:
        repository = root / "repository"
        output = root / "output"
        repository.mkdir()
        (repository / ".git").mkdir()
        output.mkdir(mode=0o700)
        auth_file = None
        if auth:
            auth_file = root / "auth.json"
            auth_file.write_text('{"tokens":{"access_token":"opaque-secret"}}', encoding="utf-8")
            if os.name != "nt":
                auth_file.chmod(0o600)
        return codex_container.ContainerInputs(
            image_id=IMAGE_ID,
            repository=repository,
            output_root=output,
            auth_file=auth_file,
        )

    def test_preflight_is_non_root_read_only_networkless_and_credential_free(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            command = codex_container.build_docker_command(
                "preflight", self._inputs(Path(raw), auth=False)
            )
        rendered = " ".join(command)
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop", command)
        self.assertIn("ALL", command)
        self.assertIn("no-new-privileges:true", command)
        self.assertIn("65532:65532", command)
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertNotIn("auth.json", rendered)
        self.assertNotIn("docker.sock", rendered)
        self.assertEqual(IMAGE_ID, command[-2])
        self.assertEqual("--preflight", command[-1])

    def test_live_launch_mounts_auth_read_only_and_uses_no_proxy_override(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            command = codex_container.build_docker_command(
                "canary", self._inputs(Path(raw), auth=True)
            )
        rendered = " ".join(command)
        self.assertIn("target=/run/secrets/auth.json,readonly", rendered)
        self.assertIn("target=/source,readonly", rendered)
        self.assertIn("target=/output", rendered)
        self.assertEqual(
            ("--canary", "--auth-file", "/run/secrets/auth.json"), command[-3:]
        )
        self.assertNotIn("HTTP_PROXY", rendered.upper())
        self.assertNotIn("OPENAI_API", rendered.upper())
        self.assertNotIn("CHATGPT_BASE", rendered.upper())

    def test_mutable_image_tags_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            inputs = self._inputs(Path(raw), auth=False)
            inputs = codex_container.ContainerInputs(
                image_id="route001:latest",
                repository=inputs.repository,
                output_root=inputs.output_root,
                auth_file=None,
            )
            with self.assertRaisesRegex(
                codex_container.ContainerContractError, "immutable image ID"
            ):
                codex_container.build_docker_command("preflight", inputs)

    def _canary_args(self, inputs: codex_container.ContainerInputs) -> list[str]:
        arguments = [
            "canary",
            "--image-id",
            inputs.image_id,
            "--repository",
            str(inputs.repository),
            "--output-root",
            str(inputs.output_root),
        ]
        if inputs.auth_file is not None:
            arguments.extend(("--auth-file", str(inputs.auth_file)))
        return arguments

    def _run_canary_main(self, inputs, runner):
        with (
            mock.patch("codex_container.inspect_image", return_value={}),
            mock.patch("codex_container.subprocess.run", side_effect=runner),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            exit_code = codex_container.main(self._canary_args(inputs))
        result_path = inputs.output_root / "canary-result.json"
        result = (
            json.loads(result_path.read_text(encoding="utf-8"))
            if result_path.is_file()
            else None
        )
        return exit_code, result

    def test_canary_runs_preflight_then_one_live_trial_and_writes_compact_result(self) -> None:
        usage = {
            "input_tokens": 100,
            "cached_input_tokens": 20,
            "cache_write_input_tokens": 0,
            "output_tokens": 30,
            "reasoning_output_tokens": 10,
        }
        preflight = {
            "mode": "credential-free-preflight",
            "authenticated_call_started": False,
            "live_authorized": False,
            "result": {
                "state": "PASS",
                "reason_codes": ["credential-free-preflight-pass"],
            },
        }
        canary = {
            "state": "PASS",
            "reason_codes": ["observational-behavior-pass"],
            "trace": {"usage": usage},
            "verdict": {
                "behavior": {
                    "grader_count": 2,
                    "passed_count": 2,
                    "graders": [
                        {"index": 0, "passed": True},
                        {"index": 1, "passed": True},
                    ],
                }
            },
        }

        with tempfile.TemporaryDirectory() as raw:
            inputs = self._inputs(Path(raw), auth=True)
            observed: list[tuple[tuple[str, ...], dict[str, object]]] = []

            def runner(command, **kwargs):
                command = tuple(command)
                observed.append((command, kwargs))
                payload = preflight if command[-1] == "--preflight" else canary
                return subprocess.CompletedProcess(
                    command, 0, json.dumps(payload), ""
                )

            exit_code, result = self._run_canary_main(inputs, runner)

        self.assertEqual(0, exit_code)
        self.assertIsNotNone(result)
        self.assertEqual(2, len(observed))
        preflight_command, preflight_kwargs = observed[0]
        canary_command, canary_kwargs = observed[1]
        self.assertEqual("--preflight", preflight_command[-1])
        self.assertNotIn("auth.json", " ".join(preflight_command))
        self.assertEqual(
            ("--canary", "--auth-file", "/run/secrets/auth.json"),
            canary_command[-3:],
        )
        self.assertIn("target=/run/secrets/auth.json,readonly", " ".join(canary_command))
        for kwargs in (preflight_kwargs, canary_kwargs):
            self.assertIs(subprocess.DEVNULL, kwargs["stdin"])
            self.assertIs(subprocess.PIPE, kwargs["stdout"])
            self.assertIs(subprocess.PIPE, kwargs["stderr"])
            self.assertTrue(kwargs["text"])
            self.assertFalse(kwargs["check"])
        self.assertEqual(
            {
                "schema_version": 1,
                "image_id": IMAGE_ID,
                "preflight": {
                    "passed": True,
                    "exit_code": 0,
                    "reason_codes": ["credential-free-preflight-pass"],
                },
                "canary": {
                    "started": True,
                    "exit_code": 0,
                    "state": "PASS",
                    "reason_codes": ["observational-behavior-pass"],
                    "failed_grader_indices": [],
                    "usage": usage,
                },
            },
            result,
        )

    def test_failed_canary_reports_only_failed_grader_indices(self) -> None:
        preflight = {
            "mode": "credential-free-preflight",
            "authenticated_call_started": False,
            "live_authorized": False,
            "result": {
                "state": "PASS",
                "reason_codes": ["credential-free-preflight-pass"],
            },
        }
        canary = {
            "state": "FAIL",
            "reason_codes": ["behavior-grader-failed"],
            "trace": {"usage": {}},
            "verdict": {
                "behavior": {
                    "grader_count": 3,
                    "passed_count": 2,
                    "graders": [
                        {"index": 0, "passed": True},
                        {"index": 1, "passed": False},
                        {"index": 2, "passed": True},
                    ],
                }
            },
        }

        with tempfile.TemporaryDirectory() as raw:
            inputs = self._inputs(Path(raw), auth=True)

            def runner(command, **kwargs):
                del kwargs
                command = tuple(command)
                payload = preflight if command[-1] == "--preflight" else canary
                return subprocess.CompletedProcess(
                    command,
                    0 if command[-1] == "--preflight" else 2,
                    json.dumps(payload),
                    "private grader detail must not persist",
                )

            exit_code, result = self._run_canary_main(inputs, runner)

        self.assertEqual(2, exit_code)
        self.assertEqual([1], result["canary"]["failed_grader_indices"])
        self.assertNotIn("private grader detail", json.dumps(result))

    def test_canary_rejects_inconsistent_grader_facts(self) -> None:
        preflight = {
            "mode": "credential-free-preflight",
            "authenticated_call_started": False,
            "live_authorized": False,
            "result": {
                "state": "PASS",
                "reason_codes": ["credential-free-preflight-pass"],
            },
        }
        canary = {
            "state": "FAIL",
            "reason_codes": ["behavior-grader-failed"],
            "trace": {"usage": {}},
            "verdict": {
                "behavior": {
                    "grader_count": 1,
                    "passed_count": 0,
                    "graders": [{"index": True, "passed": False}],
                }
            },
        }

        with tempfile.TemporaryDirectory() as raw:
            inputs = self._inputs(Path(raw), auth=True)

            def runner(command, **kwargs):
                del kwargs
                command = tuple(command)
                payload = preflight if command[-1] == "--preflight" else canary
                return subprocess.CompletedProcess(
                    command,
                    0 if command[-1] == "--preflight" else 2,
                    json.dumps(payload),
                    "",
                )

            exit_code, result = self._run_canary_main(inputs, runner)

        self.assertEqual(3, exit_code)
        self.assertEqual("INCONCLUSIVE", result["canary"]["state"])
        self.assertEqual(
            ["canary-output-invalid"], result["canary"]["reason_codes"]
        )
        self.assertIsNone(result["canary"]["failed_grader_indices"])

    def test_failed_preflight_writes_result_and_never_starts_the_paid_trial(self) -> None:
        preflight = {
            "mode": "credential-free-preflight",
            "authenticated_call_started": False,
            "live_authorized": False,
            "result": {
                "state": "INCONCLUSIVE",
                "reason_codes": ["python-runtime-mismatch"],
            },
        }

        with tempfile.TemporaryDirectory() as raw:
            inputs = self._inputs(Path(raw), auth=True)
            observed: list[tuple[str, ...]] = []

            def runner(command, **kwargs):
                del kwargs
                command = tuple(command)
                observed.append(command)
                if command[-1] != "--preflight":
                    raise AssertionError("paid canary started after failed preflight")
                return subprocess.CompletedProcess(
                    command, 4, json.dumps(preflight), ""
                )

            exit_code, result = self._run_canary_main(inputs, runner)

        self.assertEqual(4, exit_code)
        self.assertIsNotNone(result)
        self.assertEqual(1, len(observed))
        self.assertEqual(
            {
                "started": False,
                "exit_code": None,
                "state": None,
                "reason_codes": ["preflight-failed"],
                "failed_grader_indices": None,
                "usage": None,
            },
            result["canary"],
        )
        self.assertEqual(
            {
                "passed": False,
                "exit_code": 4,
                "reason_codes": ["python-runtime-mismatch"],
            },
            result["preflight"],
        )

    def test_canary_rejects_missing_auth_before_running_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            inputs = self._inputs(Path(raw), auth=False)
            runner = mock.Mock(
                side_effect=AssertionError("preflight ran before live inputs were valid")
            )
            exit_code, result = self._run_canary_main(inputs, runner)

        self.assertEqual(3, exit_code)
        self.assertIsNone(result)
        runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
