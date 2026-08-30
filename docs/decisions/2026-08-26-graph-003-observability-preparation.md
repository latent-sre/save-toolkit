# Prepare the GRAPH-003 observability handoff without speculative alerting

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision owner:** `latent-sre`
- **Current state (2026-08-30):** `GRAPH-002` closed; `graph-sandbox/v1` is the accepted runtime.
  This record still governs the producer/consumer telemetry handoff. Context below was written
  before that closeout and does not claim the graph is unimplemented today.

## Context

The accepted GRAPH-002 decision names `checkout-payments-timeout-drill/v1` as the first executable
graph and `graph-sandbox/v1` as its consumer-specific Docker Compose runtime. That resolves the two
owner choices GRAPH-003 previously lacked: the scope is renewed and the first graph is named.

The graph is not implemented yet. There is therefore no emitted event stream, metric series,
checkpoint history, failure timing, or alert evaluation result to inspect. Choosing dashboards,
queries, thresholds, retention, or paging behavior now would manufacture an operating contract from
design intent rather than observed behavior.

Preparation is still useful. GRAPH-002 needs to know which identities and boundary events must exist
so GRAPH-003 can later distinguish a graph failure from a runner, model, checkpoint, or downstream
service failure. This decision freezes that producer/consumer handoff and a failure-injection matrix;
it does not claim that the telemetry exists or that any alert is verified.

The OpenTelemetry GenAI agent/workflow conventions were Development status at the upstream revision
inspected by the 2026-08-23 research refresh and did not provide the fleet's full attempt/replay
identity. The first implementation may map stable fields to applicable standard attributes, but it
must retain a versioned fleet namespace for the missing graph-specific identities rather than
calling an unstable convention complete.

## Decision

1. **Keep ownership split at the telemetry boundary.** GRAPH-002 produces versioned structured
   events and the evidence bundle. GRAPH-003 interprets observed data into indicators, queries,
   cardinality budgets, runbook branches, dashboards if justified, and synthetic alert rules. The
   graph runner does not define paging semantics.
2. **Prepare for one graph only.** The contract covers `checkout-payments-timeout-drill/v1` in
   `graph-sandbox/v1`. A later graph may reuse fields that fit, but must justify additional signals
   and failure planes rather than turning this into a universal graph telemetry schema by default.
3. **Emit boundary events, not loop chatter.** Events occur at run, node/task, edge, approval,
   checkpoint, effect, budget, cancellation, and reconciliation boundaries. Inner-loop progress is
   emitted only when a named stuck-work question requires it.
4. **Separate correlation from aggregation.** High-cardinality identities belong in structured logs,
   traces, and the evidence envelope. Metrics use bounded dimensions only. `run_id`, `task_id`,
   `attempt_id`, `replay_id`, `checkpoint_id`, `effect_id`, order IDs, prompt contents, tool
   arguments, and arbitrary error text are forbidden metric labels.
5. **Do not collect sensitive content by default.** Prompts, model input/output, tool arguments,
   credentials, authorization headers, checkout payloads, and raw exception bodies are absent from
   the normal telemetry path. A sanitized error class and bounded failure plane are sufficient for
   the first graph. Detailed evidence remains in the access-controlled run bundle when required.
6. **Defer operational tuning to observed data.** No numeric alert threshold, `for` duration,
   retention period, SLO target, dashboard layout, or production routing decision is accepted here.
   GRAPH-003 selects those only after the sandbox emits data under the accepted fault cases.
7. **Keep the first alert set synthetic.** Rules are evaluated against sandbox data and prove fire
   and resolve behavior, ownership, and runbook linkage. They do not connect to a live notification
   route or create a pager.

## Telemetry handoff from GRAPH-002

The implementation emits a versioned structured record for every boundary event. Exact encoding and
field types belong to the implementation contract, but the following semantics are required before
GRAPH-003 unblocks.

| Field group | Required meaning | Cardinality posture |
|---|---|---|
| Contract | event contract version, graph contract/version, sandbox profile/version, exact source revision | evidence/log attribute; graph version may be a bounded metric label |
| Time | UTC event time, monotonic duration where applicable | duration becomes a histogram observation; timestamp is not a label |
| Run lineage | run, parent run where applicable, terminal authoritative result | identities stay in logs/traces/evidence; bounded outcome may label metrics |
| Work lineage | node name, edge/transition class, task, attempt, retry, replay | node and transition class may be bounded labels; unique IDs never label metrics |
| State durability | thread and checkpoint identity, checkpoint operation, resume source/result, schema/build version | identities stay in logs/traces/evidence; operation/result may be bounded labels |
| Effects | effect class, idempotency identity, dispatch/receipt/reconciliation state, authoritative or `UNKNOWN` result | identities and receipts stay in evidence; bounded class/state may label metrics |
| Control | approval request/result/wait, budget kind/limit/consumed/remaining, cancellation request/acknowledgement | numeric values become observations; actor identity and request IDs stay out of metrics |
| Failure | failure plane, bounded error class, retryability decision, terminal or recoverable disposition | bounded plane/class/disposition may label metrics; raw error text stays in logs/evidence |

The initial boundary-event vocabulary covers:

- run accepted, started, terminal, cancelled, superseded, and inconclusive;
- node/task scheduled, started, completed, failed, retry scheduled, and retry exhausted;
- edge selected, fan-out emitted, join satisfied, and join starved;
- approval requested, approved, rejected, and timed out;
- checkpoint write started/completed/failed, resume started/completed/failed, and checkpoint rejected;
- effect prepared, dispatched, receipt recorded, marked `UNKNOWN`, reconciled, and replay refused;
- budget observed, threshold reached, and exhausted; and
- cancellation requested, propagated, acknowledged, and unconfirmed.

