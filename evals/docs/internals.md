# Evaluation runner internals

[Evaluation home](../README.md) · [Verification policy](../../CONTRIBUTING.md#3-verify-in-proportion-to-the-change)

## Runner layout

The [frontend trial verification patch](../fixtures/frontend-craft-verification/README.md)
preserves the private craft trial's verification wiring without shipping the prototype.

`build_probe.py` is only the command line; the code is in [`probe/`](../probe), one module per job (its
[`__init__.py`](../probe/__init__.py) lists them), and tests and tools import those modules directly:

- **Typed results.** A check returns an `Outcome` that states whether its evidence measured the
  candidate (`PASS`, `FAIL` or `INCONCLUSIVE`) and whether a failure was the grading machinery's. It
  is a frozen dataclass whose equality and hash include the state, evidence and both classification
  flags. Unpacking and indexing retain the `(passed, evidence)` reading API; a plain tuple is not
  equal to an outcome. Saved grades keep their text representation; only `Outcome.read` interprets it.
- **Declared checks.** Each check in [`probe/checking.py`](../probe/checking.py) is registered with
  `@declare`: whether it forbids, requires or both, and the evidence it reads. Polarity,
  regradability and the cut-short rules are read from those declarations.
- **One grading loop.** `assessment.assess` grades a live trial and a regrade alike; a regrade
  supplies the saved verdicts it keeps. A result rule therefore changes in one place.
- **A published record contract.** `records.RecordV1` validates each `record.json` strictly, as
  the JSON its readers parse, on the first write and on every later change, and
  [`eval-record-v1.schema.json`](../../docs/fleet-evaluation/eval-record-v1.schema.json) is generated
  from it by `build_probe.py schema --out ...`; a test fails when the two differ.
- **Static checks.** [`pyproject.toml`](../../pyproject.toml) runs Ruff's lint rules over the runner,
  `graders.py`, `inspect_pilot.py` and the `test_*.py` files, Ruff's formatter over all of them but
  the tests, which keep their compact hand layout, and strict mypy over the same code without the
  tests; CI runs them after the component tests. `python -m ruff check`,
  `python -m ruff format --check` and `python -m mypy` reproduce them locally. A separate
  `python -m ruff check --isolated --select E9,F63,F7,F82 evals/judge.py evals/clean_room.py evals/oracles`
  checks syntax, invalid control flow and undefined names in those byte-bound files. Their existing
  layouts and incremental typing remain: whole-file formatting or typing migrations would replace
  calibration and case identities without establishing a behavioral improvement.

A function is patched in the module that defines it, such as `probe.trials.run_trial`: every other
module calls it through that module, so one patch reaches every caller, and a test enforces it. A
class or constant is bound by name in each module that imports it, so a patch must reach each of
them. `build_probe` holds no runner name, so a patch aimed at it fails instead of leaving real code
running.
## Provenance

Every run records the plugin root's commit, plugin-input dirty state, and a path-bound source digest
over `agents/`, `skills/`, `commands/`, `hooks/`, the manifest, and the guard scripts
(`provenance.json`, the trace summary, the summary line), the path of the image of those inputs the
trial was served (`plugin_served_from`), plus the requested and resolved model,
trials, timeout, per-trial duration, cost, and the exact argv. Each run also records `runtime`: the
CLI's own `--version` line (`null` when it cannot report one), the host's system, release and
machine, and OS-observed hostname, account ID, elevation and observation source. Windows uses the
process token; POSIX uses the effective UID, where elevation means UID 0 rather than a capabilities
audit. The batch measures this once; `--regrade` keeps the recorded value. Every attempted CLI
invocation writes `invocation.json` before launch, with argv and workspace, and records launch,
exit and boundary results afterward; resumed calls retain their own file under `followup/`.
On a CLI timeout or Python interruption (including Ctrl-C), the runner terminates its POSIX process
group or uses Windows [`taskkill /T /F`](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/taskkill)
before reaping the parent and grading partial evidence. Tree cleanup failures abort the attempt;
they are not recorded as ordinary trial timeouts. This covers children that remain in the invocation's
process tree, not deliberately detached processes or an abrupt kill of the runner itself.
Identity hashes say two runs
measured the same plugin; they do not say the runs measured it the same way — **pin `--model` and
`--timeout` for any numbers you intend to diff, and compare runs only within one CLI version.** A
batch refuses to pool trials whose recorded CLI version, host, account or privilege differ. Legacy
v1 records without account evidence remain readable, but unknown identity never establishes a
matching host/account and does not pool. Comparison reports name that gap while preserving each
record's verdict. `provenance.json` also names the runner:
`runner_commit`, `runner_source_dirty` and `runner_source_sha256`, so a run graded with
`--plugin-root` on another checkout still says which runner graded it. The measured guard scripts
include `readonly-guard-hook.ps1`, which `hooks/hooks.json` runs for PowerShell. A measured input that
is a link or junction, its target present or not, or a required one that is missing, leaves the
candidate unidentified: the batch refuses to run (exit 3), and a trial that finds one stops the batch.
An optional guard script that is absent is measured as absent.
Hashing and image staging use the same Git inventory: tracked files and non-ignored untracked
files in the measured paths. Ignored untracked residue enters neither; tracked files stay measured
even when a current ignore rule matches them. Ordinary untracked inputs
remain measured and dirty. An explicitly named hook that Git ignores is refused rather than
silently omitted, and an unreadable inventory cannot identify a clean candidate.

Cost is the CLI's reported list-price estimate, not a subscription bill; a missing, negative, infinite
or NaN figure is unknown. `timing.json` and summary
rows give `total_cost_usd` only when the trial and every judge call are priced; otherwise it is
`null`, with `known_cost_usd` and `cost_complete: false` beside it, and a cached verdict counts as a
known zero, and live and cached judge calls are counted apart. `--max-batch-usd USD` (finite and
above 0) stops scheduling once the batch's known spend reaches `USD`, or as soon as any attempt's
cost is unknown, because an unknown cost cannot be held to a cap. That spend counts, once each, the
rows of this label and model's summary for the selected scenarios, including those `--overwrite`
replaces, and the superseded and incomplete attempts kept under the label's `attempts/`, which every
model of the label shares. An attempt that raised records what it is known to have cost: nothing
when the CLI never started, else what its partial trace reports, which is unknown without the
trace's result event. One attempt of unknown cost, such as a wall-clock timeout, therefore blocks
capped runs of its scenario under that label; run it uncapped or under a new label. A batch whose
CLI does not report its version is refused before any model call. Judge calibration
receipts still sum an unpriced call as zero: changing `judge.py` invalidates every receipt, so that
fix waits for the next recalibration.

Each graded attempt also writes `record.json`, the [v1 result record](../../docs/fleet-evaluation/contracts.md#result-record-v1)
that the comparison report reads: format and version, a `case_sha256` over the scenario, oracles and
rubric definitions alone (unlike `scenario_sha256`, it survives a runner edit), candidate and runner
identity, run conditions, attempt number and UTC times, how the run ended (an attempt that raised keeps a partial record with
`run_end: incomplete` and no verdict), each check's kind (forbids, requires, or both), state,
reason when INCONCLUSIVE, and truncation flag (evidence is cut at 600 characters and flagged), the
verdict, the cost, and evidence paths relative to the attempt folder. A record the contract refuses
is not written, and the run is still published with its verdict: the record only maps facts the
attempt's files keep, the summary row carries `record_problem`, and the batch goes on. Attempt folders are created with a plain `mkdir`, so
they inherit `.eval-runs/` permissions; `tempfile.mkdtemp` made them readable only by the account
that ran them on Windows.

Machine records retain the complete candidate digest and a scenario digest covering the spec, its
referenced oracle files, the explicit judge binding when used, and the rubric definitions the judge actually consumes. The judge caches
rubrics on first load for the process; file edits take effect in a new process. The digest uses those
same cached definitions. Appending requires candidate and scenario identities to match the existing
batch before any model call. Scenario inputs are checked again before and after grading;
a change in the effective definitions or oracle bytes invalidates the trial. Regrade identifies each assertion by its scenario digest and
position and retains live-judge/workspace verdicts from the live grade (`grading.original.json` for a
run an older runner regraded in place); duplicate display
labels cannot substitute one verdict for another. Legacy records without identities, changed
scenarios, and missing original assertions are INCONCLUSIVE and require a fresh trial. Regrade does
not call a judge or recover workspace evidence that was never recorded. Rubric regrades use the
immutable binding embedded in the original live grade, without reopening a current receipt or
recalibrating. Missing binding evidence or a changed judged response makes the regrade INCONCLUSIVE. A regrade voids a run only when its live grade
did: the run-level reason that grade records as `void`, or, in a grade from before `void` was
recorded, a reason every saved check carries. One check's own INCONCLUSIVE leaves the others
measured, so a supported FAIL beside it stands (result rules 1 and 3). Without the raw trace, a regrade re-measures
only what the trace summary records; an expectation that reads what only the raw trace held
(completion order, completed returns, reads, the plugin namespace) is INCONCLUSIVE on its own.
Tool-call counts regrade from a complete raw trace or validated recorded summary counts. Empty,
truncated or malformed traces cannot establish zero calls; missing or invalid summary counts stay
unknown. Observed calls can still establish a ceiling violation when the total is incomplete.
A legacy native timeout can recover as cut short only when its recorded
plugin root and digest still match and its raw invocation evidence establishes the profile and
session. The resulting forbidden-action failures remain visible.

The scenario digest also binds the evaluator implementation: `build_probe.py`, every module in
`probe/` (found by listing the package, so a new module is bound the moment it exists), `graders.py`,
`judge.py`, and `clean_room.py`, plus Python and PyYAML versions. Start the runner in a fresh process
from a stable checkout with the pinned dependencies. Source edits made after the identity is
captured abort grading/regrade and require a new process rather than assigning changed disk bytes to
already-imported code. The digest is conservative: even an
unrelated evaluator edit invalidates prior scenario identities. In-process code replacement is
unsupported; this is provenance for the trusted runner, not attestation of its Python environment.

Because of that, `regrade` cannot show what a runner edit changes. `rescore ITERATION_DIR --out
DIR` grades every saved run with the current runner into the new directory `DIR`, never writing the
saved runs, and grades across a runner change by finding kept verdicts under the saved identity;
those runs are marked `identity_relaxed`. A kept rubric judgment whose judge code or configuration
has changed since the run is INCONCLUSIVE on its own; the checks the saved trace re-measures keep
their verdicts, so a supported FAIL beside it still fails. `DIR/rescore.json` records the runner identity, each
run's saved and rescored verdicts, unreadable runs, and scenarios or runs it skipped. A rescore is a
comparison, never a verdict: its differences from the saved verdicts also include scenario edits made
since the run. To isolate a runner change, rescore the same runs with the base and candidate
checkouts and run `diff BASE_DIR CANDIDATE_DIR`, which lists every run and check whose
verdict differs and exits 1 when any does. Each runner commit explains every line it prints in its
commit message.

A regrade never rewrites what a run recorded (threat-model ADR result rule 8): it writes
`assessments/<k>/grading.json` and that assessment's trace summary beside the run, lists the revision
in the attempt's `record.json` under `assessments`, and writes its rows to `regrade-<UTC>.json` in the
iteration directory. `grading.json`, the run's trace summary and the batch `summary-*.json` files keep
their recorded verdicts. Run slots are shared across models under each label; prefer separate labels
for separate model/candidate comparisons. The regrade's exit code pools runs only as one batch could:
each label, resolved model, candidate digest, CLI version, host/account/privilege and scenario identity is
aggregated apart, and a run whose model, candidate digest, CLI version or host/account evidence is unknown pools with
nothing and counts as INCONCLUSIVE.

`--overwrite` prepares a complete replacement in a hidden sibling attempt directory. The previous
run remains intact through execution, grading, artifact writes, and workspace cleanup. Publication
renames the previous slot to a backup and restores it if the replacement rename fails; only a
published attempt reports its summary. No attempt is deleted: the replaced run moves to
`<label>/attempts/run-N/<k>/` as `superseded`, and an attempt that raised before publishing (an
interrupt, an authentication failure, a refused preflight) moves there as `incomplete` with the
reason. Each attempt's `attempt.json` records its number, state and time, and the summary row carries
the published attempt's number, so a re-run is never invisible. If moving the backup fails, it is
retained beside the slot with a warning. If the process stops between publication renames, inspect
the `.run-N-previous-*` sibling before restoring it; a two-directory rename is not a crash-atomic
filesystem transaction. An authentication failure stops the batch and exits 4, distinct from FAIL (1)
and INCONCLUSIVE (2), whatever else the batch holds: rows an `--overwrite` had not replaced yet
cannot change that exit or its reason. It prints the stop line and no verdict, since the resumed
batch decides it; the stop line's `unfixed_by_resume` names an identity or model problem that
resuming would not fix. Each completed trial still prints its summary line as it publishes, and
keeps its row in `summary-*.json`.
## Clean-room boundary

Every trial points `CLAUDE_CONFIG_DIR` at a temporary directory holding only the selected Claude
credential, rebuilds the child environment from an allowlist so unrelated host tokens cannot reach
model-invoked tools, and runs from a temporary git root outside this repository so the repo's own
`AGENTS.md`, `CLAUDE.md`, and local settings cannot teach a routing trial the answer. `--plugin-dir`
and `--add-dir` name an image of the measured plugin inputs, staged beside that git root and
recorded as `plugin_served_from`, never the checkout itself: a session can read the shipped skills
but not this repository's evals, docs or history (`EVAL-014`); a regrade restages the image at the
recorded path while it runs. The runner checks the checkout's digest before execution, after the
model returns, and after plugin-dependent grading, and the image's beside it;
a change makes the trial INCONCLUSIVE, and a mismatch with the batch digest prevents the model call.
These checks detect persistent changes, not a transient edit restored between checks; keep the
candidate checkout stable for the batch. Strict MCP mode supplies an explicit empty server set.
Runtime init must report exactly one plugin with that image's identity and
exactly the requested tool inventory, and the trace must name the model it ran on; a missing or
foreign tool, an MCP server, a trace that names no model, an error result, a
nonzero exit, or — where reads were granted — a successful read outside the workspace and plugin
image makes the trial **INCONCLUSIVE**, never a verdict. An auth failure aborts the batch.

CLI children and grading/oracle commands receive workspace-owned `TMP`, `TEMP` and `TMPDIR`.
Ordinary Python children suppress bytecode generation. Cleanup records `cleanup.json`, including
the workspace, explicit retention, removal result and problems; `--keep-workspace` records an
intentional retained workspace. A failed cleanup preserves an already measured verdict, records
the problem under `after_assessment`, and prevents the batch from reusing the environment. These
environment settings govern cooperative temporary-file use, not arbitrary host writes.

Those run-level failures mark every check INCONCLUSIVE, so nothing observed under the wrong plugin,
model or tools counts. A trial whose identity is wrong — its tool inventory, plugin or model, or
plugin inputs that changed — also stops the batch, since every later trial would run as the same
wrong candidate: its summary row records `identity_failure`, and a later invocation of the label
schedules nothing until that run is replaced with `--overwrite` or a new label is used. The batch
then exits 2 unless a FAIL verdict decides it. A failure the candidate's own run causes, such as a
read outside the workspace or a refused command, voids only its trial, and a backing service that
never started stops only its scenario. A run cut short on the declared profile is different: after a timeout, a
missing result, an error result, a nonzero exit or the native spend cap, the partial trace must still
show the declared plugin, tools and read boundary, and for a native conversation its model, grants,
session and helper, and then a forbidding check whose violation is
already in it is FAIL, while one with no violation yet and every requiring check stay INCONCLUSIVE;
the grade records `run_end: cut_short` with `run_stop` (`wall_clock`, `no_result`, `error_result`,
`nonzero_exit` or `spend_guard`) so a regrade applies the same rule, a native invocation records
`cut_short` too, and a run voided at run level records `void`. A negative routing expectation fails
a cut-short run only when its forbidden target fired; an alternative that never fired stays
INCONCLUSIVE. Otherwise each check is PASS, FAIL or INCONCLUSIVE (its `state` in
`grading.json`), and a trial with any failed check is FAIL even when another check could not be
measured; that reason is kept as `unmeasured`. Without a failure, any unmeasured check makes the trial
INCONCLUSIVE, with the reason in `inconclusive`. A check that reports `instrument:` evidence could
not be measured, as when its backing service stops answering: it is INCONCLUSIVE and, like a grader crash, stops its scenario. A grader that raises, or a judge that could not judge, is a
measurement failure: its check is INCONCLUSIVE, the grade names it as `grader_error`, and the batch
runs no more trials of that scenario; a grader returns an error in the candidate's own output as a
FAIL. A `tool_call_count` with a positive minimum is both: on a run cut short, calls beyond its
maximum FAIL while a minimum not yet reached stays INCONCLUSIVE.
An unknown `fleet_grader` name is rejected by `--validate`. The supervised oracle protocol above
separates contract failures from machinery failures. Backing-service proxies stop admitting
requests and drain accepted requests before grading reads audit and service state; the backing
services remain available for the checks' direct reads. Unsettled service evidence is inconclusive
without erasing independent failures. Service JSON equality distinguishes booleans from numbers,
including nested values, while numeric `3` and `3.0` compare equal.
Every scenario must declare `max_turns` (1 to 500), passed to the CLI as `--max-turns`; a session the CLI
ends there is a completed run (`run_end: turn_limit`) whose unmet requirements fail. In a conversation
the limit covers all invocations: each resumed invocation gets only what prior invocations left,
a conversation that spends it ends without later messages, and a regrade refuses a saved conversation
that ran past it. Wall-clock and native CLI spend guards apply per invocation. These follow
the result rules of the accepted [threat-model ADR](../../docs/decisions/2026-10-03-eval-harness-threat-model.md).
The original 242-scenario sizing pass added 235 limits and preserved seven existing limits.
The new values are provisional offline budgets derived from saved counts and elapsed evidence,
with same-profile fallbacks and a 450-second sizing target within the 900-second wall-clock guard.
A slow individual tool or helper can still hit that guard. These limits do not establish live
completion or candidate uplift; the [EVAL-011 closeout](../../docs/reviews/2026-10-10-eval-011-closeout.md)
records their sizing and the cases whose budgets are below historical counts.

This is an evaluation boundary, **not an OS sandbox**. A build lane's Bash runs on the host with
network, and the credential copy sits where an unguarded tool could reach it (the probe scans
outputs for credential markers and warns). Under subscription login, Claude Code itself adds the
account email to the trial's context, even with `--setting-sources ""`; a trial that repeats it is
showing that injection, not a leak from the copied files. Use only reviewed, non-secret prompts, and keep raw
traces private: they carry complete prompts and responses, session IDs, and tool payloads. Artifacts
are written owner-only under `.eval-runs/`; quote the numbers a review depends on into that review
rather than publishing the batch.
