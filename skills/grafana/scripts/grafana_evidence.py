"""Write an offline, private evidence package from an already-masked report.

Telemetry remains sensitive. This module does not load credentials, fetch URLs,
read paths from report content, or establish health or visual verification.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import struct
from pathlib import Path

MAX_REPORT_BYTES = 32 * 1024 * 1024
MAX_PACKAGE_BYTES = 96 * 1024 * 1024
MAX_HTML_BYTES = 2 * 1024 * 1024


def _bounded_json(value: object) -> bytes:
    result = bytearray()
    for chunk in json.JSONEncoder(ensure_ascii=False, indent=2, allow_nan=False).iterencode(value):
        for offset in range(0, len(chunk), 65536):
            encoded = chunk[offset:offset + 65536].encode("utf-8")
            if len(result) + len(encoded) + 1 > MAX_REPORT_BYTES:
                raise ValueError("Report JSON size limit exceeded (32 MiB)")
            result.extend(encoded)
    result.extend(b"\n")
    return bytes(result)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _details(title: str, value: object) -> str:
    return f"<details><summary>{_escape(title)}</summary><pre>{_escape(_json(value))}</pre></details>"


def _query_overview(result: dict) -> str:
    summary = result.get("summary") or {}
    if not summary:
        return "<p>Numeric summary unavailable; inspect query evidence.</p>"
    output = [f"<p>Summary parsing: {_escape(summary.get('status', 'unknown'))}. "
              f"Actual timestamps (epoch ms): {_escape(summary.get('timestamp_min_ms', 'unavailable'))} "
              f"to {_escape(summary.get('timestamp_max_ms', 'unavailable'))}; "
              f"timestamp coverage: {_escape(summary.get('timestamp_status', 'unavailable'))}.</p>"]
    for warning in summary.get("warnings", [])[:100]:
        output.append(f"<p>Warning: {_escape(warning)}</p>")
    series = summary.get("series", [])
    if series:
        output.append("<div class=table-scroll><table><caption>Observed numeric series (returned row order; no dashboard transformations)</caption><thead><tr>" +
                      "".join(f"<th scope=col>{name}</th>" for name in ("Name / labels", "Count", "Min", "Max", "Last", "Nulls")) + "</tr></thead><tbody>")
        for item in series[:100]:
            name = str(item.get("name", "unnamed")) + " " + json.dumps(item.get("labels") or {}, ensure_ascii=False)
            values = [name, *(item.get(key) for key in ("point_count", "min", "max", "last", "null_count"))]
            output.append("<tr>" + "".join(f"<td>{_escape('null' if value is None else value)}</td>" for value in values) + "</tr>")
        output.append("</tbody></table></div>")
    else:
        output.append("<p>No numeric series summarized; this does not establish absence of data.</p>")
    if summary.get("series_truncated") or len(series) > 100:
        output.append("<p>Series display truncated at 100; inspect complete query evidence and reported counts.</p>")
    return "\n".join(output)


def _context_overview(context: dict) -> str:
    output = ["<h2>Alert and annotation context</h2>"]
    for name in ("alerts", "annotations"):
        value = context.get(name) or {}
        if value.get("ok") is not True:
            output.append(f"<p>{name.title()}: unavailable; {_escape(value.get('error', 'not captured'))}.</p>")
            continue
        if name == "alerts":
            groups = value.get("groups", [])
            rules = [rule for group in groups for rule in group.get("rules", [])]
            count = sum(len(rule.get("alerts", [])) for rule in rules)
            observed = f"{len(groups)} groups, {len(rules)} rules, {count} alert instances"
        else:
            observed = f"{len(value.get('items', []))} annotations"
        output.append(f"<p>{name.title()}: observed {observed}. Coverage: {_escape(value.get('coverage', 'unknown'))}. "
                      f"Truncated: {_escape(value.get('truncated', 'unknown'))}. Counts reflect returned records only.</p>")
    return "\n".join(output)


def _table(title: str, headers: tuple, rows: list) -> str:
    output = [f"<h3>{_escape(title)}</h3>"]
    if not rows:
        return output[0] + "<p>No rows reported.</p>"
    output.append("<div class=table-scroll><table><thead><tr>" +
                  "".join(f"<th scope=col>{_escape(name)}</th>" for name in headers) + "</tr></thead><tbody>")
    for row in rows[:200]:
        output.append("<tr>" + "".join(f"<td>{_escape('null' if value is None else value)}</td>" for value in row) + "</tr>")
    output.append("</tbody></table></div>")
    if len(rows) > 200:
        output.append(f"<p>HTML display limited to 200 of {len(rows)} rows; complete evidence retained below.</p>")
    return "\n".join(output)


def _preview_overview(report: dict) -> str:
    output = ["<h2>Sampled alert preview</h2><dl>"]
    for key in ("status", "operator", "threshold", "pending_ms", "step_ms", "evaluation_slots", "coverage",
                "initial_state", "pre_window_history", "end_censored", "notification_delivery", "saved_rule_replay", "limits"):
        output.append(f"<dt>{_escape(key)}</dt><dd>{_escape(report.get(key, 'unknown'))}</dd>")
    output.append("</dl><p>This is a sampled threshold preview, not a replay of a saved rule or notification delivery. "
                  "Missing samples reset pending state. Null interval ends remain open at the last observed evaluation; no future state is inferred.</p>")
    for warning in report.get("warnings", []):
        output.append(f"<p>Warning: {_escape(warning)}</p>")
    if report.get("unsupported_frames"):
        output.append(_table("Unsupported frames", ("Frame", "Reason"),
                             [[item.get("frame_index"), item.get("reason")] for item in report["unsupported_frames"]]))
    for series in report.get("series", [])[:100]:
        output.append(f"<article><h3>{_escape(series.get('field', 'unnamed'))} {_escape(series.get('labels', {}))}</h3>"
                      f"<p>Status: {_escape(series.get('status', 'unknown'))}; evaluated samples: {_escape(series.get('evaluated_samples', 'unknown'))}; "
                      f"missing evaluations: {_escape(series.get('missing_evaluations', 'unknown'))}.</p>")
        for warning in series.get("warnings", []):
            output.append(f"<p>Warning: {_escape(warning)}</p>")
        output.append(_table("Firing intervals", ("Start ms", "End ms", "First breach ms", "End reason"),
                             [[row.get(key) for key in ("start_ms", "end_ms", "first_breach_ms", "end_reason")] for row in series.get("intervals", [])]))
        output.append(_table("Missing data periods", ("Start ms", "End ms"),
                             [[row.get("start_ms"), row.get("end_ms")] for row in series.get("missing_data_periods", [])]))
        output.append(f"<p>Pending at end: {_escape(series.get('pending_at_end') or 'none observed')}. "
                      f"Last evaluation ms: {_escape(series.get('last_evaluation_ms', 'unknown'))}; "
                      f"end censored: {_escape(series.get('end_censored', 'unknown'))}.</p></article>")
    if len(report.get("series", [])) > 100:
        output.append("<p>Preview series display limited to 100; complete evidence retained below.</p>")
    return "\n".join(output)


def _dependency_overview(report: dict) -> str:
    nodes = sorted(report.get("nodes", []), key=lambda node: (str(node.get("kind", "")), str(node.get("id", ""))))
    by_id = {node.get("id"): node for node in nodes}
    def title(node):
        return str(node.get("kind", "unknown")) + ": " + str(next((node.get(key) for key in ("title", "name", "ref_id", "uid", "id") if node.get(key)), "unnamed"))
    def endpoint(identity):
        node = by_id.get(identity)
        return (title(node) + " [" + str(identity) + "]") if node else str(identity)
    output = ["<h2>Configuration dependency map</h2>",
              f"<p>Coverage: {_escape(report.get('coverage', 'unknown'))}. Truncated: {_escape(report.get('truncated', 'unknown'))}.</p>",
              f"<p>Metric extraction: {_escape(report.get('metric_extraction', 'unknown'))}.</p>"]
    for limitation in report.get("limitations", []):
        output.append(f"<p>{_escape(limitation)}</p>")
    output.append(_table("Nodes by type", ("Type", "Name", "ID", "Expression"),
                         [[node.get("kind"), title(node), node.get("id"), node.get("expression", "")] for node in nodes]))
    edges = sorted(report.get("edges", []), key=lambda edge: (str(edge.get("source", "")), str(edge.get("relation", "")), str(edge.get("target", ""))))
    output.append(_table("Dependency edges", ("Source", "Relation", "Target"),
                         [[endpoint(edge.get("source")), edge.get("relation"), endpoint(edge.get("target"))] for edge in edges]))
    output.append(_table("Dependency gaps", ("Source", "Gap"),
                         [[endpoint(gap.get("source")), gap.get("code")] for gap in report.get("gaps", []) if isinstance(gap, dict)]))
    return "\n".join(output)


def _render_html(report: dict, image_names: set[str]) -> bytes:
    dashboard = report.get("dashboard") or {}
    title = dashboard.get("title", report.get("operation", "Grafana evidence"))
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'img-src \'self\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        f"<title>{_escape(title)} — Grafana evidence</title>",
        "<style>body{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#182635;background:#f5f7fa}"
        "article{background:white;padding:1rem;margin:1rem 0;border:1px solid #b8c6d2;border-radius:6px}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf1f5;padding:1rem}"
        "img{max-width:100%;height:auto}summary{cursor:pointer}dt{font-weight:bold}dd{margin-bottom:.5rem}"
        "table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:.5rem;border:1px solid #b8c6d2}"
        ".table-scroll{overflow-x:auto}td:first-child{overflow-wrap:anywhere}caption{text-align:left;margin:.5rem 0}"
        "h1,h2,h3,p,li,dd{overflow-wrap:anywhere}</style></head><body>",
        f"<header><h1>{_escape(title)}</h1><p>Grafana {_escape(report.get('operation', 'evidence'))} report</p></header>",
        "<p>Sensitive telemetry: keep this package private. Values returned do not establish health. "
        "Images are image_uninspected unless separately reviewed; rendering does not prove visual correctness.</p>",
        "<dl>",
    ]
    for key, value in (("Dashboard UID", dashboard.get("uid")), ("Dashboard version", dashboard.get("version")),
                       ("From (epoch milliseconds)", report.get("from_ms")), ("To (epoch milliseconds)", report.get("to_ms"))):
        if value is not None:
            parts.append(f"<dt>{_escape(key)}</dt><dd>{_escape(value)}</dd>")
    parts.append("</dl>")
    if report.get("gaps") and report.get("operation") != "dependencies":
        parts.append("<h2>Investigation gaps</h2><ul>" + "".join(f"<li>{_escape(gap)}</li>" for gap in report["gaps"]) + "</ul>")
    if report.get("context"):
        parts.append(_context_overview(report["context"]))
    if report.get("operation") == "alert_preview":
        parts.append(_preview_overview(report))
    elif report.get("operation") == "dependencies":
        parts.append(_dependency_overview(report))
    for panel in report.get("panels", []):
        parts.append(f"<article><h2>Panel {_escape(panel.get('id', '?'))}: {_escape(panel.get('title', 'Untitled'))}</h2>")
        parts.append(f"<p>Status: <strong>{_escape(panel.get('status', 'unknown'))}</strong> · Coverage: {_escape(panel.get('coverage', 'not_established'))}</p>")
        for gap in panel.get("gaps", []):
            parts.append(f"<p>Gap: {_escape(gap)}</p>")
        for target in panel.get("targets", []):
            parts.append(f"<h3>Target {_escape(target.get('ref_id', '?'))}: {_escape(target.get('status', 'unknown'))}</h3>")
            if target.get("error"):
                parts.append(f"<p>{_escape(target['error'])}</p>")
            result = target.get("result", {})
            parts.append(_query_overview(result))
            parts.append("<p>Full query evidence is retained in report.json.</p>")
        render = panel.get("render") or {}
        image_name = render.get("image_file")
        if isinstance(image_name, str) and image_name in image_names:
            parts.append(f'<figure><img src="{_escape(image_name)}" alt="Rendered panel {_escape(panel.get("id", "?"))}"><figcaption>image_uninspected — verify labels, values, and clipping before making visual claims.</figcaption></figure>')
        elif render:
            parts.append(_details("Render evidence (no embedded image)", render))
        parts.append("</article>")
    # JSON is the primary agent artifact. Never duplicate large wire frames in HTML.
    compact = json.dumps(report, ensure_ascii=False, allow_nan=False)
    if len(compact) < 65536:
        parts.append(_details("Complete report: queries, context, provenance, and limits", report))
    else:
        parts.append('<p>Complete machine-readable evidence: <a href="report.json">report.json</a>.</p>')
    parts.append("</body></html>")
    return "\n".join(parts).encode("utf-8")


def validate_image(name: str, content: bytes) -> None:
    if not re.fullmatch(r"panel-[0-9]+\.png", name):
        raise ValueError("Image names must match panel-[digits].png")
    if not isinstance(content, bytes) or not 45 <= len(content) <= 8 * 1024 * 1024:
        raise ValueError("Images must be PNG bytes no larger than 8 MiB")
    if content[:16] != b"\x89PNG\r\n\x1a\n\0\0\0\rIHDR":
        raise ValueError("Invalid PNG signature or IHDR")
    width, height = struct.unpack(">II", content[16:24])
    if not (1 <= width <= 4096 and 1 <= height <= 4096 and width * height <= 8_000_000):
        raise ValueError("PNG dimensions exceed evidence bounds")
    if content[-12:] != b"\0\0\0\0IEND\xaeB`\x82":
        raise ValueError("PNG is truncated or has trailing content")


def _partial_report(report: dict) -> tuple[dict, list]:
    """Copy only containers that may be trimmed; never mutate caller evidence."""
    value = dict(report)
    value['panels'] = [{**panel, 'targets': [dict(target) for target in panel.get('targets', [])]}
                       for panel in report.get('panels', [])]
    previous = report.get('evidence', {})
    omitted: list = list(previous.get('omitted', []))
    value['evidence'] = {**previous, 'status': 'partial', 'reason': 'export_budget_exhausted', 'omitted': omitted}
    return value, omitted


def _trim_candidates(report: dict):
    # Preserve panel/target identity and observed status; omission is distinct from no data.
    # Folder maps retain their already-derived graph when raw source captures exceed
    # the export budget. Dropping graph nodes first destroys the useful result.
    for key in ('dashboard_captures', 'alert_captures'):
        if key in report:
            yield report, key, {'field': key, 'capture_count': len(report[key]) if isinstance(report[key], list) else None}
    targets = []
    for panel in report.get('panels', []):
        for target in panel.get('targets', []):
            if 'result' in target:
                try:
                    size = len(_bounded_json(target['result']))
                except ValueError as error:
                    if 'size limit' not in str(error):
                        raise
                    size = MAX_REPORT_BYTES + 1
                targets.append((size, target, {'panel_id': panel.get('id'), 'ref_id': target.get('ref_id'), 'mode': target.get('mode')}))
    for _, target, identity in sorted(targets, key=lambda item: item[0], reverse=True):
        yield target, 'result', identity
    for key in ('dashboard_capture', 'context', 'dashboard', 'query_plan', 'hygiene', 'series', 'nodes', 'edges'):
        if key in report:
            yield report, key, {'field': key}


def _fit_report(report: dict) -> tuple[dict, bytes]:
    try:
        return report, _bounded_json(report)
    except ValueError as error:
        if 'size limit' not in str(error):
            raise
    value, omitted = _partial_report(report)
    for owner, key, identity in _trim_candidates(value):
        owner.pop(key)
        if key == 'result':
            owner['evidence_status'] = 'omitted_export_budget'
        omitted.append(identity)
        try:
            return value, _bounded_json(value)
        except ValueError as error:
            if 'size limit' not in str(error):
                raise
    # Unknown future result sections may themselves be large. Preserve a bounded receipt.
    value = {key: report[key] for key in ('schema_version', 'operation', 'from_ms', 'to_ms') if key in report}
    value['evidence'] = {**report.get('evidence', {}), 'status': 'partial', 'reason': 'export_budget_exhausted',
                         'omitted': [{'field': key} for key in list(report)[:200] if key not in value],
                         'original_field_count': len(report)}
    return value, _bounded_json(value)


def _write_private(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)


def write_package(report: dict, destination: Path, *, images: dict[str, bytes] | None = None) -> dict:
    """Create a new package; never overwrite an existing destination.

    The caller supplies masked JSON and image bytes from trusted bounded reads.
    On a write failure the new directory retains an explicit .incomplete marker.
    POSIX modes are 0700/0600; Windows inherits its parent's access controls.
    """
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Evidence destination must not exist")
    images = dict(images or {})
    if len(images) > 50:
        raise ValueError("Evidence packages support at most 50 images")
    for name, content in images.items():
        validate_image(name, content)
    report, report_json = _fit_report(report)
    html_bytes = _render_html(report, set(images))
    if len(html_bytes) > MAX_HTML_BYTES:
        html_bytes = b'<!doctype html><html lang="en"><meta charset="utf-8"><title>Grafana evidence</title><p>HTML summary exceeded its display budget. Machine-readable evidence: <a href="report.json">report.json</a>.</p></html>'
    omitted_images = []
    # Reserve enough room for the bounded manifest and omission receipt. Query evidence wins over images.
    while images and len(report_json) + len(html_bytes) + sum(map(len, images.values())) + 65536 > MAX_PACKAGE_BYTES:
        name = max(images, key=lambda item: len(images[item]))
        images.pop(name)
        omitted_images.append(name)
    if omitted_images:
        report = dict(report)
        report['evidence'] = {**report.get('evidence', {}), 'status': 'partial',
                              'reason': 'export_budget_exhausted', 'omitted_images': omitted_images}
        report, report_json = _fit_report(report)
        html_bytes = _render_html(report, set(images))
        if len(html_bytes) > MAX_HTML_BYTES:
            html_bytes = b'<!doctype html><title>Grafana evidence</title><p>Read report.json for machine-readable evidence.</p>'
    files = {"report.json": report_json, "report.html": html_bytes, **images}
    manifest = {
        "schema_version": 1,
        "privacy": "Sensitive telemetry; Windows permissions are inherited" if os.name == "nt" else "Sensitive telemetry; directory 0700 and files 0600",
        "image_verification": "image_uninspected",
        "files": {name: {"size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()} for name, content in files.items()},
    }
    manifest_bytes = (_json(manifest) + "\n").encode("utf-8")
    if len(manifest_bytes) + sum(map(len, files.values())) > MAX_PACKAGE_BYTES:
        raise ValueError("Package payload size limit exceeded (96 MiB)")
    destination.mkdir(mode=0o700)
    marker = destination / ".incomplete"
    try:
        _write_private(marker, b"Incomplete evidence package: do not treat as a complete capture.\n")
    except OSError:
        # rmdir removes only this newly created directory, and only if still empty.
        if not marker.exists():
            destination.rmdir()
        raise
    for name, content in files.items():
        _write_private(destination / name, content)
    _write_private(destination / "manifest.json", manifest_bytes)
    marker.unlink()
    return {"schema_version": 1, "status": "partial" if report.get('evidence', {}).get('status') == 'partial' else "complete", "directory": str(destination.resolve()), "manifest": "manifest.json", "privacy": manifest["privacy"], "image_verification": "image_uninspected", "file_count": len(files) + 1, "evidence": report.get('evidence', {'status': 'complete'})}
