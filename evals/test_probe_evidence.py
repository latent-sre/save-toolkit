"""Evidence-v1: what an attempt writes beside its grade, and what `legacy` reads back from a run saved
before it (stage 1 of the runner rewrite, RUNNER-001).

The goldens are pre-evidence directories by construction, so every case gives one live attempt that
writes `evidence.json` and one saved directory that `legacy` loads; the two must describe the same
run wherever the facts are the run's and not the host's or the clock's.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import shutil
from pathlib import Path
from unittest import mock

import golden_runs
import judge
import pytest
from probe import checking, evidence, rescoring, tracing
from probe.checking import Need

CASES = [c for c in golden_runs.CASES if not c.raises]
IDS = [c.name for c in CASES]
ROOT = Path(__file__).resolve().parent.parent


def _live(item: golden_runs.Case, root: Path) -> tuple[Path, evidence.EvidenceV1, dict]:
    root.mkdir(exist_ok=True)
    run_dir, grading, _raised, _summary = golden_runs.run_live(item, root)
    assert grading is not None
    text = (run_dir / evidence.FILE).read_text(encoding="utf-8")
    return run_dir, evidence.EvidenceV1.model_validate_json(text), grading


def _saved(item: golden_runs.Case, root: Path) -> tuple[Path, evidence.EvidenceV1]:
    copy = root / "saved" / "run-1"
    shutil.copytree(golden_runs.FIXTURES / item.name / "run-1", copy)
    golden_runs.denormalize(copy, root / "saved")
    return copy, rescoring.load_evidence(copy, golden_runs.scenario(item))


def test_the_published_schema_is_the_model() -> None:
    published = json.loads((ROOT / "docs/fleet-evaluation/eval-evidence-v1.schema.json").read_text("utf-8"))
    assert published == evidence.evidence_schema(), (
        "regenerate: python evals/build_probe.py schema --model evidence "
        "--out docs/fleet-evaluation/eval-evidence-v1.schema.json"
    )


def test_the_trace_block_carries_every_trace_summary_field() -> None:
    """The parsed trace goes into the evidence in full; a field added to `TraceSummary` must be added here."""
    summary_fields = {f.name for f in dataclasses.fields(tracing.TraceSummary)}
    assert set(evidence.Trace.model_fields) == summary_fields | {"raw_sha256", "restored_from_summary"}


def test_every_need_a_regradable_check_reads_has_a_block() -> None:
    """The twenty regradable checks read only what the evidence keeps; the rest are probes whose
    live outcome is evidence. The partition is the one `checking` declares, not a hand-kept list."""
    blocks = {
        Need.TEXT: "trace",
        Need.TRACE: "trace",
        Need.RAW_TRACE: "trace",
        Need.ORDERED_TRACE: "trace",
        Need.CHANGES: "git",
        Need.STATE: "workspace",
        Need.CHECKOUT: "probes",
        Need.SERVICE: "probes",
        Need.JUDGE: "probes",
    }
    assert set(blocks) == set(Need)
    assert set(blocks.values()) <= set(evidence.EvidenceV1.model_fields)
    regradable, probes = [], []
    for name, declared in checking.CHECKS.items():
        needs = declared.needs_of({"check": name}, {})
        (regradable if declared.can_regrade({"check": name}, {}) else probes).append(name)
        if declared.regradable is None:
            assert (needs <= checking.SAVED) == (name in regradable), name
    assert regradable and probes
    assert set(regradable) == checking.REGRADABLE


@pytest.mark.parametrize("item", CASES, ids=IDS)
def test_a_live_attempt_writes_evidence_that_round_trips_and_holds_no_verdict(
    item: golden_runs.Case, tmp_path: Path
) -> None:
    run_dir, found, grading = _live(item, tmp_path)
    assert found.written_by == "live"
    assert found.format.model_dump() == evidence.EVIDENCE_FORMAT
    dumped = found.model_dump_json()
    assert evidence.EvidenceV1.model_validate_json(dumped) == found
    assert json.loads((run_dir / evidence.FILE).read_text("utf-8")) == json.loads(dumped)
    top = set(found.model_dump())
    assert not {"status", "summary", "expectations", "verdict"} & top
    # The trace block is the parsed raw trace, field for field, with the trace's own digest.
    parsed = dataclasses.asdict(tracing.parse_trial_trace(run_dir))
    assert {k: found.trace.model_dump(mode="json")[k] for k in parsed} == json.loads(json.dumps(parsed))
    assert found.trace.raw_sha256["stdout.jsonl"] == evidence.file_sha256(run_dir / "stdout.jsonl")
    assert found.trace.restored_from_summary is False
    assert found.identity.scenario_sha256 == grading["scenario_sha256"]
    assert found.identity.case_id == item.spec()["id"]
    assert found.host.workspace and found.host.plugin_served_from
    record = json.loads((run_dir / "record.json").read_text("utf-8"))
    assert record["evidence"]["evidence.json"] == "evidence.json"


@pytest.mark.parametrize("item", CASES, ids=IDS)
def test_legacy_reads_a_saved_run_into_the_evidence_the_live_attempt_wrote(
    item: golden_runs.Case, tmp_path: Path
) -> None:
    """A pre-evidence directory loads into the same evidence as the live attempt, except where the fact
    is the host's or the clock's (temporary paths, fresh fixture commits, timestamps, the runner
    identity in a probe's id) and three the old format never saved (the identity failure and the
    service problem the batch read from the result row, and a final text the live trace left empty,
    which a regrade reads back as the `(no result)` placeholder the response file holds)."""
    _run_dir, live, _grading = _live(item, tmp_path / "live")
    _copy, saved = _saved(item, tmp_path)
    assert saved.written_by == "legacy"

    def comparable(found: evidence.EvidenceV1) -> dict:
        d = found.model_dump(mode="json")
        trace = {
            **d["trace"],
            "raw_sha256": sorted(d["trace"]["raw_sha256"]),
            "runtime_plugins": [p.get("name") for p in d["trace"]["runtime_plugins"]],
        }
        trace["result_text"] = trace["result_text"] or "(no result)"
        git = {
            **d["git"],
            "commit_ids_before": len(d["git"]["commit_ids_before"] or []),
            "commit_ids_after": len(d["git"]["commit_ids_after"] or []),
        }
        turns = [
            {
                k: t[k]
                for k in (
                    "folder",
                    "resume",
                    "expected_model",
                    "session_id",
                    "main_models",
                    "init_session_ids",
                    "exit_code",
                    "state",
                    "cut_short",
                    "run_stop",
                    "inconclusive",
                )
            }
            for t in d["turns"]
        ]
        probes = [{k: p[k] for k in ("text", "kind", "state", "kept_as")} for p in d["probes"]]
        ending = {k: d["ending"][k] for k in ("kind", "stop", "reason")}
        return {
            "trace": trace,
            "git": git,
            "workspace": d["workspace"],
            "services": d["services"],
            "ending": ending,
            "turns": turns,
            "probes": probes,
        }

    assert comparable(saved) == comparable(live)
    assert saved.trace.restored_from_summary is False, "the goldens keep their raw traces"
    assert saved.identity.case_sha256 == live.identity.case_sha256


def test_legacy_restores_from_the_summary_when_the_raw_trace_is_gone(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "pass")
    copy, _ = _saved(item, tmp_path)
    (copy / "stdout.jsonl").unlink()
    found = rescoring.load_evidence(copy, golden_runs.scenario(item))
    assert found.trace.restored_from_summary is True
    assert found.trace.raw_sha256 == {}
    assert found.trace.bash_commands, "the summary restores the calls a check re-measures"


def test_a_written_regrade_carries_the_evidence_it_reconstructed(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "rubric_kept")
    copy, _ = _saved(item, tmp_path)
    before = (copy / "grading.json").read_bytes()
    with contextlib.ExitStack() as stack:
        # The saved judge identity is the generating host's; replay it, as the golden regrade does.
        binding = json.loads((copy / "grading.json").read_text("utf-8"))["judge_binding"]
        stack.enter_context(mock.patch.object(judge, "execution_identity", return_value=binding["execution"]))
        rescoring.regrade_run(copy, golden_runs.scenario(item), write=True, relax_identity=True)
    assert (copy / "grading.json").read_bytes() == before
    assert not (copy / evidence.FILE).exists(), "the live attempt's folder is never rewritten"
    written = evidence.EvidenceV1.model_validate_json((copy / "assessments/1" / evidence.FILE).read_text("utf-8"))
    assert written.written_by == "legacy"
    assert [p.kept_as for p in written.probes] == [checking.LIVE_JUDGE]


def test_a_damaged_invocation_field_does_not_abort_a_written_regrade(tmp_path: Path) -> None:
    """A regrade names damaged invocation evidence itself and stays INCONCLUSIVE; the evidence it
    writes beside that assessment records the damaged field as unknown rather than refusing."""
    item = next(c for c in CASES if c.name == "native_pass")
    copy, _ = _saved(item, tmp_path)
    metadata_path = copy / "followup" / "invocation.json"
    metadata = json.loads(metadata_path.read_text("utf-8"))
    metadata["exit_code"] = "0"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    grading = rescoring.regrade_run(copy, golden_runs.scenario(item), write=True, relax_identity=True)
    assert grading["status"] == "INCONCLUSIVE"
    assert "boundary evidence missing or invalid" in str(grading["inconclusive"])
    assert (copy / "assessments/1/grading.json").is_file()
    written = evidence.EvidenceV1.model_validate_json((copy / "assessments/1" / evidence.FILE).read_text("utf-8"))
    assert [t.exit_code for t in written.turns] == [0, None]


def test_legacy_carries_the_recorded_case_digest_never_the_current_inputs(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "pass")
    copy, found = _saved(item, tmp_path)
    record_path = copy / "record.json"
    record = json.loads(record_path.read_text("utf-8"))
    assert found.identity.case_sha256 == record["case"]["case_sha256"]
    record["case"]["case_sha256"] = "a" * 64
    record_path.write_text(json.dumps(record), encoding="utf-8")
    assert rescoring.load_evidence(copy, golden_runs.scenario(item)).identity.case_sha256 == "a" * 64
    record_path.unlink()
    assert rescoring.load_evidence(copy, golden_runs.scenario(item)).identity.case_sha256 is None


def test_a_saved_run_with_its_own_evidence_is_read_as_written(tmp_path: Path) -> None:
    item = next(c for c in CASES if c.name == "pass")
    run_dir, found, _ = _live(item, tmp_path)
    assert rescoring.load_evidence(run_dir, golden_runs.scenario(item)) == found


def test_host_facts_are_in_their_own_block() -> None:
    """A regrade elsewhere compares the measurement, not the computer: every path, CLI, account and
    judge-execution fact is under `host`, and no other block names one."""
    host = set(evidence.Host.model_fields)
    assert host == {"runtime", "workspace", "plugin_root", "plugin_served_from", "judge_execution", "judge_cache_dir"}
    for name in evidence.Identity.model_fields:
        assert "path" not in name and "root" not in name, name
    assert "execution" not in evidence.Identity.model_fields
