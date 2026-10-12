"""Row fixtures replay current source independently without quadratic JSON decoding."""

import json
import unittest
from unittest import mock

from atlas_test_support import fact_rows, row_extraction
from fleet_atlas_v2_artifacts import checked_facts
from fleet_atlas_v2_sources import Snapshot, Source


class RowFixtureTests(unittest.TestCase):
    def snapshot(self, rows):
        return Snapshot("fixture", (Source("README.md", fact_rows(rows)),))

    def test_replay_decoding_scales_with_rows_not_pairs_of_rows(self):
        rows = [(f"row:{i}", "document:README.md", "state", f"value:{i}") for i in range(32)]
        snapshot = self.snapshot(rows)
        with mock.patch("atlas_test_support.json.loads", wraps=json.loads) as decode:
            checked = checked_facts(snapshot, lambda current: row_extraction(current, "README.md"))
        self.assertEqual({row[0]: row[3] for row in rows},
                         {fact.id: fact.object for fact in checked.graph.facts})
        self.assertLessEqual(decode.call_count, 2 * len(rows), "decode extraction and replay once each")

    def test_replay_uses_current_source_values_positions_and_qualifiers(self):
        rows = [("a", "document:README.md", "state", "old"),
                ("b", "document:README.md", "state", "other")]
        original = self.snapshot(rows)
        extraction = row_extraction(original, "README.md")
        fact = extraction.buckets[0].facts[0]
        replay = extraction.evaluators[fact.proof.evaluator]
        self.assertEqual("old", replay(fact, original, {}).value)
        changed = self.snapshot([rows[1], ("a", "document:README.md", "state", "new", {"key": "value"})])
        result = replay(fact, changed, {})
        self.assertEqual("new", result.value)
        self.assertEqual((("key", "value"),), result.qualifiers)
        self.assertEqual((changed.source("README.md").span(2, 2),), result.proof.inputs)
        self.assertEqual("old", replay(fact, original, {}).value)


if __name__ == "__main__":
    unittest.main()
