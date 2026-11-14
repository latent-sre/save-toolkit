"""Pure WP04 submission collection/schema shared by native checks and upstream export.

Keep this module independent of the adapter and probe packages: both import it during startup.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import Any


def validate_submission(submission: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if submission.get("status") != "submitted" or not isinstance(submission.get("case_id"), str):
        raise ValueError("submission requires a case_id and submitted status")
    entities = submission.get("entities")
    edges = submission.get("edges")
    if not isinstance(entities, list) or not isinstance(edges, list):
        raise ValueError("entities and edges must be explicit arrays")
    ids: set[str] = set()
    names: set[str] = set()
    ranks: set[int] = set()
    for entity in entities:
        if not isinstance(entity, dict):
            raise ValueError("entity must be an object")
        name = entity.get("name")
        identifier = entity.get("id")
        rank = entity.get("rank")
        if not isinstance(name, str) or re.fullmatch(r"[^/\s]*/[^/\s]+/[^/\s]+", name) is None or name in names:
            raise ValueError("entity requires a unique namespace/Kind/name; use empty namespace for cluster resources")
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError("entity id must be nonempty and unique")
        if "rank" not in entity or (rank is not None and (type(rank) is not int or rank < 1 or rank in ranks)):
            raise ValueError("contributing rank must be a unique positive integer or explicit null")
        if not isinstance(entity.get("reason"), str) or not entity["reason"].strip():
            raise ValueError("entity reason required; the adapter cannot invent one")
        ids.add(identifier)
        names.add(name)
        if rank is not None:
            ranks.add(rank)
    if ranks and ranks != set(range(1, len(ranks) + 1)):
        raise ValueError("ranked hypotheses must be contiguous from one")
    seen_edges: set[tuple[str, str]] = set()
    for edge in edges:
        if not isinstance(edge, dict) or any(
            not isinstance(edge.get(key), str) or edge[key] not in ids for key in ("source", "target")
        ):
            raise ValueError("edge endpoints must be submitted entities")
        pair = (edge["source"], edge["target"])
        if pair in seen_edges or pair[0] == pair[1]:
            raise ValueError("duplicate/self edge")
        seen_edges.add(pair)
        if any(not isinstance(edge.get(key), str) or not edge[key].strip() for key in ("condition", "effect")):
            raise ValueError("edge condition and effect required; absent claims are not inferred")
    return entities, edges


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("submission JSON contains a duplicate object key")
        value[key] = item
    return value


def _nonfinite(value: str) -> Any:
    raise ValueError("submission JSON contains a nonfinite number")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("submission JSON contains a nonfinite number")
    return number


def collect_submission(response: str, case_id: str) -> dict[str, Any]:
    """Collect exactly one complete JSON fence, rejecting duplicate keys and nonfinite numbers.

    Prose is not interpreted as a claim. Empty entity/edge arrays remain schema-valid; operational
    usefulness, observation grounding and causal correctness still require independent review.
    """
    opening = r"^```json[ \t]*\r?$"
    blocks = re.findall(r"^```json[ \t]*\r?\n(.*?)\r?\n```[ \t]*\r?$", response, re.MULTILINE | re.DOTALL)
    if len(re.findall(opening, response, re.MULTILINE)) != 1 or len(blocks) != 1:
        raise ValueError("response must contain exactly one JSON submission block")
    try:
        submission = json.loads(
            blocks[0], object_pairs_hook=_unique_object, parse_constant=_nonfinite, parse_float=_finite_float
        )
    except RecursionError as exc:
        raise ValueError("submission JSON exceeds parser nesting capacity") from exc
    if not isinstance(submission, dict) or submission.get("case_id") != case_id:
        raise ValueError("submission case differs from selected case")
    validate_submission(submission)
    return submission
