# Signal patterns, symptom comparisons, and systemic analysis

Interpret evidence strictly within target, population, coverage, and window bounds. Correlation or
post-change improvement alone never proves causation, and an exhaustion mechanism never excludes the
upstream demand, dependency, or change that drove it.

## Symptom comparisons

Choose a comparison within confirmed access (for known PCF apps with confirmed view access, use
Apps Manager -> app -> Overview -> app events; otherwise request owner exports or safe tickets):

| Symptom | Useful first comparison | Decision impact |
|---|---|---|
| "Users cannot log in" | Compare failing vs working attempts by stage: page reachability, submit/MFA, callback, protected action | Narrows stage; denial after sign-in points to permissions/session. Never collect passwords, tokens, or cookies |
| "It fails sometimes" | Compare failure/success over the same interval by cohort, route, region, version, or request ID | Cohort differences lead; uniform rates keep shared paths open. Green aggregates never clear a minority |
| "Requests are slow" | Separate pre-work wait, processing, and downstream time against normal baseline | Total duration alone hides where delay sits; inspect a sample breakdown before sizing |
| "Monitor/Situation says down" | Compare failing/passing external vantages against in-network requests and platform state | External-only failure points to edge/DNS/network; treat Situation scope/start as hypothesis; restarting healthy apps worsens impact |
| "Data is old or wrong" | Compare one safe record's source, processed result, and published value/version with clock zones | Newer processed record + stale visible view narrows to publication/serving; stale processed narrows ingestion/processing; never substitute a summary count for one end-to-end record |
| "Job never finished" | Compare due time/zone, dispatch/start/progress events, and delivery/recipient readback | Matching readback at 08:20 after 08:00 finish proves receipt, not delivery latency/path (ask provider-acceptance + delivery events with zones); reconcile before any rerun |

## Dependency and signal patterns

- **Downstream & network splits:** Split caller errors/latency by downstream target before blaming client or dependency. Multiple callers failing together suggest a shared dependency. A dependency that looks fast from the caller on failing requests is not slow — count calls instead, and split flat aggregate dependency dashboards by failing region/route/account before clearing it.
- **429s, resets & TLS:** For `429`, identify which layer enforces the limit and compare caller request + retry volume against the limit's window. For connection refused/reset, compare multiple callers in the same window with proxy/listener records. For TLS/mTLS errors, compare presented hostname/chain with caller trust store and client certs even when traffic is flat. Confirm payload correctness separately from `200 OK` + fast latency (stale quotes/prices/positions return `200`).
- **Timing, hot instances & restarts:** Latency rising before errors fits waiting followed by timeouts — compare change exposure time against onset (earlier onset excludes a later change as initiator, not as an amplifier; pre-existing leaks do not prove rollback won't help via amplification/state recycle). A single hot instance points to routing skew, sticky sessions, or poison input as well as local faults; uniform instance failures leave shared dependencies and uniform code/config defects open. Restart time != deployed revision identity.
- **Pools, capacity & CPU:** `"Waiting to acquire a connection"` proves an acquisition wait at that instant — compare configured maximum, created, active/borrowed, idle/eligible, and waiting counts (`borrowed / maximum` = limit use; `maximum - borrowed` = unused configured capacity, NOT ready connections; waiting below max leaves creation/validation/lock/downstream-lease duration open). Capacity is a limit, never occupancy; match units/populations/windows before deriving ratios (`LB seconds` vs `app milliseconds` can reflect in-process queueing; `unreturned` count at one snapshot can still be in-flight requests). Low aggregate CPU with high latency leaves pool waits, hot instances, single-thread stalls, and per-core CPU throttling open.
- **Snapshots & telemetry coverage:** Repeated snapshots != uninterrupted duration; sample time != aggregation window; completion time != start time (an observed failure proves onset at or before that time, never after). Empty views or old last-event times prove missing coverage, not staleness or health. Fresh zero only covers what the metric defines and captures. Running instances never prove job completion or downstream effect; verify operation receipts.

## Systemic analysis (cascades, shared fate, and persistence)

Sketch affected callers, dependencies, queues, and shared failure domains (pool, partition, tenant,
cell, zone, DB, identity, network path) and compare with an unaffected cohort:

| Candidate mechanism | Discriminating check |
|---|---|
| Cascading timeouts | Did downstream latency rise before caller pool occupancy and caller timeouts on the same requests? |
| Retry amplification / herd | Compare total attempts per original request and retry burst timing vs successful work (are retries keeping the dependency down?) |
| Saturation collapse | Compare arrival rate, queue age, service time, and limits across onset |
| Poison item / stuck partition | Compare repeated failing item IDs, partition offset lag, and oldest-item age against healthy partitions |
| Control-loop feedback | Align autoscaler, health-check restart, or failover events with load/error spikes (controllers can amplify harm) |
| Shared dependency / domain | Trace common downstreams/quotas/paths across co-failing services (simultaneous alerts alone do not prove shared cause) |
| Self-sustaining degradation | First confirm trigger removal (did rollback/flag-off land and dependency load drop?), then check remaining backlog, retries, or cold caches |

Interrupt the mechanism (suppress retries, isolate poison partitions) while warning of destructive side
effects (dropping queued work loses data). Confirm recovery across affected partitions and cohorts over the full window, not just an improved aggregate mean.
