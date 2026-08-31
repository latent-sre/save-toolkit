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
import re
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
CANONICAL_GLOBS = ("scripts/fleet_atlas*.py", "scripts/test_*.py", "evals/test_*.py")


def tracked_relative_paths(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
    )
    return {
        item.decode("utf-8", errors="surrogateescape")
        for item in result.stdout.split(b"\0")
        if item
    }


def _matches_canonical(relative: str) -> bool:
    if any(relative == entry or relative.startswith(f"{entry}/") for entry in CANONICAL_INPUTS):
        return True
    path = Path(relative)
    return (
        (path.parent.as_posix() == "scripts" and path.name.startswith("fleet_atlas") and path.suffix == ".py")
        or (path.parent.as_posix() == "scripts" and path.name.startswith("test_") and path.suffix == ".py")
        or (path.parent.as_posix() == "evals" and path.name.startswith("test_") and path.suffix == ".py")
    )


def canonical_inputs(root: Path) -> list[Path]:
    return [
        root / relative
        for relative in sorted(tracked_relative_paths(root))
        if _matches_canonical(relative) and (root / relative).is_file()
    ]


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


def render_all(root: Path, provenance: dict[str, object] | None = None) -> dict[str, bytes]:
    sys.path.insert(0, str(root / "scripts"))
    import fleet_atlas_views  # noqa: E402

    document = snapshot(root, build_graph(root))
    if provenance is not None:
        document["metadata"]["revision"] = provenance.get("revision")
        document["metadata"]["dirty"] = provenance.get("dirty")
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


REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


def provenance_failures(root: Path, metadata: object) -> list[str]:
    if not isinstance(metadata, dict):
        return ["atlas metadata is missing"]
    revision = metadata.get("revision")
    if not isinstance(revision, str) or not REVISION_RE.fullmatch(revision):
        return ["atlas revision is not a full lowercase Git object ID"]
    if metadata.get("dirty") is not False:
        return ["atlas was generated from dirty canonical inputs"]
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        cwd=root, capture_output=True,
    )
    if exists.returncode != 0:
        return [f"atlas revision {revision} is not available in this repository"]
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", revision, "HEAD"],
        cwd=root, capture_output=True,
    )
    if ancestor.returncode != 0:
        return [f"atlas revision {revision} is not an ancestor of HEAD"]
    pathspecs = [*CANONICAL_INPUTS, *(f":(glob){item}" for item in CANONICAL_GLOBS)]
    equivalent = subprocess.run(
        ["git", "diff", "--quiet", revision, "HEAD", "--", *pathspecs],
        cwd=root, capture_output=True,
    )
    if equivalent.returncode == 1:
        return [f"canonical inputs changed after atlas revision {revision}"]
    if equivalent.returncode != 0:
        return ["could not compare the atlas revision with HEAD"]
    return []


def manifest_failures(files: dict[str, bytes]) -> list[str]:
    try:
        recorded = json.loads(files.get("manifest.json", b""))
    except (json.JSONDecodeError, UnicodeError):
        return ["manifest.json is not valid JSON"]
    actual = manifest({name: content for name, content in files.items() if name != "manifest.json"})
    return [] if recorded == actual else ["manifest.json does not match the generated file set and hashes"]


