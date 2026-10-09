"""Consumer acceptance against an explicitly selected, real sre-context checkout.

Set SRE_CONTEXT_ROOT to the reviewed producer checkout to run the CLI cases. The
default suite skips external integration; a skip is not compatibility evidence.
Only temporary synthetic catalogs are modified, never the producer checkout.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from testkit import must_replace


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/service-lifecycle"
PRODUCER = os.environ.get("SRE_CONTEXT_ROOT")


class LifecycleContractTests(unittest.TestCase):
    def test_transition_guidance_is_reachable_and_has_each_owner(self) -> None:
        reference = "./references/record-transitions.md"
        self.assertIn(reference, (SKILL / "SKILL.md").read_text(encoding="utf-8"))
        text = (SKILL / reference).read_text(encoding="utf-8")
        for transition in ("Change", "Remediation", "Refresh", "Retirement"):
            row = next(line for line in text.splitlines() if line.startswith(f"| {transition} |"))
            cells = [cell.strip() for cell in row.strip("|").split("|")]
            self.assertEqual(len(cells), 4)
            self.assertTrue(all(cells), transition)

    def test_deployment_freshness_is_bounded_without_becoming_mandatory(self) -> None:
        spec = yaml.safe_load((SKILL / "context-requirements.yaml").read_text(encoding="utf-8"))["spec"]
        self.assertIn("/target/deployment", spec["optional"])
        self.assertEqual(spec["freshness"], [{"path": "/target/deployment", "maxAge": "P30D"}])


@unittest.skipUnless(PRODUCER, "set SRE_CONTEXT_ROOT for external producer CLI acceptance")
class LifecycleProducerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.producer = Path(PRODUCER).resolve()
        self.assertTrue((self.producer / "sre_context/cli.py").is_file())
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)
        self.source = self.workspace / "fixtures"
        shutil.copytree(self.producer / "fixtures", self.source)
        self.requirements = self.workspace / "requirements.yaml"
        shutil.copyfile(SKILL / "context-requirements.yaml", self.requirements)
        self.deployment = self.source / "entities/deployment-alpha-checkout-production.yaml"

    def resolve(self, as_of: str | None = "2026-09-23", *extra: str) -> subprocess.CompletedProcess:
        command = [
            sys.executable, "-B", "-m", "sre_context.cli", "resolve",
            "--source", str(self.source), "--requirements", str(self.requirements),
            "--team", "tenant-alpha", "--service", "checkout-api",
            "--environment", "production", "--allow-fixtures", "--json",
        ]
        if as_of is not None:
            command.extend(["--as-of", as_of])
        command.extend(extra)
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        return subprocess.run(command, cwd=self.producer, env=environment,
                              text=True, capture_output=True, timeout=30)

    def success(self, result: subprocess.CompletedProcess) -> dict:
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        bundle = json.loads(result.stdout)
        self.assertEqual(bundle["source"], {"mode": "fixture", "nonOperational": True})
        self.assertEqual(bundle["target"]["actionSelection"], "prohibited")
        self.assertNotIn("approval", bundle["target"])
        self.assertNotIn("credential", bundle["target"])
        self.assertEqual(bundle["apiVersion"], "sre-context/resolved/v1alpha6")
        for name in ("service", "deployment"):
            if name in bundle["target"]:
                self.assertIn(bundle["target"][name]["lifecycle"], ("active", "deprecated", "retired"))
                self.assertEqual(bundle["target"][name]["ownerRef"], "team:global/tenant-alpha")
        return bundle

    def failure(self, result: subprocess.CompletedProcess, code: int, message: str) -> None:
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertEqual(result.stdout, "", "failure must not leak a usable partial bundle")
        self.assertIn(message, json.loads(result.stderr)["message"])

    def mutate(self, path: Path, old: str, new: str) -> None:
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"producer fixture drift: {path.name}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_exact_consumer_mirror(self) -> None:
        actual = yaml.safe_load(self.requirements.read_text(encoding="utf-8"))
        mirror = yaml.safe_load((self.producer / "examples/service-lifecycle.requirements.yaml").read_text(encoding="utf-8"))
        self.assertEqual(actual, mirror)

    def test_fresh_at_inclusive_30_day_boundary(self) -> None:
        bundle = self.success(self.resolve())
        self.assertEqual(bundle["requirements"]["freshness"], {
            "asOf": "2026-09-23", "checks": [{"path": "/target/deployment",
            "lastVerified": "2026-08-24", "ageDays": 30, "maxAge": "P30D"}],
        })

    def test_stale_at_31_days(self) -> None:
        self.failure(self.resolve("2026-09-24"), 5, "stale context")

    def test_retired_record_is_visible_and_remains_non_operational(self) -> None:
        for name in ("service-alpha-checkout.yaml", self.deployment.name):
            self.mutate(self.source / "entities" / name, "lifecycle: active", "lifecycle: retired")
        bundle = self.success(self.resolve())
        self.assertEqual(bundle["target"]["service"]["lifecycle"], "retired")
        self.assertEqual(bundle["target"]["deployment"]["lifecycle"], "retired")

    def test_explicit_evaluation_date_required(self) -> None:
        self.failure(self.resolve(None), 5, "explicit --as-of")

    def test_missing_verification_date_fails(self) -> None:
        self.mutate(self.deployment, "    lastValidated: 2026-08-24\n", "")
        self.failure(self.resolve(), 5, "no lastVerified evidence")

    def test_future_verification_date_fails(self) -> None:
        self.failure(self.resolve("2026-08-23"), 5, "dated after --as-of")

    def test_refresh_changes_only_locator_freshness(self) -> None:
        self.failure(self.resolve("2026-09-30"), 5, "stale context")
        self.mutate(self.deployment, "lastValidated: 2026-08-24", "lastValidated: 2026-09-30")
        bundle = self.success(self.resolve("2026-09-30"))
        self.assertEqual(bundle["requirements"]["freshness"]["checks"][0]["ageDays"], 0)
        # Catalog validation is not runbook execution evidence or lifecycle acceptance.
        self.assertNotIn("last_verified", json.dumps(bundle))

    def test_absent_optional_deployment_is_a_gap(self) -> None:
        catalog_path = self.source / "catalog.yaml"
        catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        catalog["spec"]["entities"].remove("entities/" + self.deployment.name)
        catalog_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")
        self.deployment.unlink()
        bundle = self.success(self.resolve())
        self.assertNotIn("deployment", bundle["target"])
        self.assertIn("/target/deployment", bundle["requirements"]["optionalMissing"])
        self.assertEqual(bundle["requirements"]["freshness"]["checks"], [])
        self.failure(self.resolve("2026-09-23", "--deployment", "checkout-production"), 4,
                     "no deployment matches")

    def test_forbidden_checks_are_enforced_not_silently_ignored(self) -> None:
        # A present nonsecret sentinel exercises the forbidden mechanism without
        # asking the producer to admit credentials to its closed source schema.
        self.mutate(self.requirements, "/target/approval", "/target/actionSelection")
        self.failure(self.resolve(), 5, "forbidden context is present")

    def test_approval_and_credential_source_fields_are_rejected(self) -> None:
        original = self.deployment.read_text(encoding="utf-8")
        for field in ("approval", "credential"):
            with self.subTest(field=field):
                self.deployment.write_text(
                    must_replace(original, "spec:\n", f"spec:\n  {field}: synthetic-denied\n"), encoding="utf-8")
                result = self.resolve()
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(json.loads(result.stderr)["category"], "invalid-source")


if __name__ == "__main__":
    unittest.main()
