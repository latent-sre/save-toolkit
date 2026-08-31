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
    # Resolve dependencies against CLOSED items too, not just live ones. A live item routinely
    # depends on something that has since closed -- GRAPH-003 waited on GRAPH-002, which closed
    # when PR #193 was accepted -- and that is exactly the relationship an operator asks about
    # ("is this unblocked now?"). Restricting to live ids dropped the edge silently, which is a
    # worse answer than saying "depends_on GRAPH-002 (historical)". The closed nodes are created
    # later by extract_closed_register; an edge may name a target that appears after it, which the
    # graph permits.
    closed_text = (root / "docs/roadmap-closed.md").read_text(encoding="utf-8") if (root / "docs/roadmap-closed.md").is_file() else ""
    known = {item["id"] for item in items} | set(BACKTICK_ID_RE.findall(closed_text))
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


import json  # noqa: E402
from check_evidence_refs import BATCH_ID_RE  # noqa: E402

EVAL_DOC_RE = re.compile(r"-eval-(\d{8}T\d{6}Z-[0-9a-f]{8})\.md$")
LITERAL_RE = re.compile(r"[\"']((?:agents|skills|docs|evals|commands|hooks|schemas|scripts)/[A-Za-z0-9._/-]+)[\"']")
LANE_SLUG_RE = re.compile(r"[^a-z0-9]+")
_yaml_unavailable_reported = False


def _path_index(graph: Graph) -> dict[str, str]:
    return {node.path: node.id for node in graph.nodes.values() if node.path}


def extract_reviews(root: Path, graph: Graph) -> None:
    for path in sorted((root / "docs/reviews").glob("*.md")):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        head = "\n".join(text.splitlines()[:8])
        batch = EVAL_DOC_RE.search(path.name)
        date = DATE_RE.match(path.name)
        attrs = {"date": date.group(1) if date else "", "banner": "Status" in head,
                 "batches": sorted(set(BATCH_ID_RE.findall(text)))}
        if batch:
            attrs["batch"] = batch.group(1)
        graph.add_node(Node(f"review:{path.stem}", "review", path.stem,
                            "generated" if batch else "historical-evidence", relative,
                            "generated" if batch else "historical", attrs,
                            [cite(root, relative, 1, 1, "extract.review", "STATIC_EXTRACTED")]))
    index = _path_index(graph)
    for node in [n for n in graph.nodes.values() if n.type == "review"]:
        for line_no, line in enumerate((root / node.path).read_text(encoding="utf-8").splitlines(), start=1):
            for match in LINK_RE.finditer(line):
                resolved = _resolve_link(root, node.path, match.group(2))
                target = index.get(resolved) if resolved else None
                if target and target != node.id:
                    graph.add_edge(Edge(edge_id("cites", node.id, target, str(line_no)), node.id, target, "cites",
                                        "STATIC_EXTRACTED", {},
                                        [cite(root, node.path, line_no, line_no, "extract.review-link", "STATIC_EXTRACTED")]))


