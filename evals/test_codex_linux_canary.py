#!/usr/bin/env python3
"""Fail-closed contracts for the Linux-container ROUTE-001 canary."""
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
import codex_container  # noqa: E402
import run_codex_routing  # noqa: E402


# The mutation guard derives subjects from exact path literals when a test spans several modules.
MUTATION_SUBJECTS = (
    "evals/codex_container.py",
    "evals/run_codex_routing.py",
)


IMAGE_ID = "sha256:" + "a" * 64
class LinuxManifestTests(unittest.TestCase):
    def test_linux_manifest_is_the_exact_fixed_canary_shape(self) -> None:
        manifest = run_codex_routing.load_manifest(
            run_codex_routing.LINUX_MANIFEST_PATH
        )

        self.assertEqual(
            "route-001-codex-terra-canary-v1", manifest["instrument"]
        )
        self.assertEqual("linux-x86_64", manifest["runtime_platform"])
        self.assertEqual("linux-container", manifest["runtime_kind"])
        self.assertEqual("65532:65532", manifest["container_user"])
        for retired in (
            "campaign",
            "trials",
            "threshold",
            "before_revision",
            "scenarios",
            "scenario_bundle_sha256",
        ):
            self.assertNotIn(retired, manifest)
        self.assertEqual([], run_codex_routing.validate_manifest(manifest))
        self.assertEqual([], run_codex_routing.validate_canary_scenario(manifest))
        spec = run_codex_routing.canary_spec(manifest)
        self.assertEqual(run_codex_routing.CANARY_SCENARIO_ID, spec.scenario_id)
        self.assertEqual(run_codex_routing.CURRENT_REVISION, spec.revision)
        self.assertEqual(run_codex_routing.CANARY_TRIAL, spec.trial)

    def test_legacy_campaign_key_is_rejected(self) -> None:
        manifest = run_codex_routing.load_manifest()
        manifest["campaign"] = "route-001-codex-terra-linux-v1"

        self.assertIn(
            "manifest has unknown keys: campaign",
            run_codex_routing.validate_manifest(manifest),
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

    def test_retired_campaign_mode_is_rejected_before_docker_launch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(codex_container.ContainerContractError, "mode"):
                codex_container.build_docker_command(
                    "campaign", self._inputs(Path(raw), auth=True)
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
