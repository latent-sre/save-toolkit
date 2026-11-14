"""Field histories preserve typed observations and expose normalized embedded JSON separately."""

from __future__ import annotations

import hashlib
import json
from decimal import localcontext
from pathlib import PurePosixPath
from typing import Any

import pytest
from itbench_adapter.observations import FIELD_HISTORY_PROFILE, build_observation_index
from test_itbench_observations import payload, table, tsv


def object_record(**fields: Any) -> dict[str, Any]:
    return {"kind": "Widget", "metadata": {"name": "sample", "namespace": "demo", "uid": "u1"}, **fields}


def prepared(objects: list[dict[str, Any]], **options: Any) -> tuple[dict[str, str], dict[str, Any]]:
    result = build_observation_index({"k8s_objects_raw.tsv": tsv(objects)}, field_history=True, **options)
    return result["files"], json.loads(result["files"]["observations/index.json"])


def stream_view(
    files: dict[str, str],
    index: dict[str, Any],
    stream: str = "object",
    uid: str = "u1",
    profile: str = FIELD_HISTORY_PROFILE,
) -> dict[str, Any]:
    extension = index["extensions"][profile]
    resource = next(r for r in table(files, extension["directory"]) if r["uid"] == uid)
    return next(s for s in table(files, resource["streams"]) if s["stream"] == stream)


def positions(files: dict[str, str], occurrences: dict[str, Any]) -> list[int]:
    ranges = occurrences.get("ranges")
    if ranges is None:
        ranges = [[r["start"], r["end"]] for r in table(files, occurrences["ranges_table"])]
    result = [position for start, end in ranges for position in range(start, end + 1)]
    assert len(result) == occurrences["count"]
    assert len(ranges) == occurrences["range_count"]
    return result


def variants(
    files: dict[str, str], stream: dict[str, Any], path: str, view: str = "resource"
) -> list[tuple[Any, list[int]]]:
    field = next(f for f in table(files, stream["fields"]) if f["path"] == path and f["view"] == view)
    values = field.get("values")
    if not isinstance(values, list):
        values = table(files, field.get("values_table", values))
    assert len(values) == field["variants"]
    return [
        (
            v["value"] if "value" in v else payload(files, {"content": v["value_locator"]}),
            positions(files, v["occurrences"]),
        )
        for v in values
    ]


def test_formatting_changes_preserve_literal_values_and_group_normalized_fields() -> None:
    first = '{\n "flag": {"percentage": 0}, "ports": [80, 443]\n}'
    same = '{"ports":[80,443],"flag":{"percentage":0}}'
    changed = '{"flag":{"percentage":100},"ports":[80,443]}'
    files, index = prepared([object_record(config=value) for value in [first, same, changed, first]])
    stream = stream_view(files, index)
    assert variants(files, stream, "/config") == [
        ({"type": "string", "value": first}, [1, 4]),
        ({"type": "string", "value": same}, [2]),
        ({"type": "string", "value": changed}, [3]),
    ]
    view = next(v for v in table(files, stream["views"]) if v.get("source_path") == "/config")
    assert view["parent_view"] == "resource"
    assert positions(files, view["available"]) == [1, 2, 3, 4]
    assert variants(files, stream, "/flag/percentage", view["id"]) == [
        ({"type": "integer", "value": 0}, [1, 2, 4]),
        ({"type": "integer", "value": 100}, [3]),
    ]
    config = next(f for f in table(files, stream["fields"]) if f["view"] == "resource" and f["path"] == "/config")
    assert all(v["decode"] == {"status": "decoded", "view": view["id"]} for v in table(files, config["values"]))


