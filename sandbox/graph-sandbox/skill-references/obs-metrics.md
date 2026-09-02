# `graph-sandbox/v1` indicators

Use only for the synthetic `checkout-payments-timeout-drill/v1` graph. These indicators are derived
from verified `graph-evidence/v2` boundary-event bundles; they are not a production metrics schema,
an SLO, or permission to deploy a collector.

## Questions and signals

| Operational question | Indicator | Source | Bounded dimensions |
|---|---|---|---|
| Did accepted work reach an authoritative result? | `graph_run_terminal_total` counter and `graph_run_duration_seconds` histogram | manifest outcome and start/end time | graph contract, sandbox version, outcome |
| Which plane failed? | `graph_failure_total` counter | non-null event failure plane, error class, terminal disposition | failure plane, bounded error class, disposition |
| Did the executed path diverge or starve? | edge selection, fan-out, join-satisfied, and join-starved counters | `edge.*` events | node, transition class, result |
| Are attempts retrying or exhausting? | task/attempt and retry counters | task start/completion/failure/retry events | node, status, bounded error class |
| Is approval blocking progress? | `graph_approval_wait_seconds` histogram and timeout counter | approval request through decision/timeout | decision only |
| Is durable state current? | checkpoint completion age and resume-result counters | checkpoint write/resume events | operation and result |
| Is recovery safe? | replay-refused and resume-result counters | effect replay and checkpoint resume events | result and bounded reason class |
| Is an effect unresolved? | `graph_effect_unknown` gauge | terminal effect ledger state | effect class only |
| Did a control terminate promptly? | cancellation acknowledgement histogram | cancellation request through acknowledgement | result only |
| Did the loop stop at its declared ceiling? | consumed/limit ratio and exhaustion counter | budget observations | budget kind and result |

Unique run, task, attempt, replay, checkpoint, effect, order, and receipt identities belong in the
structured event/evidence view. Never use them as metric labels. Prompt text, tool arguments, raw
payloads, actor identity, arbitrary exception text, and credentials are absent from this signal set.

## Current observed shape

The 2026-08-30 exact-revision exercise used Docker Engine 29.7.2, Compose 5.4.0, Linux/amd64, and
source revision `964e9a4aca83c138dc2b5a483b2192422d5e361e`. Eight injected runs plus one later healthy
recovery produced:

- authoritative success, readiness failure, downstream HTTP failure, approval timeout, duplicate
  idempotent delivery, partial-effect failure, latency timeout, and ambiguous-after-commit outcomes;
- run durations from 0.353 to 2.644 seconds in this synthetic sample;
- approval waits from 0.010 to 0.123 seconds where approval was reached;
- six or ten completed checkpoints per run, with the last completion 0.008 seconds before the
  terminal event in the alert fire/resolve pair; and
- an `UNKNOWN` effect that remained unresolved after an unrelated healthy run.

Those values describe this bounded exercise, not thresholds. Do not turn them into an SLO, `for:`
duration, or retention policy. The current single-runner topology exposes no scheduler queue or
worker pool, so queue depth, worker saturation, fairness, and hot-shard indicators are `n/a` for
this runtime. Runner exit/OOM state and service liveness remain host verification facts until a
queue or worker contract actually exists.

## Interpretation order

1. Read outcome and unresolved-effect count first. `SUCCEEDED` is not healthy while an earlier
   effect remains `UNKNOWN`.
2. Use failure plane to select the owner and runbook branch; do not average the planes into one
   success percentage.
3. Correlate one run in structured events only after the bounded aggregate identifies the plane.
4. Treat missing boundary events as telemetry failure, not zero activity.
5. Keep resume, cancellation, checkpoint-failure, model-fixture failure, and budget-exhaustion
   measurements unverified until current evidence contains those exact events.
