# Worked contrasts

These fictional examples teach claim boundaries; their numbers are not service defaults.

## Retry duration with and without an overall deadline

Local configuration permits three attempts of up to 12 seconds under a 30-second caller deadline.
The per-attempt settings permit up to 36 seconds before backoff. That is a lead: inspect the caller,
effective overrides and whether a shared deadline cancels the underlying request and releases
resources. A 20-second overall cap with working cancellation can disprove this particular lead.
Without those controls, source can support a conditional resource-retention risk. A dated,
representative experiment is needed to claim the risk occurred or estimate affected capacity.

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
worker calls `ledger.post` before acknowledging each queue message. Its caller permits three
12-second attempts, shares a 20-slot worker pool with account reads, and has no demonstrated
overall deadline or cancellation. A ledger slowdown could retain all 20 slots through retries,
delaying unrelated reads. This is a **supported design risk**, not evidence that production has
exhausted the pool. The same source shows a stable event ID on each message, but the persistence
contract and any downstream deduplication are unknown; do not recommend blind redelivery.

The application owner should first verify effective deadline overrides and whether cancellation
releases a worker slot. If those controls already bound the operation and protect reads, close this
lead within that scope. Otherwise compare two changes:

| Option | Benefit | Cost and remaining risk |
|---|---|---|
| Propagate one caller deadline, cancel outstanding attempts, and reserve/bound ledger concurrency | Stops slow ledger calls from occupying every shared slot | May reject ledger work sooner; must preserve an explicit retry/unknown-commit contract and verify cancellation actually releases resources |
| Add more worker replicas | Raises temporary capacity | Shared ledger saturation and retry amplification remain; cost grows and all replicas can still block |

Choose the first option **conditionally**, owned by the application team, because it interrupts the
shown propagation path instead of only increasing capacity. Before implementation, the owner must
settle the acceptable timeout and partial-commit semantics; this example supplies neither an SLO
nor approval to change production. The smallest useful proof is an authorized, same-version test
that delays `ledger.post` beyond the chosen overall deadline while running representative account
reads and a duplicate-delivery case. Record completed/failed user transactions, worker occupancy,
queue age, duplicate credits, and cancellation time. The proposal is falsified if reads still lose
their reserved capacity, workers stay occupied after cancellation, or redelivery duplicates a
business effect. Stop the experiment at the agreed queue-age or error bound, remove the injected
delay, and verify queue drain, read recovery, and ledger reconciliation before calling the test
recovered. The test result, load representativeness, effective overrides and downstream atomicity
remain unknown until measured; implementation and independent review remain separate work.
