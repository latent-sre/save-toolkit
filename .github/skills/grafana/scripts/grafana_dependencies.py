"""Bounded, offline configuration references from masked Grafana captures.

No expression execution, network access, or health inference. PromQL AST selectors
identify explicit metric references; unresolved names remain visible as gaps.
Python 3.14+; promql-parser is loaded only for Prometheus expression inspection.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path
from runpy import run_path

_module = run_path(str(Path(__file__).with_name("grafana_modules.py")))["load_module"]
promql = _module("grafana_promql")

MAX_DASHBOARDS, MAX_ALERTS = 50, 100
MAX_NODES, MAX_EDGES, MAX_GAPS = 5000, 10000, 1000
MAX_PANELS, MAX_QUERIES, MAX_VARIABLES = 1000, 100, 200
MAX_TEXT = promql.MAX_TEXT
VARIABLE = promql.VARIABLE


def _id(kind, *parts):
    digest = hashlib.sha256(json.dumps(parts, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()[:24]
    return kind + ":" + digest


def _text(value):
    return value[:MAX_TEXT] if isinstance(value, str) else ""


def _scope(capture):
    return (_text(capture.get("grafana_url")), str(capture.get("organization_id", "unknown")))


def _model(capture):
    """The Classic model, or the reader's mapped panel view of a V2 dashboard."""
    return capture.get("panel_view", capture.get("dashboard", {}))


