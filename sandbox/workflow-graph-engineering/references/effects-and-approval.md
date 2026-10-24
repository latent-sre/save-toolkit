# Effects and approval

Read this when any node performs an external effect — a write, message, deployment, payment,
ticket, or any call whose result persists outside the graph — or when a human approval gates one.
The graph's own state store is not the world: the world does not roll back with a checkpoint, and
it does not know which attempt is talking to it.

## Contents

- Why at-least-once is the honest default
- The effect row
- Idempotency key construction
- Receipt, journal, and reconciliation
- The `UNKNOWN` state machine
- Bounded review probes
- Compensation
- The approval gate
- Failure modes this section exists to catch

## Why at-least-once is the honest default

A handler that dispatches a remote mutation can lose its process after the target commits and
before the result reaches the checkpoint. On resume the graph sees an incomplete node and runs it
again. Retries, deterministic replay, lease expiry, and cancellation all create the same window.
So every effect is designed as **at-least-once with semantic idempotency**, and the design proves
the second execution is harmless — or proves it cannot happen until someone has looked.
*[sourced: AWS Builders' Library,
[Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/),
reviewed 2026-08-24]*

## The effect row

Section 9 of the artifact carries one row per effect node. A row is complete when it names:

| Field | What it must say |
|---|---|
| Operation and target | The exact remote operation, target system, and resource scope; "the API" is not a target |
| Caller and tenant | Which actor identity dispatches, under which credential scope, on behalf of which tenant |
| Logical request ID | Caller-supplied or allocated once and persisted before first dispatch; stable across retries, resume and replay; distinct for each new operation even with identical payload |
| Intent digest | Canonical payload digest immutably bound to the scoped logical request ID — normalised field order, units, and identifiers |
| Key construction | `key = H(caller, operation, target, tenant, logical request ID)`; deterministic from persisted state; never regenerate the ID per attempt |
| Attempt identity | A per-dispatch attempt ID distinct from the key, so a journal can show three attempts under one key |
| Replay-safety class | `pure`, `idempotent-by-key`, `idempotent-by-target` (the target dedupes natively), or `non-idempotent` |
| Timeout owner | Which layer times the call out and what the layer records when it does |
| Retry owner | The one layer allowed to retry this failure class, its attempt and time budget, and backoff |
| Receipt store | Where the receipt lands and whether it commits atomically with the mutation |
| Reconciliation | The read-after-write query that resolves an `UNKNOWN` dispatch, and who runs it |
| Retention | How long the result or tombstone is kept: at least the full retry window plus the ambiguity window plus late-arrival slack |
| Compensation | `reversible via <operation>` with its own effect row, or `irreversible` |
| Approval | Whether an approval precedes it and the binding it carries (next section) |

## Idempotency key construction

- Bind the key to the **logical operation**, not just its payload or node. Two intentional sends
  of the same reminder get distinct logical request IDs and keys; retrying either keeps its ID
  and key. A caller token or an ID allocated once (including a UUID) is valid only if persisted
  before first dispatch and recovered rather than regenerated after a crash.
- Store the canonical payload digest against the scoped logical request ID before dispatch. A
  changed payload with that ID is a conflict, not a new key; a new operation needs a new ID.
  Compare and reserve this binding atomically so concurrent first attempts cannot bind it twice.
- Reject reuse with mismatched intent **before dispatch**: if the journal already holds this key
  with a different intent digest, the node fails closed and reports the conflict. Silently
  proceeding would either duplicate the effect or return a stale result for a different request.
- A checkpoint hit, a cache hit, or a successful model turn does not supply this contract; only
  the effect boundary can.
- `idempotent-by-target` is a claim about the remote system and stays `[unverified]` until its
  documented dedupe behaviour and window are cited.

## Receipt, journal, and reconciliation

Prefer a receipt that commits **atomically with the mutation** — a transactional outbox in the same
store, a target that returns a durable operation ID, or a conditional write keyed on the
idempotency key. Where atomic coupling is unavailable, reconciliation is mandatory: the design
names the read-after-write query, its expected latency, and the owner who runs it. A journal that
records "dispatched" before the call and "received" after it is the minimum; without it, an
operator cannot tell a lost result from a call that never happened.

## The `UNKNOWN` state machine

