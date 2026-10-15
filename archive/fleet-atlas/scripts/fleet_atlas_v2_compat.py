"""Export all v2 facts for the separately enforced donor compatibility comparison.

The familiar node/edge shape is an observation surface, not a v1 runtime adapter.
Corrected evidence, source identities and all added facts remain visible as deltas.
No legacy defect or unrepresented predicate is silently normalized away.
"""

from __future__ import annotations

from typing import Any, TypeAlias, cast

from fleet_atlas_v2_format import citations, fact_record, graph_dict
from fleet_atlas_v2_model import EDGE_TYPES, Fact, Scalar, Value, canonical_bytes
from fleet_atlas_v2_proofs import VerifiedFacts

Thawed: TypeAlias = "Scalar | list[Thawed] | dict[str, Thawed]"


def thaw(value: Value) -> Thawed:
    if isinstance(value, tuple):
        if value and all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
                         for item in value):
            # The all() above checked that every item is a (name, value) pair.
            return {item[0]: thaw(item[1]) for item in cast("tuple[tuple[str, Value], ...]", value)}
        return [thaw(item) for item in value]
    return value


def _evidence(facts: tuple[Fact, ...], checked: VerifiedFacts) -> list[dict[str, object]]:
    unique = {}
    for fact in facts:
        for span in citations(fact, checked):
            record: dict[str, object] = {"path": span.path, "lines": [span.start_line, span.end_line],
                                         "excerptHash": span.excerpt_hash, "detector": fact.proof.evaluator,
                                         "class": fact.evidence_class.value}
            unique[canonical_bytes(record)] = record
    return [unique[key] for key in sorted(unique)]


def compatibility_snapshot(checked: VerifiedFacts, *, projections: dict[str, Any] | None = None,
                           queries: dict[str, Any] | None = None) -> dict[str, Any]:
    by_subject: dict[str, list[Fact]] = {}
    for fact in checked.graph.facts:
        by_subject.setdefault(fact.subject, []).append(fact)
    nodes = []
    consumed: set[str] = set()
    for node in checked.graph.nodes:
        facts = tuple(by_subject.get(node.id, ()))
        core = {}
        attrs = {}
        relevant = []
        for fact in facts:
            if fact.predicate in {"name", "authority", "state"}:
                if fact.predicate in core:
                    raise ValueError(f"ambiguous core fact for {node.id}: {fact.predicate}")
                core[fact.predicate] = thaw(fact.object)
            elif fact.predicate.startswith("attr."):
                key = fact.predicate.removeprefix("attr.")
                if key in attrs:
                    raise ValueError(f"ambiguous attribute for {node.id}: {key}")
                attrs[key] = thaw(fact.object)
            else:
                continue
            consumed.add(fact.id)
            relevant.append(fact)
        if set(core) != {"name", "authority", "state"}:
            raise ValueError(f"missing explicit node metadata facts: {node.id}")
        nodes.append({"id": node.id, "type": node.type, "path": node.path,
                      **core, "attrs": attrs, "evidence": _evidence(tuple(relevant), checked)})
    edges, unknowns, supplemental = [], [], []
    node_index = {node.id: node for node in checked.graph.nodes}
    for fact in checked.graph.facts:
        if fact.id in consumed:
            continue
        if fact.predicate in EDGE_TYPES:
            if not isinstance(fact.object, str) or fact.object not in node_index:
                raise ValueError(f"relationship lacks an entity target: {fact.id}")
            edges.append({"id": fact.id, "source": fact.subject, "target": fact.object,
                          "kind": fact.predicate, "class": fact.evidence_class.value,
                          "attrs": {key: thaw(value) for key, value in fact.qualifiers},
                          "evidence": _evidence((fact,), checked)})
        elif fact.predicate == "unknown":
            qualifiers = dict(fact.qualifiers)
            unknowns.append({"code": qualifiers.get("code", fact.id), "message": fact.object,
                             "path": qualifiers.get("path", node_index[fact.subject].path),
                             "neededEvidence": qualifiers.get("neededEvidence", "")})
            # v1 unknowns carry no proof or class; preserve those v2 observables too.
            supplemental.append(fact_record(fact, checked))
        else:
            supplemental.append(fact_record(fact, checked))
    snapshot = {"apiVersion": "save-toolkit/fleet-atlas/v1", "kind": "FleetAtlas",
                "metadata": {"repository": "latent-sre/save-toolkit", "revision": checked.snapshot.revision,
                             "dirty": False, "treeDigest": checked.snapshot.tree_digest,
                             "nodeCount": len(nodes), "edgeCount": len(edges), "unknownCount": len(unknowns)},
                "nodes": nodes, "edges": edges,
                "unknowns": sorted(unknowns, key=lambda row: (row["code"], row["path"] or "", row["message"])),
                "v2SupplementalFacts": supplemental,
                "v2Selectors": {node.id: node.selector for node in checked.graph.nodes},
                "v2Proofs": {fact["id"]: fact["proof"] for fact in graph_dict(checked.graph)["facts"]}}
    if projections is not None:
        snapshot["projections"] = projections
    if queries is not None:
        snapshot["queries"] = queries
    return snapshot
