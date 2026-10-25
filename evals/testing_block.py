"""Prepare/validate bounded admitted-case commands and report saved records; never launch a runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from codex_probe import GCP_CASES, RELIABILITY_CASE, SUPPORTED_CASES, model_matches
from probe import catalog, constants, fingerprints, layout
from probe.records import RecordV1, known_usd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "evals/manifests/multi-model-testing.json"
CASES = ["build-injection-log-benign", "build-injection-log-malicious"]
MODELS = [
    {"model": "claude-sonnet-5-5", "profile": "native-claude-cli", "host_group": "native"},
    *(
        {"model": model, "profile": "codex-structured-file-v1", "host_group": "codex"}
        for model in ("gpt-6.1-sol", "gpt-6-luna", "gpt-5.6-terra")
    ),
]


def safe(path: Path) -> Path:
    """Reject traversal and symlink components before resolving inputs or outputs."""
    if ".." in path.parts:
        raise ValueError("path traversal is unsupported")
    absolute = path.absolute()
    if any(part.is_symlink() for part in (absolute, *absolute.parents)):
        raise ValueError("symlink paths are unsupported")
    return absolute


def read(path: Path) -> Any:
    path = safe(path)
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("JSON input exceeds 8 MiB")
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write(path: Path, value: Any) -> None:
    with safe(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def case_groups(names: Any) -> list[tuple[str, list[str]]]:
    """Keep selected admitted pairs complete and adjacent; reliability is a singleton."""
    if not isinstance(names, list) or not names or any(not isinstance(name, str) for name in names):
        raise ValueError("cases must be a nonempty explicit list")
    if len(set(names)) != len(names) or set(names) - SUPPORTED_CASES:
        raise ValueError("duplicate or unsupported selected case")
    groups: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        pair = (
            "reliability"
            if name == RELIABILITY_CASE
            else "gcp01"
            if name in GCP_CASES
            else name.removeprefix("build-injection-").rsplit("-", 1)[0]
        )
        members = (
            [RELIABILITY_CASE]
            if pair == "reliability"
            else sorted(GCP_CASES)
            if pair == "gcp01"
            else [f"build-injection-{pair}-{arm}" for arm in ("benign", "malicious")]
        )
        if not set(members) <= set(names):
            raise ValueError(f"incomplete selected pair: {pair}")
        groups.append((pair, members))
        seen.update(members)
    return groups


def cases(names: Any = None) -> list[dict[str, Any]]:
    specs = [
        catalog.load_scenario(constants.SCENARIO_DIR / f"{name}.yaml")
        for _, members in case_groups(CASES if names is None else names)
        for name in members
    ]
    for spec in specs:
        problems = catalog.validate_scenario(spec)
        if problems or any(check.get("rubric_name") for check in spec["checks"]):
            raise ValueError(f"unsupported or judged case: {spec['id']}")
    return specs


def selected_manifest(path: Path) -> dict[str, Any]:
    manifest = read(path)
    keys = {"format", "cases", "models", "trials_per_case", "attempt_limit", "judge_calls", "approved_total_usd"}
    if (
        not isinstance(manifest, dict)
        or set(manifest) != keys
        or manifest["format"] != "multi-model-testing-v1"
        or manifest["models"] != MODELS
    ):
        raise ValueError("unsupported manifest/model/profile selection")
    groups = case_groups(manifest["cases"])
    trials = manifest["trials_per_case"]
    if type(trials) is not int or not 1 <= trials <= 3:
        raise ValueError("trials_per_case must be 1..3")
    count = sum(len(members) for _, members in groups) * len(MODELS) * trials
    if (
        type(manifest["attempt_limit"]) is not int
        or manifest["attempt_limit"] != count
        or type(manifest["judge_calls"]) is not int
        or manifest["judge_calls"] != 0
    ):
        raise ValueError("attempt_limit must match all selected slots and judge_calls must be zero")
    cap = known_usd(manifest["approved_total_usd"])
    if cap is None or cap <= 0:
        raise ValueError("approved_total_usd must be a positive finite dollar amount")
    return manifest


def adapters() -> dict[str, str]:
    return {
        name: hashlib.sha256((ROOT / "evals" / name).read_text(encoding="utf-8").encode()).hexdigest()
        for name in ("codex_probe.py", "codex_fixture_tools.py", "codex_gcp_queries.py")
    }


def prepare(manifest: Path, candidate: Path, out: Path, native_host: str, codex_host: str) -> dict[str, Any]:
    expected = selected_manifest(manifest)
    groups = case_groups(expected["cases"])
    trials = expected["trials_per_case"]
    if not native_host.strip() or not codex_host.strip():
        raise ValueError("both recorded hostnames are required")
    candidate, out = safe(candidate), safe(out)
    bindings = [{"id": spec["id"], "case_sha256": fingerprints.case_digest(spec)} for spec in cases(expected["cases"])]
    plugin = fingerprints.plugin_digest(candidate)
    plan: dict[str, Any] = {
        "format": "multi-model-testing-plan-v1",
        "manifest": expected,
        "candidate_root": str(candidate),
        "plugin_sha256": plugin,
        "runner_sha256": fingerprints.harness_source_digest(),
        "adapter_sha256": adapters(),
        "case_bindings": bindings,
        "slots": [],
        "commands": [],
        "budget": {
            "approved_total_usd": expected["approved_total_usd"],
            "kind": "scheduling-limit",
            "hard_enforcement": False,
            "native_invocation_usd": 0.75,
        },
    }
    by_case = {binding["id"]: binding for binding in bindings}
    for model in MODELS:
        host = native_host if model["host_group"] == "native" else codex_host
        name = model["model"]
        common = ["--expect-plugin-digest", plugin, "--model", name]
        for trial in range(1, trials + 1):
            for pair, members in groups:
                for case in members:
                    plan["slots"].append(
                        {
                            "case": case,
                            "case_sha256": by_case[case]["case_sha256"],
                            "model": name,
                            "host": host,
                            "profile": model["profile"],
                            "trial": trial,
                            "semantic_review_required": case == RELIABILITY_CASE or case in GCP_CASES,
                        }
                    )
                if model["host_group"] == "native":
                    commands = [
                        [
                            sys.executable,
                            str(ROOT / "evals/build_probe.py"),
                            "run",
                            "--scenario",
                            case,
                            "--plugin-root",
                            str(candidate),
                            "--label",
                            name,
                            "--trials",
                            "1",
                            "--run-offset",
                            str(trial - 1),
                            "--max-invocation-usd",
                            "0.75",
                            "--out",
                            str(out / "results/native"),
                            *common,
                        ]
                        for case in members
                    ]
                else:
                    # Keep legacy one-pair/one-trial smoke paths readable; repeated commands get fresh destinations.
                    destination = out / "results" / name
                    if trials > 1 or len(groups) > 1:
                        destination = destination / f"trial-{trial}" / pair
                    commands = [
                        [
                            sys.executable,
                            str(ROOT / "evals/codex_probe.py"),
                            "--pair",
                            pair,
                            "--candidate-root",
                            str(candidate),
                            "--case-bindings",
                            str(out / "case-bindings.json"),
                            "--out",
                            str(destination),
                            "--approve-fixture-tools",
                            *common,
                        ]
                    ]
                for argv in commands:
                    plan["commands"].append(
                        {"model": name, "profile": model["profile"], "host": host, "trial": trial, "argv": argv}
                    )
    plan["testing_block_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    plan["plan_sha256"] = digest(plan)
    out.mkdir(parents=True, exist_ok=False)
    write(out / "case-bindings.json", bindings)
    write(out / "plan.json", plan)
    return plan


def load_plan(block: Path) -> dict[str, Any]:
    plan = read(block / "plan.json")
    if not isinstance(plan, dict) or plan.get("format") != "multi-model-testing-plan-v1":
        raise ValueError("unsupported testing plan")
    payload = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if plan.get("plan_sha256") != digest(payload):
        raise ValueError("testing plan digest mismatch")
    if read(block / "case-bindings.json") != plan["case_bindings"]:
        raise ValueError("case binding file differs from plan")
    return plan


def validate(block: Path) -> dict[str, Any]:
    plan = load_plan(block)
    bindings = [
        {"id": spec["id"], "case_sha256": fingerprints.case_digest(spec)} for spec in cases(plan["manifest"]["cases"])
    ]
    if (
        bindings != plan["case_bindings"]
        or fingerprints.plugin_digest(safe(Path(plan["candidate_root"]))) != plan["plugin_sha256"]
    ):
        raise ValueError("case or plugin bytes changed since prepare")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != plan["testing_block_sha256"]:
        raise ValueError("testing block bytes changed since prepare")
    if fingerprints.harness_source_digest() != plan["runner_sha256"] or adapters() != plan["adapter_sha256"]:
        raise ValueError("runner or adapter bytes changed since prepare")
    return {"validated": True, "attempt_limit": len(plan["slots"]), "judge_calls": 0, "launch_performed": False}


def attempt(path: Path, plan: dict[str, Any], record_root: Path | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"record": str(path), "state": None, "cost_usd": None, "known_usd": None, "problems": []}
    problems = row["problems"]
    try:
        raw = read(path)
        if not isinstance(raw, dict):
            raise ValueError("record must be an object")
        if raw.get("format") == {"name": "save-toolkit.eval-record", "version": 1}:
            raw = RecordV1.model_validate_json(json.dumps(raw)).model_dump(mode="json")
            cond = raw["conditions"]
            runtime = cond["runtime"] or {}
            row.update(
                case=raw["case"]["id"],
                model=cond["requested_model"],
                host=(runtime.get("host_identity") or {}).get("hostname"),
                profile="native-claude-cli",
                state=raw["verdict"]["status"],
                record_execution_profile=cond.get("execution_profile"),
            )
            if cond["observed_models"] != [row["model"]]:
                problems.append("observed native model differs from requested model")
            cost = raw["cost"]
            components = [known_usd(cost[key]) for key in ("trial_usd", "judge_usd")]
            component_floor = math.fsum(value for value in components if value is not None)
            floor = known_usd(cost["known_usd"])
            row["known_usd"] = (
                max(component_floor, floor or 0.0)
                if floor is not None or any(value is not None for value in components)
                else None
            )
            if cost["complete"]:
                row["cost_usd"] = math.fsum(value for value in components if value is not None)
                if floor is None or not math.isclose(floor, row["cost_usd"], abs_tol=0.000001):
                    problems.append("native cost floor differs from complete components")
            row["trial"] = raw["attempt"]["slot"]
            if raw["attempt"]["number"] != 1:
                problems.append("unexpected native attempt/slot number")
            if cost["judge_calls"] != 0:
                problems.append("unexpected judge calls")
            case_sha, plugin, runner = raw["case"]["case_sha256"], raw["candidate"], raw["runner"]
        elif raw.get("schema") == "codex-record-v1":
            if not all(isinstance(raw.get(key), dict) for key in ("host", "candidate", "shared_runner", "artifacts")):
                raise ValueError("malformed Codex identity sections")
            row.update(
                case=raw["scenario_id"],
                model=raw["model_requested"],
                host=raw["host"].get("hostname"),
                profile="codex-structured-file-v1",
                state=raw["state"],
                record_execution_profile=None,
            )
            relative = path.relative_to(record_root) if record_root is not None else path
            path_trials = {number for part in relative.parts if (number := layout.number(part, "trial-")) is not None}
            row["trial"] = (
                next(iter(path_trials))
                if len(path_trials) == 1
                else 1
                if plan["manifest"]["trials_per_case"] == 1
                else None
            )
            row["trial_binding_from_path"] = bool(path_trials)
            row["execution_id"] = raw.get("thread_id") if isinstance(raw.get("thread_id"), str) else None
            row["cost_usd"] = row["known_usd"] = known_usd(raw.get("cost_usd"))
            if raw.get("pin") != "prompt-injected" or raw.get("reasoning_effort") != "high":
                problems.append("Codex transport profile mismatch")
            session_path = safe(path.parent / "session.jsonl")
            session = session_path.read_text(encoding="utf-8") if session_path.is_file() else ""
            session_sha = hashlib.sha256(session.encode()).hexdigest()
            if raw.get("identity_verified") is not True or not model_matches(
                session, raw.get("thread_id", ""), row["model"]
            ):
                problems.append("observed Codex model/thread identity unverified or mismatched")
            if (raw.get("artifacts") or {}).get("session.jsonl") != session_sha:
                problems.append("Codex model evidence digest mismatch")
            if raw.get("adapter_sha256") != plan["adapter_sha256"]:
                problems.append("Codex adapter identity mismatch")
            if not raw.get("evidence_complete") or raw.get("problem") or raw.get("problems"):
                problems.append("Codex evidence incomplete")
            case_sha, plugin, runner = raw["case_sha256"], raw["candidate"], raw["shared_runner"]
        else:
            raise ValueError("unsupported record format")
        row["runtime"] = raw.get("runtime") if row["profile"].startswith("codex") else runtime
        row["host_identity"] = raw.get("host") if row["profile"].startswith("codex") else runtime.get("host_identity")
        if runtime_problem := fingerprints.runtime_evidence_problem(row["runtime"]):
            problems.append("runtime identity gap: " + runtime_problem)
        if (
            plugin.get("plugin_source_sha256") != plan["plugin_sha256"]
            or runner.get("runner_source_sha256") != plan["runner_sha256"]
        ):
            problems.append("plugin or runner identity mismatch")
        matches = [
            slot
            for slot in plan["slots"]
            if all(slot[key] == row[key] for key in ("case", "model", "host", "profile"))
            and slot.get("trial", 1) == row["trial"]
        ]
        row["slot"] = plan["slots"].index(matches[0]) if len(matches) == 1 else None
        if not matches:
            problems.append("unplanned case/model/host/profile")
        elif case_sha != matches[0]["case_sha256"]:
            problems.append("case identity mismatch")
        row["semantic_review_required"] = row["case"] == RELIABILITY_CASE or row["case"] in GCP_CASES
        if row["semantic_review_required"]:
            row["semantic_review_status"] = "required_not_assessed"
        if row["state"] not in {"PASS", "FAIL", "INCONCLUSIVE", None}:
            problems.append("unsupported result state")
    except (ValueError, KeyError, TypeError, OSError):
        problems.append("invalid or unreadable record")
    return row


def path_trial(directory: Path) -> int | None:
    numbers = {
        number
        for part in directory.parts
        if (number := layout.number(part, "trial-") or layout.slot(part) or layout.hidden_slot(part)) is not None
    }
    return next(iter(numbers)) if len(numbers) == 1 else 1 if not numbers else None


def report(block: Path, records: Path) -> dict[str, Any]:
    plan, records = load_plan(block), safe(records)
    if not records.is_dir():
        raise ValueError("records directory does not exist")
    attempts = []
    for folder, dirs, files in os.walk(records, followlinks=False):
        for name in [*dirs, *files]:
            safe(Path(folder) / name)
        directory = Path(folder)
        recordless_attempt = (
            (layout.slot(directory.name) is not None and directory.parent.name != "attempts")
            or layout.hidden_slot(directory.name) is not None
            or (layout.number(directory.name) is not None and directory.parent.parent.name == "attempts")
            or directory.name in SUPPORTED_CASES
        )
        if "record.json" in files or recordless_attempt:
            row = attempt(directory / "record.json", plan, records)
            if "record.json" not in files:
                matches = [
                    index
                    for index, slot in enumerate(plan["slots"])
                    if slot["model"] in directory.parts
                    and (slot["case"] in directory.parts or "eval-" + slot["case"] in directory.parts)
                    and slot.get("trial", 1) == path_trial(directory.relative_to(records))
                ]
                if len(matches) == 1:
                    row["slot"] = matches[0]
                    row["binding_from_path_only"] = True
            attempts.append(row)
    executions = Counter(row["execution_id"] for row in attempts if row.get("execution_id"))
    for row in attempts:
        row["duplicate_execution"] = executions.get(row.get("execution_id"), 0) > 1
        if row["duplicate_execution"]:
            row["problems"].append("duplicate execution identity reused across saved attempts")
        row["fresh_coverage"] = not row["problems"] and row.get("slot") is not None and row["state"] is not None
    slots, problems = [], []
    for index, slot in enumerate(plan["slots"]):
        rows = [row for row in attempts if row.get("slot") == index]
        slots.append(
            {
                **slot,
                "attempts": len(rows),
                "status": "missing"
                if not rows
                else "duplicate_execution"
                if any(row["duplicate_execution"] for row in rows)
                else "duplicate"
                if len(rows) > 1
                else "present",
                "fresh_coverage": len(rows) == 1 and rows[0]["fresh_coverage"],
            }
        )
        if len(rows) > 1:
            problems.append(f"duplicate attempts for slot {index}")
    problems.extend(problem for row in attempts for problem in row["problems"])
    known = [row["known_usd"] for row in attempts if row["known_usd"] is not None]
    unknown = sum(row["cost_usd"] is None for row in attempts)
    missing = sum(slot["status"] == "missing" for slot in slots)
    complete = bool(attempts) and not unknown
    total = round(math.fsum(row["cost_usd"] for row in attempts), 6) if complete else None
    return {
        "format": "multi-model-testing-report-v1",
        "plan_sha256": plan["plan_sha256"],
        "slots": slots,
        "attempts": attempts,
        "attempt_count": len(attempts),
        "missing_slots": missing,
        "problems": problems,
        "known_usd": round(sum(known), 6) if known else None,
        "cost_usd": total,
        "unknown_cost_attempts": unknown,
        "budget": plan["budget"],
        "ready_for_further_spend": bool(
            complete
            and not missing
            and not problems
            and total is not None
            and total < plan["budget"]["approved_total_usd"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    prep.add_argument("--candidate-root", type=Path, required=True)
    prep.add_argument("--out", type=Path, required=True)
    prep.add_argument("--native-host", required=True)
    prep.add_argument("--codex-host", required=True)
    check = commands.add_parser("validate")
    check.add_argument("block", type=Path)
    saved = commands.add_parser("report")
    saved.add_argument("block", type=Path)
    saved.add_argument("--records", type=Path, required=True)
    saved.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            plan = prepare(args.manifest, args.candidate_root, args.out, args.native_host, args.codex_host)
            result = {"prepared": str(args.out), "attempt_limit": len(plan["slots"]), "launch_performed": False}
        elif args.command == "validate":
            result = validate(args.block)
        else:
            result = report(args.block, args.records)
            write(args.out, result)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"testing block refused: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
