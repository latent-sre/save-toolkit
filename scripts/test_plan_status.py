#!/usr/bin/env python3
"""Regression tests for the single-live-roadmap planning contract."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import check_plan_status


class PlanStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs/superpowers/plans").mkdir(parents=True)
        (self.root / "docs/superpowers/specs").mkdir(parents=True)
        (self.root / "docs/fleet-roadmap.md").write_text(
            "# Fleet roadmap\n\n> **Status: live.**\n> This is the only document for "
            "unfinished work.\n",
            encoding="utf-8",
        )
        (self.root / "docs/superpowers/plans/old.md").write_text(
            "# Old plan\n\n> **Status: superseded — historical.** Current work: "
            "[`docs/fleet-roadmap.md`](../../fleet-roadmap.md).\n\n- [ ] stale step\n",
            encoding="utf-8",
        )
        (self.root / "docs/superpowers/specs/old.md").write_text(
            "# Old spec\n\n**Status:** implemented\n",
            encoding="utf-8",
        )
        (self.root / "docs/AUDIT-2026-07-12.md").write_text(
            "# Audit\n\n> **Historical snapshot.**\n",
            encoding="utf-8",
        )
        for name in ("AGENTS.md", "README.md", "CONTRIBUTING.md"):
            (self.root / name).write_text(
                "See docs/fleet-roadmap.md for live work.\n", encoding="utf-8"
            )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_valid_archive_and_live_roadmap_pass(self) -> None:
        self.assertEqual([], check_plan_status.check(self.root))

    def test_unlabeled_unchecked_plan_fails(self) -> None:
        (self.root / "docs/superpowers/plans/old.md").write_text(
            "# Looks active\n\n- [ ] execute me\n", encoding="utf-8"
        )
        failures = check_plan_status.check(self.root)
        self.assertTrue(any("lacks a top-of-file Status" in item for item in failures))

    def test_preimplementation_spec_fails(self) -> None:
        (self.root / "docs/superpowers/specs/old.md").write_text(
            "# Old spec\n\n**Status:** approved design, pre-implementation\n",
            encoding="utf-8",
        )
        failures = check_plan_status.check(self.root)
        self.assertTrue(any("specification status must mark it" in item for item in failures))

    def test_other_active_spec_statuses_fail(self) -> None:
        for status in ("approved", "draft", "ready"):
            with self.subTest(status=status):
                (self.root / "docs/superpowers/specs/old.md").write_text(
                    f"# Old spec\n\n**Status:** {status}\n", encoding="utf-8"
                )
                failures = check_plan_status.check(self.root)
                self.assertTrue(any("specification status must mark it" in item for item in failures))

    def test_marker_substrings_outside_the_status_value_do_not_pass(self) -> None:
        (self.root / "docs/superpowers/plans/old.md").write_text(
            "# Old plan\n\n> **Status: not implemented.** See docs/fleet-roadmap.md.\n",
            encoding="utf-8",
        )
        (self.root / "docs/superpowers/specs/old.md").write_text(
            "# Old spec\n\n**Status:** draft\n\nThis mentions historical work.\n",
            encoding="utf-8",
        )
        failures = check_plan_status.check(self.root)
        self.assertTrue(any("plan status must mark it" in item for item in failures))
        self.assertTrue(any("specification status must mark it" in item for item in failures))

    def test_root_pointer_and_audit_banner_are_required(self) -> None:
        (self.root / "README.md").write_text("# No backlog pointer\n", encoding="utf-8")
        (self.root / "docs/AUDIT-2026-07-12.md").write_text(
            "# Audit\n\nAll findings OPEN.\n", encoding="utf-8"
        )
        failures = check_plan_status.check(self.root)
        self.assertTrue(any(item.startswith("README.md:") for item in failures))
        self.assertTrue(any("Historical snapshot" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
