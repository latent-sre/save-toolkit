"""One fact projection and exact UTF-8 budgets for fleet-atlas v2 surfaces."""

from __future__ import annotations

from dataclasses import asdict
import json
from typing import Iterable

from fleet_atlas_v2_model import (
    EvidenceClass, Fact, FactRef, Graph, Node, Proof, ProofKind, Span, Value,
    canonical_bytes, unsafe_identifier,
)
from fleet_atlas_v2_proofs import VerifiedFacts


DETAIL_BUDGET = 20_000
INDEX_BUDGET = 4_000
API_VERSION = "save-toolkit/fleet-atlas/v2"
PIPELINE = "typed-facts/v2"


def graph_dict(graph: Graph) -> dict:
    facts = []
    for fact in graph.facts:
        record = asdict(fact)
        record["proof"]["inputs"] = [
            {"kind": "span", **asdict(item)} if isinstance(item, Span)
            else {"kind": "fact", "fact_id": item.fact_id}
            for item in fact.proof.inputs
        ]
        facts.append(record)
    return {"nodes": [asdict(node) for node in graph.nodes], "facts": facts}


def _keys(value: object, expected: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"invalid record; expected fields {sorted(expected)}")
    return value


def _text(value: object) -> str:
    if type(value) is not str:
        raise ValueError("expected text")
    return value


def _value(value: object) -> Value:
    if isinstance(value, list):
        return tuple(_value(item) for item in value)
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise ValueError("unsupported fact value")


def parse_graph(record: object) -> Graph:
    """Strict shape conversion, not verification. Unknown fields fail closed."""
    data = _keys(record, {"nodes", "facts"})
    if not isinstance(data["nodes"], list) or not isinstance(data["facts"], list):
        raise ValueError("nodes and facts must be arrays")
    nodes = []
    for candidate in data["nodes"]:
        item = _keys(candidate, {"id", "type", "path", "selector"})
        nodes.append(Node(**{key: _text(value) for key, value in item.items()}))
    facts = []
    for candidate in data["facts"]:
        item = _keys(candidate, {"id", "subject", "predicate", "object", "evidence_class", "proof", "qualifiers"})
        proof = _keys(item["proof"], {"kind", "inputs", "evaluator", "scope_digest"})
        if not isinstance(proof["inputs"], list):
            raise ValueError("proof inputs must be an array")
        inputs = []
        for candidate_input in proof["inputs"]:
            if isinstance(candidate_input, dict) and candidate_input.get("kind") == "span":
                source = _keys(candidate_input, {"kind", "path", "blob_hash", "start_line", "end_line", "excerpt_hash"})
                inputs.append(Span(_text(source["path"]), _text(source["blob_hash"]),
                                   source["start_line"], source["end_line"], _text(source["excerpt_hash"])))
            else:
                premise = _keys(candidate_input, {"kind", "fact_id"})
                if premise["kind"] != "fact":
                    raise ValueError("unknown proof input kind")
                inputs.append(FactRef(_text(premise["fact_id"])))
        scope = proof["scope_digest"]
        if scope is not None:
            scope = _text(scope)
        if not isinstance(item["qualifiers"], list):
            raise ValueError("qualifiers must be an array")
        qualifiers = []
        for pair in item["qualifiers"]:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError("invalid qualifier")
            qualifiers.append((_text(pair[0]), _value(pair[1])))
        facts.append(Fact(_text(item["id"]), _text(item["subject"]), _text(item["predicate"]),
                          _value(item["object"]), EvidenceClass(item["evidence_class"]),
                          Proof(ProofKind(proof["kind"]), tuple(inputs), _text(proof["evaluator"]), scope),
                          tuple(qualifiers)))
    return Graph(tuple(nodes), tuple(facts))


def citations(fact: Fact, checked: VerifiedFacts) -> tuple[Span, ...]:
    if not isinstance(checked, VerifiedFacts):
        raise TypeError("fact projection requires proof-verified VerifiedFacts")
    index = checked.fact_index
    if index.get(fact.id) != fact:
        raise ValueError("cannot project a fact outside the verified graph")
    result: set[Span] = set()

    def collect(item: Fact) -> None:
        for source in item.proof.inputs:
            if isinstance(source, Span):
                result.add(source)
            else:
                collect(index[source.fact_id])

    collect(fact)
    return tuple(sorted(result))