@pytest.mark.parametrize("precision", [1, 28])
def test_normalized_decimals_preserve_near_values_underflow_and_equivalent_exponents(precision: int) -> None:
    numbers = [
        "1.0000000000000000",
        "1.0000000000000001",
        "1e-1000",
        "0.0",
        "1e0",
        "100e-2",
        "-12.3400",
        "-1234e-2",
        "1e1000000",
        "10e999999",
        "-0e-99999",
    ]
    literals = ['{"number":' + value + "}" for value in numbers]
    with localcontext() as context:
        context.prec = precision
        context.Emax = 9
        context.Emin = -9
        files, index = prepared([object_record(config=value) for value in literals])
    stream = stream_view(files, index)
    view = next(v for v in table(files, stream["views"]) if v.get("source_path") == "/config")
    assert [occurrences for _, occurrences in variants(files, stream, "/number", view["id"])] == [
        [1, 5, 6],
        [2],
        [3],
        [4, 11],
        [7, 8],
        [9, 10],
    ]
    assert positions(files, view["available"]) == list(range(1, 12))
    assert variants(files, stream, "/number", view["id"]) == [
        ({"type": "number", "coefficient": "1", "exponent": 0}, [1, 5, 6]),
        ({"type": "number", "coefficient": "10000000000000001", "exponent": -16}, [2]),
        ({"type": "number", "coefficient": "1", "exponent": -1000}, [3]),
        ({"type": "number", "coefficient": "0", "exponent": 0}, [4, 11]),
        ({"type": "number", "coefficient": "-1234", "exponent": -2}, [7, 8]),
        ({"type": "number", "coefficient": "1", "exponent": 1000000}, [9, 10]),
    ]
    assert [value["value"] for value, _ in variants(files, stream, "/config")] == literals
    coverage = json.loads(files[index["extensions"][FIELD_HISTORY_PROFILE]["coverage"]])
    assert coverage["normalization_complete"] is True


def test_unrepresentable_decimal_exponent_is_explicitly_unavailable_with_literal_intact() -> None:
    literal = '{"number":1e9999999999999999999999999999}'
    files, index = prepared([object_record(config=literal)])
    stream = stream_view(files, index)
    config = next(f for f in table(files, stream["fields"]) if f["view"] == "resource" and f["path"] == "/config")
    assert table(files, config["values"])[0]["decode"] == {"status": "number_limit"}
    assert variants(files, stream, "/config") == [({"type": "string", "value": literal}, [1])]
    assert not any(v["kind"] == "embedded-json" for v in table(files, stream["views"]))
    coverage = json.loads(files[index["extensions"][FIELD_HISTORY_PROFILE]["coverage"]])
    assert coverage["complete"] is True and coverage["normalization_complete"] is False


def test_absence_null_scalar_types_empty_containers_and_escaped_paths_remain_distinct() -> None:
    values: list[Any] = [None, True, 1, 1.0, "", [], {}, [1, 2], [2, 1]]
    objects = [object_record(**{"a/b~": value}) for value in values]
    objects.insert(0, object_record())
    files, index = prepared(objects)
    stream = stream_view(files, index)
    expected = [
        ({"type": "null", "value": None}, [2]),
        ({"type": "boolean", "value": True}, [3]),
        ({"type": "integer", "value": 1}, [4]),
        ({"type": "number", "value": 1.0}, [5]),
        ({"type": "string", "value": ""}, [6]),
        ({"type": "array", "length": 0}, [7]),
        ({"type": "object", "keys": []}, [8]),
        ({"type": "array", "length": 2}, [9, 10]),
        ({"type": "absent"}, [1]),
    ]
    assert variants(files, stream, "/a~1b~0") == expected
    assert variants(files, stream, "/a~1b~0/0") == [
        ({"type": "integer", "value": 1}, [9]),
        ({"type": "integer", "value": 2}, [10]),
        ({"type": "absent"}, list(range(1, 9))),
    ]
    field = next(f for f in table(files, stream["fields"]) if f["path"] == "/a~1b~0" and f["view"] == "resource")
    assert (field["observations"], field["present"], field["absent"]) == (10, 9, 1)


