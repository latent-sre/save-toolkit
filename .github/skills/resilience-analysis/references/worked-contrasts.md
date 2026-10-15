# Worked contrasts

These fictional examples teach claim boundaries; their numbers are not service defaults.

## Retry duration with and without an overall deadline

A loop permits up to three calls and passes `timeout_seconds=12` to an unseen client. This proves
the call limit and requested timeout, not enforcement. A false return may permit another call;
an uncaught client exception stops the loop. The nominal timeout sum is 36 seconds, conditional
on three attempts with enforced 12-second limits; elapsed time and slot occupancy also depend on
backoff, other work, cancellation and resource release. "Three retries" may mean four attempts.
Keep these conditions attached when reusing the calculation, including in a findings table.

A 20-second overall deadline does not make a third attempt unreachable: early failures can allow
all three attempts before it expires. Conversely, a caller returning at 20 seconds does not prove
underlying work stopped or released a shared slot. Inspect deadline propagation and cancellation.
Same-revision evidence of cancellation, slot release and protected unrelated work can close this
particular resource-retention lead within the tested conditions. Without it, source can support a
conditional risk; a dated, representative experiment is needed to claim observed impact or capacity.

An improvement must explain deadline propagation and resource release; naming a circuit breaker
does not establish that it addresses this failure. Verify behavior while the dependency is slow
and after it recovers, including unrelated work sharing the pool.

## Restore evidence versus recovery failure

A record shows successful daily backups. No restore result is supplied. Classify recoverability as
a verification gap, not proven backup failure. Request the relevant restore evidence or propose a
bounded rehearsal covering data correctness and the business transaction. Recovery objectives are
owner-supplied requirements; never invent them or infer success from a backup job's exit code.

## Replica count versus independent resilience

Three app instances use one database endpoint. Establish what that endpoint represents: it may
hide an independently managed failover service. Trace availability, degraded behavior, recovery
dependencies and surviving capacity before concluding there is an unacceptable single point of
failure. Pin current configuration separately from a diagram or older incident export.

## No material finding in a bounded slice

An inspected caller propagates a deadline, cancels downstream work and bounds concurrency.
Supplied same-version evidence exercises slow-dependency recovery and unrelated request behavior
within the accepted limits. It is reasonable to report no material finding for that path, while
preserving the supplied evidence's provenance and uninspected paths. This is not whole-service
certification, a merge verdict or production authorization.

## Complete engineering proposal: slow ledger dependency

This fictional assessment starts with an owner-supplied requirement: checkout must either commit
once or return a clear failure; a slow ledger must not stop unrelated account reads. The inspected
worker calls `ledger.post` before acknowledging each queue message. Its caller permits up to three
calls requesting 12-second timeouts; client enforcement and exception behavior are unknown. It
shares a 20-slot worker pool with account reads and has no demonstrated overall deadline or
cancellation. A ledger slowdown could retain all 20 slots through retries,
delaying unrelated reads. This is a **supported design risk**, not evidence that production has
exhausted the pool. The same source shows a stable event ID on each message, but the persistence
contract and any downstream deduplication are unknown; do not recommend blind redelivery.

The application owner should first verify effective deadline overrides and whether cancellation
releases a worker slot. If those controls already bound the operation and protect reads, close this
lead within that scope. Otherwise compare two changes:

| Option | Benefit | Cost and remaining risk |
|---|---|---|
| Propagate one deadline, verify cancellation, and admit ledger work before shared-slot acquisition or reject/defer without retaining a shared slot | Can preserve capacity for account reads, including when ledger admission is overloaded | May reject ledger work sooner; preserve an explicit retry/unknown-commit contract and verify release of calls, permit waiters and retries |
| Add more worker replicas | Raises temporary capacity | Shared ledger saturation and retry amplification remain; cost grows and all replicas can still block |

Choose the first option **conditionally**, owned by the application team, because it interrupts the
shown propagation path instead of only increasing capacity. Before implementation, the owner must
settle the acceptable timeout and partial-commit semantics; this example supplies neither an SLO
nor approval to change production. The smallest useful proof is an authorized, same-version test
that overloads ledger admission and delays `ledger.post` beyond the chosen overall deadline while
running representative account reads and a duplicate-delivery case. Count all ledger-owned slots,
including permit waiters and retries. Record completed/failed user transactions, worker occupancy,
queue age, duplicate credits, and cancellation time. The proposal is falsified if reads still lose
their reserved capacity, workers stay occupied after cancellation, or redelivery duplicates a
business effect. Stop the experiment at the agreed queue-age or error bound, remove the injected
delay, and verify queue drain, read recovery, and ledger reconciliation before calling the test
recovered. The test result, load representativeness, effective overrides and downstream atomicity
remain unknown until measured; implementation and independent review remain separate work.
