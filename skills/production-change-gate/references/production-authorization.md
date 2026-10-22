# Production authorization

Read before classifying or authorizing a production action, or recording or reconciling its execution
result. The [parent skill](../SKILL.md) owns gate selection and execution authority; this reference
owns production tiers, approval requirements, the production verdict, and execution receipts.

## Classify the action

Classify first, then check only what the tier needs.

| Tier | Action | Who may proceed |
|---|---|---|
| 0 | Observe: reads, health checks, config validation, dry runs | The agent, only through its lane's granted, output-protected read path, reporting commands and evidence; otherwise it names the read for the human |
| 1 | Prepare: edit version-controlled config, docs, or an unapplied artifact | The agent, never applying it to a live target |
| 2 | Reversible live change | A human or protected automation, after explicit approval of the exact command shown |
| 3 | Destructive or access-path change: data deletion, storage or backup, credential or identity, DNS, firewall, VPN, proxy, remote access | As Tier 2 plus a proven backup or recovery path; stop until the named action and target are approved |

Approval covers only the command, target, and applying actor shown; a material change re-enters
the gate. During a declared incident, ITO's approval in the TLC may cover a bounded envelope instead
(see the [incident fast path](./incident-fast-path.md)). For covered actions, its short checklist
replaces the production table below.

Urgency without a declared incident does not open the fast path. A new artifact and every Tier 3
action stay on the full checklist at any severity.

## Full production checklist

| Item | Passes when |
|---|---|
| Readiness evidence | A new-artifact deployment attaches the exact candidate commit's independent review, green checks, the release artifact, the `gate: release` PASS record, and the named production approver. A non-deployment action attaches the current command or diff and named approval instead. Rolling back to the previously live artifact reuses that artifact's records. |
| Execution boundary on | Evidence that the named human or protected automation, not the agent, holds the least-privilege role or credential for this exact action (for a deployment, the protected environment gating the credential). Naming an executor or promising not to act is not evidence; repository approval counts are not production authority. Deferred during a declared incident. |
| Approved | An authorized human approved this exact target, command or diff, applying actor, and time, with a `Valid until` UTC deadline and the change record where the process requires one (name the system; `stack-profile` owns the Remedy/Jira fact). |
| Binding current | Immediately before execution the executor confirms the approval has not expired and the current target, action, actor, and candidate or configuration identity match the approved record. Any mismatch is BLOCKED and re-enters. |
| Blast radius | Affected apps, routes, spaces, users or traffic share, and the worst credible failure are recorded. |
| Backout / recovery | Exact rollback where feasible; otherwise state what cannot be undone and provide an evidence-backed recovery path, verification and stop conditions. The human release owner owns execution; unresolved recovery evidence blocks approval. Prefer reversible actions; recovery does not make an action reversible or lower its tier. |
| Plan shown | Every command and the manifest or configuration diff are shown; approval covers no undisclosed side effect. |
| Timing, monitoring, comms | Peak and freeze periods considered; a named human watches the golden signals with agreed abort criteria; stakeholders and on-call are told before and after. During an incident ITO's TLC and update cadence satisfy these; never delay a mitigation for a notification. |

## Production verdict

```text
gate: production
verdict: APPROVED | BLOCKED
Tier: <0|1|2|3 | not applicable>   Target: <exact target>   Actor: <human or protected automation>
Candidate commit ID: <exact commit | not applicable>   Artifact identity: <immutable digest or version | not applicable>
Approved by: <human>   When: <UTC>   Valid until: <UTC | not applicable for Tier 0/1>
Execution-time binding: <rechecked target/action/actor/identity at UTC | pending>
Backout/recovery: <exact rollback, or non-reversible effects and evidenced recovery>   Watching: <who, which signals>   Abort if: <criteria>
Production execution boundary: <protected environment or least-privilege executor evidence | missing>
Blocking items: <the NOs, each with what clears it>   Waivers: <item, approving human, reason>
```

## Execution result

Approval records a decision, not whether the effect happened. After every Tier 2 or 3 attempt the
executor returns the result; the agent records it and never invents a receipt, substitutes its own
read for the executor's receipt, or upgrades an ambiguous result. A dispatched Tier 0 readback is
evidence for the reconciliation owner. A missing response is not `not executed`: if dispatch may
have occurred and no durable result exists, record `UNKNOWN`, and nothing is retried or re-issued
until the named reconciliation owner resolves it and grants retry.

```text
Execution outcome: <executed | not executed | UNKNOWN>
Actor/time: <human or protected automation + UTC | unavailable>
Target/action: <exact target + action>
Receipt/operation ID: <durable receipt | unavailable>
Reconciliation owner: <named human>   Reconciliation query: <exact read-after-write query>
Retry permission: <ALLOWED | BLOCKED_PENDING_RECONCILIATION>
```
