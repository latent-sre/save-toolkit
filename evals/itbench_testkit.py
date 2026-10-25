"""Test-only builders for the focused WP04 controls; never part of a runner identity."""

from __future__ import annotations

import hashlib
from pathlib import Path

SHA = "d0916b08ba421ce5e672e9ad68aa947d938dfef0"
EVAL_SHA = "14f026fc9cc348c4ecec5ab32714de954c95c1b1"
PREFIX = "snapshots/sre/v0.2-B96DF826-4BB2-4B62-97AB-6D84254C53D7"


def manifest(source: Path) -> dict:
    cases = []
    for i in [24, 7, 21, 80, 102]:
        p = source / f"Scenario-{i}" / "k8s_events_raw.tsv"
        p.parent.mkdir(parents=True)
        p.write_text("Timestamp\tBody\n2025-12-15 18:00:00\tobserved\n")
        hidden = p.parent / "ground_truth.yaml"
        hidden.write_text("recommended_actions: [ANSWER_CANARY]\n")
        cases.append(
            {
                "id": f"wp04-{i}",
                "source_id": f"Scenario-{i}",
                "source_path": f"{PREFIX}/Scenario-{i}",
                "status": "proposed-human-review",
                "timezone": "unknown for naive collector timestamps; embedded UTC retained",
                "observables": [
                    {
                        "path": "k8s_events_raw.tsv",
                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                        "size": p.stat().st_size,
                    }
                ],
                "hidden": [
                    {
                        "path": "ground_truth.yaml",
                        "sha256": hashlib.sha256(hidden.read_bytes()).hexdigest(),
                        "size": hidden.stat().st_size,
                    }
                ],
                "coherence_gaps": ["source semantics require human review"],
            }
        )
    return {
        "format": "wp04-itbench-manifest",
        "version": 1,
        "dataset": "ibm-research/ITBench-Lite",
        "revision": SHA,
        "license": "Apache-2.0",
        "evaluator_revision": EVAL_SHA,
        "cases": cases,
    }


def diagnosis() -> dict:
    return {
        "case_id": "wp04-24",
        "status": "submitted",
        "entities": [
            {
                "id": "a",
                "name": "otel-demo/Deployment/checkout",
                "rank": 1,
                "reason": "Configuration differs from endpoint",
            },
            {"id": "b", "name": "otel-demo/Service/checkout", "rank": None, "reason": "Observed symptom"},
        ],
        "edges": [
            {"source": "a", "target": "b", "condition": "configuration used by workload", "effect": "downstream error"}
        ],
    }


def truth() -> dict:
    return {
        "groups": [
            {
                "id": "deployment",
                "kind": "Deployment",
                "namespace": "otel-demo",
                "name": "checkout",
                "root_cause": True,
            },
            {"id": "service", "kind": "Service", "namespace": "otel-demo", "filter": [r"checkout\b"]},
        ],
        "aliases": [["deployment", "pod"]],
        "propagations": [{"source": "deployment", "target": "service"}],
    }


BINDINGS = {"otel-demo/Deployment/checkout": ["deployment"], "otel-demo/Service/checkout": ["service"]}
