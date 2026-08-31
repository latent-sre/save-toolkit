# `checkout-payments-timeout-drill/v1` — implementation contract v2

- Runtime: `graph-sandbox/v1`
- Case: `graph-sandbox-case/v2`
- State: `graph-state/v2`
- Boundary event: `graph-boundary-event/v2`
- Checkpoint lineage: `graph-checkpoint-lineage/v2`
- Evidence: `graph-evidence/v2`

This is the living interface shared by activation, the three synthetic services, and the graph
runner. A change to any shape here changes all producers and consumers in the same revision.

## Trust boundary

`activate.py` is the only supported build or runtime entrypoint. The host may run only its
standard-library validation, evidence inspection, and tests. Application and graph code run only in
the reviewed Docker Compose model. The runtime publishes no host port, uses one `internal: true`
network, receives no credential, and has no bind mount, socket, external network, or production
authority. Docker calls name one validated local context and use a scrubbed environment.

Each container is numeric non-root, read-only, capability-free, `no-new-privileges`, and has bounded
CPU, memory, PIDs, tmpfs, stop grace, and runtime. The runner starts only after the synthetic
services pass their exact `/livez` health checks.

## Independent identities

`case_id` selects one immutable fault document. `run_id` selects one execution and is never derived
from the case. Several runs may execute the same case. The case SHA-256 is over the exact checked-in
UTF-8 bytes and is frozen by the host validator.

The thread identity is `checkout-payments-timeout-drill-v1:<run_id>`. Task, attempt, replay,
checkpoint, effect, receipt, and authoritative-result identities remain distinct. Resume reuses the
run, case, case digest, source revision, context fingerprint, thread, volumes, and identity claim.

## Immutable case document

Exactly these case IDs exist; an extra or missing document, an unknown ID, changed digest, link, or
schema mismatch fails before launch:

1. `mission-healthy-001`
2. `checkout-readiness-failure-001`
3. `checkout-ambiguous-after-commit-001`
4. `payments-latency-001`
5. `payments-http-error-001`
6. `payments-ambiguous-after-commit-001`
7. `inventory-http-error-after-payment-001`
8. `duplicate-effect-001`

The closed document shape is:

```json
{
  "case_version": "graph-sandbox-case/v2",
  "case_id": "mission-healthy-001",
  "service_fixtures": {
    "checkout": {"readiness": "ready", "effect": "success"},
    "payments": {"readiness": "ready", "effect": "success"},
    "inventory": {"readiness": "ready", "effect": "success"}
  },
  "checkout": {
    "order_id": "synthetic-order-healthy-001",
    "amount_cents": 1299,
    "currency": "USD",
    "items": [{"sku": "synthetic-sku-001", "quantity": 1}]
  },
  "model_fixture": {"plan_class": "checkout", "token_count": 64},
  "budgets": {
    "attempts": {"limit": 8, "consumed": 0},
    "wall_time_ms": {"limit": 120000, "consumed": 0},
    "model_calls": {"limit": 1, "consumed": 0},
    "tokens": {"limit": 64, "consumed": 0},
    "spend_micro_usd": {"limit": 0, "consumed": 0}
  }
}
```

The runner receives `CASE_ID` and `CASE_DIGEST`. Each service receives its own immutable
`SANDBOX_CASE_ID`, `READINESS_FIXTURE`, and `EFFECT_FIXTURE`; it cannot see or select another
service's fixture. Every synthetic request carries `X-Sandbox-Case: <case_id>`. A service rejects a
missing or mismatched header before reading or writing its receipt store.

## Synthetic HTTP seams

Every service exposes an always-200 process-liveness `GET /livez`; fixture state never changes it.
The graph probes faultable readiness through `GET /healthz`: `ready` returns 200 and `unavailable`
returns 503, so readiness failure is captured in graph evidence after the runner starts. The checkout
effect is `POST /checkout`; payments is `POST /v1/authorizations`; inventory is
`POST /v1/reservations`. Mutation requests carry `Idempotency-Key`, `X-Request-ID`, and
`X-Sandbox-Case`. Responses and failures use closed, bounded JSON. A timeout or lost response after
dispatch is not proof that an effect did not occur.

## Durable topology

Five ownership-labelled run-scoped volumes are the only durable mounts:

| Volume | Container | Target | Contents |
|---|---|---|---|
| `runner-state` | graph-runner | `/state` | LangGraph checkpoint, effect ledger, boundary event DB |
| `runner-evidence` | graph-runner | `/evidence` | bounded exported evidence |
| `checkout-data` | checkout | `/data` | checkout request/receipt SQLite |
| `payments-data` | payments | `/data` | payment idempotency/receipt SQLite |
| `inventory-data` | inventory | `/data` | inventory idempotency/receipt SQLite |

All service writes are transactional and idempotency-keyed. A committed receipt survives a service
or runner restart. `UNKNOWN` blocks automatic replay until reconciliation returns an authoritative
receipt or an explicit terminal unknown result.

