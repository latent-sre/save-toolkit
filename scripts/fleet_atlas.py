#!/usr/bin/env python3
"""Fleet knowledge atlas (GRAPH-004): a revision-bound graph over the fleet's own artifacts.

The atlas CITES edges that existing validators enforce (delegation, guard roster, generated
projections, roadmap prerequisites) and EXTRACTS the rest from canonical bytes. It never defines an
authority, never parses application source, never touches the network, and never writes outside
docs/fleet-atlas/generated/. A generated answer is a projection; only a human edit changes truth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("docs/fleet-atlas/generated")
API_VERSION = "save-toolkit/fleet-atlas/v1"
PROVENANCE = ("CONTRACT_RESOLVED", "STATIC_EXTRACTED", "STATIC_INFERRED", "OPERATOR_CONFIRMED", "UNKNOWN")
AUTHORITY = ("canonical", "live-contract", "generated", "historical-evidence", "external")
STATES = ("live", "historical", "retired", "proposed", "rejected", "deprecated", "generated")


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def excerpt_hash(lines: list[str]) -> str:
    return "sha256:" + hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Evidence:
    path: str
    lines: tuple[int, int]
    excerpt_hash: str
    detector: str
    cls: str

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "lines": list(self.lines),
            "excerptHash": self.excerpt_hash,
            "detector": self.detector,
            "class": self.cls,
        }


def cite(root: Path, relative: str, start: int, end: int, detector: str, cls: str) -> Evidence:
    if cls not in PROVENANCE:
        raise ValueError(f"unknown provenance class {cls!r}")
    lines = (root / relative).read_text(encoding="utf-8").splitlines()
    if not 1 <= start <= end <= max(1, len(lines)):
        raise ValueError(f"{relative}: line range {start}-{end} outside 1-{len(lines)}")
    return Evidence(relative, (start, end), excerpt_hash(lines[start - 1 : end]), detector, cls)


@dataclass
class Node:
    id: str
    type: str
    name: str
    authority: str
    path: str | None
    state: str
    attrs: dict[str, object] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "authority": self.authority,
            "path": self.path,
            "state": self.state,
            "attrs": self.attrs,
            "evidence": [item.as_dict() for item in self.evidence],
        }


@dataclass
class Edge:
    id: str
    source: str
    target: str
    kind: str
    cls: str
    attrs: dict[str, object] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "class": self.cls,
            "attrs": self.attrs,
            "evidence": [item.as_dict() for item in self.evidence],
        }


@dataclass
class Unknown:
    code: str
    message: str
    path: str | None
    needed_evidence: str

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "neededEvidence": self.needed_evidence,
        }


class Graph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Edge] = {}
        self.unknowns: list[Unknown] = []

    def add_node(self, node: Node) -> Node:
        if node.id in self.nodes:
            raise ValueError(f"duplicate node id {node.id}")
        if node.authority not in AUTHORITY:
            raise ValueError(f"unknown authority {node.authority!r} on {node.id}")
        if node.state not in STATES:
            raise ValueError(f"unknown state {node.state!r} on {node.id}")
        self.nodes[node.id] = node
        return node

    def add_edge(self, edge: Edge) -> Edge:
        if edge.cls not in PROVENANCE:
            raise ValueError(f"unknown provenance class {edge.cls!r} on {edge.id}")
        if edge.id in self.edges:
            raise ValueError(f"duplicate edge id {edge.id}")
        self.edges[edge.id] = edge
        return edge

    def add_unknown(self, unknown: Unknown) -> None:
        self.unknowns.append(unknown)


def git_revision(root: Path) -> tuple[str, bool]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout
    return head, bool(status.strip())


def snapshot(root: Path, graph: Graph) -> dict[str, object]:
    sys.path.insert(0, str(root / "scripts"))
    import evidence_envelope  # noqa: E402  (stdlib-only sibling script)

    revision, dirty = git_revision(root)
    return {
        "apiVersion": API_VERSION,
        "kind": "FleetAtlas",
        "metadata": {
            "repository": root.name,
            "revision": revision,
            "dirty": dirty,
            "treeDigest": "sha256:" + evidence_envelope.tree_digest(root / "agents"),
            "nodeCount": len(graph.nodes),
            "edgeCount": len(graph.edges),
            "unknownCount": len(graph.unknowns),
        },
        "nodes": [graph.nodes[key].as_dict() for key in sorted(graph.nodes)],
        "edges": [graph.edges[key].as_dict() for key in sorted(graph.edges)],
        "unknowns": [item.as_dict() for item in sorted(graph.unknowns, key=lambda u: (u.code, u.path or "", u.message))],
    }


def write_json(path: Path, document: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")


def build_graph(root: Path) -> Graph:
    sys.path.insert(0, str(root / "scripts"))
    import fleet_atlas_extract  # noqa: E402

    graph = Graph()
    fleet_atlas_extract.extract_agents(root, graph)
    fleet_atlas_extract.extract_skills(root, graph)
    fleet_atlas_extract.extract_commands(root, graph)
    return graph


def cmd_build(root: Path) -> int:
    document = snapshot(root, build_graph(root))
    write_json(root / OUTPUT / "atlas.json", document)
    print(f"fleet_atlas: wrote {OUTPUT}/atlas.json "
          f"({document['metadata']['nodeCount']} nodes, {document['metadata']['edgeCount']} edges, "
          f"{document['metadata']['unknownCount']} unknowns)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="regenerate docs/fleet-atlas/generated/")
    args = parser.parse_args(argv)
    if args.command == "build":
        return cmd_build(args.root.resolve())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
