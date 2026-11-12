"""Deterministic derived views of already validated observable contents; no file reader or oracle."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections.abc import Iterator, Mapping
from typing import Any

from .field_history import FIELD_HISTORY_INLINE_PROFILE as FIELD_HISTORY_INLINE_PROFILE
from .field_history import FIELD_HISTORY_PROFILE as FIELD_HISTORY_PROFILE
from .field_history import FieldHistory

PROFILE = "indexed-v1"
LOOKUP_PROFILE = "lookup-catalog-v1"
SCOPED_LOOKUP_PROFILE = "lookup-catalog-v2"
PREFIX = "observations/"
DEFAULT_PAGE_BYTES = 16 * 1024


def _dump(value: Any) -> str:
    # ASCII makes the character slicing below an exact byte bound, including non-ASCII inputs.
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"


def _id(value: Any) -> str:
    return hashlib.sha256(_dump(value).encode()).hexdigest()[:24]


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _json(text: str) -> Any:
    def constant(value: str) -> Any:
        raise ValueError(f"non-JSON numeric constant: {value}")

    return json.loads(text, object_pairs_hook=_pairs, parse_constant=constant)


class _Pages:
    def __init__(self, page_bytes: int, budget: int) -> None:
        self.limit = page_bytes
        self.budget = budget
        self.files: dict[str, str] = {}
        self.size = 0
        self.content_number = 1
        self.content = ""

    def put(self, path: str, text: str) -> None:
        size = len(text.encode("utf-8"))
        if size > self.limit:
            raise ValueError("derived page exceeds page byte limit")
        if self.size + size > self.budget:
            raise ValueError("derived evidence exceeds byte budget")
        if path in self.files:
            raise ValueError("duplicate derived page")
        self.files[path] = text
        self.size += size

    def content_path(self) -> str:
        return f"{PREFIX}content/{self.content_number:08d}.txt"

    def flush(self) -> None:
        if self.content:
            self.put(self.content_path(), self.content)
            self.content_number += 1
            self.content = ""

    def record(self, record_id: str, fields: Any) -> dict[str, Any]:
        text = _dump({"id": record_id, "fields": fields})
        if len(text) > self.limit:
            self.flush()
            first = self.content_number
            for start in range(0, len(text), self.limit):
                self.put(self.content_path(), text[start : start + self.limit])
                self.content_number += 1
            return {
                "fragmented": True,
                "first_page": first,
                "page_count": self.content_number - first,
                "path_template": f"{PREFIX}content/{{page:08d}}.txt",
                "reconstruct": "Concatenate all numbered pages in order, without inserting separators, then parse JSON.",
            }
        if len(self.content) + len(text) > self.limit:
            self.flush()
        start_line = self.content.count("\n") + 1
        self.content += text
        return {
            "fragmented": False,
            "page": self.content_path(),
            "line_start": start_line,
            "line_end": self.content.count("\n"),
        }

    @staticmethod
    def _table_entry_size(item: dict[str, Any]) -> int:
        text = _dump(item)
        return len(text) + 6 * len(text.splitlines()) + 2

    def table_entry_fits(self, item: dict[str, Any]) -> bool:
        return self._table_entry_size(item) <= self.limit - 512

    def table(self, name: str, items: list[dict[str, Any]]) -> str | None:
        if not items:
            return None
        offset, page_number = 0, 1
        while offset < len(items):
            path = f"{PREFIX}{name}/{page_number:08d}.json"
            following = f"{PREFIX}{name}/{page_number + 1:08d}.json"
            selected: list[dict[str, Any]] = []
            size = 0
            # Reserve the envelope and indentation overhead; the final page is checked again by put().
            while offset + len(selected) < len(items):
                item = items[offset + len(selected)]
                item_size = self._table_entry_size(item)
                if size + item_size > self.limit - 512:
                    break
                selected.append(item)
                size += item_size
            if not selected:
                raise ValueError("index entry exceeds page byte limit")
            self.put(
                path,
                _dump(
                    {
                        "total": len(items),
                        "offset": offset,
                        "returned": len(selected),
                        "next": following if offset + len(selected) < len(items) else None,
                        "items": selected,
                    }
                ),
            )
            offset += len(selected)
            page_number += 1
        return f"{PREFIX}{name}/00000001.json"

    def catalog(
        self, category: str, rows: list[tuple[str, bool]], *, resource: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        directory = f"{PREFIX}lookup/{category}"
        resource_context = {}
        if resource is not None:
            resource_id = _id(resource)
            directory = f"{PREFIX}lookup-v2/{category}/{resource_id}"
            resource_context = {
                "resource_id": resource_id,
                "resource": resource,
                "resource_path": "/".join(
                    part for part in (resource["namespace"], resource["kind"], resource["name"]) if part
                ),
            }
        offset, page_number = 0, 1
        while offset < len(rows):
            prefix = f"{directory}/{page_number:08d}"
            selected: list[str] = []
            size = 0
            while offset + len(selected) < len(rows):
                line, _ = rows[offset + len(selected)]
                line_bytes = len(line.encode("utf-8"))
                if size + line_bytes > self.limit:
                    break
                selected.append(line)
                size += line_bytes
            if not selected:
                raise ValueError("lookup catalog row exceeds page byte limit")
            following = f"{directory}/{page_number + 1:08d}.json" if offset + len(selected) < len(rows) else None
            self.put(prefix + ".jsonl", "".join(selected))
            self.put(
                prefix + ".json",
                _dump(
                    {
                        "total": len(rows),
                        "offset": offset,
                        "returned": len(selected),
                        "next": following,
                        "rows": prefix + ".jsonl",
                        **resource_context,
                    }
                ),
            )
            offset += len(selected)
            page_number += 1
        complete = sum(complete for _, complete in rows)
        return {
            "category": category,
            "records": len(rows),
            "payload_complete": complete,
            "locator_only": len(rows) - complete,
            "first": f"{directory}/00000001.json" if rows else None,
            **resource_context,
            **({"rows_search": {"directory": directory, "glob": "*.jsonl"}} if resource is not None else {}),
        }

    def scoped_catalog(
        self, category: str, grouped_rows: dict[str, list[tuple[str, bool]]], resources: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        groups = [
            self.catalog(
                category,
                rows,
                resource={key: resources[resource_id][key] for key in ("kind", "namespace", "name", "uid")},
            )
            for resource_id, rows in sorted(grouped_rows.items())
        ]
        directory = f"{PREFIX}lookup-v2/{category}"
        return {
            "category": category,
            "records": sum(group["records"] for group in groups),
            "payload_complete": sum(group["payload_complete"] for group in groups),
            "locator_only": sum(group["locator_only"] for group in groups),
            "resource_groups": self.table(f"lookup-v2/{category}/resources", groups),
            "resources_search": {
                "directory": directory + "/resources",
                "glob": "*.json",
                "resource_count": len(groups),
            },
            "rows_search": {"directory": directory, "glob": "*/*.jsonl"},
        }


def _lookup_row(record: dict[str, Any], resource: dict[str, Any] | None, fields: Any, limit: int) -> tuple[str, bool]:
    row = {**record, "resource": resource, "payload_complete": True, "fields": fields}
    line = json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    if len(line.encode("utf-8")) <= limit:
        return line, True
    del row["fields"]
    row["payload_complete"] = False
    line = json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    if len(line.encode("utf-8")) > limit:
        raise ValueError("lookup catalog metadata exceeds page byte limit")
    return line, False


def _alert_response(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        if value.get("status") != "success":
            raise ValueError(
                "alert response status must be success; failed or unknown responses are not empty snapshots"
            )
        data = value.get("data")
        if not isinstance(data, dict):
            raise ValueError("alert response data must contain an alerts array")
        alerts = data.get("alerts")
        context = {"shape": "envelope", "status": value["status"], "alerts_path": "/data/alerts"}
    else:
        alerts = value
        context = {"shape": "array", "status": None, "alerts_path": ""}
    if not isinstance(alerts, list) or any(not isinstance(item, dict) for item in alerts):
        raise ValueError("alert snapshot must contain a JSON array of objects")
    return {**context, "alert_count": len(alerts)}


def _records(name: str, text: str) -> Iterator[tuple[str, int, int, Any]]:
    if re.fullmatch(r"alerts/alerts_(?:at|in_alerting_state)_[0-9TZ.\-]+\.json", name):
        value = _json(text)
        _alert_response(value)
        yield "alert_snapshot", 1, max(1, len(text.splitlines())), value
        return
    if name not in {"k8s_objects_raw.tsv", "k8s_events_raw.tsv", "otel_logs_raw.tsv"}:
        raise ValueError(f"unsupported indexed observable: {name}")
    reader = csv.reader(io.StringIO(text, newline=""), delimiter="\t", strict=True)
    header = next(reader, [])
    if not {"Timestamp", "Body"} <= set(header) or len(set(header)) != len(header) or "" in header:
        raise ValueError("TSV requires unique named columns including Timestamp and Body")
    while True:
        start = reader.line_num + 1
        row = next(reader, None)
        if row is None:
            break
        if len(row) != len(header):
            raise ValueError("TSV row width differs from header")
        fields = dict(zip(header, row, strict=True))
        if name == "otel_logs_raw.tsv":
            yield "log", start, reader.line_num, fields
        else:
            body = _json(fields["Body"])
            if not isinstance(body, dict):
                raise ValueError("Kubernetes Body must be a JSON object")
            yield (
                "event" if name == "k8s_events_raw.tsv" else "object",
                start,
                reader.line_num,
                {**fields, "Body": body},
            )


def _identity(obj: Any, *, reference: bool = False) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("missing Kubernetes object or event subject")
    metadata = obj if reference else obj.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("missing Kubernetes metadata")
    kind, name = obj.get("kind"), metadata.get("name")
    namespace, uid = metadata.get("namespace", ""), metadata.get("uid")
    if (
        not isinstance(kind, str)
        or not kind
        or not isinstance(name, str)
        or not name
        or not isinstance(namespace, str)
        or (uid is not None and not isinstance(uid, str))
    ):
        raise ValueError("invalid Kubernetes kind/name/namespace/UID")
    return {"kind": kind, "namespace": namespace, "name": name, "uid": uid}


def _context(category: str, fields: Any, source_name: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if category == "alert_snapshot":
        return {
            "alert_response": _alert_response(fields),
            "clocks": {
                "filename": {
                    "value": source_name.removeprefix("alerts/"),
                    "zone": "UTC" if source_name.endswith("Z.json") else "unknown",
                },
                "embedded": "Retained in snapshot content; filename time is not alert onset.",
                **(
                    {"response_timestamp": fields["timestamp"]}
                    if isinstance(fields, dict) and "timestamp" in fields
                    else {}
                ),
            },
        }, None
    context: dict[str, Any] = {
        "clocks": {"collector": {"value": fields["Timestamp"], "zone": "unknown"}, "embedded": {}}
    }
    if category == "log":
        context["service"] = fields.get("ServiceName")
        context["trace_id"] = fields.get("TraceId")
        return context, None
    body = fields["Body"]
    # Real resources may themselves have fields named object and type. Their own
    # identity takes precedence; incomplete outer identity must not select a nested one.
    watch_type = None
    if "kind" in body or "metadata" in body:
        obj = body
    elif body.get("type") in ("ADDED", "MODIFIED", "DELETED", "BOOKMARK", "ERROR") and isinstance(
        body.get("object"), dict
    ):
        obj = body["object"]
        watch_type = body["type"]
    else:
        raise ValueError("Kubernetes Body is neither an identified resource nor an explicit watch envelope")
    actual = _identity(obj)
    embedded = context["clocks"]["embedded"]
    for key in ("firstTimestamp", "lastTimestamp", "deprecatedFirstTimestamp", "deprecatedLastTimestamp", "eventTime"):
        if key in obj:
            embedded[key] = obj[key]
    metadata = obj["metadata"]
    if "creationTimestamp" in metadata:
        embedded["metadata.creationTimestamp"] = metadata["creationTimestamp"]
    updates = metadata.get("managedFields", [])
    if not isinstance(updates, list) or any(not isinstance(entry, dict) for entry in updates):
        raise ValueError("invalid managedFields representation")
    if updates:
        embedded["metadata.managedFields"] = [
            {key: entry[key] for key in ("manager", "operation", "time") if key in entry} for entry in updates
        ]
    if isinstance(obj.get("series"), dict) and "lastObservedTime" in obj["series"]:
        embedded["series.lastObservedTime"] = obj["series"]["lastObservedTime"]
    context["resource_version"] = metadata.get("resourceVersion")
    context["watch_type"] = watch_type
    context["observed_object"] = actual
    if category == "event":
        if actual["kind"] != "Event":
            raise ValueError("event export contains a non-Event object")
        resource = _identity(obj.get("involvedObject") or obj.get("regarding"), reference=True)
        context["role"] = "event_subject"
        context["reason"] = obj.get("reason")
    else:
        resource = actual
        context["role"] = "object"
    return context, resource


def build_observation_index(
    files: Mapping[str, str],
    *,
    page_bytes: int = DEFAULT_PAGE_BYTES,
    max_derived_bytes: int = 256 * 1024 * 1024,
    lookup_catalog: bool = False,
    field_history: bool = False,
    inline_field_values: bool = False,
    scoped_lookup: bool = False,
) -> dict[str, Any]:
    """Index supplied contents only. Callers own manifest/hash/path validation before this seam.

    No file paths are opened here. Unsupported or malformed sources fail the whole preparation;
    every successfully parsed record, including repeats, receives a locator. Histories retain
    source order and clocks separately, never an inferred offset, causal rank, or alias mapping.
    """
    if type(page_bytes) is not int or not 2048 <= page_bytes <= 1024 * 1024:
        raise ValueError("page byte limit must be between 2048 and 1048576")
    if type(max_derived_bytes) is not int or max_derived_bytes < 1:
        raise ValueError("derived byte budget must be positive")
    if type(lookup_catalog) is not bool:
        raise ValueError("lookup catalog option must be boolean")
    if type(field_history) is not bool:
        raise ValueError("field history option must be boolean")
    if type(inline_field_values) is not bool:
        raise ValueError("inline field values option must be boolean")
    if inline_field_values and not field_history:
        raise ValueError("inline field values requires field_history")
    if type(scoped_lookup) is not bool:
        raise ValueError("scoped lookup option must be boolean")
    if scoped_lookup and not lookup_catalog:
        raise ValueError("scoped lookup requires lookup_catalog")
    field_collector = FieldHistory() if field_history else None
    pages = _Pages(page_bytes, max_derived_bytes)
    sources: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    resources: dict[str, dict[str, Any]] = {}
    histories: dict[str, list[dict[str, Any]]] = {}
    catalog_rows: dict[str, list[tuple[str, bool]]] = {
        category: [] for category in ("alert_snapshot", "event", "log", "object")
    }
    scoped_rows: dict[str, dict[str, list[tuple[str, bool]]]] = {"object": {}, "event": {}}
    catalog_bytes = 0
    old_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(256 * 1024 * 1024)
        for name, text in sorted(files.items()):
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            count = 0
            for category, start, end, fields in _records(name, text):
                record_id = _id([name, digest, start, end])
                context, resource = _context(category, fields, name)
                record = {
                    "id": record_id,
                    "category": category,
                    "source": {"path": name, "sha256": digest, "line_start": start, "line_end": end},
                    **context,
                    "content": pages.record(record_id, fields),
                }
                records.append(record)
                if lookup_catalog:
                    line, complete = _lookup_row(record, resource, fields, page_bytes)
                    catalog_bytes += len(line.encode("utf-8"))
                    if pages.size + catalog_bytes > max_derived_bytes:
                        raise ValueError("derived evidence exceeds byte budget")
                    if scoped_lookup and resource is not None:
                        scoped_rows[category].setdefault(_id(resource), []).append((line, complete))
                    else:
                        catalog_rows[category].append((line, complete))
                count += 1
                if resource is not None:
                    resource_id = _id(resource)
                    resources.setdefault(
                        resource_id, {"id": resource_id, **resource, "object_records": 0, "event_records": 0}
                    )
                    resources[resource_id]["object_records" if category == "object" else "event_records"] += 1
                    histories.setdefault(resource_id, []).append(record)
                    if field_collector is not None:
                        field_collector.add(resource_id, resource, record, fields)
            sources.append(
                {"path": name, "sha256": digest, "bytes": len(text.encode()), "records": count, "complete": True}
            )
    except (csv.Error, RecursionError, UnicodeError, TypeError) as exc:
        raise ValueError("unsupported or malformed observable representation") from exc
    finally:
        csv.field_size_limit(old_limit)
    pages.flush()
    for resource_id, resource in resources.items():
        resource["history"] = pages.table(f"histories/{resource_id}", histories[resource_id])
    index: dict[str, Any] = {
        "format": "observable-index",
        "profile": PROFILE,
        "page_byte_limit": page_bytes,
        "sources": pages.table("sources", sources),
        "records": pages.table("records", records),
        "resources": pages.table("resources", [resources[key] for key in sorted(resources)]),
        "coverage": {"sources": len(sources), "records": len(records), "resources": len(resources), "complete": True},
        "history_order": "Source path then physical record order, not a total temporal ordering. No clock alignment or deduplication.",
        "content_policy": "Kubernetes Body JSON is decoded; nested config strings and log/attribute strings remain literal. Original files are retained.",
        "pagination": "Follow next until null in each table. Fragmented content must be concatenated as its locator specifies; fragments alone are incomplete.",
    }
    if lookup_catalog:
        catalogs = [
            pages.scoped_catalog(category, scoped_rows[category], resources)
            if scoped_lookup and category in scoped_rows
            else pages.catalog(category, rows)
            for category, rows in catalog_rows.items()
        ]
        index["extensions"] = {
            SCOPED_LOOKUP_PROFILE if scoped_lookup else LOOKUP_PROFILE: {
                "catalogs": pages.table("lookup-v2/catalogs" if scoped_lookup else "lookup/catalogs", catalogs),
                "line_byte_limit": page_bytes,
                "coverage": {
                    "records": len(records),
                    "payload_complete": sum(c["payload_complete"] for c in catalogs),
                    "locator_only": sum(c["locator_only"] for c in catalogs),
                    "complete": True,
                },
                **(
                    {
                        "resource_scope": "Object/event JSONL pages contain one exact reported resource identity each. Null UID is unknown, not an alias for a known UID. Events are grouped by their referenced subject; actual Event identity remains in each row."
                    }
                    if scoped_lookup
                    else {}
                ),
            }
        }
    if field_collector is not None:
        history_profile = FIELD_HISTORY_INLINE_PROFILE if inline_field_values else FIELD_HISTORY_PROFILE
        index.setdefault("extensions", {})[history_profile] = field_collector.emit(
            pages, len(records), inline_values=inline_field_values
        )
    extensions = ([SCOPED_LOOKUP_PROFILE if scoped_lookup else LOOKUP_PROFILE] if lookup_catalog else []) + (
        [FIELD_HISTORY_INLINE_PROFILE if inline_field_values else FIELD_HISTORY_PROFILE] if field_history else []
    )
    pages.put(f"{PREFIX}index.json", _dump(index))
    return {
        "files": pages.files,
        "derived_bytes": pages.size,
        "coverage": index["coverage"],
        "profile": PROFILE,
        **({"extensions": extensions} if extensions else {}),
    }
