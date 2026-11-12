"""A disposable native fixture must contain evidence only and keep semantics unavailable."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
import weakref
from pathlib import Path
from typing import Any

import pytest
import yaml
from itbench_adapter import collect_submission, prepare_ground_truth, prepare_native
from itbench_adapter import native as native_module
from itbench_adapter.core import _read_asset
from itbench_adapter.observations import build_observation_index
from itbench_testkit import diagnosis, manifest
from probe.catalog import validate_scenario
from probe.checking import check_command_exit_zero
from probe.outcomes import State
from probe.workspaces import Workspace
from probe_testkit import context


def test_native_prep_is_bounded_observed_only_and_validates_existing_runner_contract(tmp_path: Path) -> None:
    source = tmp_path / "cache"
    m = manifest(source)
    destination = tmp_path / "runner-fixtures"
    receipt = prepare_native(m, source, destination, max_prepared_bytes=1_000_000)
    assert len(receipt["scenarios"]) == 5
    assert receipt["live_execution"] is False
    assert hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest() == (
        "cdff282eaeed3d84ba91b7fdb077f57a9311329e1d136778e096f274d1411cba"
    )
    # Golden serialized identity from the pre-index raw preparer, independent of the new opt-in path.
    assert {item["path"]: item["sha256"] for item in receipt["scenarios"]} == {
        "wp04-itbench-24.yaml": "5ed847b475381490a74ed687c57119d04400a9025a092281f65fbcc44c865281",
        "wp04-itbench-7.yaml": "bfdb8dd50221f96fd76f694d33615e20a538df3c6b5843764792cc0fcff7df43",
        "wp04-itbench-21.yaml": "993dcec5ae9b8b63ee44b73b59b959c52d5d6104ec152294664ec2b20f755eb7",
        "wp04-itbench-80.yaml": "4733f343c2a3328d58554ac8486ee2591fbb4fec1d6b3cc04599156fcba85dd2",
        "wp04-itbench-102.yaml": "20721d6ec4228c116ba7d58283791a3f7dba7b0c99e8adc09886af4adb32affb",
    }
    for item in receipt["scenarios"]:
        p = destination / item["path"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"]
        spec = yaml.safe_load(p.read_text())
        assert validate_scenario(spec, where=str(p)) == []
        assert spec["tools"] == ["Read", "Grep", "Glob", "Skill"]
        assert spec["agent"] == "sre-assistant"
        assert set(spec["fixture"]["files"]) == {"k8s_events_raw.tsv"}
        serialized = p.read_text()
        assert "ANSWER_CANARY" not in serialized
        assert "recommended_actions" not in serialized
        assert "ground_truth.yaml" not in serialized
        assert "aliases" not in serialized
        assert spec["checks"][-1]["inconclusive_exit_code"] == 2


def test_prep_refuses_before_output_when_raw_budget_too_small(tmp_path: Path) -> None:
    source = tmp_path / "cache"
    m = manifest(source)
    with pytest.raises(ValueError, match="budget"):
        prepare_native(m, source, tmp_path / "fixtures", max_prepared_bytes=1)
    assert not (tmp_path / "fixtures").exists()


@pytest.mark.parametrize(
    "profile", ["raw", "indexed-v1", "indexed-v2", "indexed-v3", "indexed-v4", "indexed-v5", "indexed-v6"]
)
def test_native_serialization_accepts_exact_byte_budget_and_cleans_partial_output(tmp_path: Path, profile: str) -> None:
    source = tmp_path / "source"
    m = indexable_manifest(source)
    reference = prepare_native(m, source, tmp_path / "reference", evidence_profile=profile)
    budget = reference["prepared_bytes"]
    exact = prepare_native(m, source, tmp_path / "exact", evidence_profile=profile, max_prepared_bytes=budget)
    assert exact == {**reference, "max_prepared_bytes": budget}
    assert {p.name: p.read_bytes() for p in (tmp_path / "exact").iterdir()} == {
        p.name: p.read_bytes() for p in (tmp_path / "reference").iterdir()
    }
    with pytest.raises(ValueError, match="serialized native fixtures exceed prepared-byte budget"):
        prepare_native(m, source, tmp_path / "too-small", evidence_profile=profile, max_prepared_bytes=budget - 1)
    assert not (tmp_path / "too-small").exists()
    assert not list(tmp_path.glob(".wp04-native-*"))


def test_native_dump_streams_without_materializing_a_serialized_return_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    m = indexable_manifest(source)
    real_dump = yaml.dump
    completed = []

    def checked_dump(*args: Any, **kwargs: Any) -> Any:
        assert kwargs.get("stream") is not None, "native fixtures must stream instead of accumulating YAML"
        result = real_dump(*args, **kwargs)
        assert result is None
        completed.append(args[0]["id"])
        return result

    monkeypatch.setattr(yaml, "dump", checked_dump)
    result = prepare_native(m, source, tmp_path / "native", evidence_profile="indexed-v3")
    assert len(completed) == len(result["scenarios"]) == 5


def test_native_stream_writer_counts_utf8_and_refuses_before_exceeding_budget() -> None:
    stream = io.BytesIO()
    writer = native_module._FixtureWriter(stream, 5)
    assert writer.write("λ\n") == 2
    assert writer.write("é") == 1
    expected = "λ\né".encode()
    assert stream.getvalue() == expected
    assert writer.size == 5
    assert writer.sha256.hexdigest() == hashlib.sha256(expected).hexdigest()
    with pytest.raises(ValueError, match="serialized native fixtures exceed prepared-byte budget"):
        writer.write("x")
    assert stream.getvalue() == expected
    assert writer.size == 5
    assert writer.sha256.hexdigest() == hashlib.sha256(expected).hexdigest()


@pytest.mark.parametrize("profile", ["raw", "indexed-v3"])
def test_native_releases_original_and_derived_contents_before_reading_next_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str
) -> None:
    source = tmp_path / "source"
    m = indexable_manifest(source)
    pending: list[weakref.ReferenceType[str]] = []
    previous_source: Path | None = None
    read_asset, build_index = _read_asset, build_observation_index

    class TrackedText(str):
        pass

    dumper = getattr(yaml, "CSafeDumper", yaml.SafeDumper)
    represent_string = dumper.yaml_representers[str]

    def represent_tracked(instance: Any, value: str) -> Any:
        return represent_string(instance, str(value))

    monkeypatch.setitem(dumper.yaml_representers, TrackedText, represent_tracked)

    class TrackedBytes(bytes):
        def decode(self, *args: Any, **kwargs: Any) -> str:
            text = TrackedText(super().decode(*args, **kwargs))
            pending.append(weakref.ref(text))
            return text

    def checked_read(root: Path, *args: Any, **kwargs: Any) -> bytes:
        nonlocal previous_source
        if root != previous_source:
            assert all(ref() is None for ref in pending), "previous case contents are still retained"
            previous_source = root
        return TrackedBytes(read_asset(root, *args, **kwargs))

    def checked_index(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = build_index(*args, **kwargs)
        for name, text in result["files"].items():
            tracked = TrackedText(text)
            pending.append(weakref.ref(tracked))
            result["files"][name] = tracked
        return result

    monkeypatch.setattr(native_module, "_read_asset", checked_read)
    monkeypatch.setattr(native_module, "build_observation_index", checked_index)
    prepare_native(m, source, tmp_path / "native", evidence_profile=profile)
    assert pending and all(ref() is None for ref in pending)


def test_collect_preserves_claims_and_rejects_case_mismatch_or_ambiguity() -> None:
    d = diagnosis()
    response = "Returning to: human requester\n```json\n" + json.dumps(d) + "\n```\nCaller next step: review."
    assert collect_submission(response, "wp04-24") == d
    with pytest.raises(ValueError, match="case"):
        collect_submission(response, "wp04-29")
    with pytest.raises(ValueError, match="one"):
        collect_submission(response + "\n```json\n" + json.dumps(d) + "\n```", "wp04-24")


def test_native_manual_check_is_unavailable_and_missing_interpreter_is_instrument_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "cache"
    m = manifest(source)
    dest = tmp_path / "prepared"
    prepare_native(m, source, dest, max_prepared_bytes=1_000_000)
    spec = yaml.safe_load((dest / "wp04-itbench-24.yaml").read_text())
    check = spec["checks"][-1]
    ws = Workspace(tmp_path, tmp_path, tmp_path / "bin", tmp_path / "state", 0, "main")
    ctx = context(spec, ws=ws)
    monkeypatch.setenv("PATH", str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""))
    outcome = check_command_exit_zero(ctx, check)
    assert outcome.state == State.INCONCLUSIVE
    assert outcome.machinery is False
    missing = {**check, "command": 'wp04-no-such-interpreter -c "raise SystemExit(2)"'}
    outcome = check_command_exit_zero(ctx, missing)
    assert outcome.state == State.INCONCLUSIVE
    assert outcome.machinery is True


def test_upstream_ground_truth_projection_preserves_source_entities_edges_and_aliases(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = manifest(source)
    raw_truth = {
        "groups": [{"id": "original-root", "kind": "JVMChaos", "root_cause": True}],
        "fault": [{"entity": {"kind": "Service", "group_id": "original-root"}}],
        "propagations": [{"source": "original-root", "target": "dangling-original"}],
        "aliases": [["original-root", "original-alias"]],
    }
    originals = {}
    for case in m["cases"]:
        body = (
            {"apiVersion": "itbench.io/v1", "kind": "GroundTruth", "spec": raw_truth}
            if case["source_id"] == "Scenario-102"
            else raw_truth
        )
        p = source / case["source_id"] / "ground_truth.yaml"
        p.write_text(yaml.safe_dump(body))
        originals[case["source_id"]] = p.read_bytes()
        case["hidden"][0].update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), size=p.stat().st_size)
    result = prepare_ground_truth(m, source)
    assert len(result["ground_truths"]) == 5
    assert {v["id"] for v in result["ground_truths"]} == {"7", "21", "24", "80", "102"}
    for value in result["ground_truths"]:
        assert {k: v for k, v in value.items() if k != "id"} == raw_truth
    assert result["receipt"]["wrapper_unwrapped"] == ["Scenario-102"]
    assert all((source / case / "ground_truth.yaml").read_bytes() == data for case, data in originals.items())


def test_upstream_truth_preparation_rejects_tampered_hidden_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = manifest(source)
    (source / m["cases"][0]["source_id"] / "ground_truth.yaml").write_text("changed answer")
    with pytest.raises(ValueError, match="mismatch"):
        prepare_ground_truth(m, source)


def test_native_prompt_describes_actual_per_case_log_availability(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = manifest(source)
    case = next(c for c in m["cases"] if c["id"] == "wp04-7")
    log = source / "Scenario-7" / "otel_logs_raw.tsv"
    log.write_text("Timestamp\tBody\n2025-12-15 18:00:00\tobserved application event\n")
    case["observables"].append(
        {
            "path": "otel_logs_raw.tsv",
            "sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            "size": log.stat().st_size,
        }
    )
    prepare_native(m, source, tmp_path / "native", max_prepared_bytes=1_000_000)
    with_logs = yaml.safe_load((tmp_path / "native/wp04-itbench-7.yaml").read_text())
    without_logs = yaml.safe_load((tmp_path / "native/wp04-itbench-24.yaml").read_text())
    assert "Application logs are supplied" in with_logs["prompt"]
    assert "Application logs are unavailable" in without_logs["prompt"]
    assert "Traces and metrics are unavailable" in with_logs["prompt"]


def indexable_manifest(source: Path) -> dict[str, Any]:
    m = manifest(source)
    for case in m["cases"]:
        body = {
            "kind": "Event",
            "metadata": {"name": "event-1", "uid": "event-uid"},
            "regarding": {"kind": "Pod", "name": "worker", "namespace": "demo", "uid": "pod-uid"},
            "eventTime": "2025-12-15T17:00:00Z",
            "note": "ordinary observation",
        }
        buf = io.StringIO(newline="")
        writer = csv.writer(buf, delimiter="\t", lineterminator="\n")
        writer.writerow(["Timestamp", "Body"])
        writer.writerow(["2025-12-15 18:00:00", json.dumps(body)])
        p = source / case["source_id"] / "k8s_events_raw.tsv"
        p.write_text(buf.getvalue())
        case["observables"][0].update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), size=p.stat().st_size)
    return m


def test_indexed_preparation_retains_raw_inputs_has_distinct_identity_and_never_reads_hidden(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = indexable_manifest(source)
    for case in m["cases"]:
        (source / case["source_id"] / "ground_truth.yaml").unlink()
    raw = prepare_native(m, source, tmp_path / "raw")
    explicit_raw = prepare_native(m, source, tmp_path / "explicit-raw", evidence_profile="raw")
    assert raw == explicit_raw
    assert {p.name: p.read_bytes() for p in (tmp_path / "raw").iterdir()} == {
        p.name: p.read_bytes() for p in (tmp_path / "explicit-raw").iterdir()
    }
    result = prepare_native(m, source, tmp_path / "indexed", evidence_profile="indexed-v1")
    assert result["evidence_profile"] == "indexed-v1"
    # Freeze the measured v1 condition, including prompt, serialized fixtures and receipt.
    assert hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest() == (
        "a6ad6c097fa5ba30431a5ce91bc769f44eebff9d131c9ec1ffcbf0d59388d538"
    )
    assert {item["path"]: item["sha256"] for item in result["scenarios"]} == {
        "wp04-itbench-24-indexed-v1.yaml": "457d2a3d1b971e68f302dad7e96ac8a40ed3f157c731fd88640506ca5d26fa59",
        "wp04-itbench-7-indexed-v1.yaml": "a2639e3ebcf77988d38e4c3930a1941a8fae2e602a1e4fc6001a438099a97bb4",
        "wp04-itbench-21-indexed-v1.yaml": "dfff1a4e23d8518f6361940f340c289ca3061b40ab54658ccf3f210e973d78bc",
        "wp04-itbench-80-indexed-v1.yaml": "58cce710269621c6eab5dd02b5c275c1fe5ca7dce6a0369c9fce003ed6f884bf",
        "wp04-itbench-102-indexed-v1.yaml": "ec2594808bb379067deb0b3b30e5b3f4d94855eb7b0a79f8dd801a5d9b5159e7",
    }
    for item in result["scenarios"]:
        path = tmp_path / "indexed" / item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        spec = yaml.safe_load(path.read_text())
        assert spec["id"].endswith("-indexed-v1")
        assert validate_scenario(spec, where=item["path"]) == []
        assert spec["tools"] == ["Read", "Grep", "Glob", "Skill"]
        files = spec["fixture"]["files"]
        assert files["k8s_events_raw.tsv"] == (source / item["source_id"] / "k8s_events_raw.tsv").read_text()
        assert "observations/index.json" in files
        assert "observations/index.json" in spec["prompt"]
        assert "alert filenames omit a timezone" not in spec["prompt"]
        assert "no later\nobservation" not in spec["prompt"]
        assert "Alert filenames ending Z.json explicitly indicate UTC" in spec["prompt"]
        assert "later timestamps may occur within these released records" in spec["prompt"]
        assert "ANSWER_CANARY" not in json.dumps(files)
        assert item["derived_evidence"]["profile"] == "indexed-v1"
        assert item["case_id"] in {c["id"] for c in m["cases"]}  # submission/scoring identity unchanged


def test_indexed_v2_changes_only_prompt_identity_and_preserves_all_observations(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = indexable_manifest(source)
    m["profile"] = "released-source-profile"
    for case in m["cases"]:
        (source / case["source_id"] / "ground_truth.yaml").unlink()
    v1 = prepare_native(m, source, tmp_path / "v1", evidence_profile="indexed-v1")
    v2 = prepare_native(m, source, tmp_path / "v2", evidence_profile="indexed-v2")
    assert v2["evidence_profile"] == "indexed-v2"
    assert v2["observation_index_profile"] == "indexed-v1"
    assert v2["source_observation_profile"] == v1["source_observation_profile"] == m["profile"]
    assert v2["manifest_sha256"] == v1["manifest_sha256"]
    assert v2["raw_observable_bytes"] == v1["raw_observable_bytes"]
    for previous, current in zip(v1["scenarios"], v2["scenarios"], strict=True):
        assert current["path"] == previous["path"].replace("-indexed-v1.yaml", "-indexed-v2.yaml")
        assert current["case_id"] == previous["case_id"]
        assert current["source_assets"] == previous["source_assets"]
        assert current["derived_evidence"] == previous["derived_evidence"]
        old_spec = yaml.safe_load((tmp_path / "v1" / previous["path"]).read_text())
        path = tmp_path / "v2" / current["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == current["sha256"]
        spec = yaml.safe_load(path.read_text())
        assert spec["id"] == old_spec["id"].replace("-indexed-v1", "-indexed-v2")
        assert validate_scenario(spec, where=current["path"]) == []
        assert {k: v for k, v in spec.items() if k not in {"id", "prompt"}} == {
            k: v for k, v in old_spec.items() if k not in {"id", "prompt"}
        }
        assert json.loads(spec["fixture"]["files"]["observations/index.json"])["profile"] == "indexed-v1"
        assert "ANSWER_CANARY" not in json.dumps(spec)
        prompt = spec["prompt"]
        assert "Do not infer offsets or align these clocks" not in prompt
        assert "You may order explicitly zoned, comparable timestamps using their stated zones." in prompt
        assert "Do not infer offsets or relationships between these timestamps and unknown-zone clocks." in prompt
        assert "later timestamps may occur within these released records" in prompt
        assert "No further conversational\nobservation release or human mitigation" in prompt
        assert prompt == old_spec["prompt"].replace(
            "Do not infer offsets or align these clocks. ",
            "You may order explicitly zoned, comparable timestamps using their stated zones.\n"
            "Do not infer offsets or relationships between these timestamps and unknown-zone clocks.\n",
        ).replace("Evidence profile indexed-v1:", "Evidence profile indexed-v2:")


def test_indexed_v2_serialized_fixtures_and_receipt_remain_frozen(tmp_path: Path) -> None:
    source = tmp_path / "source"
    receipt = prepare_native(indexable_manifest(source), source, tmp_path / "v2", evidence_profile="indexed-v2")
    assert hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest() == (
        "47eeee8468bb794e0a77af6b09c2d76529274b52334ffcd02b436248c550fbbc"
    )
    assert {item["path"]: item["sha256"] for item in receipt["scenarios"]} == {
        "wp04-itbench-24-indexed-v2.yaml": "2c40cc4007aeecb79a17a00cba1a955158f1bd22420d6a1d179a4f66ce7a8e55",
        "wp04-itbench-7-indexed-v2.yaml": "9b6c42d57c480edeeabdf72c84302e6e8c7f7a11e2bf26edb960d9f37d965a67",
        "wp04-itbench-21-indexed-v2.yaml": "eb4f69ba8b5576672c065c4c2588858d6c55446fb2e6cb19ac0b49bc4c95965a",
        "wp04-itbench-80-indexed-v2.yaml": "96154a90df6ec8540fff4bd01f2d0d1a3f763f144ec0105e1c15cac4ff596925",
        "wp04-itbench-102-indexed-v2.yaml": "339547d7052c9d3a78604db3d44fa05b62e15a482a75d060680a3dfa17a8e0bf",
    }
    for item in receipt["scenarios"]:
        assert hashlib.sha256((tmp_path / "v2" / item["path"]).read_bytes()).hexdigest() == item["sha256"]


def test_indexed_v3_exposes_catalogs_with_distinct_identity_and_never_reads_hidden(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = indexable_manifest(source)
    for case in m["cases"]:
        (source / case["source_id"] / "ground_truth.yaml").unlink()
    v2 = prepare_native(m, source, tmp_path / "v2", evidence_profile="indexed-v2")
    v3 = prepare_native(m, source, tmp_path / "v3", evidence_profile="indexed-v3")
    assert hashlib.sha256(json.dumps(v3, sort_keys=True).encode()).hexdigest() == (
        "e21fcc70c9451cafb9a373e66806b92ea016509e31fb1e5a6a9ba0d54e8c32aa"
    )
    assert {item["path"]: item["sha256"] for item in v3["scenarios"]} == {
        "wp04-itbench-24-indexed-v3.yaml": "20bff46493667b0e6eaaa7bb216cf2b748eb40e3842a75d2cae999dcbdef8aa5",
        "wp04-itbench-7-indexed-v3.yaml": "310ebfe1b89790f56cac012aea8f819b4b21d4c7711b2dc8fe527f0f18147016",
        "wp04-itbench-21-indexed-v3.yaml": "9a15d9de44a083fa3f04eecd4eecba9718b407cfca191479635e6be9ab716dd4",
        "wp04-itbench-80-indexed-v3.yaml": "8cbc61f58aa1e54b0d478a09457b5358cb334c451da2e1cc900790ec0ce22887",
        "wp04-itbench-102-indexed-v3.yaml": "c35e909d1ecfdd758148b80c0affb1c6b5be7ebb251bb9b8b565245a062e4b79",
    }
    assert v3["evidence_profile"] == "indexed-v3"
    assert v3["observation_index_profile"] == "indexed-v1"
    assert v3["observation_index_extensions"] == ["lookup-catalog-v1"]
    assert v3["manifest_sha256"] == v2["manifest_sha256"]
    assert v3["raw_observable_bytes"] == v2["raw_observable_bytes"]
    for previous, current in zip(v2["scenarios"], v3["scenarios"], strict=True):
        assert current["path"] == previous["path"].replace("-indexed-v2.yaml", "-indexed-v3.yaml")
        assert current["case_id"] == previous["case_id"]
        assert current["source_assets"] == previous["source_assets"]
        assert current["derived_evidence"]["profile"] == "indexed-v1"
        assert current["derived_evidence"]["extensions"] == ["lookup-catalog-v1"]
        assert current["derived_evidence"]["derived_bytes"] > previous["derived_evidence"]["derived_bytes"]
        old_spec = yaml.safe_load((tmp_path / "v2" / previous["path"]).read_text())
        path = tmp_path / "v3" / current["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == current["sha256"]
        spec = yaml.safe_load(path.read_text())
        assert spec["id"] == old_spec["id"].replace("-indexed-v2", "-indexed-v3")
        assert validate_scenario(spec, where=current["path"]) == []
        assert spec["tools"] == old_spec["tools"]
        files = spec["fixture"]["files"]
        assert all(
            files[name] == text
            for name, text in old_spec["fixture"]["files"].items()
            if name != "observations/index.json"
        )
        assert "lookup-catalog-v1" in json.loads(files["observations/index.json"])["extensions"]
        assert "ANSWER_CANARY" not in json.dumps(spec)
        assert spec["prompt"].startswith(
            old_spec["prompt"].replace("Evidence profile indexed-v2:", "Evidence profile indexed-v3:")
        )
        assert "Search JSONL files with literal patterns" in spec["prompt"]
        assert "payload_complete:false" in spec["prompt"]
        assert "Follow every next link and check totals/coverage" in spec["prompt"]


def test_indexed_prep_refuses_malformed_inputs_and_unknown_profile_without_publishing(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = manifest(source)  # valid manifest, intentionally opaque/non-JSON Event Body
    for profile in ["indexed-v1", "indexed-v2", "indexed-v3", "indexed-v4", "indexed-v5", "indexed-v6", "unrecognized"]:
        with pytest.raises(ValueError):
            prepare_native(m, source, tmp_path / profile, evidence_profile=profile)
        assert not (tmp_path / profile).exists()


def test_native_prep_refuses_unknown_profile_with_valid_observations(tmp_path: Path) -> None:
    source = tmp_path / "source"
    m = indexable_manifest(source)
    with pytest.raises(ValueError, match="unsupported evidence profile"):
        prepare_native(m, source, tmp_path / "invalid", evidence_profile="unrecognized")
    assert not (tmp_path / "invalid").exists()


@pytest.mark.parametrize(
    "profile", ["indexed-v1", "indexed-v2", "indexed-v3", "indexed-v4", "indexed-v5", "indexed-v6"]
)
def test_indexed_native_keeps_hash_and_symlink_boundaries(tmp_path: Path, profile: str) -> None:
    source = tmp_path / "source"
    m = indexable_manifest(source)
    p = source / m["cases"][0]["source_id"] / "k8s_events_raw.tsv"
    original = p.read_bytes()
    p.write_bytes(original + b"tamper")
    with pytest.raises(ValueError, match="mismatch"):
        prepare_native(m, source, tmp_path / "tampered", evidence_profile=profile)
    p.unlink()
    outside = tmp_path / "outside.tsv"
    outside.write_bytes(original)
    p.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        prepare_native(m, source, tmp_path / "symlink", evidence_profile=profile)


def test_indexed_v4_adds_resource_field_histories_without_changing_grants_or_prior_evidence(tmp_path: Path) -> None:
    source = tmp_path / "source"
    manifest_data = indexable_manifest(source)
    for case in manifest_data["cases"]:
        (source / case["source_id"] / "ground_truth.yaml").unlink()
    v3 = prepare_native(manifest_data, source, tmp_path / "v3", evidence_profile="indexed-v3")
    v4 = prepare_native(manifest_data, source, tmp_path / "v4", evidence_profile="indexed-v4")
    extensions = ["lookup-catalog-v1", "resource-field-history-v1"]
    assert v4["evidence_profile"] == "indexed-v4"
    assert v4["observation_index_profile"] == "indexed-v1"
    assert v4["observation_index_extensions"] == extensions
    assert v4["manifest_sha256"] == v3["manifest_sha256"]
    for previous, current in zip(v3["scenarios"], v4["scenarios"], strict=True):
        assert current["case_id"] == previous["case_id"]
        assert current["source_assets"] == previous["source_assets"]
        assert current["derived_evidence"]["extensions"] == extensions
        old = yaml.safe_load((tmp_path / "v3" / previous["path"]).read_text())
        spec = yaml.safe_load((tmp_path / "v4" / current["path"]).read_text())
        assert validate_scenario(spec, where=current["path"]) == []
        assert spec["tools"] == old["tools"] == ["Read", "Grep", "Glob", "Skill"]
        assert spec["checks"] == old["checks"]
        assert spec["max_turns"] == old["max_turns"]
        files = spec["fixture"]["files"]
        assert all(
            text == files[name] for name, text in old["fixture"]["files"].items() if name != "observations/index.json"
        )
        index = json.loads(files["observations/index.json"])
        assert set(index["extensions"]) == set(extensions)
        assert "ANSWER_CANARY" not in json.dumps(spec)
        assert current["sha256"] != previous["sha256"]


def test_indexed_v5_exposes_complete_search_scope_and_inline_values_without_new_tools(tmp_path: Path) -> None:
    source = tmp_path / "source"
    manifest_data = indexable_manifest(source)
    for case in manifest_data["cases"]:
        (source / case["source_id"] / "ground_truth.yaml").unlink()
    v4 = prepare_native(manifest_data, source, tmp_path / "v4", evidence_profile="indexed-v4")
    v5 = prepare_native(manifest_data, source, tmp_path / "v5", evidence_profile="indexed-v5")
    assert v5["observation_index_extensions"] == ["lookup-catalog-v1", "resource-field-history-v2"]
    for previous, current in zip(v4["scenarios"], v5["scenarios"], strict=True):
        assert previous["source_assets"] == current["source_assets"]
        assert previous["case_id"] == current["case_id"]
        old = yaml.safe_load((tmp_path / "v4" / previous["path"]).read_text())
        spec = yaml.safe_load((tmp_path / "v5" / current["path"]).read_text())
        assert spec["tools"] == old["tools"] == ["Read", "Grep", "Glob", "Skill"]
        assert spec["checks"] == old["checks"] and spec["max_turns"] == old["max_turns"]
        assert validate_scenario(spec, where=current["path"]) == []
        files = spec["fixture"]["files"]
        extension = json.loads(files["observations/index.json"])["extensions"]["resource-field-history-v2"]
        resource = json.loads(files[extension["directory"]])["items"][0]
        stream = json.loads(files[resource["streams"]])["items"][0]
        scope = stream["fields_search"]
        assert stream["fields"].startswith(scope["directory"] + "/")
        fields = json.loads(files[stream["fields"]])["items"]
        assert any(isinstance(field.get("values"), list) for field in fields)
        assert "ANSWER_CANARY" not in json.dumps(spec)
        assert current["derived_evidence"]["extensions"] == v5["observation_index_extensions"]


def test_indexed_v6_scopes_record_catalogs_without_changing_raw_sources_or_grading(tmp_path: Path) -> None:
    source = tmp_path / "source"
    manifest_data = indexable_manifest(source)
    for case in manifest_data["cases"]:
        (source / case["source_id"] / "ground_truth.yaml").unlink()
    v5 = prepare_native(manifest_data, source, tmp_path / "v5", evidence_profile="indexed-v5")
    v6 = prepare_native(manifest_data, source, tmp_path / "v6", evidence_profile="indexed-v6")
    assert v6["observation_index_extensions"] == ["lookup-catalog-v2", "resource-field-history-v2"]
    for previous, current in zip(v5["scenarios"], v6["scenarios"], strict=True):
        assert previous["source_assets"] == current["source_assets"]
        assert previous["case_id"] == current["case_id"]
        old = yaml.safe_load((tmp_path / "v5" / previous["path"]).read_text())
        spec = yaml.safe_load((tmp_path / "v6" / current["path"]).read_text())
        assert spec["tools"] == old["tools"] == ["Read", "Grep", "Glob", "Skill"]
        assert spec["checks"] == old["checks"] and spec["max_turns"] == old["max_turns"]
        assert validate_scenario(spec, where=current["path"]) == []
        files = spec["fixture"]["files"]
        assert files["k8s_events_raw.tsv"] == old["fixture"]["files"]["k8s_events_raw.tsv"]
        ext = json.loads(files["observations/index.json"])["extensions"]["lookup-catalog-v2"]
        categories = json.loads(files[ext["catalogs"]])["items"]
        events = next(row for row in categories if row["category"] == "event")
        group = json.loads(files[events["resource_groups"]])["items"][0]
        assert group["resource"]["name"] == "worker"
        page = json.loads(files[group["first"]])
        assert page["resource"] == group["resource"]
        assert json.loads(files[page["rows"]])["resource"] == group["resource"]
        assert not any(name.startswith("observations/lookup/event/") for name in files)
        assert "ANSWER_CANARY" not in json.dumps(spec)
