#!/usr/bin/env python3
"""Offline sampled threshold preview, Python 3.12+, standard library only.

This module never evaluates a saved Grafana rule or its no-data/error policy,
replays pre-window state, or predicts notification delivery. The evaluation grid
defaults to the requested window start; observed/explicit alignment is optional.
Only exact timestamp matches count;
missing, null and invalid samples reset pending state. No interpolation occurs.
"""

import json
import math
import operator as comparisons
from itertools import pairwise
from pathlib import Path
from runpy import run_path

DAY_MS = 86400000
MAX_SERIES = 100
MAX_SLOTS = 10000
MAX_POINTS = 10000
OPERATORS = {"gt": comparisons.gt, "ge": comparisons.ge, "lt": comparisons.lt,
             "le": comparisons.le, "eq": comparisons.eq, "ne": comparisons.ne}
_module = run_path(str(Path(__file__).with_name('grafana_modules.py')))['load_module']
reader = _module('grafana_read')


def _finite(value):
    return type(value) in (int, float) and (isinstance(value, int) or math.isfinite(value))


def _epoch(value):
    if isinstance(value, str) and value.isascii() and value.isdigit():
        value = int(value)
    if not _finite(value) or value < 0 or value != int(value) or value > 2**53 - 1:
        raise ValueError("invalid_timestamp")
    return int(value)


def _frame(frame):
    """Return wide numeric series or one static unsupported reason for a frame."""
    decoded, reason = reader.frame_columns(frame)
    if decoded is None:
        return None, reason
    fields, columns = decoded
    # The preview requires unambiguous numeric series and exact ordered timestamps;
    # the reader can also count log rows and summarize numeric-only instant frames.
    if not isinstance(frame['schema'].get('meta', {}), dict):
        return None, "row_labelled_frame"
    if not fields:
        return None, "invalid_columns"
    if any(field['type'] not in ('time', 'number') for field in fields):
        return None, "unsupported_fields"
    if len(columns[0]) > MAX_POINTS:
        return None, "point_limit"
    time_indexes = [index for index, field in enumerate(fields) if field["type"] == "time"]
    if len(time_indexes) != 1 or len(fields) < 2:
        return None, "requires_one_time_and_numeric_fields"
    try:
        times = [_epoch(value) for value in columns[time_indexes[0]]]
    except (ValueError, OverflowError):
        return None, "invalid_timestamps"
    if any(right <= left for left, right in pairwise(times)):
        return None, "unordered_or_duplicate_timestamps"
    series = []
    for field, values in zip(fields, columns, strict=False):
        if field["type"] == "time":
            continue
        name, labels = field.get("name"), field.get("labels", {})
        if not isinstance(name, str) or not isinstance(labels, dict) or not all(
                isinstance(key, str) and isinstance(value, str) for key, value in labels.items()):
            return None, "invalid_series_identity"
        identity = json.dumps({"field": name, "labels": labels}, sort_keys=True, separators=(",", ":"))
        series.append({"identity": identity, "field": name, "labels": dict(labels), "times": times, "values": values})
    return series, None


