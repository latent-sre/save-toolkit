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