def cmd_check(root: Path) -> int:
    sys.path.insert(0, str(root / "scripts"))
    import fleet_atlas_cite  # noqa: E402

    out = root / OUTPUT
    failures: list[str] = []
    committed_files = {
        path.name: path.read_bytes() for path in sorted(out.iterdir()) if path.is_file()
    } if out.is_dir() else {}
    if not committed_files:
        print(f"fleet_atlas check: {OUTPUT.as_posix()} is missing; run "
              "`python scripts/fleet_atlas.py build`", file=sys.stderr)
        print("fleet_atlas check: FAIL (1)")
        return 1
    try:
        committed_document = json.loads(committed_files.get("atlas.json", b""))
    except (json.JSONDecodeError, UnicodeError):
        committed_document = None
    failures.extend(provenance_failures(
        root,
        committed_document.get("metadata") if isinstance(committed_document, dict) else None,
    ))
    failures.extend(manifest_failures(committed_files))
    provenance = committed_document.get("metadata") if isinstance(committed_document, dict) else None
    expected = render_all(root, provenance if isinstance(provenance, dict) else None)
    committed = {k: v for k, v in committed_files.items() if k != "manifest.json"}
    for name in sorted(set(committed) | set(expected)):
        if committed.get(name) != expected.get(name):
            failures.append(f"drift: {name}")
    failures.extend(fleet_atlas_cite.parity_failures(root, json.loads(expected["atlas.json"])))
    for failure in sorted(set(failures)):
        print(f"fleet_atlas check: {failure}", file=sys.stderr)
    print("fleet_atlas check: " + ("PASS" if not failures else f"FAIL ({len(set(failures))})"))
    return 0 if not failures else 1


QUERY_VERBS = (
    "governs", "owner-of", "loads-for", "supersedes", "depends-on", "blocks",
    "verified-by", "evidence-for", "generated-from", "state",
)
QUERY_LIMIT = 20


def _node_summary(node: dict[str, object]) -> dict[str, object]:
    return {
        key: node.get(key)
        for key in ("id", "type", "name", "authority", "path", "state", "attrs", "evidence")
    }


def _node_matches(node: dict[str, object], term: str) -> bool:
    needle = term.casefold()
    values = (node.get("id"), node.get("name"), node.get("path"))
    return any(needle in str(value).casefold() for value in values if value is not None)


def _matching_nodes(
    document: dict[str, object], term: str, *, node_type: str | None = None
) -> list[dict[str, object]]:
    nodes = [
        node for node in document["nodes"]  # type: ignore[index]
        if isinstance(node, dict) and (node_type is None or node.get("type") == node_type)
    ]
    needle = term.casefold()
    exact = [
        node for node in nodes
        if any(
            needle == str(node.get(field)).casefold()
            for field in ("id", "name", "path")
            if node.get(field) is not None
        )
    ]
    return exact or [node for node in nodes if _node_matches(node, term)]


def _edge_summary(
    edge: dict[str, object], nodes: dict[str, dict[str, object]]
) -> dict[str, object]:
    return {
        "resultType": "edge",
        **edge,
        "sourceNode": _node_summary(nodes[str(edge["source"])]),
        "targetNode": _node_summary(nodes[str(edge["target"])]),
    }


