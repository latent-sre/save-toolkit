"""Immutable fleet-atlas facts, explicit references, and deterministic graph assembly.

This is the v2 model foundation, not an atlas entrypoint. In particular a Graph is
unverified input; downstream surfaces must wait for the separate verifier boundary.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import TypeAlias

Scalar: TypeAlias = str | int | float | bool | None
Value: TypeAlias = Scalar | tuple["Value", ...]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def unsafe_identifier(value: str) -> bool:
    return any(unicodedata.category(character) in {"Cc", "Zl", "Zp"} for character in value)


def validate_path(path: str) -> None:
    parts = PurePosixPath(path).parts
    if (not parts or path.startswith("/") or "\\" in path or ":" in path
            or unsafe_identifier(path)
            or ".." in parts or PurePosixPath(path).as_posix() != path):
        raise ValueError(f"not a normalized repository-relative path: {path!r}")


def validate_value(value: Value) -> None:
    if isinstance(value, tuple):
        for item in value:
            validate_value(item)
    elif value is not None and type(value) not in (str, int, float, bool):
        raise TypeError("fact values must be immutable JSON scalars or tuples")
    canonical_bytes(value)  # Reject NaN and infinities as well as unserializable values.


class ProofKind(StrEnum):
    EXTRACTED = "EXTRACTED"
    NORMALIZED = "NORMALIZED"
    COMPUTED = "COMPUTED"
    JOINED = "JOINED"
    INFERRED = "INFERRED"
    ABSENCE = "ABSENCE"
    DEBT = "DEBT"


class EvidenceClass(StrEnum):
    CONTRACT = "CONTRACT_RESOLVED"
    EXTRACTED = "STATIC_EXTRACTED"
    INFERRED = "STATIC_INFERRED"
    OPERATOR = "OPERATOR_CONFIRMED"
    UNKNOWN = "UNKNOWN"

    @property
    def label(self) -> str:
        if self in (EvidenceClass.CONTRACT, EvidenceClass.EXTRACTED):
            return "verified"
        return "sourced" if self == EvidenceClass.OPERATOR else "unverified"


@dataclass(frozen=True, order=True)
class Span:
    path: str
    blob_hash: str
    start_line: int
    end_line: int
    excerpt_hash: str

    def __post_init__(self) -> None:
        validate_path(self.path)
        if type(self.start_line) is not int or type(self.end_line) is not int:
            raise ValueError("line bounds must be integers")
        if not 1 <= self.start_line <= self.end_line:
            raise ValueError("invalid source span")
        for value in (self.blob_hash, self.excerpt_hash):
            if not value.startswith("sha256:") or len(value) != 71:
                raise ValueError("source hashes must be full SHA-256 values")
            if any(c not in "0123456789abcdef" for c in value[7:]):
                raise ValueError("invalid SHA-256 digest")

    @classmethod
    def from_bytes(cls, path: str, blob: bytes, start: int, end: int) -> Span:
        return cls.from_lines(path, digest(blob), blob.decode("utf-8").splitlines(), start, end)

    @classmethod
    def from_lines(cls, path: str, blob_hash: str, lines: Sequence[str], start: int, end: int) -> Span:
        """The span of an already decoded blob: `lines` must be its UTF-8 text's splitlines()."""
        if not 1 <= start <= end <= len(lines):
            raise ValueError(f"span outside {path}: {start}-{end}")
        excerpt = "\n".join(lines[start - 1:end]).encode("utf-8")
        return cls(path, blob_hash, start, end, digest(excerpt))

    def verify(self, blob: bytes) -> None:
        self.verify_lines(digest(blob), blob.decode("utf-8").splitlines())

    def verify_lines(self, blob_hash: str, lines: Sequence[str]) -> None:
        if self != Span.from_lines(self.path, blob_hash, lines, self.start_line, self.end_line):
            raise ValueError(f"source span differs: {self.path}:{self.start_line}")


@dataclass(frozen=True, order=True)
class FactRef:
    fact_id: str


@dataclass(frozen=True)
class Proof:
    kind: ProofKind
    inputs: tuple[Span | FactRef, ...]
    evaluator: str
    scope_digest: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ProofKind):
            raise TypeError("proof kind must be explicit")
        if not isinstance(self.inputs, tuple) or not self.inputs:
            raise ValueError("proofs require immutable, nonempty determining inputs")
        if any(not isinstance(item, (Span, FactRef)) for item in self.inputs):
            raise TypeError("invalid proof input")
        if len(set(self.inputs)) != len(self.inputs):
            raise ValueError("duplicate proof input")
        if not self.evaluator or "/v" not in self.evaluator:
            raise ValueError("proof evaluator must have a versioned name")
        if self.kind == ProofKind.ABSENCE and not self.scope_digest:
            raise ValueError("absence proof requires a closed-world scope digest")


