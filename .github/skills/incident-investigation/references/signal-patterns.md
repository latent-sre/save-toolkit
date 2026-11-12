# Signal patterns

Patterns guide comparisons; evidence may change ranking or leave it unchanged. For multi-service
impact or harm outliving its trigger, also read [systemic analysis](./systemic-analysis.md).

For a comparison, state the observed difference, the causes still compatible with it, and the next
check that distinguishes those causes. Timing or improvement after a change alone does not attribute
the outcome to that change. Establishing a mechanism such as exhaustion does not exclude the
dependency, demand, or change that produced it.

## Dependencies

- errors or timeouts on calls to one dependency while other calls stay healthy point at that
  dependency or at the app's client for it (its pool, timeout, or credentials): split the caller's
  errors and latency by downstream target before blaming either;
- several services failing together suggest a shared dependency; verify their common calls;
- a dependency that is fast from the caller's side, for the failing requests, is not slow however
  many times it is called — count the calls instead; its own flat dashboard clears only the series
  it covers, so it stays open until timings split by the failing region, route, or account type
  are compared;
- throttling (429), connection refused or reset, or certificate errors from a dependency point at
  its limits, availability, or credentials rather than the app's code — unless your own call volume
  rose: check its status, recent changes, and certificate dates with its team;
- retries against a struggling dependency multiply its load and can keep it down after the trigger
  is gone: compare the caller's retry rate with the dependency's load;
- a normal status code and latency do not prove correct content: a stale quote, wrong price, or
  wrong position can come back fast with a 200 — check the content itself.

## Other patterns

- latency rising before errors is consistent with waiting followed by timeouts, among other
  mechanisms. Compare the affected requests' waits, processing and downstream timing with limits;
  compare any change's exposure time with observed onset before ranking it;
- one hot instance among calm ones is instance-scoped impact, not yet a local cause: routing
  skew, sticky sessions, or poison input can land a shared fault on one process, so compare
  routing, inputs, and resources before calling it local. Uniform impact across instances leaves
  both shared resources and the same local defect or configuration on each instance open; compare
  their revisions, inputs and dependency paths before locating the cause;
- a restart timestamp establishes a restart, not its cause or deployed revision. Compare actual
  revision identities before treating a restarted cohort as the new-code cohort;
- a sampled thread waiting to *get* a connection establishes an acquisition wait at that instant.
  Compare wait duration with separately observed configured maximum, created, borrowed and
  idle/eligible connections for that pool. Borrowed count divided by the matching configured
  maximum measures use of the limit; their difference is unused configured capacity, not a count
  of ready connections. Waiting below that maximum leaves creation, validation, acquisition-path
  contention and other client limits open. Ask the owner for the missing stage's observations;
  neither low occupancy nor long acquisition waits alone locate or exclude the bottleneck. A
  holder's downstream wait can explain its lease duration without explaining every waiter's delay;
- capacity is a limit, not observed occupancy or a count of workers. Combine counts only when their
  units, population, and observation window match; otherwise the derived count stays unknown.
  A count without the relevant denominator or impact bound does not establish that impact is small;
- load-balancer seconds versus application-log milliseconds can reflect time outside the logged
  interval, including in-process queueing. Match the same request and timer boundaries before
  locating the delay;
- repeated snapshots establish repeated observations, not uninterrupted duration. A sample's timestamp
  does not replace its aggregation window, and a later fresh view does not establish an earlier view's freshness.
  Completion time does not establish start time. An observed failure bounds onset at or before that
  observation, not at or after it;
- low aggregate CPU with high latency leaves waiting, per-core saturation, and CPU throttling
  open — a blocked pool, one hot instance, or one saturated thread hides under a low average, so
  check the affected requests' waits and the instance's CPU limit or per-core usage;
- an old last-event time or an empty view is a missing observation: it proves neither staleness,
  a broken pipeline, nor health — check coverage and signal arrival;
- earlier onset excludes a later change as the initiator of that earlier symptom, not as an amplifier
  of later impact. Old-version failures do not exclude shared deployment effects. A pre-existing
  leak does not prove rollback cannot help: it may remove amplification or recycle affected state.
  Unreturned connections may still be legitimately in flight; check owner completion and return
  behavior before calling a gap a leak. A sample does not establish permanence or exclude later reclamation;
- a fresh zero covers the metric's outcome definition and window. It does not exclude user failures
  that the metric may not count; absent errors cannot identify which telemetry component is faulty;
- a running instance does not establish that a job was accepted, completed, or had its intended effect;
  use operation-bound receipts and outcome evidence for those claims;
- degradation after rollback/flag-off: confirm effective removal, then test sustaining mechanisms
  under [systemic analysis](./systemic-analysis.md). Did dependency load actually fall?
