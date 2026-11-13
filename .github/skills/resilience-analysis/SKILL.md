---
name: resilience-analysis
description: >-
  Analyze failure propagation and design service resilience using source, configuration, operational
  evidence, and explicit assumptions. Triggers: 'what happens if this dependency slows down',
  'find resilience weaknesses', 'design a safer recovery path'. Covers capacity under failure,
  partial completion, degraded behavior, recovery, and existing service readiness. Active incidents
  use incident-investigation; change verdicts belong to reviewer.
argument-hint: "[service or design, user outcome, environment, evidence]"
---

# Resilience analysis

Load `stack-profile` for applicable ownership and platform constraints. This method grants no access,
execution, design approval, or change authority; an experiment remains proposed until an authorized
actor supplies results from an established verification environment.

## Establish the outcome and evidence

Name the critical user transaction or batch/data outcome, environment, relevant requirements and
scope. Use accepted SLOs, recovery objectives and constraints; missing targets remain unknown or
explicit proposals for the human owner.

Compare intended behavior (design/runbook), implemented behavior (effective code/configuration and
tests), and observed behavior (targeted telemetry or exercise results). Bind each to its revision,
deployment and time. Conflicting or stale records are leads to reconcile, not permission to choose
the convenient one. Source-only work can establish a conditional risk, not current production impact.

## Trace and challenge a failure path

1. Follow the user and data paths, including asynchronous work, shared resources and external
   dependencies. Inspect actual callers and configuration overrides, not just definitions.
2. Select credible failure or saturation conditions. For the relevant workload read
   [failure scenarios](references/failure-scenarios.md); do not apply every scenario to every service.
3. Trace **trigger -> component behavior -> propagation -> user effect -> protection -> recovery**.
   Record the existing controls and seek counter-evidence: overall deadlines, cancellation,
   admission limits, replay/deduplication, failover capacity, or a deliberately accepted degraded mode.
   For retrying code, trace which returns or handled exceptions reach another call and which
   exceptions exit. Count total calls separately from retries; carry these paths into the assessment.
4. Choose the smallest observation or controlled experiment that distinguishes the remaining
   explanations. An inaccessible source or failed query leaves a gap. Do not claim an alternative
   ruled out because it was not observed, nor trigger a production fault to demonstrate a risk.
5. Assess normal, degraded, overloaded and recovering behavior where applicable. A successful
   restart, cleared alert, completed backup or reverted commit does not by itself prove user recovery
   or data integrity. Use `database-reliability` for data and restore mechanics and `root-cause` for
   diagnosing an observed failure.

## Substantiate and prioritize

A material finding needs the outcome/requirement, reachable trigger and mechanism, evidence,
controls checked, consequence and a useful next action. Classify the result separately from its
evidence label:

| Result | What it establishes |
|---|---|
| Observed defect | Direct or supplied evidence demonstrates incorrect behavior under stated conditions |
| Supported design risk | A credible conditional failure path is established; occurrence and frequency may be unknown |
| Verification gap | An important claim lacks adequate evidence; this does not prove the control is absent |
| Improvement opportunity | A supported benefit may justify work without a demonstrated defect |

Use `[verified]`, `[sourced]`, `[unverified]` with their target, method and time. Inspect beyond
missing pattern names: no circuit breaker is not a defect when other controls meet the requirement.
No observed incident is not proof of resilience. Allow no material finding within the inspected
scope and retain coverage gaps.

State why the proposed work outranks alternatives. A missing required verification can matter
urgently without proving that recovery will fail.

## Existing-service readiness

For a general readiness audit, inspect each applicable surface and report it as passed, a finding,
or a gap, with evidence and its age: owner and on-call path; runtime and health check; deploy and
exact rollback path; telemetry arrival; SLI/SLO and paging alerts with runbook links; runbook and
service record; critical dependencies, limits and headroom; backup scope with a dated restore
rehearsal. Load the owning skill only for the surface you are on. A readiness gap needs the surface,
the evidence inspected and the consequence, not a failure path. A control present but unrecorded is
a documentation gap; absent from both is a readiness gap. Then trace failure paths for the surfaces
that matter. An audit changes nothing and approves nothing.

## Engineer the improvement and proof

Compare the smallest effective change with existing controls and consequential alternatives. Specify
the mechanism it changes, compatibility, degraded behavior, operational burden, recovery, owner and
acceptance criteria. Return consequential shared-contract decisions for `principal-engineer`. Implementation,
independent change review and live execution retain their existing owners.

Include these elements within the caller's permitted sections or fields when their condition applies:

- For a retrying path, **Retry paths:** the condition for another call and the exit paths.
  When client behavior is unknown, explain conditionally: a false return may permit another call
  if the retry condition and budget allow;
  an uncaught exception exits the path; a caught exception depends on its handler. Which behavior a
  timeout produces stays unknown until source or observations establish it.
- For retry timing, **Retry-count basis:** the source wording and whether it establishes maximum
  total calls or retries after the initial call. If that meaning is unresolved, state each compatible
  total-call count as an interpretation; do not label one selected count as sourced. Keep these
  alternatives beside every derived sum and later reuse until code or target-bound evidence resolves them.
- For a numeric timing or capacity claim, **Timing and capacity basis:** the equation and units,
  with measured and assumed inputs separated. For retry timing, use the retry-count basis, requested versus
  enforced timeout, backoff, cancellation and slot release.
  A timeout sum alone bounds neither elapsed time nor occupancy. A throughput estimate from slots
  needs actual or explicitly hypothetical mean slot residence and capacity after shared demand;
  a maximum duration alone supplies neither a mean nor a throughput ceiling.

Carry the conditions beside every reused number in recommendations, tables and proposed checks.
An earlier caveat does not turn conditional arithmetic into a worst case or capacity limit later.
When supplied evidence already establishes an overall deadline, preserve that scope and examine
enforcement or release gaps rather than reopening per-attempt scope.
Reconcile a helper's calculation with its source before endorsing the summary: source-reported
inputs are sourced; the derived number and its assumptions remain a separate calculation.
Use existing permitted calculators when available; no tool capability may be invented. A model
estimate is not measured load-test evidence.
A concurrency limit protects shared capacity only if admission or waiting does not retain the
slots being reserved.

Verification names the target/version, stimulus, expected user and resource behavior, discriminating
measurements, bounds/stop conditions, and recovery checks. To verify an admission or isolation control,
drive arrivals above completion capacity until its limit and overflow path are exercised, while
protected work runs concurrently. Count active work, permit waiters and retries in shared-slot
occupancy; representative demand alone may never exercise the protection. Preserve actual results
separately from the proposed test. Assess findings and coverage, not a blanket reliability score; test passes do not
approve a deployment. See [worked contrasts](references/worked-contrasts.md) for supported risks,
effective controls and missing evidence. External practices, including Google SRE guidance on
non-abstract design, cascading failures, reliability testing and SLOs, are guidance, not company
policy; check platform documentation for version-specific mechanisms.
