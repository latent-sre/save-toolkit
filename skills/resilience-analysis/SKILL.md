---
name: resilience-analysis
description: >-
  Analyze failure propagation and design service resilience using source, configuration, operational
  evidence, and explicit assumptions. Triggers: 'what happens if this dependency slows down',
  'find resilience weaknesses', 'design a safer recovery path'. Covers capacity under failure,
  partial completion, degraded behavior and recovery. Active incidents use incident-investigation;
  basic readiness checklists use service-lifecycle; change verdicts belong to reviewer.
argument-hint: "[service or design, user outcome, environment, evidence]"
---

# Resilience analysis

Produce a supported engineering decision about a service's failure behavior. Load `stack-profile`
for applicable ownership and platform constraints. This method grants no access, execution, design
approval, or change authority. Use available source and observations; an experiment remains proposed
until an authorized actor supplies results from an established verification environment.

## Establish the outcome and evidence

Name the critical user transaction or batch/data outcome, environment, relevant requirements and
scope. Use accepted SLOs, recovery objectives and constraints; missing targets remain unknown or
explicit proposals for the human owner. External practices are guidance, not company policy.

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

Use `[verified]`, `[sourced]`, `[unverified]` with their target, method and time; preserve
`[UNTRUSTED]` data through summaries. Inspect beyond missing pattern names: no circuit breaker is
not a defect when other controls meet the requirement. No observed incident is not proof of resilience.
Allow no material finding within the inspected scope and retain coverage gaps.

Prioritize user impact, plausible exposure, recovery difficulty, uncertainty and engineering cost.
State why the proposed work outranks alternatives; avoid invented probability scores. A missing
required verification can matter urgently without proving that recovery will fail.

## Engineer the improvement and proof

Compare the smallest effective change with existing controls and consequential alternatives. Specify
the mechanism it changes, compatibility, degraded behavior, operational burden, recovery, owner and
acceptance criteria. Load `eng-ladder` for consequential shared-contract decisions. Implementation,
independent change review and live execution retain their existing owners.

For calculations, show units, measured versus assumed inputs, the equation, uncertainty and validity
conditions. Account for shared demand and failure capacity. Use existing permitted calculators when
available; no tool capability may be invented. A model estimate is not measured load-test evidence.

Verification names the target/version, stimulus, expected user and resource behavior, discriminating
measurements, bounds/stop conditions, and recovery checks. Preserve actual results separately from
the proposed test. Assess findings and coverage, not a blanket reliability score; test passes do not
approve a deployment. See [worked contrasts](references/worked-contrasts.md) for supported risks,
effective controls and missing evidence. Read [sources](references/sources.md) when checking a
practice's provenance or adapting this method.
