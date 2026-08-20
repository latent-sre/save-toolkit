#!/usr/bin/env python3
"""Fail-closed contracts for the Linux-container ROUTE-001 executor."""
from __future__ import annotations

import hashlib
import json
import os
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


if __name__ == "__main__":
    unittest.main()
