#!/usr/bin/env python3
"""Offline, bounded agent evidence views of captured Grafana data.

No telemetry reads, expression execution, or health inference. Source JSON pointers
let an agent inspect the supporting capture rather than treating a digest as proof.
"""

import json
from pathlib import Path
from runpy import run_path

MAX_PANELS, MAX_TARGETS, MAX_FINDINGS = 50, 100, 1000
MAX_VALUE_BYTES, MAX_MODEL_BYTES = 65536, 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024


# Load trusted sibling code once. analyze_capture itself performs no file/network I/O.
_module = run_path(str(Path(__file__).with_name('grafana_modules.py')))['load_module']
hygiene = _module('dashboard_hygiene')
dependencies = _module('grafana_dependencies')
frames = _module('grafana_frames')


def _copy(value, limit=MAX_VALUE_BYTES):
    data, size = [], 0
    try:
        for chunk in json.JSONEncoder(ensure_ascii=True, allow_nan=False).iterencode(value):
            size += len(chunk)
            if size > limit:
                raise ValueError("analysis_value_limit")
            data.append(chunk)
        return json.loads("".join(data))
    except (TypeError, RecursionError):
        raise ValueError("invalid_analysis_value") from None


def _value(value, pointer, gaps):
    try:
        return _copy(value)
    except ValueError:
        gaps.append({"code": "value_omitted", "evidence_ref": pointer})
        return {"omitted": "value_limit_or_invalid", "evidence_ref": pointer}


def _source_gaps(report):
    gaps = report.get("gaps", [])
    if not isinstance(gaps, list):
        return [{"code": "malformed_source_gaps", "evidence_ref": "/gaps"}]
    result = [{"code": "source_gap", "evidence_ref": f"/gaps/{i}",
               "detail": _value(gap, f"/gaps/{i}", [])} for i, gap in enumerate(gaps[:100])]
    if len(gaps) > 100:
        result.append({"code": "source_gaps_truncated", "evidence_ref": "/gaps"})
    return result


def _captures(report):
    if report.get("operation") == "dependencies":
        captures = report.get("dashboard_captures")
        if isinstance(captures, list):
            return [(capture, f"/dashboard_captures/{index}") for index, capture in enumerate(captures[:50])], len(captures) > 50
        return [], False
    capture = report.get("dashboard_capture")
    if isinstance(capture, dict):
        return [(capture, "/dashboard_capture")], False
    if isinstance(report.get("dashboard"), dict):
        provenance = report.get("provenance", {})
        capture = {"dashboard": report["dashboard"]}
        if isinstance(provenance, dict):
            capture.update({key: provenance[key] for key in ("grafana_url", "organization_id", "retrieved_at_utc") if key in provenance})
        return [(capture, "")], False
    return [], False


def _hygiene(captures):
    results = []
    for capture, pointer in captures:
        item = {"evidence_ref": pointer + "/dashboard", "coverage": "static_hygiene_only", "ok": False,
                "findings": [], "query_analysis": [], "gaps": []}
        results.append(item)
        try:
            if not isinstance(capture, dict) or not isinstance(capture.get("dashboard"), dict):
                raise ValueError("dashboard_model_unavailable")
            model = _copy(capture["dashboard"], MAX_MODEL_BYTES)
            spec, _ = hygiene.locate_spec(model)
            if "elements" in spec or "layout" in spec or "panels" not in spec:
                raise ValueError("unsupported_dashboard_model")
            checked = hygiene.validate_shape(spec)
            query_analysis = []
            findings = hygiene.check(spec, query_analysis=query_analysis)
            item.update(ok=True, panel_count=len(checked), finding_count=len(findings),
                        findings=[{**finding.as_report(), "evidence_ref": pointer + "/dashboard"}
                                  for finding in findings[:MAX_FINDINGS]],
                        query_analysis_count=len(query_analysis),
                        query_analysis=[{**query, "evidence_ref": pointer + "/dashboard"}
                                        for query in query_analysis[:MAX_FINDINGS]],
                        truncated=len(findings) > MAX_FINDINGS or len(query_analysis) > MAX_FINDINGS)
            if len(findings) > MAX_FINDINGS:
                item["gaps"].append("hygiene_findings_truncated")
            if len(query_analysis) > MAX_FINDINGS:
                item["gaps"].append("hygiene_query_analysis_truncated")
        except (ValueError, RecursionError, TypeError):
            item["gaps"].append("hygiene_input_unsupported_or_over_limit")
    return {"coverage": "static_hygiene_only", "dashboards": results,
            "limitations": ["Findings are configuration heuristics, not service health or query validation."]}