An implementation may combine events when it preserves these distinctions and their ordering. It may
not report a terminal success until the authoritative-final-result identity is known, nor collapse
an ambiguous effect into a generic retryable failure.

## Operational questions

GRAPH-003 will derive the smallest useful signals from observed events to answer these questions:

1. **Is the graph serving?** Did accepted runs reach an authoritative terminal result within their
   declared time and budget?
2. **Where is it failing?** Is the failing plane graph control, runner/worker, model fixture or
   approved provider, checkpoint store, checkout, payments, inventory, or effect reconciliation?
3. **Is work stuck?** Are scheduled tasks not starting, fan-out branches not joining, approvals not
   resolving, cancellations not acknowledging, or checkpoints becoming stale?
4. **Is recovery safe?** Did resume select the intended thread and checkpoint, preserve committed
   nodes, and refuse unsafe effect replay?
5. **Are retries helping or amplifying failure?** Which bounded error classes retry, exhaust, or
   cause duplicate/ambiguous effects?
6. **Is the graph within its operating budget?** Are attempt, wall-time, model-call, token, and cost
   ceilings respected, and does exhaustion stop new scheduling?
7. **Can an operator act?** Does each actionable symptom identify the owner, first diagnostic step,
   safe control action, verification, and escalation path?

## Failure-injection matrix

This matrix defines evidence GRAPH-002 must make observable. It does not preselect alert thresholds.

| Injected condition | Question and required evidence | Expected operational branch |
|---|---|---|
| Healthy checkout through payments and inventory | Can one run complete with ordered node/edge lineage, receipts, checkpoint history, duration, and budget evidence? | Baseline only; no alert |
| Checkout fails readiness before graph start | Does admission refuse the run and name the application plane without creating task attempts? | Fix application readiness; do not replay |
| Payments latency exceeds the checkout timeout | Are downstream latency, checkout failure, retry decision, attempt count, and final outcome distinguishable? | Diagnose payments latency; retry only within the declared policy |
| Payments returns a bounded HTTP failure | Does the event carry a sanitized error class and downstream failure plane without payload leakage? | Follow payments dependency failure branch |
| Payment commits but the response is lost | Is the effect marked `UNKNOWN`, with idempotency and reconciliation identity, and is automatic replay refused? | Reconcile/read after write before any replay |
| Inventory returns a bounded HTTP failure after payment receipt | Is the partial-effect state visible and separate from a wholly failed checkout? | Preserve receipt, stop, and follow partial-effect handling |
| Model fixture or approved provider fails | Can the operator distinguish provider failure from graph logic and tool/application failure? | Use provider/fixture branch; respect retry and budget limits |
| Node retry exhausts | Are every attempt, retry cause, backoff decision, and terminal disposition attributable to one task? | Stop retrying; inspect the owning failure plane |
| Fan-out branch never reaches its join | Are outstanding branches and join age visible without per-run metric labels? | Quarantine or cancel late work; follow join-starvation branch |
| Runner stops after checkpoint commit | Does restart resume the selected thread without reapplying committed work? | Resume from the verified checkpoint and compare lineage |
| Runner stops after effect dispatch but before receipt | Does the run remain `UNKNOWN` and block automatic replay until reconciliation? | Reconcile the target, then resume or terminate explicitly |
| Checkpoint write fails or stored state is rejected | Is the run `inconclusive`, with checkpoint operation and compatibility evidence preserved? | Stop; preserve evidence; start a clean run after diagnosis |
| Approval is not answered within its bound | Are approval wait, timeout, stopped scheduling, and terminal disposition visible? | Escalate or terminate; never self-approve |
| Attempt, time, token, or cost budget exhausts | Does scheduling stop and identify the exhausted budget without reporting success? | Terminate and review the budget/loop design |
| Cancellation requested during active work | Are propagation and acknowledgement latency visible, and are late results quarantined? | Treat unacknowledged descendants as unverified, not stopped |

## Completion boundary

This preparation is complete when the roadmap links this decision and GRAPH-002 carries the required
telemetry handoff. GRAPH-003 implementation remains blocked until the offline graph produces these
events under the failure matrix. At that point the observability owner inspects actual cardinality,
frequency, timing, and failure behavior before choosing metrics, queries, thresholds, dashboards,
retention, runbooks, or alert rules.

No paid or Terra run is needed for this preparation. A later Terra run may validate provider-specific
behavior only under the separately approved GRAPH-002 live profile; it does not replace deterministic
sandbox fault evidence.

## Rejected alternatives

- **Write alerts and dashboards now.** No real series, distribution, or failure timing exists, so
  thresholds and panels would be decorative assumptions.
- **Put unique run identities into metric labels.** That makes correlation convenient by consuming
  unbounded time-series cardinality. Logs, traces, and evidence own those identities.
- **Capture prompts and tool arguments by default.** The first operational questions do not require
  sensitive content, and telemetry is a poor place to create another retained copy.
- **Use one aggregate graph-success metric.** It hides the failure-plane owner and cannot distinguish
  unsafe effect uncertainty from an ordinary failed run.
- **Create a graph-operations agent.** Existing observability, runbook, and SRE ownership is
  sufficient; the graph adds signals and failure branches, not a new authority boundary.

## Reopen trigger

Write a superseding decision if observed sandbox data cannot answer the operational questions with
this handoff, if a later graph introduces a materially different scheduler or durability plane, or
if a stable upstream semantic convention covers the fleet-specific attempt/replay/effect identities
without losing required distinctions.

<!-- ADRs are append-only and immutable once accepted. To change a decision, write a new ADR and mark
     this one "superseded by <YYYY-MM-DD>-<slug>". -->
