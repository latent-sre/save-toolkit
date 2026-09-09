"""Check shipped asset structures: target-bound commands and non-authoritative context paths."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class SkillAssetTests(unittest.TestCase):
    def test_ci_starter_cancellation_is_local_to_each_validation_leg(self) -> None:
        workflow = yaml.safe_load(
            (ROOT / "skills/ci-actions/assets/ci.reusable.yml").read_text(encoding="utf-8")
        )
        self.assertFalse(workflow.get("concurrency", {}).get("cancel-in-progress", False))
        job = workflow["jobs"]["test"]
        self.assertTrue(job["concurrency"]["cancel-in-progress"])
        group = job["concurrency"]["group"]

        def resolve(workflow_name: str, ref: str, caller: str, version: str) -> str:
            context = {"github.workflow": workflow_name, "github.ref": ref,
                       "inputs.concurrency-key": caller, "matrix.python-version": version}
            return re.sub(r"\$\{\{\s*(.*?)\s*\}\}", lambda m: context[m[1]], group)

        # Reusable invocations, Python legs, branches and workflows must not cancel each other.
        groups = {resolve(workflow_name, ref, caller, version)
                  for workflow_name in ("checks", "release")
                  for ref in ("refs/heads/a", "refs/heads/b")
                  for caller in ("api", "worker")
                  for version in job["strategy"]["matrix"]["python-version"]}
        self.assertEqual(len(groups), 8 * len(job["strategy"]["matrix"]["python-version"]))

    def test_pcf_example_pushes_only_the_downloaded_release_paths(self) -> None:
        text = (ROOT / "skills/ci-actions/references/pcf-deploy-job.md").read_text(encoding="utf-8")
        job = yaml.safe_load(re.search(r"```yaml\n(.*?)\n```", text, re.DOTALL)[1])["deploy-prod"]
        download = next(step for step in job["steps"]
                        if step.get("uses", "").startswith("actions/download-artifact@"))
        self.assertIn("path", download["with"], "artifact destination is implicit")
        release_dir = job["env"]["RELEASE_DIR"]
        # GitHub's jobs.<job_id>.env context contract excludes runner and steps.
        job_env_contexts = {"github", "needs", "strategy", "matrix", "vars", "secrets", "inputs"}
        for expression in re.findall(r"\$\{\{\s*(.*?)\s*\}\}", release_dir):
            self.assertIn(expression.split(".")[0], job_env_contexts)
        self.assertEqual(download["with"]["path"], "${{ env.RELEASE_DIR }}")
        self.assertTrue(release_dir)
        deploy = next(step for step in job["steps"] if "cf push " in step.get("run", ""))
        push = next(line for line in deploy["run"].splitlines() if line.strip().startswith("cf push "))
        words = shlex.split(push)
        for flag, filename in (("-p", "app.zip"), ("-f", "manifest.yml")):
            self.assertIn(flag, words)
            self.assertEqual(words[words.index(flag) + 1], f"$RELEASE_DIR/{filename}")
        self.assertEqual(job["needs"], "build")
        # Identity checks precede credential use; parsing this plan never executes cf.
        verify_index = next(i for i, step in enumerate(job["steps"])
                            if "sha256sum" in step.get("run", ""))
        self.assertLess(verify_index, job["steps"].index(deploy))
        verify = job["steps"][verify_index]
        self.assertEqual(verify["env"]["APP_SHA256"], "${{ needs.build.outputs.app_sha256 }}")
        self.assertEqual(verify["env"]["MANIFEST_SHA256"], "${{ needs.build.outputs.manifest_sha256 }}")

    def test_operational_template_revision_slots_use_short_commit_ids(self) -> None:
        for name, field, expected in (
            ("runbook/assets/runbook-template.md", "source_revision",
             "<repository@short-commit or reviewed release identifier>"),
            ("postmortem/assets/postmortem-template.md", "source_revision",
             "<repository@short-commit or reviewed release identifier>"),
            ("operational-learning/assets/service-card-template.md", "source_revision",
             "<repository@short-commit or reviewed release identifier>"),
            ("operational-learning/assets/alert-card-template.md", "source_definition",
             "<repository path + unique short commit ID>"),
        ):
            with self.subTest(template=name):
                text = (ROOT / "skills" / name).read_text(encoding="utf-8")
                metadata = yaml.safe_load(text.split("---", 2)[1])
                self.assertEqual(metadata[field], expected)

    def test_postmortem_template_keeps_unknown_metadata_nullable(self) -> None:
        text = (ROOT / "skills/postmortem/assets/postmortem-template.md").read_text(encoding="utf-8")
        metadata = yaml.safe_load(text.split("---", 2)[1])
        for field in ("severity", "started_at", "resolved_at", "resolution_confirmed_at"):
            with self.subTest(field=field):
                self.assertIn(field, metadata)
                self.assertIsNone(metadata[field], "unknown facts must not acquire a default value")

    def test_gcp_triage_commands_bind_the_supplied_target(self) -> None:
        text = (ROOT / "skills/gcp-ops/SKILL.md").read_text(encoding="utf-8")
        commands = re.findall(r"`(gcloud run [^`\n]+)`|^(gcloud run .+)$", text, re.MULTILINE)
        self.assertTrue(commands, "no Cloud Run command examples found")
        for inline, fenced in commands:
            command = inline or fenced
            with self.subTest(command=command):
                words = shlex.split(command)
                self.assertIn("--project", words)
                self.assertEqual(words[words.index("--project") + 1], "<project>")
                self.assertIn("--region", words)
                self.assertEqual(words[words.index("--region") + 1], "<region>")

    def test_gcp_logging_example_binds_service_location_and_project(self) -> None:
        text = (ROOT / "skills/gcp-ops/SKILL.md").read_text(encoding="utf-8")
        commands = re.findall(r"^gcloud logging read .+$", text, re.MULTILINE)
        self.assertTrue(commands, "no Logging command examples found")
        for command in commands:
            with self.subTest(command=command):
                words = shlex.split(command)
                self.assertIn("resource.labels.service_name=<service>", words[3])
                self.assertIn("resource.labels.location=<region>", words[3])
                self.assertIn("--project", words)
                self.assertEqual(words[words.index("--project") + 1], "<project>")

    def test_gcp_example_reads_remain_allowed_and_traffic_writes_denied(self) -> None:
        text = (ROOT / "skills/gcp-ops/SKILL.md").read_text(encoding="utf-8")
        commands = re.findall(r"^gcloud (?:run|logging) .+$", text, re.MULTILINE)
        self.assertTrue(commands, "no executable command examples found")
        targets = {"service": "orders", "revision": "orders-00002", "project": "project-a",
                   "region": "us-central1", "previous-revision": "orders-00001"}
        for command in commands:
            concrete = re.sub(r"<([^>]+)>", lambda match: targets[match[1]], command)
            with self.subTest(command=concrete):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "scripts/readonly-guard.py")],
                    input=json.dumps({"agent_type": "save-toolkit:sre-assistant",
                                      "tool_name": "Bash", "tool_input": {"command": concrete}}),
                    text=True, capture_output=True, timeout=30,
                )
                denied = " update-traffic " in concrete
                self.assertEqual(result.returncode, 43 if denied else 42, result.stderr)
                if denied:
                    self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
                else:
                    self.assertEqual(result.stdout, "")

    def test_service_lifecycle_context_requirements_declare_no_authority_paths(self) -> None:
        sidecar_path = ROOT / "skills/service-lifecycle/context-requirements.yaml"
        document = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        spec = document["spec"]

        self.assertEqual(
            spec["forbidden"],
            ["/target/approval", "/target/credential"],
            "an effect-capable consumer must keep approval and credential paths forbidden",
        )
        declared = (
            spec["required"]
            + spec["optional"]
            + [p for alt in spec.get("alternatives", []) for p in alt["anyOf"]]
        )
        self.assertTrue(declared, "the sidecar declares no context paths at all")
        for pointer in declared:
            for banned in ("approval", "approve", "credential", "secret", "token", "auth"):
                with self.subTest(pointer=pointer, banned=banned):
                    self.assertNotIn(banned, pointer.lower())


if __name__ == "__main__":
    unittest.main()