def test_complete_ledgers_preserve_duplicates_provenance_clocks_and_generic_field_changes() -> None:
    objects = [
        object_record(spec={"ports": [{"port": port}]}, status={"ready": ready, "restarts": count})
        for port, ready, count in [(80, False, 0), (80, False, 0), (443, True, 1), (80, False, 0)]
    ]
    sources = {"k8s_objects_raw.tsv": tsv(objects)}
    result = build_observation_index(sources, field_history=True)
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    stream = stream_view(files, index)
    ledger = table(files, stream["ledger"])
    assert [r["position"] for r in ledger] == [1, 2, 3, 4]
    assert len({r["id"] for r in ledger}) == 4
    assert [r["source"]["line_start"] for r in ledger] == [2, 3, 4, 5]
    assert all(
        r["source"]["sha256"] == hashlib.sha256(sources["k8s_objects_raw.tsv"].encode()).hexdigest() for r in ledger
    )
    assert all(r["clocks"]["collector"]["zone"] == "unknown" for r in ledger)
    assert [payload(files, r)["Body"] for r in ledger] == objects
    assert variants(files, stream, "/spec/ports/0/port") == [
        ({"type": "integer", "value": 80}, [1, 2, 4]),
        ({"type": "integer", "value": 443}, [3]),
    ]
    assert variants(files, stream, "/status/ready") == [
        ({"type": "boolean", "value": False}, [1, 2, 4]),
        ({"type": "boolean", "value": True}, [3]),
    ]


def test_resource_uid_event_subject_and_watch_views_are_separate_and_complete() -> None:
    original = object_record(status={"ready": False})
    replacement = {**object_record(), "metadata": {"name": "sample", "namespace": "demo", "uid": "u2"}}
    event = {
        "kind": "Event",
        "metadata": {"name": "event-1", "uid": "e1"},
        "regarding": {"kind": "Widget", "namespace": "demo", "name": "sample", "uid": "u1"},
        "reason": "Observed",
        "note": "ordinary event",
        "eventTime": "2025-12-15T17:00:00Z",
    }
    sources = {
        "k8s_objects_raw.tsv": tsv(
            [original, {"type": "DELETED", "object": original, "extra": "retained"}, replacement]
        ),
        "k8s_events_raw.tsv": tsv([event, event]),
        "otel_logs_raw.tsv": tsv(["log remains in original index"], log=True),
        "alerts/alerts_at_2025-12-15T17-00Z.json": "[]",
    }
    result = build_observation_index(sources, lookup_catalog=True, field_history=True)
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    object_stream, event_stream = stream_view(files, index), stream_view(files, index, "event")
    assert object_stream["observations"] == event_stream["observations"] == 2
    assert stream_view(files, index, uid="u2")["observations"] == 1
    assert variants(files, object_stream, "/status/ready") == [({"type": "boolean", "value": False}, [1, 2])]
    assert variants(files, object_stream, "/extra", "watch") == [
        ({"type": "string", "value": "retained"}, [2]),
        ({"type": "absent"}, [1]),
    ]
    assert variants(files, object_stream, "/Timestamp", "export") == [
        ({"type": "string", "value": "2025-12-15 17:54:00"}, [1, 2]),
    ]
    assert variants(files, event_stream, "/note") == [({"type": "string", "value": "ordinary event"}, [1, 2])]
    ledger = table(files, event_stream["ledger"])
    assert all(r["role"] == "event_subject" and r["observed_object"]["uid"] == "e1" for r in ledger)
    assert all(r["clocks"]["embedded"]["eventTime"] == event["eventTime"] for r in ledger)
    coverage = json.loads(files[index["extensions"][FIELD_HISTORY_PROFILE]["coverage"]])
    assert coverage["resources"] == 2 and coverage["streams"] == 3
    assert coverage["resource_records"] == 5 and coverage["other_records"] == 2
    assert coverage["complete"] is True


