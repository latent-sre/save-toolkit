# Workflow graph design contract: <graph name>

Conclusion: <what the graph is for, its riskiest edge, what remains unresolved>. Labels:
`[verified]` independently run or observed; `[sourced]` cited; `[unverified]` not established.

## 1. Scope, consumer, owner, authority

| Field | Value |
|---|---|
| Purpose | |
| Consumer | |
| Owner | |
| Caller and trust boundary | |
| Start condition | |
| Authority this design grants | none — design only |
| Assumptions | |
| Unresolved decisions | |

## 2. Identities

| Identity | Value or `[unverified] not supplied` |
|---|---|
| Graph ID / version | |
| Actor | |
| Build / code version | |
| Prompt revisions | |
| Tool identities and revisions | |
| Schema versions | |
| Configuration | |
| Grader identities and thresholds | |
| Model identity | |
| Runtime identity | deferred unless supplied by an approved consumer decision |

## 3. Typed data contract

| Contract | Type / schema | Notes |
|---|---|---|
| Input | | |
| Internal state | | |
| Context | | |
| Node input/output (per node class) | | |
| Edge payload | | |
| Reducer state | | |
| Checkpoint | | |
| Final output | | |

## 4. Node table

| Node | Class (compute / model / tool-effect / approval / reducer-join / verifier / terminal) | Preconditions | Authority and credential scope | Timeout owner | Retry owner | Success result | Failure result |
|---|---|---|---|---|---|---|---|

## 5. Edge and routing table

| Edge | Class (deterministic / conditional / model-selected / fan-out / fan-in / interrupt / retry / compensation / terminal) | Guard or condition | Allowed destination set | Deterministic guardrails | Payload and labels carried |
|---|---|---|---|---|---|

## 6. Scheduling, admission, fairness, backpressure, load shedding, worker liveness

| Concern | Statement |
|---|---|
| Queue ownership and capacity | |
| Priority and fairness | |
| Tenant quota | |
| Concurrency cap | |
| Backpressure | |
| Load shedding | |
| Worker lease / heartbeat / liveness timeout | |
| Stale-worker handling | |
| Poison-work quarantine and manual-repair owner | |
| Admission evidence | |

## 7. Fan-out / fan-in and state merge

| Fan-out edge | Budget | Branch identity | Per-branch budget | Partial-failure policy | Late-result policy | Duplicate-result policy |
|---|---|---|---|---|---|---|

| State key | Writer cardinality | Reducer and algebra | Ordering guarantee | Conflict handling | Join quorum | Schema version |
|---|---|---|---|---|---|---|

## 8. Failure, retry, timeout, replay safety

| Failure class | Retry owner | Attempt / time budget | Backoff | Replay-safety class | Authority for an unsafe replay | Timeout owner | Fail-closed handling |
|---|---|---|---|---|---|---|---|

## 9. Effects: idempotency, receipt, retention, `UNKNOWN`, reconciliation, compensation

| Effect node | Operation / target / tenant | Key construction | Attempt identity | Mismatched-intent rejection | Receipt store and atomic coupling | Retention | `UNKNOWN` handling | Reconciliation query and owner | Compensation |
|---|---|---|---|---|---|---|---|---|---|

## 10. Approval, durability, resume, cancellation, supersession, restart, replay/fork, compatibility

| Control | Statement |
|---|---|
| Approval binding (approver, action, target, candidate identity, expiry, rejection, timeout, resumed-state check) | |
| Run / thread / checkpoint identity | |
| State and checkpoint schema version | |
| Durability mode and checkpoint boundary | |
| Recovery model (checkpoint resume or event-history replay) | |
| Resume semantics | |
| Cooperative cancel (signal, safe points) | |
| Durable cancel (persistence, dispatch prevention) | |
| In-flight effect and late-worker disposition | |
| Supersession | |
| Restart behaviour | |
| Fork semantics | |
| Compatibility boundary and migration | |
| Cleanup deadline | |

## 11. Termination budgets

| Terminal class | Bound | Evidence written |
|---|---|---|
| Success | | |
| No progress | | |
| Maximum turns / iterations | | |
| Maximum time | | |
| Maximum tokens / cost | | |
| Cancellation | | |
| Safety stop | | |
| Unreachable exit detected | | |

## 12. Context provenance, taint, security

| Concern | Statement |
|---|---|
| Actor and credential scope per node | |
| Least authority per node | |
| Untrusted-input treatment | |
| Provenance and freshness | |
| Taint propagation across edges and handoffs | |
| Redaction | |
| Retention | |

## 13. Trace and evaluation plan

| Lineage identity | run / node / edge / attempt / retry-replay / authoritative-final-result |
|---|---|
| Events | tool, handoff, guardrail, approval, checkpoint, effect, admission, cancel |
| Indicators by failure plane | |
| Evaluations | node, edge, path, outcome, recovery, consistency, temporal, budget — each with trials, threshold, numerator/denominator |
| Evidence separation | activation/routing, artifact quality, runtime behaviour reported independently |

## 14. Runtime-selection criteria

Status: **deferred** — <owner decision it waits on>. Criteria a selection must satisfy:

- 

## What I did NOT do

- No runtime selected. Nothing executed. No credential, approval, or production access granted.
- Runtime behaviour, durability, provider behaviour, effect safety, and production readiness are
  `[unverified]` until an approved implementation is exercised.
