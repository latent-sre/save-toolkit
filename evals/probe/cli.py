"""The `build_probe.py` command line: run, validate, regrade, rescore, diff, and schema.

Each job is a subcommand. The flat flags the runner has always taken (`--validate`, `--regrade DIR`,
`--rescore DIR --out DIR`, `--rescore-diff BASE CANDIDATE`, and a bare run) still parse and reach
the same handlers, so saved scripts and a base runner in a rescore gate keep working.

Exit codes: 0 a passing batch or a clean job, 1 a FAIL verdict or a differing rescore, 2 an
INCONCLUSIVE batch, 3 a refused job (bad input or scenario), 4 authentication lost mid-batch.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import clean_room
import judge as rubric_judge

from . import assessment, batches, catalog, fingerprints, records, rescoring, trials
from .constants import ROOT

DEFAULT_TIMEOUT = 900
COMMANDS = ("run", "validate", "regrade", "rescore", "diff", "schema")
MIXED_MODELS = "mixed resolved model identities"


def _threshold(value: str) -> float:
    """The same bound the scenario validator applies: 0 < threshold <= 1.

    An unbounded float makes the flag a way to fake a verdict: 0 or less sets `required` to zero
    and reports PASS for a batch where every trial failed, above one makes success impossible, and
    `nan` crashes `math.ceil` mid-batch. All three fail the one comparison below.
    """
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"--threshold must be a number, got {value!r}") from None
    if not 0 < number <= 1:  # also rejects nan and inf, which compare false against everything
        raise argparse.ArgumentTypeError(f"--threshold must be > 0 and <= 1, got {value!r}")
    return number


def _budget(value: str) -> float:
    """A spend cap: finite and above zero. NaN compares false against everything, so it would never stop."""
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"--max-batch-usd must be a number, got {value!r}") from None
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError(f"--max-batch-usd must be finite and > 0, got {value!r}")
    return number


def _scenario_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scenario", default="all", help="scenario id under evals/build-scenarios, or 'all'")


def _threshold_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--threshold",
        type=_threshold,
        default=None,
        help="fraction of trials that must PASS for a scenario verdict (positives only; "
        "not_fire scenarios are always clamped to 1.0). Default: the scenario's own.",
    )


def _run_options(parser: argparse.ArgumentParser, *, required: bool) -> None:
    _scenario_option(parser)
    parser.add_argument(
        "--plugin-root",
        type=Path,
        default=ROOT,
        help="plugin root to load with --plugin-dir (a worktree for the incumbent)",
    )
    parser.add_argument(
        "--label", required=required, help="configuration label for the output layout, e.g. new_skill / old_skill"
    )
    parser.add_argument("--model", default=None, help="Claude model alias; resolved model is recorded from the trace")
    parser.add_argument(
        "--judge-calibration",
        type=Path,
        help="completed canonical calibration identity.json required by rubric-backed trials",
    )
    parser.add_argument("--trials", type=int, default=1)
    _threshold_option(parser)
    parser.add_argument(
        "--run-offset", type=int, default=0, help="first run number minus one, to append trials to an existing label"
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--max-batch-usd",
        type=_budget,
        default=None,
        metavar="USD",
        help="stop scheduling trials once this batch's known spend reaches USD, or once a trial's cost is unknown",
    )
    parser.add_argument(
        "--out", type=Path, required=required, help="iteration directory for the reviewer/aggregator layout"
    )
    parser.add_argument("--executable", default=os.environ.get("CLAUDE_BIN", "claude"))
    parser.add_argument("--keep-workspace", action="store_true")
    parser.add_argument(
        "--overwrite", action="store_true", help="replace an existing run-N under this label instead of refusing"
    )
    parser.add_argument(
        "--expect-plugin-digest",
        metavar="SHA256",
        help="refuse to run unless the plugin root's source digest starts with this value "
        "(binds a batch to approved candidate bytes)",
    )
    parser.add_argument("--docker", default="docker", help="container runtime executable used by backing services")


def _command_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_probe.py", description=(__doc__ or "").split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    _run_options(
        commands.add_parser("run", help="run trials of the selected scenarios and publish each attempt"), required=True
    )
    _scenario_option(commands.add_parser("validate", help="validate scenario specs and exit"))
    regrade = commands.add_parser(
        "regrade", help="re-score saved runs with the current checks, beside each run (no model)"
    )
    regrade.add_argument("iteration", type=Path, metavar="ITERATION_DIR")
    _scenario_option(regrade)
    _threshold_option(regrade)
    rescore = commands.add_parser(
        "rescore",
        help="grade saved runs with this runner into a new directory; "
        "a comparison across runner revisions, not a verdict",
    )
    rescore.add_argument("iteration", type=Path, metavar="ITERATION_DIR")
    rescore.add_argument("--out", type=Path, help="a new directory outside the saved runs")
    _scenario_option(rescore)
    diff = commands.add_parser(
        "diff", help="list every verdict that differs between two rescores (exit 1 when any does)"
    )
    diff.add_argument("diff_paths", type=Path, nargs=2, metavar=("BASE", "CANDIDATE"))
    schema = commands.add_parser("schema", help="print the JSON Schema of the v1 result record")
    schema.add_argument("--out", type=Path, help="write the schema here instead of printing it")
    return parser


def _legacy_parser() -> argparse.ArgumentParser:
    """The flat flags every earlier runner took; each one maps onto a subcommand."""
    parser = argparse.ArgumentParser(
        prog="build_probe.py",
        description=(__doc__ or "").split("\n\n")[0],
        epilog=f"Subcommands: {', '.join(COMMANDS)}. Run `build_probe.py COMMAND --help` for each.",
    )
    _run_options(parser, required=False)
    parser.add_argument("--validate", action="store_true", help="validate scenario specs and exit")
    parser.add_argument(
        "--regrade",
        type=Path,
        metavar="ITERATION_DIR",
        help="re-score saved runs under this directory with the current checks (no model); workspace-dependent verdicts are kept",
    )
    parser.add_argument(
        "--rescore",
        type=Path,
        metavar="ITERATION_DIR",
        help="grade saved runs with this runner into --out, never writing the saved runs; a comparison across runner revisions, not a verdict",
    )
    parser.add_argument(
        "--rescore-diff",
        type=Path,
        nargs=2,
        metavar=("BASE", "CANDIDATE"),
        help="list every verdict that differs between two --rescore outputs (exit 1 when any does)",
    )
    return parser


def _legacy_command(args: argparse.Namespace) -> str:
    """The subcommand a set of flat flags means, in the precedence the flags always had."""
    if args.rescore_diff:
        args.diff_paths = args.rescore_diff
        return "diff"
    if args.validate:
        return "validate"
    if args.rescore:
        args.iteration = args.rescore
        return "rescore"
    if args.regrade:
        args.iteration = args.regrade
        return "regrade"
    return "run"


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] in COMMANDS:
        parser = _command_parser()
        args = parser.parse_args(arguments)
        command = args.command
    else:
        parser = _legacy_parser()
        args = parser.parse_args(arguments)
        command = _legacy_command(args)
    if getattr(args, "trials", 1) < 1:
        parser.error("--trials must be at least 1 (an empty batch is not a green batch)")
    if getattr(args, "run_offset", 0) < 0:
        parser.error("--run-offset must be at least 0 (run numbers start at 1)")
    if command == "diff":
        return diff(args.diff_paths)
    if command == "schema":
        return schema(args.out)
    try:
        scenarios = catalog.load_all_scenarios()
    except ValueError as exc:
        print(f"invalid build scenario:\n{exc}", file=sys.stderr)
        return 3
    if args.scenario != "all":
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
        if not scenarios:
            print(f"no scenario named {args.scenario!r}", file=sys.stderr)
            return 3
    if command == "validate":
        return validate(scenarios)
    if command == "rescore":
        return rescore(args.iteration, args.out, scenarios)
    if command == "regrade":
        return regrade(args.iteration, scenarios, args.threshold)
    if not args.label or not args.out:
        parser.error("--label and --out are required to run trials")
    return run(args, scenarios)


def diff(paths: Sequence[Path]) -> int:
    try:
        base, candidate = (rescoring.load_rescore(path) for path in paths)
    except (OSError, ValueError) as exc:
        print(f"cannot read a rescore: {exc}", file=sys.stderr)
        return 3
    lines = rescoring.rescore_diff(base, candidate)
    for line in lines:
        print(line)
    if base.get("runner") == candidate.get("runner"):
        print("warning: both rescores came from the same runner identity", file=sys.stderr)
    print(f"{len(lines)} difference(s)")
    return 1 if lines else 0


def schema(out: Path | None) -> int:
    text = json.dumps(records.record_schema(), indent=2, ensure_ascii=False) + "\n"
    if out is None:
        sys.stdout.write(text)
    else:
        out.write_text(text, encoding="utf-8", newline="\n")
    return 0


def validate(scenarios: list[dict[str, Any]]) -> int:
    kinds: dict[str, int] = {}
    for spec in scenarios:
        kinds[catalog.scenario_kind(spec)] = kinds.get(catalog.scenario_kind(spec), 0) + 1
    shape = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
    expectations = sum(len(assessment.scenario_assertions(s)) for s in scenarios)
    print(f"scenarios OK -- {len(scenarios)} spec(s) ({shape}), {expectations} graded expectations")
    return 0


def rescore(iteration_dir: Path, out_dir: Path | None, scenarios: list[dict[str, Any]]) -> int:
    iteration, out = iteration_dir.resolve(), (out_dir.resolve() if out_dir else None)
    if out is None or out.exists() or out.is_relative_to(iteration):
        print("--rescore needs --out naming a new directory outside the saved runs", file=sys.stderr)
        return 3
    out.mkdir(parents=True)
    rows = rescoring.rescore(iteration, scenarios, out)
    changed = 0
    for r in rows:
        if r.get("error"):
            print(f"eval-{r['scenario']} {r['label']}/run-{r['run']}: not rescored: {r['error']}")
            continue
        saved, now = r["saved"]["status"], r["rescored"]["status"]
        changed += saved != now
        relaxed = " (identity relaxed)" if r["identity_relaxed"] else ""
        print(f"eval-{r['scenario']} {r['label']}/run-{r['run']}: saved {saved}, rescored {now}{relaxed}")
    skipped = json.loads((out / "rescore.json").read_text(encoding="utf-8"))["skipped"]
    if skipped["scenarios"]:
        print(f"skipped scenario(s) not in this checkout: {', '.join(skipped['scenarios'])}")
    if skipped["runs_without_trace_summary"]:
        print(f"skipped {skipped['runs_without_trace_summary']} run(s) with no trace summary")
    if skipped["other_run_folders"]:
        print(f"skipped folder(s) that are not numbered runs: {', '.join(skipped['other_run_folders'])}")
    print(
        f"rescored {len(rows)} run(s) into {out}; {changed} differ from the saved verdict "
        "(including any scenario edits since the run; diff two rescores to isolate a runner change)"
    )
    return 0


def regrade(iteration_dir: Path, scenarios: list[dict[str, Any]], threshold: float | None) -> int:
    rows = rescoring.regrade(iteration_dir.resolve(), scenarios)
    for r in rows:
        scope = " (structural only; semantics UNVERIFIED)" if r.get("semantic_assessment") else ""
        print(f"eval-{r['scenario']} {r['label']}/run-{r['run']}: {r['status']} {r['passed']}/{r['total']}{scope}")
    print(f"regraded {len(rows)} run(s)")

    # Exit like a run: trials aggregate per scenario against its threshold within one label and one
    # resolved model (a directory can hold several arms, and a label's slots several models), then
    # 1 for any FAIL verdict and 2 for any INCONCLUSIVE one. Regrading nothing measured nothing.
    def arm(row: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
        return row["label"], tuple(batches.model_identities([row]))

    states = [
        verdict["verdict"]
        for key in sorted({arm(r) for r in rows})
        for verdict in batches.aggregate_by_scenario(scenarios, [r for r in rows if arm(r) == key], threshold).values()
    ]
    if "FAIL" in states:
        return 1
    return 2 if not states or "INCONCLUSIVE" in states else 0


def run(args: argparse.Namespace, scenarios: list[dict[str, Any]]) -> int:
    """Run the batch, publish every attempt, and exit on the batch's verdict."""
    required = set().union(*(fingerprints.required_rubrics(spec) for spec in scenarios))
    judge_binding = None
    try:
        if required:
            if not args.judge_calibration:
                raise rubric_judge.JudgeUnavailable("rubric-backed trials require --judge-calibration identity.json")
            judge_binding = rubric_judge.load_binding(args.judge_calibration, required)
    except rubric_judge.JudgeUnavailable as exc:
        print(f"refusing to run: {exc}", file=sys.stderr)
        return 3
    provenance = fingerprints.plugin_provenance(args.plugin_root.resolve())
    runtime = fingerprints.runtime_identity(args.executable)
    print(
        json.dumps(
            {
                "plugin": provenance,
                "runtime": runtime,
                "judge_binding": judge_binding.metadata if judge_binding else None,
            }
        ),
        flush=True,
    )
    if args.expect_plugin_digest and not provenance["plugin_source_sha256"].startswith(args.expect_plugin_digest):
        print(
            f"refusing to run: plugin source digest {provenance['plugin_source_sha256'][:12]}… does not match "
            "--expect-plugin-digest",
            file=sys.stderr,
        )
        return 3
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / f"summary-{args.label}-{args.model or 'default'}.json"
    existing = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else []
    replaced = {(s["id"], args.label, args.run_offset + i + 1) for s in scenarios for i in range(args.trials)}
    retained = [
        e for e in existing if not args.overwrite or (e.get("scenario"), e.get("label"), e.get("run")) not in replaced
    ]
    problem = batches.batch_identity_problem(
        retained, scenarios, provenance["plugin_source_sha256"], judge_binding, runtime
    )
    if problem:
        print(json.dumps({"batch": "INCONCLUSIVE", "reason": problem}), flush=True)
        return 2
    results: list[dict[str, Any]] = []
    blocked: str | None = None
    auth_failed = False
    planned = [(spec, i) for spec in scenarios for i in range(args.trials)]
    selected_ids = {spec["id"] for spec in scenarios}
    prior = [e for e in retained if e.get("scenario") in selected_ids]
    spent = sum(records.known_usd(e.get("known_cost_usd")) or 0.0 for e in prior)
    if args.max_batch_usd is not None and any(e.get("cost_complete") is not True for e in prior):
        # A retained trial without a known cost leaves the batch's spend unknown; the cap cannot hold.
        blocked = f"a retained trial's cost is unknown; the USD {args.max_batch_usd:g} cap cannot be enforced"
    machinery_stopped: dict[str, str] = {}
    try:
        for spec, i in planned:
            if blocked:  # stopped before scheduling: a retained trial already broke the cap's accounting
                break
            if spec["id"] in machinery_stopped:
                continue  # its grader cannot measure; more trials would spend for nothing
            if args.max_batch_usd is not None and spent >= args.max_batch_usd:
                blocked = f"batch spend USD {spent:.4f} reached the USD {args.max_batch_usd:g} cap"
                break
            try:
                results.append(
                    trials.run_trial(
                        spec,
                        plugin_root=args.plugin_root.resolve(),
                        label=args.label,
                        model=args.model,
                        run_number=args.run_offset + i + 1,
                        out_dir=out,
                        timeout=args.timeout,
                        executable=args.executable,
                        keep_workspace=args.keep_workspace,
                        overwrite=args.overwrite,
                        docker=args.docker,
                        expected_plugin_digest=provenance["plugin_source_sha256"],
                        judge_binding=judge_binding,
                        runtime=runtime,
                    )
                )
            except clean_room.AuthUnavailable as exc:
                # Every later trial would fail the same way; the attempt is kept, the batch stops.
                blocked, auth_failed = f"authentication unavailable: {exc}", True
                break
            if results[-1].get("grader_error"):
                machinery_stopped[spec["id"]] = results[-1]["grader_error"]
                print(
                    json.dumps(
                        {"scenario": spec["id"], "stopped": f"grading machinery failed: {results[-1]['grader_error']}"}
                    ),
                    flush=True,
                )
            if results[-1].get("after_assessment"):
                # The finished trial keeps its verdict; nothing else may reuse the uncleaned environment.
                blocked = results[-1]["after_assessment"]
                break
            spent += float(results[-1].get("known_cost_usd") or 0.0)
            if args.max_batch_usd is not None and results[-1].get("cost_complete") is False:
                # An unknown cost cannot be held to a cap; stop before spending more blind.
                blocked = f"trial cost unknown; the USD {args.max_batch_usd:g} cap cannot be enforced"
                break
    finally:
        # Written even when a trial raised: every trial that finished was paid for and stays counted.
        merged = batches.merge_summary_entries(existing, results)
        summary_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    # `--run-offset` appends trials to an existing label. The verdict is about that whole batch, not
    # about this invocation: a final one-trial append must not report PASS over earlier failures.
    batch = [entry for entry in merged if entry.get("scenario") in selected_ids]
    problem = batches.batch_identity_problem(
        batch, scenarios, provenance["plugin_source_sha256"], judge_binding, runtime
    )
    stop = (
        {
            "batch": "INCONCLUSIVE",
            "reason": f"stopped after {blocked}" if blocked else "grading machinery failed",
            **({"scenarios_stopped": sorted(machinery_stopped)} if machinery_stopped else {}),
            "trials_not_run": len(planned) - len(results),
        }
        if blocked or machinery_stopped
        else None
    )
    if auth_failed and stop is not None:
        # A resume replaces what this --overwrite had not reached yet, but keeps the other rows and
        # this invocation's trials; name what they would still refuse.
        kept = [e for e in batches.merge_summary_entries(retained, results) if e.get("scenario") in selected_ids]
        unfixed = batches.batch_identity_problem(
            kept, scenarios, provenance["plugin_source_sha256"], judge_binding, runtime
        ) or (MIXED_MODELS if len(batches.model_identities(kept)) > 1 else None)
        if unfixed:
            stop["unfixed_by_resume"] = unfixed
    return _conclude(batch, scenarios, args.threshold, problem, stop, auth_failed=auth_failed)