def extract_scenarios(root: Path, graph: Graph) -> None:
    global _yaml_unavailable_reported
    try:
        import yaml
    except ImportError:
        if not _yaml_unavailable_reported:
            graph.add_unknown(Unknown("extract.yaml-unavailable", "PyYAML is not installed; scenarios were not extracted",
                                      "evals/scenarios", "pip install -r requirements-dev.txt"))
            _yaml_unavailable_reported = True
        return
    paths = sorted((root / "evals/scenarios").glob("*.yaml")) + sorted((root / "evals/build-scenarios").glob("*.yaml"))
    for path in paths:
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if not isinstance(data, dict) or "id" not in data:
            graph.add_unknown(Unknown("extract.scenario-unparsed", f"{relative} has no id", relative, "run_evals --validate owns this"))
            continue
        routing = data.get("routing") or {}
        alternative = routing.get("expected_alternative")
        node_id = f"scenario:{data['id']}"
        graph.add_node(Node(node_id, "scenario", str(data["id"]), "live-contract", relative, "live",
                            {"mode": data.get("mode", ""), "split": data.get("split", ""),
                             "expect": routing.get("expect", ""), "threshold": data.get("threshold"),
                             "expected_alternative": alternative if isinstance(alternative, str) else
                             (f"{alternative.get('kind')}:{alternative.get('name')}" if isinstance(alternative, dict) else ""),
                             "file": relative},
                            [cite(root, relative, 1, 1, "extract.scenario", "STATIC_EXTRACTED")]))
        target = data.get("target") or {}
        # evals/build-scenarios/*.yaml carries no "target: {kind, name}" mapping -- it names its
        # single agent directly as a bare "agent: <name>" scalar (build-software-engineer-*.yaml,
        # build-sre-*.yaml, ...). Falling through to "None:None" there is not an unresolved
        # reference to report; it is reading the wrong field of a file whose shape this branch
        # never checked. Treat "agent:" as the direct-mode target when "target:" is absent.
        if target:
            target_id = f"{target.get('kind')}:{target.get('name')}"
            line = find_line(root, relative, "target:")
        elif isinstance(data.get("agent"), str) and data["agent"]:
            target_id = f"agent:{data['agent']}"
            line = find_line(root, relative, "agent:")
        else:
            target_id = "None:None"
            line = 1
        if target_id not in graph.nodes:
            graph.add_unknown(Unknown("extract.scenario-target-missing", f"{relative} targets {target_id}, which has no node",
                                      relative, "Retarget the scenario or restore the component"))
        elif routing.get("expect") == "not_fire":
            graph.add_edge(Edge(edge_id("near_miss_for", node_id, target_id), node_id, target_id, "near_miss_for",
                                "STATIC_EXTRACTED", {"expected_alternative": graph.nodes[node_id].attrs["expected_alternative"]},
                                [cite(root, relative, line, line, "extract.scenario-routing", "STATIC_EXTRACTED")]))
            if isinstance(alternative, dict):
                alt_id = f"{alternative.get('kind')}:{alternative.get('name')}"
                if alt_id in graph.nodes:
                    graph.add_edge(Edge(edge_id("routes_to", node_id, alt_id), node_id, alt_id, "routes_to",
                                        "STATIC_EXTRACTED", {"via": "expected_alternative"}, []))
        else:
            graph.add_edge(Edge(edge_id("verified_by", target_id, node_id), target_id, node_id, "verified_by",
                                "STATIC_EXTRACTED", {"mode": data.get("mode", "")},
                                [cite(root, relative, line, line, "extract.scenario-target", "STATIC_EXTRACTED")]))
        for item_id in sorted(set(check_plan_status.ROADMAP_ITEM_ID_RE.findall(text))):
            if f"roadmap-item:{item_id}" in graph.nodes:
                graph.add_edge(Edge(edge_id("cites", node_id, f"roadmap-item:{item_id}"), node_id,
                                    f"roadmap-item:{item_id}", "cites", "STATIC_INFERRED", {"via": "comment"}, []))


