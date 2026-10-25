"""Incident-v1 controls exercise real subprocess CLI resume; no model calls."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
import yaml
from probe import catalog, conversations, fingerprints, rescoring, tracing, trials
from probe_testkit import STUB_RUNTIME, read_json

ROOT = Path(__file__).resolve().parent.parent


def spec(n=6):
    return {
        "id": "incident-session-control",
        "max_turns": 20,
        "agent": "reliability-engineer",
        "tools": ["Skill", "Read", "Task"],
        "expected_model": "stub-model",
        "prompt": "Supplied intake. CHECK protocol is available.",
        "fixture": {"files": {"evidence.md": "Supplied evidence; no future observations."}},
        "followups": [f"Supplied update {i}." for i in range(2, n + 1)],
        "conversation": {
            "profile": "incident-v1",
            "helpers": [None] * n,
            "partition": "development",
            "manual_review": "pending",
        },
    }


def branch():
    return {
        "request_map": [
            {"id": "instances", "requests": ["instances", "show instance health"], "text": "INSTANCE_RELEASE"},
            {
                "id": "dependency",
                "requests": ["dependency latency", "show upstream timing"],
                "text": "DEPENDENCY_SECRET",
            },
        ],
        "unavailable": "Unavailable: choose an accessible check.",
        "ambiguous": "Clarify one check.",
    }


STUB = r"""
import json, sys
from pathlib import Path
args = sys.argv[1:]
def flag(name): return args[args.index(name) + 1]
p = Path.cwd() / "session.json"
state = json.loads(p.read_text()) if p.exists() else {"turn": 0, "session": "same-session"}
i = state["turn"]
assert ("--resume" in args) == (i > 0)
if i: assert flag("--resume") == state["session"]
assert 0 < int(flag("--max-turns")) <= 20 - i * 2
prompt = flag("-p")
mode = Path(__file__).stem
assert "DEPENDENCY_SECRET" not in prompt if mode != "alternative" else ("DEPENDENCY_SECRET" in prompt) == (i == 1)
assert "DEPENDENCY_SECRET" not in (Path.cwd() / "evidence.md").read_text()
sid = "drift" if mode == "drift" and i == 1 else state["session"]
def emit(event): print(json.dumps(event), flush=True)
emit({"type":"system", "subtype":"init", "session_id": sid, "model":"stub-model",
      "tools":["Skill","Read","Task"], "plugins":[{"name":"save-toolkit","path":flag("--plugin-dir")}],"mcp_servers":[]})
if mode == "interrupted" and i == 2: sys.exit(0)
if mode == "wall" and i == 1:
    import time
    time.sleep(2)
