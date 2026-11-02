"""Offline contracts for the Inspect orchestration of native scenarios; no model and no Claude CLI.

The trial is faked where the native batch's own tests fake it, `probe.trials.run_trial`, and the
native preflight is scripted, so the suite runs on any account. Live parity with `build_probe.py run`
is the separate run plan, not these tests.
"""

import json
from pathlib import Path

import clean_room
import inspect_fleet
import pytest
from inspect_ai import eval as inspect_eval
from probe import batches as probe_batches
from probe import catalog as probe_catalog
from probe import cli as probe_cli
from probe import trials as probe_trials
from probe.exits import ExitCode

PROVENANCE = {"plugin_root": "/plugin", "plugin_commit": "c" * 40, "plugin_inputs_dirty": False,
              "plugin_source_sha256": "f" * 64}
RUNTIME = {"cli_version": "1.0.0", "host_platform": {"system": "Linux", "release": "x", "machine": "x86_64"},
           "host_identity": {"hostname": "h", "account_id": "1000", "elevated": False,
                             "identity_source": "posix_effective_uid"}}


@pytest.fixture
def preflight(monkeypatch):
    """The native preflight, scripted to accept; it is patched where it is defined."""
    seen = []

    def accept(args, chosen):
        seen.append((args, [spec["id"] for spec in chosen]))
        return None, dict(PROVENANCE), dict(RUNTIME)

    monkeypatch.setattr(probe_cli, "_preflight", accept)
    return seen


def by_kind():
    kinds = {}
    for spec in probe_catalog.load_all_scenarios():
        kinds.setdefault(probe_catalog.scenario_kind(spec), []).append(spec["id"])
    return kinds


def test_all_means_every_routing_and_contract_scenario_and_nothing_else(preflight, tmp_path):
    kinds = by_kind()
    task = inspect_fleet.native_scenarios(label="l", out=str(tmp_path / "it"))
    ids = sorted(sample.id for sample in task.dataset)
    assert ids == sorted(kinds["routing"] + kinds["contract"])
    assert task.epochs == 1 and task.metadata["label"] == "l"
    assert sorted(preflight[0][1]) == ids, "the native preflight sees exactly the scenarios that will run"
    sample = next(sample for sample in task.dataset if sample.id == ids[0])
    assert sample.metadata["kind"] in {"routing", "contract"} and len(sample.metadata["case_sha256"]) == 64


def test_an_explicit_build_or_conversation_selection_is_refused(preflight, tmp_path):
    kinds = by_kind()
    for kind in ("build", "native"):
        with pytest.raises(ValueError, match=r"build_probe\.py"):
            inspect_fleet.native_scenarios(label="l", out=str(tmp_path), scenario=kinds[kind][0])
    with pytest.raises(ValueError, match="no scenario named"):
        inspect_fleet.native_scenarios(label="l", out=str(tmp_path), scenario="no-such-scenario")


def test_label_and_out_are_required_like_the_native_run(preflight, tmp_path):
    with pytest.raises(ValueError, match=r"-T label=.* -T out="):
        inspect_fleet.native_scenarios(out=str(tmp_path))
    with pytest.raises(ValueError, match=r"-T label=.* -T out="):
        inspect_fleet.native_scenarios(label="l")


def test_a_native_preflight_refusal_refuses_the_task(monkeypatch, tmp_path):
    monkeypatch.setattr(probe_cli, "_preflight", lambda args, chosen: ExitCode.REFUSED)
    with pytest.raises(ValueError, match="native preflight refused"):
        inspect_fleet.native_scenarios(label="l", out=str(tmp_path))


def test_rows_that_cannot_pool_with_the_batch_are_refused(preflight, monkeypatch, tmp_path):
    out = tmp_path / "it"
    out.mkdir()
    (out / "summary-l-default.json").write_text(json.dumps([{"scenario": "x", "label": "l", "run": 1}]))
    monkeypatch.setattr(probe_batches, "batch_identity_problem", lambda *args: "mixed resolved model identities")
    with pytest.raises(ValueError, match=r"cannot pool.*mixed resolved model identities"):
        inspect_fleet.native_scenarios(label="l", out=str(out))


