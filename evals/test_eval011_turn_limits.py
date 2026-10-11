"""Every admitted scenario declares a bounded CLI turn budget; checks spend no model calls."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest
import turn_counts
from probe import catalog, cli, fingerprints, invocation, tracing, trials
from probe_testkit import ROOT, tiny_spec


@pytest.mark.parametrize("value", [None, True, False, 0, -1, 501, 2.5, "12", [], {}])
def test_cli_refuses_missing_or_invalid_turn_limit_before_any_call(tmp_path: Path, value: object) -> None:
    spec = tiny_spec(max_turns=value)
    if value is None:
        spec.pop("max_turns")
    (tmp_path / "tiny.yaml").write_text(json.dumps(spec), encoding="utf-8")
    with (mock.patch.object(catalog, "SCENARIO_DIR", tmp_path),
          mock.patch.object(catalog, "CONTRACT_SCENARIO_DIR", tmp_path / "absent"),
          mock.patch.object(cli, "_preflight", side_effect=AssertionError("budget validation must precede preflight")),
          mock.patch.object(fingerprints, "runtime_identity") as runtime,
          mock.patch.object(trials, "run_trial") as model):
        assert cli.main(["run", "--scenario", "tiny", "--label", "test", "--out", str(tmp_path / "out")]) == 3
    runtime.assert_not_called()
    model.assert_not_called()
    assert not (tmp_path / "out").exists()


def test_every_active_scenario_declares_the_cli_budget_and_preserves_approved_values() -> None:
    approved = {
        "build-operator-cli-safe-requeue": 40,
        "build-repository-investigator-denied-shell-canary": 15,
        "build-sre-assistant-active-incident-guarded-triage": 42,
        "build-sre-assistant-guard-denies-script-canary": 15,
        "discovery-principal-engineer-platform-selection": 13,
        "native-incident-helper-return-and-resume": 17,
        "native-reliability-helper-return-and-resume": 18,
        # The owner's WP-10 limits of 2026-10-10: sre-assistant 42, software-engineer 64, investigator 16.
        **{f"build-injection-{family}-{arm}": 42 for family in ("log", "log-role", "helper", "helper-relayed-owner")
           for arm in ("benign", "malicious")},
        **{f"build-natural-injection-log-{arm}": 42 for arm in ("benign", "malicious")},
        **{f"build-injection-{family}-{arm}": 64 for family in ("repository", "repository-policy")
           for arm in ("benign", "malicious")},
        **{f"build-natural-injection-{family}-{arm}": 64 for family in ("repository", "helper")
           for arm in ("benign", "malicious")},
        **{f"build-repository-investigator-{case}": 16 for case in ("source", "missing-runtime")},
        # Owner, 2026-10-10: the closest saved analog (two skills, one document) ran 25 turns, above #348's 22.
        "build-reliability-engineer-proportionate-options": 40,
    }
    specs = catalog.load_all_scenarios()
    assert len(specs) >= 242
    for spec in specs:
        limit = spec["max_turns"]
        assert type(limit) is int and 1 <= limit <= 500, spec["id"]
        command = invocation.build_command("unused-claude", ROOT, catalog.agent_pin(spec), "p", None,
                                             catalog.scenario_tools(spec), max_turns=limit)
        assert command.count("--max-turns") == 1
        assert command[command.index("--max-turns") + 1] == str(limit)
        assert invocation.reached_turn_limit(tracing.TraceSummary(result_subtype="error_max_turns"), spec)
        if spec["id"] in approved:
            assert limit == approved[spec["id"]]


@pytest.mark.parametrize(("timing", "expected"), [
    ({"trial_duration_seconds": 20, "total_duration_seconds": 30}, 20),
    ({"total_duration_seconds": 435.2}, 435.2),
    ({"trial_duration_seconds": None, "total_duration_seconds": 40}, 40),
    ({"trial_duration_seconds": -1}, None),
    ({"trial_duration_seconds": True}, None),
    ({"trial_duration_seconds": float("nan")}, None),
    ({"trial_duration_seconds": float("inf")}, None),
])
def test_turn_counts_reads_valid_current_or_legacy_elapsed_evidence(tmp_path: Path, timing: dict, expected: float | None) -> None:
    path = tmp_path / "iteration/eval-example/arm/run-1/timing.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"num_turns": 60, **timing}), encoding="utf-8")
    observed = turn_counts.collect(tmp_path, {"example"})["example"]
    assert observed.turns == [60]
    assert observed.longest_seconds == expected
