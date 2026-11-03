"""Inspect AI orchestration of the native runner's routing and contract scenarios.

One sample is one native scenario and one epoch is one trial slot. The solver calls
`probe.trials.run_trial` exactly as `build_probe.py run` does, so each attempt is published under
the iteration directory in the same layout, with the same record, provenance, judge binding and
batch summary file, and the scorer reports the verdict `run_trial` returned. Nothing is graded twice
or differently: grading parity with the native batch is by construction. Inspect adds the sample
queue, its limits, the `.eval` log and `inspect view`; trials themselves run one at a time and the
native stop rules hold between them (see `native_trial`). Build probes and native conversations
stay with `build_probe.py` in this cut.

Run with `--model none`: the Claude CLI authenticates itself inside the clean room and Inspect's
model API is not involved. `build_probe.py regrade <out>` remains the per-scenario verdict with
thresholds over the published runs; Inspect's accuracy metric is a mean over trials.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import catalog as suites
from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import CORRECT, INCORRECT, NOANSWER, Score, Scorer, Target, accuracy, scorer, stderr
from inspect_ai.solver import Generate, Solver, TaskState, solver
from probe import batches, fingerprints, layout, selection
from probe import catalog as scenarios
from probe import cli as native_cli
from probe import trials as native_trials
from probe.constants import ROOT
from probe.exits import ExitCode

SUPPORTED_KINDS = frozenset({"routing", "contract"})
# What the score carries from the trial summary, so a log reader sees the same facts a summary row has.
SUMMARY_KEYS = (
    "scenario",
    "label",
    "run",
    "passed",
    "total",
    "models",
    "seconds",
    "known_cost_usd",
    "cost_complete",
    "plugin_source_sha256",
    "runner_source_sha256",
    "scenario_sha256",
    "after_assessment",
    "grader_error",
    "service_error",
    "identity_failure",
)
VERDICTS = {"PASS": CORRECT, "FAIL": INCORRECT}


class SummaryFile:
    """The batch summary `build_probe.py run` keeps beside its runs, merged under a lock because
    Inspect may finish several trials at once."""

    def __init__(self, path: Path, existing: list[dict[str, Any]]) -> None:
        self.path = path
        self.existing = existing
        self.results: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def add(self, entry: dict[str, Any]) -> None:
        async with self._lock:
            self.results.append(entry)
            layout.write_json(self.path, batches.merge_summary_entries(self.existing, self.results), ascii_only=True)


def _chosen(
    specs: list[dict[str, Any]], *, scenario: str, suite: str | None, frozen: selection.Selection | None
) -> list[dict[str, Any]]:
    """The scenarios this task runs. `all` means every supported kind; an explicit scenario, suite or
    frozen selection that names an unsupported kind is refused rather than silently narrowed."""
    explicit = scenario != "all" or suite is not None or frozen is not None
    chosen = frozen.scenarios if frozen is not None else specs
    if scenario != "all":
        chosen = [spec for spec in chosen if spec["id"] == scenario]
        if not chosen:
            raise ValueError(f"no scenario named {scenario!r}")
    if suite is not None:
        members = suites.load_suites(ROOT).get(suite)
        if members is None:
            raise ValueError(f"no suite named {suite!r}; `python evals/catalog.py suites` lists them")
        chosen = [spec for spec in chosen if spec["id"] in set(members["native_scenarios"])]
        if not chosen:
            raise ValueError(f"suite {suite!r} selects no native scenario")
    unsupported = [
        f"{spec['id']} ({scenarios.scenario_kind(spec)})"
        for spec in chosen
        if scenarios.scenario_kind(spec) not in SUPPORTED_KINDS
    ]
    if explicit and unsupported:
        raise ValueError(
            "only routing and contract scenarios run under Inspect in this cut; run these with "
            "build_probe.py: " + ", ".join(unsupported)
        )
    return [spec for spec in chosen if scenarios.scenario_kind(spec) in SUPPORTED_KINDS]


class BatchState:
    """What the native batch loop carries between trials: one trial at a time, a batch-wide stop,
    and the scenarios whose grading machinery failed."""

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.stopped: str | None = None
        self.machinery_stopped: dict[str, str] = {}


@solver
def native_trial(
    settings: native_trials.BatchSettings,
    specs: dict[str, dict[str, Any]],
    run_offset: int,
    summary: SummaryFile,
    batch: BatchState,
) -> Solver:
    """Run the native trial for this sample's scenario in this epoch's slot and keep its summary."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        spec = specs[str(state.sample_id)]
        run_number = run_offset + state.epoch
        # Trials run one at a time whatever --max-samples says: the judge's spend accumulator is
        # process-wide and run_trial drains it after grading, so overlapping trials would book one
        # trial's judge calls to another. Under the same lock the native batch's stop rules apply
        # before a trial starts: an identity failure or a failed environment cleanup stopped the
        # batch, and a scenario whose grading machinery failed is not run again. AuthUnavailable and
        # MeasuredInputRefused propagate: Inspect records the sample error and, with its default
        # fail_on_error, stops the eval, as the native batch stops.
        async with batch.lock:
            if batch.stopped:
                raise RuntimeError(f"native batch stopped: {batch.stopped}")
            reason = batch.machinery_stopped.get(spec["id"])
            if reason:
                state.store.set("native_skipped", f"grading machinery failed: {reason}")
                return state
            result = await asyncio.to_thread(native_trials.run_trial, spec, run_number=run_number, settings=settings)
            await summary.add(result)
            machinery = result.get("grader_error") or result.get("service_error")
            if machinery:
                batch.machinery_stopped[spec["id"]] = str(machinery)
            batch.stopped = native_cli._stop_after(result, None)
        state.store.set("native_summary", result)
        models = result.get("models") or []
        state.output = ModelOutput.from_content(
            model=str(models[0]) if models else "none",
            content=f"{result['status']} {result.get('passed')}/{result.get('total')}",
        )
        return state

    return solve