@pytest.mark.parametrize(
    ("literal", "status"),
    [
        ('{"x":1,"x":2}', "invalid_json"),
        ('{"x":NaN}', "invalid_json"),
        ('{"x":Infinity}', "invalid_json"),
        ('{"x":-Infinity}', "invalid_json"),
        ('{"x":', "invalid_json"),
        ("plain text", "not_container_json"),
        ("42", "not_container_json"),
        ("[" * 70 + "0" + "]" * 70, "depth_limit"),
    ],
)
def test_embedded_json_failures_preserve_literal_and_do_not_claim_normalized_absence(literal: str, status: str) -> None:
    files, index = prepared(
        [object_record(config='{"x":1}'), object_record(config=literal), object_record(config="{}")]
    )
    stream = stream_view(files, index)
    field = next(f for f in table(files, stream["fields"]) if f["view"] == "resource" and f["path"] == "/config")
    entries = table(files, field["values"])
    assert entries[1]["decode"]["status"] == status
    assert variants(files, stream, "/config")[1] == ({"type": "string", "value": literal}, [2])
    view = next(v for v in table(files, stream["views"]) if v.get("source_path") == "/config")
    assert positions(files, view["available"]) == [1, 3]
    assert variants(files, stream, "/x", view["id"]) == [
        ({"type": "integer", "value": 1}, [1]),
        ({"type": "absent"}, [3]),
    ]
    coverage = json.loads(files[index["extensions"][FIELD_HISTORY_PROFILE]["coverage"]])
    assert coverage["complete"] is True
    assert coverage["normalization_complete"] is (status == "not_container_json")
    assert view["unavailable"] == 1


def test_embedded_size_and_nested_decode_limits_preserve_exact_originals() -> None:
    large = '{"large":"' + "x" * 1_048_576 + '"}'
    nested = '{"leaf":0}'
    for _ in range(4):
        nested = json.dumps({"next": nested})
    files, index = prepared([object_record(large=large, nested=nested)])
    stream = stream_view(files, index)
    assert variants(files, stream, "/large") == [({"type": "string", "value": large}, [1])]
    fields = table(files, stream["fields"])
    large_field = next(f for f in fields if f["path"] == "/large" and f["view"] == "resource")
    assert table(files, large_field["values"])[0]["decode"]["status"] == "size_limit"
    assert variants(files, stream, "/nested") == [({"type": "string", "value": nested}, [1])]
    views = [v for v in table(files, stream["views"]) if v["kind"] == "embedded-json"]
    assert len(views) == 3
    counts = json.loads(files[index["extensions"][FIELD_HISTORY_PROFILE]["coverage"]])["string_decode_occurrences"]
    assert counts["size_limit"] == counts["decode_depth_limit"] == 1


def test_primary_depth_limit_refuses_instead_of_publishing_incomplete_fields() -> None:
    nested: Any = None
    for _ in range(70):
        nested = {"child": nested}
    with pytest.raises(ValueError, match="resource field depth limit"):
        prepared([object_record(deep=nested)])


def test_large_fields_ranges_and_tables_use_complete_bounded_locators_and_budget() -> None:
    large = "λ\n" * 4000
    objects = [object_record(message=large, alternating=i % 2) for i in range(120)]
    files, index = prepared(objects, page_bytes=2048)
    stream = stream_view(files, index)
    assert variants(files, stream, "/message") == [({"type": "string", "value": large}, list(range(1, 121)))]
    assert variants(files, stream, "/alternating") == [
        ({"type": "integer", "value": 0}, list(range(1, 121, 2))),
        ({"type": "integer", "value": 1}, list(range(2, 121, 2))),
    ]
    assert all(len(text.encode()) <= 2048 for text in files.values())
    assert json.loads(files[stream["ledger"]])["next"] is not None
    used = sum(len(text.encode()) for text in files.values())
    assert (
        build_observation_index(
            {"k8s_objects_raw.tsv": tsv(objects)}, page_bytes=2048, field_history=True, max_derived_bytes=used
        )["derived_bytes"]
        == used
    )
    with pytest.raises(ValueError, match="budget"):
        prepared(objects, page_bytes=2048, max_derived_bytes=used - 1)


def test_field_history_extension_preserves_every_legacy_file_and_is_disabled_by_default() -> None:
    sources = {"k8s_objects_raw.tsv": tsv([object_record(config='{"x":1}'), object_record(config='{"x":2}')])}
    legacy = build_observation_index(sources, lookup_catalog=True, page_bytes=2048)
    assert build_observation_index(sources, lookup_catalog=True, field_history=False, page_bytes=2048) == legacy
    extended = build_observation_index(sources, lookup_catalog=True, field_history=True, page_bytes=2048)
    assert extended["extensions"] == ["lookup-catalog-v1", FIELD_HISTORY_PROFILE]
    assert all(
        extended["files"][path] == text for path, text in legacy["files"].items() if path != "observations/index.json"
    )
    assert extended["derived_bytes"] == sum(len(text.encode()) for text in extended["files"].values())


