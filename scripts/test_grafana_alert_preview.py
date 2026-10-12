"""Sampled alert previews are offline calculations, never saved-rule replays."""
import copy
from pathlib import Path

import pytest

from testkit import load_path

MODULE = Path(__file__).resolve().parents[1] / "skills/grafana/scripts/grafana_alert_preview.py"
preview = load_path(MODULE, "grafana_alert_preview").preview


def query(values, *, times=None, start=30000, end=150000):
    return {"ok": True, "operation": "query", "mode": "range", "kind": "prometheus",
            "from": str(start), "to": str(end), "datasource": "metrics", "expression": {"resolved": "up"},
            "results": {"A": {"frames": [{"schema": {"fields": [
                {"name": "Time", "type": "time"},
                {"name": "Value", "type": "number", "labels": {"host": "a"}}]},
                "data": {"values": [times if times is not None else list(range(start, end + 1, 30000)), values]}}]}}}


def run(data, **kwargs):
    return preview(data, **{"operator": "gt", "threshold": 5, "pending_ms": 90000, "step_ms": 30000, **kwargs})


def test_pending_fires_on_fourth_breach_and_normal_ends_interval():
    result = run(query([6, 6, 6, 6, 0]))
    assert result["series"][0]["intervals"] == [
        {"start_ms": 120000, "end_ms": 150000, "first_breach_ms": 30000, "end_reason": "threshold_not_breached"}]
    assert result["coverage"] == "sampled_threshold_preview"
    assert result["initial_state"] == "unknown"
    assert result["notification_delivery"] == "not_evaluated"


def test_missing_resets_pending_and_censors_final_firing():
    result = run(query([6, 6, None, 6, 6]), pending_ms=30000)
    series = result["series"][0]
    assert series["intervals"] == [
        {"start_ms": 60000, "end_ms": 90000, "first_breach_ms": 30000, "end_reason": "missing_data"},
        {"start_ms": 150000, "end_ms": None, "first_breach_ms": 120000, "end_reason": "window_end"}]
    assert series["missing_data_periods"] == [{"start_ms": 90000, "end_ms": 120000}]
    assert series["status"] == "gaps"


def test_no_interpolation_and_offgrid_outside_are_explicit():
    series = run(query([6, 6, 6, 6], times=[0, 30000, 61000, 180000]))["series"][0]
    assert series["outside_window_count"] == 2
    assert series["off_grid_count"] == 1
    assert series["missing_evaluations"] == 4
    assert series["intervals"] == []


@pytest.mark.parametrize(("operator", "value", "fires"), [
    ("gt", 5, False), ("ge", 5, True), ("lt", 5, False),
    ("le", 5, True), ("eq", 5, True), ("ne", 5, False), ("ne", 6, True)])
def test_operators_and_zero_pending(operator, value, fires):
    series = run(query([value] * 5), operator=operator, pending_ms=0)["series"][0]
    assert bool(series["intervals"]) is fires


@pytest.mark.parametrize("value", [None, "6", True, float("nan"), float("inf")])
def test_invalid_values_are_missing_and_never_breaches(value):
    series = run(query([6, value, 6, 6, 6]))["series"][0]
    assert series["missing_evaluations"] == 1
    assert series["intervals"] == []
    assert series["pending_at_end"]["first_breach_ms"] == 90000


@pytest.mark.parametrize("times", [[30000, 60000, 60000, 120000, 150000],
                                  [60000, 30000, 90000, 120000, 150000],
                                  [True, 60000, 90000, 120000, 150000]])
def test_ambiguous_timestamps_unsupported(times):
    result = run(query([6] * 5, times=times))
    assert result["status"] == "unsupported"
    assert result["unsupported_frames"]
    assert not result["series"]


@pytest.mark.parametrize("encoding", ["entities", "bases", "factors", "enums", "nanos"])
def test_encoded_columns_unsupported(encoding):
    data = query([6] * 5)
    data["results"]["A"]["frames"][0]["data"][encoding] = [1]
    assert run(data)["status"] == "unsupported"


@pytest.mark.parametrize("encoding", ["entities", "bases", "factors", "enums", "nanos"])
@pytest.mark.parametrize("value", [False, 0, ""])
def test_scalar_wire_encodings_do_not_become_plain_samples(encoding, value):
    data = query([6] * 5)
    data["results"]["A"]["frames"][0]["data"][encoding] = value
    result = run(data)
    assert result["status"] == "unsupported"
    assert result["unsupported_frames"] == [{"frame_index": 0, "reason": "encoded_frame"}]
    assert result["series"] == []


@pytest.mark.parametrize("meta", [None, [], "unknown"])
def test_preview_still_requires_object_metadata(meta):
    data = query([6] * 5)
    data["results"]["A"]["frames"][0]["schema"]["meta"] = meta
    assert run(data)["unsupported_frames"] == [{"frame_index": 0, "reason": "row_labelled_frame"}]