def extract_tests(root: Path, graph: Graph) -> None:
    index = _path_index(graph)
    for path in sorted((root / "scripts").glob("test_*.py")) + sorted((root / "evals").glob("test_*.py")):
        relative = path.relative_to(root).as_posix()
        node_id = f"test:{relative}"
        graph.add_node(Node(node_id, "test", relative, "canonical", relative, "live", {},
                            [cite(root, relative, 1, 1, "extract.test-file", "STATIC_EXTRACTED")]))
        # Deduplicate per (target, node_id): the same literal path is often quoted on multiple
        # lines within one test file (e.g. a fixture read several times), and edge_id() below does
        # not fold in the line number, so a second occurrence would collide with the first edge's
        # id. Recording the first citing line is sufficient -- the claim is "this test reads that
        # path", not "on every one of these lines".
        seen: set[str] = set()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for literal in LITERAL_RE.findall(line):
                target = index.get(literal)
                if target:
                    if target in seen:
                        continue
                    seen.add(target)
                    graph.add_edge(Edge(edge_id("verified_by", target, node_id), target, node_id, "verified_by",
                                        "STATIC_EXTRACTED", {"via": "string-literal"},
                                        [cite(root, relative, line_no, line_no, "extract.test-literal", "STATIC_EXTRACTED")]))
                # A literal resolving to no node is deliberately not reported. It cannot be told
                # apart statically from a synthetic fixture path: these suites build temp
                # repositories containing skills/thing/scripts/converter.py and
                # skills/incident-command/references/severity.md, which exist only inside a
                # TemporaryDirectory. Reporting them as stale produced 143 findings with no true
                # positive, which would bury real contradictions in the stale-evidence view.
                # Telling a stale pin from a fixture needs scope analysis this extractor does not
                # do, so the honest output is the pin edges alone.


def extract_schemas(root: Path, graph: Graph) -> None:
    catalog = json.loads((root / "schemas/catalog-v1.json").read_text(encoding="utf-8"))
    for entry in catalog["schemas"]:
        node_id = f"schema:{entry['id']}"
        line = find_line(root, "schemas/catalog-v1.json", f"\"{entry['id']}\"")
        graph.add_node(Node(node_id, "schema", entry["id"], "live-contract", entry["canonical_path"], "live",
                            {"status": entry["status"], "version": entry["version"]},
                            [cite(root, "schemas/catalog-v1.json", line, line, "extract.catalog-entry", "CONTRACT_RESOLVED")]))
        if entry.get("validator"):
            validator = ensure_document(root, graph, entry["validator"])
            graph.add_edge(Edge(edge_id("constrained_by", node_id, validator), node_id, validator, "constrained_by",
                                "CONTRACT_RESOLVED", {"via": "catalog-v1.json"}, []))
        for projection in entry.get("generated_projections", []):
            # Deviates from the plan snippet on purpose, for three compounding reasons discovered
            # by running the suite, not guessed:
            #  1. schemas/fleet-atlas-v1.schema.json's own Node.type enum is closed (agent, skill,
            #     reference, bundle-file, command, rule, decision, roadmap-item, review, scenario,
            #     test, schema, generated-projection, capability, owner, probe, hook, document,
            #     validator) and has no "schema-projection" or other free-form slot; inventing one
            #     would make snapshot() emit atlas.json that fails its own committed schema.
            #  2. Reusing type "generated-projection" for a schema-declared projection instead
            #     collides with CitedContractTests.test_every_generated_output_has_exactly_one_
            #     generated_from_edge and fleet_atlas_cite.parity_failures(), which both audit that
            #     type, and the "generated_from" edge kind, as EXACTLY
            #     generate_platform_adapters.expected_outputs() -- proven by running both fixes and
            #     watching each break that test in a different way.
            #  3. The one non-empty entry today, fleet-atlas-v1, declares
            #     docs/fleet-atlas/generated/atlas.json -- the atlas's own build output, which this
            #     task's constraints forbid writing or committing, and cite() (used by every node
            #     constructor here) reads the file it cites, so fabricating a node for a path that
            #     may not exist on disk would crash extraction on a checkout where Task 7 has not
            #     run `fleet_atlas.py build` yet.
            # None of those three are satisfied by minting a node, so an unresolved projection is
            # exactly what the rest of this file calls an Unknown carrying its text: this schema
            # declares a projection this atlas revision has no node for yet. If a future catalog
            # entry's generated_projections happens to name a path some earlier extractor already
            # gave a node (checked by path, not assumed), wire the real edge instead of guessing one.
            target = node_for_path(graph, projection)
            if target is None:
                graph.add_unknown(Unknown(
                    "extract.schema-projection-unresolved",
                    f"{entry['id']} declares generated_projections {projection}, which has no node yet",
                    entry["canonical_path"],
                    "Build the projection, or extract the node that would represent it, before citing it",
                ))
                continue
            graph.add_edge(Edge(edge_id("constrained_by", target, node_id), target, node_id, "constrained_by",
                                "CONTRACT_RESOLVED", {"via": "catalog-v1.json"}, []))


