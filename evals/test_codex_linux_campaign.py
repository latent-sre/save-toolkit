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
OTHER_IMAGE_ID = "sha256:" + "d" * 64
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
            with codex_campaign.CampaignLock(root) as lock:
                journal = codex_campaign.CampaignJournal.create(
                    root,
                    plan=plan,
                    manifest_sha256=MANIFEST_SHA256,
                    container_image_id=IMAGE_ID,
                    lock=lock,
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
            with codex_campaign.CampaignLock(root) as lock:
                journal = codex_campaign.CampaignJournal.create(
                    root,
                    plan=plan,
                    manifest_sha256=MANIFEST_SHA256,
                    container_image_id=IMAGE_ID,
                    lock=lock,
                )
                journal.begin(plan[0])
            with codex_campaign.CampaignLock(root) as lock:
                resumed = codex_campaign.CampaignJournal.open(
                    root,
                    plan=plan,
                    manifest_sha256=MANIFEST_SHA256,
                    container_image_id=IMAGE_ID,
                    lock=lock,
                )
                dispatched = mock.Mock()
                with self.assertRaises(codex_campaign.UnknownOutcomeError):
                    resumed.run_next(dispatched)
                dispatched.assert_not_called()

    def test_resume_verifies_finished_result_bytes_and_digest(self) -> None:
        plan = _plan()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with codex_campaign.CampaignLock(root) as lock:
                journal = codex_campaign.CampaignJournal.create(
                    root,
                    plan=plan,
                    manifest_sha256=MANIFEST_SHA256,
                    container_image_id=IMAGE_ID,
                    lock=lock,
                )
                journal.run_next(lambda spec: _result(spec))
            result_path = next((root / "results").glob("*.json"))
            result_path.write_text("{}\n", encoding="utf-8")

            with codex_campaign.CampaignLock(root) as lock:
                with self.assertRaisesRegex(
                    codex_campaign.CampaignContractError, "result digest"
                ):
                    codex_campaign.CampaignJournal.open(
                        root,
                        plan=plan,
                        manifest_sha256=MANIFEST_SHA256,
                        container_image_id=IMAGE_ID,
                        lock=lock,
                    )

    def test_campaign_runs_strictly_sequential_and_stops_on_inconclusive(self) -> None:
        plan = _plan()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with codex_campaign.CampaignLock(root) as lock:
                journal = codex_campaign.CampaignJournal.create(
                    root,
                    plan=plan,
                    manifest_sha256=MANIFEST_SHA256,
                    container_image_id=IMAGE_ID,
                    lock=lock,
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

    def test_inconclusive_result_remains_blocked_after_reopen(self) -> None:
        plan = _plan()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with codex_campaign.CampaignLock(root) as lock:
                journal = codex_campaign.CampaignJournal.create(
                    root,
                    plan=plan,
                    manifest_sha256=MANIFEST_SHA256,
                    container_image_id=IMAGE_ID,
                    lock=lock,
                )
                journal.run_next(lambda spec: _result(spec, state="INCONCLUSIVE"))
            with codex_campaign.CampaignLock(root) as lock:
                resumed = codex_campaign.CampaignJournal.open(
                    root,
                    plan=plan,
                    manifest_sha256=MANIFEST_SHA256,
                    container_image_id=IMAGE_ID,
                    lock=lock,
                )
                dispatched = mock.Mock()
                summary = codex_campaign.run_campaign(resumed, dispatched)

        dispatched.assert_not_called()
        self.assertEqual("blocked", summary["status"])
        self.assertTrue(summary["inconclusive_result"])

    def test_final_inconclusive_result_is_not_reported_complete(self) -> None:
        plan = _plan()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with codex_campaign.CampaignLock(root) as lock:
                journal = codex_campaign.CampaignJournal.create(
                    root,
                    plan=plan,
                    manifest_sha256=MANIFEST_SHA256,
                    container_image_id=IMAGE_ID,
                    lock=lock,
                )
                calls = 0

                def runner(spec):
                    nonlocal calls
                    calls += 1
                    state = "INCONCLUSIVE" if calls == len(plan) else "PASS"
                    return _result(spec, state=state)

                summary = codex_campaign.run_campaign(journal, runner)

        self.assertEqual(len(plan), summary["completed_trials"])
        self.assertEqual("blocked", summary["status"])
        self.assertTrue(summary["inconclusive_result"])

    def test_campaign_lock_rejects_a_concurrent_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with codex_campaign.CampaignLock(root):
                with self.assertRaises(codex_campaign.CampaignBusyError):
                    with codex_campaign.CampaignLock(root):
                        self.fail("concurrent campaign lock was acquired")

    def test_resume_rejects_a_different_container_image(self) -> None:
        plan = _plan()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with codex_campaign.CampaignLock(root) as lock:
                codex_campaign.CampaignJournal.create(
                    root,
                    plan=plan,
                    manifest_sha256=MANIFEST_SHA256,
                    container_image_id=IMAGE_ID,
                    lock=lock,
                )
            with codex_campaign.CampaignLock(root) as lock:
                with self.assertRaisesRegex(
                    codex_campaign.CampaignContractError, "contract bytes"
                ):
                    codex_campaign.CampaignJournal.open(
                        root,
                        plan=plan,
                        manifest_sha256=MANIFEST_SHA256,
                        container_image_id=OTHER_IMAGE_ID,
                        lock=lock,
                    )


class ContainerCommandTests(unittest.TestCase):
    def test_canary_prompt_digest_matches_the_fixed_manifest_prompt(self) -> None:
        manifest = run_codex_routing.load_manifest(
            run_codex_routing.LINUX_MANIFEST_PATH
        )
        prompt = manifest["canary_scenario"]["prompt"]
        expected = hashlib.sha256(
            f"$gcp-ops\n\n{prompt}".encode("utf-8")
        ).hexdigest()

        self.assertEqual(expected, codex_container.CANARY_PROMPT_SHA256)

    def test_description_prompt_digest_is_target_blind_and_exact(self) -> None:
        manifest = run_codex_routing.load_manifest(
            run_codex_routing.LINUX_MANIFEST_PATH
        )
        prompt = (
            f"{run_codex_routing.CANARY_DESCRIPTION_PROMPT_PREFIX}"
            f"{manifest['canary_scenario']['prompt']}"
        )
        self.assertNotIn("gcp-ops", run_codex_routing.CANARY_DESCRIPTION_PROMPT_PREFIX)
        self.assertEqual(
            hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            codex_container.CANARY_DESCRIPTION_PROMPT_SHA256,
        )

    def _inputs(self, root: Path, *, auth: bool) -> codex_container.ContainerInputs:
        repository = root / "repository"
        output = root / "output"
        repository.mkdir()
        (repository / ".git").mkdir()
        output.mkdir(mode=0o700)
        # Resolve after creation so symlinked temp roots (e.g. /var → /private/var on macOS)
        # do not trip the _normal_path resolved != candidate check.
        repository = repository.resolve()
        output = output.resolve()
        auth_file = None
        if auth:
            auth_file = root / "auth.json"
            auth_file.write_text('{"tokens":{"access_token":"opaque-secret"}}', encoding="utf-8")
            if os.name != "nt":
                auth_file.chmod(0o600)
            auth_file = auth_file.resolve()
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
            with mock.patch.object(
                codex_container, "_path_owner_uid", return_value=65532
            ):
                command = codex_container.build_docker_command(
                    "canary", self._inputs(Path(raw), auth=True)
                )
        rendered = " ".join(command)
        self.assertIn("target=/run/secrets/auth.json,readonly", rendered)
        self.assertIn("target=/source,readonly", rendered)
        self.assertNotIn("target=/output", rendered)
        self.assertEqual(
            (
                "--canary",
                "--canary-arm",
                "body",
                "--auth-file",
                "/run/secrets/auth.json",
            ),
            command[-5:],
        )
        self.assertNotIn("HTTP_PROXY", rendered.upper())
        self.assertNotIn("OPENAI_API", rendered.upper())
        self.assertNotIn("CHATGPT_BASE", rendered.upper())

    def test_campaign_passes_the_exact_image_id_to_the_inner_journal(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with mock.patch.object(
                codex_container, "_path_owner_uid", return_value=65532
            ):
                command = codex_container.build_docker_command(
                    "campaign", self._inputs(Path(raw), auth=True)
                )

        self.assertIn("--container-image-id", command)
        self.assertIn("target=/output", " ".join(command))
        self.assertEqual(
            IMAGE_ID, command[command.index("--container-image-id") + 1]
        )

    def test_native_linux_rejects_auth_not_owned_by_the_container_uid(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            inputs = self._inputs(Path(raw), auth=True)
            with (
                mock.patch.object(
                    codex_container,
                    "_host_requires_container_uid_ownership",
                    return_value=True,
                ),
                mock.patch.object(codex_container, "_path_owner_uid", return_value=1000),
                self.assertRaisesRegex(
                    codex_container.ContainerContractError, "owned by UID 65532"
                ),
            ):
                codex_container.build_docker_command("canary", inputs)

    def test_native_linux_rejects_campaign_output_not_owned_by_container_uid(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            inputs = self._inputs(Path(raw), auth=True)

            def owner(path: Path) -> int:
                return 1000 if path == inputs.output_root else 65532

            with (
                mock.patch.object(
                    codex_container,
                    "_host_requires_container_uid_ownership",
                    return_value=True,
                ),
                mock.patch.object(codex_container, "_path_owner_uid", side_effect=owner),
                self.assertRaisesRegex(
                    codex_container.ContainerContractError,
                    "output root must be owned by UID 65532",
                ),
            ):
                codex_container.build_docker_command("campaign", inputs)

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

    def _canary_args(
        self, inputs: codex_container.ContainerInputs, *, arm: str | None = None
    ) -> list[str]:
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
        if arm is not None:
            arguments.extend(("--canary-arm", arm))
        return arguments

    def _run_canary_main(self, inputs, runner, *, arm: str | None = None):
        with (
            mock.patch("codex_container.inspect_image", return_value={}),
            mock.patch("codex_container.subprocess.run", side_effect=runner),
            mock.patch("codex_container._path_owner_uid", return_value=65532),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            exit_code = codex_container.main(self._canary_args(inputs, arm=arm))
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
            "scenario": {"prompt_sha256": codex_container.CANARY_PROMPT_SHA256},
            "configuration": {"invocation_mode": "explicit-skill-body-probe"},
            "runtime": {
                "selected_skill_name": "gcp-ops",
                "selected_skill_body_sha256": codex_container.CANARY_SKILL_BODY_SHA256,
            },
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
            (
                "--canary",
                "--canary-arm",
                "body",
                "--auth-file",
                "/run/secrets/auth.json",
            ),
            canary_command[-5:],
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
                    "arm": "body",
                    "invocation_mode": "explicit-skill-body-probe",
                    "prompt_sha256": codex_container.CANARY_PROMPT_SHA256,
                    "selected_skill_body_sha256": codex_container.CANARY_SKILL_BODY_SHA256,
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
            "scenario": {"prompt_sha256": codex_container.CANARY_PROMPT_SHA256},
            "configuration": {"invocation_mode": "explicit-skill-body-probe"},
            "runtime": {
                "selected_skill_name": "gcp-ops",
                "selected_skill_body_sha256": codex_container.CANARY_SKILL_BODY_SHA256,
            },
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
        self.assertEqual(
            "explicit-skill-body-probe", result["canary"]["invocation_mode"]
        )
        self.assertEqual(
            codex_container.CANARY_PROMPT_SHA256,
            result["canary"]["prompt_sha256"],
        )
        self.assertEqual(
            codex_container.CANARY_SKILL_BODY_SHA256,
            result["canary"]["selected_skill_body_sha256"],
        )
        self.assertNotIn("private grader detail", json.dumps(result))

    def test_description_canary_uses_catalog_selection_without_body_binding(self) -> None:
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
            "reason_codes": ["description-selection-pass"],
            "scenario": {
                "prompt_sha256": codex_container.CANARY_DESCRIPTION_PROMPT_SHA256
            },
            "configuration": {"invocation_mode": "description-selection-probe"},
            "trace": {"usage": {}},
            "verdict": {
                "behavior": {
                    "grader_count": 1,
                    "passed_count": 1,
                    "graders": [{"index": 0, "passed": True}],
                }
            },
        }

        with tempfile.TemporaryDirectory() as raw:
            inputs = self._inputs(Path(raw), auth=True)

            def runner(command, **kwargs):
                del kwargs
                command = tuple(command)
                payload = preflight if command[-1] == "--preflight" else canary
                return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

            exit_code, result = self._run_canary_main(
                inputs, runner, arm="description"
            )

        self.assertEqual(0, exit_code)
        self.assertEqual("description", result["canary"]["arm"])
        self.assertEqual(
            "description-selection-probe", result["canary"]["invocation_mode"]
        )
        self.assertIsNone(result["canary"]["selected_skill_body_sha256"])

    def test_canary_rejects_a_missing_explicit_probe_mode(self) -> None:
        payload = {
            "state": "PASS",
            "reason_codes": ["observational-behavior-pass"],
            "scenario": {"prompt_sha256": codex_container.CANARY_PROMPT_SHA256},
            "trace": {"usage": {}},
            "verdict": {
                "behavior": {
                    "grader_count": 1,
                    "passed_count": 1,
                    "graders": [{"index": 0, "passed": True}],
                }
            },
        }
        process = subprocess.CompletedProcess(
            ("codex",), 0, json.dumps(payload), ""
        )

        result, exit_code = codex_container._canary_result(process)

        self.assertEqual(3, exit_code)
        self.assertEqual("INCONCLUSIVE", result["state"])
        self.assertEqual(["canary-output-invalid"], result["reason_codes"])
        self.assertIsNone(result["invocation_mode"])

    def test_canary_rejects_a_state_exit_code_mismatch(self) -> None:
        payload = {
            "state": "PASS",
            "reason_codes": ["observational-behavior-pass"],
            "scenario": {"prompt_sha256": codex_container.CANARY_PROMPT_SHA256},
            "configuration": {"invocation_mode": "explicit-skill-body-probe"},
            "trace": {"usage": {}},
            "verdict": {
                "behavior": {
                    "grader_count": 1,
                    "passed_count": 1,
                    "graders": [{"index": 0, "passed": True}],
                }
            },
        }
        process = subprocess.CompletedProcess(
            ("codex",), 2, json.dumps(payload), ""
        )

        result, exit_code = codex_container._canary_result(process)

        self.assertEqual(3, exit_code)
        self.assertEqual("INCONCLUSIVE", result["state"])
        self.assertEqual(["canary-output-invalid"], result["reason_codes"])

    def test_canary_rejects_a_wrong_explicit_probe_prompt_digest(self) -> None:
        payload = {
            "state": "PASS",
            "reason_codes": ["observational-behavior-pass"],
            "scenario": {"prompt_sha256": "0" * 64},
            "configuration": {"invocation_mode": "explicit-skill-body-probe"},
            "trace": {"usage": {}},
            "verdict": {
                "behavior": {
                    "grader_count": 1,
                    "passed_count": 1,
                    "graders": [{"index": 0, "passed": True}],
                }
            },
        }
        process = subprocess.CompletedProcess(
            ("codex",), 0, json.dumps(payload), ""
        )

        result, exit_code = codex_container._canary_result(process)

        self.assertEqual(3, exit_code)
        self.assertEqual("INCONCLUSIVE", result["state"])
        self.assertEqual(["canary-output-invalid"], result["reason_codes"])
        self.assertIsNone(result["prompt_sha256"])

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
            "scenario": {"prompt_sha256": codex_container.CANARY_PROMPT_SHA256},
            "configuration": {"invocation_mode": "explicit-skill-body-probe"},
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
                "arm": "body",
                "invocation_mode": None,
                "prompt_sha256": None,
                "selected_skill_body_sha256": None,
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
