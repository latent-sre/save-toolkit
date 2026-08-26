#!/usr/bin/env python3
"""Focused contracts for roadmap measurement-evidence resolution."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import check_evidence_refs


BATCH = "20260826T120000Z-1234abcd"


class EvidenceReferenceTests(unittest.TestCase):
    def make_root(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "docs" / "reviews").mkdir(parents=True)
        return root

    def test_roadmap_batch_must_resolve_to_review_record(self) -> None:
        root = self.make_root()
        (root / "docs" / "fleet-roadmap.md").write_text(
            f"# Roadmap\n\nBatch `{BATCH}` is load-bearing.\n", encoding="utf-8"
        )

        failures = check_evidence_refs.check(root)

        self.assertEqual(1, len(failures))
        self.assertIn(BATCH, failures[0])

    def test_review_record_resolves_roadmap_batch(self) -> None:
        root = self.make_root()
        (root / "docs" / "fleet-roadmap.md").write_text(
            f"# Roadmap\n\nBatch `{BATCH}` is load-bearing.\n", encoding="utf-8"
        )
        (root / "docs" / "reviews" / "batch.md").write_text(
            f"# Evidence\n\nBatch `{BATCH}`.\n", encoding="utf-8"
        )

        self.assertEqual([], check_evidence_refs.check(root))

    def test_non_batch_numbers_are_ignored(self) -> None:
        root = self.make_root()
        (root / "docs" / "fleet-roadmap.md").write_text(
            "# Roadmap\n\nCommit 12345678 and date 2026-08-26.\n", encoding="utf-8"
        )

        self.assertEqual([], check_evidence_refs.check(root))


if __name__ == "__main__":
    unittest.main()