## Evidence interfaces

Runner evidence is copied from the exact graph-runner container to an exclusive directory beneath
the canonical evidence root, checked for links, unexpected paths, count/size bounds, checksums,
closed schemas, and cross-file identity agreement. Only then may it be atomically published as
`<evidence-root>/<run_id>`.

Required runner files are `manifest.json`, `final-state.json`, `events.jsonl`, `effects.jsonl`,
`checkpoint-lineage.json`, `runtime.json`, and `checksums.sha256`. Successful evidence additionally
contains payment and inventory receipts. Host publication adds `commands.jsonl`,
`compose-config.json`, `verification.json`, and `environment.json` and recomputes all checksums.

`manifest.json` includes the closed lineage: evidence/contract/sandbox versions, source revision,
run ID, case ID, case digest, thread ID, outcome, authoritative result ID, timestamps, and artifact
inventory. `final-state.json` carries the same lineage and the closed terminal graph state.

The checkout-level ambiguous-after-commit case is the one bounded exception to the ordinary
single-bundle layout. The runner reaches a durable static reconciliation breakpoint after recording
`UNKNOWN`, exports a provisional terminal projection without adding that terminal event to the
durable event store, resumes from the recorded checkpoint, observes the target-owned checkout
receipt, and transitions that same effect to `RECONCILED`. It exports two independently checksummed
bundles. Activation validates both against the same exited runner and atomically publishes them as
`<evidence-root>/<run-id>/{unknown,reconciled}`. Host verification v2 identifies each bundle's
`snapshot_role`; `exit_code` remains the semantic bundle result (`2` then `0`), while
`runner_container_exit` truthfully records the single final runner exit. The later event history
extends the earlier durable prefix after excluding only the provisional terminal projection, and
the effect ledger extends exactly `PREPARED -> DISPATCHED -> UNKNOWN -> RECONCILED`.

Only the read-only `reconcile_if_ambiguous:0` receipt lookup may use more than one task attempt, and
only after the same checkout effect is durably `UNKNOWN`. Its attempt ordinals start at one, remain
contiguous, and may not exceed the runtime's `budgets.attempts.limit`; the final attempt completes.
Reconciliation starts only after the checkout `effect.unknown`, checkout `task.failed`, and the
snapshot-required `effect.replay_refused`, in that order. Every prior attempt is exactly
`task.started -> effect.replay_refused -> task.failed`, with one matching refusal. The final attempt
encloses the single `effect.reconciled` between its start and completion. If a crash occurs after the
ledger transition but before task/checkpoint persistence, recovery completes that same open attempt;
it does not invent a later ordinal. Readiness and checkout-effect tasks remain attempt one, checkout
dispatch consumption remains exactly one, and reconciliation never redispatches, replays, or widens
effect authority.

### Boundary event oracle

Every `graph-boundary-event/v2` record has exactly: `event_version`, `event_type`, `event_id`,
`sequence`, `time_utc`, `contract_version`, `sandbox_version`, `source_revision`, `run_id`,
`case_id`, `case_digest`, `thread_id`, `node_id`, `task_id`, `attempt_id`, `replay_id`,
`checkpoint_id`, `effect_id`, `failure_plane`, `error_class`, and `data`. Event data is closed per
event type. Sequences start at one without gaps and `event_id` is `<run_id>:<sequence-8-digits>`.
All lineage is constant. Exactly one outcome-matching run terminal event is last. Approval precedes
every effect preparation or dispatch. `run.accepted` and `run.started` are the immutable prefix.
Effect-bearing paths prove fan-out, all three readiness task pairs, the matching join, approval
request and decision, and the durable effect transition chain in causal order. Pre-effect paths use
their own closed automata: readiness failure ends in `edge.join_starved` before any approval;
rejection and timeout require the healthy join then the exact approval request/decision; cancellation
proves request/propagation/acknowledgement (either before fan-out or while awaiting approval); and
budget exhaustion proves whether it stopped admission, planning, or the pre-dispatch attempt. A
`NOT_STARTED` run contains neither effect ledger rows nor `effect.*` events.

The allowed vocabulary is: `run.accepted`, `run.started`, `run.terminal`, `run.cancelled`,
`run.inconclusive`; task scheduled/started/completed/failed/retry-scheduled/retry-exhausted; edge
selected/fanout-emitted/join-satisfied/join-starved; approval requested/approved/rejected/timed-out;
checkpoint write-started/write-completed/write-failed/resume-started/resume-completed/resume-failed/
rejected; effect prepared/dispatched/receipt-recorded/unknown/reconciled/replay-refused; budget
observed/threshold-reached/exhausted; and cancellation requested/propagated/acknowledged/unconfirmed.

### Checkpoint oracle

