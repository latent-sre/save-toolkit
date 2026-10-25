"""Original-source metadata must never map an unrelated downstream resource into a causal graph."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from pathlib import Path

import itbench_adapter as adapter
import pytest
from itbench_testkit import manifest

BASE = Path(__file__).parent / "manifests"
LOAD_REPLACEMENTS = {
    "ad-deployment-1": "otel-demo/Deployment/load-generator",
    "ad-replicaset-1": "otel-demo/ReplicaSet/load-generator-57ffcd644",
    "ad-pod-1": "otel-demo/Pod/load-generator-57ffcd644-rwl8b",
    "ad-service-1": "otel-demo/Service/load-generator",
}


def quota_control() -> tuple[dict, dict, dict]:
    gt = json.loads((BASE / "wp04-binding-metadata.json").read_text())["cases"]["wp04-102"]
    bindings = json.loads((BASE / "wp04-bindings.json").read_text())["cases"]["wp04-102"]
    referenced = {v for edge in gt["propagations"] for v in (edge["source"], edge["target"])}
    root = next(g["id"] for g in gt["groups"] if g.get("root_cause"))
    names = {
        g: next(name for name, mapped in bindings.items() if mapped == [g] and "load-generator" not in name)
        for g in referenced
    }
    submission = {
        "case_id": "wp04-102",
        "status": "submitted",
        "entities": [
            {
                "id": g,
                "name": names[g],
                "rank": 1 if g == root else None,
                "reason": "Synthetic source-bound control, not a candidate diagnosis",
            }
            for g in sorted(referenced)
        ],
        "edges": [
            {**edge, "condition": "Synthetic source graph control", "effect": "Synthetic propagation control"}
            for edge in gt["propagations"]
        ],
    }
    return submission, bindings, gt


def test_actual_wrong_load_generator_downstream_graph_never_passes() -> None:
    correct, bindings, gt = quota_control()
    assert adapter.assess_local(correct, bindings, gt)["adapted_local"]["verdict"] == "PASS"
    wrong = copy.deepcopy(correct)
    for entity in wrong["entities"]:
        entity["name"] = LOAD_REPLACEMENTS.get(entity["id"], entity["name"])
    result = adapter.assess_local(wrong, bindings, gt)
    assert result["adapted_local"]["root_entity_at_1"] == 1
    assert result["adapted_local"]["verdict"] in {"FAIL", "INCONCLUSIVE"}
    assert result["adapted_local"]["edge_precision"] != 1.0


def test_scorer_rejects_poisoned_bindings_even_when_the_supplied_ids_exist() -> None:
    submission, bindings, gt = quota_control()
    poisoned = {**bindings, **{name: [gid] for gid, name in LOAD_REPLACEMENTS.items()}}
    for entity in submission["entities"]:
        entity["name"] = LOAD_REPLACEMENTS.get(entity["id"], entity["name"])
    result = adapter.assess_local(submission, poisoned, gt)
    assert result["adapted_local"]["root_entity_at_1"] == 1
    assert result["adapted_local"]["verdict"] == "INCONCLUSIVE"
    assert len(result["mapping_gaps"]) == 4


@pytest.mark.parametrize(
    "name",
    [
        "otel-demo/Deployment/load-generator",
        "otel-demo/Pod/load-generator-57ffcd644-rwl8b",
        "otel-demo/ReplicaSet/load-generator-57ffcd644",
        "otel-demo/Service/load-generator",
    ],
)
def test_ad_filters_are_anchored_at_the_start_of_the_resource_name(name: str) -> None:
    gt = json.loads((BASE / "wp04-binding-metadata.json").read_text())["cases"]["wp04-102"]
    assert adapter.binding_candidates(name, gt["groups"]) == []


def test_all_frozen_bindings_match_original_source_metadata() -> None:
    refs = json.loads((BASE / "wp04-binding-metadata.json").read_text())["cases"]
    frozen = json.loads((BASE / "wp04-bindings.json").read_text())["cases"]
    for case_id, names in frozen.items():
        for name, ids in names.items():
            assert ids == adapter.binding_candidates(name, refs[case_id]["groups"]), (case_id, name, ids)


def test_matching_preserves_chaos_suffixes_but_not_interior_substrings_or_wrong_scope() -> None:
    groups = [
        {
            "id": "memory",
            "kind": "StressChaos",
            "namespace": "chaos-mesh",
            "filter": ["otel-demo-valkey-memory-stress"],
            "root_cause": True,
        }
    ]
    assert adapter.binding_candidates("chaos-mesh/StressChaos/otel-demo-valkey-memory-stress-4fvng", groups) == [
        "memory"
    ]
    assert adapter.binding_candidates("chaos-mesh/StressChaos/not-otel-demo-valkey-memory-stress-4fvng", groups) == []
    assert adapter.binding_candidates("other/StressChaos/otel-demo-valkey-memory-stress-4fvng", groups) == []
    assert adapter.binding_candidates("chaos-mesh/Pod/otel-demo-valkey-memory-stress-4fvng", groups) == []


def test_full_name_precedence_and_genuine_ambiguity_are_preserved() -> None:
    groups = [
        {"id": "frontend", "kind": "Service", "filter": [r"frontend\b"]},
        {"id": "proxy", "kind": "Service", "filter": [r"frontend-proxy\b"]},
    ]
    assert adapter.binding_candidates("otel-demo/Service/frontend-proxy", groups) == ["proxy"]
    groups = [
        {"id": "frontend-pod", "kind": "Pod", "filter": ["frontend-.*"]},
        {"id": "proxy-pod", "kind": "Pod", "filter": ["frontend-proxy-.*"]},
    ]
    assert adapter.binding_candidates("otel-demo/Pod/frontend-proxy-abc", groups) == ["frontend-pod", "proxy-pod"]


def test_rebuilding_bindings_reads_only_hash_bound_original_metadata_and_observations(tmp_path: Path) -> None:
    m = manifest(tmp_path / "source")
    for case in m["cases"]:
        directory = tmp_path / "source" / case["source_id"]
        gt = {
            "groups": [
                {"id": "ad-root", "kind": "Service", "namespace": "otel-demo", "filter": [r"ad\b"], "root_cause": True}
            ],
            "propagations": [],
        }
        hidden = directory / "ground_truth.yaml"
        hidden.write_text(json.dumps(gt))
        stream = io.StringIO()
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["Timestamp", "Body"])
        for namespace, kind, name in [
            ("otel-demo", "Service", "ad"),
            ("otel-demo", "Service", "load-generator"),
            ("other", "Service", "ad"),
            ("otel-demo", "Pod", "ad"),
        ]:
            writer.writerow(
                [
                    "2025-12-15 18:00:00",
                    json.dumps({"object": {"involvedObject": {"namespace": namespace, "kind": kind, "name": name}}}),
                ]
            )
        observed = directory / "k8s_events_raw.tsv"
        observed.write_text(stream.getvalue())
        for asset, path in [(case["hidden"][0], hidden), (case["observables"][0], observed)]:
            asset.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size=path.stat().st_size)
    result = adapter.build_bindings(m, tmp_path / "source")
    assert result["binding_policy"] == "wp04-original-metadata-anchored-name-v1"
    assert all(value == {"otel-demo/Service/ad": ["ad-root"]} for value in result["cases"].values())
    (tmp_path / "source" / m["cases"][0]["source_id"] / "k8s_events_raw.tsv").write_text("tampered")
    with pytest.raises(ValueError, match="mismatch"):
        adapter.build_bindings(m, tmp_path / "source")


def test_frozen_metadata_reference_is_bound_to_original_selected_gt_digests() -> None:
    refs = json.loads((BASE / "wp04-binding-metadata.json").read_text())["cases"]
    selected = json.loads((BASE / "wp04-itbench-five.json").read_text())["cases"]
    assert set(refs) == {case["id"] for case in selected}
    for case in selected:
        assert refs[case["id"]]["ground_truth_sha256"] == case["hidden"][0]["sha256"]


@pytest.mark.parametrize("name", ["wrong-namespace/Service/ad", "otel-demo/ConfigMap/ad"])
def test_existing_group_ids_do_not_override_wrong_namespace_or_kind(name: str) -> None:
    submission, bindings, gt = quota_control()
    target = next(entity for entity in submission["entities"] if entity["id"] == "ad-service-1")
    target["name"] = name
    result = adapter.assess_local(submission, {**bindings, name: ["ad-service-1"]}, gt)
    assert result["adapted_local"]["root_entity_at_1"] == 1
    assert result["adapted_local"]["verdict"] == "INCONCLUSIVE"
    assert any("unsupported original metadata" in gap for gap in result["mapping_gaps"])
