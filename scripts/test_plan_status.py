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


class SpecPointerAndDecisionStatusTests(unittest.TestCase):
    """Two promises docs/README.md and rules.md made that the script did not keep."""

    def test_live_tree_passes(self) -> None:
        self.assertEqual([], check_plan_status.check())

    def test_a_spec_without_a_roadmap_pointer_is_flagged(self) -> None:
        """The pointer was enforced in the plans loop only; a spec could omit it and pass green.

        docs/superpowers/specs/2026-07-13-eval-clean-room-design.md really did, until this landed.
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


class WorkflowPolicyTests(unittest.TestCase):
    """The governing surfaces must not reintroduce broad, routine work."""

    @staticmethod
    def _read(relative: str) -> str:
        return (check_plan_status.ROOT / relative).read_text(encoding="utf-8")

    @staticmethod
    def _normalized(text: str) -> str:
        return " ".join(text.split())

    def test_description_changes_use_after_first_routing_evidence(self) -> None:
        agents = self._read("AGENTS.md")
        rules = self._read("docs/rules.md")
        pull_request = self._read(".github/pull_request_template.md")
        roadmap = self._normalized(self._read("docs/fleet-roadmap.md")).lower()

        normalized_agents = self._normalized(agents)
        self.assertIn("run them through the clean-room runner **after** the change", normalized_agents)
        self.assertIn(
            "Run the **before** baseline only for a scenario that comes back red",
            normalized_agents,
        )
        self.assertIn("after-change clean-room runs", rules)
        self.assertNotIn("before and after", pull_request.lower())
        self.assertIn("after-change", pull_request)
        self.assertIn(
            "after-first shortcut does not replace the incumbent baseline",
            normalized_agents.lower(),
        )
        self.assertIn("failure-driven edit still needs the incumbent baseline", rules.lower())
        self.assertIn("fleet-failure-driven edit also trips the next row", pull_request.lower())
        for forbidden in (
            "every description edit shows before/after",
            "scenarios before and after",
            "without before/after routing runs",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, roadmap)

    def test_failure_driven_learning_loop_stays_bounded(self) -> None:
        prompt_agent = self._normalized(self._read("agents/prompt-engineer.md")).lower()
        authoring_skill = self._normalized(self._read("skills/agent-authoring/SKILL.md")).lower()
        artifact = self._normalized(
            self._read("skills/agent-authoring/references/artifact.md")
        ).lower()
        roster = self._normalized(
            self._read("skills/agent-authoring/references/roster.md")
        ).lower()
        agents = self._normalized(self._read("AGENTS.md")).lower()
        evals_readme = self._normalized(self._read("evals/README.md")).lower()

        for text in (prompt_agent, authoring_skill, artifact):
            self.assertNotIn("eval-first, always", text)
            self.assertNotIn("generate→evaluate→refine", text)
            self.assertNotIn("generate → evaluate → refine", text)
        self.assertIn("one candidate by default", prompt_agent)
        self.assertIn("another candidate", prompt_agent)
        self.assertIn("explicit new-behavior target", authoring_skill)
        self.assertIn("ordinary routing-description edit", artifact)
        self.assertIn("pure rewording needs no live eval", authoring_skill)
        self.assertIn("pure rewording needs no live eval", artifact)
        self.assertIn("step 2", authoring_skill)
        self.assertIn("step 2", artifact)
        for text in (prompt_agent, artifact, roster, agents, evals_readme):
            self.assertNotIn("roadmap or issue", text)
            self.assertNotIn("roadmap/issue", text)

    def test_repository_bootstrap_applies_only_to_pr_implementation(self) -> None:
        contributing = self._read("CONTRIBUTING.md")
        rules = self._read("docs/rules.md")
        normalized = self._normalized(contributing)

        self.assertNotIn("Open every working session", normalized)
        self.assertIn("implementation intended for a pull request", normalized)
        self.assertIn("Read-only investigation or review", normalized)
        self.assertIn("preserve dirty and published branches", rules)
        self.assertNotIn("rebase on `origin/main` before PR", rules)

    def test_release_verification_is_owned_by_the_changed_surface(self) -> None:
        agents = self._read("AGENTS.md")
        rules = self._read("docs/rules.md")
        pull_request = self._read(".github/pull_request_template.md")

        old_blanket = (
            "run the release-contract and workflow mutation tests plus the host-probe tests"
        )
        self.assertNotIn(old_blanket, agents)
        for text in (agents, rules, pull_request):
            self.assertIn("metadata-only", text)
            self.assertIn("release_contract.py", text)
            self.assertIn("release_workflow_contract.py", text)
            self.assertIn("host_install_probe.py", text)

    def test_closed_mutation_campaigns_keep_owner_dispositions_in_history(self) -> None:
        roadmap = self._read("docs/fleet-roadmap.md")
        sweep = self._read("docs/reviews/2026-08-15-fleet-mutation-sweep.md")

        self.assertNotIn("### MUTATION-001", roadmap)
        self.assertNotIn("### SWEEP-001", roadmap)
        self.assertIn("explicit owner disposition", roadmap)
        self.assertIn("**Owner disposition (2026-08-21):** `not_applicable`", sweep)
        self.assertIn("owner `latent-sre`", sweep)


if __name__ == "__main__":
    unittest.main()
