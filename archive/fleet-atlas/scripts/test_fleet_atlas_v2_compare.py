"""The compatibility gate detects lost facts and narrowly binds declared corrections."""
import copy
import tempfile
import unittest
from pathlib import Path

from fleet_atlas_v2_compare import compare, differences, read_json


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.base = {"metadata": {"revision": "r1", "dirty": False},
                     "nodes": [{"id": "skill:x", "attrs": {"bytes": 40},
                                "evidence": [{"path": "skills/x/SKILL.md", "lines": [2, 3]}]}],
                     "edges": [], "unknowns": [], "query": {"empty": {"outcome": "EMPTY"}}}

    def test_identical_observables_pass(self):
        self.assertEqual("MATCH", compare(self.base, copy.deepcopy(self.base), [])["outcome"])

    def test_preserves_all_fact_proof_provenance_and_query_fields(self):
        changes = [lambda a: a["nodes"][0]["attrs"].clear(),
                   lambda a: a["nodes"][0].update(evidence=[]),
                   lambda a: a["metadata"].update(revision="r2"),
                   lambda a: a["query"]["empty"].update(outcome="INVALID"),
                   lambda a: a.update(unknowns=[{"code": "missing-owner"}]),
                   lambda a: a["edges"].append({"id": "edge:1", "kind": "owns"})]
        for change in changes:
            with self.subTest(change=change):
                changed = copy.deepcopy(self.base)
                change(changed)
                self.assertEqual("DIFFERENT", compare(self.base, changed, [])["outcome"])

    def test_named_correction_must_bind_exact_path_and_both_values(self):
        after = copy.deepcopy(self.base)
        after["nodes"][0]["attrs"]["bytes"] = 39
        delta = {"name": "normalized-LF-size", "path": "/nodes/skill:x/attrs/bytes",
                 "before": {"present": True, "value": 40},
                 "after": {"present": True, "value": 39}}
        self.assertEqual("MATCH", compare(self.base, after, [delta])["outcome"])
        for replacement in (38, True, None):
            after["nodes"][0]["attrs"]["bytes"] = replacement
            self.assertEqual("DIFFERENT", compare(self.base, after, [delta])["outcome"])
        self.assertEqual("DIFFERENT", compare(self.base, self.base, [delta])["outcome"])

    def test_entity_order_does_not_hide_duplicate_identity(self):
        after = copy.deepcopy(self.base)
        after["nodes"].append({"id": "skill:y"})
        reversed_nodes = copy.deepcopy(after)
        reversed_nodes["nodes"].reverse()
        self.assertEqual("MATCH", compare(after, reversed_nodes, [])["outcome"])
        after["nodes"].append({"id": "skill:x"})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compare(self.base, after, [])

    def test_absence_null_boolean_and_numeric_values_remain_distinct(self):
        self.assertTrue(differences({}, {"x": None}))
        self.assertTrue(differences({"x": True}, {"x": 1}))
        self.assertEqual("/a~1b/~0", differences({"a/b": {"~": 1}}, {"a/b": {"~": 2}})[0]["path"])

    def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "snapshot.json"
            for text in ('{"nodes": [], "nodes": []}', '{"value": NaN}'):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_json(path)


if __name__ == "__main__":
    unittest.main()