def _summary(report):
    result = {"coverage": "stored_query_evidence_only", "health": "not_assessed", "panels": [], "gaps": [],
              "query_status_counts": {}, "truncated": False}
    panels = report.get("panels")
    if not isinstance(panels, list):
        result["gaps"].append({"code": "panel_evidence_unavailable", "evidence_ref": "/panels"})
        return result
    if len(panels) > MAX_PANELS:
        result["truncated"] = True
        result["gaps"].append({"code": "panel_digest_limit_reached", "evidence_ref": "/panels"})
    count = 0
    statistics = frames.FrameStatistics()
    for index, panel in enumerate(panels[:MAX_PANELS]):
        pointer = f"/panels/{index}"
        if not isinstance(panel, dict):
            result["gaps"].append({"code": "malformed_panel_evidence", "evidence_ref": pointer})
            continue
        item = {"evidence_ref": pointer, "targets": [], "gaps": []}
        for key in ("id", "title", "type", "status", "coverage", "gaps", "render"):
            if key in panel:
                item[key] = _value(panel[key], pointer + "/" + key, result["gaps"])
        render = panel.get("render")
        if isinstance(render, dict) and render.get("status") == "image_uninspected":
            item["next_action"] = "inspect_render"
            item["appearance"] = "not_assessed"
            item["render_evidence_ref"] = pointer + "/render"
        if "fallback_reason" in panel:
            item["fallback_reason"] = _value(panel["fallback_reason"], pointer + "/fallback_reason", result["gaps"])
        result["panels"].append(item)
        targets = panel.get("targets", [])
        if not isinstance(targets, list):
            result["gaps"].append({"code": "malformed_target_evidence", "evidence_ref": pointer + "/targets"})
            continue
        for target_index, target in enumerate(targets):
            if count >= MAX_TARGETS:
                result["truncated"] = True
                result["gaps"].append({"code": "query_digest_limit_reached", "evidence_ref": pointer + "/targets"})
                break
            count += 1
            ref = pointer + f"/targets/{target_index}"
            if not isinstance(target, dict):
                result["gaps"].append({"code": "malformed_target_evidence", "evidence_ref": ref})
                continue
            status = target.get("status")
            status = status[:100] if isinstance(status, str) else "unknown"
            result["query_status_counts"][status] = result["query_status_counts"].get(status, 0) + 1
            digest = {"evidence_ref": ref, "status": status}
            for key in ("ref_id", "mode", "error", "evidence_status", "omitted"):
                if key in target:
                    digest[key] = _value(target[key], ref + "/" + key, result["gaps"])
            if target.get("evidence_status") == "omitted_export_budget":
                result["gaps"].append({"code": "query_evidence_omitted_export_budget", "evidence_ref": ref + "/evidence_status"})
            query = target.get("result")
            if isinstance(query, dict):
                digest["result_evidence_ref"] = ref + "/result"
                digest["series_statistics"] = statistics.summarize(query, ref + "/result")
                for key in ("summary", "grafana_url", "organization_id", "retrieved_at_utc", "from_ms", "to_ms",
                            "from", "to", "datasource", "kind", "evaluation_time_ms", "datasource_uid",
                            "expression", "mode", "limits", "coverage", "provenance"):
                    if key in query:
                        digest[key] = _value(query[key], ref + "/result/" + key, result["gaps"])
                if "summary" not in query:
                    result["gaps"].append({"code": "query_summary_unavailable", "evidence_ref": ref + "/result"})
            elif status in ("values_returned", "no_data", "all_null", "unsupported_result"):
                result["gaps"].append({"code": "query_result_unavailable", "evidence_ref": ref})
            item["targets"].append(digest)
    result["queries_in_digest"] = count
    return result


