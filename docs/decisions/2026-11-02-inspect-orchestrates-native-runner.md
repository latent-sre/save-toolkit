# Inspect AI orchestrates the native runner

- Date: 2026-11-02
- Status: accepted for implementation by the repository owner's instruction in the session that
  implemented it; the native runner remains the acceptance reference until the parity run in
  EVAL-016 is accepted
- Decision owner: repository owner
- Scope: narrows the Inspect role left open by [one eval runner](2026-09-03-one-eval-runner.md) and
  the evaluation specification's integrations clause; the rubric judge contract, the grader
  registry and the explicit native selections are unchanged

## Context

[sourced] The evaluation specification keeps the native Claude Code plugin run as the automated
reference (DEC-02), asks for "the smallest native/Inspect extension" compared against the native
path, and requires a replacement inventory and a rollback before native scheduling or lifecycle code
is removed. [verified] The existing Inspect pilot drives Inspect SWE's sandboxed Claude Code agent,
and that agent installs skills but loads no plugin, agent or hook, so it can only ever grade
artifacts. [verified] The native batch loop in `probe/cli.py` schedules trials serially, publishes
each attempt through `probe.trials.run_trial`, and aggregates per-scenario verdicts with thresholds;
the corpus holds 113 routing and 116 contract scenarios that need no fixture services, 175 build
probes and 18 native conversations.

[sourced] The owner chose: Inspect orchestrates the native runner rather than porting graders to
Inspect scorers or extending the sandbox pilot; routing and contract scenarios first; the new path
sits beside the native CLI until an owner-run paid comparison matches.

## Decision

We will add `evals/inspect_fleet.py`, an Inspect task whose dataset is the selected native
scenarios, whose solver calls the unchanged `probe.trials.run_trial` with the settings
`build_probe.py run` would build, and whose scorer reports the verdict the trial returned. Each
attempt is published under the iteration directory in the native layout, with the native record,
provenance, judge binding and batch summary file, so `build_probe.py regrade` and the saved-run
readers apply unchanged. The task runs with Inspect's `none` model: the Claude CLI authenticates
itself in the clean room.

The native preflight (judge binding, candidate provenance, runtime identity, the unelevated-account
rule) and the pooling check over existing rows run before the task starts. An explicit scenario,
suite or frozen selection that names a build probe or conversation is refused; `all` means every
routing and contract scenario. The module lives beside `probe/`, so the runner identity and every
saved run identity are unchanged.

`build_probe.py` remains the documented entry point and the acceptance reference. No native
scheduling code is removed by this decision. EVAL-016 runs one frozen selection through both paths
on the same model, CLI and host; only after that comparison is accepted does a follow-up decision
name what Inspect replaces, with the replacement inventory the specification requires.

## Consequences

Inspect's concurrency, sample limits, `.eval` log and viewer apply to fleet regressions today with
no change to what is measured. Grading parity is by construction and is tested offline by faking
`run_trial` where the native tests fake it. Operational parity (timeouts, cost accounting, host load
under parallel trials) is not established until EVAL-016, so the documented default is one sample
at a time.

Two paths publish into the same layout for the duration, which the specification allows only with
a named consumer and an end: the consumer is the parity comparison, the end is EVAL-016's
disposition. The native batch spend cap is not available through Inspect in this cut; the
per-invocation cap is. Inspect's accuracy metric averages trials and is not the per-scenario verdict
with thresholds, which stays with `regrade`.

What would show this decision was wrong: verdicts that differ between the two paths on the same
runs, Inspect's event loop or sample isolation interfering with the clean room, or a maintenance
cost in keeping the task's `-T` options aligned with the native flags. The rollback is the native
CLI, which this decision leaves untouched.

<!-- ADRs are append-only once accepted. Only the decision owner may amend an accepted ADR, adding a
     dated "Amended:" line that names the change. Anyone else writes a new ADR and marks this one
     "superseded by <YYYY-MM-DD>-<slug>". -->
