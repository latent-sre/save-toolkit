"""Observable-only indexing preserves records, provenance and explicit coverage."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Any

import pytest
from itbench_adapter.observations import build_observation_index


def tsv(bodies: Sequence[object], *, log: bool = False) -> str:
    out = io.StringIO(newline="")
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(["Timestamp", "ServiceName", "Body"])
    for body in bodies:
        writer.writerow(["2025-12-15 17:54:00", "store" if log else "", body if log else json.dumps(body)])
    return out.getvalue()


def table(files: dict[str, str], first: str | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    while first:
        page = json.loads(files[first])
        assert page["offset"] == len(result)
        assert page["returned"] == len(page["items"])
        result.extend(page["items"])
        first = page["next"]
    if result:
        assert len(result) == page["total"]
    return result


def payload(files: dict[str, str], record: dict[str, Any]) -> Any:
    location = record["content"]
    if location["fragmented"]:
        text = "".join(
            files[location["path_template"].format(page=n)]
            for n in range(location["first_page"], location["first_page"] + location["page_count"])
        )
    else:
        lines = files[location["page"]].splitlines(keepends=True)
        text = "".join(lines[location["line_start"] - 1 : location["line_end"]])
    return json.loads(text)["fields"]


def test_wrapped_alert_response_preserves_envelope_and_explicit_response_semantics() -> None:
    name = "alerts/alerts_in_alerting_state_2025-12-15T175926.147792Z.json"
    envelope = {
        "status": "success",
        "timestamp": "2025-12-15T17:59:20Z",
        "data": {"alerts": [{"labels": {"service": "sample"}, "state": "firing"}]},
        "warnings": ["example response annotation"],
    }
    text = json.dumps(envelope, indent=2)
    result = build_observation_index({name: text})
    files = result["files"]
    record = table(files, json.loads(files["observations/index.json"])["records"])[0]
    assert payload(files, record) == envelope
    assert record["alert_response"] == {
        "shape": "envelope",
        "status": "success",
        "alerts_path": "/data/alerts",
        "alert_count": 1,
    }
    assert record["clocks"]["response_timestamp"] == envelope["timestamp"]
    assert record["source"]["line_end"] == len(text.splitlines())
    assert record["source"]["sha256"] == hashlib.sha256(text.encode()).hexdigest()


@pytest.mark.parametrize(
    "envelope",
    [
        {"status": "error", "error": "unavailable", "data": {"alerts": []}},
        {"status": "success", "data": {}},
        {"status": "success", "data": {"alerts": ["malformed"]}},
        {"data": {"alerts": []}},
    ],
)
def test_unsuccessful_or_malformed_alert_envelope_is_not_an_empty_snapshot(envelope: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="alert"):
        build_observation_index({"alerts/alerts_in_alerting_state_2025-12-15T175926Z.json": json.dumps(envelope)})


def test_resource_identity_history_and_full_payload_ignore_nested_type_mentions() -> None:
    pod = {"kind": "Pod", "metadata": {"name": "store-a", "namespace": "demo", "uid": "pod-1"}}
    event = {
        "type": "DELETED",
        "object": {
            "kind": "Event",
            "metadata": {"name": "event-a", "uid": "event-1"},
            "involvedObject": {"kind": "Pod", "namespace": "demo", "name": "store-a", "uid": "pod-1"},
            "firstTimestamp": "2025-12-15T16:00:00Z",
            "reason": "Started",
        },
    }
    crd = {
        "kind": "CustomResourceDefinition",
        "metadata": {"name": "networkchaos.example", "uid": "crd-1"},
        "spec": {"names": {"kind": "NetworkChaos"}},
    }
    sources = {"k8s_objects_raw.tsv": tsv([pod, crd, pod]), "k8s_events_raw.tsv": tsv([event, event])}
    result = build_observation_index(sources)
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    records = table(files, index["records"])
    resources = table(files, index["resources"])
    assert index["coverage"]["records"] == 5
    assert len(records) == len({r["id"] for r in records}) == 5  # duplicates retained
    assert {r["kind"] for r in resources} == {"Pod", "CustomResourceDefinition"}
    resource = next(r for r in resources if r["kind"] == "Pod")
    history = table(files, resource["history"])
    assert len(history) == 4
    assert {h["role"] for h in history} == {"object", "event_subject"}
    e = next(r for r in records if r["category"] == "event")
    assert e["clocks"]["collector"] == {"value": "2025-12-15 17:54:00", "zone": "unknown"}
    assert e["clocks"]["embedded"]["firstTimestamp"] == "2025-12-15T16:00:00Z"
    assert e["watch_type"] == "DELETED"
    assert payload(files, e)["Body"] == event
    assert result == build_observation_index(dict(reversed(list(sources.items()))))


def test_nested_config_multiline_logs_and_large_records_are_reconstructable_and_bounded() -> None:
    config = {"kind": "ConfigMap", "metadata": {"name": "config"}, "data": {"flags.json": '{"enabled": false}'}}
    huge = {"kind": "CustomResourceDefinition", "metadata": {"name": "large"}, "description": "xλ\n" * 2000}
    logs = tsv(["line one\nline two", ""], log=True)
    sources = {"k8s_objects_raw.tsv": tsv([config, huge]), "otel_logs_raw.tsv": logs}
    result = build_observation_index(sources, page_bytes=2048)
    files = result["files"]
    assert all(len(v.encode()) <= 2048 for v in files.values())
    index = json.loads(files["observations/index.json"])
    records = table(files, index["records"])
    log = next(r for r in records if r["category"] == "log")
    assert log["source"]["line_start"] == 2
    assert log["source"]["line_end"] == 3
    assert log["source"]["sha256"] == hashlib.sha256(logs.encode()).hexdigest()
    assert payload(files, log)["Body"] == "line one\nline two"
    objects = [payload(files, r)["Body"] for r in records if r["category"] == "object"]
    assert objects == [config, huge]
    assert any(r["content"]["fragmented"] for r in records)
    assert result["derived_bytes"] == sum(len(v.encode()) for v in files.values())


def test_json_key_order_does_not_change_identity_or_fields() -> None:
    a = {"kind": "Pod", "metadata": {"name": "app", "namespace": "demo", "uid": "u"}, "status": {"ready": False}}
    b = dict(reversed(list(a.items())))
    resources = []
    for obj in [a, b]:
        result = build_observation_index({"k8s_objects_raw.tsv": tsv([obj])})
        files = result["files"]
        index = json.loads(files["observations/index.json"])
        resources.append(table(files, index["resources"])[0]["id"])
        assert payload(files, table(files, index["records"])[0])["Body"] == a
    assert resources[0] == resources[1]


@pytest.mark.parametrize("nested", [{"kind": "Pod", "metadata": {"name": "inner"}}, "ordinary field value"])
def test_actual_resource_object_field_is_not_a_watch_envelope(nested: object) -> None:
    outer = {
        "kind": "Bundle",
        "metadata": {"name": "outer", "resourceVersion": "12", "creationTimestamp": "2025-12-15T12:00:00Z"},
        "object": nested,
        "type": "ADDED",
    }
    wrapped = {"type": "MODIFIED", "object": outer}
    result = build_observation_index({"k8s_objects_raw.tsv": tsv([outer, wrapped])})
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    records = table(files, index["records"])
    resources = table(files, index["resources"])
    assert len(resources) == 1
    assert resources[0]["kind"] == "Bundle"
    assert resources[0]["name"] == "outer"
    assert resources[0]["object_records"] == 2
    assert [r["watch_type"] for r in records] == [None, "MODIFIED"]
    assert all(r["resource_version"] == "12" for r in records)
    assert all(r["clocks"]["embedded"]["metadata.creationTimestamp"] == "2025-12-15T12:00:00Z" for r in records)
    assert [payload(files, r)["Body"] for r in records] == [outer, wrapped]


@pytest.mark.parametrize(
    "body",
    [
        {"object": {"kind": "Pod", "metadata": {"name": "inner"}}},
        {"type": "unexpected", "object": {"kind": "Pod", "metadata": {"name": "inner"}}},
        {"kind": "Bundle", "type": "ADDED", "object": {"kind": "Pod", "metadata": {"name": "inner"}}},
        {"type": "ADDED", "object": "not an object"},
    ],
)
def test_malformed_or_ambiguous_watch_wrapper_is_rejected(body: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        build_observation_index({"k8s_objects_raw.tsv": tsv([body])})


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("ground_truth.yaml", "answer: secret"),
        ("../k8s_objects_raw.tsv", tsv([])),
        ("otel_traces_raw.tsv", "Timestamp\tBody\n"),
        ("k8s_objects_raw.tsv", "Timestamp\tBody\nt\tnot json\n"),
        ("k8s_objects_raw.tsv", "Timestamp\tBody\nt\t{}\n"),
        ("k8s_objects_raw.tsv", 'Timestamp\tBody\nt\t"unterminated\n'),
        ("otel_logs_raw.tsv", "Timestamp\tBody\nt\tx\textra\n"),
        ("otel_logs_raw.tsv", "Timestamp\tTimestamp\tBody\nt\tt\tx\n"),
        ("alerts/alerts_at_2025-12-15T10-00.json", "{not-json}"),
    ],
)
def test_malformed_or_unsupported_sources_fail_explicitly(name: str, content: str) -> None:
    with pytest.raises(ValueError):
        build_observation_index({name: content})


def test_derived_budget_and_page_bounds_fail_explicitly() -> None:
    with pytest.raises(ValueError, match="budget"):
        build_observation_index({"otel_logs_raw.tsv": tsv(["log"], log=True)}, max_derived_bytes=10)
    with pytest.raises(ValueError, match="page"):
        build_observation_index({}, page_bytes=10)


def test_table_continuations_and_alert_snapshot_preserve_all_entries_and_raw_values() -> None:
    objects = [
        {"metadata": {"name": f"worker-{i}", "uid": str(i)}, "kind": "Pod", "status": {"restarts": i}}
        for i in range(30)
    ]
    alert_name = "alerts/alerts_at_2025-12-15T10-00.json"
    alerts = [{"labels": {"service_name": "worker"}, "activeAt": "2025-12-15T09:00:00Z", "value": "0"}]
    result = build_observation_index(
        {"k8s_objects_raw.tsv": tsv(objects), alert_name: json.dumps(alerts, indent=2)}, page_bytes=2048
    )
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    records = table(files, index["records"])
    assert len(records) == 31
    assert json.loads(files[index["records"]])["next"] is not None
    assert len(table(files, index["resources"])) == 30
    assert payload(files, next(r for r in records if r["category"] == "alert_snapshot")) == alerts
    assert len(table(files, index["sources"])) == 2
    assert all(len(v.encode()) <= 2048 for v in files.values())


@pytest.mark.parametrize("body", ['{"kind":"Pod","kind":"Event"}', '{"kind":"Pod","metadata":{"name":"x"},"x":NaN}'])
def test_json_that_would_lose_information_is_refused(body: str) -> None:
    with pytest.raises(ValueError):
        build_observation_index({"k8s_objects_raw.tsv": "Timestamp\tBody\nt\t" + body + "\n"})


def test_filename_and_embedded_clocks_keep_their_own_meaning() -> None:
    utc = "alerts/alerts_in_alerting_state_2025-12-15T175926.147792Z.json"
    naive = "alerts/alerts_at_2025-12-15T17-59-40.132.json"
    obj = {
        "kind": "ConfigMap",
        "metadata": {
            "name": "settings",
            "creationTimestamp": "2025-12-15T17:00:00Z",
            "managedFields": [{"manager": "client", "operation": "Update", "time": "2025-12-15T17:30:00Z"}],
        },
    }
    result = build_observation_index({utc: "[]", naive: "[]", "k8s_objects_raw.tsv": tsv([obj])})
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    records = {r["source"]["path"]: r for r in table(files, index["records"])}
    assert records[utc]["clocks"]["filename"] == {"value": utc.removeprefix("alerts/"), "zone": "UTC"}
    assert records[naive]["clocks"]["filename"]["zone"] == "unknown"
    assert records["k8s_objects_raw.tsv"]["clocks"]["collector"]["zone"] == "unknown"
    assert (
        records["k8s_objects_raw.tsv"]["clocks"]["embedded"]["metadata.managedFields"][0]["time"]
        == "2025-12-15T17:30:00Z"
    )
    assert "not a total temporal ordering" in index["history_order"]


def lookup_rows(files: dict[str, str], index: dict[str, Any]) -> list[dict[str, Any]]:
    extension = index["extensions"]["lookup-catalog-v1"]
    rows: list[dict[str, Any]] = []
    for catalog in table(files, extension["catalogs"]):
        first = catalog["first"]
        offset = 0
        complete = 0
        while first:
            page = json.loads(files[first])
            assert page["total"] == catalog["records"]
            assert page["offset"] == offset
            lines = files[page["rows"]].splitlines(keepends=True)
            assert all(len(line.encode()) <= index["page_byte_limit"] for line in lines)
            current = [json.loads(line) for line in lines]
            assert page["returned"] == len(current)
            assert all(row["category"] == catalog["category"] for row in current)
            offset += len(current)
            complete += sum(row["payload_complete"] for row in current)
            rows.extend(current)
            first = page["next"]
        assert offset == catalog["records"]
        assert complete == catalog["payload_complete"]
        assert offset - complete == catalog["locator_only"]
    assert len(rows) == extension["coverage"]["records"] == index["coverage"]["records"]
    assert sum(row["payload_complete"] for row in rows) == extension["coverage"]["payload_complete"]
    assert len(rows) - sum(row["payload_complete"] for row in rows) == extension["coverage"]["locator_only"]
    assert extension["coverage"]["complete"] is True
    return rows


def test_default_index_bytes_remain_frozen_and_lookup_extension_is_opt_in() -> None:
    obj = {"kind": "ConfigMap", "metadata": {"name": "settings"}, "data": {"mode": "plain"}}
    sources = {"k8s_objects_raw.tsv": tsv([obj, obj])}
    result = build_observation_index(sources)
    assert hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest() == (
        "f7f3563995b92ced0e6cd8437b9bb8b35412123d3f8cb34bcd9977bfa3dc56a8"
    )
    assert result == build_observation_index(sources, lookup_catalog=False)
    extended = build_observation_index(sources, lookup_catalog=True)
    assert extended["extensions"] == ["lookup-catalog-v1"]
    original_files, files = result["files"], extended["files"]
    assert {p: files[p] for p in original_files if p != "observations/index.json"} == {
        p: value for p, value in original_files.items() if p != "observations/index.json"
    }
    index = json.loads(files["observations/index.json"])
    assert {k: v for k, v in index.items() if k != "extensions"} == json.loads(
        original_files["observations/index.json"]
    )


def test_lookup_catalog_includes_every_category_repeat_and_complete_decoded_fields() -> None:
    obj = {
        "kind": "ConfigMap",
        "metadata": {"name": "settings", "namespace": "demo", "uid": "config-1"},
        "data": {"flags.json": '{"enabled": false}'},
        "status": {"ready": True},
    }
    event = {
        "kind": "Event",
        "metadata": {"name": "notice", "uid": "event-1"},
        "regarding": {"kind": "ConfigMap", "name": "settings", "namespace": "demo", "uid": "config-1"},
        "eventTime": "2025-12-15T17:01:00Z",
        "reason": "Observed",
        "note": "Recorded λ status",
    }
    alerts = {"status": "success", "data": {"alerts": [{"labels": {"service": "store"}}]}}
    sources = {
        "k8s_objects_raw.tsv": tsv([obj, obj]),
        "k8s_events_raw.tsv": tsv([event, event]),
        "otel_logs_raw.tsv": tsv(["first line\nsecond line", ""], log=True),
        "alerts/alerts_at_2025-12-15T17-00Z.json": json.dumps(alerts, indent=2),
    }
    result = build_observation_index(sources, page_bytes=2048, lookup_catalog=True)
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    rows = lookup_rows(files, index)
    assert len(rows) == len({row["id"] for row in rows}) == 7
    assert {row["category"] for row in rows} == {"object", "event", "log", "alert_snapshot"}
    records = {record["id"]: record for record in table(files, index["records"])}
    for row in rows:
        assert row["payload_complete"] is True
        assert {key: row[key] for key in records[row["id"]]} == records[row["id"]]
        assert row["fields"] == payload(files, row)
        source = row["source"]
        assert source["sha256"] == hashlib.sha256(sources[source["path"]].encode()).hexdigest()
    assert [row["fields"]["Body"] for row in rows if row["category"] == "object"] == [obj, obj]
    assert [row["fields"]["Body"] for row in rows if row["category"] == "event"] == [event, event]
    first_log = next(row for row in rows if row["category"] == "log")
    assert first_log["source"]["line_start"] == 2 and first_log["source"]["line_end"] == 3
    assert first_log["fields"]["Body"] == "first line\nsecond line"
    first_event = next(row for row in rows if row["category"] == "event")
    assert first_event["resource"] == event["regarding"]
    assert first_event["clocks"]["collector"]["zone"] == "unknown"
    assert first_event["clocks"]["embedded"]["eventTime"] == event["eventTime"]
    matching_lines = [
        line
        for path, text in files.items()
        if path.endswith(".jsonl")
        for line in text.splitlines()
        if "Recorded λ status" in line
    ]
    assert len(matching_lines) == 2
    assert all('"name":"settings"' in line and '"reason":"Observed"' in line for line in matching_lines)
    assert all("2025-12-15T17:01:00Z" in line for line in matching_lines)
    assert next(row for row in rows if row["category"] == "alert_snapshot")["fields"] == alerts
    assert all(len(text.encode()) <= 2048 for text in files.values())
    assert result == build_observation_index(
        dict(reversed(list(sources.items()))), page_bytes=2048, lookup_catalog=True
    )


@pytest.mark.parametrize("kind", ["Pod", "ConfigMap", "CustomResourceDefinition", "Widget"])
def test_lookup_catalog_size_policy_preserves_small_and_locates_oversized_payloads(kind: str) -> None:
    small = {"kind": kind, "metadata": {"name": "small"}, "description": "intact"}
    large = {"kind": kind, "metadata": {"name": "large"}, "description": "xλ\n" * 2000}
    result = build_observation_index({"k8s_objects_raw.tsv": tsv([small, large])}, page_bytes=2048, lookup_catalog=True)
    files = result["files"]
    rows = lookup_rows(files, json.loads(files["observations/index.json"]))
    assert rows[0]["payload_complete"] is True
    assert rows[0]["fields"]["Body"] == small
    assert rows[1]["payload_complete"] is False
    assert "fields" not in rows[1]
    assert rows[1]["content"]["fragmented"] is True
    assert payload(files, rows[1])["Body"] == large
    assert all(len(text.encode()) <= 2048 for text in files.values())


def test_lookup_catalog_continuations_account_for_all_rows_and_added_bytes() -> None:
    sources = {"otel_logs_raw.tsv": tsv(["ordinary recorded observation " * 10] * 35, log=True)}
    base = build_observation_index(sources, page_bytes=2048)
    result = build_observation_index(sources, page_bytes=2048, lookup_catalog=True)
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    rows = lookup_rows(files, index)
    assert len(rows) == 35
    assert sum(path.endswith(".jsonl") for path in files) > 1
    assert result["derived_bytes"] == sum(len(text.encode()) for text in files.values())
    assert result["derived_bytes"] > base["derived_bytes"]
    with pytest.raises(ValueError, match="budget"):
        build_observation_index(
            sources, page_bytes=2048, lookup_catalog=True, max_derived_bytes=result["derived_bytes"] - 1
        )
    assert (
        build_observation_index(
            sources, page_bytes=2048, lookup_catalog=True, max_derived_bytes=result["derived_bytes"]
        )
        == result
    )


def test_empty_lookup_catalog_has_explicit_complete_zero_coverage() -> None:
    result = build_observation_index({}, page_bytes=2048, lookup_catalog=True)
    assert lookup_rows(result["files"], json.loads(result["files"]["observations/index.json"])) == []


def scoped_rows(files: dict[str, str], index: dict[str, Any]) -> list[dict[str, Any]]:
    extension = index["extensions"]["lookup-catalog-v2"]
    result = []
    for catalog in table(files, extension["catalogs"]):
        grouped = catalog["category"] in {"object", "event"}
        groups = table(files, catalog["resource_groups"]) if grouped else [catalog]
        linked_rows = set()
        if grouped:
            assert "first" not in catalog
            assert len(groups) == catalog["resources_search"]["resource_count"]
            assert sum(group["records"] for group in groups) == catalog["records"]
            assert sum(group["payload_complete"] for group in groups) == catalog["payload_complete"]
            assert sum(group["locator_only"] for group in groups) == catalog["locator_only"]
            search = catalog["resources_search"]
            group_pages = [
                name for name in files if PurePosixPath(name).match(search["directory"] + "/" + search["glob"])
            ]
            assert sum(json.loads(files[name])["returned"] for name in group_pages) == len(groups)
        for group in groups:
            first, offset, complete = group["first"], 0, 0
            previous_end = 0
            while first:
                page = json.loads(files[first])
                linked_rows.add(page["rows"])
                assert page["total"] == group["records"] and page["offset"] == offset
                rows = [json.loads(line) for line in files[page["rows"]].splitlines()]
                assert len(rows) == page["returned"]
                assert all(row["category"] == catalog["category"] for row in rows)
                if grouped:
                    assert page["resource"] == group["resource"]
                    assert page["resource_id"] == group["resource_id"]
                    assert page["resource_path"] == group["resource_path"]
                    assert all(row["resource"] == group["resource"] for row in rows)
                    assert str(PurePosixPath(page["rows"]).parent) == group["rows_search"]["directory"]
                    assert PurePosixPath(page["rows"]).match(group["rows_search"]["glob"])
                    for row in rows:
                        assert row["source"]["line_start"] > previous_end
                        previous_end = row["source"]["line_end"]
                offset += len(rows)
                complete += sum(row["payload_complete"] for row in rows)
                result.extend(rows)
                first = page["next"]
            assert offset == group["records"]
            assert complete == group["payload_complete"]
            assert offset - complete == group["locator_only"]
        if grouped:
            search = catalog["rows_search"]
            assert linked_rows == {
                name for name in files if PurePosixPath(name).match(search["directory"] + "/" + search["glob"])
            }
    assert len(result) == len({row["id"] for row in result}) == extension["coverage"]["records"]
    assert sum(row["payload_complete"] for row in result) == extension["coverage"]["payload_complete"]
    assert len(result) - sum(row["payload_complete"] for row in result) == extension["coverage"]["locator_only"]
    return result


def test_scoped_lookup_separates_adjacent_resource_counters_and_retains_repeats() -> None:
    first = {
        "kind": "Pod",
        "metadata": {"name": "first", "namespace": "demo", "uid": "u1"},
        "status": {"restartCount": 0},
    }
    second = {
        "kind": "Pod",
        "metadata": {"name": "second", "namespace": "demo", "uid": "u2"},
        "status": {"restartCount": 4},
    }
    sources = {"k8s_objects_raw.tsv": tsv([first, second, first])}
    legacy = build_observation_index(sources, lookup_catalog=True)
    assert hashlib.sha256(json.dumps(legacy, sort_keys=True).encode()).hexdigest() == (
        "9c175ce78dc10e8cdd0be0d74db43a1327e32f2e75dbf72f5f45662f76c9cbcf"
    )
    old_rows = [json.loads(line) for line in legacy["files"]["observations/lookup/object/00000001.jsonl"].splitlines()]
    assert [row["fields"]["Body"]["status"]["restartCount"] for row in old_rows] == [0, 4, 0]
    assert build_observation_index(sources, lookup_catalog=True, scoped_lookup=False) == legacy
    result = build_observation_index(sources, lookup_catalog=True, scoped_lookup=True)
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    rows = scoped_rows(files, index)
    assert sorted(rows, key=lambda row: row["id"]) == sorted(old_rows, key=lambda row: row["id"])
    object_files = [
        path for path in files if path.startswith("observations/lookup-v2/object/") and path.endswith(".jsonl")
    ]
    assert len(object_files) == 2
    assert not any(path.startswith("observations/lookup/object/") for path in files)
    for path in object_files:
        page_rows = [json.loads(line) for line in files[path].splitlines()]
        assert len({row["resource"]["uid"] for row in page_rows}) == 1
        expected = 0 if page_rows[0]["resource"]["uid"] == "u1" else 4
        assert all(row["fields"]["Body"]["status"]["restartCount"] == expected for row in page_rows)


def test_scoped_lookup_keeps_namespaces_known_and_unknown_uids_and_event_subjects_distinct() -> None:
    identities: list[dict[str, Any]] = [
        {"kind": "Pod", "namespace": "one", "name": "same", "uid": "a"},
        {"kind": "Pod", "namespace": "one", "name": "same", "uid": "b"},
        {"kind": "Pod", "namespace": "two", "name": "same", "uid": "a"},
        {"kind": "Pod", "namespace": "one", "name": "same", "uid": None},
    ]
    objects = [
        {"kind": identity["kind"], "metadata": {k: v for k, v in identity.items() if k != "kind"}}
        for identity in identities
    ]
    events = [
        {
            "kind": "Event",
            "metadata": {"name": "notice", "uid": f"e{i}"},
            "regarding": identity,
            "eventTime": "2025-12-15T16:00:00Z",
            "note": "ordinary event",
        }
        for i, identity in enumerate(identities)
    ]
    sources = {"k8s_objects_raw.tsv": tsv([*objects, objects[-1]]), "k8s_events_raw.tsv": tsv([*events, events[0]])}
    result = build_observation_index(sources, lookup_catalog=True, scoped_lookup=True, page_bytes=2048)
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    rows = scoped_rows(files, index)
    catalogs = table(files, index["extensions"]["lookup-catalog-v2"]["catalogs"])
    for category in ["object", "event"]:
        catalog = next(c for c in catalogs if c["category"] == category)
        groups = table(files, catalog["resource_groups"])
        assert len(groups) == 4
        assert {json.dumps(group["resource"], sort_keys=True) for group in groups} == {
            json.dumps(identity, sort_keys=True) for identity in identities
        }
        assert len({group["resource_id"] for group in groups}) == 4
        assert sum(group["resource_path"] == "one/Pod/same" for group in groups) == 3
        assert all(PurePosixPath(group["first"]).parent.name == group["resource_id"] for group in groups)
        assert all(
            len(group["resource_id"]) == 24 and set(group["resource_id"]) <= set("0123456789abcdef") for group in groups
        )
    event_rows = [row for row in rows if row["category"] == "event"]
    assert all(row["role"] == "event_subject" and row["observed_object"]["kind"] == "Event" for row in event_rows)
    assert all(row["clocks"]["embedded"]["eventTime"] == "2025-12-15T16:00:00Z" for row in event_rows)
    assert all(row["clocks"]["collector"]["zone"] == "unknown" for row in rows)


def test_scoped_lookup_preserves_flat_logs_alerts_and_all_existing_evidence_views() -> None:
    objects = [
        {"kind": "Pod", "metadata": {"name": name, "uid": name}, "status": {"ready": True}} for name in ["one", "two"]
    ]
    sources = {
        "k8s_objects_raw.tsv": tsv(objects),
        "otel_logs_raw.tsv": tsv(["multiline\nrecord", "repeated", "repeated"], log=True),
        "alerts/alerts_at_2025-12-15T17-00Z.json": "[]",
    }
    options: dict[str, Any] = {
        "lookup_catalog": True,
        "field_history": True,
        "inline_field_values": True,
        "page_bytes": 2048,
    }
    legacy = build_observation_index(sources, **options)
    result = build_observation_index(sources, scoped_lookup=True, **options)
    assert result["extensions"] == ["lookup-catalog-v2", "resource-field-history-v2"]
    files = result["files"]
    rows = scoped_rows(files, json.loads(files["observations/index.json"]))
    assert len(rows) == 6
    for path, text in legacy["files"].items():
        if (
            path.startswith(
                ("observations/lookup/object/", "observations/lookup/event/", "observations/lookup/catalogs/")
            )
            or path == "observations/index.json"
        ):
            continue
        assert files[path] == text
    assert all(len(text.encode()) <= 2048 for text in files.values())


def test_scoped_lookup_group_pagination_locator_fallback_and_exact_budget() -> None:
    huge = "λ\n" * 2000
    objects = []
    for i in range(20):
        objects.extend(
            [
                {
                    "kind": "Pod",
                    "metadata": {"name": "one", "uid": "a"},
                    "data": huge if i == 0 else "small",
                    "status": {"counter": i},
                },
                {"kind": "Pod", "metadata": {"name": "two", "uid": "b"}, "status": {"counter": i}},
            ]
        )
    sources = {"k8s_objects_raw.tsv": tsv(objects)}
    result = build_observation_index(sources, lookup_catalog=True, scoped_lookup=True, page_bytes=2048)
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    rows = scoped_rows(files, index)
    assert len(rows) == 40
    incomplete = [row for row in rows if not row["payload_complete"]]
    assert len(incomplete) == 1 and "fields" not in incomplete[0]
    assert payload(files, incomplete[0])["Body"] == objects[0]
    catalog = next(
        c for c in table(files, index["extensions"]["lookup-catalog-v2"]["catalogs"]) if c["category"] == "object"
    )
    groups = table(files, catalog["resource_groups"])
    assert all(json.loads(files[group["first"]])["next"] is not None for group in groups)
    assert all(group["records"] == 20 for group in groups)
    assert all(len(text.encode()) <= 2048 for text in files.values())
    assert result["derived_bytes"] == sum(len(text.encode()) for text in files.values())
    assert (
        build_observation_index(
            sources, lookup_catalog=True, scoped_lookup=True, page_bytes=2048, max_derived_bytes=result["derived_bytes"]
        )
        == result
    )
    with pytest.raises(ValueError, match="budget"):
        build_observation_index(
            sources,
            lookup_catalog=True,
            scoped_lookup=True,
            page_bytes=2048,
            max_derived_bytes=result["derived_bytes"] - 1,
        )


@pytest.mark.parametrize("invalid", [None, 0, 1, "true"])
def test_scoped_lookup_refuses_nonboolean_flags(invalid: Any) -> None:
    with pytest.raises(ValueError, match="scoped lookup option must be boolean"):
        build_observation_index({}, lookup_catalog=True, scoped_lookup=invalid)


def test_scoped_lookup_requires_catalog_and_keeps_empty_coverage_explicit() -> None:
    with pytest.raises(ValueError, match="requires lookup_catalog"):
        build_observation_index({}, scoped_lookup=True)
    result = build_observation_index({}, scoped_lookup=True, lookup_catalog=True, page_bytes=2048)
    assert scoped_rows(result["files"], json.loads(result["files"]["observations/index.json"])) == []
