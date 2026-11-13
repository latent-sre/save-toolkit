# Worked contrast: a slow ledger dependency

Fictional inputs, not service defaults: order submission must commit once or return a clear failure;
a slow ledger must not stop unrelated account reads. A record says a worker calls `ledger.post`
before queue acknowledgement and "retries up to three times at 12 seconds per attempt." It shares
a 20-slot pool with reads. Total-call interpretation, timeout enforcement, exception behavior,
overall deadline and cancellation are unknown.

## Assessment excerpt

**Retry paths:** if the retry condition accepts a false return and budget remains, another call may
follow. An uncaught client exception exits the path; caught exceptions depend on their handlers.
The unseen client's timeout-to-return/exception behavior is unknown.

**Retry-count basis:** the wording does not establish whether the maximum is three total calls or
an initial call plus three retries (four total). These are alternative interpretations, not two
source-reported limits; the actual number of calls is unknown. A helper's "three calls total"
summary does not resolve the ambiguity.

**Timing and capacity basis:** if the respective maximum number of calls occurs and every call
lasts the reported 12 seconds, the alternatives sum to `3 x 12 = 36 seconds` or `4 x 12 = 48 seconds`.
The source establishes neither those durations nor timeout enforcement. These are calculations
under the two count interpretations, not source-reported durations or elapsed-time/occupancy bounds.
Backoff, other work, cancellation and slot release remain unknown. Correct a helper calling either
sum a sourced worst case before endorsing its summary or reusing the figures.

Even a 20-second overall deadline can admit three early-failing attempts. A caller returning at
20 seconds does not prove downstream work stopped or released its slot. Inspect effective overrides,
deadline propagation and cancellation before claiming a bound.

If a later same-revision record establishes a 20-second overall deadline and release within it,
retain that overall scope. It does not establish a 20-second mean slot residence. The illustrative
`20 ledger-only slots / hypothetical 20-second mean residence = 1 post/second` assumes every slot
is available to ledger work, one slot per post and that mean residence; shared account reads reduce available slots.
It is not a measured saturation threshold or general capacity ceiling. An overload check needs
observed completion/occupancy or an explicit hypothetical workload, not a maximum substituted for
the mean.

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
and partial-commit contract. Select the deadline against the owner's outcome requirement and verify
its enforcement and slot release; the nominal 36/48-second sums under the three/four-call
interpretations are not demonstrated worst cases for
setting it. The example supplies neither an SLO nor production authorization.

## Proof that exercises the protection

Propose an authorized, same-version test that overloads ledger admission and delays `ledger.post`
beyond the chosen deadline, while account reads and duplicate deliveries run. Measure shared-slot
occupancy, completed/failed transactions, queue age, duplicate credits and cancellation time.

The proposal is falsified if reads lose reserved capacity, workers remain occupied after cancellation,
or redelivery duplicates an effect. Stop at agreed queue-age/error bounds, remove the delay, then verify
queue drain, read recovery and ledger reconciliation. Results, load representativeness and downstream
atomicity remain unknown until measured; implementation and independent review remain separate.
