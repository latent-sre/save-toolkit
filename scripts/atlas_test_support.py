"""Fixtures shared by the fleet-atlas v2 test suites. Not a test module: pytest collects only test_*.py.

Plain functions and a mixin rather than pytest fixtures, so the unittest suites still run directly.
Every helper builds its fixture from scratch; none caches a repository, snapshot or verified graph.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections.abc import Collection, Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from fleet_atlas_v2_artifacts import OUTPUT, runtime_modules
from fleet_atlas_v2_model import (
    EDGE_TYPES,
    Bucket,
    EvidenceClass,
    Fact,
    Node,
    Predicate,
    Proof,
    ProofKind,
    assemble,
)
from fleet_atlas_v2_proofs import Derivation, Evaluator, Extraction, VerifiedFacts, verify_facts
from fleet_atlas_v2_sources import Snapshot, Source

if TYPE_CHECKING:
    # The mixin's tests subclass unittest.TestCase, which supplies addCleanup.
    from unittest import TestCase as _TestCase
else:
    _TestCase = object

RUNTIME = Path(__file__).resolve().parent


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout


def init_repository(root: Path, user: str = "Atlas test") -> None:
    """An empty repository whose commits keep the exact bytes the fixture writes."""
    git(root, "init", "-q")
    git(root, "config", "user.name", user)
    git(root, "config", "user.email", "atlas@example.invalid")
    git(root, "config", "core.autocrlf", "false")


def copy_runtime(root: Path) -> Path:
    """Copy the running atlas implementation into `root`/scripts, as the real tree holds it."""
    scripts = root / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for path in runtime_modules(RUNTIME):
        shutil.copyfile(path, scripts / path.name)
    return scripts


class ReadmeRepository(_TestCase):
    """setUp for a temporary one-commit repository whose only file is README.md = b"live\\n"."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        init_repository(self.root)
        (self.root / "README.md").write_bytes(b"live\n")
        self.git("add", "README.md")
        self.git("commit", "-qm", "fixture")

    def git(self, *args: str) -> bytes:
        return git(self.root, *args)

    def output(self, name: str) -> Path:
        return self.root / OUTPUT / name


def fixture_extract(snapshot: Snapshot) -> Extraction:
    """A one-fact extraction: README.md's first line is the document's state."""
    source = snapshot.source("README.md")
    node = Node("document:README.md", "document", source.path, "WHOLE_DOCUMENT")
    proof = Proof(ProofKind.EXTRACTED, (source.span(1, 1),), "fixture-title/v1")
    fact = Fact("state:README.md", node.id, "state", source.lines[0], EvidenceClass.EXTRACTED, proof)
    rule = Predicate("state", frozenset({"document"}), None, ("README.md",), 1)

    def evaluate(candidate: Fact, sources: Snapshot, premises: Mapping[str, Fact]) -> Derivation:
        current = sources.source("README.md")
        return Derivation(current.lines[0], EvidenceClass.EXTRACTED,
                          Proof(ProofKind.EXTRACTED, (current.span(1, 1),), "fixture-title/v1"))

    return Extraction((Bucket("fixture", (node,), (fact,)),), (rule,), {"fixture-title/v1": evaluate})


def fact_rows(rows: Iterable[Iterable[object]]) -> bytes:
    """One JSON row per line: [id, subject, predicate, value] or [..., {qualifier: value}].

    ASCII escaping keeps U+2028, U+0085 and other str.splitlines() separators inside a row.
    """
    return b"".join((json.dumps(list(row), ensure_ascii=True, sort_keys=True) + "\n").encode("ascii") for row in rows)


def row_extraction(snapshot: Snapshot, path: str, evaluator: str = "row-fixture/v1") -> Extraction:
    """An extraction with one fact per row of `path`, each cited by and replayed from its own line.

    Nodes are every row subject and relationship target; a relationship is any row whose
    predicate is in the fleet's EDGE_TYPES, and its target node type is the identity's prefix.
    """
    source = snapshot.source(path)
    rows = [json.loads(line) for line in source.lines]
    identities = sorted({row[1] for row in rows} | {row[3] for row in rows if row[2] in EDGE_TYPES})
    nodes = tuple(Node(identity, identity.split(":", 1)[0], source.path, identity) for identity in identities)
    facts = tuple(Fact(row[0], row[1], row[2], row[3], EvidenceClass.EXTRACTED,
                       Proof(ProofKind.EXTRACTED, (source.span(i, i),), evaluator),
                       tuple(sorted(row[4].items())) if len(row) > 4 else ())
                  for i, row in enumerate(rows, 1))
    kinds = frozenset(node.type for node in nodes)
    rules = tuple(Predicate(predicate, kinds, kinds if predicate in EDGE_TYPES else None, (source.path,))
                  for predicate in sorted({row[2] for row in rows}))

    def replay(fact: Fact, current_snapshot: Snapshot, premises: Mapping[str, Fact]) -> Derivation:
        current = current_snapshot.source(path)
        i, row = next((i, json.loads(line)) for i, line in enumerate(current.lines, 1)
                      if json.loads(line)[0] == fact.id)
        return Derivation(row[3], EvidenceClass.EXTRACTED,
                          Proof(ProofKind.EXTRACTED, (current.span(i, i),), evaluator),
                          tuple(sorted(row[4].items())) if len(row) > 4 else ())

    return Extraction((Bucket("rows", nodes, facts),), rules, {evaluator: replay})


def echo(fact: Fact, snapshot: Snapshot, premises: Mapping[str, Fact]) -> Derivation:
    """A replay that confirms whatever the fact claims. For rendering tests only, never proof tests."""
    return Derivation(fact.object, fact.evidence_class, fact.proof, fact.qualifiers)


def verified(sources: Iterable[Source], nodes: Iterable[Node], facts: Collection[Fact], predicates: Iterable[Predicate],
             evaluators: Mapping[str, Evaluator] | None = None, *, revision: str = "fixture") -> VerifiedFacts:
    """Proof-verify a fixture graph; without `evaluators`, every fact's evaluator is echo()."""
    predicates = tuple(predicates)
    graph = assemble((Bucket("fixture", tuple(nodes), tuple(facts)),), predicates)
    evaluators = evaluators or {fact.proof.evaluator: echo for fact in facts}
    return verify_facts(graph, Snapshot(revision, tuple(sources)), predicates, evaluators)
