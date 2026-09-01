#!/usr/bin/env python3
"""Contradiction and staleness detectors. Every output is STATIC_INFERRED: a finding, never a fact."""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_stale_names  # noqa: E402
import fleet_atlas_extract  # noqa: E402
import validate_fleet  # noqa: E402
from fleet_atlas import Edge, Graph, Unknown, cite  # noqa: E402
from fleet_atlas_extract import DATE_RE, _cells, edge_id, find_line  # noqa: E402


def _finding(root: Path, graph: Graph, detector: str, source: str, target: str, message: str, path: str, line: int, **attrs) -> None:
    # Both ends of a contradicts edge must be real nodes -- an edge naming a node id that does not
    # exist in this revision's graph is not a finding a consumer can follow, it is a dangling
    # pointer dressed as one. When either end is missing, downgrade to an Unknown that still carries
    # the message and path instead of writing a meaningless edge.
    if source not in graph.nodes or target not in graph.nodes:
        graph.add_unknown(Unknown(f"stale.{detector}-target-missing", message, path,
                                  "Both ends of this finding must resolve to atlas nodes"))
        return
    graph.add_edge(Edge(edge_id("contradicts", source, target, detector), source, target, "contradicts", "STATIC_INFERRED",
                        {"detector": detector, "message": message, **attrs},
                        [cite(root, path, line, line, f"detect.{detector}", "STATIC_INFERRED")]))


def detect_uncited_review(root: Path, graph: Graph) -> None:
    # "cites" and "evidenced_by" are the two edge kinds that already point AT a review: "cites" comes
    # from a review-to-review/decision link (extract_reviews) and, separately, from a roadmap-item or
    # decision linking a review by URL; "evidenced_by" comes from fleet_atlas_extract.link_evidence,
    # which resolves both a markdown link AND a batch id (via check_evidence_refs.BATCH_ID_RE) to the
    # review node carrying that batch. A generated eval-evidence doc is therefore already correctly
    # counted as cited here -- no separate batch-resolution pass is needed in this detector, because
    # link_evidence() ran before this module (fleet_atlas.build_graph calls it, then detect.run).
    incoming = {e.target for e in graph.edges.values() if e.kind in ("cites", "evidenced_by")}
    # Neither link_evidence() nor extract_reviews() scans a live root/docs guide's own body for
    # links -- only roadmap-item, decision, and review sources are walked. But docs/README.md's
    # audit index cites reviews by plain Markdown links, and running this on the real repository
    # found the six 2026-08-24 skill-audit batches were not actually uncited. Scanning the same
    # LIVE_DOCS set fleet_atlas_extract.py already treats as citing authority closes that gap
    # without adding a new extraction pass to that file.
    #
    # Known remaining gap, deliberately not closed here: docs/roadmap-closed.md's disposition rows
    # also cite closure evidence (extract_closed_register() reads the file for historical
    # roadmap-item rows but never calls ensure_document() on the file itself, so it gets no node and
    # link_evidence() never walks it). Adding it to this scan was tried and measured zero effect on
    # this repository's real yield (72 before and after) -- its one relevant citation,
    # docs/reviews/2026-08-25-grader-003-verification-batch.md from the SKILLS-003 row, uses a
    # nested-bracket label ([`[verified]` 62/62 ...](reviews/...)) that check_links.LINK_RE's
    # `\[([^\]]*)\]\(([^)]+)\)` cannot parse at all: the inner `]` from "[verified]" ends the
    # `[^\]]*` capture before the real link boundary, so the match fails regardless of which document
    # contains it. That is a limitation of the shared LINK_RE the whole atlas already depends on, not
    # something this detector's scan set can fix, so docs/roadmap-closed.md was left out rather than
    # added for no measured benefit.
    index = {node.path: node.id for node in graph.nodes.values() if node.path}
    for relative in sorted(fleet_atlas_extract.live_guide_paths(root)):
        path = root / relative
        if not path.is_file():
            continue
        for match in fleet_atlas_extract.LINK_RE.finditer(path.read_text(encoding="utf-8")):
            resolved = fleet_atlas_extract._resolve_link(root, relative, match.group(2))
            target = index.get(resolved) if resolved else None
            if target and target.startswith("review:"):
                incoming.add(target)
    for node in sorted(graph.nodes.values(), key=lambda n: n.id):
        if node.type == "review" and node.id not in incoming:
            graph.add_unknown(Unknown("stale.review-uncited",
                                      f"{node.path} is cited by no roadmap item, decision, review, or live guide",
                                      node.path, "docs/README.md: a review nothing cites is removed, or the citing document is restored"))


