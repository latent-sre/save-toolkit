---
name: production-change-gate
description: >-
  Gate the path from code to production with one checklist per question: is this change ready to
  merge, is this build ready to ship, and may this exact action run against production. Records a
  human decision and never executes. Triggers: 'is this ready to merge', 'is this build ready to
  ship', 'can I run this cf command in prod', 'authorize this production change'. Not for code
  review itself (reviewer) or for choosing a mitigation during an incident (incident-command).
argument-hint: "[the change, build, or production action to gate]"
---

# Production change gate

Three questions, one gate. Each has its own checklist and verdict; a later question consumes the
earlier verdict as evidence and never re-runs it. The agent classifies, checks, and records. A human
release owner or separately approved protected automation executes; the agent never does, and no
approval changes that. The one exception in the fleet is `observability-engineer`'s Grafana
dashboard write, which its own agent body governs.

> **The checklist is not the enforcement.** It records a human decision. The load-bearing control
> is the least-privilege production role or credential held by the named human or protected
> automation, and for a deployment the protected environment that gates the deployment credential.
> Branch protection protects source history; it is not a production boundary.

| The question | Read, then run | Verdict line |
|---|---|---|
| Is this change ready to merge? | [Merge readiness](./references/merge-readiness.md) | `gate: merge` · `PASS \| BLOCKED` |
| Is this build ready to ship to an environment? | [Release readiness](./references/release-readiness.md) | `gate: release` · `PASS \| BLOCKED` |
| May this exact action touch production now? | Production authorization, below | `gate: production` · `APPROVED \| BLOCKED` |

Read only the row the question needs; the two references carry their full checklists.

## Production authorization

Classify first, then check only what the tier needs.

| Tier | Action | Who may proceed |
|---|---|---|
| 0 | Observe: reads, health checks, config validation, dry runs | The agent, reporting commands and evidence |
| 1 | Prepare: edit version-controlled config, docs, or an unapplied artifact | The agent, never applying it to a live target |
| 2 | Reversible live change | A human or protected automation, after explicit approval of the exact command shown |
| 3 | Destructive or access-path change: data deletion, storage or backup, credential or identity, DNS, firewall, VPN, proxy, remote access | As Tier 2 plus a proven backup or recovery path; stop until the named action and target are approved |

Approval covers only the command, target, and applying actor shown; a material change re-enters
the gate. During a declared incident the incident commander may approve a bounded envelope instead
(see the [incident fast path](./references/incident-fast-path.md)).

| Item | Passes when |
|---|---|
| Readiness evidence | A new-artifact deployment attaches the exact candidate commit's independent review, green checks, the release artifact, the `gate: release` PASS record, and the named production approver. A non-deployment action attaches the current command or diff and named approval instead. Rolling back to the previously live artifact reuses that artifact's records. |
| Execution boundary on | Evidence that the named human or protected automation, not the agent, holds the least-privilege role or credential for this exact action (for a deployment, the protected environment gating the credential). Naming an executor or promising not to act is not evidence; repository approval counts are not production authority. Deferred during a declared incident. |
| Approved | An authorized human approved this exact target, command or diff, applying actor, and time, with a `Valid until` UTC deadline and the change record where the process requires one (this team keeps them in BMC Remedy and Jira; name the system). |
| Binding current | Immediately before execution the executor confirms the approval has not expired and the current target, action, actor, and candidate or configuration identity match the approved record. Any mismatch is BLOCKED and re-enters. |
| Blast radius | Affected apps, routes, spaces, users or traffic share, and the worst credible failure are recorded. |
| Backout | An exact, reversible backout with verification and known-good recovery evidence, owned and executed by the human release owner; prefer route remaps and flag flips over irreversible actions. |
| Plan shown | Every command and the manifest or configuration diff are shown; approval covers no undisclosed side effect. |
| Timing, monitoring, comms | Peak and freeze periods considered; a named human watches the golden signals with agreed abort criteria; stakeholders and on-call are told before and after. During an incident the commander's roles and comms cadence satisfy these; never delay a mitigation for a notification. |

## Verdict

```text
gate: merge | release | production
verdict: PASS | BLOCKED | APPROVED
Tier: <0|1|2|3 | not applicable>   Target: <exact target>   Actor: <human or protected automation>
Candidate commit ID: <exact commit | not applicable>   Artifact identity: <immutable digest or version | not applicable>
Approved by: <human>   When: <UTC>   Valid until: <UTC | not applicable for Tier 0/1>
Execution-time binding: <rechecked target/action/actor/identity at UTC | pending>
Backout: <exact reversible steps>   Watching: <who, which signals>   Abort if: <criteria>
Production execution boundary: <protected environment or least-privilege executor evidence | missing>
Blocking items: <the NOs, each with what clears it>   Waivers: <item, approving human, reason>
```

## Execution result

Approval records a decision, not whether the effect happened. After every Tier 2 or 3 attempt the
executor returns the result; the agent records it and never invents a receipt, runs a verification
query, or upgrades an ambiguous result. A missing response is not `not executed`: if dispatch may
have occurred and no durable result exists, record `UNKNOWN`, and nothing is retried or re-issued
until the named reconciliation owner runs the read-after-write query and resolves it.

```text
Execution outcome: <executed | not executed | UNKNOWN>
Actor/time: <human or protected automation + UTC | unavailable>
Target/action: <exact target + action>
Receipt/operation ID: <durable receipt | unavailable>
Reconciliation owner: <named human>   Reconciliation query: <exact read-after-write query>
Retry permission: <ALLOWED | BLOCKED_PENDING_RECONCILIATION>
```

## Read only what the decision needs

| If the request involves | Read |
|---|---|
| Preparing a Tier 2 or 3 approval-request packet, or an explicit ask for the template | [Tier 2 approval example](./references/tier-2-approval-example.md) |
| A declared incident needing reversible Tier 0–2 mitigation, a bounded envelope, rollback to the live artifact, or post-incident reconciliation | [Incident fast path](./references/incident-fast-path.md) |
| Proving a release artifact is the immutable one that was tested | [Release artifact evidence](./references/release-artifact-evidence.md) |

Urgency without a declared incident does not open the fast path. A new artifact and every Tier 3
action stay on the full checklist at any severity.
