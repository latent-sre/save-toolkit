"""Bounded fixture checks for the repaired telemetry guidance and eval criteria."""

import re
from pathlib import Path

import yaml

from evals.graders import run_grader

ROOT = Path(__file__).resolve().parents[1]


def test_overall_spl_without_taxonomy_preserves_population_and_unknown_status() -> None:
    source = (ROOT / "skills/obs-analysis/references/spl.md").read_text()
    query = source.split("### Overall deploy error rate")[1].split("````spl")[1].split("````")[0]
    # Exercise the supplied aggregation's contract over completion-event fixtures;
    # this is deliberately not a Splunk integration test.
    assert "count AS total, count(status) AS classified" in query
    assert "count(eval(status>=500 AND status<600)) AS errors by phase" in query
    assert "error_type" not in query
    assert "if(total>0 AND classified=total, errors/total, null())" in query

    def rate(statuses: list[str | None]) -> float | None:
        valid = [int(s) for s in statuses if s is not None and re.fullmatch(r"[1-5][0-9]{2}", s)]
        return sum(s >= 500 for s in valid) / len(statuses) if statuses and len(valid) == len(statuses) else None

    assert rate(["200"] * 99 + ["500"]) == 0.01
    assert rate(["200"] * 90 + ["500"] * 10) == 0.10
    assert rate(["200"] * 900 + ["500"] * 100) == 0.10
    for invalid in (None, "0", "700", "500.5"):
        assert rate(["200", invalid]) is None
    assert rate([]) is None
    catalog = (ROOT / "skills/obs-analysis/references/query-catalog.md").read_text()
    assert "./spl.md#overall-deploy-error-rate" in catalog


def grade_scenario(name: str, response: str) -> bool:
    data = yaml.safe_load((ROOT / f"evals/scenarios/{name}-freegen-contract.yaml").read_text())
    return all(run_grader(spec, response)[0] for spec in data["graders"])


def test_trace_actual_graders_reject_each_wrong_maturity() -> None:
    lines = [
        "A: service.instance.id Stable",
        "B: server.address Stable",
        "C: http.route Stable",
        "D: db.collection.name Stable",
        "E: messaging.destination.name Development",
    ]
    assert grade_scenario("obs-traces-semantics", "\n".join(lines))
    for index in range(5):
        wrong = lines.copy()
        wrong[index] = (
            wrong[index].replace("Stable", "Development")
            if index < 4
            else wrong[index].replace("Development", "Stable")
        )
        assert not grade_scenario("obs-traces-semantics", "\n".join(wrong)), index


def test_metrics_actual_graders_require_discovery_before_syncer() -> None:
    prefix = "A: alignment\nB: 60 seconds\nC: not retroactive\nD: "
    assert grade_scenario("obs-metrics-gcp-gotchas", prefix + "discover_datasource_and_auth_then_select_path")
    for bad in (
        "investigate_syncer_first",
        "Datasource authentication uses OAuth; always investigate the syncer first without discovery.",
    ):
        assert not grade_scenario("obs-metrics-gcp-gotchas", prefix + bad)


def test_naming_actual_graders_discriminate_counter_types() -> None:
    good = "A: http.server.request.duration s\nB: attribute\nC: jobs.processed\nD: job.active"
    assert grade_scenario("obs-pipeline-naming", good)
    for bad in (good.replace("jobs.processed", "job.processed"), good.replace("job.active", "jobs.active")):
        assert not grade_scenario("obs-pipeline-naming", bad)