response = "CHECK: show instance health" if i == 0 else "unknown remains"
if mode == "bad": response = "unsupported cause"
if mode == "alternative" and i == 0: response = "CHECK: show upstream timing"
if mode == "correction": response = "CHECK: splunk" if i == 0 else "CHECK: instances"
if mode == "unavailable" and i == 0: response = "CHECK: splunk"
if mode == "ambiguous" and i == 0: response = "CHECK: instances\nCHECK: dependency latency"
if mode == "helper" and i == 3:
    emit({"type":"assistant","message":{"model":"stub-model","content":[{"type":"tool_use","id":"child","name":"Task","input":{"subagent_type":"save-toolkit:sre-assistant"}}]}})
    emit({"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"child","content":"supplied observation summarized"}]}})
    emit({"type":"assistant","message":{"model":"stub-model","content":[{"type":"text","text":"I assess the helper evidence."}]}})
state["turn"] += 1
p.write_text(json.dumps(state))
emit({"type":"result","subtype":"success","session_id":sid,"result":response,"num_turns":2,
      "duration_ms":5,"usage":{"input_tokens":5},"modelUsage":{"stub-model":{}},"total_cost_usd": 9 if mode == "spend" else .01})
"""


def run(tmp_path, case, mode="good"):
    stub = tmp_path / f"{mode}.py"
    stub.write_text(STUB)

    @contextlib.contextmanager
    def env():
        yield dict(os.environ)

    summary = trials.run_trial(
        case,
        run_number=1,
        settings=trials.BatchSettings(
            plugin_root=ROOT,
            label=mode,
            model="stub-model",
            out_dir=tmp_path / "runs",
            timeout=1 if mode == "wall" else 10,
            executable=f"{sys.executable} {stub}",
            keep_workspace=False,
            env_factory=env,
            runtime=STUB_RUNTIME,
        ),
    )
    return summary, tmp_path / f"runs/eval-{case['id']}/{mode}/run-1"


def test_opt_in_preserves_legacy_and_rejects_malformed():
    case = spec()
    assert catalog.validate_scenario(case) == []
    legacy = copy.deepcopy(case)
    del legacy["conversation"]
    legacy["helper"] = "sre-assistant"
    assert any("exactly one" in p for p in catalog.validate_scenario(legacy))
    for change in ({"helpers": [None]}, {"profile": "incident-v2"}, {"partition": "other"}):
        bad = copy.deepcopy(case)
        bad["conversation"].update(change)
        assert catalog.validate_scenario(bad)


@pytest.mark.parametrize(
    "answer,selected",
    [
        ("CHECK: instances", "instances"),
        ("Advice.\nCHECK: show instance health", "instances"),
        ("CHECK: show upstream timing", "dependency"),
        ("CHECK: splunk", "unavailable"),
        ("CHECK: instances\nCHECK: dependency latency", "ambiguous"),
        ("maybe check something", "ambiguous"),
    ],
)
def test_frozen_branch_aliases_and_no_invented_observation(answer, selected):
    release = conversations.resolve(branch(), answer)
    assert release["selected"] == selected
    if selected != "dependency":
        assert "DEPENDENCY_SECRET" not in release["text"]


def test_real_subprocess_six_resume_and_regrade_parity(tmp_path):
    case = spec()
    case["followups"][0] = branch()
    summary, folder = run(tmp_path, case)
    assert summary["status"] == "PASS"
    folders = conversations.folders(folder, case)
    assert len(folders) == 6 and len(set(folders)) == 6
    assert tracing.parse_trial_trace(folder).num_turns == 12
    for i, turn in enumerate(folders):
        meta = read_json(turn / "invocation.json")
        assert ("--resume" in meta["argv"]) == (i > 0)
        assert meta["argv"][meta["argv"].index("--max-turns") + 1] == str(20 - 2 * i)
        context = read_json(turn / "judge-context.json")
        assert len(context["messages"]) == 2 * i + 1
        assert "DEPENDENCY_SECRET" not in json.dumps(context)
        assert "Supplied update 6" not in json.dumps(context) if i < 5 else True
    assert rescoring.regrade_run(folder, case)["status"] == "PASS"
    evidence = read_json(folder / "record.json")["evidence"]
    assert "invocations/006/input.md" in evidence
    assert "invocations/006/judge-context.json" in evidence
    assert read_json(folder / "outputs/trace-summary.json")["semantic_assessment"] == "UNVERIFIED"


@pytest.mark.parametrize(
    "mode,expected,count",
    [
        ("drift", "INCONCLUSIVE", 2),
        ("interrupted", "INCONCLUSIVE", 3),
        ("spend", "INCONCLUSIVE", 1),
        ("wall", "INCONCLUSIVE", 2),
        ("good", "FAIL", 2),
    ],
)
def test_stop_and_budget_controls(tmp_path, mode, expected, count):
    case = spec()
    if mode == "good":
        case["max_turns"] = 4
    summary, folder = run(tmp_path, case, mode)
    assert summary["status"] == expected
    assert len([p for p in conversations.folders(folder, case) if (p / "invocation.json").exists()]) == count
    assert rescoring.regrade_run(folder, case)["status"] == expected


def test_turn_four_actual_helper_events_are_required(tmp_path):
    case = spec()
    case["conversation"]["helpers"][3] = "sre-assistant"
    summary, folder = run(tmp_path, case, "helper")
    assert summary["status"] == "PASS"
    assert rescoring.regrade_run(folder, case)["status"] == "PASS"


@pytest.mark.parametrize("mode,selected", [("unavailable", "unavailable"), ("ambiguous", "ambiguous")])
def test_unavailable_and_ambiguous_branch_is_persisted(tmp_path, mode, selected):
    case = spec(2)
    case["followups"][0] = branch()
    summary, folder = run(tmp_path, case, mode)
    assert summary["status"] == "PASS"
    release = read_json(conversations.folders(folder, case)[1] / "release.json")
    assert release["selected"] == selected


def test_per_turn_grader_controls_and_tamper_refusal(tmp_path):
    case = spec(2)
    case["conversation"]["turn_graders"] = [[{"type": "contains_any", "of": ["CHECK:"]}], []]
    summary, folder = run(tmp_path, case)
    assert summary["status"] == "PASS"
    assert rescoring.regrade_run(folder, case)["status"] == "PASS"
    (folder / "input.md").write_text("changed input")
    assert rescoring.regrade_run(folder, case)["status"] == "INCONCLUSIVE"
    bad, bad_folder = run(tmp_path, case, "bad")
    assert bad["status"] == "FAIL"
    assert rescoring.regrade_run(bad_folder, case)["status"] == "FAIL"


def test_alternative_useful_branch_and_correction_are_supported(tmp_path):
    alternative = spec(2)
    alternative["followups"][0] = branch()
    summary, folder = run(tmp_path, alternative, "alternative")
    assert summary["status"] == "PASS"
    turn = conversations.folders(folder, alternative)[1]
    assert "DEPENDENCY_SECRET" in (turn / "input.md").read_text()
    assert "INSTANCE_RELEASE" not in (turn / "judge-context.json").read_text()
    assert rescoring.regrade_run(folder, alternative)["status"] == "PASS"
    correction = spec(3)
    correction["followups"] = [branch(), branch()]
    summary, folder = run(tmp_path, correction, "correction")
    assert summary["status"] == "PASS"
    turns = conversations.folders(folder, correction)
    assert read_json(turns[1] / "release.json")["selected"] == "unavailable"
    assert read_json(turns[2] / "release.json")["selected"] == "instances"
    assert rescoring.regrade_run(folder, correction)["status"] == "PASS"


def test_authored_manifest_partition_and_hidden_review_are_bound():
    base = ROOT / "evals/incident-conversations"
    manifest = read_json(base / "manifest.json")
    assert len(manifest["profiles"]) == 18
    assert manifest["held_out_families"] == ["INC-05", "INC-06"]
    selected = {item["instance_id"]: item for item in read_json(base / "report-selection.json")["tasks"]}
    for entry in manifest["reviews"]:
        assert hashlib.sha256((base / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
    for entry in manifest["profiles"]:
        path = base / entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        case = yaml.safe_load(path.read_text())
        assert catalog.validate_scenario(case) == []
        assert selected[case["id"]]["case_sha256"] == fingerprints.case_digest(case)
        fixture = json.dumps(case["fixture"])
        assert "review/" not in fixture and "pair_delta" not in fixture
        assert case["conversation"]["manual_review"] == "pending"
        if "incident_case" in case:
            family = case["incident_case"]["family"]
            review = next(item for item in manifest["reviews"] if item["family"] == family)
            assert case["incident_case"]["review_sha256"] == review["sha256"]
            assert case["conversation"]["partition"] == (
                "held-out" if family in manifest["held_out_families"] else "development"
            )


@pytest.mark.parametrize("mutation", ["resume", "budget", "release", "judge", "trace", "response", "extra"])
def test_saved_evidence_mutations_cannot_regrade_as_pass(tmp_path, mutation):
    case = spec(2)
    case["followups"][0] = branch()
    _, folder = run(tmp_path, case)
    later = conversations.folders(folder, case)[1]
    if mutation in ("resume", "budget"):
        path = later / "invocation.json"
        metadata = read_json(path)
        flag = "--resume" if mutation == "resume" else "--max-turns"
        metadata["argv"][metadata["argv"].index(flag) + 1] = "other" if mutation == "resume" else "999"
        path.write_text(json.dumps(metadata))
    elif mutation == "release":
        path = later / "release.json"
        receipt = read_json(path)
        receipt["selected"] = "dependency"
        path.write_text(json.dumps(receipt))
    elif mutation == "judge":
        path = folder / "judge-context.json"
        context = read_json(path)
        context["messages"].append({"role": "user", "content": "DEPENDENCY_SECRET"})
        path.write_text(json.dumps(context))
    elif mutation == "trace":
        (later / "stdout.jsonl").unlink()
    elif mutation == "response":
        (later / "response.md").write_text("changed response")
    else:
        (folder / "invocations/999").mkdir()
    assert rescoring.regrade_run(folder, case)["status"] == "INCONCLUSIVE"


def test_saved_rescore_preserves_original_and_compares_identically(tmp_path):
    case = spec(2)
    _, folder = run(tmp_path, case)
    original = (folder / "grading.json").read_bytes()
    first = rescoring.rescore(tmp_path / "runs", [case], tmp_path / "rescore-a")
    second = rescoring.rescore(tmp_path / "runs", [case], tmp_path / "rescore-b")
    assert len(first["runs"]) == 1
    assert first["runs"][0]["saved"]["status"] == first["runs"][0]["rescored"]["status"] == "PASS"
    assert rescoring.rescore_diff(first, second) == []
    assert (folder / "grading.json").read_bytes() == original


def test_future_authored_observation_changes_case_fingerprint():
    case = spec(2)
    case["followups"][0] = branch()
    before = fingerprints.case_digest(case)
    case["followups"][0]["request_map"][1]["text"] = "changed unchosen evidence"
    assert fingerprints.case_digest(case) != before
