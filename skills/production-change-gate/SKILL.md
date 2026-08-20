---
name: production-change-gate
description: >-
  Authorize or block one exact production-facing action. Use when asked to approve a live command,
  workflow dispatch, configuration change, rollback, or destructive operation. Triggers: "authorize
  this production change", "can I run this command in prod", "review this rollback plan". Do not use
  for merge or release readiness, and never treat the request itself as approval.
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Production change gate

Lead with `APPROVED` or `BLOCKED`. The agent may classify, inspect evidence, and prepare a packet;
it never performs the live action. A named human release owner or separately approved protected
automation executes only the exact target and effect that were approved.

The checklist is a decision record, not enforcement. The load-bearing boundary must bind approval to
the actual effect: protected workflow/environment controls for automation, or an authenticated change
record plus least-privilege human execution for a manual action. Branch policy protects source review;
by itself it does not authorize a runtime change.

## Classify the effect

- **Tier 0 — observe:** no mutation.
- **Tier 1 — prepare:** create a plan, diff, artifact, or dry run without touching production.
- **Tier 2 — reversible live effect:** requires approval of the exact actor, target, action, verification,
  and rollback.
- **Tier 3 — destructive, data-bearing, or access-path effect:** requires Tier 2 evidence plus a proven
  restore/recovery path and an explicit acknowledgement of irreversible consequences.

A material change to any approved field re-enters the gate.

## Required evidence

- [ ] **Exact effect** — actor, target, command/diff/workflow ref and inputs, intended result, and every
      material side effect are shown.
- [ ] **Current readiness** — for a release, attach the reviewed SHA, immutable artifact, checks, and
      release-readiness packet. For an ad-hoc action, attach the reviewed plan/diff and mark artifact
      fields `N/A`.
- [ ] **Effect boundary** — prove the configured approval and bypass behavior on the mechanism that can
      cause the change. Record who can approve, whether self-review or administrator bypass is possible,
      and which credentials the executor receives.
- [ ] **Repository controls, when applicable** — inspect both classic branch protection and active
      repository ruleset or organization-rule evidence. A classic endpoint 404
      does not prove the branch is unprotected; it can also reflect missing access, and rules use a
      separate endpoint.
      Follow [GitHub change controls](./references/github-change-controls.md) for the current evidence
      shape.
- [ ] **Explicit approval** — an authorized human approved this exact effect, executor, target, and time.
      A task request, incident urgency, earlier approval, or approval of a different command is not this
      approval.
- [ ] **Blast radius and failure mode** — affected users, traffic, data, services, regions/spaces, and
      worst credible outcome are bounded.
- [ ] **Verification and abort** — predeclare success signals, observation window, abort thresholds, and
      the human who decides.
- [ ] **Rollback or recovery** — exact inverse or recovery steps, prerequisites, known-good state, owner,
      and evidence are attached. If the effect is irreversible, say so and require the Tier 3 recovery
      evidence instead of calling it reversible.
- [ ] **Timing and coordination** — freeze/window, load, dependencies, on-call, stakeholder notice, and
      conflicting changes are checked or marked `N/A` with a reason.

For a compact filled example, read [approval packet example](./references/approval-packet-example.md).

## Verdict

```text
production-change-gate: APPROVED | BLOCKED
Tier: <0|1|2|3>
Actor and authority: <human/protected automation — approval record — time>
Target and effect: <exact target — command/diff/workflow ref and inputs>
Blast radius: <scope — worst credible outcome>
Effect boundary: <environment/change-control evidence — bypass/self-review facts>
Verification/abort: <signals — window — thresholds — decision owner>
Rollback/recovery: <exact steps — known-good state — evidence — owner>
Blocking items: <each missing or failed predicate and what clears it>
```

## Emergency path

A declared incident may shorten coordination, never authority. Retain exact scope, named human
approval, effect-bound execution, verification, and rollback/recovery. Record the emergency decision
and reconcile the normal change record afterward. Tier 2/3 execution remains human- or protected-
automation-owned.

## Conditional references

| Need | Read |
|---|---|
| Verify GitHub branch/ruleset and environment controls | [GitHub change controls](./references/github-change-controls.md) |
| See the minimum complete approval-request shape | [Approval packet example](./references/approval-packet-example.md) |
