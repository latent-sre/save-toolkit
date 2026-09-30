"""Compatibility exports preserve additions and refuse missing core semantics."""

from dataclasses import replace
import unittest

from fleet_atlas_v2_compat import compatibility_snapshot
from fleet_atlas_v2_model import Bucket, EvidenceClass, Fact, Node, Predicate, Proof, ProofKind, assemble
from fleet_atlas_v2_proofs import Derivation, verify_facts
from fleet_atlas_v2_sources import Snapshot, Source


class CompatibilityExportTests(unittest.TestCase):
    def checked(self, omit_name=False):
        source = Source("skills/demo/SKILL.md", b"Demo source\n")
        node = Node("skill:demo", "skill", source.path, "WHOLE_DOCUMENT")
        proof = Proof(ProofKind.EXTRACTED, (source.span(1, 1),), "fixture/v1")
        values = {"name": "demo", "authority": "canonical", "state": "live",
                  "attr.tools": ("Read", "Grep"), "guidance": "dependency timeouts"}
        if omit_name:
            values.pop("name")
        facts = tuple(Fact("fact:" + key, node.id, key, value, EvidenceClass.EXTRACTED, proof)
                      for key, value in values.items())
        rules = tuple(Predicate(key, frozenset({"skill"}), None, (source.path,)) for key in values)
        graph = assemble((Bucket("fixture", (node,), facts),), rules)

        def evaluator(fact, snapshot, premises):
            return Derivation(values[fact.predicate], EvidenceClass.EXTRACTED, proof)

        return verify_facts(graph, Snapshot("fixture", (source,)), rules, {"fixture/v1": evaluator})

    def test_no_supplemental_fact_is_discarded(self):
        snapshot = compatibility_snapshot(self.checked())
        self.assertEqual(["Read", "Grep"], snapshot["nodes"][0]["attrs"]["tools"])
        self.assertEqual("guidance", snapshot["v2SupplementalFacts"][0]["predicate"])
        self.assertEqual("WHOLE_DOCUMENT", snapshot["v2Selectors"]["skill:demo"])
        self.assertEqual(5, len(snapshot["v2Proofs"]))

    def test_missing_core_fact_is_error_not_invented_default(self):
        with self.assertRaisesRegex(ValueError, "missing explicit"):
            compatibility_snapshot(self.checked(omit_name=True))


if __name__ == "__main__":
    unittest.main()
