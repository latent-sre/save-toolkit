# Worked contrast: a slow ledger dependency

Fictional inputs, not service defaults: order submission must commit once or return a clear failure;
a slow ledger must not stop unrelated account reads. A worker calls `ledger.post` before queue
acknowledgement, permits three calls requesting 12-second timeouts, and shares a 20-slot pool with
reads. Client timeout enforcement, exception behavior, overall deadline and cancellation are unknown.

## What the source establishes

The nominal timeout sum is 36 seconds **only if** all three attempts use enforced 12-second limits.
A false return may allow another call; an uncaught exception stops the loop. Backoff, other work,
cancellation and resource release affect elapsed time and slot occupancy. "Three retries" can
mean four attempts; keep these conditions attached to calculations and findings tables.

Even a 20-second overall deadline can admit three early-failing attempts. A caller returning at
20 seconds does not prove downstream work stopped or released its slot. Inspect effective overrides,
deadline propagation and cancellation before claiming a bound.

Retries could exhaust the shared pool and delay reads: a **supported design risk**, not observed
production exhaustion. Stable event IDs do not prove persistent deduplication or safe redelivery.
Same-revision evidence that cancellation releases slots and protects reads can close this lead within
its tested scope; do not demand a named pattern such as a circuit breaker when existing controls work.

## Conditional improvement

If the effective controls do not protect reads, compare:

| Option | Benefit | Cost and remaining risk |
|---|---|---|
| Propagate one deadline, verify cancellation, and admit ledger work before shared-slot acquisition or reject/defer without retaining a shared slot | Can preserve capacity for account reads, including when ledger admission is overloaded | May reject ledger work sooner; preserve an explicit retry/unknown-commit contract and verify release of calls, permit waiters and retries |
| Add more worker replicas | Raises temporary capacity | Shared ledger saturation and retry amplification remain; cost grows and all replicas can still block |

Prefer the first option for this mechanism, conditional on the application owner settling the timeout
and partial-commit contract. The example supplies neither an SLO nor production authorization.

## Proof that exercises the protection

Propose an authorized, same-version test that overloads ledger admission and delays `ledger.post`
beyond the chosen deadline, while account reads and duplicate deliveries run. Representative demand
alone may never reach the admission limit. Count active ledger work, permit waiters and retries in
shared-slot occupancy; measure completed/failed transactions, queue age, duplicate credits and
cancellation time.

The proposal is falsified if reads lose reserved capacity, workers remain occupied after cancellation,
or redelivery duplicates an effect. Stop at agreed queue-age/error bounds, remove the delay, then verify
queue drain, read recovery and ledger reconciliation. Results, load representativeness and downstream
atomicity remain unknown until measured; implementation and independent review remain separate.
