"""Isolation and integrity tests for Codex resolved-context bundles."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import resolved_context


class ResolvedContextBundleTests(unittest.TestCase):
    def _candidate(self, *, reference: str = "# First response\n\nq_first_1234\n") -> Path:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "agents").mkdir()
        (root / "skills/incident-investigation/references").mkdir(parents=True)
        (root / "agents/sre.md").write_text(
            "---\nname: sre\ndescription: triage\ntools: Read, Grep, Glob, Skill\n---\n"
            "Load `incident-investigation`.\n",
            encoding="utf-8",
        )
        (root / "skills/incident-investigation/SKILL.md").write_text(
            "---\nname: incident-investigation\ndescription: choose mode\n---\n"
            "Read [first response](./references/first-response.md).\n",
            encoding="utf-8",
        )
        (root / "skills/incident-investigation/references/first-response.md").write_text(
            reference,
            encoding="utf-8",
        )
        (root / "outside.txt").write_text("must not be copied", encoding="utf-8")
        return root

    def _scenario(self) -> dict[str, object]:
        return {
            "id": "agent-direct-sre-first-response",
            "target": {"kind": "agent", "name": "sre"},
            "prompt": "Triage the new alert.",
        }

    def test_bundle_contains_only_resolved_context_and_no_graders(self) -> None:
        root = self._candidate()
        with resolved_context.resolved_bundle(
            candidate_root=root,
            scenario=self._scenario(),
            candidate_sha="a" * 40,
            required_references=(
                "skills/incident-investigation/references/first-response.md",
            ),
        ) as bundle:
            relative = {path.relative_to(bundle.root).as_posix() for path in bundle.root.rglob("*") if path.is_file()}
            self.assertEqual(
                {
                    "AGENTS.md",
                    "agents/sre.md",
                    "context-manifest.json",
                    "prompt.txt",
                    "response-schema.json",
                    "skills/incident-investigation/SKILL.md",
                    "skills/incident-investigation/references/first-response.md",
                },
                relative,
            )
            self.assertFalse((bundle.root / "outside.txt").exists())
            rendered = "\n".join(
                path.read_text(encoding="utf-8")
                for path in bundle.root.rglob("*")
                if path.is_file()
            )
            self.assertNotIn("success_criteria", rendered)
            self.assertNotIn("graders", rendered)
            self.assertEqual(
                {"skills/incident-investigation/references/first-response.md": "q_first_1234"},
                bundle.canaries,
            )
            self.assertRegex(bundle.tree_sha256, r"^[0-9a-f]{64}$")
            self.assertRegex(bundle.policy_sha256, r"^[0-9a-f]{64}$")
            manifest = json.loads((bundle.root / "context-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("a" * 40, manifest["candidate_sha"])
            self.assertNotIn("tree_sha256", manifest)
            self.assertNotIn("q_first_1234", json.dumps(manifest))
            self.assertEqual(
                ["skills/incident-investigation/references/first-response.md"],
                manifest["required_references"],
            )

    def test_traversal_link_is_rejected_before_copy(self) -> None:
        root = self._candidate()
        (root / "skills/incident-investigation/SKILL.md").write_text(
            "[escape](../../outside.txt)\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(resolved_context.BundleError, "escapes|traversal"):
            with resolved_context.resolved_bundle(
                candidate_root=root,
                scenario=self._scenario(),
                candidate_sha="a" * 40,
            ):
                pass

    def test_absolute_link_is_rejected_before_copy(self) -> None:
        root = self._candidate()
        (root / "skills/incident-investigation/SKILL.md").write_text(
            "[escape](/etc/passwd)\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(resolved_context.BundleError, "absolute"):
            with resolved_context.resolved_bundle(
                candidate_root=root,
                scenario=self._scenario(),
                candidate_sha="a" * 40,
            ):
                pass

    @unittest.skipUnless(hasattr(os, "symlink"), "platform cannot create symlinks")
    def test_source_symlink_is_rejected(self) -> None:
        root = self._candidate()
        reference = root / "skills/incident-investigation/references/first-response.md"
        reference.unlink()
        try:
            reference.symlink_to(root / "outside.txt")
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is not permitted here")
        with self.assertRaisesRegex(resolved_context.BundleError, "link or reparse"):
            with resolved_context.resolved_bundle(
                candidate_root=root,
                scenario=self._scenario(),
                candidate_sha="a" * 40,
            ):
                pass

    def test_required_reference_without_canary_is_rejected(self) -> None:
        root = self._candidate(reference="# First response\n\nNo marker.\n")
        with self.assertRaisesRegex(resolved_context.BundleError, "canary"):
            with resolved_context.resolved_bundle(
                candidate_root=root,
                scenario=self._scenario(),
                candidate_sha="a" * 40,
                required_references=(
                    "skills/incident-investigation/references/first-response.md",
                ),
            ):
                pass

    def test_unknown_required_reference_is_rejected(self) -> None:
        root = self._candidate()
        with self.assertRaisesRegex(resolved_context.BundleError, "required reference"):
            with resolved_context.resolved_bundle(
                candidate_root=root,
                scenario=self._scenario(),
                candidate_sha="a" * 40,
                required_references=("skills/other/references/not-there.md",),
            ):
                pass


if __name__ == "__main__":
    unittest.main()
