# Signal patterns

Read when interpreting a pasted metric, log, thread dump, dashboard, or timing. Each pattern moves a
candidate up or down and names the check that settles it; none is a diagnosis on its own. For
multi-service impact or degradation that outlives its trigger, also read
[systemic analysis](./systemic-analysis.md).

## Dependencies

Most of this team's incidents trace to a dependency — most often order management, the trading
apps, or the quote plant — so test the dependency candidate early, not last, and work it with that
dependency's team.

- errors or timeouts on calls to one dependency while other calls stay healthy point at that
  dependency or at the app's client for it (its pool, timeout, or credentials): split the caller's
  errors and latency by downstream target before blaming either;
- several services failing together often share one dependency: find what they all call before
  chasing each one; other teams reporting the same issue is the same signal;
- a dependency that is fast from the caller's side, for the failing requests, is not slow however
  many times it is called — count the calls instead; its own flat dashboard clears only the series
  it covers, so it stays open until timings split by the failing region, route, or account type
  are compared;
- throttling (429), connection refused or reset, or certificate errors from a dependency point at
  its limits, availability, or credentials rather than the app's code — unless your own call volume
  rose: check its status, recent changes, and certificate dates with its team;
- retries against a struggling dependency multiply its load and can keep it down after the trigger
  is gone: compare the caller's retry rate with the dependency's load;
- a dependency's maintenance window or change can land as your incident: ask its team what changed
  and when, and compare that with observed onset;
- a normal status code and latency do not prove correct content: a stale quote, wrong price, or
  wrong position can come back fast with a 200 — check the content itself.

## Other patterns

- latency rising before errors reads as waiting, then timeouts: saturation moves up and a change
  at onset stays in play — compare the change with observed onset, then the affected requests'
  waits and limits;
- one hot instance among calm ones is instance-scoped impact, not yet a local cause: routing
  skew, sticky sessions, or poison input can land a shared fault on one process, so compare
  routing, inputs, and resources before calling it local; all instances together is shared,
  though shared data or a shared dependency also hits every instance alike;
- a sampled thread waiting to *get* a connection says that request waited at that instant, not
  that the pool is the bottleneck: wait duration and the pool's active, maximum, and waiting
  counts settle that, and without them exhaustion is a candidate, not a finding; a thread
  *holding* a connection while it waits on a socket says why the pool is held;
- a load balancer that sees seconds where the container logs milliseconds is time spent outside
  the container;
- low aggregate CPU with high latency leaves waiting, per-core saturation, and CPU throttling
  open — a blocked pool, one hot instance, or one saturated thread hides under a low average, so
  check the affected requests' waits and the instance's CPU limit or per-core usage;
- an old last-event time or an empty view is a missing observation: it proves neither staleness,
  a broken pipeline, nor health — check coverage and signal arrival;
- the trigger is gone — rolled back, flag off — and the service is still degraded: confirm the
  removal took effect, then test for a self-sustaining mechanism (retries, a queue backlog, cold
  caches, a control loop reacting to its own effect): did load on the dependency fall when the
  trigger was removed?