def _evaluate(series, start, end, step, pending, compare, threshold, origin):
    samples, outside, off_grid = {}, 0, 0
    for timestamp, value in zip(series["times"], series["values"], strict=False):
        if timestamp < start or timestamp > end:
            outside += 1
        elif (timestamp - origin) % step:
            off_grid += 1
        else:
            samples[timestamp] = value
    intervals, missing_periods = [], []
    first_breach = firing = missing_start = None
    missing = evaluated = 0
    first_grid = start + (origin - start) % step
    for timestamp in range(first_grid, end + 1, step):
        value = samples.get(timestamp)
        valid = _finite(value)
        if valid:
            evaluated += 1
            if missing_start is not None:
                missing_periods.append({"start_ms": missing_start, "end_ms": timestamp})
                missing_start = None
        else:
            missing += 1
            if missing_start is None:
                missing_start = timestamp
        if valid and compare(value, threshold):
            if first_breach is None:
                first_breach = timestamp
            if firing is None and timestamp - first_breach >= pending:
                firing = {"start_ms": timestamp, "end_ms": None, "first_breach_ms": first_breach,
                          "end_reason": "window_end"}
                intervals.append(firing)
        else:
            if firing is not None:
                firing.update(end_ms=timestamp, end_reason="threshold_not_breached" if valid else "missing_data")
            first_breach = firing = None
    if missing_start is not None:
        missing_periods.append({"start_ms": missing_start, "end_ms": None})
    warnings = []
    if outside:
        warnings.append("samples_outside_window_ignored")
    if off_grid:
        warnings.append("off_grid_samples_ignored")
    if missing:
        warnings.append("missing_data_resets_pending")
    if not evaluated:
        warnings.append("zero_evaluated_samples")
    last_grid = first_grid + ((end - first_grid) // step) * step if first_grid <= end else None
    return {"identity": series["identity"], "field": series["field"], "labels": series["labels"],
            "status": "gaps" if missing or off_grid or outside else "evaluated",
            "evaluated_samples": evaluated, "missing_evaluations": missing,
            "outside_window_count": outside, "off_grid_count": off_grid, "warnings": warnings,
            "intervals": intervals, "missing_data_periods": missing_periods,
            "pending_at_end": {"first_breach_ms": first_breach, "observed_duration_ms": last_grid - first_breach}
            if first_breach is not None and firing is None else None,
            "last_evaluation_ms": last_grid, "end_censored": True}


def _alignment(series, start, end, step, requested, explicit_origin):
    """Resolve a shared grid from eligible series, keeping diagnostics on refusal.

    A None origin means observed alignment is unresolved. No eligible series
    retains the window grid so the caller can report its existing no-data state.
    """
    phases, cadences, observed_times = set(), set(), 0
    for item in series:
        times = [timestamp for timestamp in item['times'] if start <= timestamp <= end]
        observed_times += len(times)
        phases.update(timestamp % step for timestamp in times)
        cadences.update(right - left for left, right in pairwise(times))
    origin = explicit_origin if requested == 'explicit' else start
    result = {'requested': requested, 'source': 'explicit_origin' if requested == 'explicit' else 'window_start',
              'observed_timestamp_count': observed_times,
              'observed_phase_count': len(phases), 'observed_phases_ms': sorted(phases)[:20],
              'observed_cadence_count': len(cadences), 'observed_cadences_ms': sorted(cadences)[:20],
              'diagnostics_truncated': len(phases) > 20 or len(cadences) > 20,
              'interpolation': 'none'}
    if requested == 'observed' and series:
        # Require one phase and compatible cadence across every eligible series;
        # the first series alone cannot establish a shared evaluation grid.
        if len(phases) != 1 or not cadences or any(cadence % step for cadence in cadences):
            result.update(source='unresolved', grid_origin_ms=None, first_evaluation_ms=None)
            return result
        origin = next(iter(phases))
        result['source'] = 'observed_sample_phase'
    first_grid = start + (origin - start) % step
    result.update(grid_origin_ms=origin, first_evaluation_ms=first_grid if first_grid <= end else None)
    return result


def preview(query_result: dict, *, operator: str, threshold: float, pending_ms: int, step_ms: int,
            alignment: str = 'window', grid_origin_ms=None) -> dict:
    """Preview a threshold on a full grafana_read range result without any I/O.

    Invalid contracts/budgets raise ValueError with a static code. Unsupported
    frames and ambiguous identities are reported, never silently discarded.
    Up to 100 series, 10000 samples per frame and 10000 grid slots are supported.
    """
    if not isinstance(operator, str) or operator not in OPERATORS or not _finite(threshold):
        raise ValueError("invalid_threshold")
    if type(pending_ms) is not int or not 0 <= pending_ms <= DAY_MS:
        raise ValueError("invalid_pending_ms")
    if type(step_ms) is not int or not 1000 <= step_ms <= DAY_MS:
        raise ValueError("invalid_step_ms")
    if alignment not in ('window', 'observed', 'explicit'):
        raise ValueError('invalid_alignment')
    if grid_origin_ms is not None:
        grid_origin_ms = _epoch(grid_origin_ms)
        if alignment != 'explicit':
            raise ValueError('grid_origin_requires_explicit_alignment')
    elif alignment == 'explicit':
        raise ValueError('explicit_alignment_requires_grid_origin')
    if (not isinstance(query_result, dict) or query_result.get("ok") is not True or
            query_result.get("operation") != "query" or query_result.get("mode") != "range" or
            query_result.get("kind") not in ("prometheus", "loki") or
            not isinstance(query_result.get("results"), dict)):
        raise ValueError("requires_full_range_query_result")
    start, end = _epoch(query_result.get("from")), _epoch(query_result.get("to"))
    if not start < end or end - start > DAY_MS:
        raise ValueError("invalid_window")
    slots = (end - start) // step_ms + 1
    if slots > MAX_SLOTS:
        raise ValueError("evaluation_slot_limit")
    result = {"operation": "alert_preview", "schema_version": 1, "from_ms": start, "to_ms": end,
              "operator": operator, "threshold": threshold, "pending_ms": pending_ms, "step_ms": step_ms,
              "evaluation_slots": slots, "coverage": "sampled_threshold_preview", "health": "not_assessed",
              "initial_state": "unknown", "pre_window_history": "not_replayed", "end_censored": True,
              "notification_delivery": "not_evaluated", "saved_rule_replay": False,
              "datasource": query_result.get("datasource"), "expression": query_result.get("expression"),
              "provenance": {key: query_result.get(key) for key in
                             ("grafana_url", "organization_id", "retrieved_at_utc")},
              "limitations": [
                  "Sampled threshold calculation only; this does not replay a saved alert rule.",
                  "Events between sampled evaluation times are unknown; samples are never interpolated.",
                  "Saved-rule no-data and error policies are not evaluated; missing samples reset preview pending state.",
                  "Saved-rule keep-firing duration, recovery thresholds and hysteresis are not evaluated.",
                  "Routing, silences, grouping and notification delivery policies are not evaluated.",
                  "Pre-window state is unknown, and open intervals at the window end are censored."],
              "series": [], "unsupported_frames": [],
              "warnings": [], "limits": {"series": MAX_SERIES, "samples_per_frame": MAX_POINTS, "evaluation_slots": MAX_SLOTS}}
    results = query_result["results"]
    response = results.get("A")
    if (set(results) != {"A"} or not isinstance(response, dict) or response.get("error") or
            response.get("status", 200) != 200 or not isinstance(response.get("frames"), list)):
        result.update(status="unsupported", warnings=["unsupported_or_failed_query_response"])
        return result
    candidates, identities = [], {}
    for index, frame in enumerate(response["frames"]):
        parsed, reason = _frame(frame)
        if reason:
            result["unsupported_frames"].append({"frame_index": index, "reason": reason})
        else:
            for item in parsed:
                item["frame_index"] = index
                candidates.append(item)
                identities[item["identity"]] = identities.get(item["identity"], 0) + 1
    if len(candidates) > MAX_SERIES:
        raise ValueError("series_limit")
    eligible = [item for item in candidates if identities[item['identity']] == 1]
    for item in candidates:
        if identities[item['identity']] != 1:
            result['unsupported_frames'].append({'frame_index': item['frame_index'],
                                                  'reason': 'duplicate_series_identity', 'identity': item['identity']})
    result['alignment'] = _alignment(eligible, start, end, step_ms, alignment, grid_origin_ms)
    origin = result['alignment']['grid_origin_ms']
    if origin is None:
        result.update(status='alignment_unresolved', evaluation_slots=0,
                      evaluated_samples=0, evaluation_status='zero_evaluated_samples',
                      warnings=['observed_alignment_ambiguous_or_insufficient', 'zero_evaluated_samples'])
        return result
    first_grid = result['alignment']['first_evaluation_ms']
    result['evaluation_slots'] = (end - first_grid) // step_ms + 1 if first_grid is not None else 0
    for item in eligible:
        result["series"].append(_evaluate(item, start, end, step_ms, pending_ms, OPERATORS[operator], threshold, origin))
    if result["unsupported_frames"]:
        result["status"] = "partial" if result["series"] else "unsupported"
    elif not result["series"]:
        result.update(status="no_data", warnings=["no_numeric_series_returned"])
    elif any(series["status"] == "gaps" for series in result["series"]):
        result["status"] = "gaps"
    else:
        result["status"] = "evaluated"
    result['evaluated_samples'] = sum(series['evaluated_samples'] for series in result['series'])
    result['evaluation_status'] = 'evaluated' if result['evaluated_samples'] else 'zero_evaluated_samples'
    if result['series'] and not result['evaluated_samples']:
        result['warnings'].append('zero_evaluated_samples')
    return result
