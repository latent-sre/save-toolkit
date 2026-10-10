"""Runtime identity admission and historical comparison without any model calls."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from unittest import mock

import compare_runs
import pytest
from probe import batches, catalog, cli, fingerprints, records, trials
from probe_testkit import tiny_spec

RUNTIME = {
    "cli_version": "1.0 (synthetic)",
    "host_platform": {"system": "Linux", "release": "synthetic", "machine": "x86_64"},
    "host_identity": {"hostname": "synthetic-host", "account_id": "uid:1001", "elevated": False,
                      "identity_source": "posix_effective_uid"},
}


def runtime_with(problem: str) -> dict:
    runtime = copy.deepcopy(RUNTIME)
    if problem == "legacy":
        runtime.pop("host_identity")
    elif problem == "cli":
        runtime["cli_version"] = None
    elif problem == "platform":
        runtime["host_platform"] = {}
    elif problem == "elevated":
        runtime["host_identity"]["elevated"] = True
    elif problem == "privilege-unknown":
        runtime["host_identity"]["elevated"] = None
    elif problem == "reported-problem":
        runtime["host_identity"]["problem"] = "token lookup unavailable"
    elif problem == "bad-source":
        runtime["host_identity"]["identity_source"] = "environment"
    else:
        runtime["host_identity"][problem] = None
    return runtime


@pytest.mark.parametrize("problem", ["legacy", "cli", "platform", "hostname", "account_id", "elevated",
                                    "identity_source", "reported-problem", "bad-source", "privilege-unknown"])
def test_live_batch_refuses_unverified_or_elevated_runtime_before_spending(tmp_path: Path, problem: str) -> None:
    runtime = runtime_with(problem)
    with (mock.patch.object(catalog, "load_all_scenarios", return_value=[tiny_spec()]),
          mock.patch.object(fingerprints, "plugin_provenance", return_value={"plugin_source_sha256": "a" * 64}),
          mock.patch.object(fingerprints, "runtime_identity", return_value=runtime),
          mock.patch.object(trials, "run_trial", side_effect=AssertionError("unverified runtime reached a trial")) as trial):
        assert cli.main(["run", "--label", "test", "--out", str(tmp_path / "runs")]) == 3
    trial.assert_not_called()
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("problem", ["legacy", "hostname", "account_id", "identity_source", "reported-problem", "bad-source", "privilege-unknown"])
def test_historical_identity_gaps_never_pool_or_imply_matching_hosts(problem: str) -> None:
    runtime = runtime_with(problem)
    entry = {"models": ["model"], "plugin_source_sha256": "a" * 64, "scenario_sha256": "b" * 64, "runtime": runtime}
    conditions = {**entry, "observed_models": entry["models"]}
    assert batches.pool_identity(entry) is None
    reason = compare_runs._identity_gap(conditions)
    assert reason and "host" in reason


@pytest.mark.parametrize("field,changed", [("hostname", "another-host"), ("account_id", "uid:1002"), ("elevated", True)])
def test_known_different_runtime_identities_never_pool(field: str, changed: object) -> None:
    original = {"models": ["model"], "plugin_source_sha256": "a" * 64, "scenario_sha256": "b" * 64,
                "runtime": copy.deepcopy(RUNTIME)}
    other = copy.deepcopy(original)
    other["runtime"]["host_identity"][field] = changed
    assert batches.pool_identity(original) is not None
    assert batches.pool_identity(other) is not None, "historical observed elevation is evidence, not a new live admission"
    assert batches.pool_identity(original) != batches.pool_identity(other)


def test_legacy_runtime_stays_readable_without_fabricated_account_evidence() -> None:
    runtime = {key: value for key, value in RUNTIME.items() if key != "host_identity"}
    parsed = records.Runtime.model_validate_json(json.dumps(runtime))
    assert parsed.host_identity is None
    assert parsed.model_dump(mode="json", exclude_unset=True) == runtime


def test_complete_unelevated_identity_admits_a_new_batch(tmp_path: Path) -> None:
    args = cli._command_parser().parse_args(["run", "--label", "test", "--out", str(tmp_path / "runs")])
    with (mock.patch.object(fingerprints, "plugin_provenance", return_value={"plugin_source_sha256": "a" * 64}),
          mock.patch.object(fingerprints, "runtime_identity", return_value=RUNTIME)):
        result = cli._preflight(args, [tiny_spec()])
    assert isinstance(result, tuple)
    assert result[2] == RUNTIME


@pytest.mark.parametrize("change", ["legacy", "unknown", "different-account", "different-privilege"])
def test_comparison_preserves_historical_verdicts_and_reports_identity_gaps(tmp_path: Path, change: str) -> None:
    bundle = Path(__file__).parent / "fixtures/v1-bundle"
    case = "synthetic-gain"
    shutil.copytree(bundle / "runs" / f"eval-{case}", tmp_path / f"eval-{case}")
    for label in ("incumbent", "candidate"):
        path = tmp_path / f"eval-{case}" / label / "run-1/record.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        runtime = record["conditions"]["runtime"]
        if change == "legacy":
            runtime.pop("host_identity")
        elif change == "unknown":
            runtime["host_identity"]["account_id"] = None
        elif label == "candidate":
            runtime["host_identity"]["account_id" if change == "different-account" else "elevated"] = (
                "uid:2002" if change == "different-account" else True
            )
        path.write_text(json.dumps(record), encoding="utf-8")
    spec = catalog.load_scenario(bundle / "scenarios" / f"{case}.yaml")
    report = compare_runs.compare_bundle(tmp_path, "incumbent", "candidate", [spec])
    pair = report["cases"][0]
    assert pair["incumbent"]["trials"][0]["status"] == "FAIL"
    assert pair["candidate"]["trials"][0]["status"] == "PASS"
    if change in ("legacy", "unknown"):
        assert pair["outcome"] == "unmeasured"
        assert "host/account/elevation evidence" in pair["candidate"]["reason"]
        assert pair["candidate"]["verdict"] == "INCONCLUSIVE"
        identity = pair["candidate"]["conditions"]["runtime"]["host_identity"]
        assert identity is None if change == "legacy" else identity["account_id"] is None
    else:
        assert (pair["outcome"], pair["reason"]) == ("not_compared", "the arms differ in runtime")
