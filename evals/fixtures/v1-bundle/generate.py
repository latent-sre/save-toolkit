"""Write the synthetic v1 bundle that EVAL-012 WP-01's comparison tests read (evals/test_comparison.py).

Run from anywhere: `python evals/fixtures/v1-bundle/generate.py`. It rewrites `runs/` and `scenarios/`;
then refresh `expected-report.json` with `compare_runs.py ... --json` and review the diff. Valid
records pass through `RecordV1`, so they are valid by construction; the unusable ones are cut afterwards.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "evals"))

from probe import catalog, fingerprints  # noqa: E402
from probe.records import RecordV1  # noqa: E402

OUT = REPO / "evals" / "fixtures" / "v1-bundle"
SCENARIOS = OUT / "scenarios"
RUNS = OUT / "runs"
SCENARIO_SHA = "d" * 64
ARMS = {
    "incumbent": {"plugin_source_sha256": "a" * 64, "plugin_commit": "1" * 40},
    "candidate": {"plugin_source_sha256": "b" * 64, "plugin_commit": "2" * 40},
    # One label is one measurement, so a candidate measured on another CLI or model is its own label.
    "candidate-cli": {"plugin_source_sha256": "b" * 64, "plugin_commit": "2" * 40},
    "candidate-nocli": {"plugin_source_sha256": "b" * 64, "plugin_commit": "2" * 40},
    "candidate-opus": {"plugin_source_sha256": "b" * 64, "plugin_commit": "2" * 40},
}
RUNTIME = {"cli_version": "0.0.0 (synthetic)",
           "host_platform": {"system": "Linux", "release": "synthetic", "machine": "x86_64"},
           "host_identity": {"hostname": "synthetic-host", "account_id": "uid:1001", "elevated": False,
                             "identity_source": "posix_effective_uid"}}

CASES = {
    "synthetic-gain": {},
    "synthetic-regression": {},
    "synthetic-unchanged": {},
    "synthetic-threshold": {"threshold": 0.66},
    "synthetic-unmeasured": {},
    "synthetic-attempts": {},
    "synthetic-missing": {},
    "synthetic-legacy": {},
    "synthetic-case-changed": {},
    "synthetic-conditions": {},
    "synthetic-unusable": {},
    "synthetic-recordless": {},
    "synthetic-stopped-early": {},
    "synthetic-unpublished": {},
    "synthetic-identity-gap": {},
    "synthetic-mixed-trials": {},
    "synthetic-regraded": {},
    "synthetic-model": {},
    "synthetic-runner": {},
    "synthetic-misfiled": {},
    "synthetic-refused": {},
    "synthetic-wall-clock": {},
    "synthetic-unpublished-slot": {},
    "synthetic-turn-limit": {},
}


def cost_block(trial_usd: float, judge_usd: float = 0.0, *, judge_live_calls: int = 0,
               judge_cached_calls: int = 0) -> dict:
    """A complete cost, totalled as the runner records one: known_usd rounds trial plus judge spend
    (probe.records.trial_cost) and judge_calls counts live and cached calls (judge_spend)."""
    return {"trial_usd": trial_usd, "judge_usd": judge_usd, "known_usd": round(trial_usd + judge_usd, 6),
            "complete": True, "judge_calls": judge_live_calls + judge_cached_calls,
            "judge_live_calls": judge_live_calls, "judge_cached_calls": judge_cached_calls,
            "judge_unknown_cost_calls": 0}


def unknown_cost() -> dict:
    """An attempt that ended before reporting any part of its cost."""
    return dict.fromkeys(cost_block(0.0), None)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def scenario(case_id: str, extra: dict) -> dict:
    lines = [
        f"id: {case_id}",
        "max_turns: 20",
        "prompt: |",
        "  Synthetic case for the WP-01 comparison bundle; no trial ever runs it.",
        "target: {kind: agent, name: reviewer}",
        "routing:",
        "  expect: fire",
    ]
    lines += [f"{key}: {value}" for key, value in extra.items()]
    path = SCENARIOS / f"{case_id}.yaml"
    write(path, "\n".join(lines) + "\n")
    return catalog.load_scenario(path)


def record(case_id: str, case_sha: str, label: str, slot: int, number: int, status: str | None, *,
           state: str = "final", run_end: dict | None = None, check_state: str | None = None,
           cost: dict | None = None, truncated: bool = False, evidence: tuple[str, ...] = ("outputs/response.md",),
           runtime: dict | None = None, reason: str | None = None) -> dict:
    check_state = check_state or status or "INCONCLUSIVE"
    return {
        "format": {"name": "save-toolkit.eval-record", "version": 1},
        "case": {"id": case_id, "case_sha256": case_sha, "scenario_sha256": SCENARIO_SHA},
        "candidate": {"plugin_root": f"/synthetic/{label}", "plugin_inputs_dirty": False, **ARMS[label]},
        "runner": {"runner_commit": "3" * 40, "runner_source_dirty": False, "runner_source_sha256": "c" * 64},
        "conditions": {
            "requested_model": "sonnet",
            "observed_models": None if state == "incomplete" else ["claude-synthetic"],
            "runtime": runtime or RUNTIME,
            "turn_limit": 20,
            "wall_clock_seconds": 600,
        },
        "attempt": {
            "label": label, "slot": slot, "number": number, "state": state,
            "started_at": "2026-10-01T00:00:00+00:00", "ended_at": "2026-10-01T00:01:00+00:00",
            **({"reason": reason} if reason else {}),
        },
        "run_end": run_end or {"kind": "completed", "stop": None, "reason": None},
        "checks": [] if state == "incomplete" else [{
            "id": f"{SCENARIO_SHA}:0",
            "text": "routes to the reviewer",
            "kind": "requires",
            "state": check_state,
            "reason": "the trace held no routing decision" if check_state == "INCONCLUSIVE" else None,
            "evidence": ("x" * 600) if truncated else f"synthetic evidence, {check_state}",
            "evidence_truncated": truncated,
        }],
        "verdict": {"status": status, "reason": None if status != "INCONCLUSIVE" else "a check could not measure",
                    "assessment_revision": 0, "after_assessment": None},
        "cost": cost or cost_block(0.1),
        "evidence": {path: path for path in evidence},
    }


def attempt(folder: Path, fields: dict, *, files: tuple[str, ...] = ("outputs/response.md",), tweak=None) -> str:
    if tweak:
        tweak(fields)
    text = json.dumps(RecordV1.model_validate_json(json.dumps(fields)).model_dump(mode="json", exclude_unset=True),
                      indent=2, ensure_ascii=False) + "\n"
    write(folder / "record.json", text)
    for name in files:
        write(folder / name, f"Synthetic {name} for {fields['case']['id']} {fields['attempt']['label']} "
                             f"slot {fields['attempt']['slot']} attempt {fields['attempt']['number']}.\n")
    return text


def main() -> None:
    for generated in (RUNS, SCENARIOS):
        if generated.exists():
            shutil.rmtree(generated)
    digests = {case_id: fingerprints.case_digest(scenario(case_id, extra)) for case_id, extra in CASES.items()}

    def filed(folder: Path, case_id: str, label: str, slot: int, status: str | None, *, number: int = 1,
              case_sha: str | None = None, files: tuple[str, ...] = ("outputs/response.md",), tweak=None,
              **fields) -> str:
        """Write one attempt's record (fields go to record()) and files into `folder`."""
        return attempt(folder, record(case_id, case_sha or digests[case_id], label, slot, number, status, **fields),
                       files=files, tweak=tweak)

    def run(case_id: str, label: str, slot: int, status: str | None, **kw) -> str:
        """The attempt published in a slot."""
        return filed(RUNS / f"eval-{case_id}" / label / f"run-{slot}", case_id, label, slot, status, **kw)

    def kept(case_id: str, label: str, slot: int, number: int, status: str | None, **kw) -> str:
        """An earlier attempt the runner kept under attempts/ when a later one replaced it."""
        folder = RUNS / f"eval-{case_id}" / label / "attempts" / f"run-{slot}" / str(number)
        return filed(folder, case_id, label, slot, status, number=number, **kw)

    def recordless(folder: Path, state: str = "final") -> None:
        """An attempt the runner kept or published without record.json: the attempt.json it writes as
        every attempt starts, its grade and its response."""
        attempt_file = {"attempt": 1, "state": state, "recorded_at": "2026-10-01T00:00:00+00:00"}
        write(folder / "attempt.json", json.dumps(attempt_file, indent=2) + "\n")
        write(folder / "grading.json", json.dumps({"status": "FAIL", "expectations": []}, indent=2) + "\n")
        write(folder / "outputs" / "response.md", "Synthetic response with no record.\n")

    run("synthetic-gain", "incumbent", 1, "FAIL")
    run("synthetic-gain", "candidate", 1, "PASS",
        cost=cost_block(0.1, 0.01, judge_live_calls=1, judge_cached_calls=1))
    run("synthetic-regression", "incumbent", 1, "PASS")
    run("synthetic-regression", "candidate", 1, "FAIL")
    run("synthetic-unchanged", "incumbent", 1, "PASS")
    # Truncated check evidence, and a trace the record lists but the bundle lacks (AC-19).
    run("synthetic-unchanged", "candidate", 1, "PASS", truncated=True, evidence=("outputs/response.md", "stdout.jsonl"))
    for slot, status in enumerate(("PASS", "FAIL", "FAIL"), 1):
        run("synthetic-threshold", "incumbent", slot, status)
    for slot, status in enumerate(("PASS", "PASS", "FAIL"), 1):
        run("synthetic-threshold", "candidate", slot, status)
    run("synthetic-unmeasured", "incumbent", 1, "PASS")
    run("synthetic-unmeasured", "candidate", 1, "INCONCLUSIVE")
    # AC-17: a replaced attempt and its replacement fill one slot; an attempt that raised fills none.
    for slot in (1, 2):
        run("synthetic-attempts", "incumbent", slot, "PASS")
    kept("synthetic-attempts", "candidate", 1, 1, "FAIL", state="superseded", reason="replaced by attempt 2",
         cost=cost_block(0.2))
    run("synthetic-attempts", "candidate", 1, "PASS", number=2)
    kept("synthetic-attempts", "candidate", 2, 1, None, state="incomplete",
         run_end={"kind": "incomplete", "stop": None, "reason": "AuthenticationFailed: synthetic login expired"},
         cost=unknown_cost(), files=(), evidence=())
    run("synthetic-missing", "incumbent", 1, "PASS")
    legacy = RUNS / "eval-synthetic-legacy" / "incumbent" / "run-1"
    write(legacy / "grading.json", json.dumps({"status": "PASS", "expectations": []}, indent=2) + "\n")
    write(legacy / "provenance.json", json.dumps({"runtime": RUNTIME}, indent=2) + "\n")
    run("synthetic-legacy", "candidate", 1, "PASS")
    run("synthetic-case-changed", "incumbent", 1, "PASS")
    run("synthetic-case-changed", "candidate", 1, "PASS", case_sha="e" * 64)
    run("synthetic-conditions", "incumbent", 1, "PASS")
    run("synthetic-conditions", "candidate-cli", 1, "PASS", runtime={**RUNTIME, "cli_version": "0.0.1 (synthetic)"})
    # AC-02: a cut-off record, a record of an unsupported major version, and a superseded attempt whose
    # record still says final because its update failed.
    for slot in (1, 2):
        run("synthetic-unusable", "incumbent", slot, "PASS")
    text = run("synthetic-unusable", "candidate", 1, "PASS")
    write(RUNS / "eval-synthetic-unusable" / "candidate" / "run-1" / "record.json", text[: len(text) // 2])
    text = run("synthetic-unusable", "candidate", 2, "PASS")
    write(RUNS / "eval-synthetic-unusable" / "candidate" / "run-2" / "record.json",
          text.replace('"version": 1', '"version": 2', 1))
    kept("synthetic-unusable", "candidate", 1, 1, "FAIL")  # state final, filed as a kept attempt
    # A run the runner published, and an attempt it kept, without record.json (its record was refused):
    # the slot stays and fails to measure, rather than the arm pooling over fewer trials.
    for slot in (1, 2):
        run("synthetic-recordless", "incumbent", slot, "PASS")
    run("synthetic-recordless", "candidate", 1, "PASS", number=2)
    recordless(RUNS / "eval-synthetic-recordless" / "candidate" / "attempts" / "run-1" / "1", "superseded")
    recordless(RUNS / "eval-synthetic-recordless" / "candidate" / "run-2")
    # A batch that stopped early ran fewer slots: never set beside a complete arm.
    for slot, status in enumerate(("PASS", "FAIL", "FAIL"), 1):
        run("synthetic-stopped-early", "incumbent", slot, status)
    run("synthetic-stopped-early", "candidate", 1, "PASS")
    # A previous run whose move into attempts/ failed: paid for and never published, with a readable
    # record that gives its cost.
    run("synthetic-unpublished", "incumbent", 1, "PASS")
    run("synthetic-unpublished", "candidate", 1, "PASS", number=2)
    filed(RUNS / "eval-synthetic-unpublished" / "candidate" / ".run-1-previous-0a1b2c3d4e5f6a7b",
          "synthetic-unpublished", "candidate", 1, "FAIL", cost=cost_block(0.3))
    # An attempt that never published started a slot of its own: the arms then ran different slots.
    run("synthetic-unpublished-slot", "incumbent", 1, "PASS")
    run("synthetic-unpublished-slot", "candidate", 1, "PASS")
    recordless(RUNS / "eval-synthetic-unpublished-slot" / "candidate" / ".run-2-attempt-1a2b3c4d5e6f7a8b")
    # Identity a batch would refuse to pool on: an unknown CLI, and two wall-clock limits in one case.
    run("synthetic-identity-gap", "incumbent", 1, "PASS")
    run("synthetic-identity-gap", "candidate-nocli", 1, "PASS", runtime={**RUNTIME, "cli_version": None})
    for slot in (1, 2):
        run("synthetic-mixed-trials", "incumbent", slot, "PASS")
    run("synthetic-mixed-trials", "candidate", 1, "PASS")
    run("synthetic-mixed-trials", "candidate", 2, "PASS",
        tweak=lambda r: r["conditions"].update(wall_clock_seconds=300))
    # A later regrade sits beside the original verdict; the comparison keeps revision 0.
    run("synthetic-regraded", "incumbent", 1, "PASS")
    run("synthetic-regraded", "candidate", 1, "PASS", tweak=lambda r: r.update(assessments=[
        {"revision": 1, "status": "FAIL", "reason": None, "grading": "grading.regrade-1.json",
         "runner_source_sha256": "e" * 64, "assessed_at": "2026-10-02T00:00:00+00:00"},
        {"revision": 2, "status": "FAIL", "reason": None, "grading": "grading.regrade-2.json",
         "runner_source_sha256": "f" * 64, "assessed_at": "2026-10-03T00:00:00+00:00"}]))
    # Arms measured on another model, or graded by another runner, are not one comparison.
    run("synthetic-model", "incumbent", 1, "PASS")
    run("synthetic-model", "candidate-opus", 1, "PASS", tweak=lambda r: r["conditions"].update(
        requested_model="opus", observed_models=["claude-synthetic-opus"]))
    run("synthetic-runner", "incumbent", 1, "PASS")
    run("synthetic-runner", "candidate", 1, "PASS", tweak=lambda r: r["case"].update(scenario_sha256="f" * 64))
    # A case whose only attempt the runner published without a record is not legacy: its attempt.json
    # names a runner that writes records, so the slot stays and fails to measure.
    run("synthetic-refused", "incumbent", 1, "PASS")
    recordless(RUNS / "eval-synthetic-refused" / "candidate" / "run-1")
    # Arms run under different wall-clock limits are not one comparison.
    run("synthetic-wall-clock", "incumbent", 1, "PASS")
    run("synthetic-wall-clock", "candidate", 1, "PASS",
        tweak=lambda r: r["conditions"].update(wall_clock_seconds=300))
    run("synthetic-turn-limit", "incumbent", 1, "PASS")
    run("synthetic-turn-limit", "candidate", 1, "PASS", tweak=lambda r: r["conditions"].update(turn_limit=5))
    # Records filed in a folder they disagree with, one field each.
    for slot in (1, 2, 3, 4):
        run("synthetic-misfiled", "incumbent", slot, "PASS")
    run("synthetic-misfiled", "candidate", 1, "PASS", tweak=lambda r: r["attempt"].update(slot=9))
    run("synthetic-misfiled", "candidate", 2, "PASS", tweak=lambda r: r["attempt"].update(label="incumbent"))
    run("synthetic-misfiled", "candidate", 3, "PASS", tweak=lambda r: r["case"].update(id="synthetic-gain"))
    run("synthetic-misfiled", "candidate", 4, "PASS", number=2)
    kept("synthetic-misfiled", "candidate", 4, 1, "FAIL", state="superseded",
         tweak=lambda r: r["attempt"].update(number=3))
    print(f"wrote {sum(1 for p in (RUNS, SCENARIOS) for f in p.rglob('*') if f.is_file())} files under {OUT}")


if __name__ == "__main__":
    main()
