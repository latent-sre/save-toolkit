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


import check_plan_status  # noqa: E402
from check_links import _relative_target  # noqa: E402

LIVE_DOCS = {
    "AGENTS.md", "CONTRIBUTING.md", "README.md", "docs/README.md", "docs/rules.md",
    "docs/schema-compatibility.md", "docs/fleet-roadmap.md",
}
DATE_RE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
SUPERSEDES_RE = re.compile(r"\*\*Supersedes:?\*\*:?\s*(.+)|^-?\s*Supersedes:\s*(.+)", re.IGNORECASE)
DISPOSES_RE = re.compile(r"disposes\s+`([A-Z][A-Z0-9]*-\d{3})`")
BACKTICK_ID_RE = re.compile(r"`([A-Z][A-Z0-9]*-\d{3})`")
# check_plan_status._status_state tolerates a qualified marker ("accepted 2026-08-22", "superseded
# 2026-08-23 by explicit owner disposition") -- it only ever strips at the punctuation that starts
# the qualifier, not the marker word itself. A bare dict lookup on that value misses every qualified
# ADR in this repository (4 of the 5 "accepted ..." decisions carry a trailing date or clause), so
# state resolution mirrors check_plan_status.check()'s own decision-marker tolerance: exact word or
# "word " prefix.
DECISION_STATE_BY_MARKER = {
    "accepted": "live", "proposed": "proposed", "superseded": "historical",
    "rejected": "rejected", "deprecated": "deprecated",
}


def _decision_state(marker: str) -> str:
    for word, state in DECISION_STATE_BY_MARKER.items():
        if marker == word or marker.startswith(f"{word} "):
            return state
    return "historical"


def node_for_path(graph: Graph, relative: str) -> str | None:
    for node in graph.nodes.values():
        if node.path == relative:
            return node.id
    return None


def ensure_document(root: Path, graph: Graph, relative: str) -> str:
    existing = node_for_path(graph, relative)
    if existing:
        return existing
    if relative.startswith("scripts/") and relative.endswith(".py"):
        node_id, node_type, authority = f"validator:{relative}", "validator", "canonical"
    else:
        node_id, node_type = f"document:{relative}", "document"
        authority = ("live-contract" if relative in LIVE_DOCS
                     else "historical-evidence" if relative.startswith("docs/") else "canonical")
    graph.add_node(Node(node_id, node_type, relative, authority, relative, "live", {},
                        [cite(root, relative, 1, 1, "extract.document", "STATIC_EXTRACTED")]))
    return node_id


def _resolve_link(root: Path, base: str, raw_target: str) -> str | None:
    target = _relative_target(raw_target)
    if target is None:
        return None
    candidate = (root / base).parent / target
    try:
        relative = candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    return relative if (root / relative).is_file() else None


def extract_documents(root: Path, graph: Graph) -> None:
    for relative in sorted(LIVE_DOCS):
        if (root / relative).is_file():
            ensure_document(root, graph, relative)


def extract_rules(root: Path, graph: Graph) -> None:
    relative = "docs/rules.md"
    section = ""
    for line_no, line in enumerate((root / relative).read_text(encoding="utf-8").splitlines(), start=1):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("| ") or line.startswith("| Rule") or SEPARATOR_RE.match(line):
            continue
        cells = _cells(line)
        if len(cells) < 2:
            continue
        statement, source_cell = _plain(cells[0]), cells[1]
        rule_id = stable_id("rule", relative, statement)
        graph.add_node(Node(rule_id, "rule", statement[:80], "live-contract", relative, "live",
                            {"section": section, "statement": statement, "source_text": _plain(source_cell)},
                            [cite(root, relative, line_no, line_no, "extract.rules-row", "STATIC_EXTRACTED")]))
        links = [m.group(2) for m in LINK_RE.finditer(source_cell)]
        if not links:
            graph.add_unknown(Unknown("extract.rule-source-unlinked",
                                      f"{relative}:{line_no} names its source in prose only: {_plain(source_cell)[:80]}",
                                      relative, "Link the primary source so the rule can be traced"))
            continue
        for raw in links:
            resolved = _resolve_link(root, relative, raw)
            if resolved is None:
                graph.add_unknown(Unknown("extract.rule-source-missing",
                                          f"{relative}:{line_no} links {raw}, which does not resolve",
                                          relative, "check_links owns the hard failure; fix the link"))
                continue
            target = ensure_document(root, graph, resolved)
            graph.add_edge(Edge(edge_id("governed_by", rule_id, target), rule_id, target, "governed_by",
                                "STATIC_EXTRACTED", {},
                                [cite(root, relative, line_no, line_no, "extract.rules-row", "STATIC_EXTRACTED")]))


