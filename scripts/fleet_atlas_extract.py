#!/usr/bin/env python3
"""Extract atlas nodes and edges from canonical fleet files. Pure functions of a repository root."""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fleet_atlas  # noqa: E402
import fleet_frontmatter  # noqa: E402
from check_links import LINK_RE  # noqa: E402
from fleet_atlas import Edge, Graph, Node, Unknown, cite, stable_id  # noqa: E402

GRANT_RE = re.compile(r"Agent\(([^)]+)\)")
SEPARATOR_RE = re.compile(r"^\|\s*:?-{3,}")
REFERENCE_LINK_RE = re.compile(r"\]\((?:\./)?references/([A-Za-z0-9._/-]+\.md)\)")
BUNDLE_DIRS = ("scripts", "assets", "templates")


def find_line(root: Path, relative: str, needle: str, default: int = 1) -> int:
    for number, line in enumerate((root / relative).read_text(encoding="utf-8").splitlines(), start=1):
        if needle in line:
            return number
    return default


def edge_id(kind: str, source: str, target: str, key: str = "") -> str:
    return stable_id("edge", kind, source, target, key)


def _frontmatter(path: Path):
    return fleet_frontmatter.parse_file(path, mode="lenient")


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _plain(cell: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cell)
    return " ".join(text.replace("`", "").replace("**", "").split())


def routing_rows(body: str) -> list[tuple[int, str, list[str]]]:
    lines = body.splitlines()
    rows: list[tuple[int, str, list[str]]] = []
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|") or SEPARATOR_RE.match(line.strip()):
            continue
        if index + 1 < len(lines) and SEPARATOR_RE.match(lines[index + 1].strip()):
            continue  # header row
        targets = REFERENCE_LINK_RE.findall(line)
        if targets:
            rows.append((index + 1, _plain(_cells(line)[0]), targets))
    return rows


def extract_agents(root: Path, graph: Graph) -> None:
    for path in sorted((root / "agents").glob("*.md")):
        relative = path.relative_to(root).as_posix()
        parsed = _frontmatter(path)
        tools = parsed.fields.get("tools", [])
        tools_text = " ".join(tools) if isinstance(tools, list) else str(tools)
        grants: set[str] = set()
        for match in GRANT_RE.finditer(tools_text):
            grants.update(item.strip() for item in match.group(1).split(",") if item.strip())
        graph.add_node(Node(
            id=f"agent:{path.stem}", type="agent", name=path.stem, authority="canonical",
            path=relative, state="live",
            attrs={
                "description": str(parsed.fields.get("description", "")),
                "tools": tools if isinstance(tools, list) else [str(tools)],
                "grants": sorted(grants),
            },
            evidence=[cite(root, relative, 1, find_line(root, relative, "---", 1) or 1,
                           "extract.agent-frontmatter", "STATIC_EXTRACTED")],
        ))