def test_empty_history_coverage_and_unsupported_hidden_source_refusal() -> None:
    result = build_observation_index({}, field_history=True, page_bytes=2048)
    files = result["files"]
    extension = json.loads(files["observations/index.json"])["extensions"][FIELD_HISTORY_PROFILE]
    assert extension["directory"] is None
    assert json.loads(files[extension["coverage"]])["resource_records"] == 0
    with pytest.raises(ValueError, match="unsupported"):
        build_observation_index({"ground_truth.yaml": "answer: hidden"}, field_history=True)


def test_inline_field_values_requires_an_enabled_field_history() -> None:
    with pytest.raises(ValueError, match="requires field_history"):
        build_observation_index({}, inline_field_values=True)


def test_default_field_history_v1_files_remain_byte_identical() -> None:
    objects = [
        object_record(status={"ready": value}, config='{"number":1.0000000000000001}') for value in [False, True, False]
    ]
    sources = {"k8s_objects_raw.tsv": tsv(objects)}
    original = build_observation_index(sources, field_history=True, lookup_catalog=True, page_bytes=2048)
    assert hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest() == (
        "521d593ac9ad1eb03b652f56f8145d3156388b2705fec302a6989845020fce6a"
    )
    assert (
        build_observation_index(
            sources, field_history=True, lookup_catalog=True, page_bytes=2048, inline_field_values=False
        )
        == original
    )


def test_all_field_pages_are_searchable_and_inline_rows_expose_the_complete_history() -> None:
    objects = [
        object_record(**{f"alpha{i:02d}": i for i in range(30)}, status={"ready": ready})
        for ready in [False, True, False]
    ]
    sources = {"k8s_objects_raw.tsv": tsv(objects)}
    legacy = build_observation_index(sources, field_history=True, page_bytes=4096)
    result = build_observation_index(sources, field_history=True, inline_field_values=True, page_bytes=4096)
    assert result["extensions"] == ["resource-field-history-v2"]
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    stream = stream_view(files, index, profile="resource-field-history-v2")
    search = stream["fields_search"]
    assert search["glob"] == "*.json"
    field_pages = sorted(
        name
        for name in files
        if str(PurePosixPath(name).parent) == search["directory"] and PurePosixPath(name).match(search["glob"])
    )
    assert len(field_pages) > 1
    assert search["field_count"] == sum(json.loads(files[name])["returned"] for name in field_pages)
    assert not any(row["path"] == "/status/ready" for row in json.loads(files[stream["fields"]])["items"])
    matching_pages = [name for name in field_pages if '"path": "/status/ready"' in files[name]]
    assert len(matching_pages) == 1
    row = next(row for row in json.loads(files[matching_pages[0]])["items"] if row["path"] == "/status/ready")
    assert (row["observations"], row["present"], row["absent"], row["variants"]) == (3, 3, 0, 2)
    assert "values_table" not in row
    assert [(v["value"], positions(files, v["occurrences"])) for v in row["values"]] == [
        ({"type": "boolean", "value": False}, [1, 3]),
        ({"type": "boolean", "value": True}, [2]),
    ]
    assert not any(name.startswith("observations/field-history-v2/values/") for name in files)
    assert len(files) < len(legacy["files"])
    assert all(len(text.encode()) <= 4096 for text in files.values())


