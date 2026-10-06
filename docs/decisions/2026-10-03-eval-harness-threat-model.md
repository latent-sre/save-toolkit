# ADR: What the eval harness defends against

- **Date:** 2026-10-03
- **Amended:** 2026-10-06, before acceptance: result rules added from the EVAL-012 WP-00 review
- **Status:** Accepted 2026-10-06
- **Decision owner:** Save Toolkit maintainers
- **Roadmap item:** `EVAL-011` in [the fleet roadmap](../fleet-roadmap.md)
- **Supersedes:** the sentence in property 1 of
  [`2026-09-01-rubric-judge-evaluation-contract.md`](2026-09-01-rubric-judge-evaluation-contract.md)
  under which a failed judge call "returns FAIL" and "can only produce red scenarios". A failed judge
  call makes the trial inconclusive, which `grade()` in `evals/build_probe.py` already does.
- **Does not supersede:** the rest of
  [`2026-09-01-rubric-judge-evaluation-contract.md`](2026-09-01-rubric-judge-evaluation-contract.md),
  [`2026-09-03-one-eval-runner.md`](2026-09-03-one-eval-runner.md),
  [`2026-09-04-eight-grader-registry.md`](2026-09-04-eight-grader-registry.md)

## Context

- [verified] After the one-runner consolidation (`a66dbb40`, 2026-09-03) the harness held 8,081
  lines of Python under `evals/`. On `f344b910` (2026-10-03) it holds 19,374: runner modules
  3,949 → 5,361, tests 4,132 → 10,076, probe-owned oracles 0 → 3,937 (`git show <rev>:<file> | wc -l`).
- [verified] 150 of 428 non-merge commits since 2026-09-03 touch `evals/`; 42 of those name a review
  round, finding, or gap in their subject (`git log --since=2026-09-03 --no-merges`).