```
PENDING -> DISPATCHED -> SUCCEEDED
                      -> FAILED (definitive non-application, retry owner may retry)
                      -> UNKNOWN (timeout, crash, ambiguous response)
UNKNOWN -> RECONCILING -> SUCCEEDED | FAILED | STILL_UNKNOWN
STILL_UNKNOWN -> manual repair owner decides; no automatic replay
```

- `UNKNOWN` is a persisted state with an owner and an age; it is not a log line.
- No automatic redispatch is allowed while unresolved, including `RECONCILING` and `STILL_UNKNOWN`.
  An unchanged key, an idempotent class, or documented native dedupe with valid retention does
  not bypass reconciliation. A durable target receipt can establish `SUCCEEDED`; only definitive
  non-application with no in-flight or late commit possible establishes retryable `FAILED`.
  A missing eventually consistent read is insufficient. After resolution to `FAILED`, the one
  retry owner may dispatch within budget, with a new attempt ID under the same logical ID/key,
  matching digest, retained binding/receipt, and valid approval. Otherwise stop with uncertainty.
- The graph must be able to terminate with an effect still `UNKNOWN`, surfacing it in the terminal
  evidence, rather than hanging or lying.

## Bounded review probes

Use these cases to check a proposed design; they do not establish runtime behaviour.

| Reconciliation evidence | Native dedupe proof | Required decision |
|---|---|---|
| Unresolved timeout | Missing | Hold; no redispatch |
| Unresolved timeout | Same key, expired retention | Hold; no redispatch |
| Unresolved timeout | Exact target, same key, matching digest, valid retention | Hold; no redispatch |
| Missing eventually consistent read | Exact target, same key, matching digest, valid retention | Hold; no redispatch |
| Durable target success receipt | Not needed for resolution | Record success; no redispatch |
| Definitive non-application, no in-flight or late commit possible | Retained logical ID/key and matching digest | Retry owner may retry within budget and valid approval, with a new attempt ID |

## Compensation

Compensation is an effect. It has its own row, key, attempt identity, and `UNKNOWN` path. Claim it
only for an operation shown to be reversible in the domain — a ticket can be closed, a sent email
cannot be unsent, a deployment "rollback" is a new deployment with its own blast radius. Cancelling
a run never compensates anything by itself; it only stops new dispatches.

## The approval gate

An approval node sits **immediately before** the effect path so nothing can change state between
the decision and the dispatch. Its record binds:

| Binding | Why it is load-bearing |
|---|---|
| Approver identity | An approval nobody owns is an approval anyone can forge |
| Exact action and target | "Approve the deploy" without the target lets a later edit inherit the approval |
| Immutable candidate/config identity | Content hash or revision; the state at dispatch must match, or the approval is stale |
| Expiry | Approvals age out; a resumed run re-checks expiry before dispatching |
| Rejection and timeout paths | Both are edges in the graph with their own terminal evidence, not exceptions |
| Resumed-state binding | On resume, the node compares the persisted approval to the current candidate identity before dispatching |

Approval records a decision. It does not create credentials or enforcement: the effect boundary
still enforces the approved identity, arguments, and credential scope, and the approval gate is
where a human can be shown the plan and rollback before anything moves.

## Failure modes this section exists to catch

| Defect | Symptom in the design | Correction |
|---|---|---|
| Checkpoint-equals-exactly-once | "The checkpoint guarantees the payment runs once" | Add the effect row; classify replay safety; add reconciliation |
| Key built from node or timestamp | Same intent retried produces a new key and a duplicate effect | Derive the key from caller/operation/target/tenant/persisted logical request ID |
| Identical payload, distinct operations | Second intentional reminder returns the first receipt | Allocate a distinct persisted logical request ID for each new operation |
| Reused key, different intent | Second request returns the first request's result | Reject mismatched intent before dispatch |
| Retention shorter than the retry window | A late retry finds no tombstone and re-executes | Retention ≥ retry window + ambiguity window + late-arrival slack |
| Automatic replay while `UNKNOWN` | Retry loop hides a committed remote write | Persist `UNKNOWN`; reconcile before any retry |
| Approval detached from the action | Approval granted on one candidate, dispatched on another | Bind approval to candidate identity and re-check on resume |
| Compensation assumed | "On failure we roll back the notification" | Mark irreversible; design the terminal state that reports it |