`checkpoint-lineage.json` is closed `graph-checkpoint-lineage/v2` and contains contract/state/source/
package lineage, thread ID, `resume_source_checkpoint_id` (null when no resume completed), ordered checkpoint
records, and `saver_checkpoint_ids` observed directly from the configured SQLite saver. Each write
started event is paired with exactly one later write completed or failed event. Every recorded or
resumed checkpoint ID exists in `saver_checkpoint_ids`. Before resumed work, the runner closes any
crash-interrupted write or resume pair against the durable saver: a present checkpoint completes a
write; an absent one fails it; and a later recorded checkpoint completes a resume from its source.
Each resume start has exactly one later completed or failed result. The most recent successful resume
starts from exactly `resume_source_checkpoint_id` and completes on a later recorded checkpoint;
absent, duplicate, overlapping, unpaired, or unrelated IDs reject publication.

### Outcome oracle

- `SUCCEEDED`: approval is approved, all readiness branches and required tasks completed, budgets
  are bounded, cancellation is none, failure is null, checkout/payment/inventory receipts are
  authoritative, and the effect ledger ends receipt-recorded or reconciled.
- Approval rejection or timeout, readiness failure, cancellation, or budget exhaustion: checkout
  is `NOT_STARTED`, the effect ledger is empty, no receipt exists, and the outcome/event/control
  state names that exact branch. If the wall budget is exhausted only after an authoritative
  checkout receipt was durably recorded, the run is `FAILED` rather than `SUCCEEDED`, checkout
  remains truthfully `COMPLETE`, the receipt chain is retained, and failure names the completed-
  effect budget overrun.
- `UNKNOWN`: no completed checkout receipt exists and the checkout effect may not end merely
  `PREPARED` or `DISPATCHED`; it ends `UNKNOWN` or replay-refused with a reconciliation identity.
- Other failure/inconclusive outcomes cannot contain false-success receipts or authoritative result
  IDs. Exit 0 means `SUCCEEDED`; exit 2 means a validated non-success terminal outcome.

## Activation state machine

The persistent `graph-sandbox-run-claim/v2` binds run, case, case digest, approval fixture, exact
validated Compose digest, revision, and context and moves
monotonically through `PRELAUNCH`, `RUNNING`, `PRESERVED`, and `PUBLISHED`. `fresh` creates it
exclusively. `resume` requires the exact identity. A prelaunch rejection removes a newly created
claim. Any post-launch uncertainty moves it to `PRESERVED`; a published bundle awaiting resource
cleanup moves it to `PUBLISHED`. It also durably records whether the graph-runner was observed and
the last validated resource subset. Terminal cleanup releases the claim.

`PRELAUNCH` requires no run-scoped resource. `RUNNING` and `PRESERVED` accept only correctly-owned
subsets so a partially-created Compose project can resume. Once the runner has been observed, both
phases require all five durable volumes even if some containers or the network are absent.
`PUBLISHED` is cleanup-only and accepts any correctly-owned subset, including none, so partial
cleanup remains resumable. Foreign, extra, duplicate, or incorrectly-labelled resources always
fail closed.

A separate per-run activation lease is a kernel-held, non-blocking file lock. Its file is not the
lock authority. Killing the holder releases the kernel lock on Windows and POSIX, so a later process
can resume; a concurrent fresh or resume process fails before Docker work.

All post-launch faults and nonterminal exits use one preservation funnel: stop without `--volumes`,
inspect and persist the correctly-owned surviving resource subset, retain durable volumes and the
identity claim, release the kernel lease, and print one exact JSON resume
handoff containing the same context, revision, run ID, evidence root, case ID, and approval fixture.
If the resource subset cannot be proved, preservation returns 125 and retains resources fail-safe.

| Host exit | Meaning |
|---:|---|
| 124 | activation timed out; stop succeeded and state is preserved |
| 125 | preservation stop outcome is unknown; resources are retained fail-safe |
| 126 | nonterminal runner exit or post-launch host/export/publish/cleanup fault; state is preserved |
| 130 | operator interruption; stop succeeded and state is preserved |

Exit 64 is a terminal pre-effect runner rejection and permits bounded teardown. No post-launch
exception may bypass the preservation funnel. Cleanup failure after publication retains the claim
in `PUBLISHED`; resume performs cleanup only and never reruns the graph.

## Commands

```text
python graph-sandbox/activate.py build --docker-context <local> --source-revision <40-hex>
python graph-sandbox/activate.py fresh --docker-context <local> --source-revision <40-hex> --run-id <run> --evidence-root <absolute-existing-dir> --case <case-id> --approval-fixture APPROVED|REJECTED|TIMEOUT
python graph-sandbox/activate.py resume --docker-context <same> --source-revision <same> --run-id <same> --evidence-root <same> --case <same-case-id> --approval-fixture <same>
```

No direct Compose command, alternate profile, path override, ambient Docker selector, or credentials
are accepted. Live Terra remains a separate human-approved profile and is outside this contract.
