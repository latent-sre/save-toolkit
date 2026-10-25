"""Rebuild evaluator-only mappings from pinned Kubernetes observations and original GT metadata."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from .core import BINDING_POLICY, _read_asset, binding_candidates, validate_manifest


def _observed_names(data: bytes, filename: str) -> set[str]:
    names: set[str] = set()
    old_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(256 * 1024 * 1024)
        for row in csv.DictReader(io.StringIO(data.decode("utf-8")), delimiter="\t"):
            value = json.loads(row["Body"])
            if not isinstance(value, dict):
                raise ValueError(f"non-object Kubernetes record: {filename}")
            obj = value.get("object", value)
            if not isinstance(obj, dict):
                raise ValueError(f"invalid Kubernetes object: {filename}")
            if filename == "k8s_events_raw.tsv":
                obj = obj.get("involvedObject") or obj.get("regarding")
                if not isinstance(obj, dict):
                    raise ValueError("Kubernetes event lacks a resource reference")
                metadata = obj
            else:
                metadata = obj.get("metadata", {})
            if not isinstance(metadata, dict):
                raise ValueError(f"invalid resource metadata: {filename}")
            kind = obj.get("kind")
            name = metadata.get("name")
            namespace = metadata.get("namespace") or ""
            if not isinstance(kind, str) or not isinstance(name, str) or not isinstance(namespace, str):
                raise ValueError(f"resource lacks kind/name/namespace metadata: {filename}")
            names.add(f"{namespace}/{kind}/{name}")
    except csv.Error as exc:
        raise ValueError(f"invalid Kubernetes TSV: {filename}") from exc
    finally:
        csv.field_size_limit(old_limit)
    return names


def build_bindings(manifest: Mapping[str, Any], source_root: Path) -> dict[str, Any]:
    """Reproduce all five mappings, retaining genuine ambiguity and rejecting missing roots.

    Only manifest-bound event/object observations supply names; original GT supplies the
    metadata predicates. Both paths share the scorer's anchored matching policy. No aliases,
    graph positions or fault descriptions manufacture a resource match.
    """
    validate_manifest(manifest)
    cases: dict[str, Any] = {}
    sources: dict[str, Any] = {}
    counts: dict[str, int] = {}
    for case in manifest["cases"]:
        directory = source_root / case["source_id"]
        raw = _read_asset(directory, case["hidden"][0], observable=False)
        ground_truth = yaml.safe_load(raw)
        if not isinstance(ground_truth, dict):
            raise ValueError("original ground truth must be a mapping")
        ground_truth = ground_truth.get("spec", ground_truth)
        if not isinstance(ground_truth, dict) or not isinstance(ground_truth.get("groups"), list):
            raise ValueError("original ground truth lacks groups")
        groups = ground_truth["groups"]
        if any(not isinstance(g, dict) for g in groups):
            raise ValueError("malformed original group")
        consumed = {case["hidden"][0]["path"]: case["hidden"][0]["sha256"]}
        observed: set[str] = set()
        for asset in case["observables"]:
            if asset["path"] not in {"k8s_events_raw.tsv", "k8s_objects_raw.tsv"}:
                continue
            observed.update(_observed_names(_read_asset(directory, asset, observable=True), asset["path"]))
            consumed[asset["path"]] = asset["sha256"]
        bound: dict[str, list[str]] = {}
        for name in sorted(observed):
            matches = binding_candidates(name, groups)
            if matches:
                bound[name] = matches
        roots = [g["id"] for g in groups if g.get("root_cause") is True]
        if not roots or any(not any(ids == [root] for ids in bound.values()) for root in roots):
            raise ValueError(f"original root lacks an unambiguous observed binding: {case['id']}")
        cases[case["id"]] = bound
        sources[case["id"]] = consumed
        counts[case["id"]] = len(observed)
    return {
        "format": "wp04-evaluator-bindings",
        "version": 1,
        "revision": 2,
        "binding_policy": BINDING_POLICY,
        "method": "original kind/namespace/explicit name; whole-name regex preferred, otherwise anchored prefix; no alias expansion",
        "dataset_revision": manifest["revision"],
        "source_sha256": sources,
        "observed_entity_counts": counts,
        "cases": cases,
    }