def analyze_capture(report, *, analysis="all"):
    """Return bounded JSON for agents; all evidence references point into the input report.

    Modes: summary, hygiene, dependencies, all. Does not verify file integrity: callers
    loading packages must verify their manifest before passing the captured dictionary.
    """
    if analysis not in ("summary", "hygiene", "dependencies", "all"):
        raise ValueError("unsupported_analysis")
    if (not isinstance(report, dict) or report.get("schema_version") != 1
            or report.get("operation") not in ("investigate", "dependencies")):
        raise ValueError("unsupported_capture")
    result = {"schema_version": 1, "operation": "analyze", "analysis": analysis,
              "coverage": "captured_evidence_only", "health": "not_assessed", "evidence_root": "source_report",
              "gaps": _source_gaps(report), "limits": {"panels": MAX_PANELS, "queries": MAX_TARGETS,
                                                       "value_bytes": MAX_VALUE_BYTES, "output_bytes": MAX_OUTPUT_BYTES},
              "limitations": ["No new collection, expression execution, health assessment, or authenticity verification."]}
    for key in ("provenance", "from_ms", "to_ms", "variables", "coverage", "health", "evidence"):
        if key in report:
            result["source_" + key] = _value(report[key], "/" + key, result["gaps"])
    captures, truncated = _captures(report)
    if truncated:
        result["gaps"].append({"code": "dashboard_capture_limit_reached", "evidence_ref": "/dashboard_captures"})
    if analysis in ("summary", "all"):
        result["summary"] = _summary(report)
    if analysis in ("hygiene", "dependencies", "all") and not captures:
        result["gaps"].append({"code": "dashboard_capture_unavailable", "evidence_ref": ""})
    if analysis in ("hygiene", "all"):
        result["hygiene"] = _hygiene(captures)
    if analysis in ("dependencies", "all"):
        alerts = report.get("alert_captures", [])
        if (report["operation"] == "dependencies" and isinstance(report.get("nodes"), list)
                and isinstance(report.get("edges"), list)):
            # Export fitting may omit raw captures while retaining their derived graph.
            # Rebuilding also loses collection gaps even when those captures remain.
            result["dependencies"] = {key: report[key] for key in (
                "schema_version", "operation", "coverage", "nodes", "edges", "gaps", "inputs", "truncated",
                "limits", "metric_extraction", "limitations", "discovery", "provenance", "folder_uid", "evidence",
            ) if key in report}
            result["dependencies"]["evidence_ref"] = ""
        elif (report["operation"] == "dependencies" and not captures
              and not (isinstance(alerts, list) and alerts)):
            result["dependencies"] = {"omitted": "dependency_graph_unavailable", "evidence_ref": ""}
            result["gaps"].append({"code": "dependency_graph_unavailable", "evidence_ref": ""})
        else:
            result["dependencies"] = dependencies.build_map([capture for capture, _ in captures], alerts)
            if "alert_captures" not in report:
                result["dependencies"]["gaps"].append({"code": "alert_definitions_not_captured", "source": None})
        result["dependencies"]["capture_evidence_refs"] = [pointer for _, pointer in captures]
    # Enforce a final bound across individually bounded sections. Preserve the source
    # reference and an explicit gap if a section cannot fit; never return cut JSON.
    for key in ("summary", "hygiene", "dependencies"):
        if key in result:
            try:
                result[key] = _copy(result[key], MAX_OUTPUT_BYTES // 3)
            except ValueError:
                result[key] = {"omitted": "analysis_section_limit", "evidence_ref": ""}
                result["gaps"].append({"code": "analysis_section_limit", "section": key, "evidence_ref": ""})
    try:
        return _copy(result, MAX_OUTPUT_BYTES)
    except ValueError:
        return {"schema_version": 1, "operation": "analyze", "analysis": analysis,
                "coverage": "captured_evidence_only", "health": "not_assessed",
                "gaps": [{"code": "analysis_output_limit", "evidence_ref": ""}]}
