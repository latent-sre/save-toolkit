"""Offline preparation checks for a fresh PRINCIPAL-001 case; no model calls or design grading."""

import json
import unittest
from pathlib import Path
from typing import Any

from probe import catalog

ROOT = Path(__file__).resolve().parent
CASE = "live-store-cutover"
DOCUMENT = "docs/design/live-store-cutover.md"


def load_pair() -> list[dict[str, Any]]:
    return [
        catalog.load_scenario(ROOT / f"build-scenarios/build-{agent}-{CASE}.yaml")
        for agent in ("principal-engineer", "software-engineer")
    ]


class PrincipalHeldoutTests(unittest.TestCase):
    def test_pair_differs_only_by_id_and_agent(self) -> None:
        principal, builder = load_pair()
        self.assertEqual("principal-engineer", principal["agent"])
        self.assertEqual("software-engineer", builder["agent"])
        self.assertEqual(
            {key: value for key, value in principal.items() if key not in {"id", "agent"}},
            {key: value for key, value in builder.items() if key not in {"id", "agent"}},
        )
        self.assertNotIn("tools", principal, "retain the native lanes' actual tool postures")
        self.assertNotIn("references", principal, "do not pre-load the design answer or guidance")

    def test_checks_measure_artifacts_boundaries_and_method_not_semantic_keywords(self) -> None:
        for spec in load_pair():
            with self.subTest(agent=spec["agent"]):
                checks = spec["checks"]
                self.assertEqual(
                    {
                        "glob_exists",
                        "changes_within",
                        "no_new_commits",
                        "no_task_dispatch",
                        "bash_did_not_run",
                        "skill_loaded",
                    },
                    {check["check"] for check in checks},
                )
                self.assertEqual(8, len(checks))
                allowed = next(check["allowed"] for check in checks if check["check"] == "changes_within")
                self.assertEqual([DOCUMENT], allowed)
                skills = [check for check in checks if check["check"] == "skill_loaded"]
                self.assertEqual(
                    {"eng-ladder", "stack-profile", "database-reliability"}, {check["skill"] for check in skills}
                )
                self.assertTrue(all(check["before_effects"] for check in skills))
                self.assertFalse(any(check["check"] == "fleet_grader" for check in checks))

    def test_fixture_exposes_a_real_pause_constraint_and_all_writer_classes(self) -> None:
        files = load_pair()[0]["fixture"]["files"]
        limits = json.loads(files["contracts/store.json"])
        rehearsal = json.loads(files["measurements/rehearsal.json"])
        self.assertEqual(60, limits["max_write_pause_seconds"])
        self.assertGreater(rehearsal["copy_seconds"], limits["max_write_pause_seconds"])
        self.assertFalse(limits["current_change_journal"])
        self.assertFalse(limits["cross_database_transaction"])
        writers = files["inventory/writers.csv"].strip().splitlines()
        self.assertEqual("writer,owner,write_path,operations", writers[0])
        self.assertEqual(4, len(writers))
        self.assertIn("cleanup-task,platform-team,direct-sql,hard-delete", writers)
        self.assertIn("operator-cli,oncall-team,direct-sql,insert|update", writers)

    def test_equal_counts_hide_missing_new_rows_resurrection_and_stale_overwrite(self) -> None:
        rehearsal = json.loads(load_pair()[0]["fixture"]["files"]["measurements/rehearsal.json"])
        source = {row["rule_id"]: row for row in rehearsal["source_at_cutover"]}
        target = {row["rule_id"]: row for row in rehearsal["target_after_copy"]}
        self.assertEqual(len(source), len(target))
        self.assertNotEqual(source, target)
        self.assertEqual({"r22"}, source.keys() - target.keys())
        self.assertEqual({"r18"}, target.keys() - source.keys())
        self.assertEqual((8, 7), (source["r17"]["version"], target["r17"]["version"]))
        accepted = rehearsal["target_write_after_cutover"]
        self.assertEqual("r17", accepted["rule_id"])
        self.assertGreater(accepted["version"], source["r17"]["version"])
        self.assertNotEqual(accepted["value"], source["r17"]["value"])


if __name__ == "__main__":
    unittest.main()
