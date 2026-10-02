"""Proof replay boundary for immutable fleet-atlas graphs.

Evaluators are trusted implementation functions, not names imported from an atlas.
They must independently reconstruct the complete value, evidence class and proof
inputs from the closed source snapshot. Source containment alone proves no claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Callable, Mapping

from fleet_atlas_v2_model import (
    Bucket, EvidenceClass, Fact, FactRef, Graph, Predicate, Proof, ProofKind, Span,
    Value, assemble, assert_debt_subset,
)
from fleet_atlas_v2_sources import Snapshot


@dataclass(frozen=True)
class Derivation:
    value: Value
    evidence_class: EvidenceClass
    proof: Proof
    qualifiers: tuple[tuple[str, Value], ...] = ()


Evaluator = Callable[[Fact, Snapshot, Mapping[str, Fact]], Derivation]
_SEAL = object()


@dataclass(frozen=True)
class VerifiedFacts:
    """Only proof-checked graph data; artifact verification is a separate outer step."""

    graph: Graph
    snapshot: Snapshot
    _seal: object = field(repr=False, compare=False)
    fact_index: Mapping[str, Fact] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise ValueError("VerifiedFacts can only be constructed by proof verification")
        object.__setattr__(self, "fact_index", MappingProxyType({fact.id: fact for fact in self.graph.facts}))


def verify_facts(
    graph: Graph,
    snapshot: Snapshot,
    predicates: tuple[Predicate, ...],
    evaluators: Mapping[str, Evaluator],
) -> VerifiedFacts:
    """Replay all claims before allowing a graph across the fact trust boundary.

This does not certify artifacts, a manifest, or checkout freshness. The eventual
artifact verifier must check those before any query/render surface accepts data.
"""
    rebuilt = assemble((Bucket("verify", graph.nodes, graph.facts),), predicates)
    if graph != rebuilt:
        raise ValueError("graph is not in canonical deterministic order")
    assert_debt_subset(graph, frozenset(), cutover=True)
    rules = {rule.name: rule for rule in predicates}
    facts = {fact.id: fact for fact in graph.facts}
    verified: dict[str, Fact] = {}

    def verify(fact: Fact) -> None:
        if fact.id in verified:
            return
        evaluator = evaluators.get(fact.proof.evaluator)
        if evaluator is None:
            raise ValueError(f"unknown proof evaluator: {fact.proof.evaluator}")
        for item in fact.proof.inputs:
            if isinstance(item, Span):
                snapshot.verify_span(item)
                if not any(PurePosixPath(item.path).match(pattern)
                           for pattern in rules[fact.predicate].authority_globs):
                    raise ValueError(f"source has no authority for {fact.predicate}: {item.path}")
            elif isinstance(item, FactRef):
                verify(facts[item.fact_id])
        if fact.proof.kind == ProofKind.ABSENCE and fact.proof.scope_digest != snapshot.tree_digest:
            raise ValueError(f"absence proof corpus differs: {fact.id}")
        # Pass only verified premises, not unchecked candidate facts. A caller's
        # proof-input ordering does not change the set of visible trusted premises.
        premises = {item.fact_id: verified[item.fact_id]
                    for item in fact.proof.inputs if isinstance(item, FactRef)}
        expected = evaluator(fact, snapshot, MappingProxyType(premises))
        if not isinstance(expected, Derivation):
            raise TypeError("trusted evaluator returned an invalid derivation")
        if expected != Derivation(fact.object, fact.evidence_class, fact.proof, fact.qualifiers):
            raise ValueError(f"proof does not determine complete claim: {fact.id}")
        verified[fact.id] = fact

    for fact in graph.facts:
        verify(fact)
    return VerifiedFacts(graph, snapshot, _SEAL)