@dataclass(frozen=True, order=True)
class Node:
    id: str
    type: str
    path: str
    selector: str

    def __post_init__(self) -> None:
        validate_path(self.path)
        if not self.id or not self.type or not self.selector:
            raise ValueError("node identity, type, and selector are required")
        if any(unsafe_identifier(value) for value in (self.id, self.type, self.selector)):
            raise ValueError("node identity fields cannot contain control characters")


@dataclass(frozen=True)
class NodeRef:
    path: str
    node_type: str | None
    selector: str

    def __post_init__(self) -> None:
        validate_path(self.path)
        if not self.selector:
            raise ValueError("a selector is required; use WHOLE_DOCUMENT for bare links")


WHOLE_DOCUMENT = "WHOLE_DOCUMENT"

# The fleet vocabulary: every entity type, and every relationship with the entity types
# it may join. EDGE_TYPES derives from the endpoint table, so a relationship cannot be
# declared without its endpoints, nor exported as an edge without being declared.
NODE_TYPES = frozenset(("agent", "skill", "reference", "bundle-file", "command", "rule",
    "decision", "roadmap-item", "review", "scenario", "test", "schema", "schema-projection",
    "generated-projection", "capability", "owner", "probe", "hook", "document", "validator"))
# Endpoint authority is explicit, while trusted replay enforces syntax-level authority:
# a path literal inside a test never becomes a verified_by edge merely by matching a glob.
EDGE_ENDPOINTS = {
    "owns": ({"owner", "agent"}, NODE_TYPES),
    "routes_to": ({"scenario"}, {"agent", "skill", "command"}),
    "delegates_to": ({"agent"}, {"agent"}),
    "loads_when": ({"skill", "agent"}, {"reference", "skill"}),
    "governed_by": ({"rule"}, NODE_TYPES),
    "constrained_by": (NODE_TYPES, {"hook", "schema", "validator", "document"}),
    "verified_by": (NODE_TYPES, {"scenario", "test"}),
    "evidenced_by": ({"roadmap-item", "decision"}, {"decision", "review"}),
    "depends_on": ({"roadmap-item"}, {"roadmap-item"}),
    "blocks": ({"roadmap-item"}, {"roadmap-item"}),
    "supersedes": ({"decision"}, NODE_TYPES),
    "generated_from": ({"generated-projection"}, NODE_TYPES),
    "near_miss_for": ({"scenario"}, {"agent", "skill", "command"}),
    "contradicts": (NODE_TYPES, NODE_TYPES),
    "cites": (NODE_TYPES, NODE_TYPES),
}
EDGE_TYPES = frozenset(EDGE_ENDPOINTS)


class UnresolvedReference(ValueError):
    pass


class AmbiguousReference(ValueError):
    pass


class NodeIndex:
    def __init__(self, nodes: tuple[Node, ...]):
        if len({node.id for node in nodes}) != len(nodes):
            raise ValueError("duplicate node identity")
        self._nodes = tuple(sorted(nodes))

    def resolve(self, ref: NodeRef) -> Node:
        candidates = tuple(node for node in self._nodes if node.path == ref.path
                           and (ref.node_type is None or node.type == ref.node_type)
                           and (node.selector == ref.selector or node.id == ref.selector))
        if not candidates:
            raise UnresolvedReference(f"unresolved reference: {ref}")
        if len(candidates) != 1:
            raise AmbiguousReference(f"ambiguous reference {ref}: "
                                     + ", ".join(node.id for node in candidates))
        return candidates[0]


@dataclass(frozen=True)
class Predicate:
    name: str
    source_types: frozenset[str]
    target_types: frozenset[str] | None
    authority_globs: tuple[str, ...]
    max_per_subject: int | None = None