def test_row_labels_and_duplicate_series_unsupported():
    data = query([6] * 5)
    frame = data["results"]["A"]["frames"][0]
    frame["schema"]["fields"].append({"name": "host", "type": "string"})
    frame["data"]["values"].append(["a"] * 5)
    assert run(data)["status"] == "unsupported"
    data = query([6] * 5)
    data["results"]["A"]["frames"] *= 2
    result = run(data)
    assert not result["series"]
    assert result["unsupported_frames"][0]["reason"] == "duplicate_series_identity"


@pytest.mark.parametrize("changes", [{"operator": "bad"}, {"threshold": float("inf")},
                                     {"threshold": True}, {"pending_ms": -1}, {"step_ms": 999},
                                     {"step_ms": True}, {"pending_ms": 1.5}])
def test_invalid_options_fail(changes):
    with pytest.raises(ValueError):
        run(query([6] * 5), **changes)


def test_summary_only_and_instant_input_fail():
    for changes in ({"mode": "instant"}, {"results": None}, {"from": "150000"}, {"ok": False}):
        with pytest.raises(ValueError):
            run({**query([6] * 5), **changes})


def test_empty_frames_and_query_errors_are_gaps_not_health():
    data = query([6] * 5)
    data["results"]["A"]["frames"] = []
    assert run(data)["status"] == "no_data"
    data["results"]["A"]["error"] = "query error"
    assert run(data)["status"] == "unsupported"


def test_limits_fail_explicitly_without_truncation():
    with pytest.raises(ValueError, match="evaluation_slot_limit"):
        run(query([], times=[], start=0, end=86400000), step_ms=1000)
    data = query([6] * 5)
    frames = data["results"]["A"]["frames"]
    frames[:] = [{"schema": {"fields": [
        {"name": "Time", "type": "time"}, {"name": str(index), "type": "number"}]},
        "data": {"values": [[30000], [6]]}} for index in range(101)]
    with pytest.raises(ValueError, match="series_limit"):
        run(data)


def test_loki_and_multiple_label_sets_remain_separate():
    data = query([6] * 5)
    data["kind"] = "loki"
    frame = data["results"]["A"]["frames"][0]
    frame["schema"]["fields"].append({"name": "Value", "type": "number", "labels": {"host": "b"}})
    frame["data"]["values"].append([0] * 5)
    result = run(data)
    assert result["status"] == "evaluated"
    assert len(result["series"][0]["intervals"]) == 1
    assert result["series"][1]["intervals"] == []


def test_partial_preserves_supported_series_and_explicit_unsupported_frame():
    data = query([6] * 5)
    data["results"]["A"]["frames"].append({"schema": {}, "data": {}})
    result = run(data)
    assert result["status"] == "partial"
    assert len(result["series"]) == 1
    assert result["unsupported_frames"] == [{"frame_index": 1, "reason": "invalid_columns"}]


def test_trailing_missing_data_remains_open_and_all_null_is_not_health():
    series = run(query([None] * 5))["series"][0]
    assert series["missing_data_periods"] == [{"start_ms": 30000, "end_ms": None}]
    assert series["status"] == "gaps"
    assert series["evaluated_samples"] == 0
    assert series["pending_at_end"] is None


def test_timestamp_zero_pending_and_non_grid_end_are_not_lost():
    series = run(query([6, 6, 6], times=[0, 30000, 60000], start=0, end=65000),
                 pending_ms=30000)["series"][0]
    assert series["intervals"] == [{"start_ms": 30000, "end_ms": None,
                                      "first_breach_ms": 0, "end_reason": "window_end"}]
    assert series["last_evaluation_ms"] == 60000
    assert series["end_censored"] is True


@pytest.mark.parametrize("mutate", [
    lambda frame: frame["data"]["values"][1].pop(),
    lambda frame: frame["schema"]["fields"][1].update(labels={"host": 4}),
    lambda frame: frame["schema"].update(meta={"type": "timeseries-long"}),
    lambda frame: frame["schema"]["fields"][0].update(type="number"),
    lambda frame: frame["data"].update(values=[[30000] * 10001, [6] * 10001]),
])
def test_malformed_or_over_budget_frames_are_explicit(mutate):
    data = query([6] * 5)
    mutate(data["results"]["A"]["frames"][0])
    result = run(data)
    assert result["status"] == "unsupported"
    assert result["unsupported_frames"]
    assert not result["series"]


def test_input_is_not_mutated():
    data = query([6] * 5)
    before = copy.deepcopy(data)
    run(data)
    assert data == before


