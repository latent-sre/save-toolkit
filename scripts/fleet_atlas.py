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
    # The dirty check excludes OUTPUT itself. docs/fleet-atlas/generated/ is a committed,
    # self-referential artifact that embeds this very revision+dirty pair -- once committed, it was
    # necessarily generated one commit earlier (there is no way for a commit to embed its own future
    # sha), so a `build` against a freshly checked-out, otherwise-clean HEAD always rewrites it to a
    # byte-different (still correct) state and would make the tree look dirty forever after, purely
    # from the atlas describing itself. "dirty" is meant to answer whether the CANONICAL INPUTS the
    # atlas documents differ from a clean checkout, not whether the atlas's own last build already
    # matches its next one -- the same reasoning input_digest() already applies by leaving OUTPUT out
    # of CANONICAL_INPUTS. Proven by reproduction: committing generated/ then running the component
    # test suite intermittently failed ViewAndDriftTests with a spurious dirty-flag mismatch between
    # two builds in the same process; excluding OUTPUT from this pathspec made `git status` -- and
    # every subsequent build/check in the same run -- agree.
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no", "--", ".", f":(exclude){OUTPUT.as_posix()}"],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout
    return head, bool(status.strip())


CANONICAL_INPUTS = ("agents", "skills", "commands", "docs/rules.md", "docs/fleet-roadmap.md", "docs/roadmap-closed.md",
                    "docs/decisions", "docs/reviews", "docs/probes", "evals/scenarios", "evals/build-scenarios", "schemas",
                    "hooks", "AGENTS.md", "CONTRIBUTING.md", "README.md", "docs/README.md", "docs/schema-compatibility.md")


def canonical_inputs(root: Path) -> list[Path]:
    files: list[Path] = []
    for entry in CANONICAL_INPUTS:
        path = root / entry
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file())
    files.extend(p for p in (root / "scripts").glob("test_*.py"))
    files.extend(p for p in (root / "evals").glob("test_*.py"))
    return sorted(set(files))


def input_digest(root: Path) -> str:
    lines = [f"{p.relative_to(root).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}" for p in canonical_inputs(root)]
    return excerpt_hash(lines)


def snapshot(root: Path, graph: Graph) -> dict[str, object]:
    revision, dirty = git_revision(root)
    return {
        "apiVersion": API_VERSION,
        "kind": "FleetAtlas",
        "metadata": {
            "repository": root.name,
            "revision": revision,
            "dirty": dirty,
            "treeDigest": input_digest(root),
            "nodeCount": len(graph.nodes),
            "edgeCount": len(graph.edges),
            "unknownCount": len(graph.unknowns),
        },
        "nodes": [graph.nodes[key].as_dict() for key in sorted(graph.nodes)],
        "edges": [graph.edges[key].as_dict() for key in sorted(graph.edges)],
        "unknowns": [item.as_dict() for item in sorted(graph.unknowns, key=lambda u: (u.code, u.path or "", u.message))],
    }


def manifest(files: dict[str, bytes]) -> dict[str, object]:
    return {"apiVersion": "save-toolkit/fleet-atlas-manifest/v1",
            "files": {name: "sha256:" + hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())}}


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
    fleet_atlas_extract.extract_documents(root, graph)
    fleet_atlas_extract.extract_rules(root, graph)
    fleet_atlas_extract.extract_roadmap(root, graph)
    fleet_atlas_extract.extract_closed_register(root, graph)
    fleet_atlas_extract.extract_decisions(root, graph)
    fleet_atlas_extract.extract_reviews(root, graph)
    fleet_atlas_extract.extract_scenarios(root, graph)
    fleet_atlas_extract.extract_tests(root, graph)
    fleet_atlas_extract.extract_schemas(root, graph)
    fleet_atlas_extract.extract_probes(root, graph)
    fleet_atlas_extract.extract_owners(root, graph)

    import fleet_atlas_cite  # noqa: E402
    fleet_atlas_cite.cite_delegation(root, graph)
    fleet_atlas_cite.cite_guard(root, graph)
    fleet_atlas_cite.cite_generated(root, graph)
    fleet_atlas_extract.link_evidence(root, graph)

    import fleet_atlas_detect  # noqa: E402
    fleet_atlas_detect.run(root, graph)
    return graph


def render_all(root: Path) -> dict[str, bytes]:
    sys.path.insert(0, str(root / "scripts"))
    import fleet_atlas_views  # noqa: E402

    document = snapshot(root, build_graph(root))
    files = {name: text.encode("utf-8") for name, text in fleet_atlas_views.render_views(document).items()}
    files["atlas.json"] = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return files


def cmd_build(root: Path) -> int:
    files = render_all(root)
    out = root / OUTPUT
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.iterdir():
        if stale.name not in files and stale.name != "manifest.json":
            stale.unlink()
    for name, content in files.items():
        (out / name).write_bytes(content)
    write_json(out / "manifest.json", manifest(files))
    print(f"fleet_atlas: wrote {len(files) + 1} files under {OUTPUT}")
    return 0


def cmd_check(root: Path) -> int:
    sys.path.insert(0, str(root / "scripts"))
    import fleet_atlas_cite  # noqa: E402

    out = root / OUTPUT
    failures: list[str] = []
    expected = render_all(root)
    committed = json.loads((out / "manifest.json").read_text(encoding="utf-8")) if (out / "manifest.json").is_file() else {"files": {}}
    if committed["files"] != manifest(expected)["files"]:
        for name in sorted(set(committed["files"]) | set(expected)):
            if committed["files"].get(name) != manifest(expected)["files"].get(name):
                failures.append(f"drift: {name}")
    for name, content in expected.items():
        if not (out / name).is_file() or (out / name).read_bytes() != content:
            failures.append(f"drift: {name} (bytes)")
    failures.extend(fleet_atlas_cite.parity_failures(root, json.loads(expected["atlas.json"])))
    for failure in sorted(set(failures)):
        print(f"fleet_atlas check: {failure}", file=sys.stderr)
    print("fleet_atlas check: " + ("PASS" if not failures else f"FAIL ({len(set(failures))})"))
    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="regenerate docs/fleet-atlas/generated/")
    sub.add_parser("check", help="regenerate in memory and compare with the committed output")
    args = parser.parse_args(argv)
    if args.command == "build":
        return cmd_build(args.root.resolve())
    if args.command == "check":
        return cmd_check(args.root.resolve())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
