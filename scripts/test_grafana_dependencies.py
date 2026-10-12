"""Configuration-only dependency graph behavior."""

import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "skills/grafana/scripts/grafana_dependencies.py"


def load_module():
    spec = importlib.util.spec_from_file_location("grafana_dependencies", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dashboard(uid="one", panels=None, variables=None):
    return {"dashboard": {"uid": uid, "title": uid, "panels": panels or [],
                          "templating": {"list": variables or []}}, "provenance": {"org": 1}}


def panel(id_=1, expr='up{job="gpu"}', **extra):
    return {"id": id_, "datasource": {"uid": "prom", "type": "prometheus"},
            "targets": [{"refId": "A", "expr": expr}], **extra}


def test_same_metric_shared_across_panels_and_stable():
    module = load_module()
    inputs = [dashboard(panels=[panel(), panel(2)])]
    result = module.build_map(inputs)
    assert result == module.build_map(inputs)
    assert result["coverage"] == "configuration_references_only"
    metrics = [n for n in result["nodes"] if n["kind"] == "metric"]
    assert len(metrics) == 1 and metrics[0]["name"] == "up"
    assert len([e for e in result["edges"] if e["relation"] == "selects_metric"]) == 2
    assert result["inputs"][0]["provenance"] == {"org": 1}


def test_complex_promql_does_not_invent_function_or_label_metrics():
    result = load_module().build_map([dashboard(panels=[panel(expr='sum(rate(requests{job="sum"}[5m])) by (job)')])])
    assert not [n for n in result["nodes"] if n["kind"] == "metric"]
    assert any(g["code"] == "metric_extraction_unresolved" for g in result["gaps"])
    query = next(n for n in result["nodes"] if n["kind"] == "query")
    assert query["expression"].startswith("sum(rate")


def test_name_selector_and_template_datasource_are_not_fake_uids():
    module = load_module()
    first = panel(expr='{__name__="gpu_watts",host="$host"}')
    second = panel(2, datasource={"uid": "$source", "type": "prometheus"})
    result = module.build_map([dashboard(panels=[first, second], variables=[{"name": "source", "type": "datasource"}])])
    assert any(n["kind"] == "metric" and n["name"] == "gpu_watts" for n in result["nodes"])
    assert not any(n["kind"] == "datasource" and n.get("uid") == "$source" for n in result["nodes"])
    assert any(g["code"] == "missing_variable" and g["name"] == "host" for g in result["gaps"])
    assert any(g["code"] == "unresolved_datasource_template" for g in result["gaps"])


def test_alert_ref_dependencies_and_panel_annotation():
    rule = {"rule": {"uid": "alert", "condition": "B", "annotations": {"__dashboardUid__": "one", "__panelId__": "1"},
                     "data": [{"refId": "A", "datasourceUid": "prom", "model": {"expr": "up", "datasource": {"type": "prometheus"}}},
                              {"refId": "B", "datasourceUid": "__expr__", "model": {"type": "reduce", "expression": "A"}}]}}
    result = load_module().build_map([dashboard(panels=[panel()])], [rule])
    assert any(e["relation"] == "depends_on_query" for e in result["edges"])
    assert any(e["relation"] == "annotates_panel" for e in result["edges"])
    assert any(e["relation"] == "annotates_dashboard" for e in result["edges"])
    assert not any(n["kind"] == "datasource" and n.get("uid") == "__expr__" for n in result["nodes"])


def test_duplicates_nested_rows_and_library_repeat_are_explicit():
    nested = {"id": 10, "type": "row", "panels": [panel(), panel()]}
    result = load_module().build_map([dashboard(panels=[nested, panel(2, repeat="host", libraryPanel={"uid": "lib"})])])
    codes = {g["code"] for g in result["gaps"]}
    assert {"ambiguous_panel_id", "library_panel_not_expanded", "repeated_panel_not_expanded"} <= codes
    assert any(e["relation"] == "references_library_panel" for e in result["edges"])
    panels = [n for n in result["nodes"] if n["kind"] == "panel"]
    assert len(panels) == 4 and len({n["id"] for n in panels}) == 4


def test_v2_and_bounded_inputs():
    module = load_module()
    result = module.build_map([{"dashboard": {"uid": "v2", "kind": "Dashboard", "spec": {"elements": {}}}}])
    assert any(g["code"] == "unsupported_dashboard_model" for g in result["gaps"])
    result = module.build_map([dashboard(str(i)) for i in range(51)])
    assert result["truncated"] is True
    assert len(result["inputs"]) == 50


def test_node_cap_has_no_dangling_edges():
    module = load_module()
    module.MAX_NODES = 5
    result = module.build_map([dashboard(panels=[panel(i) for i in range(10)])])
    assert result["truncated"] and len(result["nodes"]) <= 5
    ids = {n["id"] for n in result["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in result["edges"])


@pytest.mark.parametrize("expression", ['up + down', 'up{job="gpu"} / 2', 'label_replace(up,"x","y","z","w")',
                                         '{__name__=~"up|down"}', 'up{job="gpu" missing="comma"}'])
def test_complex_or_invalid_selector_has_no_guessed_metric(expression):
    result = load_module().build_map([dashboard(panels=[panel(expr=expression)])])
    assert not [n for n in result["nodes"] if n["kind"] == "metric"]


def test_scope_separates_identical_uids():
    first, second = dashboard(panels=[panel()]), dashboard(panels=[panel()])
    first.update(grafana_url="https://one.invalid", organization_id=1)
    second.update(grafana_url="https://two.invalid", organization_id=1)
    result = load_module().build_map([first, second])
    assert len([n for n in result["nodes"] if n["kind"] == "datasource"]) == 2
    assert len([n for n in result["nodes"] if n["kind"] == "metric"]) == 2
    assert not any(g["code"] == "ambiguous_dashboard_uid" for g in result["gaps"])


def test_duplicate_dashboard_does_not_resolve_alert_annotation():
    result = load_module().build_map([dashboard(panels=[panel()]), dashboard(panels=[panel()])],
                                    [{"rule": {"uid": "alert", "annotations": {"__dashboardUid__": "one", "__panelId__": "1"}}}])
    assert not any(e["relation"] == "annotates_panel" for e in result["edges"])
    assert any(g["code"] == "ambiguous_dashboard_uid" for g in result["gaps"])


def test_malformed_and_oversized_provenance_do_not_claim_complete():
    capture = dashboard(panels=[None, {"id": [], "targets": [None]}])
    capture["provenance"] = {"text": "x" * 20000}
    result = load_module().build_map([None, capture, {"dashboard": []}], [None])
    assert result["truncated"]
    codes = {g["code"] for g in result["gaps"]}
    assert {"malformed_dashboard_capture", "malformed_panel", "malformed_query", "malformed_alert_capture", "provenance_truncated"} <= codes


def test_variable_dependencies_and_ambiguous_query_refs():
    inputs = dashboard(variables=[{"name": "host", "type": "query", "query": 'label_values(up{job="$job"}, host)',
                                   "datasource": {"uid": "prom", "type": "prometheus"}}, {"name": "job", "type": "custom"}],
                       panels=[panel(targets=[{"refId": "A", "expr": "up"}, {"refId": "A", "expr": "down"},
                                              {"refId": "B", "datasource": {"uid": "__expr__"}, "expression": "A", "type": "reduce"}])])
    result = load_module().build_map([inputs])
    assert any(e["relation"] == "uses_variable" for e in result["edges"])
    assert not any(e["relation"] == "depends_on_query" for e in result["edges"])
    assert any(g["code"] == "missing_query_reference" for g in result["gaps"])


def test_reverse_impact_reaches_owners_with_resolvable_evidence_refs():
    module = load_module()
    graph = module.build_map([dashboard(panels=[panel(), panel(2)])])
    result = module.reverse_impact(graph, kind="metric", key="up")
    assert result["status"] == "selected"
    assert {item["node"]["kind"] for item in result["references"]} == {"query", "panel", "dashboard"}
    assert len(result["references"]) == 5
    for item in result["references"]:
        assert graph["nodes"][int(item["evidence_ref"].split("/")[-1])]["id"] == item["node"]["id"]
        edge = graph["edges"][int(item["via"]["evidence_ref"].split("/")[-1])]
        assert edge["source"] == item["node"]["id"] and edge["target"] == item["via"]["target"]
    assert result["source_gaps"]  # Backend/recording-rule gaps remain visible.
    assert result["health"] == "not_assessed"


def test_reverse_impact_ambiguous_scope_requires_exact_id():
    module = load_module()
    first, second = dashboard(panels=[panel()]), dashboard(panels=[panel()])
    first.update(grafana_url="https://one.invalid", organization_id=1)
    second.update(grafana_url="https://two.invalid", organization_id=1)
    graph = module.build_map([first, second])
    result = module.reverse_impact(graph, kind="datasource", key="prom")
    assert result["status"] == "ambiguous" and result["references"] == []
    selected = module.reverse_impact(graph, node_id=result["matches"][0]["id"])
    assert selected["status"] == "selected" and len(selected["references"]) == 3
    assert module.reverse_impact(graph, kind="metric", key="missing")["status"] == "not_found"


def test_reverse_impact_caps_cycles_and_does_not_invent_complex_metric():
    module = load_module()
    graph = module.build_map([dashboard(panels=[panel(expr="sum(rate(up[5m]))")])])
    result = module.reverse_impact(graph, kind="metric", key="up")
    assert result["status"] == "not_found" and result["source_gaps"]
    graph = module.build_map([dashboard(panels=[panel()])])
    result = module.reverse_impact(graph, kind="metric", key="up", max_results=1)
    assert len(result["references"]) == 1 and result["truncated"]
    graph["edges"].append({"source": graph["nodes"][0]["id"], "target": graph["nodes"][0]["id"], "relation": "cycle"})
    assert module.reverse_impact(graph, node_id=graph["nodes"][0]["id"])["status"] == "selected"


@pytest.mark.parametrize("selection", [{}, {"node_id": "x", "kind": "metric", "key": "up"},
                                       {"kind": "unknown", "key": "x"}, {"kind": "metric", "key": "up", "max_results": 0}])
def test_reverse_impact_rejects_invalid_selection(selection):
    with pytest.raises(ValueError):
        load_module().reverse_impact({"schema_version": 1, "operation": "dependencies", "nodes": [], "edges": []}, **selection)


def test_reverse_impact_rejects_dangling_and_duplicate_nodes():
    module = load_module()
    graph = module.build_map([dashboard(panels=[panel()])])
    graph["edges"].append({"source": "missing", "target": graph["nodes"][0]["id"], "relation": "bad"})
    with pytest.raises(ValueError, match="invalid_dependency_graph"):
        module.reverse_impact(graph, kind="metric", key="up")


def test_reverse_impact_preserves_discovery_truncation():
    module = load_module()
    graph = module.build_map([dashboard(panels=[panel()])])
    graph["discovery"] = {"truncated": True, "coverage": "permission_scoped"}
    result = module.reverse_impact(graph, kind="metric", key="up")
    assert result["source_truncated"] and result["truncated"]
    assert graph["nodes"][int(result["selected_evidence_ref"].split("/")[-1])]["name"] == "up"