def test_inline_large_variant_sets_fall_back_to_complete_tables_and_preserve_payload_locators() -> None:
    large = "λ\n" * 2000
    objects = [object_record(status={"code": i}, payload=large) for i in range(40)]
    sources = {"k8s_objects_raw.tsv": tsv(objects)}
    result = build_observation_index(sources, field_history=True, inline_field_values=True, page_bytes=2048)
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    stream = stream_view(files, index, profile="resource-field-history-v2")
    fields = table(files, stream["fields"])
    code = next(row for row in fields if row["path"] == "/status/code" and row["view"] == "resource")
    assert "values" not in code
    assert json.loads(files[code["values_table"]])["next"] is not None
    assert variants(files, stream, "/status/code") == [({"type": "integer", "value": i}, [i + 1]) for i in range(40)]
    payload_row = next(row for row in fields if row["path"] == "/payload" and row["view"] == "resource")
    assert "values_table" not in payload_row
    assert "value_locator" in payload_row["values"][0]
    assert variants(files, stream, "/payload") == [({"type": "string", "value": large}, list(range(1, 41)))]
    assert all(len(text.encode()) <= 2048 for text in files.values())
    assert result["derived_bytes"] == sum(len(text.encode()) for text in files.values())
    assert (
        build_observation_index(
            sources,
            field_history=True,
            inline_field_values=True,
            page_bytes=2048,
            max_derived_bytes=result["derived_bytes"],
        )
        == result
    )
    with pytest.raises(ValueError, match="budget"):
        build_observation_index(
            sources,
            field_history=True,
            inline_field_values=True,
            page_bytes=2048,
            max_derived_bytes=result["derived_bytes"] - 1,
        )


def test_inline_fields_preserve_exact_decimals_absence_and_decoded_view_scope() -> None:
    objects = [
        object_record(config='{"number":1.0000000000000000}', optional=None),
        object_record(config='{"number":1.0000000000000001}'),
        object_record(config='{"number":1e0}', optional=None),
        object_record(),
    ]
    result = build_observation_index(
        {"k8s_objects_raw.tsv": tsv(objects)},
        field_history=True,
        lookup_catalog=True,
        inline_field_values=True,
        page_bytes=2048,
    )
    assert result["extensions"] == ["lookup-catalog-v1", "resource-field-history-v2"]
    files = result["files"]
    index = json.loads(files["observations/index.json"])
    stream = stream_view(files, index, profile="resource-field-history-v2")
    assert variants(files, stream, "/optional") == [
        ({"type": "null", "value": None}, [1, 3]),
        ({"type": "absent"}, [2, 4]),
    ]
    view = next(v for v in table(files, stream["views"]) if v.get("source_path") == "/config")
    assert positions(files, view["available"]) == [1, 2, 3] and view["unavailable"] == 1
    assert variants(files, stream, "/number", view["id"]) == [
        ({"type": "number", "coefficient": "1", "exponent": 0}, [1, 3]),
        ({"type": "number", "coefficient": "10000000000000001", "exponent": -16}, [2]),
    ]
    assert all(len(text.encode()) <= 2048 for text in files.values())


def test_inline_resource_directory_search_finds_later_pages_and_keeps_uid_identities_separate() -> None:
    objects = [
        {"kind": "Widget", "metadata": {"name": f"item-{i:02d}", "namespace": "demo", "uid": str(i)}} for i in range(30)
    ]
    objects.extend(
        [
            {"kind": "Widget", "metadata": {"name": "target", "namespace": "demo", "uid": uid}}
            for uid in ["target-1", "target-2"]
        ]
    )
    objects.append({"kind": "ClusterWidget", "metadata": {"name": "cluster", "uid": "cluster-1"}})
    files, index = prepared(objects, inline_field_values=True, page_bytes=2048)
    extension = index["extensions"]["resource-field-history-v2"]
    search = extension["resources_search"]
    pages = sorted(
        name
        for name in files
        if str(PurePosixPath(name).parent) == search["directory"] and PurePosixPath(name).match(search["glob"])
    )
    assert len(pages) > 1 and search["resource_count"] == 33
    assert sum(json.loads(files[name])["returned"] for name in pages) == search["resource_count"]
    literal = "demo/Widget/target"
    matching_pages = [name for name in pages if literal in files[name]]
    assert any(name != extension["directory"] for name in matching_pages)
    matches = [
        row for name in matching_pages for row in json.loads(files[name])["items"] if row["resource_path"] == literal
    ]
    assert {row["uid"] for row in matches} == {"target-1", "target-2"}
    assert len({row["id"] for row in matches}) == 2
    assert len({row["streams"] for row in matches}) == 2
    cluster = next(row for row in table(files, extension["directory"]) if row["uid"] == "cluster-1")
    assert cluster["resource_path"] == "ClusterWidget/cluster"
    assert all(len(text.encode()) <= 2048 for text in files.values())
