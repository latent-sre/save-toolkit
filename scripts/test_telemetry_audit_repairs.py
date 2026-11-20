"""Bounded fixture checks for the repaired telemetry eval criteria."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from evals.graders import run_grader

ROOT = Path(__file__).resolve().parents[1]


def grade_scenario(name: str, response: str) -> bool:
    data = yaml.safe_load((ROOT / f"evals/scenarios/{name}-freegen-contract.yaml").read_text())
    for spec in data["graders"]:
        passed, detail = run_grader(spec, response)
        assert not detail.startswith("instrument:"), detail
        if not passed:
            return False
    return True


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


def test_cloud_logging_facts_stay_bound_to_their_fields() -> None:
    name = "obs-logs-gcp-gotchas"
    facts = {
        "required_retention_days": 400, "default_retention_days": 30,
        "calls_per_minute_per_project": 60, "quota_increasable": False,
        "routing_reason": "sink_exclusion", "generation_reason": "data_access_disabled",
    }
    assert grade_scenario(name, json.dumps(facts))
    for change in (
        {"required_retention_days": 30, "default_retention_days": 400},
        {"calls_per_minute_per_project": 600}, {"quota_increasable": True},
        {"routing_reason": "sink_includes_entry"}, {"generation_reason": "sink_exclusion"},
    ):
        assert not grade_scenario(name, json.dumps({**facts, **change})), change
    assert not grade_scenario(name, json.dumps(facts).replace("per_minute", "per_hour"))
    assert not grade_scenario(name, json.dumps(facts) + " The quota can be raised.")


ERRORS = 'sum by (app) (rate(http_requests_total{env="prod",status=~"5.."}[5m]))'
REQUESTS = 'sum by (app) (rate(http_requests_total{env="prod"}[5m]))'
BUCKETS = 'sum by (app, le) (rate(http_request_duration_seconds_bucket{env="prod"}[5m]))'


@pytest.mark.skipif(shutil.which("promtool") is None, reason="requires promtool on PATH")
def test_promql_grades_result_values_and_app_labels() -> None:
    name = "obs-metrics-promql"
    good = f"1. {ERRORS} / {REQUESTS}\n2. histogram_quantile(0.95, {BUCKETS})"
    assert grade_scenario(name, good)
    equivalent = (
        f"1)\n```promql\n{ERRORS} /\n{REQUESTS}\n```\n"
        f"2)\n```promql\nhistogram_quantile(0.95,\n{BUCKETS})\n```"
    ).replace("rate(", "increase(").replace("app, le", "le, app")
    assert grade_scenario(name, equivalent)
    for wrong in (
        good.replace("histogram_quantile(", "histogram_quantile(("),
        good.replace("by (app)", "by ()"),
        good.replace("app, le", "le"),
        good.replace('status=~"5.."', 'status="500"'),
        good.replace('status=~"5.."', 'status=~"50."'),
        good.replace(REQUESTS, REQUESTS.replace('{env="prod"}', "{}")),
        good.replace(ERRORS, ERRORS.replace("[5m]", "[2m]")),
        good.replace(BUCKETS, BUCKETS.replace("[5m]", "[2m]")),
        good.replace(REQUESTS, 'rate((sum by(app)(http_requests_total{env="prod"}))[5m:1m])'),
        good.replace(BUCKETS, BUCKETS.replace('{env="prod"}', "{}")),
        good.replace(BUCKETS, 'rate((sum by(app, le)(http_request_duration_seconds_bucket{env="prod"}))[5m:1m])'),
        good.replace("0.95", "0.5"),
    ):
        assert not grade_scenario(name, wrong), wrong


def test_missing_promtool_is_inconclusive(monkeypatch) -> None:
    monkeypatch.setenv("PATH", "")
    passed, detail = run_grader({"type": "obs_promql"}, "1. vector(1)\n2. vector(2)")
    assert not passed and detail.startswith("instrument:")


@pytest.mark.skipif(shutil.which("promtool") is None, reason="requires promtool on PATH")
@pytest.mark.parametrize("layout", ["titled fences", "numbered comments"])
def test_promql_accepts_two_labelled_queries_only(layout: str) -> None:
    ratio = f"{ERRORS} / {REQUESTS}"
    p95 = f"histogram_quantile(0.95, {BUCKETS})"
    if layout == "titled fences":
        answer = f"1. Five-minute error ratio by app\n```promql\n{ratio}\n```\n2. Request p95\n```promql\n{p95}\n```"
        extra = answer + f"\n```promql\n{p95}\n```"
        repeated = answer.replace("2. Request p95", "1. Request p95")
    else:
        answer = f"```promql\n# 1\n{ratio}\n# 2. Request p95\n{p95}\n```"
        extra = answer.removesuffix("```") + f"# 3\n{ratio}\n```"
        repeated = answer.replace("# 2.", "# 1.")
    for response, expected in ((answer, True), (extra, False), (repeated, False)):
        assert grade_scenario("obs-metrics-promql", response) is expected, response