@scorer(metrics=[accuracy(), stderr()])
def native_verdict() -> Scorer:
    """The verdict the native trial returned: PASS is correct, FAIL incorrect, INCONCLUSIVE no answer."""

    async def score(state: TaskState, target: Target) -> Score:
        skipped = state.store.get("native_skipped")
        if skipped:
            return Score(value=NOANSWER, answer=None, explanation=f"not run: {skipped}")
        result = state.store.get("native_summary")
        if not isinstance(result, dict):
            return Score(value=NOANSWER, answer=None, explanation="the native trial did not run")
        status = str(result.get("status"))
        explanation = next(
            (
                str(result[key])
                for key in ("identity_failure", "grader_error", "service_error", "after_assessment")
                if result.get(key)
            ),
            f"{result.get('passed')}/{result.get('total')} expectations met",
        )
        return Score(
            value=VERDICTS.get(status, NOANSWER),
            answer=status,
            explanation=explanation,
            metadata={key: result.get(key) for key in SUMMARY_KEYS if key in result},
        )

    return score


@task
def native_scenarios(
    label: str | None = None,
    out: str | None = None,
    scenario: str = "all",
    suite: str | None = None,
    selection_file: str | None = None,
    claude_model: str | None = None,
    trials: int | None = None,
    run_offset: int = 0,
    timeout: int = native_cli.DEFAULT_TIMEOUT,
    judge_calibration: str | None = None,
    executable: str | None = None,
    plugin_root: str | None = None,
    max_invocation_usd: float | None = None,
    keep_workspace: bool = False,
    overwrite: bool = False,
    expect_plugin_digest: str | None = None,
    docker: str = "docker",
) -> Task:
    """Native routing and contract scenarios under Inspect; `-T` options mirror `build_probe.py run`."""
    if not label or not out:
        raise ValueError("-T label=... and -T out=... are required, as --label and --out are for build_probe.py run")
    if run_offset < 0 or (trials is not None and trials < 1):
        raise ValueError("run_offset must be at least 0 and trials at least 1")
    root = Path(plugin_root).resolve() if plugin_root else ROOT
    out_dir = Path(out).resolve()
    specs = scenarios.load_all_scenarios()
    frozen = selection.load(Path(selection_file), specs) if selection_file else None
    chosen = _chosen(specs, scenario=scenario, suite=suite, frozen=frozen)
    epochs = trials or 1
    if frozen is not None:
        epochs = selection.trial_count(frozen, run_offset, trials)

    # The native preflight: judge binding for rubric scenarios, candidate provenance, the runtime's
    # identity and the unelevated-account rule, printed as the native batch prints them.
    args = argparse.Namespace(
        judge_calibration=Path(judge_calibration) if judge_calibration else None,
        plugin_root=root,
        executable=executable or os.environ.get("CLAUDE_BIN", "claude"),
        expect_plugin_digest=expect_plugin_digest,
    )
    prepared = native_cli._preflight(args, chosen)
    if isinstance(prepared, ExitCode):
        raise ValueError(f"the native preflight refused to start (exit {int(prepared)}); its reason is on stderr")
    judge_binding, provenance, runtime = prepared

    out_dir.mkdir(parents=True, exist_ok=True)
    if frozen is not None:
        selection.retain(out_dir, frozen)
    summary_path = out_dir / f"summary-{label}-{claude_model or 'default'}.json"
    existing = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else []
    replaced = {(spec["id"], label, run_offset + slot) for spec in chosen for slot in range(1, epochs + 1)}
    retained = [entry for entry in existing if not overwrite or layout.run_key(entry) not in replaced]
    problem = batches.batch_identity_problem(
        retained, chosen, provenance["plugin_source_sha256"], judge_binding, runtime
    )
    if problem:
        raise ValueError(f"existing trials under this label cannot pool with this batch: {problem}")
    selected_ids = {spec["id"] for spec in chosen}
    failed = next(
        (
            entry["identity_failure"]
            for entry in retained
            if entry.get("scenario") in selected_ids and entry.get("identity_failure")
        ),
        None,
    )
    if failed:
        # WP-02's rule, as the native batch applies it: an append to the label must not run past one.
        raise ValueError(f"an earlier trial failed its identity check: {failed}; overwrite that run or use a new label")

    settings = native_trials.BatchSettings(
        plugin_root=root,
        label=label,
        model=claude_model,
        out_dir=out_dir,
        timeout=timeout,
        executable=args.executable,
        keep_workspace=keep_workspace,
        overwrite=overwrite,
        docker=docker,
        expected_plugin_digest=provenance["plugin_source_sha256"],
        judge_binding=judge_binding,
        runtime=runtime,
        max_invocation_usd=max_invocation_usd,
        expected_case_digests=frozen.case_digests if frozen is not None else None,
    )
    samples = [
        Sample(
            id=spec["id"],
            input=str(spec["prompt"]),
            metadata={
                "kind": scenarios.scenario_kind(spec),
                "case_sha256": fingerprints.case_digest(spec),
                **{key: spec[key] for key in ("target", "agent", "skill") if key in spec},
            },
        )
        for spec in chosen
    ]
    return Task(
        dataset=MemoryDataset(samples, name=f"native-{label}"),
        solver=native_trial(
            settings,
            {spec["id"]: spec for spec in chosen},
            run_offset,
            SummaryFile(summary_path, existing),
            BatchState(),
        ),
        scorer=native_verdict(),
        epochs=epochs,
        name="native_scenarios",
        metadata={
            "label": label,
            "out": str(out_dir),
            "claude_model": claude_model,
            "timeout": timeout,
            "run_offset": run_offset,
            "plugin": provenance,
            "runtime": runtime,
            "judge_binding": judge_binding.metadata if judge_binding else None,
            "selection_file_sha256": frozen.file_sha256 if frozen is not None else None,
        },
    )
