"""Build, verify and query the revision-bound fleet documentation/knowledge atlas."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

# Isolated Python (-I -S) deliberately omits the script directory. Only this
# explicitly selected, source-bound implementation directory is added back.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fleet_atlas_v2_artifacts import ArtifactDrift, VerifiedDocument, build, extraction, verify
from fleet_atlas_v2_format import bounded_envelope, fact_record, graph_dict
from fleet_atlas_v2_model import Fact, canonical_bytes

ROOT = Path(__file__).resolve().parents[1]
VERBS = ("governs", "owner-of", "loads-for", "supersedes", "depends-on", "blocks",
         "verified-by", "evidence-for", "generated-from", "state", "impact", "guidance")
RELATION = {
    "governs": "governed_by", "owner-of": "owns", "loads-for": "loads_when",
    "supersedes": "supersedes", "depends-on": "depends_on", "blocks": "depends_on",
    "verified-by": "verified_by", "evidence-for": "evidenced_by", "generated-from": "generated_from",
}
# Verbs whose term matches the relation's object rather than its subject.
REVERSED = frozenset({"blocks", "owner-of"})
# Verbs that accept several terms; every other verb takes exactly one quoted term.
MULTI_TERM = frozenset({"guidance", "loads-for", "governs", "state"})
TERM_BYTES = 2048


class UsageError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def _validate_terms(verb: str, terms: list[str]) -> None:
    """The one usage contract for query terms, checked before and after verification."""
    if verb not in VERBS or not terms or any(not term.strip() for term in terms):
        raise UsageError("a supported verb and nonempty search term are required")
    if len(" ".join(terms).encode("utf-8")) > TERM_BYTES:
        raise UsageError(f"query terms exceed {TERM_BYTES} encoded bytes")
    if verb == "loads-for" and len(terms) < 2:
        raise UsageError("loads-for requires a skill and a predicate")
    if verb not in MULTI_TERM and len(terms) != 1:
        raise UsageError(f"{verb} requires one quoted term")


def _matched(document: VerifiedDocument, term: str) -> set[str]:
    needle = term.casefold()
    nodes = document.facts.graph.nodes
    names = {fact.subject: str(fact.object).casefold() for fact in document.facts.graph.facts
             if fact.predicate == "name"}
    exact = {node.id for node in nodes if needle in (node.id.casefold(), node.path.casefold(),
                                                     node.selector.casefold(), names.get(node.id))}
    if exact:
        return exact
    return {node.id for node in nodes if needle in node.id.casefold() or needle in node.path.casefold()
            or needle in names.get(node.id, "")}


def select(document: VerifiedDocument, verb: str, terms: list[str]) -> tuple[Fact, ...]:
    if not isinstance(document, VerifiedDocument):
        raise TypeError("queries require an artifact-verified VerifiedDocument")
    _validate_terms(verb, terms)
    graph = document.facts.graph
    selected = _matched(document, " ".join(terms) if verb == "state" else terms[0])
    if verb == "governs":
        phrase = " ".join(terms).casefold()
        rules = {node.id for node in graph.nodes if node.type == "rule"}
        searchable: dict[str, list[str]] = {}
        for fact in graph.facts:
            if fact.subject in rules and fact.predicate in {"name", "attr.section", "attr.statement", "attr.source_text"}:
                searchable.setdefault(fact.subject, []).append(str(fact.object))
        selected = {identity for identity in rules if phrase == identity.casefold()
                    or phrase in "\n".join(searchable.get(identity, ())).casefold()}
        return tuple(fact for fact in graph.facts if fact.subject in selected and
                     (fact.predicate in {"governed_by", "name", "authority", "state", "unknown"}
                      or fact.predicate.startswith("attr.")))
    if verb == "guidance":
        words = " ".join(terms).casefold().split()
        source_nodes = {node.id for node in graph.nodes if node.type in
                        {"agent", "skill", "reference", "document", "rule", "command"}}
        historical = {fact.subject for fact in graph.facts if fact.predicate == "state"
                      and fact.object not in {"live", "active"}}
        selected = set()
        attributes: dict[str, list[str]] = {}
        matched_guidance: dict[str, Fact] = {}
        for fact in graph.facts:
            if fact.predicate in {"name", "attr.description", "attr.statement"}:
                attributes.setdefault(fact.subject, []).append(str(fact.object))
            if fact.predicate == "guidance" and fact.subject in source_nodes - historical:
                searchable = (str(fact.object) + " " + str(dict(fact.qualifiers))).casefold()
                if all(word in searchable for word in words):
                    matched_guidance[fact.id] = fact
                    selected.add(fact.subject)
        for node in graph.nodes:
            if node.id not in source_nodes - historical:
                continue
            searchable = " ".join((node.id, node.path, *attributes.get(node.id, []))).casefold()
            if all(word in searchable for word in words):
                selected.add(node.id)
        returned = dict(matched_guidance)
        for fact in graph.facts:
            if fact.subject in selected and fact.predicate in {"name", "authority", "attr.description", "attr.statement", "loads_when", "governed_by", "routes_to"}:
                returned[fact.id] = fact
            if fact.predicate == "loads_when" and isinstance(fact.object, str) and fact.object in selected:
                returned[fact.id] = fact
        priority = {"guidance": 0, "loads_when": 1, "name": 2, "authority": 2}
        return tuple(sorted(returned.values(), key=lambda fact: (priority.get(fact.predicate, 3), fact.id)))
    if verb == "state":
        return tuple(fact for fact in graph.facts if fact.subject in selected and
                     (fact.predicate in {"name", "authority", "state", "unknown"} or fact.predicate.startswith("attr.")))
    if verb == "impact":
        # Follow declared dependents backwards, then include their verification and
        # evidence attachments. Every returned edge explains why it is included.
        # near_miss_for is a recorded negative routing regression: a description
        # change on the target must surface the scenario that asserts non-firing.
        dependent_relations = {"depends_on", "loads_when", "governed_by", "generated_from",
                               "cites", "near_miss_for"}
        seen = set(selected)
        result: dict[str, Fact] = {}
        while True:
            expanded = set(seen)
            for fact in graph.facts:
                if fact.predicate in dependent_relations and isinstance(fact.object, str) and fact.object in seen:
                    result[fact.id] = fact
                    expanded.add(fact.subject)
            if expanded == seen:
                break
            seen = expanded
        for fact in graph.facts:
            if fact.subject in seen and fact.predicate in {"verified_by", "evidenced_by", "constrained_by", "unknown"}:
                result[fact.id] = fact
        return tuple(result[key] for key in sorted(result))
    relation = RELATION[verb]
    reverse = verb in REVERSED
    result = []
    for fact in graph.facts:
        if fact.predicate != relation:
            continue
        endpoint = fact.object if reverse else fact.subject
        if verb == "supersedes":
            matches = fact.subject in selected or (isinstance(fact.object, str) and fact.object in selected)
        else:
            matches = isinstance(endpoint, str) and endpoint in selected
        if not matches:
            continue
        if verb == "loads-for" and len(terms) >= 2:
            if " ".join(terms[1:]).casefold() not in str(dict(fact.qualifiers).get("predicate", "")).casefold():
                continue
        result.append(fact)
    # A recorded unresolved relationship is not a verified negative. Preserve the
    # advisory alongside positive relations or return an explicitly unknown answer.
    result.extend(fact for fact in graph.facts if fact.predicate == "unknown" and fact.subject in selected)
    return tuple(result)


def query(document: VerifiedDocument, verb: str, terms: list[str], *, full: bool = False) -> bytes:
    facts = select(document, verb, terms)  # Refuses anything but an artifact-verified document.
    outcome = "results" if facts else "empty"
    if facts and all(fact.predicate == "unknown" for fact in facts):
        outcome = "unverified"
    base = {"apiVersion": "save-toolkit/fleet-atlas-query-result/v2",
            "outcome": outcome, "query": {"verb": verb, "terms": terms},
            "atlas": {"revision": document.revision, "treeDigest": document.facts.snapshot.tree_digest,
                      "dirty": False},
            "scope": "Recorded repository relationships; empty is not proof of absence in operational reality."}
    if verb == "guidance":
        base["searchScope"] = "Canonical names, paths, descriptions, rule statements and source-derived guidance sections; lexical all-terms match, not inferred applicability."
    records = [fact_record(fact, document.facts) for fact in facts]
    if full:
        raw = {item["id"]: item for item in graph_dict(document.facts.graph)["facts"]}
        for record in records:
            record["fullFact"] = raw[record["id"]]
        return canonical_bytes({**base, "count": len(records), "results": records,
                                "truncated": False, "omittedResults": 0, "budgetBytes": None})
    return bounded_envelope(base, records)


def _emit(content: bytes) -> None:
    # Text streams in tests may not expose .buffer; stdout remains UTF-8 on the CLI.
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(content)
    else:
        sys.stdout.write(content.decode("utf-8"))


def main(argv: list[str] | None = None, loader: Callable = extraction) -> int:
    parser = Parser(description=__doc__, add_help=False)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("-h", "--help", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("build", add_help=False)
    sub.add_parser("check", add_help=False)
    query_parser = sub.add_parser("query", add_help=False)
    query_parser.add_argument("verb", choices=VERBS)
    query_parser.add_argument("terms", nargs="+")
    query_parser.add_argument("--full", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.help:
            _emit(bounded_envelope({"outcome": "usage", "message": parser.format_help()}, []))
            return 0
        if not args.command:
            raise UsageError("choose build, check, or query")
        # Validate query shape before touching an absent atlas so invalid usage is 2.
        if args.command == "query":
            try:
                _validate_terms(args.verb, args.terms)
            except UsageError:
                raise UsageError("invalid query arguments") from None
        document = build(args.root, loader) if args.command == "build" else verify(args.root, loader)
        if args.command == "query":
            content = query(document, args.verb, args.terms, full=args.full)
            _emit(content)
            if json.loads(content)["outcome"] == "unverified":
                return 1
        else:
            _emit(bounded_envelope({"outcome": "verified", "command": args.command,
                                   "revision": document.revision,
                                   "treeDigest": document.facts.snapshot.tree_digest}, []))
        return 0
    except UsageError as error:
        _emit(bounded_envelope({"outcome": "usage", "message": str(error)[:1000]}, []))
        return 2
    except ArtifactDrift as error:
        _emit(bounded_envelope({"outcome": "drift", "message": str(error)[:1000]}, []))
        return 1
    except (ValueError, OSError, TypeError, KeyError, ImportError, RecursionError, SyntaxError) as error:
        _emit(bounded_envelope({"outcome": "unverified", "message": str(error)[:1000]}, []))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
