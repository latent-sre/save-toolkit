"""Fail-closed structural contract for the protected-main canary workflow."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/validate-canary.yml"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
PINNED_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@([0-9a-f]{40})$")


def load_workflow() -> tuple[str, dict]:
    text = WORKFLOW.read_text(encoding="utf-8")
    document = yaml.safe_load(text)
    if not isinstance(document, dict):
        raise AssertionError("canary workflow must parse as a mapping")
    return text, document


def workflow_events(document: dict) -> dict:
    # PyYAML implements YAML 1.1 and therefore parses the unquoted GitHub key `on` as True.
    events = document.get("on", document.get(True))
    if not isinstance(events, dict):
        raise AssertionError("canary workflow must declare mapping-form events")
    return events


def steps(job: dict) -> list[dict]:
    value = job.get("steps")
    if not isinstance(value, list):
        raise AssertionError("workflow job must contain steps")
    return value


def action_steps(document: dict) -> list[dict]:
    return [
        step
        for job in document["jobs"].values()
        for step in steps(job)
        if "uses" in step
    ]


class CanaryWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text, self.workflow = load_workflow()

    def test_is_manual_only_with_closed_required_inputs(self) -> None:
        events = workflow_events(self.workflow)
        self.assertEqual({"workflow_dispatch"}, set(events))
        inputs = events["workflow_dispatch"]["inputs"]
        self.assertEqual({"candidate_sha", "canary_ref"}, set(inputs))
        for name in inputs:
            self.assertIs(inputs[name]["required"], True, name)
            self.assertEqual("string", inputs[name]["type"], name)

    def test_has_read_only_repository_authority_and_no_secret_surface(self) -> None:
        self.assertEqual({"contents": "read"}, self.workflow["permissions"])
        self.assertNotIn("env", self.workflow)
        lowered = self.text.lower()
        for forbidden in (
            "${{ secrets.",
            "id-token: write",
            "contents: write",
            "actions: write",
            "pull-requests: write",
            "environment:",
            "self-hosted",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_every_action_is_pinned_to_a_full_commit(self) -> None:
        found = action_steps(self.workflow)
        self.assertGreaterEqual(len(found), 5)
        for step in found:
            match = PINNED_ACTION.fullmatch(step["uses"])
            self.assertIsNotNone(match, step["uses"])
            self.assertTrue(FULL_SHA.fullmatch(match.group(1)), step["uses"])

    def test_preflight_binds_main_workflow_candidate_and_immutable_canary_ref(self) -> None:
        preflight = self.workflow["jobs"]["preflight"]
        self.assertEqual("ubuntu-latest", preflight["runs-on"])
        self.assertEqual(
            {
                "tree_sha": "${{ steps.bind.outputs.tree_sha }}",
                "workflow_blob_sha": "${{ steps.bind.outputs.workflow_blob_sha }}",
            },
            preflight["outputs"],
        )
        checkout = next(step for step in steps(preflight) if step.get("name") == "Check out trusted main")
        self.assertEqual("${{ github.sha }}", checkout["with"]["ref"])
        self.assertIs(checkout["with"]["persist-credentials"], False)
        bind = next(step for step in steps(preflight) if step.get("id") == "bind")
        run = bind["run"]
        for required in (
            "refs/heads/main",
            "^[0-9a-f]{40}$",
            "^canary/[a-z0-9][a-z0-9._-]*/[0-9a-f]{40}$",
            "git/ref/heads/${CANARY_REF}",
            "workflow_blob_sha",
            "tree_sha",
        ):
            self.assertIn(required, run)

    def test_candidate_gate_is_three_os_credential_free_and_exact_sha(self) -> None:
        gate = self.workflow["jobs"]["gate"]
        self.assertEqual("preflight", gate["needs"])
        self.assertEqual("${{ matrix.os }}", gate["runs-on"])
        self.assertNotIn("env", gate)
        self.assertNotIn("permissions", gate)
        matrix = gate["strategy"]["matrix"]["include"]
        self.assertEqual(
            {("ubuntu-latest", "python3"), ("macos-latest", "python3"), ("windows-latest", "python")},
            {(entry["os"], entry["py"]) for entry in matrix},
        )
        checkout = next(step for step in steps(gate) if step.get("name") == "Check out candidate")
        self.assertEqual("${{ inputs.candidate_sha }}", checkout["with"]["ref"])
        self.assertIs(checkout["with"]["persist-credentials"], False)
        for step in steps(gate):
            self.assertNotIn("env", step, step.get("name"))
        commands = "\n".join(str(step.get("run", "")) for step in steps(gate))
        self.assertIn("-m pip install -r requirements-dev.txt", commands)
        self.assertIn("scripts/gate_a.py", commands)

    def test_evidence_is_built_on_a_fresh_runner_after_all_gates(self) -> None:
        evidence = self.workflow["jobs"]["evidence"]
        self.assertEqual({"preflight", "gate"}, set(evidence["needs"]))
        self.assertEqual("ubuntu-latest", evidence["runs-on"])
        self.assertFalse(any("actions/checkout" in step.get("uses", "") for step in steps(evidence)))
        recheck = next(step for step in steps(evidence) if step.get("name") == "Recheck immutable canary ref")
        self.assertIn("git/ref/heads/${CANARY_REF}", recheck["run"])
        self.assertIn('"${REMOTE_SHA}" != "${CANDIDATE_SHA}"', recheck["run"])
        writer = next(step for step in steps(evidence) if step.get("name") == "Write trusted evidence")
        for expected in (
            "candidate_sha",
            "canary_ref",
            "tree_sha",
            "workflow_blob_sha",
            "workflow_run_id",
            "gate_result",
        ):
            self.assertIn(expected, writer["run"])
        upload = next(step for step in steps(evidence) if "actions/upload-artifact" in step.get("uses", ""))
        self.assertEqual("canary-evidence-${{ inputs.candidate_sha }}", upload["with"]["name"])
        self.assertEqual("canary-evidence.json", upload["with"]["path"])
        self.assertEqual("error", upload["with"]["if-no-files-found"])


if __name__ == "__main__":
    unittest.main()
