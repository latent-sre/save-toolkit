#!/usr/bin/env python3
"""Regression tests for the single-live-roadmap planning contract."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import check_plan_status


def _skeleton(root: Path) -> Path:
    """A minimal tree that check() accepts, so a new test asserts only its own subject."""
    (root / "docs/superpowers/plans").mkdir(parents=True)
    (root / "docs/superpowers/specs").mkdir(parents=True)
    (root / check_plan_status.DECISION_ROOT).mkdir(parents=True)
    (root / "docs/fleet-roadmap.md").write_text(
        "# Fleet roadmap\n\n> **Status: live.**\n> The only document for unfinished work.\n",
        encoding="utf-8",
    )
    for name in ("AGENTS.md", "README.md", "CONTRIBUTING.md"):
        (root / name).write_text("See docs/fleet-roadmap.md for live work.\n", encoding="utf-8")
    return root


class PlanStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs/superpowers/plans").mkdir(parents=True)
        (self.root / "docs/superpowers/specs").mkdir(parents=True)
        (self.root / check_plan_status.DECISION_ROOT).mkdir(parents=True)
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
            "# Old spec\n\n**Status:** implemented — historical; live work is in "
            "[`docs/fleet-roadmap.md`](../../fleet-roadmap.md).\n",
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

    def test_root_pointer_is_required(self) -> None:
        (self.root / "README.md").write_text("# No backlog pointer\n", encoding="utf-8")
        failures = check_plan_status.check(self.root)
        self.assertTrue(any(item.startswith("README.md:") for item in failures))

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
            "pytest reports 1,364 passed.",
            "33/33 focused tests passed.",
            "all 1,364 tests pass.",
            "all forty-seven scenarios pass.",
            "The candidate passes 1,364/1,364 grader checks.",
            "passes Gate A 8/8, and passes all 38 component suites.",
            "Gate A 8/8",
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


class SpecPointerAndDecisionStatusTests(unittest.TestCase):
    """Two promises docs/README.md and rules.md made that the script did not keep."""

    def test_live_tree_passes(self) -> None:
        self.assertEqual([], check_plan_status.check())

    def test_absent_round_directories_are_an_empty_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _skeleton(Path(temporary))
            (root / check_plan_status.PLAN_ROOT).rmdir()
            (root / check_plan_status.SPEC_ROOT).rmdir()
            self.assertEqual([], check_plan_status.check(root))

    def test_round_archive_paths_must_be_directories_when_present(self) -> None:
        for archive in (check_plan_status.PLAN_ROOT, check_plan_status.SPEC_ROOT):
            with self.subTest(archive=archive), tempfile.TemporaryDirectory() as temporary:
                root = _skeleton(Path(temporary))
                archive_path = root / archive
                archive_path.rmdir()
                archive_path.write_text("not a directory\n", encoding="utf-8")
                failures = check_plan_status.check(root)
                self.assertTrue(
                    any(
                        failure.startswith(f"{archive.as_posix()}:")
                        and "must be a directory" in failure
                        for failure in failures
                    ),
                    failures,
                )

    def test_a_spec_without_a_roadmap_pointer_is_flagged(self) -> None:
        """The pointer was enforced in the plans loop only; a spec could omit it and pass green.

        A spec in this repository really did, until this landed.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = _skeleton(Path(temporary))
            (root / check_plan_status.SPEC_ROOT / "x-design.md").write_text(
                "# X\n\n**Status:** implemented (PR #1)\n\nbody\n", encoding="utf-8"
            )
            failures = check_plan_status.check(root)
        self.assertTrue(
            any("must point to docs/fleet-roadmap.md" in f and "x-design" in f for f in failures),
            failures,
        )

    def test_a_decision_without_a_status_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = _skeleton(Path(temporary))
            (root / check_plan_status.DECISION_ROOT / "2026-01-01-thing.md").write_text(
                "# Thing\n\nWe will do the thing.\n", encoding="utf-8"
            )
            failures = check_plan_status.check(root)
        self.assertTrue(any("decision lacks a top-of-file Status" in f for f in failures), failures)

    def test_a_qualified_acceptance_is_accepted(self) -> None:
        """Real ADRs qualify the state in the same breath; matching must be by prefix.

        "accepted by the ROUTE-001 owner" and "Accepted for repository implementation" both declare
        acceptance, and an equality test would reject them for saying more rather than less.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = _skeleton(Path(temporary))
            (root / check_plan_status.DECISION_ROOT / "2026-01-01-thing.md").write_text(
                "# Thing\n\n- **Status:** accepted by the ROUTE-001 owner; canary is NO-GO\n",
                encoding="utf-8",
            )
            failures = check_plan_status.check(root)
        self.assertEqual([], [f for f in failures if "2026-01-01-thing" in f], failures)

    def test_a_list_marker_does_not_hide_the_status_field(self) -> None:
        # The ADRs write `- **Status:** accepted`; an anchored match without list-marker tolerance
        # reports a file that has a perfectly good status as having none.
        self.assertEqual(
            "accepted", check_plan_status._status_value("# T\n\n- **Status:** accepted\n")
        )


class RoadmapDispositionTests(unittest.TestCase):
    """A closed campaign is recorded in the tracker, not left implied by a dated review."""

    @staticmethod
    def _read(relative: str) -> str:
        return (check_plan_status.ROOT / relative).read_text(encoding="utf-8")

    def test_closed_mutation_campaigns_keep_owner_dispositions_in_history(self) -> None:
        """A campaign leaves the live roadmap only with its owner disposition recorded.

        The disposition used to be asserted against the dated sweep review's prose, which made a
        historical record load-bearing for this suite: it could not be swept, and could not even be
        reworded, without a red test. Dispositions belong in the tracker, so that is what this
        reads; the review is free to be history.

        The tracker is now two files -- the live roadmap owns what is still owed, and
        ``docs/roadmap-closed.md`` owns the disposition of everything that has left it. Both halves
        are asserted here: the closed campaign must be absent from the live queue AND present with
        its owner disposition in the register. A register is not a dated review; sweeping it would
        still turn this red.
        """
        roadmap = self._read("docs/fleet-roadmap.md")
        closed = self._read("docs/roadmap-closed.md")

        self.assertNotIn("### MUTATION-001", roadmap)
        self.assertNotIn("### SWEEP-001", roadmap)
        self.assertIn("explicit owner disposition", closed)
        self.assertIn("`not_applicable` as live work, owner Save Toolkit maintainers", closed)
        self.assertIn("`SWEEP-001` and `MUTATION-001`", closed)

    def test_closed_graph_003_is_not_presented_as_remaining_work(self) -> None:
        """Post-closure evidence strengthens the record without reopening the live queue."""
        roadmap = self._read("docs/fleet-roadmap.md")
        closed = self._read("docs/roadmap-closed.md")
        guidance = self._read("graph-sandbox/AGENTS.md")

        self.assertNotIn("### GRAPH-003", roadmap)
        self.assertIn("`GRAPH-003`", closed)
        self.assertIn("PR [#197]", closed)
        self.assertIn("does not reopen this disposition", closed)
        self.assertNotIn("Remaining operator work is `GRAPH-003`", guidance)
        self.assertIn("GRAPH-002 and GRAPH-003 are closed", guidance)


if __name__ == "__main__":
    unittest.main()
