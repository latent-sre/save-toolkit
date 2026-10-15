"""Adversarial proof replay tests: containment is not claim support."""

import unittest
from dataclasses import replace

from fleet_atlas_v2_model import (
    Bucket,
    EvidenceClass,
    Fact,
    FactRef,
    Node,
    Predicate,
    Proof,
    ProofKind,
    assemble,
)
from fleet_atlas_v2_proofs import Derivation, VerifiedFacts, verify_facts
from fleet_atlas_v2_sources import Snapshot, Source


class ProofTests(unittest.TestCase):
    def setUp(self):
        self.source = Source("agents/example.md", b"---\nname: example\n---\n")
        self.snapshot = Snapshot("fixture", (self.source,))
        self.node = Node("agent:example", "agent", self.source.path, "agent:example")
        self.predicate = Predicate("name", frozenset({"agent"}), None, ("agents/*.md",), 1)
        self.proof = Proof(ProofKind.EXTRACTED, (self.source.span(2, 2),), "agent-name/v1")
        self.fact = Fact("name:example", self.node.id, "name", "example",
                         EvidenceClass.EXTRACTED, self.proof)

        def name_evaluator(fact, snapshot, premises):
            source = snapshot.source("agents/example.md")
            name_line = next(i for i, line in enumerate(source.lines, 1) if line.startswith("name: "))
            value = source.lines[name_line - 1].removeprefix("name: ")
            proof = Proof(ProofKind.EXTRACTED, (source.span(name_line, name_line),), "agent-name/v1")
            return Derivation(value, EvidenceClass.EXTRACTED, proof)

        self.evaluators = {"agent-name/v1": name_evaluator}

    def verify(self, fact=None, snapshot=None):
        graph = assemble((Bucket("test", (self.node,), (fact or self.fact,)),), (self.predicate,))
        return verify_facts(graph, snapshot or self.snapshot, (self.predicate,), self.evaluators)

    def test_valid_claim_crosses_boundary_but_constructor_requires_seal(self):
        checked = self.verify()
        self.assertEqual(self.fact, checked.graph.facts[0])
        with self.assertRaisesRegex(ValueError, "only be constructed"):
            VerifiedFacts(checked.graph, checked.snapshot, object())

    def test_changed_claim_fields_fail_replay_or_the_boundary(self):
        for case, fact, refusal in (
            ("real span cannot support a wrong value", replace(self.fact, object="made up"), "complete claim"),
            ("correct value with an irrelevant span",
             replace(self.fact, proof=replace(self.proof, inputs=(self.source.span(1, 1),))), "complete claim"),
            ("wrong evidence class", replace(self.fact, evidence_class=EvidenceClass.CONTRACT), "complete claim"),
            ("unregistered evaluator is neither imported nor executed",
             replace(self.fact, proof=replace(self.proof, evaluator="evil.module/v1")), "unknown proof evaluator"),
            ("unknown debt cannot cross the verified boundary",
             replace(self.fact, evidence_class=EvidenceClass.UNKNOWN, proof=replace(self.proof, kind=ProofKind.DEBT)),
             "evidence debt"),
        ):
            with self.subTest(case), self.assertRaisesRegex(ValueError, refusal):
                self.verify(fact)

    def test_test_fixture_literal_does_not_establish_agent_fact(self):
        fixture = Source("scripts/test_example.py", b"name: example\n")
        snapshot = Snapshot("fixture", (self.source, fixture))
        fact = replace(self.fact, proof=replace(self.proof, inputs=(fixture.span(1, 1),)))
        with self.assertRaisesRegex(ValueError, "no authority"):
            self.verify(fact, snapshot)

    def test_missing_and_extra_joined_inputs_are_rejected(self):
        source = Source("agents/example.md", b"one\ntwo\nthree\n")
        snapshot = Snapshot("fixture", (source,))
        proof = Proof(ProofKind.JOINED, (source.span(1, 1), source.span(2, 2)), "join/v1")
        fact = replace(self.fact, object="one two", proof=proof)
        self.evaluators["join/v1"] = lambda f, s, p: Derivation(
            " ".join(s.source(source.path).lines[:2]), EvidenceClass.EXTRACTED,
            Proof(ProofKind.JOINED, (s.source(source.path).span(1, 1),
                                   s.source(source.path).span(2, 2)), "join/v1"))
        self.verify(fact, snapshot)
        for inputs in ((source.span(1, 1),), (*proof.inputs, source.span(3, 3))):
            with self.assertRaisesRegex(ValueError, "complete claim"):
                self.verify(replace(fact, proof=replace(proof, inputs=inputs)), snapshot)

    def test_absence_is_bound_to_complete_source_scope(self):
        proof = replace(self.proof, kind=ProofKind.ABSENCE,
                        scope_digest=self.snapshot.tree_digest, evaluator="absence/v1")
        fact = replace(self.fact, object="absent", proof=proof, evidence_class=EvidenceClass.UNKNOWN)
        self.evaluators["absence/v1"] = lambda f, s, p: Derivation(
            "absent", EvidenceClass.UNKNOWN,
            replace(proof, scope_digest=s.tree_digest))
        self.verify(fact)
        expanded = Snapshot("fixture", (*self.snapshot.sources, Source("docs/new.md", b"new\n")))
        with self.assertRaisesRegex(ValueError, "corpus differs"):
            self.verify(fact, expanded)

    def test_premises_are_verified_before_dependent_claim(self):
        premise = replace(self.fact, id="z-premise")
        proof = Proof(ProofKind.COMPUTED, (FactRef(premise.id),), "upper/v1")
        derived = replace(self.fact, id="a-derived", predicate="upper-name", object="EXAMPLE", proof=proof)
        predicate = replace(self.predicate, name="upper-name")
        rules = (self.predicate, predicate)
        graph = assemble((Bucket("test", (self.node,), (derived, premise)),), rules)
        self.evaluators["upper/v1"] = lambda f, s, p: Derivation(
            p["z-premise"].object.upper(), EvidenceClass.EXTRACTED, proof)
        result = verify_facts(graph, self.snapshot, rules, self.evaluators)
        self.assertEqual("a-derived", result.graph.facts[0].id)


if __name__ == "__main__":
    unittest.main()
