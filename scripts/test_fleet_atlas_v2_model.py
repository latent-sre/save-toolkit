"""Regressions for the GRAPH-006 selector and deterministic assembly boundary."""

import unittest
from dataclasses import FrozenInstanceError, replace
from itertools import permutations

from fleet_atlas_v2_model import (
    WHOLE_DOCUMENT,
    AmbiguousReference,
    Bucket,
    EvidenceClass,
    Fact,
    FactRef,
    Graph,
    Node,
    NodeIndex,
    NodeRef,
    Predicate,
    Proof,
    ProofKind,
    Span,
    UnresolvedReference,
    assemble,
    assert_debt_subset,
    digest,
)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.span = Span.from_bytes("docs/fleet-roadmap.md", b"# Roadmap\nItem A\n", 2, 2)
        self.proof = Proof(ProofKind.EXTRACTED, (self.span,), "roadmap/v1")
        self.a = Node("item:A", "roadmap-item", "docs/fleet-roadmap.md", "A")
        self.b = Node("item:B", "roadmap-item", "docs/fleet-roadmap.md", "B")
        self.rule = Predicate("depends_on", frozenset({"roadmap-item"}),
                              frozenset({"roadmap-item"}), ("docs/fleet-roadmap.md",))
        self.fact = Fact("edge:A:B", self.a.id, "depends_on", self.b.id,
                         EvidenceClass.EXTRACTED, self.proof)

    def build(self, fact=None, nodes=None, rule=None):
        return assemble((Bucket("roadmap", nodes or (self.a, self.b),
                                (fact or self.fact,)),), (rule or self.rule,))

    def test_evidence_link_resolves_by_selector_not_path(self):
        decision = Node("decision:d", "decision", "docs/decisions/d.md", "decision:d")
        document = Node("document:d", "document", "docs/decisions/d.md", WHOLE_DOCUMENT)
        index = NodeIndex((self.a, self.b, decision, document))
        self.assertEqual(self.b, index.resolve(NodeRef(self.b.path, "roadmap-item", "B")))
        self.assertEqual(decision, index.resolve(NodeRef(decision.path, "decision", decision.id)))
        self.assertEqual(document, index.resolve(NodeRef(document.path, None, WHOLE_DOCUMENT)))
        with self.assertRaises(UnresolvedReference):
            index.resolve(NodeRef(self.a.path, "roadmap-item", WHOLE_DOCUMENT))

    def test_ambiguous_selector_names_candidates_without_picking_first(self):
        other = replace(self.b, selector="A")
        with self.assertRaisesRegex(AmbiguousReference, "item:A, item:B"):
            NodeIndex((other, self.a)).resolve(NodeRef(self.a.path, "roadmap-item", "A"))

    def test_shuffled_extractor_registration_is_identical(self):
        buckets = (Bucket("a", (self.a,), ()), Bucket("b", (self.b,), ()),
                   Bucket("relations", (), (self.fact,)))
        expected = assemble(buckets, (self.rule,))
        for order in permutations(buckets):
            self.assertEqual(expected, assemble(order, (self.rule,)))

    def test_conflicting_nodes_and_facts_are_errors(self):
        original = Bucket("original", (self.a, self.b), (self.fact,))
        for conflict in (Bucket("new", (replace(self.a, type="document"),), ()),
                         Bucket("new", (), (replace(self.fact, object=self.a.id),))):
            with self.assertRaisesRegex(ValueError, "conflicting"):
                assemble((original, conflict), (self.rule,))

    def test_no_dangling_edges(self):
        for fact in (replace(self.fact, subject="item:missing"),
                     replace(self.fact, object="item:missing")):
            with self.assertRaisesRegex(ValueError, "dangling"):
                self.build(fact=fact)

    def test_predicate_types_and_cardinality_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "source type"):
            self.build(nodes=(replace(self.a, type="document"), self.b))
        with self.assertRaisesRegex(ValueError, "target type"):
            self.build(nodes=(self.a, replace(self.b, type="document")))
        with self.assertRaisesRegex(ValueError, "cardinality"):
            assemble((Bucket("x", (self.a, self.b),
                             (self.fact, replace(self.fact, id="edge:A:A", object=self.a.id))),),
                     (replace(self.rule, max_per_subject=1),))

    def test_span_binds_full_blob_and_exact_excerpt(self):
        self.span.verify(b"# Roadmap\nItem A\n")
        for blob in (b"# Different\nItem A\n", b"# Roadmap\nItem B\n"):
            with self.assertRaisesRegex(ValueError, "differs"):
                self.span.verify(blob)
        with self.assertRaises(ValueError):
            Span.from_bytes("docs/fleet-roadmap.md", b"one line", 2, 2)

    def test_projection_identifiers_reject_line_separators_without_rejecting_unicode(self):
        for separator in ("\n", "\r", "\x1b", "\x7f", "\x85", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)):
                with self.assertRaises(ValueError):
                    Span.from_bytes("docs/guide" + separator + "forged.md", b"fact\n", 1, 1)
                with self.assertRaises(ValueError):
                    replace(self.a, id="item:" + separator + "forged")
                with self.assertRaises(ValueError):
                    replace(self.fact, predicate="depends_on" + separator + "forged")
        accepted = Span.from_bytes("docs/操作 guide.md", b"fact\n", 1, 1)
        self.assertEqual("docs/操作 guide.md", accepted.path)

    def test_model_is_immutable_and_rejects_mutable_fact_values(self):
        with self.assertRaises(FrozenInstanceError):
            self.fact.object = "other"
        with self.assertRaises(TypeError):
            replace(self.fact, object=["mutable"])
        with self.assertRaises(ValueError):
            replace(self.fact, object=float("nan"))

    def test_no_provenance_promotion_for_inference_or_debt(self):
        for kind in (ProofKind.INFERRED, ProofKind.DEBT):
            with self.assertRaisesRegex(ValueError, "promoted"):
                replace(self.fact, proof=replace(self.proof, kind=kind))

    def test_absence_requires_closed_world_scope(self):
        with self.assertRaisesRegex(ValueError, "scope digest"):
            replace(self.proof, kind=ProofKind.ABSENCE)
        absence = replace(self.proof, kind=ProofKind.ABSENCE, scope_digest=digest(b"corpus"))
        self.assertEqual(ProofKind.ABSENCE, absence.kind)

    def test_missing_and_cyclic_proof_premises_are_rejected(self):
        for ref, message in (("missing", "missing proof premise"), (self.fact.id, "cyclic proof")):
            with self.assertRaisesRegex(ValueError, message):
                self.build(fact=replace(self.fact, proof=replace(self.proof, inputs=(FactRef(ref),))))

    def test_debt_key_replacement_cannot_hide_behind_constant_count(self):
        debt = replace(self.fact, evidence_class=EvidenceClass.UNKNOWN,
                       proof=replace(self.proof, kind=ProofKind.DEBT))
        graph = self.build(fact=debt)
        assert_debt_subset(graph, frozenset({debt.id}))
        with self.assertRaisesRegex(ValueError, "new evidence debt"):
            assert_debt_subset(graph, frozenset({"old-id"}))
        with self.assertRaisesRegex(ValueError, "zero evidence debt"):
            assert_debt_subset(graph, frozenset({debt.id}), cutover=True)
        assert_debt_subset(Graph((), ()), frozenset({debt.id}), cutover=True)


if __name__ == "__main__":
    unittest.main()
