"""Fixtures shared by the fleet-atlas v2 test suites. Not a test module: pytest collects only test_*.py.

Plain functions and a mixin rather than pytest fixtures, so the unittest suites still run directly.
Every helper builds its fixture from scratch; none caches a repository, snapshot or verified graph.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from fleet_atlas_v2_artifacts import OUTPUT, runtime_modules
from fleet_atlas_v2_model import (
    EDGE_TYPES, Bucket, EvidenceClass, Fact, Node, Predicate, Proof, ProofKind, assemble, canonical_bytes,
)
from fleet_atlas_v2_proofs import Derivation, VerifiedFacts, verify_facts
from fleet_atlas_v2_sources import Snapshot

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


class ReadmeRepository:
    """setUp for a temporary one-commit repository whose only file is README.md = b"live\\n"."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        init_repository(self.root)
        (self.root / "README.md").write_bytes(b"live\n")
        self.git("add", "README.md")
        self.git("commit", "-qm", "fixture")

    def git(self, *args):
        return git(self.root, *args)

    def output(self, name):
        return self.root / OUTPUT / name


def fixture_extract(snapshot):
    """A one-fact extraction: README.md's first line is the document's state."""
    source = snapshot.source("README.md")
    node = Node("document:README.md", "document", source.path, "WHOLE_DOCUMENT")
    proof = Proof(ProofKind.EXTRACTED, (source.span(1, 1),), "fixture-title/v1")
    fact = Fact("state:README.md", node.id, "state", source.lines[0], EvidenceClass.EXTRACTED, proof)
    rule = Predicate("state", frozenset({"document"}), None, ("README.md",), 1)

    def evaluate(candidate, sources, premises):
        current = sources.source("README.md")
        return Derivation(current.lines[0], EvidenceClass.EXTRACTED,
                          Proof(ProofKind.EXTRACTED, (current.span(1, 1),), "fixture-title/v1"))

    return SimpleNamespace(buckets=(Bucket("fixture", (node,), (fact,)),),
                           predicates=(rule,), evaluators={"fixture-title/v1": evaluate})


def fact_rows(rows) -> bytes:
    """One JSON row per line: [id, subject, predicate, value] or [..., {qualifier: value}]."""
    return b"".join(canonical_bytes(list(row)) for row in rows)


def row_extraction(snapshot, path: str, evaluator: str = "row-fixture/v1"):
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

    def replay(fact, current_snapshot, premises):
        current = current_snapshot.source(path)
        i, row = next((i, json.loads(line)) for i, line in enumerate(current.lines, 1)
                      if json.loads(line)[0] == fact.id)
        return Derivation(row[3], EvidenceClass.EXTRACTED,
                          Proof(ProofKind.EXTRACTED, (current.span(i, i),), evaluator),
                          tuple(sorted(row[4].items())) if len(row) > 4 else ())

    return SimpleNamespace(buckets=(Bucket("rows", nodes, facts),), predicates=rules,
                           evaluators={evaluator: replay})


def echo(fact, snapshot, premises):
    """A replay that confirms whatever the fact claims. For rendering tests only, never proof tests."""
    return Derivation(fact.object, fact.evidence_class, fact.proof, fact.qualifiers)


def verified(sources, nodes, facts, predicates, evaluators=None, *, revision="fixture") -> VerifiedFacts:
    """Proof-verify a fixture graph; without `evaluators`, every fact's evaluator is echo()."""
    predicates = tuple(predicates)
    graph = assemble((Bucket("fixture", tuple(nodes), tuple(facts)),), predicates)
    evaluators = evaluators or {fact.proof.evaluator: echo for fact in facts}
    return verify_facts(graph, Snapshot(revision, tuple(sources)), predicates, evaluators)
