"""A native selection binds finalized cases and a bounded window before any live effects."""

from __future__ import annotations

import copy
import hashlib
import importlib
import json

import pytest
from probe import catalog, cli, fingerprints
from probe.exits import ExitCode


@pytest.fixture
def snapshot(tmp_path):
    spec = next(s for s in catalog.load_all_scenarios() if s["id"] == "build-python-package-refactor")
    data = {"schema_version": 1, "profile": "native-selection-v1", "trials": 3,
            "tasks": [{"instance_id": spec["id"], "case_sha256": fingerprints.case_digest(spec)}],
            "source": {"git_revision": None, "dirty": None, "suites": []}}
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path, spec, data


def test_validate_admits_a_frozen_selection_without_live_preflight(snapshot, monkeypatch, capsys):
    path, _, _ = snapshot
    monkeypatch.setattr(cli, "_preflight", lambda *_: pytest.fail("offline validation reached preflight"))
    assert cli.main(["validate", "--selection", str(path)]) == 0
    assert "1 spec(s)" in capsys.readouterr().out


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(schema_version=True), lambda d: d.update(schema_version=2),
    lambda d: d.update(profile="foreign"), lambda d: d.update(extra=True),
    lambda d: d.update(trials=True), lambda d: d.update(trials=0), lambda d: d.update(trials=10001),
    lambda d: d.update(tasks=[]), lambda d: d["tasks"].append(copy.deepcopy(d["tasks"][0])),
    lambda d: d["tasks"][0].update(case_sha256="0" * 64),
    lambda d: d["tasks"][0].update(instance_id="missing"),
    lambda d: d["tasks"][0].update(instance_id="../outside"),
    lambda d: d["source"].update(dirty="false"),
])
def test_invalid_snapshot_is_refused_before_preflight_or_output(snapshot, monkeypatch, tmp_path, mutation):
    path, _, data = snapshot
    mutation(data)
    path.write_text(json.dumps(data))
    monkeypatch.setattr(cli, "_preflight", lambda *_: pytest.fail("invalid selection reached preflight"))
    output = tmp_path / "runs"
    assert cli.main(["run", "--selection", str(path), "--label", "test", "--out", str(output)]) == 3
    assert not output.exists()


def test_duplicate_keys_and_changed_definitions_are_refused(snapshot, monkeypatch):
    path, spec, _ = snapshot
    path.write_text(path.read_text().replace('"trials": 3', '"trials": 3, "trials": 3'))
    assert cli.main(["validate", "--selection", str(path)]) == 3
    path.write_text(path.read_text().replace('"trials": 3, "trials": 3', '"trials": 3'))
    changed = copy.deepcopy(spec)
    changed["prompt"] += " changed"
    monkeypatch.setattr(catalog, "load_all_scenarios", lambda: [changed])
    assert cli.main(["validate", "--selection", str(path)]) == 3


@pytest.mark.parametrize("arguments, expected", [
    ([], (0, 3)), (["--run-offset", "1"], (1, 2)),
    (["--run-offset", "1", "--trials", "1"], (1, 1)), (["--trials=2"], (0, 2)),
    (["--trial=2"], (0, 2)),
])
def test_selection_trial_window_uses_snapshot_total(snapshot, monkeypatch, tmp_path, arguments, expected):
    path, spec, _ = snapshot
    observed = []
    def receive(args, specs):
        observed.append((args.run_offset, args.trials, [s["id"] for s in specs]))
        return 0
    monkeypatch.setattr(cli, "run", receive)
    assert cli.main(["run", "--selection", str(path), "--label", "test", "--out", str(tmp_path), *arguments]) == 0
    assert observed == [(*expected, [spec["id"]])]


@pytest.mark.parametrize("arguments", [["--run-offset", "3"], ["--trials", "4"],
                                     ["--run-offset", "2", "--trials", "2"]])
def test_trial_window_cannot_expand_snapshot(snapshot, monkeypatch, tmp_path, arguments):
    path, _, _ = snapshot
    monkeypatch.setattr(cli, "run", lambda *_: pytest.fail("invalid window reached runner"))
    assert cli.main(["run", "--selection", str(path), "--label", "test", "--out", str(tmp_path), *arguments]) == 3


def test_explicit_scenario_conflicts_and_saved_run_interfaces_remain_unchanged(snapshot):
    path, _, _ = snapshot
    for args in (["validate", "--selection", str(path), "--scenario", "all"],
                 ["regrade", "saved", "--selection", str(path)],
                 ["--validate", "--selection", str(path)]):
        with pytest.raises(SystemExit) as error:
            cli.main(args)
        assert error.value.code == 3


def test_retention_preserves_file_bytes_separate_from_logical_report_hash(snapshot, tmp_path):
    selection = importlib.import_module("probe.selection")
    path, spec, data = snapshot
    admitted = selection.load(path, [spec])
    destination = selection.retain(tmp_path / "runs", admitted)
    assert destination.read_bytes() == path.read_bytes()
    assert destination.name == hashlib.sha256(path.read_bytes()).hexdigest() + ".json"
    assert selection.retain(tmp_path / "runs", admitted) == destination
    logical = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    assert destination.stem != logical
    destination.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="retained"):
        selection.retain(tmp_path / "runs", admitted)


def test_failed_preflight_does_not_retain_selection(snapshot, monkeypatch, tmp_path):
    path, _, _ = snapshot
    monkeypatch.setattr(cli, "_preflight", lambda *_: ExitCode.REFUSED)
    output = tmp_path / "runs"
    assert cli.main(["run", "--selection", str(path), "--label", "test", "--out", str(output)]) == 3
    assert not output.exists()


def test_retention_failure_stops_before_any_trial(snapshot, monkeypatch, tmp_path):
    path, _, _ = snapshot
    output = tmp_path / "runs"
    output.mkdir()
    (output / "selections").write_text("a file blocks publication")
    monkeypatch.setattr(cli, "_preflight", lambda *_: (None, {}, {}))
    monkeypatch.setattr(cli.trials, "run_trial", lambda *_args, **_kwargs: pytest.fail("trial reached"))
    assert cli.main(["run", "--selection", str(path), "--label", "test", "--out", str(output)]) == 3
    assert not list(output.glob("eval-*"))


def test_legacy_default_remains_one_trial_and_all_scenarios(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(cli, "run", lambda args, specs: seen.append((args.trials, args.scenario, len(specs))) or 0)
    assert cli.main(["run", "--label", "old", "--out", str(tmp_path)]) == 0
    assert seen == [(1, "all", len(catalog.load_all_scenarios()))]