@dataclass(frozen=True)
class Fact:
    id: str
    subject: str
    predicate: str
    object: Value
    evidence_class: EvidenceClass
    proof: Proof
    qualifiers: tuple[tuple[str, Value], ...] = ()

    def __post_init__(self) -> None:
        if not self.id or not self.subject or not self.predicate:
            raise ValueError("fact identity, subject, and predicate are required")
        if any(unsafe_identifier(value) for value in (self.id, self.subject, self.predicate)):
            raise ValueError("fact identity fields cannot contain control characters")
        validate_value(self.object)
        if (not isinstance(self.qualifiers, tuple)
                or any(not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str)
                       for item in self.qualifiers)):
            raise TypeError("fact qualifiers must be immutable named pairs")
        if [name for name, _ in self.qualifiers] != sorted({name for name, _ in self.qualifiers}):
            raise ValueError("fact qualifiers require unique sorted names")
        for _, value in self.qualifiers:
            validate_value(value)
        if not isinstance(self.evidence_class, EvidenceClass):
            raise TypeError("evidence class must be explicit")
        if self.proof.kind == ProofKind.INFERRED and self.evidence_class != EvidenceClass.INFERRED:
            raise ValueError("inferred proof cannot be promoted")
        if self.proof.kind == ProofKind.DEBT and self.evidence_class != EvidenceClass.UNKNOWN:
            raise ValueError("evidence debt cannot be promoted")


@dataclass(frozen=True)
class Bucket:
    extractor: str
    nodes: tuple[Node, ...]
    facts: tuple[Fact, ...]


@dataclass(frozen=True)
class Graph:
    nodes: tuple[Node, ...]
    facts: tuple[Fact, ...]


def assemble(buckets: tuple[Bucket, ...], predicates: tuple[Predicate, ...]) -> Graph:
    """Merge independent extractor results; reject conflict rather than choosing a winner."""
    if len({bucket.extractor for bucket in buckets}) != len(buckets):
        raise ValueError("duplicate extractor registration")
    nodes: dict[str, Node] = {}
    facts: dict[str, Fact] = {}
    rules = {item.name: item for item in predicates}
    if len(rules) != len(predicates):
        raise ValueError("duplicate predicate declaration")
    for bucket in sorted(buckets, key=lambda item: item.extractor):
        for node in bucket.nodes:
            if node.id in nodes and nodes[node.id] != node:
                raise ValueError(f"conflicting node identity: {node.id}")
            nodes[node.id] = node
        for fact in bucket.facts:
            if fact.id in facts and facts[fact.id] != fact:
                raise ValueError(f"conflicting fact identity: {fact.id}")
            facts[fact.id] = fact
    counts: dict[tuple[str, str], int] = {}
    for fact in facts.values():
        if fact.subject not in nodes:
            raise ValueError(f"dangling subject: {fact.id}")
        if fact.predicate not in rules:
            raise ValueError(f"undeclared predicate: {fact.predicate}")
        rule = rules[fact.predicate]
        if nodes[fact.subject].type not in rule.source_types:
            raise ValueError(f"invalid source type: {fact.id}")
        if rule.target_types is not None:
            if not isinstance(fact.object, str) or fact.object not in nodes:
                raise ValueError(f"dangling target: {fact.id}")
            if nodes[fact.object].type not in rule.target_types:
                raise ValueError(f"invalid target type: {fact.id}")
        key = (fact.subject, fact.predicate)
        counts[key] = counts.get(key, 0) + 1
        if rule.max_per_subject is not None and counts[key] > rule.max_per_subject:
            raise ValueError(f"predicate cardinality exceeded: {key}")
        for item in fact.proof.inputs:
            if isinstance(item, FactRef) and item.fact_id not in facts:
                raise ValueError(f"missing proof premise: {item.fact_id}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(fact_id: str) -> None:
        if fact_id in visited:
            return
        if fact_id in visiting:
            raise ValueError(f"cyclic proof: {fact_id}")
        visiting.add(fact_id)
        for item in facts[fact_id].proof.inputs:
            if isinstance(item, FactRef):
                visit(item.fact_id)
        visiting.remove(fact_id)
        visited.add(fact_id)

    for fact_id in sorted(facts):
        visit(fact_id)
    return Graph(tuple(nodes[key] for key in sorted(nodes)),
                 tuple(facts[key] for key in sorted(facts)))


def assert_debt_subset(graph: Graph, baseline: frozenset[str], *, cutover: bool = False) -> None:
    debt = {fact.id for fact in graph.facts if fact.proof.kind == ProofKind.DEBT}
    if added := debt - baseline:
        raise ValueError(f"new evidence debt: {sorted(added)}")
    if cutover and debt:
        raise ValueError(f"cutover requires zero evidence debt: {sorted(debt)}")