class _Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.gaps = []
        self.truncated = False

    def gap(self, code, source=None, **details):
        if len(self.gaps) < MAX_GAPS:
            self.gaps.append({"code": code, "source": source, **details})
        else:
            self.truncated = True

    def node(self, kind, *identity, **fields):
        key = _id(kind, *identity)
        if key not in self.nodes:
            if len(self.nodes) >= MAX_NODES:
                self.truncated = True
                return None
            self.nodes[key] = {"id": key, "kind": kind, **fields}
        return key

    def edge(self, source, target, relation):
        if source is None or target is None:
            return
        key = (source, target, relation)
        if key not in self.edges:
            if len(self.edges) >= MAX_EDGES:
                self.truncated = True
                return
            self.edges[key] = {"source": source, "target": target, "relation": relation}

    def bounded(self, items, limit, source, code):
        if not isinstance(items, list):
            self.gap("malformed_" + code, source)
            return []
        if len(items) > limit:
            self.truncated = True
            self.gap(code + "_truncated", source)
        return items[:limit]

    def variables(self, text, source, declared):
        for name in sorted({next(part for part in match if part) for match in VARIABLE.findall(text)}):
            if name.startswith("__"):
                continue
            if name in declared and declared[name] is not None:
                self.edge(source, declared[name], "uses_variable")
            else:
                self.gap("missing_variable", source, name=name)

    def datasource(self, value, source, scope, variables):
        if isinstance(value, dict):
            uid, kind = _text(value.get("uid")), _text(value.get("type"))
        elif isinstance(value, str):
            # Legacy strings are display-name references, not verified UIDs.
            uid, kind = value[:MAX_TEXT], ""
            if uid and uid not in ("__expr__", "-100", "-- Mixed --") and not VARIABLE.search(uid):
                target = self.node("datasource_reference", scope, uid, name=uid)
                self.edge(source, target, "references_datasource")
                self.gap("legacy_datasource_name_unresolved", source)
                return None, kind
        else:
            uid, kind = "", ""
        if uid in ("__expr__", "-100") or kind == "__expr__":
            return None, "__expr__"
        if VARIABLE.search(uid):
            self.variables(uid, source, variables)
            self.gap("unresolved_datasource_template", source, reference=uid)
            return None, kind
        if not uid or uid == "-- Mixed --" or kind == "mixed":
            self.gap("datasource_unresolved", source)
            return None, kind
        target = self.node("datasource", scope, uid, uid=uid, datasource_type=kind)
        self.edge(source, target, "uses_datasource")
        return target, kind

    def query(self, node, model, datasource, scope, variables, ref_nodes):
        raw_expression = model.get("expr", model.get("expression", ""))
        expression = _text(raw_expression)
        if node is not None:
            self.nodes[node]["expression"] = expression
        expression_truncated = isinstance(raw_expression, str) and len(raw_expression) > MAX_TEXT
        if expression_truncated:
            self.truncated = True
            self.gap("expression_truncated", node)
        ds, kind = self.datasource(datasource, node, scope, variables)
        if kind == "__expr__":
            expression_type = model.get("type")
            if expression_type in ("reduce", "resample", "threshold"):
                refs = [expression]
            elif expression_type == "math":
                refs = sorted({next(p for p in m if p) for m in VARIABLE.findall(expression)})
            elif expression_type == "classic_conditions":
                refs = []
                for condition in self.bounded(model.get("conditions", []), MAX_QUERIES, node, "conditions"):
                    params = condition.get("query", {}).get("params", []) if isinstance(condition, dict) and isinstance(condition.get("query", {}), dict) else []
                    if isinstance(params, list) and params and isinstance(params[0], str):
                        refs.append(params[0])
            else:
                refs = []
                self.gap("expression_query_dependencies_unresolved", node)
            for ref in refs:
                target = ref_nodes.get(ref)
                if target is None:
                    self.gap("missing_query_reference", node, ref_id=ref)
                else:
                    self.edge(node, target, "depends_on_query")
            return
        self.variables(expression, node, variables)
        if expression and kind == "prometheus" and ds:
            if expression_truncated:
                return
            analysis = promql.analyze(expression)
            self.truncated |= analysis.truncated
            for code in analysis.gaps:
                self.gap(code, node)
            for metric in analysis.metrics:
                target = self.node("metric", ds, metric, name=metric, datasource_id=ds)
                self.edge(node, target, "selects_metric")
                self.gap("recording_rule_and_backend_dependencies_unresolved", target)
        elif expression:
            self.gap("metric_extraction_unresolved", node)
        else:
            self.gap("query_expression_unavailable", node)

    def queries(self, models, owner, scope, variables, inherited, kind="query"):
        if owner is None:
            return {}
        models = self.bounded(models, MAX_QUERIES, owner, "queries")
        counts = Counter(_text(m.get("refId")) for m in models if isinstance(m, dict))
        refs, pending = {}, []
        for index, model in enumerate(models):
            if not isinstance(model, dict):
                self.gap("malformed_query", owner)
                continue
            ref = _text(model.get("refId"))
            valid = bool(ref) and counts[ref] == 1
            key = ("ref", ref) if valid else ("position", index)
            node = self.node(kind, owner, key, ref_id=ref, hidden=bool(model.get("hide", False)))
            self.edge(owner, node, "contains_query")
            if not valid:
                self.gap("ambiguous_query_reference", node, ref_id=ref)
            else:
                refs[ref] = node
            if kind == "alert_query":
                payload = model.get("model", {})
                payload = payload if isinstance(payload, dict) else {}
                ds = {"uid": model.get("datasourceUid"), "type": (payload.get("datasource", {}).get("type") if isinstance(payload.get("datasource"), dict) else "")}
            else:
                payload, ds = model, model.get("datasource", inherited)
            pending.append((node, payload, ds))
        for node, model, datasource in pending:
            self.query(node, model, datasource, scope, variables, refs)
        return refs


def _panels(graph, items, owner):
    """Iterative traversal avoids recursion on malformed nested rows."""
    pending = [(items, 0)]
    flattened = []
    while pending and len(flattened) < MAX_PANELS:
        current, depth = pending.pop()
        if depth > 50:
            graph.truncated = True
            graph.gap("panel_depth_truncated", owner)
            continue
        current = graph.bounded(current, MAX_PANELS - len(flattened), owner, "panels")
        for panel in current:
            if not isinstance(panel, dict):
                graph.gap("malformed_panel", owner)
                continue
            flattened.append(panel)
            if "panels" in panel:
                pending.append((panel["panels"], depth + 1))
    if pending:
        graph.truncated = True
        graph.gap("panels_truncated", owner)
    return flattened


