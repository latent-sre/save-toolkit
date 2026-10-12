#!/usr/bin/env python3
"""Bounded statistics for captured raw Grafana numeric columns, without I/O.

The reader owns supported wire shapes. Polars owns aggregate calculations; nulls,
invalid values, precision exclusions, and overflow remain explicit evidence gaps.
"""

import math
from pathlib import Path
from runpy import run_path

MAX_FRAMES, MAX_FIELDS, MAX_SERIES = 100, 100, 100
MAX_POINTS_PER_SERIES, MAX_TOTAL_POINTS = 10000, 100000
MAX_IDENTITY_CHARS = 4096
MAX_EXACT_INTEGER = 2**53
STATISTICS = ("mean", "median", "stddev_sample", "p05", "p95")


_module = run_path(str(Path(__file__).with_name('grafana_modules.py')))['load_module']
reader = _module('grafana_read')


def _aggregates(values):
    import polars as pl  # noqa: PLC0415 - only numeric analysis needs the optional runtime

    value = pl.col("value")
    return pl.DataFrame({"value": pl.Series(values, dtype=pl.Float64, strict=True)}).select(
        value.mean().alias("mean"), value.median().alias("median"),
        value.std(ddof=1).alias("stddev_sample"),
        value.quantile(0.05, interpolation="linear").alias("p05"),
        value.quantile(0.95, interpolation="linear").alias("p95"),
    ).row(0, named=True)


def _identity(field, pointer, gaps):
    name, labels = field.get("name"), field.get("labels")
    if name is not None and (not isinstance(name, str) or len(name) > MAX_IDENTITY_CHARS):
        gaps.append({"code": "series_name_omitted", "evidence_ref": pointer + "/name"})
        name = None
    if labels is not None:
        valid = (isinstance(labels, dict) and len(labels) <= 100
                 and all(isinstance(k, str) and isinstance(v, str) for k, v in labels.items())
                 and sum(len(k) + len(v) for k, v in labels.items()) <= MAX_IDENTITY_CHARS)
        if not valid:
            gaps.append({"code": "series_labels_omitted", "evidence_ref": pointer + "/labels"})
            labels = None
    return {"name": name, "labels": dict(labels) if labels is not None else None}


def _numeric_statistics(values, pointer, gaps):
    finite, nulls, invalid, precision = [], 0, 0, 0
    for value in values:
        if value is None:
            nulls += 1
        elif type(value) is int:
            if abs(value) > MAX_EXACT_INTEGER:
                precision += 1
            else:
                finite.append(float(value))
        elif type(value) is float and math.isfinite(value):
            finite.append(value)
        else:
            invalid += 1
    result = {"point_count": len(values), "finite_count": len(finite) + precision,
              "null_count": nulls, "invalid_count": invalid, "precision_unsupported_count": precision,
              "statistics_sample_count": 0, "statistics": dict.fromkeys(STATISTICS)}
    if invalid:
        gaps.append({"code": "invalid_numeric_samples_excluded", "evidence_ref": pointer})
    if precision:
        # Omitting the whole calculation avoids a biased aggregate over just small integers.
        gaps.append({"code": "integer_precision_unsupported", "evidence_ref": pointer})
        result["state"] = "unavailable"
        return result
    result["state"] = "partial" if invalid else "values" if finite else "all_null" if nulls else "empty"
    if not finite:
        return result
    result["statistics_sample_count"] = len(finite)
    for name, value in _aggregates(finite).items():
        if value is not None and not math.isfinite(value):
            result["state"] = "partial"
            gaps.append({"code": "statistic_nonfinite", "statistic": name, "evidence_ref": pointer})
        elif name == "stddev_sample" and value == 0 and min(finite) != max(finite):
            result["state"] = "partial"
            gaps.append({"code": "statistic_precision_loss", "statistic": name, "evidence_ref": pointer})
        else:
            result["statistics"][name] = value
    return result