def extract_roadmap(root: Path, graph: Graph) -> None:
    relative = "docs/fleet-roadmap.md"
    text = (root / relative).read_text(encoding="utf-8")
    items = check_plan_status._roadmap_items(text)
    known = {item["id"] for item in items}
    for item in items:
        fields = dict(item["fields"])
        status_text = fields.get("Status", "")
        graph.add_node(Node(f"roadmap-item:{item['id']}", "roadmap-item", item["id"], "live-contract",
                            relative, "live",
                            {"status": check_plan_status._status_state(status_text) if status_text else "",
                             "status_text": status_text[:200], "owner": fields.get("Owner", "")[:200],
                             "fields": sorted(fields)},
                            [cite(root, relative, item["line"], item["line"], "check_plan_status.roadmap_item",
                                  "CONTRACT_RESOLVED")]))
    for item in items:
        source = f"roadmap-item:{item['id']}"
        fields = dict(item["fields"])
        for field_name, value in sorted(fields.items()):
            for dep in sorted(set(check_plan_status.ROADMAP_ITEM_ID_RE.findall(value))):
                if dep == item["id"] or dep not in known:
                    continue
                contract = field_name == "Prerequisites"
                graph.add_edge(Edge(edge_id("depends_on", source, f"roadmap-item:{dep}", field_name), source,
                                    f"roadmap-item:{dep}", "depends_on",
                                    "CONTRACT_RESOLVED" if contract else "STATIC_INFERRED",
                                    {"field": field_name,
                                     "detector": "check_plan_status.prerequisites" if contract else "extract.roadmap-mention"},
                                    [cite(root, relative, item["line"], item["line"],
                                          "check_plan_status.prerequisites" if contract else "extract.roadmap-mention",
                                          "CONTRACT_RESOLVED" if contract else "STATIC_INFERRED")]))


def extract_closed_register(root: Path, graph: Graph) -> None:
    relative = "docs/roadmap-closed.md"
    if not (root / relative).is_file():
        return
    for line_no, line in enumerate((root / relative).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.startswith("| `") or SEPARATOR_RE.match(line):
            continue
        cells = _cells(line)
        if len(cells) < 3:
            continue
        for item_id in BACKTICK_ID_RE.findall(cells[0]):
            node_id = f"roadmap-item:{item_id}"
            if node_id in graph.nodes:
                continue
            graph.add_node(Node(node_id, "roadmap-item", item_id, "historical-evidence", relative, "historical",
                                {"closed": cells[1], "disposition": _plain(cells[2])[:200]},
                                [cite(root, relative, line_no, line_no, "extract.closed-register-row",
                                      "STATIC_EXTRACTED")]))


def extract_decisions(root: Path, graph: Graph) -> None:
    for path in sorted((root / "docs/decisions").glob("*.md")):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        head = "\n".join(text.splitlines()[:14])
        status_value = check_plan_status._status_value(text, lines=14) or ""
        marker = check_plan_status._status_state(status_value) if status_value else ""
        state = _decision_state(marker) if marker else "historical"
        date = DATE_RE.search(head)
        node_id = f"decision:{path.stem}"
        graph.add_node(Node(node_id, "decision", path.stem,
                            "live-contract" if state == "live" else "historical-evidence", relative, state,
                            {"date": date.group(1) if date else "", "status_text": status_value[:200]},
                            [cite(root, relative, 1, 1, "extract.decision-status", "STATIC_EXTRACTED")]))
        for item_id in DISPOSES_RE.findall(head):
            target = f"roadmap-item:{item_id}"
            if target in graph.nodes:
                line = find_line(root, relative, f"disposes `{item_id}`")
                graph.add_edge(Edge(edge_id("supersedes", node_id, target, "disposes"), node_id, target, "supersedes",
                                    "STATIC_EXTRACTED", {"relation": "disposes"},
                                    [cite(root, relative, line, line, "extract.decision-disposes", "STATIC_EXTRACTED")]))
        for line_no, line in enumerate(text.splitlines()[:14], start=1):
            match = SUPERSEDES_RE.search(line)
            if not match:
                continue
            prose = (match.group(1) or match.group(2) or "").strip()
            # Deliberately scans ONLY the matched line. A continuation line is not evidence of a
            # target: 2026-08-26-retire-verification-sandbox.md wraps to a link it names in order
            # to say that document is *not* superseded, and a proximity rule reads that backwards.
            # Prose supersession stays UNKNOWN with its text preserved; resolving it needs a
            # structured target field in the ADR convention, not a cleverer scan here.
            resolved = None
            for raw in [m.group(2) for m in LINK_RE.finditer(line)]:
                resolved = _resolve_link(root, relative, raw) or resolved
            if resolved:
                target = ensure_document(root, graph, resolved)
                graph.add_edge(Edge(edge_id("supersedes", node_id, target), node_id, target, "supersedes",
                                    "STATIC_EXTRACTED", {"relation": "supersedes", "text": prose[:200]},
                                    [cite(root, relative, line_no, line_no, "extract.decision-supersedes",
                                          "STATIC_EXTRACTED")]))
            else:
                graph.add_unknown(Unknown("extract.supersedes-unresolved",
                                          f"{relative}:{line_no} supersedes '{prose[:120]}' but names no linked target",
                                          relative, "Link the superseded decision, rule row, or document"))