def extract_skills(root: Path, graph: Graph) -> None:
    for skill_md in sorted((root / "skills").glob("*/SKILL.md")):
        skill_dir = skill_md.parent
        name = skill_dir.name
        relative = skill_md.relative_to(root).as_posix()
        parsed = _frontmatter(skill_md)
        skill_id = f"skill:{name}"
        graph.add_node(Node(
            id=skill_id, type="skill", name=name, authority="canonical", path=relative, state="live",
            attrs={
                "description": str(parsed.fields.get("description", "")),
                "manual_only": str(parsed.fields.get("disable-model-invocation", "")).lower() == "true",
                "bytes": skill_md.stat().st_size,
            },
            evidence=[cite(root, relative, 1, 1, "extract.skill-frontmatter", "STATIC_EXTRACTED")],
        ))
        for reference in sorted((skill_dir / "references").glob("*.md")) if (skill_dir / "references").is_dir() else []:
            graph.add_node(Node(
                id=f"reference:{name}/{reference.name}", type="reference",
                name=f"{name}/{reference.name}", authority="canonical",
                path=reference.relative_to(root).as_posix(), state="live",
                attrs={"skill": name, "bytes": reference.stat().st_size},
                evidence=[cite(root, reference.relative_to(root).as_posix(), 1, 1,
                               "extract.reference-file", "STATIC_EXTRACTED")],
            ))
        for bundle_dir in BUNDLE_DIRS:
            for item in sorted((skill_dir / bundle_dir).rglob("*")) if (skill_dir / bundle_dir).is_dir() else []:
                if item.is_file():
                    rel = item.relative_to(skill_dir).as_posix()
                    node_id = f"bundle-file:{name}/{rel}"
                    graph.add_node(Node(
                        id=node_id, type="bundle-file", name=f"{name}/{rel}", authority="canonical",
                        path=item.relative_to(root).as_posix(), state="live", attrs={"skill": name},
                    ))
                    graph.add_edge(Edge(edge_id("cites", skill_id, node_id), skill_id, node_id, "cites",
                                        "STATIC_EXTRACTED", {}, []))
        # A skill may also carry a file directly in its own directory (context-requirements.yaml).
        # It is canonical and it is projected, so it needs a node of its own; without one, its
        # generated projection can only cite the skill, which is not the file it derives from.
        for item in sorted(skill_dir.iterdir()):
            if item.is_file() and item.name != "SKILL.md":
                rel = item.name
                node_id = f"bundle-file:{name}/{rel}"
                graph.add_node(Node(
                    id=node_id, type="bundle-file", name=f"{name}/{rel}", authority="canonical",
                    path=item.relative_to(root).as_posix(), state="live", attrs={"skill": name},
                ))
                graph.add_edge(Edge(edge_id("cites", skill_id, node_id), skill_id, node_id, "cites",
                                    "STATIC_EXTRACTED", {}, []))
        full_text = skill_md.read_text(encoding="utf-8")
        body_offset = full_text.count("\n", 0, full_text.find(parsed.body))
        seen: set[tuple[str, str]] = set()
        for line_no, predicate, targets in routing_rows(parsed.body):
            for target in targets:
                _reference_edge(root, graph, skill_id, name, target, predicate, relative,
                                body_offset + line_no, seen)
        for line_no, line in enumerate(parsed.body.splitlines(), start=1):
            for target in REFERENCE_LINK_RE.findall(line):
                if target not in {seen_target for seen_target, _ in seen}:
                    _reference_edge(root, graph, skill_id, name, target, "UNKNOWN", relative,
                                    body_offset + line_no, seen)


def _reference_edge(root, graph, skill_id, skill, target, predicate, relative, line_no, seen) -> None:
    key = (target, predicate)
    if key in seen:
        return
    seen.add(key)
    node_id = f"reference:{skill}/{target}"
    if node_id not in graph.nodes:
        graph.add_unknown(Unknown(
            "extract.skill-link-unresolved",
            f"{relative}:{line_no} links references/{target}, which does not exist",
            relative, "Restore the file or remove the link; check_links owns the hard failure",
        ))
        return
    evidence = cite(root, relative, line_no, line_no, "extract.skill-routing-row"
                    if predicate != "UNKNOWN" else "extract.skill-plain-link", "STATIC_EXTRACTED")
    graph.add_edge(Edge(edge_id("loads_when", skill_id, node_id, predicate), skill_id, node_id,
                        "loads_when", "STATIC_EXTRACTED", {"predicate": predicate}, [evidence]))


def extract_commands(root: Path, graph: Graph) -> None:
    for path in sorted((root / "commands").glob("*.md")):
        relative = path.relative_to(root).as_posix()
        parsed = _frontmatter(path)
        graph.add_node(Node(
            id=f"command:{path.stem}", type="command", name=path.stem, authority="canonical",
            path=relative, state="live",
            attrs={
                "description": str(parsed.fields.get("description", "")),
                "argument_hint": str(parsed.fields.get("argument-hint", "")),
                "manual_only": str(parsed.fields.get("disable-model-invocation", "")).lower() == "true",
            },
            evidence=[cite(root, relative, 1, 1, "extract.command-frontmatter", "STATIC_EXTRACTED")],
        ))