class FrameStatistics:
    """One analysis-wide budget, so many individually valid queries stay bounded."""

    def __init__(self):
        self.frames = self.series = self.points = 0
        self.limits = {"frames": MAX_FRAMES, "fields_per_frame": MAX_FIELDS, "series": MAX_SERIES,
                       "points_per_series": MAX_POINTS_PER_SERIES, "total_numeric_points": MAX_TOTAL_POINTS}

    def summarize(self, query, pointer):
        result = {"coverage": "captured_raw_numeric_columns_only", "calculator": "polars",
                  "series": [], "gaps": [], "limits": self.limits.copy(), "budget_scope": "shared_across_analysis",
                  "method": {"weighting": "one_per_returned_finite_sample", "arithmetic": "float64",
                             "stddev_ddof": 1, "stddev_minimum_samples": 2,
                             "quantile_interpolation": "linear", "nulls": "excluded",
                             "invalid_values": "excluded_with_gap", "large_integers": "omit_series_statistics",
                             "integer_range_inclusive": [-MAX_EXACT_INTEGER, MAX_EXACT_INTEGER]},
                  "limitations": ["No time interpolation, Grafana transformations, or health assessment.",
                                  "Statistics describe captured samples; completeness of collection is unproven.",
                                  "Float64 aggregate calculations may round small differences."]}
        gaps = result["gaps"]
        raw = query.get("results")
        if raw is None:
            gaps.append({"code": "raw_query_results_unavailable", "evidence_ref": pointer})
        elif not isinstance(raw, dict) or set(raw) != {"A"} or not isinstance(raw["A"], dict):
            gaps.append({"code": "unsupported_query_results", "evidence_ref": pointer + "/results"})
        else:
            entry = raw["A"]
            try:
                failed = bool(entry.get("error")) or int(entry.get("status", 200)) >= 400
            except (TypeError, ValueError, OverflowError):
                failed = True
            if failed or not isinstance(entry.get("frames"), list):
                gaps.append({"code": "unsupported_query_results", "evidence_ref": pointer + "/results/A"})
            else:
                self._frames(entry["frames"], pointer + "/results/A/frames", result)
        result["status"] = "partial" if gaps and result["series"] else "unavailable" if gaps else "complete"
        return result

    def _frames(self, frames, pointer, result):
        gaps = result["gaps"]
        for frame_index, frame in enumerate(frames):
            ref = pointer + f"/{frame_index}"
            if self.frames >= MAX_FRAMES:
                gaps.append({"code": "statistics_frame_limit", "evidence_ref": ref})
                break
            self.frames += 1
            fields = frame.get("schema", {}).get("fields") if isinstance(frame, dict) and isinstance(frame.get("schema"), dict) else None
            if isinstance(fields, list) and len(fields) > MAX_FIELDS:
                gaps.append({"code": "statistics_field_limit", "evidence_ref": ref + "/schema/fields"})
                continue
            decoded, _reason = reader.frame_columns(frame)
            if decoded is None:
                gaps.append({"code": "unsupported_frame_shape", "evidence_ref": ref})
                continue
            fields, columns = decoded
            for field_index, (field, values) in enumerate(zip(fields, columns, strict=True)):
                if field["type"] != "number":
                    continue
                value_ref, field_ref = ref + f"/data/values/{field_index}", ref + f"/schema/fields/{field_index}"
                if self.series >= MAX_SERIES:
                    gaps.append({"code": "statistics_series_limit", "evidence_ref": value_ref})
                    return
                self.series += 1
                if len(values) > MAX_POINTS_PER_SERIES:
                    gaps.append({"code": "statistics_series_point_limit", "evidence_ref": value_ref})
                    continue
                if self.points + len(values) > MAX_TOTAL_POINTS:
                    gaps.append({"code": "statistics_total_point_limit", "evidence_ref": value_ref})
                    continue
                self.points += len(values)
                result["series"].append({"frame_index": frame_index, "field_index": field_index,
                                         "evidence_ref": value_ref, "field_evidence_ref": field_ref,
                                         **_identity(field, field_ref, gaps),
                                         **_numeric_statistics(values, value_ref, gaps)})
