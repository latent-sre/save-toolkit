"""UTF-8, provenance projection, and strict graph serialization contracts."""

import json
import unittest

from fleet_atlas_v2_format import (
    bounded_envelope, bounded_text, fact_line, fact_record, graph_dict, parse_graph,
)
from fleet_atlas_v2_model import Bucket, EvidenceClass, Fact, Node, Predicate, Proof, ProofKind, assemble
from fleet_atlas_v2_proofs import Derivation, verify_facts
from fleet_atlas_v2_sources import Snapshot, Source


class FormatTests(unittest.TestCase):
    def checked(self):
        source = Source("skills/demo/SKILL.md", b"name: demo\nload condition\n")
        proof = Proof(ProofKind.JOINED, (source.span(1, 1), source.span(2, 2)), "demo/v1")
        node = Node("skill:demo", "skill", source.path, "skill:demo")
        fact = Fact("name:demo", node.id, "name", "demo\n# injected heading\u2028unicode separator",
                    EvidenceClass.EXTRACTED, proof)
        predicates = (Predicate("name", frozenset({"skill"}), None, ("skills/*/SKILL.md",)),)
        graph = assemble((Bucket("demo", (node,), (fact,)),), predicates)
        evaluator = lambda f, s, p: Derivation("demo\n# injected heading\u2028unicode separator", EvidenceClass.EXTRACTED, proof)
        return verify_facts(graph, Snapshot("fixture", (source,)), predicates, {"demo/v1": evaluator})

    def test_every_projected_fact_carries_class_label_and_all_citations(self):
        checked = self.checked()
        fact = checked.graph.facts[0]
        record = fact_record(fact, checked)
        self.assertEqual("verified", record["label"])
        self.assertEqual([1, 2], [span["start"] for span in record["citations"]])
        line = fact_line(fact, checked)
        self.assertIn("STATIC_EXTRACTED [verified]", line)
        self.assertIn("SKILL.md:1-1", line)
        self.assertIn("SKILL.md:2-2", line)
        self.assertEqual(1, len(line.splitlines()))

    def test_graph_roundtrip_and_unknown_field_rejection(self):
        graph = self.checked().graph
        record = json.loads(json.dumps(graph_dict(graph)))
        self.assertEqual(graph, parse_graph(record))
        record["facts"][0]["verified"] = True
        with self.assertRaises(ValueError):
            parse_graph(record)

    def test_query_bounded_by_encoded_bytes_with_truncation_record(self):
        records = [{"value": "π" * 1000} for _ in range(100)]
        encoded = bounded_envelope({"outcome": "results"}, records, 4000)
        envelope = json.loads(encoded)
        self.assertLessEqual(len(encoded), 4000)
        self.assertEqual(len(encoded), envelope["encodedBytes"])
        self.assertTrue(envelope["truncated"])
        self.assertEqual(100, envelope["count"] + envelope["omittedResults"])
        self.assertGreater(envelope["count"], 0)

    def test_single_oversized_result_is_explicitly_omitted(self):
        encoded = bounded_envelope({"outcome": "results"}, [{"value": "x" * 20_000}], 4000)
        data = json.loads(encoded)
        self.assertEqual(0, data["count"])
        self.assertEqual(1, data["omittedResults"])
        self.assertTrue(data["truncated"])
        self.assertEqual("results", data["outcome"])

    def test_index_truncation_reports_its_own_budget(self):
        content = bounded_text("# Index", ("π" * 2000 for _ in range(3)), 4000)
        marker = content.decode().split("<!-- ")[-1].removesuffix(" -->\n")
        data = json.loads(marker)
        self.assertEqual(4000, data["budgetBytes"])
        self.assertEqual(len(content), data["encodedBytes"])
        self.assertEqual(3, data["omittedResults"])
        self.assertLessEqual(len(content), 4000)

    def test_verified_empty_is_not_an_omitted_result(self):
        data = json.loads(bounded_envelope({"outcome": "empty"}, []))
        self.assertFalse(data["truncated"])
        self.assertEqual(0, data["omittedResults"])
        self.assertEqual("empty", data["outcome"])


if __name__ == "__main__":
    unittest.main()
