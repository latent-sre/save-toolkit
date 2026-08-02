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

    def test_current_evidence_rejects_volatile_numeric_pass_counts(self) -> None:
        samples = (
            "Gate A passes 26/26, the validator passes 33 focused tests.",
            "Gate A passes\n27/27 structural steps.",
            "Gate A is 29/29.",
            "The lifecycle suite is 52/52.",
            "The evidence-envelope suite is 10/10.",
            "The ledger suite has 11 passes plus one skipped.",
            "The ledger suite recorded 11 passes.",
            "The focused suite has 11 test passes.",
            "The single-case suite has 1 pass.",
            "pytest reports 18 passed.",
            "33/33 focused tests passed.",
            "all forty-seven scenarios pass.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                (self.root / "docs/fleet-roadmap.md").write_text(
                    "# Fleet roadmap\n\n"
                    "> **Status: live.**\n"
                    "> This is the only document for unfinished work.\n\n"
                    "## Active\n\n"
                    "### LEARN-001 -- stale evidence\n\n"
                    f"**Current evidence:** {sample}\n",
                    encoding="utf-8",
                )
                failures = check_plan_status.check(self.root)
                self.assertTrue(
                    any("volatile numeric pass count" in item for item in failures),
                    failures,
                )

    def _write_roadmap_item(
        self,
        *,
        item_id: str = "HOST-001",
        status: str = "active",
        include_acceptance: bool = True,
        prerequisites: str = "None.",
        reopen_trigger: str | None = None,
    ) -> None:
        acceptance = "\n**Acceptance:** The observable result is recorded.\n" if include_acceptance else "\n"
        reopen = f"\n**Reopen trigger:** {reopen_trigger}\n" if reopen_trigger else ""
        (self.root / "docs/fleet-roadmap.md").write_text(
            "# Fleet roadmap\n\n"
            "> **Status: live.**\n"
            "> This is the only document for unfinished work.\n\n"
            "## Active runtime work\n\n"
            f"### {item_id} -- test item\n\n"
            f"**Status:** `{status}`\n\n"
            "**Outcome:** A measurable result exists.\n\n"
            "**Source:** Test decision.\n\n"
            f"**Prerequisites:** {prerequisites}\n"
            f"{acceptance}"
            "**Next action:** Perform the smallest safe step.\n"
            f"{reopen}",
            encoding="utf-8",
        )

    def test_roadmap_item_contract_passes(self) -> None:
        self._write_roadmap_item()
        self.assertEqual([], check_plan_status.check(self.root))

    def test_roadmap_item_rejects_undocumented_status(self) -> None:
        self._write_roadmap_item(status="parked")
        failures = check_plan_status.check(self.root)
        self.assertTrue(any("unsupported status 'parked'" in item for item in failures), failures)

    def test_roadmap_item_requires_acceptance(self) -> None:
        self._write_roadmap_item(include_acceptance=False)
        failures = check_plan_status.check(self.root)
        self.assertTrue(any("missing field 'Acceptance'" in item for item in failures), failures)

    def test_roadmap_item_ids_are_unique(self) -> None:
        self._write_roadmap_item()
        roadmap = self.root / "docs/fleet-roadmap.md"
        roadmap.write_text(
            roadmap.read_text(encoding="utf-8")
            + "\n### HOST-001 -- duplicate\n\n"
            "**Status:** `ready`\n\n"
            "**Outcome:** Duplicate.\n\n"
            "**Source:** Test.\n\n"
            "**Prerequisites:** None.\n\n"
            "**Acceptance:** Never.\n\n"
            "**Next action:** None.\n",
            encoding="utf-8",
        )
        failures = check_plan_status.check(self.root)
        self.assertTrue(any("duplicate roadmap item ID" in item for item in failures), failures)

    def test_roadmap_item_rejects_unknown_prerequisite_id(self) -> None:
        self._write_roadmap_item(prerequisites="MISSING-999.")
        failures = check_plan_status.check(self.root)
        self.assertTrue(any("unknown prerequisite MISSING-999" in item for item in failures), failures)

    def test_deferred_item_requires_reopen_trigger(self) -> None:
        self._write_roadmap_item(status="deferred")
        failures = check_plan_status.check(self.root)
        self.assertTrue(any("deferred item lacks 'Reopen trigger'" in item for item in failures), failures)


if __name__ == "__main__":
    unittest.main()
