#!/usr/bin/env python3
"""Cite edges that existing validators enforce. Nothing here derives an authority."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import generate_platform_adapters as adapters  # noqa: E402
import validate_fleet  # noqa: E402
from fleet_atlas import Edge, Graph, Node, Unknown, cite  # noqa: E402
from fleet_atlas_extract import edge_id, find_line  # noqa: E402

GUARD_ID = "hook:readonly-guard"


def cite_delegation(root: Path, graph: Graph) -> None:
    for agent, targets in sorted(validate_fleet.EXPECTED_DELEGATION.items()):
        source = f"agent:{agent}"
        if source not in graph.nodes:
            graph.add_unknown(Unknown("cite.delegation-agent-missing",
                                      f"EXPECTED_DELEGATION names {agent}, which has no agent file",
                                      None, "Add agents/<name>.md or remove the literal entry"))
            continue
        relative = f"agents/{agent}.md"
        granted = set(graph.nodes[source].attrs.get("grants", []))
        if granted != set(targets):
            graph.add_unknown(Unknown("cite.delegation-mismatch",
                                      f"{relative} grants {sorted(granted)} but EXPECTED_DELEGATION says {sorted(targets)}",
                                      relative, "validate_fleet owns this failure; the atlas records it and emits no edge"))
            continue
        line = find_line(root, relative, "tools:")
        for target in sorted(targets):
            graph.add_edge(Edge(edge_id("delegates_to", source, f"agent:{target}"), source, f"agent:{target}",
                                "delegates_to", "CONTRACT_RESOLVED", {},
                                [cite(root, relative, line, line, "validate_fleet.EXPECTED_DELEGATION",
                                      "CONTRACT_RESOLVED")]))


def cite_guard(root: Path, graph: Graph) -> None:
    line = find_line(root, "hooks/hooks.json", "readonly-guard.py")
    graph.add_node(Node(GUARD_ID, "hook", "readonly-guard", "live-contract", "hooks/hooks.json", "live",
                        {"matcher": "Bash"},
                        [cite(root, "hooks/hooks.json", line, line, "hooks.PreToolUse", "CONTRACT_RESOLVED")]))
    for agent in sorted(adapters.GUARDED_AGENTS):
        source = f"agent:{agent}"
        if source in graph.nodes:
            graph.add_edge(Edge(edge_id("constrained_by", source, GUARD_ID), source, GUARD_ID, "constrained_by",
                                "CONTRACT_RESOLVED", {"via": "generate_platform_adapters.GUARDED_AGENTS"},
                                [cite(root, "hooks/hooks.json", line, line, "generate_platform_adapters.GUARDED_AGENTS",
                                      "CONTRACT_RESOLVED")]))


def canonical_for(projection: str) -> str | None:
    if projection.startswith(".github/agents/") and projection.endswith(".agent.md"):
        return "agent:" + projection.removeprefix(".github/agents/").removesuffix(".agent.md")
    prefix = "platforms/copilot/skills/"
    if projection.startswith(prefix):
        rest = projection.removeprefix(prefix)
        skill, _, tail = rest.partition("/")
        if tail == "SKILL.md":
            return f"skill:{skill}"
        if tail.startswith("references/") and tail.endswith(".md"):
            return f"reference:{skill}/{tail.removeprefix('references/')}"
        return f"bundle-file:{skill}/{tail}"
    return None


def cite_generated(root: Path, graph: Graph) -> None:
    catalog = json.loads((root / "schemas/catalog-v1.json").read_text(encoding="utf-8"))
    projection_schemas = {
        projection: f"schema:{entry['id']}"
        for entry in catalog["schemas"]
        for projection in entry.get("generated_projections", [])
    }
    generator_line = find_line(root, "scripts/generate_platform_adapters.py", "def expected_outputs")
    for path, content in sorted(adapters.expected_outputs(root).items()):
        projection = path.as_posix()
        node_id = f"generated-projection:{projection}"
        graph.add_node(Node(node_id, "generated-projection", projection, "generated", projection, "generated",
                            {"bytes": len(content)},
                            [cite(root, "scripts/generate_platform_adapters.py", generator_line, generator_line,
                                  "generate_platform_adapters.expected_outputs", "CONTRACT_RESOLVED")]))
        target = canonical_for(projection)
        if target is None or target not in graph.nodes:
            graph.add_unknown(Unknown("cite.generated-source-missing",
                                      f"{projection} has no canonical node ({target})", projection,
                                      "Regenerate adapters; the generator owns this mapping"))
            continue
        graph.add_edge(Edge(edge_id("generated_from", node_id, target), node_id, target, "generated_from",
                            "CONTRACT_RESOLVED", {"via": "generate_platform_adapters.expected_outputs"},
                            [cite(root, "scripts/generate_platform_adapters.py", generator_line, generator_line,
                                  "generate_platform_adapters.expected_outputs", "CONTRACT_RESOLVED")]))
        schema_id = projection_schemas.get(projection)
        if schema_id in graph.nodes:
            line = find_line(root, "schemas/catalog-v1.json", f'"{projection}"')
            graph.add_edge(Edge(edge_id("constrained_by", node_id, schema_id), node_id, schema_id,
                                "constrained_by", "CONTRACT_RESOLVED", {"via": "catalog-v1.json"},
                                [cite(root, "schemas/catalog-v1.json", line, line,
                                      "extract.catalog-projection", "CONTRACT_RESOLVED")]))


def parity_failures(root: Path, document: dict) -> list[str]:
    failures: list[str] = []
    edges = document["edges"]
    nodes = document["nodes"]
    delegation = {(e["source"].removeprefix("agent:"), e["target"].removeprefix("agent:"))
                  for e in edges if e["kind"] == "delegates_to"}
    expected = {(a, b) for a, ts in validate_fleet.EXPECTED_DELEGATION.items() for b in ts}
    for missing in sorted(expected - delegation):
        failures.append(f"delegates_to missing in atlas: {missing[0]} -> {missing[1]}")
    for extra in sorted(delegation - expected):
        failures.append(f"delegates_to not enforced by validate_fleet: {extra[0]} -> {extra[1]}")
    guarded = {e["source"].removeprefix("agent:") for e in edges
               if e["kind"] == "constrained_by" and e["target"] == GUARD_ID}
    if guarded != set(adapters.GUARDED_AGENTS):
        failures.append(f"guard roster mismatch: atlas {sorted(guarded)} vs {sorted(adapters.GUARDED_AGENTS)}")
    projections = {n["path"] for n in nodes if n["type"] == "generated-projection"}
    expected_paths = {p.as_posix() for p in adapters.expected_outputs(root)}
    if projections != expected_paths:
        failures.append(f"generated projections differ from expected_outputs by "
                        f"{len(projections ^ expected_paths)} path(s)")
    return failures
