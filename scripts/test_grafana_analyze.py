"""Agent evidence digests preserve gaps, provenance, and offline boundaries."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "skills/grafana/scripts/grafana_analyze.py"


def load_module():
    spec = importlib.util.spec_from_file_location("grafana_analyze", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def capture():
    model = {"uid": "example", "title": "Example", "panels": [
        {"id": 1, "type": "stat", "title": "Count", "targets": [{"refId": "A", "expr": "up"}],
         "datasource": {"uid": "prom", "type": "prometheus"}}]}
    return {"schema_version": 1, "operation": "investigate", "dashboard": model,
            "dashboard_capture": {"dashboard": model, "grafana_url": "https://metrics.invalid", "organization_id": 2},
            "provenance": {"grafana_url": "https://metrics.invalid", "organization_id": 2},
            "from_ms": 1000, "to_ms": 60000, "gaps": ["reads_are_not_an_atomic_snapshot"],
            "panels": [{"id": 1, "title": "Count", "status": "mixed", "gaps": ["transformations_not_applied"],
                        "targets": [{"ref_id": "A", "mode": "range", "status": "values_returned", "result": {
                            "grafana_url": "https://metrics.invalid", "organization_id": 2,
                            "summary": {"status": "complete", "row_count": 2, "series": [{"min": 0, "max": 1}]},
                            "response": {"opaque": "not part of digest"}}},
                                    {"ref_id": "B", "status": "unsupported", "error": "unsupported_query_format"},
                                    {"ref_id": "C", "status": "no_data", "result": {"summary": {"status": "complete", "row_count": 0}}}]}]}


def pointer(document, ref):
    for token in ref.split("/")[1:]:
        document = document[int(token)] if isinstance(document, list) else document[token.replace("~1", "/").replace("~0", "~")]
    return document


def test_summary_preserves_status_gaps_provenance_and_refs_without_raw_frames():
    source = capture()
    original = copy.deepcopy(source)
    report = load_module().analyze_capture(source, analysis="summary")
    assert source == original
    assert report["health"] == "not_assessed"
    assert report["source_provenance"]["organization_id"] == 2
    summary = report["summary"]
    assert summary["query_status_counts"] == {"values_returned": 1, "unsupported": 1, "no_data": 1}
    assert summary["panels"][0]["gaps"] == ["transformations_not_applied"]
    assert report["gaps"][0]["detail"] == "reads_are_not_an_atomic_snapshot"
    for target in summary["panels"][0]["targets"]:
        assert pointer(source, target["evidence_ref"])["status"] == target["status"]
        if "summary" in target:
            assert pointer(source, target["result_evidence_ref"])["summary"] == target["summary"]
        assert "response" not in target


def test_all_analysis_is_offline_and_hygiene_structured(monkeypatch):
    module = load_module()
    def forbidden(*args, **kwargs):
        raise AssertionError("analysis performed I/O or execution")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    report = module.analyze_capture(capture())
    hygiene = report["hygiene"]["dashboards"][0]
    assert hygiene["ok"] and hygiene["coverage"] == "static_hygiene_only"
    assert any(f["rule"] == "panel-units" for f in hygiene["findings"])
    assert all(pointer(capture(), f["evidence_ref"]) for f in hygiene["findings"])
    assert any(n["kind"] == "metric" and n["name"] == "up" for n in report["dependencies"]["nodes"])
    assert report["dependencies"]["capture_evidence_refs"] == ["/dashboard_capture"]
    assert any(g["code"] == "alert_definitions_not_captured" for g in report["dependencies"]["gaps"])


def test_missing_result_is_gap_never_converted_to_no_data():
    source = capture()
    source["panels"][0]["targets"][0].pop("result")
    report = load_module().analyze_capture(source, analysis="summary")["summary"]
    assert report["panels"][0]["targets"][0]["status"] == "values_returned"
    assert report["gaps"][0]["code"] == "query_result_unavailable"


def test_export_omissions_remain_explicit_alongside_observed_status():
    source = capture()
    source["evidence"] = {"status": "partial", "reason": "export_budget_exhausted", "omitted": [{"panel_id": 1, "ref_id": "A"}]}
    target = source["panels"][0]["targets"][0]
    target.pop("result")
    target["evidence_status"] = "omitted_export_budget"
    report = load_module().analyze_capture(source, analysis="summary")
    assert report["source_evidence"] == source["evidence"]
    digest = report["summary"]["panels"][0]["targets"][0]
    assert digest["status"] == "values_returned" and digest["evidence_status"] == "omitted_export_budget"
    assert any(g["code"] == "query_evidence_omitted_export_budget" for g in report["summary"]["gaps"])


def test_fallback_render_is_an_inspection_action_not_appearance_or_health_claim():
    source = capture()
    source["panels"][0]["render"] = {"status": "image_uninspected", "image_file": "panel-1.png",
                                     "receipt": {"image_path": "/private/panel-1.png"},
                                     "fallback_reason": ["unsupported_result"]}
    item = load_module().analyze_capture(source, analysis="summary")["summary"]["panels"][0]
    assert item["next_action"] == "inspect_render" and item["appearance"] == "not_assessed"
    assert item["render"]["image_file"] == "panel-1.png"
    assert item["render"]["receipt"]["image_path"] == "/private/panel-1.png"
    assert item["render"]["fallback_reason"] == ["unsupported_result"]
    assert pointer(source, item["render_evidence_ref"])["status"] == "image_uninspected"


@pytest.mark.parametrize("model", [{"elements": {}}, {"panels": "wrong"}, {"panels": [{"type": "stat", "title": []}]}])
def test_hygiene_unsupported_model_never_clean(model):
    source = capture()
    source["dashboard_capture"]["dashboard"] = model
    report = load_module().analyze_capture(source, analysis="hygiene")
    result = report["hygiene"]["dashboards"][0]
    assert not result["ok"] and result["gaps"]


def test_hygiene_keeps_query_method_and_template_gaps_with_source_pointers():
    source = capture()
    source['dashboard_capture']['dashboard']['panels'][0]['targets'] = [
        {'refId': 'A', 'expr': 'up{requests_total="label"}'},
        {'refId': 'B', 'expr': 'rate(requests_total[$__rate_interval])'},
    ]
    result = load_module().analyze_capture(source, analysis='hygiene')['hygiene']['dashboards'][0]
    assert result['query_analysis_count'] == 2
    assert [query['mode'] for query in result['query_analysis']] == ['promql_ast', 'text_heuristic']
    assert result['query_analysis'][1]['gaps'] == ['promql_template_unresolved']
    assert all(pointer(source, query['evidence_ref']) for query in result['query_analysis'])
    assert not any(finding['rule'] == 'target-counter-agg' for finding in result['findings'])


def test_hygiene_query_method_details_are_bounded(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, 'MAX_FINDINGS', 1)
    source = capture()
    source['dashboard_capture']['dashboard']['panels'][0]['targets'] = [
        {'refId': 'A', 'expr': 'up'}, {'refId': 'B', 'expr': 'process_start_time_seconds'},
    ]
    result = module.analyze_capture(source, analysis='hygiene')['hygiene']['dashboards'][0]
    assert result['query_analysis_count'] == 2
    assert len(result['query_analysis']) == 1
    assert result['truncated'] is True
    assert 'hygiene_query_analysis_truncated' in result['gaps']


def test_bounds_produce_explicit_gaps():
    source = capture()
    source["panels"][0]["targets"][0]["result"]["summary"]["large"] = "x" * 70000
    source["panels"] *= 51
    report = load_module().analyze_capture(source, analysis="summary")
    summary = report["summary"]
    assert summary["truncated"] and len(summary["panels"]) == 50
    assert summary["queries_in_digest"] == 100
    assert {"value_omitted", "panel_digest_limit_reached", "query_digest_limit_reached"} <= {g["code"] for g in summary["gaps"]}
    assert len(json.dumps(report)) < 8 * 1024 * 1024


def test_dependencies_capture_and_missing_capture():
    module = load_module()
    source = {"schema_version": 1, "operation": "dependencies", "dashboard_captures": [capture()["dashboard_capture"]], "alert_captures": []}
    report = module.analyze_capture(source)
    assert report["dependencies"]["capture_evidence_refs"] == ["/dashboard_captures/0"]
    assert report["summary"]["gaps"][0]["code"] == "panel_evidence_unavailable"
    source.pop("dashboard_captures")
    assert any(g["code"] == "dashboard_capture_unavailable" for g in module.analyze_capture(source)["gaps"])


@pytest.mark.parametrize("source", [None, [], {"schema_version": 99, "operation": "investigate"}, {"schema_version": 1, "operation": "alert-preview"}])
def test_unsupported_capture_rejected(source):
    with pytest.raises(ValueError, match="unsupported_capture"):
        load_module().analyze_capture(source)


def test_named_modes_only():
    with pytest.raises(ValueError, match="unsupported_analysis"):
        load_module().analyze_capture(capture(), analysis="eval")


def test_summary_adds_raw_sample_statistics_without_replacing_captured_summary():
    source = capture()
    query = source["panels"][0]["targets"][0]["result"]
    query["results"] = {"A": {"frames": [{
        "schema": {"fields": [{"type": "number", "name": "load", "labels": {"host": "example"}}]},
        "data": {"values": [[1, None, 3, 5]]},
    }]}}
    report = load_module().analyze_capture(source, analysis="summary")
    digest = report["summary"]["panels"][0]["targets"][0]
    assert digest["summary"] == query["summary"]
    series = digest["series_statistics"]["series"][0]
    assert series["statistics"]["mean"] == 3 and series["statistics"]["stddev_sample"] == 2
    assert pointer(source, series["evidence_ref"]) == [1, None, 3, 5]
    assert pointer(source, series["field_evidence_ref"])["labels"] == series["labels"]
    assert report["health"] == "not_assessed"


def test_summary_only_capture_explicitly_lacks_raw_statistics():
    digest = load_module().analyze_capture(capture(), analysis="summary")["summary"]["panels"][0]["targets"][0]
    assert digest["series_statistics"]["status"] == "unavailable"
    assert digest["series_statistics"]["gaps"] == [{
        "code": "raw_query_results_unavailable", "evidence_ref": "/panels/0/targets/0/result",
    }]