def query_document(
    document: dict[str, object], verb: str, terms: list[str]
) -> tuple[list[dict[str, object]], bool]:
    if verb not in QUERY_VERBS:
        raise ValueError(f"unknown query verb {verb!r}")
    if not terms or any(not term.strip() for term in terms):
        raise ValueError("query terms must be non-empty")
    if verb == "loads-for" and len(terms) < 2:
        raise ValueError("loads-for requires a skill and a predicate")

    node_list = [node for node in document["nodes"] if isinstance(node, dict)]  # type: ignore[index]
    edge_list = [edge for edge in document["edges"] if isinstance(edge, dict)]  # type: ignore[index]
    nodes = {str(node["id"]): node for node in node_list}
    results: list[dict[str, object]] = []

    if verb == "governs":
        phrase = " ".join(terms).casefold()
        matched = [
            node for node in node_list
            if node.get("type") == "rule"
            and phrase in json.dumps(node, sort_keys=True).casefold()
        ]
        matched_ids = {str(node["id"]) for node in matched}
        results.extend({"resultType": "node", **_node_summary(node)} for node in matched)
        results.extend(
            _edge_summary(edge, nodes) for edge in edge_list
            if edge.get("kind") == "governed_by" and edge.get("source") in matched_ids
        )
    elif verb == "state":
        results.extend(
            {"resultType": "node", **_node_summary(node)}
            for node in _matching_nodes(document, " ".join(terms))
        )
    else:
        term = terms[0]
        matched_ids = {str(node["id"]) for node in _matching_nodes(document, term)}
        if verb == "loads-for":
            predicate = " ".join(terms[1:]).casefold()
            skill_ids = {
                str(node["id"])
                for node in _matching_nodes(document, term, node_type="skill")
            }
            selected = [
                edge for edge in edge_list
                if edge.get("kind") == "loads_when"
                and edge.get("source") in skill_ids
                and predicate in json.dumps(edge.get("attrs", {}), sort_keys=True).casefold()
            ]
        elif verb == "owner-of":
            selected = [
                edge for edge in edge_list
                if edge.get("kind") == "owns" and edge.get("target") in matched_ids
            ]
        elif verb == "supersedes":
            selected = [
                edge for edge in edge_list
                if edge.get("kind") == "supersedes"
                and (edge.get("source") in matched_ids or edge.get("target") in matched_ids)
            ]
        elif verb == "depends-on":
            selected = [
                edge for edge in edge_list
                if edge.get("kind") == "depends_on" and edge.get("source") in matched_ids
            ]
        elif verb == "blocks":
            selected = [
                edge for edge in edge_list
                if edge.get("kind") == "depends_on" and edge.get("target") in matched_ids
            ]
        elif verb == "verified-by":
            selected = [
                edge for edge in edge_list
                if edge.get("kind") == "verified_by" and edge.get("source") in matched_ids
            ]
        elif verb == "evidence-for":
            selected = [
                edge for edge in edge_list
                if edge.get("kind") == "evidenced_by" and edge.get("source") in matched_ids
            ]
        else:  # generated-from
            selected = [
                edge for edge in edge_list
                if edge.get("kind") == "generated_from" and edge.get("source") in matched_ids
            ]
        results.extend(_edge_summary(edge, nodes) for edge in selected)

    results.sort(key=lambda item: (str(item.get("resultType")), str(item.get("id"))))
    return results[:QUERY_LIMIT], len(results) > QUERY_LIMIT


def cmd_query(root: Path, verb: str, terms: list[str]) -> int:
    path = root / OUTPUT / "atlas.json"
    if not path.is_file():
        print("fleet_atlas query: generated atlas is missing; run build", file=sys.stderr)
        return 1
    try:
        document = json.loads(path.read_bytes())
    except (json.JSONDecodeError, UnicodeError):
        print("fleet_atlas query: generated atlas is not valid JSON", file=sys.stderr)
        return 1
    if not isinstance(document, dict) or document.get("apiVersion") != API_VERSION:
        print("fleet_atlas query: generated atlas has the wrong contract", file=sys.stderr)
        return 1
    metadata = document.get("metadata")
    if (
        not isinstance(metadata, dict)
        or metadata.get("treeDigest") != input_digest(root)
        or provenance_failures(root, metadata)
    ):
        print("fleet_atlas query: generated atlas is stale; run check", file=sys.stderr)
        return 1
    try:
        results, truncated = query_document(document, verb, terms)
    except ValueError as exc:
        print(f"fleet_atlas query: {exc}", file=sys.stderr)
        return 2
    record = {
        "apiVersion": "save-toolkit/fleet-atlas-query-result/v1",
        "query": {"verb": verb, "terms": terms},
        "atlas": {
            key: metadata.get(key)
            for key in ("revision", "dirty", "treeDigest")
        },
        "count": len(results),
        "truncated": truncated,
        "results": results,
    }
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if results else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="regenerate docs/fleet-atlas/generated/")
    sub.add_parser("check", help="regenerate in memory and compare with the committed output")
    query = sub.add_parser("query", help="query the committed, current fleet atlas")
    query.add_argument("verb", choices=QUERY_VERBS)
    query.add_argument("terms", nargs="+")
    args = parser.parse_args(argv)
    if args.command == "build":
        return cmd_build(args.root.resolve())
    if args.command == "check":
        return cmd_check(args.root.resolve())
    if args.command == "query":
        return cmd_query(args.root.resolve(), args.verb, args.terms)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