def test_actual_reader_provenance_and_preview_limits_are_preserved():
    data = {**query([6] * 5), "grafana_url": "https://grafana.example", "organization_id": 7,
            "retrieved_at_utc": "2026-10-12T15:00:00Z"}
    result = run(data)
    assert result["provenance"] == {"grafana_url": "https://grafana.example", "organization_id": 7,
                                    "retrieved_at_utc": "2026-10-12T15:00:00Z"}
    for phrase in ("no-data", "error", "keep-firing", "recovery", "hysteresis", "notification", "between"):
        assert any(phrase in limitation for limitation in result["limitations"])


def test_observed_alignment_recovers_fractional_window_without_interpolation():
    data = query([6, 6, 6, 0], times=[60000, 90000, 120000, 150000], start=30349, end=150349)
    anchored = run(data)
    assert anchored['evaluation_status'] == 'zero_evaluated_samples'
    result = run(data, alignment='observed', pending_ms=60000)
    assert result['evaluated_samples'] == 4
    assert result['alignment']['source'] == 'observed_sample_phase'
    assert result['alignment']['first_evaluation_ms'] == 60000
    assert result['alignment']['observed_cadences_ms'] == [30000]
    assert result['series'][0]['intervals'] == [
        {'start_ms': 120000, 'end_ms': 150000, 'first_breach_ms': 60000, 'end_reason': 'threshold_not_breached'}]


def test_observed_alignment_refuses_ambiguous_or_insufficient_samples():
    for times in ([30000, 61000], [30000]):
        result = run(query([6] * len(times), times=times), alignment='observed')
        assert result['status'] == 'alignment_unresolved'
        assert result['evaluation_slots'] == 0
        assert not result['series']


def test_explicit_grid_origin_and_no_slots_are_reported():
    result = run(query([6, 6], times=[31000, 61000]), alignment='explicit', grid_origin_ms=1000)
    assert result['alignment']['first_evaluation_ms'] == 31000
    assert result['evaluated_samples'] == 2
    result = run(query([], times=[], start=0, end=1000), alignment='explicit', grid_origin_ms=2000)
    assert result['evaluation_slots'] == 0
    assert result['series'][0]['last_evaluation_ms'] is None


@pytest.mark.parametrize('options', [{'alignment': 'bad'}, {'alignment': 'explicit'},
                                      {'grid_origin_ms': 1}, {'alignment': 'explicit', 'grid_origin_ms': True}])
def test_invalid_alignment_contract_is_rejected(options):
    with pytest.raises(ValueError):
        run(query([6] * 5), **options)


def test_observed_alignment_uses_all_eligible_series_before_evaluating():
    data = query([6, 6], times=[30000, 60000])
    second = copy.deepcopy(data['results']['A']['frames'][0])
    second['schema']['fields'][1]['labels']['host'] = 'b'
    second['data']['values'][0] = [31000, 61000]
    data['results']['A']['frames'].append(second)
    before = copy.deepcopy(data)

    result = run(data, alignment='observed')

    assert result['status'] == 'alignment_unresolved'
    assert result['alignment'] == {
        'requested': 'observed', 'source': 'unresolved', 'observed_timestamp_count': 4,
        'observed_phase_count': 2, 'observed_phases_ms': [0, 1000],
        'observed_cadence_count': 1, 'observed_cadences_ms': [30000],
        'diagnostics_truncated': False, 'interpolation': 'none',
        'grid_origin_ms': None, 'first_evaluation_ms': None}
    assert result['warnings'] == ['observed_alignment_ambiguous_or_insufficient', 'zero_evaluated_samples']
    assert result['series'] == []
    assert data == before


def test_duplicate_identities_do_not_determine_observed_alignment():
    data = query([6, 6], times=[30000, 60000])
    duplicate = copy.deepcopy(data['results']['A']['frames'][0])
    duplicate['data']['values'][0] = [31000, 61000]
    data['results']['A']['frames'].append(duplicate)
    eligible = copy.deepcopy(data['results']['A']['frames'][0])
    eligible['schema']['fields'][1]['labels']['host'] = 'b'
    data['results']['A']['frames'].append(eligible)

    result = run(data, alignment='observed')

    assert result['status'] == 'partial'
    assert result['alignment']['observed_timestamp_count'] == 2
    assert result['alignment']['observed_phases_ms'] == [0]
    assert result['alignment']['source'] == 'observed_sample_phase'
    assert [frame['frame_index'] for frame in result['unsupported_frames']] == [0, 1]
    assert [series['labels'] for series in result['series']] == [{'host': 'b'}]


def test_observed_alignment_without_series_keeps_no_data_contract():
    data = query([6] * 5)
    data['results']['A']['frames'] = []

    result = run(data, alignment='observed')

    assert result['status'] == 'no_data'
    assert result['alignment']['source'] == 'window_start'
    assert result['alignment']['grid_origin_ms'] == 30000
    assert result['evaluation_slots'] == 5
    assert result['warnings'] == ['no_numeric_series_returned']
