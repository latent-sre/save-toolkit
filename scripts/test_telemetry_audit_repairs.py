"""Bounded fixture checks for the repaired telemetry eval criteria."""

from pathlib import Path

import yaml

from evals.graders import run_grader

ROOT = Path(__file__).resolve().parents[1]


def grade_scenario(name: str, response: str) -> bool:
    data = yaml.safe_load((ROOT / f"evals/scenarios/{name}-freegen-contract.yaml").read_text())
    return all(run_grader(spec, response)[0] for spec in data["graders"])


def test_alloy_actual_graders_distinguish_default_from_retention_guarantee() -> None:
    wiring = "forward_to prometheus.remote_write otelcol.receiver.otlp\n"
    answer = "A: default=8h; guaranteed_outage_retention=no; depends on WAL truncation and send lag.\nB: drops the batch"
    assert grade_scenario("obs-pipeline-alloy", wiring + answer)
    for wrong in (
        answer.replace("retention=no", "retention=yes"),
        answer.replace("default=8h", "default=2h"),
        "A: 8h of guaranteed outage retention.\nB: drops the batch",
    ):
        assert not grade_scenario("obs-pipeline-alloy", wiring + wrong)


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