def detect_retired_name(root: Path, graph: Graph) -> None:
    # check_stale_names.py's public retired-name collection is the module-level tuple `STALE` (not
    # `RETIRED_NAMES` or `RETIRED` -- neither exists in that module). Its carve-outs are not a plain
    # word-boundary regex: `_filename_exempt_names()` computes, per repository root, which retired
    # names still name a real file in the scanned tree (e.g. `api-design` survives as
    # `skills/backend-craft/references/api-design.md`), and `_hits()`/`_scan_file()` only exempt a
    # match when it sits in path-like position (adjacent to '/' or '.md'). Reimplementing that logic
    # with a bare regex would false-positive on every legitimate link to such a surviving file, so
    # this detector calls the module's own scan primitives directly instead of re-deriving them --
    # the "honour the carve-outs cheaply" the task calls for.
    # Deliberately does not call check_stale_names._scan_file() directly: it formats its message
    # with path.as_posix() on whatever Path it is given, and calling it with the absolute
    # `root / node.path` embeds an absolute filesystem path in the Unknown -- forbidden by this
    # atlas's "no absolute paths" output rule. _hits() takes only a line of text, so calling that
    # instead and formatting the message from node.path (already repo-relative) keeps the real
    # carve-out logic while keeping the output relative. Proven by running with an absolute Path
    # first: the message read "F:/repos/.../agents/sre.md:249: ...".
    exempt = check_stale_names._filename_exempt_names(root)
    seen_paths: set[str] = set()
    for node in sorted(graph.nodes.values(), key=lambda n: n.id):
        if node.authority != "canonical" or not node.path or not node.path.endswith(".md"):
            continue
        if node.path in seen_paths:
            continue
        seen_paths.add(node.path)
        for line_no, line in enumerate((root / node.path).read_text(encoding="utf-8").splitlines(), start=1):
            match = next(check_stale_names._hits(line, exempt), None)
            if match:
                graph.add_unknown(Unknown("stale.retired-name",
                                          f"{node.path}:{line_no}: stale fleet-unit name '{match.group(1)}'",
                                          node.path, "check_stale_names owns the hard failure"))
                break


def detect_superseded_text_present(root: Path, graph: Graph) -> None:
    for edge in sorted(graph.edges.values(), key=lambda e: e.id):
        if edge.kind != "supersedes" or not edge.attrs.get("text"):
            continue
        target = graph.nodes.get(edge.target)
        if not target or not target.path:
            continue
        needle = edge.attrs["text"][:40]
        text = (root / target.path).read_text(encoding="utf-8")
        if needle and needle in text:
            _finding(root, graph, "superseded_text_present", edge.source, edge.target,
                     f"{target.path} still contains superseded text: {needle!r}", target.path,
                     find_line(root, target.path, needle))


def detect_roadmap_evidence_older_than_status(root: Path, graph: Graph) -> None:
    for node in sorted(graph.nodes.values(), key=lambda n: n.id):
        if node.type != "roadmap-item" or node.state != "live" or node.attrs.get("status") != "active":
            continue
        status_date = DATE_RE.search(node.attrs.get("status_text", ""))
        if not status_date:
            continue
        dates = [graph.nodes[e.target].attrs.get("date", "") for e in graph.edges.values()
                 if e.kind == "evidenced_by" and e.source == node.id and e.target in graph.nodes]
        dates = [d for d in dates if d]
        if dates and max(dates) < status_date.group(1):
            graph.add_unknown(Unknown("stale.evidence-predates-status",
                                      f"{node.name} status is dated {status_date.group(1)} but its newest cited evidence is {max(dates)}",
                                      node.path, "Cite the evidence behind the current status or revise the status"))


# detect_rule_source_phrase_missing was cut, not shipped. docs/rules.md's own header says each row
# is "a short statement" -- a human paraphrase of its source, never a verbatim excerpt -- so
# comparing a rule's first three words against the source document word-for-word is comparing two
# independently-worded sentences almost by design. Measured on the real repository: 59 of 88
# governed_by edges (67%) fired, and a 9-finding spot check (the printed samples plus three targeted
# checks -- "single live backlog" vs AGENTS.md's "the only live backlog", "gate a is" vs
# production-change-gate/SKILL.md's "gate authorizes the prod action", "agents prepare and" vs the
# 2026-08-21 ADR containing no such run of words) found 0 true positives: every source document did
# carry the rule's substance, just not that exact three-word run. That is the same failure shape the
# task brief predicted ("a rule row whose statement opens with generic words will false-positive"),
# and it is not a tunable threshold -- word count, stemming, or a stopword filter would all still
# compare paraphrase to paraphrase. Per this task's instruction to cut a detector dominated by one
# systemic, non-actionable pattern rather than ship it, this function and its call in run() were
# removed; scripts/test_fleet_atlas.py no longer carries a test for it (there is no detector left to
# assert fires).


def detect_delegation_mismatch(root: Path, graph: Graph) -> None:
    rows: dict[str, set[str]] = {}
    in_table = False
    line_of: dict[str, int] = {}
    for line_no, line in enumerate((root / "AGENTS.md").read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not in_table:
            in_table = stripped.startswith("|") and "Delegates to" in stripped
            continue
        if not stripped.startswith("|"):
            break
        cells = _cells(stripped)
        if len(cells) < 4 or set(cells[0]) <= set("-: "):
            continue
        agent = cells[0].strip("`")
        rows[agent] = set(re.findall(r"`([a-z0-9-]+)`", cells[-1]))
        line_of[agent] = line_no
    for agent, expected in sorted(validate_fleet.EXPECTED_DELEGATION.items()):
        if agent in rows and rows[agent] != set(expected):
            _finding(root, graph, "delegation_mismatch", f"agent:{agent}", "document:AGENTS.md",
                     f"roster says {agent} delegates to {sorted(rows[agent])}; validate_fleet enforces {sorted(expected)}",
                     "AGENTS.md", line_of[agent])


def run(root: Path, graph: Graph) -> None:
    detect_uncited_review(root, graph)
    detect_retired_name(root, graph)
    detect_superseded_text_present(root, graph)
    detect_roadmap_evidence_older_than_status(root, graph)
    if "document:AGENTS.md" in graph.nodes:
        detect_delegation_mismatch(root, graph)
