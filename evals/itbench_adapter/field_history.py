"""Observable-only resource field histories with explicit occurrence coverage."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal, DecimalException, InvalidOperation
from typing import Any, Protocol

FIELD_HISTORY_PROFILE = "resource-field-history-v1"
FIELD_HISTORY_INLINE_PROFILE = "resource-field-history-v2"
MAX_FIELD_DEPTH = 64
MAX_JSON_DEPTH = 32
MAX_JSON_BYTES = 1024 * 1024
MAX_EMBEDDED_LAYERS = 3


class PageSink(Protocol):
    limit: int

    def record(self, record_id: str, fields: Any) -> dict[str, Any]: ...
    def table(self, name: str, items: list[dict[str, Any]]) -> str | None: ...
    def table_entry_fits(self, item: dict[str, Any]) -> bool: ...
    def put(self, path: str, text: str) -> None: ...
    def flush(self) -> None: ...


def _dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"))


def _id(value: Any) -> str:
    return hashlib.sha256(_dump(value).encode()).hexdigest()


@dataclass
class _Ranges:
    spans: list[list[int]] = field(default_factory=list)

    def add(self, position: int) -> None:
        if self.spans and self.spans[-1][1] + 1 == position:
            self.spans[-1][1] = position
        else:
            self.spans.append([position, position])

    @property
    def count(self) -> int:
        return sum(end - start + 1 for start, end in self.spans)


def _difference(scope: _Ranges, present: _Ranges) -> _Ranges:
    result = _Ranges()
    cursor = 0
    for start, end in scope.spans:
        while cursor < len(present.spans) and present.spans[cursor][1] < start:
            cursor += 1
        position, index = start, cursor
        while index < len(present.spans) and present.spans[index][0] <= end:
            left, right = present.spans[index]
            if position < left:
                result.spans.append([position, left - 1])
            position = max(position, right + 1)
            index += 1
        if position <= end:
            result.spans.append([position, end])
    return result


def _typed(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {"type": "object", "keys": sorted(value)}
    if isinstance(value, list):
        return {"type": "array", "length": len(value)}
    if isinstance(value, Decimal):
        sign, digits, exponent = value.as_tuple()
        if not isinstance(exponent, int):
            raise ValueError("nonfinite normalized decimal")
        coefficient = "".join(str(digit) for digit in digits)
        trimmed = coefficient.rstrip("0")
        # Tuple/string operations preserve all digits regardless of the active Decimal context.
        return {
            "type": "number",
            "coefficient": ("-" if sign else "") + trimmed if trimmed else "0",
            "exponent": exponent + len(coefficient) - len(trimmed) if trimmed else 0,
        }
    kind = {type(None): "null", bool: "boolean", int: "integer", float: "number", str: "string"}.get(type(value))
    if kind is None:
        raise ValueError("unsupported field value type")
    return {"type": kind, "value": value}


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate embedded JSON key")
        result[key] = value
    return result


def _exact_number(text: str) -> Decimal:
    value = Decimal(text)
    if not value.is_finite():
        raise InvalidOperation("embedded JSON number exceeds exact representation")
    return value


def _constant(text: str) -> Any:
    raise ValueError(f"non-JSON constant: {text}")


def _decode(text: str, layer: int) -> tuple[str, Any]:
    stripped = text.lstrip()
    if not stripped.startswith(("{", "[")):
        return "not_container_json", None
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        return "size_limit", None
    if layer >= MAX_EMBEDDED_LAYERS:
        return "decode_depth_limit", None
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                return "depth_limit", None
        elif char in "]}":
            depth -= 1
    try:
        return "decoded", json.loads(
            text, object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_exact_number
        )
    except DecimalException:
        return "number_limit", None
    except ValueError, RecursionError:
        return "invalid_json", None


@dataclass
class _Variant:
    occurrences: _Ranges = field(default_factory=_Ranges)
    decode: dict[str, str] | None = None


@dataclass
class _Field:
    present: _Ranges = field(default_factory=_Ranges)
    variants: dict[str, _Variant] = field(default_factory=dict)


@dataclass
class _View:
    metadata: dict[str, Any]
    available: _Ranges = field(default_factory=_Ranges)


@dataclass
class _Stream:
    ledger: list[dict[str, Any]] = field(default_factory=list)
    fields: dict[tuple[str, str], _Field] = field(default_factory=dict)
    views: dict[str, _View] = field(default_factory=dict)


class FieldHistory:
    """Collect unique typed values and occurrence ranges, never copies of full resource trees."""

    def __init__(self) -> None:
        self.resources: dict[str, dict[str, Any]] = {}
        self.streams: dict[tuple[str, str], _Stream] = {}
        self.values: dict[str, dict[str, Any]] = {}
        self.decode_counts: Counter[str] = Counter()

    def add(self, resource_id: str, resource: dict[str, Any], record: dict[str, Any], fields: Any) -> None:
        self.resources.setdefault(resource_id, resource)
        stream = self.streams.setdefault((resource_id, record["category"]), _Stream())
        position = len(stream.ledger) + 1
        stream.ledger.append({"position": position, **record})
        body = fields["Body"]
        wrapped = "kind" not in body and "metadata" not in body
        views = {
            "resource": body["object"] if wrapped else body,
            "export": {key: value for key, value in fields.items() if key != "Body"},
            "watch": {key: value for key, value in body.items() if key != "object"} if wrapped else {},
        }
        for name, value in views.items():
            view = stream.views.setdefault(name, _View({"id": name, "kind": name}))
            view.available.add(position)
            self._walk(stream, name, value, "", position, 0, 0)

    def _walk(self, stream: _Stream, view: str, value: Any, path: str, position: int, depth: int, layer: int) -> None:
        if depth > MAX_FIELD_DEPTH:
            raise ValueError("resource field depth limit exceeded")
        typed = _typed(value)
        value_id = _id(typed)
        self.values.setdefault(value_id, typed)
        item = stream.fields.setdefault((view, path), _Field())
        item.present.add(position)
        variant = item.variants.setdefault(value_id, _Variant())
        variant.occurrences.add(position)
        if isinstance(value, str):
            status, decoded = _decode(value, layer)
            self.decode_counts[status] += 1
            variant.decode = {"status": status}
            if status == "decoded":
                decoded_id = "json-" + _id([view, path])[:24]
                variant.decode["view"] = decoded_id
                normalized = stream.views.setdefault(
                    decoded_id,
                    _View({"id": decoded_id, "kind": "embedded-json", "parent_view": view, "source_path": path}),
                )
                normalized.available.add(position)
                self._walk(stream, decoded_id, decoded, "", position, 0, layer + 1)
        elif isinstance(value, dict):
            for key, child in sorted(value.items()):
                escaped = key.replace("~", "~0").replace("/", "~1")
                self._walk(stream, view, child, path + "/" + escaped, position, depth + 1, layer)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self._walk(stream, view, child, path + "/" + str(index), position, depth + 1, layer)

    def emit(self, pages: PageSink, total_records: int, *, inline_values: bool = False) -> dict[str, Any]:
        """Append only after legacy views are emitted and their pending content is flushed."""
        namespace = "field-history-v2" if inline_values else "field-history"
        value_refs = {
            key: (
                {"value": value}
                if len(_dump(value)) <= pages.limit // 8
                else {"value_locator": pages.record(key, value)}
            )
            for key, value in sorted(self.values.items())
        }
        pages.flush()
        ranges_cache: dict[str, dict[str, Any]] = {}

        def occurrences(ranges: _Ranges) -> dict[str, Any]:
            key = _id(ranges.spans)
            if key not in ranges_cache:
                result: dict[str, Any] = {"count": ranges.count, "range_count": len(ranges.spans)}
                if len(_dump(ranges.spans)) <= 128:
                    result["ranges"] = ranges.spans
                else:
                    result["ranges_table"] = pages.table(
                        f"{namespace}/ranges/{key}", [{"start": start, "end": end} for start, end in ranges.spans]
                    )
                ranges_cache[key] = result
            return ranges_cache[key]

        stream_entries: dict[str, list[dict[str, Any]]] = {}
        variants_total = 0
        inline_fields = 0
        for (resource_id, category), stream in sorted(self.streams.items()):
            prefix = f"{namespace}/{resource_id}/{category}"
            field_entries = []
            for (view, path), item in sorted(stream.fields.items()):
                field_id = _id([resource_id, category, view, path])
                values = [
                    {
                        **value_refs[key],
                        "occurrences": occurrences(variant.occurrences),
                        **({"decode": variant.decode} if variant.decode is not None else {}),
                    }
                    for key, variant in item.variants.items()
                ]
                scope = stream.views[view].available
                absent = _difference(scope, item.present)
                if absent.count:
                    values.append({"value": {"type": "absent"}, "occurrences": occurrences(absent)})
                variants_total += len(values)
                entry = {
                    "view": view,
                    "path": path,
                    "observations": scope.count,
                    "present": item.present.count,
                    "absent": absent.count,
                    "variants": len(values),
                }
                if inline_values and pages.table_entry_fits({**entry, "values": values}):
                    entry["values"] = values
                    inline_fields += 1
                else:
                    entry["values_table" if inline_values else "values"] = pages.table(
                        f"{namespace}/values/{field_id}", values
                    )
                field_entries.append(entry)
            views = [
                {
                    **view.metadata,
                    "observations": len(stream.ledger),
                    "available": occurrences(view.available),
                    "unavailable": len(stream.ledger) - view.available.count,
                }
                for _, view in sorted(stream.views.items())
            ]
            stream_entries.setdefault(resource_id, []).append(
                {
                    "stream": category,
                    "observations": len(stream.ledger),
                    "ledger": pages.table(prefix + "/ledger", stream.ledger),
                    "fields": pages.table(prefix + "/fields", field_entries),
                    "views": pages.table(prefix + "/views", views),
                    **(
                        {
                            "fields_search": {
                                "directory": f"observations/{prefix}/fields",
                                "glob": "*.json",
                                "field_count": len(field_entries),
                            }
                        }
                        if inline_values
                        else {}
                    ),
                }
            )
        directory = [
            {
                "id": key,
                **resource,
                "streams": pages.table(f"{namespace}/{key}/streams", stream_entries[key]),
                **(
                    {
                        "resource_path": "/".join(
                            part for part in (resource["namespace"], resource["kind"], resource["name"]) if part
                        )
                    }
                    if inline_values
                    else {}
                ),
            }
            for key, resource in sorted(self.resources.items())
        ]
        resource_records = sum(len(stream.ledger) for stream in self.streams.values())
        coverage = {
            "profile": FIELD_HISTORY_INLINE_PROFILE if inline_values else FIELD_HISTORY_PROFILE,
            "resources": len(directory),
            "streams": len(self.streams),
            "resource_records": resource_records,
            "other_records": total_records - resource_records,
            "fields": sum(len(stream.fields) for stream in self.streams.values()),
            "variants": variants_total,
            "string_decode_occurrences": dict(sorted(self.decode_counts.items())),
            "normalization_complete": not any(
                count for status, count in self.decode_counts.items() if status not in {"decoded", "not_container_json"}
            ),
            "complete": True,
            "limits": {
                "field_depth": MAX_FIELD_DEPTH,
                "json_depth": MAX_JSON_DEPTH,
                "json_bytes": MAX_JSON_BYTES,
                "embedded_layers": MAX_EMBEDDED_LAYERS,
            },
            "position_order": "One-based source/physical record order within each resource and stream; not time or latest state.",
            "containers": "Object values list all keys; array values give length. Child paths retain every typed value in order.",
            "normalized_numbers": "Embedded JSON decimals are exact signed coefficient strings times 10 to integer exponents; base parser numbers keep their original representation.",
            **(
                {
                    "inline_fields": inline_fields,
                    "paged_fields": sum(len(stream.fields) for stream in self.streams.values()) - inline_fields,
                    "field_values": "Each field has all groups inline in values or a values_table link to all groups; never a partial preview. Follow every next link in paged values and ranges.",
                    "fields_search": "Search directory with glob from the stream descriptor across all field pages; field_count is the total, not the first page. Payload value_locator contents remain separate.",
                    "resource_paths": "Search every resources_search page. resource_path is only a display label; equal labels can have distinct UIDs and must remain separate.",
                }
                if inline_values
                else {}
            ),
        }
        coverage_path = f"observations/{namespace}/coverage.json"
        pages.put(coverage_path, _dump(coverage) + "\n")
        return {
            "directory": pages.table(f"{namespace}/resources", directory),
            "coverage": coverage_path,
            **(
                {
                    "resources_search": {
                        "directory": f"observations/{namespace}/resources",
                        "glob": "*.json",
                        "resource_count": len(directory),
                    }
                }
                if inline_values
                else {}
            ),
        }
