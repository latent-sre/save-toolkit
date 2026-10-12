"""Polars statistics are bounded, evidence-linked, and explicit about exclusions."""

import copy
import importlib.util
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "skills/grafana/scripts/grafana_frames.py"


def load_module():
    spec = importlib.util.spec_from_file_location("grafana_frames_test", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame(values):
    return {"schema": {"fields": [{"name": "time", "type": "time"},
                                  {"name": "load", "type": "number", "labels": {"host": "example"}}]},
            "data": {"values": [[1000 + index * 1000 for index in range(len(values))], values]}}


def query(*frames):
    return {"results": {"A": {"frames": list(frames)}}}


def summarize(values):
    return load_module().FrameStatistics().summarize(query(frame(values)), "/query")


@pytest.mark.parametrize("values", [[1, 2, 4, 9], [-7.5, 2.25, 15.0], [0, 0], [2**53 - 2, 2**53]])
def test_statistics_match_independent_sample_math(values):
    result = summarize(values)
    series = result["series"][0]
    measured = series["statistics"]
    assert result["status"] == "complete"
    assert measured["mean"] == pytest.approx(statistics.mean(values))
    assert measured["median"] == pytest.approx(statistics.median(values))
    assert measured["stddev_sample"] == pytest.approx(statistics.stdev(values))
    ordered = sorted(values)
    # Linear sample quantiles use the (n - 1) rank; compare independently of Polars.
    for name, quantile in (("p05", 0.05), ("p95", 0.95)):
        rank = (len(values) - 1) * quantile
        low, high = math.floor(rank), math.ceil(rank)
        expected = ordered[low] + (ordered[high] - ordered[low]) * (rank - low)
        assert measured[name] == pytest.approx(expected)
    assert series["statistics_sample_count"] == len(values)
    assert result["method"]["stddev_ddof"] == 1
    assert result["method"]["quantile_interpolation"] == "linear"


def test_series_identity_and_source_are_preserved_without_aliasing():
    source = query(frame([1, None, 3]))
    original = copy.deepcopy(source)
    result = load_module().FrameStatistics().summarize(source, "/query")
    series = result["series"][0]
    assert source == original
    assert series["labels"] == {"host": "example"} and series["name"] == "load"
    assert series["evidence_ref"] == "/query/results/A/frames/0/data/values/1"
    assert series["field_evidence_ref"] == "/query/results/A/frames/0/schema/fields/1"
    series["labels"]["host"] = "changed"
    assert source == original
    assert (series["point_count"], series["null_count"], series["finite_count"]) == (3, 1, 2)
    assert series["statistics"]["mean"] == 2


@pytest.mark.parametrize("values,state,nulls", [([], "empty", 0), ([None, None], "all_null", 2)])
def test_empty_and_null_data_produce_null_statistics(values, state, nulls):
    result = summarize(values)
    series = result["series"][0]
    assert result["status"] == "complete" and series["state"] == state
    assert series["null_count"] == nulls and series["statistics_sample_count"] == 0
    assert set(series["statistics"].values()) == {None}


def test_one_value_has_no_sample_standard_deviation():
    measured = summarize([7])["series"][0]["statistics"]
    assert measured == {"mean": 7, "median": 7, "stddev_sample": None, "p05": 7, "p95": 7}


def test_invalid_values_are_counted_and_excluded_without_coercion():
    result = summarize([True, "2", float("inf"), float("-inf"), float("nan"), {}, None, 4, 8])
    series = result["series"][0]
    assert result["status"] == "partial" and series["state"] == "partial"
    assert (series["invalid_count"], series["null_count"], series["finite_count"]) == (6, 1, 2)
    assert series["statistics"]["mean"] == 6
    assert {gap["code"] for gap in result["gaps"]} == {"invalid_numeric_samples_excluded"}
    json.dumps(result, allow_nan=False)


def test_invalid_only_values_do_not_become_zeros_or_empty_data():
    result = summarize([True, "3", float("nan")])
    series = result["series"][0]
    assert series["state"] == "partial" and series["invalid_count"] == 3
    assert series["point_count"] == 3 and series["finite_count"] == 0
    assert set(series["statistics"].values()) == {None}


@pytest.mark.parametrize("value", [2**53 + 1, -(2**53 + 1), 2**100, 10**1000])
def test_large_integers_never_enter_a_lossy_float_cast(value):
    result = summarize([0, value])
    series = result["series"][0]
    assert series["state"] == "unavailable" and series["finite_count"] == 2
    assert series["precision_unsupported_count"] == 1
    assert series["statistics_sample_count"] == 0
    assert set(series["statistics"].values()) == {None}
    assert {gap["code"] for gap in result["gaps"]} == {"integer_precision_unsupported"}


def test_aggregate_overflow_is_a_gap_and_json_contains_no_infinity():
    result = summarize([1e308, 1e308])
    series = result["series"][0]
    assert series["state"] == "partial" and series["statistics"]["mean"] is None
    assert any(gap["code"] == "statistic_nonfinite" and gap["statistic"] == "mean" for gap in result["gaps"])
    json.dumps(result, allow_nan=False)


def test_underflow_does_not_report_nonconstant_samples_as_zero_variation():
    result = summarize([1e-200, 2e-200])
    series = result["series"][0]
    assert series["state"] == "partial" and series["statistics"]["stddev_sample"] is None
    assert any(gap["code"] == "statistic_precision_loss" and gap["statistic"] == "stddev_sample"
               for gap in result["gaps"])


@pytest.mark.parametrize("encoding", ["entities", "bases", "factors", "enums", "nanos"])
def test_encoded_wire_frames_are_not_treated_as_plain_values(encoding):
    source = frame([1, 2])
    source["data"][encoding] = {"0": [1]}
    result = load_module().FrameStatistics().summarize(query(source), "/query")
    assert result["status"] == "unavailable" and not result["series"]
    assert result["gaps"][0]["code"] == "unsupported_frame_shape"


@pytest.mark.parametrize("shape", ["long", "labels_in_rows", "unequal_columns", "unknown"])
def test_unsupported_frames_keep_the_reader_shape_boundary(shape):
    source = frame([1, 2])
    if shape == "long":
        source["schema"]["meta"] = {"type": "timeseries-long"}
    elif shape == "labels_in_rows":
        source["schema"]["fields"][0]["type"] = "string"
    elif shape == "unequal_columns":
        source["data"]["values"][0].pop()
    else:
        source = {"rows": [[1, 2]]}
    result = load_module().FrameStatistics().summarize(query(source), "/query")
    assert result["status"] == "unavailable" and not result["series"]
    assert result["gaps"][0]["code"] == "unsupported_frame_shape"


@pytest.mark.parametrize("source,code", [
    ({"summary": {"row_count": 0}}, "raw_query_results_unavailable"),
    ({"results": []}, "unsupported_query_results"),
    ({"results": {"B": {"frames": []}}}, "unsupported_query_results"),
    ({"results": {"A": {"frames": [], "status": 500}}}, "unsupported_query_results"),
    ({"results": {"A": {"frames": None}}}, "unsupported_query_results"),
])
def test_missing_or_bad_full_results_are_not_invented_from_summaries(source, code):
    result = load_module().FrameStatistics().summarize(source, "/query")
    assert result["status"] == "unavailable" and not result["series"]
    assert result["gaps"][0]["code"] == code


@pytest.mark.parametrize("limit,code", [
    ("MAX_FRAMES", "statistics_frame_limit"), ("MAX_FIELDS", "statistics_field_limit"),
    ("MAX_SERIES", "statistics_series_limit"), ("MAX_POINTS_PER_SERIES", "statistics_series_point_limit"),
    ("MAX_TOTAL_POINTS", "statistics_total_point_limit"),
])
def test_caps_emit_gaps_instead_of_statistics_for_a_sliced_prefix(monkeypatch, limit, code):
    module = load_module()
    monkeypatch.setattr(module, limit, 1)
    result = module.FrameStatistics().summarize(query(frame([1, 3]), frame([2, 4])), "/query")
    assert code in {gap["code"] for gap in result["gaps"]}
    assert all(series["point_count"] == 2 for series in result["series"])
    if limit in ("MAX_POINTS_PER_SERIES", "MAX_TOTAL_POINTS", "MAX_FIELDS"):
        assert not result["series"]


def test_point_budget_is_shared_between_queries(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "MAX_TOTAL_POINTS", 3)
    budget = module.FrameStatistics()
    assert len(budget.summarize(query(frame([1, 2])), "/first")["series"]) == 1
    second = budget.summarize(query(frame([3, 4])), "/second")
    assert not second["series"] and second["gaps"][0]["code"] == "statistics_total_point_limit"


def test_bounded_identity_is_omitted_with_an_evidence_pointer(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "MAX_IDENTITY_CHARS", 3)
    result = module.FrameStatistics().summarize(query(frame([1])), "/query")
    series = result["series"][0]
    assert series["name"] is None and series["labels"] is None
    assert {gap["code"] for gap in result["gaps"]} == {"series_name_omitted", "series_labels_omitted"}


def test_loading_statistics_preserves_the_workflow_reader(monkeypatch):
    sentinel = object()
    monkeypatch.setitem(sys.modules, "grafana_read", sentinel)
    assert summarize([1])["series"][0]["statistics"]["mean"] == 1
    assert sys.modules["grafana_read"] is sentinel


def test_polars_is_loaded_only_for_numeric_calculation(monkeypatch):
    module = load_module()
    def unavailable(_values):
        raise ModuleNotFoundError("polars", name="polars")
    monkeypatch.setattr(module, "_aggregates", unavailable)
    budget = module.FrameStatistics()
    assert budget.summarize({}, "/query")["status"] == "unavailable"
    assert budget.summarize(query(frame([])), "/query")["series"][0]["state"] == "empty"
    with pytest.raises(ModuleNotFoundError, match="polars"):
        budget.summarize(query(frame([1])), "/query")


def test_import_and_missing_results_work_without_site_packages():
    code = """
import runpy
import sys
module = runpy.run_path(sys.argv[1])
assert 'polars' not in sys.modules
budget = module['FrameStatistics']()
assert budget.summarize({}, '/query')['status'] == 'unavailable'
assert 'polars' not in sys.modules
raw = {'results': {'A': {'frames': [{'schema': {'fields': [{'type': 'number'}]}, 'data': {'values': [[1]]}}]}}}
try:
    budget.summarize(raw, '/query')
except ModuleNotFoundError as exc:
    assert exc.name == 'polars'
else:
    raise AssertionError('numeric calculation must require Polars')
"""
    completed = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(MODULE)],
                               capture_output=True, text=True, check=False, timeout=20)
    assert completed.returncode == 0, completed.stderr