def scripted_trial(calls, statuses):
    """A fake `run_trial` returning a native summary whose status follows the scenario's script."""

    def run_trial(spec, *, run_number, settings):
        calls.append((spec["id"], run_number, settings))
        status = statuses.get(spec["id"], ["PASS"])[(run_number - 1) % len(statuses.get(spec["id"], ["PASS"]))]
        passed = 1 if status == "PASS" else 0
        return {"scenario": spec["id"], "label": settings.label, "run": run_number, "status": status,
                "passed": passed, "total": 1, "models": ["claude-sonnet-5-5"], "seconds": 1.5,
                "known_cost_usd": 0.01, "cost_complete": True, "plugin_source_sha256": "f" * 64,
                "runner_source_sha256": "a" * 64, "scenario_sha256": "b" * 64,
                **({"grader_error": "judge down"} if status == "INCONCLUSIVE" else {})}

    return run_trial


def test_each_sample_runs_once_per_epoch_through_the_native_trial(preflight, monkeypatch, tmp_path):
    calls = []
    out = tmp_path / "it"
    task = inspect_fleet.native_scenarios(label="cand", out=str(out), claude_model="sonnet", trials=2,
                                          timeout=120, executable="claude-test")
    first, second = (sample.id for sample in task.dataset[:2])
    scripts = {first: ["PASS", "FAIL"], second: ["INCONCLUSIVE"]}
    monkeypatch.setattr(probe_trials, "run_trial", scripted_trial(calls, scripts))

    logs = inspect_eval(task, model="none", limit=2, log_dir=str(tmp_path / "logs"), display="none", max_samples=2)

    assert logs[0].status == "success", logs[0].error
    assert sorted((scenario, run) for scenario, run, _ in calls) == [(first, 1), (first, 2), (second, 1), (second, 2)]
    settings = calls[0][2]
    assert isinstance(settings, probe_trials.BatchSettings)
    assert (settings.label, settings.model, settings.timeout, settings.executable) == ("cand", "sonnet", 120, "claude-test")
    assert settings.out_dir == out.resolve() and settings.expected_plugin_digest == PROVENANCE["plugin_source_sha256"]
    assert settings.runtime == RUNTIME and settings.judge_binding is None
    scores = {(sample.id, sample.epoch): sample.scores["native_verdict"] for sample in logs[0].samples}
    assert scores[(first, 1)].value == "C" and scores[(first, 1)].answer == "PASS"
    assert scores[(first, 2)].value == "I" and scores[(first, 2)].answer == "FAIL"
    assert scores[(second, 1)].value == "N" and scores[(second, 1)].explanation == "judge down"
    assert scores[(first, 1)].metadata["known_cost_usd"] == 0.01 and scores[(first, 1)].metadata["run"] == 1
    rows = json.loads((out / "summary-cand-sonnet.json").read_text(encoding="utf-8"))
    assert sorted((row["scenario"], row["run"], row["status"]) for row in rows) == [
        (first, 1, "PASS"), (first, 2, "FAIL"), (second, 1, "INCONCLUSIVE"), (second, 2, "INCONCLUSIVE")]
    assert list((tmp_path / "logs").glob("*.eval"))
    assert logs[0].eval.metadata["plugin"] == PROVENANCE and logs[0].eval.metadata["claude_model"] == "sonnet"


def test_run_offset_appends_slots_like_the_native_run(preflight, monkeypatch, tmp_path):
    calls = []
    task = inspect_fleet.native_scenarios(label="l", out=str(tmp_path / "it"), trials=1, run_offset=2)
    monkeypatch.setattr(probe_trials, "run_trial", scripted_trial(calls, {}))
    logs = inspect_eval(task, model="none", limit=1, log_dir=str(tmp_path / "logs"), display="none")
    assert logs[0].status == "success"
    assert [run for _, run, _ in calls] == [3]


def test_lost_authentication_ends_the_eval_as_an_error(preflight, monkeypatch, tmp_path):
    def refuse(spec, *, run_number, settings):
        raise clean_room.AuthUnavailable("Not logged in")

    task = inspect_fleet.native_scenarios(label="l", out=str(tmp_path / "it"))
    monkeypatch.setattr(probe_trials, "run_trial", refuse)
    logs = inspect_eval(task, model="none", limit=1, log_dir=str(tmp_path / "logs"), display="none")
    assert logs[0].status == "error"
    assert "Not logged in" in str(logs[0].error)


def test_the_runner_is_registered_for_discovery():
    root = Path(__file__).resolve().parents[1]
    tracks = json.loads((root / "evals/tracks.json").read_text(encoding="utf-8"))["tracks"]
    track = next(track for track in tracks if track["id"] == "inspect-native")
    assert track["entrypoints"] == ["evals/inspect_fleet.py"] and "inspect" in track["suites"]
    suite = json.loads((root / "evals/suites/inspect.json").read_text(encoding="utf-8"))
    assert "evals/test_inspect_fleet.py" in suite["tests"]