def _conclude(
    batch: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
    threshold: float | None,
    problem: str | None,
    stop: dict[str, Any] | None,
    *,
    auth_failed: bool,
) -> int:
    """Print how the batch ended and return its exit code; the order of these exits is the policy.

    `problem` is why the batch's trials cannot be pooled, and `stop` why scheduling ended early.
    """
    if auth_failed and stop:
        # Exit 4, distinct from FAIL (1) and INCONCLUSIVE (2): re-authenticate, then resume. Until
        # then no verdict covers the batch, and nothing a later check refuses changes why it stopped.
        print(json.dumps(stop), flush=True)
        return 4
    if problem:
        print(json.dumps({"batch": "INCONCLUSIVE", "reason": problem}), flush=True)
        return 2
    identities = batches.model_identities(batch)
    if len(identities) > 1:
        # Routing and behaviour are model-dependent, so trials under two resolved models are two
        # measurements. Aggregating them would emit one verdict for neither.
        print(
            json.dumps({"batch": "INCONCLUSIVE", "reason": MIXED_MODELS, "models": identities}),
            flush=True,
        )
        print(f"{len(batch)} trial(s) under {len(identities)} resolved models: not aggregated, not publishable")
        return 2
    verdicts = batches.aggregate_by_scenario(scenarios, batch, threshold)
    for scenario_id, verdict in sorted(verdicts.items()):
        print(
            json.dumps(
                {
                    "scenario": scenario_id,
                    "verdict": verdict["verdict"],
                    **assessment.native_assessment(next(spec for spec in scenarios if spec["id"] == scenario_id)),
                    "passed": verdict["passed"],
                    "trials": verdict["trials"],
                    "threshold": verdict["threshold"],
                }
            ),
            flush=True,
        )
    passed = sum(r["status"] == "PASS" for r in batch)
    print(f"{passed}/{len(batch)} trials PASS ({sum(r['status'] == 'INCONCLUSIVE' for r in batch)} inconclusive)")
    states = [v["verdict"] for v in verdicts.values()]
    if stop:
        print(json.dumps(stop), flush=True)
    if "FAIL" in states:
        return 1
    return 2 if stop or "INCONCLUSIVE" in states else 0
