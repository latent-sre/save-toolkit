"""Fail-closed contract for the brokered Codex/Sol conformance workflow."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/codex-sol-conformance.yml"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
PINNED_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@([0-9a-f]{40})$")
CODEX_ACTION_SHA = "dd78cb653811af44014baa08fe954e28d32c1bf9"


def load_workflow() -> tuple[str, dict]:
    text = WORKFLOW.read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    if not isinstance(document, dict):
        raise AssertionError("Codex conformance workflow must parse as a mapping")
    return text, document


def workflow_events(document: dict) -> dict:
    events = document.get("on", document.get(True))
    if not isinstance(events, dict):
        raise AssertionError("Codex conformance workflow must declare mapping-form events")
    return events


def steps(job: dict) -> list[dict]:
    value = job.get("steps")
    if not isinstance(value, list):
        raise AssertionError("workflow job must contain steps")
    return value


class CodexConformanceWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text, self.workflow = load_workflow()

    def test_is_manual_main_only_with_immutable_inputs(self) -> None:
        events = workflow_events(self.workflow)
        self.assertEqual({"workflow_dispatch"}, set(events))
        inputs = events["workflow_dispatch"]["inputs"]
        self.assertEqual({"candidate_sha", "canary_ref"}, set(inputs))
        self.assertTrue(all(item["required"] is True for item in inputs.values()))
        self.assertEqual("${{ github.ref == 'refs/heads/main' }}", self.workflow["jobs"]["preflight"]["if"])
        bind = next(step for step in steps(self.workflow["jobs"]["preflight"]) if step.get("id") == "bind")
        for contract in (
            "^[0-9a-f]{40}$",
            "^canary/[a-z0-9][a-z0-9._-]*/[0-9a-f]{40}$",
            "git/ref/heads/${CANARY_REF}",
            "workflow_blob_sha",
            "tree_sha",
        ):
            self.assertIn(contract, bind["run"])

    def test_repository_authority_is_read_only_and_every_action_is_sha_pinned(self) -> None:
        self.assertEqual({"contents": "read"}, self.workflow["permissions"])
        self.assertNotIn("pull_request_target", self.text)
        action_steps = [
            step
            for job in self.workflow["jobs"].values()
            for step in steps(job)
            if "uses" in step
        ]
        self.assertGreaterEqual(len(action_steps), 5)
        for step in action_steps:
            match = PINNED_ACTION.fullmatch(step["uses"])
            self.assertIsNotNone(match, step["uses"])
            self.assertTrue(FULL_SHA.fullmatch(match.group(1)), step["uses"])

    def test_api_key_exists_only_on_the_proxy_bootstrap_step(self) -> None:
        secret_reference = "${{ secrets.CODEX_CONFORMANCE_OPENAI_API_KEY }}"
        self.assertEqual(1, self.text.count(secret_reference))
        self.assertNotIn("env", self.workflow)
        conformance = self.workflow["jobs"]["conformance"]
        broker_index = next(
            index
            for index, step in enumerate(steps(conformance))
            if step.get("name") == "Establish credential broker and drop sudo"
        )
        checkout_index = next(
            index
            for index, step in enumerate(steps(conformance))
            if step.get("name") == "Check out candidate after the credential boundary exists"
        )
        trusted_index = next(
            index
            for index, step in enumerate(steps(conformance))
            if step.get("name") == "Check out trusted evaluator from main"
        )
        self.assertLess(trusted_index, broker_index)
        self.assertLess(broker_index, checkout_index)
        broker = steps(conformance)[broker_index]
        self.assertEqual(f"openai/codex-action@{CODEX_ACTION_SHA}", broker["uses"])
        self.assertEqual(secret_reference, broker["with"]["openai-api-key"])
        self.assertEqual("drop-sudo", broker["with"]["safety-strategy"])
        self.assertEqual("0.145.0", broker["with"]["codex-version"])
        self.assertNotIn("prompt", broker["with"])
        self.assertNotIn("prompt-file", broker["with"])
        self.assertEqual("trusted-main", steps(conformance)[trusted_index]["with"]["path"])
        self.assertEqual("candidate", steps(conformance)[checkout_index]["with"]["path"])

    def test_trusted_evaluator_reads_candidate_only_as_data_and_is_the_last_step(self) -> None:
        conformance_steps = steps(self.workflow["jobs"]["conformance"])
        run = conformance_steps[-1]
        self.assertEqual("Run pinned Sol skill and agent conformance", run["name"])
        self.assertEqual("run", run["id"])
        self.assertEqual(
            {
                "CODEX_HOME": "${{ runner.temp }}/sre-agents-broker-home",
                "CANDIDATE_ROOT": "${{ github.workspace }}/candidate",
                "TRUSTED_MAIN": "${{ github.workspace }}/trusted-main",
            },
            run["env"],
        )
        command = run["run"]
        self.assertIn('${TRUSTED_MAIN}/evals/run_codex_conformance.py', command)
        self.assertIn('${TRUSTED_MAIN}/evals/run_codex_agent_conformance.py', command)
        self.assertNotIn("candidate/evals/run_codex", command)
        self.assertEqual(2, command.count("--target-root"))
        self.assertEqual(2, command.count('"${CANDIDATE_ROOT}"'))
        self.assertNotIn("--manifest", command)
        self.assertEqual(2, command.count("--broker-config"))
        self.assertNotIn("auth.json", command)
        self.assertIn("skill_report_sha256", command)
        self.assertIn("agent_report_sha256", command)
        self.assertIn("skill_report_b64", command)
        self.assertIn("agent_report_b64", command)
        self.assertIn("131072", command)
        self.assertIn("stopping before another model lane", command)
        recheck = conformance_steps[-2]
        self.assertIn("git -C trusted-main rev-parse HEAD", recheck["run"])
        self.assertIn("git -C candidate rev-parse HEAD", recheck["run"])
        self.assertIn("HEAD^{tree}", recheck["run"])
        self.assertIn("EXPECTED_WORKFLOW_BLOB_SHA", recheck["run"])
        self.assertIn("git/ref/heads/${CANARY_REF}", recheck["run"])

    def test_reports_are_reconstructed_validated_and_attested_on_a_fresh_runner(self) -> None:
        evidence = self.workflow["jobs"]["evidence"]
        self.assertEqual({"preflight", "conformance"}, set(evidence["needs"]))
        self.assertFalse(any("openai/codex-action" in step.get("uses", "") for step in steps(evidence)))
        checkout = next(
            step
            for step in steps(evidence)
            if step.get("name") == "Check out trusted evidence reducer from main"
        )
        self.assertEqual("${{ github.sha }}", checkout["with"]["ref"])
        self.assertEqual("trusted-main", checkout["with"]["path"])
        self.assertFalse(checkout["with"]["persist-credentials"])
        recheck = next(
            step
            for step in steps(evidence)
            if step.get("name") == "Recheck trusted reducer and immutable canary ref"
        )
        self.assertIn("git -C trusted-main rev-parse HEAD", recheck["run"])
        self.assertIn("EXPECTED_WORKFLOW_BLOB_SHA", recheck["run"])
        writer = next(
            step
            for step in steps(evidence)
            if step.get("name") == "Reconstruct, validate, and attest reduced reports"
        )
        for contract in (
            "SKILL_REPORT_B64",
            "AGENT_REPORT_B64",
            "base64 --decode",
            "trusted-main/scripts/reduce_codex_conformance_reports.py",
            "--candidate-sha",
            "--evaluator-sha",
            "--workflow-blob-sha",
            "--tree-sha",
            "--conformance-job-result",
            "--output codex-sol-conformance-attestation.json",
        ):
            self.assertIn(contract, writer["run"])
        self.assertNotIn("candidate/scripts", writer["run"])
        upload = next(step for step in steps(evidence) if "actions/upload-artifact" in step.get("uses", ""))
        self.assertEqual("codex-sol-conformance-${{ inputs.candidate_sha }}", upload["with"]["name"])
        for filename in (
            "codex-sol-skills.json",
            "codex-sol-agents.json",
            "codex-sol-conformance-attestation.json",
        ):
            self.assertIn(filename, upload["with"]["path"])

    def test_every_job_has_a_hard_timeout(self) -> None:
        jobs = self.workflow["jobs"]
        self.assertEqual({"preflight", "conformance", "evidence"}, set(jobs))
        for name, job in jobs.items():
            timeout = job.get("timeout-minutes")
            self.assertIsInstance(timeout, int, name)
            self.assertGreater(timeout, 0, name)
            self.assertLessEqual(timeout, 120, name)


if __name__ == "__main__":
    unittest.main()
