"""Local evidence packages preserve telemetry without executing report content."""

import base64
import hashlib
import importlib.util
import json
import os
import struct
import zlib
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "skills/grafana/scripts/grafana_evidence.py"


@pytest.fixture
def evidence():
    spec = importlib.util.spec_from_file_location("grafana_evidence", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC")


def test_png_crc_and_pixel_stream_are_checked_before_writes(evidence, tmp_path):
    corrupt_crc = bytearray(PNG)
    corrupt_crc[-13] ^= 1
    # Correct framing and CRC do not establish a decodable pixel stream.
    payload = b'not a zlib stream'
    chunk = struct.pack('>I', len(payload)) + b'IDAT' + payload
    chunk += struct.pack('>I', zlib.crc32(b'IDAT' + payload))
    invalid_pixels = PNG[:33] + chunk + PNG[-12:]
    for content in (bytes(corrupt_crc), invalid_pixels, PNG + b'junk' + PNG[-12:]):
        with pytest.raises(ValueError):
            evidence.write_package({}, tmp_path / 'bad', images={'panel-1.png': content})
        assert not (tmp_path / 'bad').exists()


def report():
    return {
        "operation": "investigate", "dashboard": {"uid": "demo", "title": "Fleet <script>alert(1)</script>", "version": 7},
        "from_ms": 1000, "to_ms": 2000, "variables": {"host": "example-host"},
        "panels": [{"id": 6, "title": "GPU power", "status": "values_returned", "coverage": "not_established",
                    "gaps": ["No health expectation defined"], "targets": [{"ref_id": "A", "status": "values_returned", "result": {"summary": {"row_count": 2, "last": 8.26}}}],
                    "render": {"status": "rendered", "image_file": "panel-6.png"}}],
        "context": {"alerts": {"status": "unavailable"}}, "gaps": ["Alert state unavailable"],
    }


def test_package_readable_escaped_and_verifiable(evidence, tmp_path):
    destination = tmp_path / "package"
    receipt = evidence.write_package(report(), destination, images={"panel-6.png": PNG})
    assert receipt["status"] == "complete"
    assert json.loads((destination / "report.json").read_text("utf-8")) == report()
    html = (destination / "report.html").read_text("utf-8")
    for expected in ("GPU power", "values_returned", "not_established", "8.26", "Alert state unavailable", "image_uninspected", 'src="panel-6.png"', "Content-Security-Policy"):
        assert expected in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    manifest = json.loads((destination / "manifest.json").read_text("utf-8"))
    assert manifest["schema_version"] == 1
    assert set(manifest["files"]) == {"report.json", "report.html", "panel-6.png"}
    for name, entry in manifest["files"].items():
        content = (destination / name).read_bytes()
        assert entry == {"size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    assert not (destination / ".incomplete").exists()


def test_existing_destination_preserved(evidence, tmp_path):
    (tmp_path / "owned.txt").write_text("keep")
    with pytest.raises(FileExistsError):
        evidence.write_package({}, tmp_path)
    assert (tmp_path / "owned.txt").read_text() == "keep"


@pytest.mark.parametrize("name,content", [("../escape.png", PNG), ('panel-1.png\" onerror=\"evil', PNG), ("panel-1.png", b"not PNG"), ("panel-1.png", PNG[:24]), ("panel-1.png", PNG + b"a" * (8 * 1024 * 1024))], ids=["traversal", "attribute", "signature", "truncated", "oversized"])
def test_invalid_images_fail_before_directory_creation(evidence, tmp_path, name, content):
    with pytest.raises(ValueError):
        evidence.write_package({}, tmp_path / "out", images={name: content})
    assert not (tmp_path / "out").exists()


def test_no_report_path_reads_or_external_image_links(evidence, tmp_path):
    value = report()
    value["panels"][0]["render"].update(image_file="https://evil.example/track", image_path=str(tmp_path / "secret"))
    evidence.write_package(value, tmp_path / "out")
    html = (tmp_path / "out/report.html").read_text("utf-8")
    assert "<img" not in html


@pytest.mark.parametrize("width,height", [(0, 1), (4097, 1), (4096, 4096)])
def test_invalid_dimensions_refused(evidence, tmp_path, width, height):
    image = PNG[:16] + struct.pack(">II", width, height) + PNG[24:]
    with pytest.raises(ValueError, match="dimensions"):
        evidence.write_package({}, tmp_path / "out", images={"panel-1.png": image})
    assert not (tmp_path / "out").exists()


def test_image_count_bounded(evidence, tmp_path):
    with pytest.raises(ValueError, match="50 images"):
        evidence.write_package({}, tmp_path / "out", images={f"panel-{i}.png": PNG for i in range(51)})
    assert not (tmp_path / "out").exists()


def test_generic_report_remains_useful(evidence, tmp_path):
    evidence.write_package({"operation": "preview", "intervals": [{"start": 1000, "state": "firing"}]}, tmp_path / "out")
    assert "firing" in (tmp_path / "out/report.html").read_text("utf-8")


def test_visible_series_bounds_warnings_and_context(evidence, tmp_path):
    value = report()
    value["panels"][0]["targets"][0]["result"]["summary"] = {
        "status": "complete", "timestamp_min_ms": 999, "timestamp_max_ms": 2001,
        "timestamp_status": "complete", "warnings": ["outside_<window>"],
        "series": [{"name": "watts", "labels": {"gpu": "<nvidia>"}, "point_count": 2,
                    "min": 8.1, "max": 8.4, "last": None, "null_count": 1}],
    }
    value["context"] = {
        "alerts": {"ok": True, "groups": [{"rules": [{"alerts": [{"state": "firing"}]}]}],
                   "coverage": "permission_scoped", "truncated": True},
        "annotations": {"ok": True, "items": [{"text": "deploy"}], "coverage": "permission_scoped", "truncated": False},
    }
    evidence.write_package(value, tmp_path / "out")
    html = (tmp_path / "out/report.html").read_text("utf-8")
    visible = html.split("<details>")[0]
    for expected in ("watts", "&lt;nvidia&gt;", "8.1", "8.4", "null", "999", "2001", "outside_&lt;window&gt;",
                     "1 groups", "1 rules", "1 alert instances", "1 annotations", "permission_scoped", "Truncated: True"):
        assert expected in visible
    assert "<nvidia>" not in html


def test_visible_series_table_capped(evidence, tmp_path):
    value = report()
    value["panels"][0]["targets"][0]["result"]["summary"] = {
        "series": [{"name": f"series-{i}"} for i in range(101)], "series_truncated": True,
    }
    evidence.write_package(value, tmp_path / "out")
    visible = (tmp_path / "out/report.html").read_text("utf-8").split("<details>")[0]
    assert "series-99" in visible and "series-100" not in visible
    assert "Series display truncated" in visible


def test_alert_preview_visible_intervals_and_limits_are_escaped(evidence, tmp_path):
    value = {"operation": "alert_preview", "status": "gaps", "operator": "gt", "threshold": 80,
             "pending_ms": 2000, "step_ms": 1000, "coverage": "sampled_threshold_preview",
             "initial_state": "unknown", "pre_window_history": "not_replayed", "end_censored": True,
             "notification_delivery": "not_evaluated", "saved_rule_replay": False,
             "series": [{"field": "<watts>", "labels": {"gpu": "<script>"}, "status": "gaps",
                         "missing_evaluations": 1, "evaluated_samples": 4, "warnings": ["<warning>"],
                         "intervals": [{"start_ms": 3000, "end_ms": 4000, "first_breach_ms": 1000, "end_reason": "missing_data"}],
                         "missing_data_periods": [{"start_ms": 4000, "end_ms": None}],
                         "pending_at_end": {"first_breach_ms": 5000, "observed_duration_ms": 1000}}]}
    evidence.write_package(value, tmp_path / "out")
    visible = (tmp_path / "out/report.html").read_text("utf-8").split("<details>")[0]
    for expected in ("Firing intervals", "3000", "Missing data periods", "4000", "Pending at end", "5000",
                     "sampled_threshold_preview", "not_replayed", "not_evaluated", "&lt;watts&gt;", "&lt;script&gt;", "&lt;warning&gt;"):
        assert expected in visible
    assert "<script>" not in visible


def test_dependency_report_visible_named_edges_gaps_and_limits(evidence, tmp_path):
    value = {"operation": "dependencies", "coverage": "configuration_references_only", "truncated": True,
             "nodes": [{"id": "panel:1", "kind": "panel", "title": "GPU <power>"},
                       {"id": "query:1", "kind": "query", "ref_id": "A", "expression": "<script>"}],
             "edges": [{"source": "panel:1", "relation": "contains_query", "target": "query:1"}],
             "gaps": [{"code": "metric_extraction_unresolved", "source": "query:1"}],
             "limitations": ["No <runtime> dependencies resolved."]}
    evidence.write_package(value, tmp_path / "out")
    visible = (tmp_path / "out/report.html").read_text("utf-8").split("<details>")[0]
    for expected in ("Nodes by type", "Dependency edges", "GPU &lt;power&gt;", "query: A", "contains_query",
                     "metric_extraction_unresolved", "configuration_references_only", "Truncated: True", "&lt;script&gt;", "&lt;runtime&gt;"):
        assert expected in visible
    assert "<script>" not in visible


def test_dependency_display_capped_at_200_with_full_json_retained(evidence, tmp_path):
    value = {"operation": "dependencies", "nodes": [{"id": f"node{i:03}", "kind": "metric", "name": f"metric{i:03}"} for i in range(201)], "edges": []}
    evidence.write_package(value, tmp_path / "out")
    html = (tmp_path / "out/report.html").read_text("utf-8")
    visible = html.split("<details>")[0]
    assert "metric199" in visible and "metric200" not in visible
    assert "HTML display limited to 200 of 201 rows" in visible
    assert "metric200" in html


@pytest.mark.parametrize("limit", ["MAX_REPORT_BYTES", "MAX_PACKAGE_BYTES"])
def test_size_limits_fail_before_creation(evidence, tmp_path, monkeypatch, limit):
    monkeypatch.setattr(evidence, limit, 100)
    with pytest.raises(ValueError, match="size limit"):
        evidence.write_package(report(), tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_oversized_results_preserve_explicit_partial_capture(evidence, tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, 'MAX_REPORT_BYTES', 5000)
    value = report()
    value['panels'][0]['targets'].append({'ref_id': 'B', 'status': 'values_returned', 'result': {'data': 'x' * 10000}})
    receipt = evidence.write_package(value, tmp_path / 'out')
    saved = json.loads((tmp_path / 'out/report.json').read_text())
    assert receipt['status'] == 'partial'
    assert saved['panels'][0]['id'] == 6
    assert saved['panels'][0]['targets'][0]['result']['summary']['last'] == 8.26
    assert saved['evidence']['status'] == 'partial'
    assert saved['panels'][0]['targets'][1]['evidence_status'] == 'omitted_export_budget'
    assert value['panels'][0]['targets'][1]['result']['data'] == 'x' * 10000
    assert not (tmp_path / 'out/.incomplete').exists()


def test_large_frames_are_not_duplicated_in_html(evidence, tmp_path):
    value = report()
    value['panels'][0]['targets'][0]['result']['results'] = {'wire': 'distinct-frame-data-' * 10000}
    evidence.write_package(value, tmp_path / 'out')
    assert 'distinct-frame-data' not in (tmp_path / 'out/report.html').read_text()
    assert 'distinct-frame-data' in (tmp_path / 'out/report.json').read_text()


def test_repeated_budget_trimming_preserves_prior_omissions(evidence, tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, 'MAX_REPORT_BYTES', 5000)
    value = report()
    value['evidence'] = {'status': 'partial', 'omitted': [{'ref_id': 'earlier'}], 'omitted_images': ['panel-9.png']}
    value['panels'][0]['targets'].append({'ref_id': 'B', 'result': {'wire': 'x' * 10000}})
    evidence.write_package(value, tmp_path / 'out')
    saved = json.loads((tmp_path / 'out/report.json').read_text())
    assert {'ref_id': 'earlier'} in saved['evidence']['omitted']
    assert saved['evidence']['omitted_images'] == ['panel-9.png']


@pytest.mark.parametrize('field', ['dashboard_captures', 'alert_captures'])
def test_oversized_source_captures_preserve_dependency_graph(evidence, tmp_path, monkeypatch, field):
    monkeypatch.setattr(evidence, 'MAX_REPORT_BYTES', 5000)
    value = {'schema_version': 1, 'operation': 'dependencies', 'coverage': 'configuration_references_only',
             'nodes': [{'id': 'datasource:metrics', 'kind': 'datasource'}], 'edges': [],
             field: [{'dashboard': {'uid': 'demo', 'description': 'x' * 10000}}]}
    receipt = evidence.write_package(value, tmp_path / 'out')
    saved = json.loads((tmp_path / 'out/report.json').read_text())
    assert receipt['status'] == 'partial'
    assert saved['nodes'] == value['nodes'] and saved['edges'] == []
    assert saved['coverage'] == 'configuration_references_only'
    assert saved['evidence']['omitted'] == [{'field': field, 'capture_count': 1}]
    assert field not in saved and field in value


def test_image_budget_retains_queries_and_marks_omission(evidence, tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, 'MAX_PACKAGE_BYTES', 10000)
    receipt = evidence.write_package(report(), tmp_path / 'out', images={'panel-6.png': PNG})
    saved = json.loads((tmp_path / 'out/report.json').read_text())
    assert receipt['status'] == 'partial'
    assert saved['panels'][0]['targets'][0]['result']['summary']['last'] == 8.26
    assert saved['evidence']['omitted_images'] == ['panel-6.png']
    assert 'src="panel-6.png"' not in (tmp_path / 'out/report.html').read_text()


def test_public_image_validator_rejects_truncated_header(evidence):
    with pytest.raises(ValueError):
        evidence.validate_image('panel-1.png', PNG[:24])


def test_real_collection_budget_can_export_partial_package(evidence, tmp_path):
    value = report()
    payload = 'x' * 600000
    value['panels'][0]['targets'] = [
        {'ref_id': f'Q{index}', 'status': 'values_returned', 'result': {'wire_data': payload}}
        for index in range(65)
    ]
    # 39 MB fits the collector's 64 MiB budget but exceeds the 32 MiB JSON budget.
    receipt = evidence.write_package(value, tmp_path / 'out')
    assert receipt['status'] == 'partial'
    raw = (tmp_path / 'out/report.json').read_bytes()
    assert len(raw) <= evidence.MAX_REPORT_BYTES
    saved = json.loads(raw)
    retained = [target for target in saved['panels'][0]['targets'] if 'result' in target]
    assert 0 < len(retained) < 65
    assert len(retained) + len(saved['evidence']['omitted']) == 65


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission contract")
def test_private_permissions_and_symlink_refusal(evidence, tmp_path):
    destination = tmp_path / "out"
    evidence.write_package({}, destination, images={"panel-1.png": PNG})
    assert destination.stat().st_mode & 0o777 == 0o700
    for entry in destination.iterdir():
        assert entry.stat().st_mode & 0o777 == 0o600
    link = tmp_path / "link"
    link.symlink_to(destination, target_is_directory=True)
    with pytest.raises(FileExistsError):
        evidence.write_package({}, link)


def test_failure_leaves_explicit_incomplete_marker(evidence, tmp_path, monkeypatch):
    original = evidence.os.open
    def fail_report(path, *args, **kwargs):
        if Path(path).name == "report.html":
            raise OSError("disk failure")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(evidence.os, "open", fail_report)
    with pytest.raises(OSError, match="disk failure"):
        evidence.write_package({}, tmp_path / "out")
    assert (tmp_path / "out/.incomplete").exists()
    assert not (tmp_path / "out/manifest.json").exists()


def test_initial_write_failure_removes_only_new_empty_directory(evidence, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("disk failure")
    monkeypatch.setattr(evidence.os, "open", fail)
    with pytest.raises(OSError, match="disk failure"):
        evidence.write_package({}, tmp_path / "out")
    assert not (tmp_path / "out").exists()
