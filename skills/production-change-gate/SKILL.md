---
name: production-change-gate
description: >-
  Gate the path from code to production with one checklist per question: is this change ready to
  merge, is this build ready to ship, and may this exact action run against production. Records a
  human decision and never executes. Triggers: 'is this ready to merge', 'is this build ready to
  ship', 'can I run this cf command in prod', 'authorize this production change'. Not for code
  review itself (reviewer) or for incident mitigation advice (incident-investigation).
argument-hint: "[the change, build, or production action to gate]"
---

# Production change gate

Three questions, one gate. Each has its own checklist and verdict; a later question consumes the
earlier verdict as evidence and never re-runs it. The agent classifies, checks, and records. A human
release owner or separately approved protected automation executes; the agent never does, and no
approval changes that. The one exception is the invoked `observability-engineer`'s scoped Grafana
writes, governed by that agent's Change authority rule and the `grafana` operation procedures;
rule deletion and shared notification infrastructure remain on this gate.

> **The checklist is not the enforcement.** It records a human decision. The load-bearing control
> is the least-privilege production role or credential held by the named human or protected
> automation, and for a deployment the protected environment that gates the deployment credential.
> Branch protection protects source history; it is not a production boundary.

| The question | Read, then run | Verdict line |
|---|---|---|
| Is this change ready to merge? | [Merge readiness](./references/merge-readiness.md) | `gate: merge` · `PASS \| BLOCKED` |
| Is this build ready to ship to an environment? | [Release readiness](./references/release-readiness.md) | `gate: release` · `PASS \| BLOCKED` |
| May this exact action touch production now, or how should its execution result be recorded or reconciled? | [Production authorization](./references/production-authorization.md) | `gate: production` · `APPROVED \| BLOCKED` |

Read the matching checklist before evaluating that decision. A merge or release question loads only
its checklist and applicable supporting detail. Classifying or authorizing a production action, or
recording or reconciling its result, requires the production authorization reference first, including
when the incident fast path applies. A later gate consumes the earlier verdict as evidence.

## Merge or release verdict

```text
gate: merge | release
verdict: PASS | BLOCKED
Candidate commit ID: <exact commit | not applicable>   Artifact identity: <immutable digest or version | not applicable>
Blocking items: <the NOs, each with what clears it>   Waivers: <item, approving human, reason>
```

## Read only what the decision needs

| If the request involves | Read |
|---|---|
| Preparing a Tier 2 or 3 approval-request packet, or an explicit ask for the template | [Tier 2 approval example](./references/tier-2-approval-example.md) |
| A declared incident needing reversible Tier 0–2 mitigation, a bounded envelope, rollback to the live artifact, or post-incident reconciliation | [Incident fast path](./references/incident-fast-path.md) |
| Proving a release artifact is the immutable one that was tested | [Release artifact evidence](./references/release-artifact-evidence.md) |
| A `cf` state-changing command (restart, restage, scale, set-env, push, rollback) | Load `pcf-ops` and read its state-changing command effects reference for blast radius and for whether the action creates a new artifact |