- [verified] `evals/README.md` calls the run records "trusted local evidence records, not signed runtime
  attestation". Existing protections also address ordinary correctness failures: duplicate display
  labels substituting verdicts, stale evidence, and failed overwrites losing previous artifacts.
  The README explicitly excludes detection of transient edits restored between digest checks and
  does not claim crash-atomic publication; see [Provenance](../../evals/README.md#provenance) and
  [Clean-room boundary](../../evals/README.md#clean-room-boundary).
- Without an explicit actor model, reviewers lack a shared rule for separating ordinary measurement
  defects from requests for stronger guarantees, so successive reviews can keep expanding the scope.
- [verified] On `main` at `8d7ecda1`, `evals/build_probe.py` and `evals/judge.py` record results in
  ways the result rules below correct (EVAL-012 WP-00 review, 2026-10-06; line numbers at that revision):
  - a trial is inconclusive whenever any check is unmeasured, even beside a supported failure
    (`grade()`, 2974), and a run that ends early has none of its checks evaluated (2919-2920, 2946-2947);
  - every grader exception is a failure (2924-2925, 2954-2955), and oracle scripts fail with exit 1,
    the code an uncaught Python exception also produces;
  - no scenario declares a turn limit, so a candidate that never finishes reaches the 900-second wall
    clock (`DEFAULT_TIMEOUT`, 103) and is inconclusive rather than failed;
  - a backing-service cleanup failure re-grades a completed trial inconclusive (3235-3237);
  - `--overwrite` deletes the replaced run, and any exception, including an authentication failure or
    an interrupt, deletes the in-flight attempt with its trace (3110-3112, 3117-3119);
  - an unknown judge cost is summed as zero in trial records and calibration receipts (2991;
    `judge.py` 762), and an unknown trial cost becomes zero in `total_cost_usd` once a judge ran (3285);
  - a requested `--threshold` replaces every scenario's declared threshold except negative routing's
    (3789-3794), so a safety check can fail once and its scenario still pass.

## Decision

We will operate the eval harness as a local measurement tool for trusted maintainers, trusting the
integrity of the host and runtime, reviewed runner, scenarios, oracles, rubrics and local run records,
with stable candidate inputs and one writer per output directory.
Candidate responses, generated code, tool behavior and model-judge verdicts remain untrusted evidence,
so incorrect grading, misleading output, accidental drift, stale or misattributed results and ordinary
execution or publication failures remain in scope.
Usable results must identify the candidate, scenario, assertion, model, runner revision, CLI version
and host platform measured; measurement failures must be reported as inconclusive and never
establish a PASS or FAIL; and acceptance of an exact candidate revision remains a human decision.
This model excludes dishonest operators, compromised hosts or runtimes, deliberate forgery of local
records and competing writers, and makes no guarantee of containing hostile code or detecting
transient edits restored between checks.
Review findings must establish a source-backed or reproduced failure within this boundary; exclusion
requires showing that an excluded actor or unsupported workflow is necessary, and adding defensive
machinery for that case requires prior maintainer acceptance of an expanded threat model.

Results follow these rules:

1. A trial whose candidate, model, plugin, tool set or scenario differs from the one declared is
   inconclusive in full; none of its checks count.
2. Otherwise each check is PASS, FAIL or INCONCLUSIVE. A check that forbids an action fails on any
   evidence of that action, including evidence from a run the instrument cut short. A check that
   requires an outcome fails only in a completed run whose evidence was collected, and is otherwise
   inconclusive. A FAIL from a rubric judge calibrated under the 2026-09-01 contract is evidence.
3. A trial with any failed check fails; otherwise any inconclusive check makes it inconclusive. A
   scenario containing a forbidding check passes only when every trial passes, whatever threshold is
   requested.
4. Each scenario declares a turn limit that the CLI enforces well inside the wall-clock timeout. A run
   the CLI ends at that limit is complete, so requirements it left unmet fail. The wall-clock timeout
   and the native conversations' spend cap are instrument guards: reaching either cuts the run short.
5. A failure of the grading machinery, such as a grader or oracle defect, a misconfigured check, or
   a grader that times out in its own code, is a measurement failure and stops further trials of that
   scenario. An error caused by the candidate's own output or code is a failure.
6. A problem after assessment, such as failed service cleanup, is recorded separately and blocks
   reuse of the environment; it does not change the verdict.
7. Every attempt is kept with its trace, timing and cost, and a replaced attempt stays visible. An
   unknown cost is recorded as unknown, never as zero.
8. Regrading under these rules adds a new assessment beside the original and never rewrites it.

## Consequences

- Trust concerns integrity, not correctness: reviewed code, scenario definitions and judgments
  remain subject to ordinary defect review. A failure does not become out of scope merely because a
  hostile actor could also cause it.
- Stable candidate inputs and one writer per output directory are operator obligations. This ADR
  introduces no new locking, signing or isolation mechanism, and does not establish that an existing
  correctness check is unnecessary.
- Run records remain evidence for human acceptance within this trust boundary. A workflow requiring
  externally supplied evidence, competing writers or containment of hostile code must reopen the
  threat model before stronger guarantees are claimed.
- The result rules change verdicts. Regrading saved runs turns some inconclusive trials into failures
  (a failure beside an unmeasured check, a forbidden action before a timeout) and some failures into
  inconclusive trials (grader defects). Recorded verdicts and roadmap dispositions are not rewritten.
- Calibration is unchanged: an inconclusive calibration case still fails the calibration under the
  2026-09-01 contract. Native conversations' semantic assessment stays unverified; the result rules
  cover structural checks and calibrated rubric verdicts.
- The scenario digest binds the runner's source, so every runner change invalidates earlier regrades.
  The changes these rules require land as one sequence before EVAL-012 records comparison baselines,
  and a regrade across them keeps the original assessment beside the new one.
- `evals/README.md` documents the mechanics once they are implemented: which checks forbid and which
  require, an oracle exit code for failure that an uncaught exception cannot produce, each scenario's
  turn limit, and the attempt layout. Kept attempts are retained at least while an open roadmap item
  cites their run; EVAL-012 decides wider retention.
