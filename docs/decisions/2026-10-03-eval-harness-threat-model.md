# ADR: What the eval harness defends against

- **Date:** 2026-10-03
- **Status:** Proposed
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