def extract_probes(root: Path, graph: Graph) -> None:
    roadmap = (root / "docs/fleet-roadmap.md").read_text(encoding="utf-8")
    for path in sorted((root / "docs/probes").glob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        linked = path.name in roadmap
        graph.add_node(Node(f"probe:{path.stem}", "probe", path.stem,
                            "live-contract" if linked else "historical-evidence", relative,
                            "live" if linked else "historical", {"linked_from_roadmap": linked}, []))


def extract_owners(root: Path, graph: Graph) -> None:
    agents = {n.name for n in graph.nodes.values() if n.type == "agent"}
    for agent in sorted(agents):
        graph.add_node(Node(f"owner:{agent}", "owner", agent, "canonical", f"agents/{agent}.md", "live", {"kind": "agent"}, []))
    text = (root / "docs/fleet-roadmap.md").read_text(encoding="utf-8")
    for item in check_plan_status._roadmap_items(text):
        owner_field = str(item["fields"].get("Owner", ""))
        # An Owner field names owners, but it also mentions components in passing ("`agent-engineer`
        # owns the `fleet-atlas` skill text"). A backticked name matching a skill or command is a
        # component reference, not an owner, and typing it "human" invents a person: `runbook` and
        # `stack-profile` were both classified as humans before this filter. A name that is neither
        # an agent nor a known component is treated as human, which is the only remaining reading.
        components = {node.name for node in graph.nodes.values() if node.type in ("skill", "command")}
        owner_mentions = {
            match.group(1): owner_field[match.end() :].lstrip()
            for match in re.finditer(r"`([a-z][a-z0-9-]+)`", owner_field)
        }
        for name, suffix in sorted(owner_mentions.items()):
            if name in components and name not in agents:
                continue
            if name not in agents and re.match(r"(?:skill|command)\b", suffix):
                continue
            if name not in agents and f"owner:{name}" not in graph.nodes:
                graph.add_node(Node(f"owner:{name}", "owner", name, "external", None, "live", {"kind": "human"}, []))
            if f"owner:{name}" in graph.nodes:
                graph.add_edge(Edge(edge_id("owns", f"owner:{name}", f"roadmap-item:{item['id']}"), f"owner:{name}",
                                    f"roadmap-item:{item['id']}", "owns", "STATIC_EXTRACTED", {"field": "Owner"},
                                    [cite(root, "docs/fleet-roadmap.md", item["line"], item["line"], "extract.roadmap-owner",
                                          "STATIC_EXTRACTED")]))
    in_table = False
    for line_no, line in enumerate((root / "AGENTS.md").read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not in_table:
            in_table = stripped.startswith("|") and "Delegates to" in stripped
            continue
        if not stripped.startswith("|"):
            break
        if SEPARATOR_RE.match(stripped):
            continue
        cells = _cells(stripped)
        agent = cells[0].strip("`")
        if agent in agents and len(cells) >= 2:
            lane = _plain(cells[1])
            slug = LANE_SLUG_RE.sub("-", lane.lower()).strip("-")[:60]
            cap_id = f"capability:{slug}"
            if cap_id not in graph.nodes:
                graph.add_node(Node(cap_id, "capability", lane, "canonical", "AGENTS.md", "live", {"lane": lane},
                                    [cite(root, "AGENTS.md", line_no, line_no, "extract.roster-lane", "STATIC_INFERRED")]))
            graph.add_edge(Edge(edge_id("owns", f"agent:{agent}", cap_id), f"agent:{agent}", cap_id, "owns", "STATIC_INFERRED",
                                {"via": "roster-lane"},
                                [cite(root, "AGENTS.md", line_no, line_no, "extract.roster-lane", "STATIC_INFERRED")]))


def link_evidence(root: Path, graph: Graph) -> None:
    index = _path_index(graph)
    by_batch: dict[str, str] = {}
    for node in graph.nodes.values():
        if node.type == "review":
            for batch in node.attrs.get("batches", []):
                by_batch.setdefault(batch, node.id)
    sources = [n for n in graph.nodes.values() if n.type in ("roadmap-item", "decision") and n.path]
    for node in sources:
        text = (root / node.path).read_text(encoding="utf-8")
        lines = text.splitlines()
        if node.type == "roadmap-item":
            start = int(node.evidence[0].lines[0]) if node.evidence else 1
            # node.evidence[0].lines[0] is the 1-based line number of the "### ITEM-ID" heading
            # itself (extract_roadmap cites exactly that line). The item's own content starts on
            # the NEXT line, so the search for the next heading -- and the span handed to the
            # second loop below, which treats each value as a 1-based line number -- both begin at
            # start + 1. Using `start` unshifted here included the heading line in the span and
            # searched for the terminator one line too early; off by one, though not one that
            # happens to change any assertion in this file, since no evidence link in this
            # repository's roadmap items sits on the heading line itself.
            end = next((i for i in range(start, len(lines)) if lines[i].startswith("### ")), len(lines))
            span = range(start + 1, end + 1)
        else:
            span = range(1, len(lines) + 1)
        # Two separately-typed sets, not one mixed set: a link-derived hit dedupes by target alone
        # (edge_id() for the link case has no batch key, so a second link to the same review would
        # collide), while a batch-derived hit dedupes by (target, batch) (edge_id() there includes
        # the batch, so two different batches resolving to the same review are two real edges).
        # Keeping them as separate sets makes each dedup key explicit instead of relying on tuples
        # and strings never colliding by accident.
        seen_links: set[str] = set()
        seen_batches: set[tuple[str, str]] = set()
        for line_no in span:
            line = lines[line_no - 1] if line_no - 1 < len(lines) else ""
            for match in LINK_RE.finditer(line):
                resolved = _resolve_link(root, node.path, match.group(2))
                target = index.get(resolved) if resolved else None
                if target and target.startswith(("review:", "decision:")) and target != node.id and target not in seen_links:
                    seen_links.add(target)
                    graph.add_edge(Edge(edge_id("evidenced_by", node.id, target), node.id, target, "evidenced_by",
                                        "STATIC_EXTRACTED", {},
                                        [cite(root, node.path, line_no, line_no, "extract.evidence-link", "STATIC_EXTRACTED")]))
            for batch in BATCH_ID_RE.findall(line):
                target = by_batch.get(batch)
                if target is None:
                    # check_evidence_refs.check() only requires a durable review for batches cited
                    # in docs/fleet-roadmap.md (its `cited` set comes solely from ROADMAP text) --
                    # it never reads docs/decisions/*.md. A decision may cite a batch as inline
                    # evidence the ADR itself is the durable record of (e.g.
                    # 2026-08-22-agent-discovery-calibration.md:29-35 cites five batches with no
                    # separate review file, and that is not a gap check_evidence_refs would ever
                    # flag). Reporting it as extract.batch-unresolved here would assert a contract
                    # the cited detector does not enforce, so this Unknown is scoped to the node
                    # type check_evidence_refs actually reads.
                    if node.type == "roadmap-item":
                        graph.add_unknown(Unknown("extract.batch-unresolved", f"{node.path}:{line_no} cites batch {batch} with no review",
                                                  node.path, "check_evidence_refs owns the hard failure"))
                elif (target, batch) not in seen_batches:
                    seen_batches.add((target, batch))
                    graph.add_edge(Edge(edge_id("evidenced_by", node.id, target, batch), node.id, target, "evidenced_by",
                                        "STATIC_EXTRACTED", {"batch": batch},
                                        [cite(root, node.path, line_no, line_no, "extract.evidence-batch", "STATIC_EXTRACTED")]))