def fact_record(fact: Fact, checked: VerifiedFacts) -> dict:
    return {
        "id": fact.id, "subject": fact.subject, "predicate": fact.predicate,
        "object": fact.object, "qualifiers": dict(fact.qualifiers),
        "class": fact.evidence_class.value, "label": fact.evidence_class.label,
        "citations": [{"path": span.path, "start": span.start_line, "end": span.end_line,
                       "blobHash": span.blob_hash, "excerptHash": span.excerpt_hash}
                      for span in citations(fact, checked)],
    }


def fact_line(fact: Fact, checked: VerifiedFacts) -> str:
    record = fact_record(fact, checked)
    # JSON escaping preserves newlines/control characters without permitting a source
    # value to introduce a second fact line, Markdown heading, or evidence label.
    # Every projected field is escaped: a Markdown-significant path or identity must
    # not split record fields or visually inject a class, label, or citation.
    # Per-character escaping; canonical_bytes would wrap the whole value in quotes.
    # Unicode controls/separators get JSON escapes; Markdown/record-significant
    # characters (| < >) need an explicit \uXXXX escape because json.dumps leaves
    # them literal, which would let them split the pipe-delimited record.
    def inline(value):
        out = []
        for char in str(value):
            if char in '|<>':
                out.append(f"\\u{ord(char):04x}")
            elif unsafe_identifier(char):
                out.append(json.dumps(char, ensure_ascii=True)[1:-1])
            else:
                out.append(char)
        return "".join(out)

    identity = inline(record["id"])
    subject = inline(record["subject"])
    predicate = inline(record["predicate"])
    value = inline(record["object"])
    qualifier = inline(record["qualifiers"])
    where = ", ".join(f"{inline(span['path'])}:{span['start']}-{span['end']}"
                      for span in record["citations"])
    return (f"{identity} | {subject} | {predicate} | {value} | {qualifier} | "
            f"{record['class']} [{record['label']}] | {where}")


def bounded_envelope(base: dict, records: Iterable[dict], budget: int = DETAIL_BUDGET) -> bytes:
    """Budget the complete JSON envelope, reserving its own truncation metadata."""
    values = tuple(records)

    def encode(count: int) -> bytes:
        output = {**base, "results": values[:count], "count": count,
                  "truncated": count < len(values), "omittedResults": len(values) - count,
                  "budgetBytes": budget, "encodedBytes": 0}
        for _ in range(12):
            encoded = canonical_bytes(output)
            if output["encodedBytes"] == len(encoded):
                return encoded
            output["encodedBytes"] = len(encoded)
        raise ValueError("cannot stabilize envelope size")

    if len(encode(0)) > budget:
        raise ValueError("query metadata alone exceeds output budget")
    low, high = 0, len(values)
    while low < high:
        mid = (low + high + 1) // 2
        if len(encode(mid)) <= budget:
            low = mid
        else:
            high = mid - 1
    return encode(low)


def bounded_text(header: str, lines: Iterable[str], budget: int) -> bytes:
    values = tuple(lines)

    def encode(count: int) -> bytes:
        prefix = (header.rstrip() + "\n\n" + "\n".join(values[:count]) + "\n").encode("utf-8")
        info = {"truncated": count < len(values), "omittedResults": len(values) - count,
                "budgetBytes": budget, "encodedBytes": 0}
        for _ in range(12):
            encoded = prefix + b"<!-- " + canonical_bytes(info).rstrip(b"\n") + b" -->\n"
            if info["encodedBytes"] == len(encoded):
                return encoded
            info["encodedBytes"] = len(encoded)
        raise ValueError("cannot stabilize view size")

    if len(encode(0)) > budget:
        raise ValueError("view header alone exceeds output budget")
    low, high = 0, len(values)
    while low < high:
        mid = (low + high + 1) // 2
        if len(encode(mid)) <= budget:
            low = mid
        else:
            high = mid - 1
    return encode(low)