def _dashboard(graph, capture, occurrence, ambiguous, panel_index, dashboard_index):
    dashboard = _model(capture)
    if not isinstance(dashboard, dict):
        graph.gap("malformed_dashboard")
        return
    uid, scope = _text(dashboard.get("uid")), _scope(capture)
    identity = ("uid", uid) if uid and not ambiguous else ("position", occurrence)
    owner = graph.node("dashboard", scope, identity, uid=uid, title=_text(dashboard.get("title")))
    if owner is None:
        return
    if not uid or ambiguous:
        graph.gap("ambiguous_dashboard_uid", owner)
    elif owner:
        dashboard_index[(scope, uid)] = owner
    if "spec" in dashboard or "elements" in dashboard or "panels" not in dashboard:
        graph.gap("unsupported_dashboard_model", owner)
        return
    variables = dashboard.get("templating", {})
    variables = variables.get("list", []) if isinstance(variables, dict) else []
    variables = graph.bounded(variables, MAX_VARIABLES, owner, "variables")
    counts = Counter(_text(v.get("name")) for v in variables if isinstance(v, dict))
    declared, pending = {}, []
    for index, variable in enumerate(variables):
        if not isinstance(variable, dict):
            graph.gap("malformed_variable", owner)
            continue
        name = _text(variable.get("name"))
        valid = bool(name) and counts[name] == 1
        node = graph.node("variable", owner, name if valid else index, name=name, variable_type=_text(variable.get("type")))
        graph.edge(owner, node, "declares_variable")
        if valid:
            declared[name] = node
        else:
            graph.gap("ambiguous_variable_name", node)
        pending.append((node, variable))
    for node, variable in pending:
        query = variable.get("query", "")
        expression = _text(query.get("query", "")) if isinstance(query, dict) else _text(query)
        graph.variables(expression, node, declared)
        if "datasource" in variable:
            graph.datasource(variable["datasource"], node, scope, declared)
        if node:
            graph.nodes[node]["expression"] = expression
        if variable.get("type") == "query":
            graph.gap("variable_query_backend_dependencies_unresolved", node)
    panels = _panels(graph, dashboard["panels"], owner)
    counts = Counter(p.get("id") for p in panels if type(p.get("id")) is int and p["id"] > 0)
    for index, panel in enumerate(panels):
        number = panel.get("id")
        valid = type(number) is int and number > 0 and counts[number] == 1
        node = graph.node("panel", owner, number if valid else "position:" + str(index), panel_id=number if type(number) is int else None, title=_text(panel.get("title")), panel_type=_text(panel.get("type")))
        if node is None:
            break
        graph.edge(owner, node, "contains_panel")
        if valid and uid and not ambiguous:
            panel_index[(scope, uid, str(number))] = node
        else:
            graph.gap("ambiguous_panel_id", node)
        if "libraryPanel" in panel:
            graph.gap("library_panel_not_expanded", node)
            library = panel["libraryPanel"]
            library_uid = _text(library.get("uid")) if isinstance(library, dict) else ""
            if library_uid:
                target = graph.node("library_panel_reference", scope, library_uid, uid=library_uid)
                graph.edge(node, target, "references_library_panel")
        if panel.get("repeat"):
            graph.variables("$" + _text(panel["repeat"]), node, declared)
            graph.gap("repeated_panel_not_expanded", node)
        graph.queries(panel.get("targets", []), node, scope, declared, panel.get("datasource"))
        if panel.get("transformations"):
            graph.gap("panel_transformations_not_evaluated", node)


