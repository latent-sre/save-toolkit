"""Small pinned ITBench-Lite boundary and explicitly non-upstream local metric."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import tempfile
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

DATASET = "ibm-research/ITBench-Lite"
REVISION = "d0916b08ba421ce5e672e9ad68aa947d938dfef0"
EVALUATOR_REVISION = "14f026fc9cc348c4ecec5ab32714de954c95c1b1"
PREFIX = "snapshots/sre/v0.2-B96DF826-4BB2-4B62-97AB-6D84254C53D7"
SOURCE_IDS = {"Scenario-7", "Scenario-21", "Scenario-24", "Scenario-80", "Scenario-102"}
MAPPING_VERSION = "wp04-exact-entity-edge-v2"
BINDING_POLICY = "wp04-original-metadata-anchored-name-v1"
HIDDEN_MARKERS = re.compile(rb"(?i)(ground_truth|recommended_actions|[\"']root_cause[\"']\s*:|[\"']aliases[\"']\s*:)")


def binding_candidates(entity_name: str, groups: Sequence[Mapping[str, Any]]) -> list[str]:
    """Match original kind/namespace/name or a regex anchored at the resource-name start.

    Full resource-name matches take precedence; a unique prefix can describe generated
    chaos suffixes. Substring search and alias expansion are deliberately absent.
    Multiple eligible groups remain multiple candidates, never an invented resolution.
    """
    if re.fullmatch(r"[^/\s]*/[^/\s]+/[^/\s]+", entity_name) is None:
        raise ValueError("invalid namespace/Kind/name")
    namespace, kind, name = entity_name.split("/")
    full: list[str] = []
    prefix: list[str] = []
    for group in groups:
        identifier = group.get("id")
        if not isinstance(identifier, str) or not isinstance(group.get("kind"), str):
            raise ValueError("original group lacks id/kind metadata")
        if group["kind"] != kind or (group.get("namespace") is not None and group["namespace"] != namespace):
            continue
        explicit = group.get("name")
        if explicit is not None:
            if not isinstance(explicit, str) or not explicit:
                raise ValueError("invalid original group name")
            if explicit == name:
                full.append(identifier)
            continue
        patterns = group.get("filter", [])
        if not isinstance(patterns, list) or not patterns or any(not isinstance(p, str) or not p for p in patterns):
            raise ValueError("original group lacks usable name/filter metadata")
        try:
            if any(re.fullmatch(pattern, name) for pattern in patterns):
                full.append(identifier)
            elif any(re.match(pattern, name) for pattern in patterns):
                prefix.append(identifier)
        except re.error as exc:
            raise ValueError(f"invalid original group filter: {identifier}") from exc
    return full or prefix


def _asset_path(value: Any, *, hidden: bool = False) -> str:
    if not isinstance(value, str) or "\\" in value or any(v in value.split("/") for v in ("", ".", "..")):
        raise ValueError("asset path must be a normalized relative POSIX path")
    path = PurePosixPath(value)
    allowed = (
        value == "ground_truth.yaml"
        if hidden
        else (
            value in {"k8s_events_raw.tsv", "k8s_objects_raw.tsv", "otel_logs_raw.tsv", "otel_traces_raw.tsv"}
            or re.fullmatch(r"alerts/alerts_(?:at|in_alerting_state)_[0-9TZ.\-]+\.json", value) is not None
        )
    )
    if path.is_absolute() or not allowed:
        raise ValueError(f"asset outside the {'hidden' if hidden else 'observable'} allowlist: {value}")
    return value


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    """Reject mutable identity, answer files, duplicate assets and unbound content."""
    expected = {
        "format": "wp04-itbench-manifest",
        "version": 1,
        "dataset": DATASET,
        "revision": REVISION,
        "license": "Apache-2.0",
        "evaluator_revision": EVALUATOR_REVISION,
    }
    for key, value in expected.items():
        if manifest.get(key) != value or (key == "version" and type(manifest[key]) is not int):
            raise ValueError(f"unsupported or unpinned manifest {key}")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 5:
        raise ValueError("pilot requires five explicitly selected cases")
    ids: set[str] = set()
    sources: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("case must be an object")
        source_id = case.get("source_id")
        if source_id not in SOURCE_IDS or source_id in sources:
            raise ValueError("unknown or duplicate source case")
        sources.add(source_id)
        case_id = case.get("id")
        if case_id != "wp04-" + source_id.removeprefix("Scenario-") or case_id in ids:
            raise ValueError("local/source case identity mismatch")
        ids.add(case_id)
        if case.get("source_path") != f"{PREFIX}/{source_id}":
            raise ValueError("source path must preserve the pinned snapshot identity")
        if case.get("status") != "proposed-human-review" or not case.get("timezone"):
            raise ValueError("case admission and source timezone must remain explicit")
        seen: set[str] = set()
        hashes: dict[str, set[str]] = {"observables": set(), "hidden": set()}
        for group in ("observables", "hidden"):
            assets = case.get(group)
            if not isinstance(assets, list) or not assets:
                raise ValueError(f"case requires bound {group}")
            for asset in assets:
                if not isinstance(asset, dict):
                    raise ValueError("asset must be an object")
                path = _asset_path(asset.get("path"), hidden=group == "hidden")
                digest = asset.get("sha256")
                size = asset.get("size")
                if path in seen or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                    raise ValueError("duplicate asset or invalid SHA-256")
                if type(size) is not int or size < 1 or size > 256 * 1024 * 1024:
                    raise ValueError("invalid or oversized asset")
                seen.add(path)
                hashes[group].add(digest)
        if hashes["observables"] & hashes["hidden"]:
            raise ValueError("hidden content cannot also be an observable")


def _regular_path(root: Path, relative: str) -> Path:
    path = root / relative
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError(f"symlink in source or destination path: {part}")
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"missing or escaped regular file: {relative}")
    return path


def _read_asset(root: Path, asset: Mapping[str, Any], *, observable: bool) -> bytes:
    path = _regular_path(root, str(asset["path"]))
    if path.stat().st_size != asset["size"]:
        raise ValueError(f"size mismatch: {asset['path']}")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != asset["sha256"]:
        raise ValueError(f"digest mismatch: {asset['path']}")
    if observable and HIDDEN_MARKERS.search(data):
        raise ValueError(f"answer/evaluator marker in observable: {asset['path']}")
    return data


def stage_case(manifest: Mapping[str, Any], case_id: str, source_root: Path, destination: Path) -> dict[str, Any]:
    """Publish a new observed-only workspace after all files pass validation.

    Returns evaluator-side provenance; never writes it or hidden metadata in the workspace.
    This is a file boundary, not an OS sandbox for tools with arbitrary host reads.
    """
    validate_manifest(manifest)
    cases = [case for case in manifest["cases"] if case["id"] == case_id]
    if not cases:
        raise ValueError("case not selected")
    case = cases[0]
    source = source_root.resolve()
    dest = destination.absolute()
    for part in [destination, *destination.parents]:
        if part.is_symlink():
            raise ValueError("symlink in destination path")
    if dest.exists() or dest.resolve().is_relative_to(source) or source.is_relative_to(dest.resolve()):
        raise ValueError("destination must be new and disjoint from evaluator source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".wp04-stage-", dir=destination.parent))
    try:
        for asset in case["observables"]:
            data = _read_asset(source_root / case["source_id"], asset, observable=True)
            output = temporary / asset["path"]
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        temporary.rename(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return {
        "format": "wp04-staging-receipt",
        "version": 1,
        "case_id": case_id,
        "source_id": case["source_id"],
        "dataset_revision": REVISION,
        "manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        "candidate_files": copy.deepcopy(case["observables"]),
        "boundary": "logical-file-staging-only",
    }


def fetch_sources(manifest: Mapping[str, Any], source_root: Path, *, include_hidden: bool = False) -> dict[str, Any]:
    """Fetch only exact manifest-bound immutable public URLs, never execute downloads."""
    validate_manifest(manifest)
    fetched: list[str] = []
    for case in manifest["cases"]:
        assets = case["observables"] + (case["hidden"] if include_hidden else [])
        for asset in assets:
            output = source_root / case["source_id"] / asset["path"]
            for part in [output, *output.parents]:
                if part.is_symlink():
                    raise ValueError("symlink in cache path")
            if output.exists():
                _read_asset(source_root / case["source_id"], asset, observable=asset in case["observables"])
                continue
            url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{case['source_path']}/{asset['path']}"
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read(asset["size"] + 1)
            if len(data) != asset["size"] or hashlib.sha256(data).hexdigest() != asset["sha256"]:
                raise ValueError(f"download differs from frozen content: {asset['path']}")
            if asset in case["observables"] and HIDDEN_MARKERS.search(data):
                raise ValueError("answer marker in downloaded observable")
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(data)
            fetched.append(f"{case['source_id']}/{asset['path']}")
    return {"fetched": fetched, "dataset_revision": REVISION, "executed": False}


def _submission(submission: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
        if not isinstance(edge, dict) or edge.get("source") not in ids or edge.get("target") not in ids:
            raise ValueError("edge endpoints must be submitted entities")
        pair = (edge["source"], edge["target"])
        if pair in seen_edges or pair[0] == pair[1]:
            raise ValueError("duplicate/self edge")
        seen_edges.add(pair)
        if any(not isinstance(edge.get(key), str) or not edge[key].strip() for key in ("condition", "effect")):
            raise ValueError("edge condition and effect required; absent claims are not inferred")
    return entities, edges


def export_submission(submission: Mapping[str, Any]) -> dict[str, Any]:
    """Export upstream generated-response entities with ordered contributing_factor flags.

    Upstream's judge accepts a JSON generated response, not a validated agent schema.
    Its prompt specifies namespace/Kind/name and ordered contributing_factor entities.
    Hidden group IDs/aliases are deliberately absent from this export.
    """
    entities, edges = _submission(submission)
    ordered = sorted(entities, key=lambda entity: entity["rank"] if entity["rank"] is not None else len(entities) + 1)
    return {
        "entities": [
            {"id": e["id"], "name": e["name"], "contributing_factor": e["rank"] is not None, "reason": e["reason"]}
            for e in ordered
        ],
        "propagations": copy.deepcopy(edges),
    }


def assess_local(
    submission: Mapping[str, Any],
    bindings: Mapping[str, Any],
    ground_truth: Mapping[str, Any],
    upstream_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Exact group-ID root-at-1 and directed edge overlap; no semantic/alias credit.

    Bindings are evaluator-only, explicitly reviewed exact observation-name→group lists.
    Unknown/ambiguous bindings make the adapted measurement unavailable, never guessed.
    Original upstream results survive unchanged and are not synthesized from this metric.
    """
    result: dict[str, Any] = {
        "mapping_version": MAPPING_VERSION,
        "binding_policy": BINDING_POLICY,
        "case_id": submission.get("case_id"),
        "upstream_result": copy.deepcopy(upstream_result),
        "upstream_assessment": "unmeasured" if upstream_result is None else "imported-unchanged",
        "manual_semantics": {"verdict": "INCONCLUSIVE", "reason": "requires independent human operational review"},
        "mapping_gaps": [],
        "adapted_local": {
            "method": "exact-root-group-at-1-and-directed-edge-overlap-no-aliases",
            "verdict": "INCONCLUSIVE",
            "root_entity_at_1": None,
            "edge_precision": None,
            "edge_recall": None,
        },
    }
    if submission.get("status") == "unavailable":
        result["mapping_gaps"].append(str(submission.get("reason", "submission measurement unavailable")))
        return result
    entities, edges = _submission(submission)
    gt = ground_truth.get("spec", ground_truth)
    if (
        not isinstance(gt, Mapping)
        or not isinstance(gt.get("groups"), list)
        or not isinstance(gt.get("propagations"), list)
    ):
        result["mapping_gaps"].append("ground truth lacks groups/propagations")
        return result
    groups = gt["groups"]
    if any(not isinstance(g, dict) or not isinstance(g.get("id"), str) for g in groups) or any(
        not isinstance(e, dict) or not isinstance(e.get("source"), str) or not isinstance(e.get("target"), str)
        for e in gt["propagations"]
    ):
        result["mapping_gaps"].append("malformed ground-truth group or edge")
        return result
    group_ids = {g["id"] for g in groups}
    roots = {g["id"] for g in groups if g.get("root_cause") is True}
    gt_edges = {(e["source"], e["target"]) for e in gt["propagations"]}
    if not roots or len(group_ids) != len(groups):
        result["mapping_gaps"].append("missing roots or duplicate ground-truth group IDs")
    for source, target in gt_edges:
        if source not in group_ids or target not in group_ids:
            result["mapping_gaps"].append(f"dangling ground-truth edge {source} -> {target}")
    reference_valid = not result["mapping_gaps"]
    resolved: dict[str, str] = {}
    for entity in entities:
        matches = bindings.get(entity["name"])
        if (
            not isinstance(matches, list)
            or len(matches) != 1
            or not isinstance(matches[0], str)
            or matches[0] not in group_ids
        ):
            result["mapping_gaps"].append(f"missing/ambiguous exact binding for {entity['name']}")
        else:
            try:
                supported = binding_candidates(entity["name"], groups)
            except ValueError as exc:
                result["mapping_gaps"].append(f"original metadata unavailable for {entity['name']}: {exc}")
                continue
            if supported != matches:
                result["mapping_gaps"].append(f"unsupported original metadata binding for {entity['name']}")
            else:
                resolved[entity["id"]] = matches[0]
    ranked = sorted((e for e in entities if e["rank"] is not None), key=lambda e: e["rank"])
    root_correct = None
    if roots and len(group_ids) == len(groups) and (not ranked or ranked[0]["id"] in resolved):
        root_correct = int(bool(ranked) and resolved[ranked[0]["id"]] in roots)
        result["adapted_local"]["root_entity_at_1"] = root_correct
    edges_complete = reference_valid and all(e["source"] in resolved and e["target"] in resolved for e in edges)
    edge_correct = None
    if edges_complete:
        predicted = {(resolved[e["source"]], resolved[e["target"]]) for e in edges}
        overlap = len(predicted & gt_edges)
        edge_correct = predicted == gt_edges
        result["adapted_local"].update(
            edge_precision=overlap / len(predicted) if predicted else None,
            edge_recall=overlap / len(gt_edges) if gt_edges else None,
            predicted_edges=len(predicted),
            reference_edges=len(gt_edges),
            matched_edges=overlap,
        )
    if root_correct == 0 or edge_correct is False:
        result["adapted_local"]["verdict"] = "FAIL"
    elif root_correct == 1 and edge_correct is True:
        result["adapted_local"]["verdict"] = "PASS"
    return result