def build_map(dashboards: list[dict], alerts: list[dict] | None = None) -> dict:
    """Return deterministic bounded references, never completeness or health claims."""
    graph = _Graph()
    inputs, panel_index, dashboard_index = [], {}, {}
    dashboards = graph.bounded(dashboards, MAX_DASHBOARDS, None, "dashboards")
    alerts = graph.bounded(alerts if alerts is not None else [], MAX_ALERTS, None, "alerts")
    counts = Counter((_scope(c), _text(_model(c).get("uid"))) for c in dashboards if isinstance(c, dict) and isinstance(_model(c), dict))
    for index, capture in enumerate(dashboards):
        if not isinstance(capture, dict):
            graph.gap("malformed_dashboard_capture")
            continue
        inputs.append(_provenance(graph, capture, "dashboard", index))
        dashboard = _model(capture)
        uid = _text(dashboard.get("uid")) if isinstance(dashboard, dict) else ""
        _dashboard(graph, capture, index, counts[(_scope(capture), uid)] > 1, panel_index, dashboard_index)
    counts = Counter((_scope(c), _text(c["rule"].get("uid"))) for c in alerts if isinstance(c, dict) and isinstance(c.get("rule"), dict))
    for index, capture in enumerate(alerts):
        if not isinstance(capture, dict) or not isinstance(capture.get("rule"), dict):
            graph.gap("malformed_alert_capture")
            continue
        inputs.append(_provenance(graph, capture, "alert", index))
        rule, scope = capture["rule"], _scope(capture)
        uid = _text(rule.get("uid"))
        valid = bool(uid) and counts[(scope, uid)] == 1
        node = graph.node("alert", scope, uid if valid else index, uid=uid, title=_text(rule.get("title")))
        if not valid:
            graph.gap("ambiguous_alert_uid", node)
        refs = graph.queries(rule.get("data", []), node, scope, {}, None, "alert_query")
        condition = _text(rule.get("condition"))
        if condition in refs:
            graph.edge(node, refs[condition], "evaluates_condition")
        else:
            graph.gap("alert_condition_unresolved", node)
        annotations = rule.get("annotations", {})
        if isinstance(annotations, dict) and "__dashboardUid__" in annotations:
            dashboard_uid = _text(annotations["__dashboardUid__"])
            number = str(annotations.get("__panelId__", ""))
            dashboard_target = dashboard_index.get((scope, dashboard_uid))
            if dashboard_target:
                graph.edge(node, dashboard_target, "annotates_dashboard")
            else:
                graph.gap("alert_dashboard_annotation_unresolved", node, dashboard_uid=dashboard_uid)
            target = panel_index.get((scope, dashboard_uid, number))
            if target:
                graph.edge(node, target, "annotates_panel")
            else:
                graph.gap("alert_panel_annotation_unresolved", node, dashboard_uid=dashboard_uid, panel_id=number)
    return {"schema_version": 1, "operation": "dependencies", "coverage": "configuration_references_only",
            "nodes": sorted(graph.nodes.values(), key=lambda n: n["id"]),
            "edges": [graph.edges[key] for key in sorted(graph.edges)], "gaps": graph.gaps,
            "inputs": inputs, "truncated": graph.truncated,
            "limits": {"dashboards": MAX_DASHBOARDS, "alerts": MAX_ALERTS, "nodes": MAX_NODES,
                       "edges": MAX_EDGES, "gaps": MAX_GAPS, "expression_characters": MAX_TEXT,
                       "promql_depth": promql.MAX_DEPTH, "promql_nodes": promql.MAX_NODES,
                       "promql_tokens": promql.MAX_TOKENS},
            "metric_extraction": "bounded_promql_ast_selectors",
            "limitations": ["No inventory completeness or health claim.",
                            "No recording rule, exporter, backend, or runtime dependencies resolved.",
                            "Library panels, repeated instances, and transformations are not expanded."]}


def _provenance(graph, capture, kind, index):
    result = {"kind": kind, "input_index": index}
    for key in ("grafana_url", "organization_id", "retrieved_at_utc", "provenance"):
        if key in capture:
            value = capture[key]
            if len(json.dumps(value, ensure_ascii=True)) > MAX_TEXT:
                result[key] = {"omitted": "provenance_size_limit"}
                graph.truncated = True
                graph.gap("provenance_truncated", input_kind=kind, input_index=index)
            else:
                result[key] = value
    if "grafana_url" not in capture or "organization_id" not in capture:
        graph.gap("input_scope_unspecified", input_kind=kind, input_index=index)
    return result
