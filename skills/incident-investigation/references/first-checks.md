# First checks on this stack

Read when naming the next check for a responder. Every row says where to look, what it tells you,
and what healthy and unhealthy look like, in the tools this team actually opens: Apps Manager for
PCF, Splunk for logs, Wavefront and PCF App Metrics for application metrics, the Cloud Run console
for GCP. Command-line equivalents are fallbacks for the few who have the CLI installed; never
assume a responder has it. `[sourced: operator statement 2026-09-02]` for the tool choices; the
exact names of views and tabs vary by Apps Manager and console version and are `[unverified]`
until the responder confirms what they see.

## PCF, in Apps Manager

| Look at | It tells you | Healthy | Unhealthy | CLI fallback |
|---|---|---|---|---|
| The app's **Events** list, newest first | What changed and when: pushes, restages, scaling, crashes, restarts, environment or route updates, with the actor and UTC time | Nothing newer than the last planned change | A push, restage, scale, or config update inside the onset window; repeated `crash` events; an actor nobody expected | `cf events <app>` |
| The **instances** table on the app overview | Per-instance state, CPU, memory, disk, uptime, and crash count | All instances `running`, memory well below the quota, uptime older than the onset | An instance `crashed`, `starting`, or flapping; memory pinned at the quota (a 137 exit is often, not always, out of memory); one instance hot while the others are calm | `cf app <app>` |
| The **Logs** view (recent tail) | The last few minutes of router (`RTR`) and application (`APP`) lines: status codes, response times, exceptions, pool waits | Steady 2xx/3xx at normal response times; no repeating exception | A burst of 5xx or long response times on `RTR` lines; `HikariPool` or connection waits; a stack trace repeating on one instance | `cf logs <app> --recent` |
| The app's **routes** and the bound **services** | Whether the route still maps here and which backing services are bound | Route present, services bound and healthy | Route missing or remapped; a binding changed inside the onset window | `cf routes`, `cf services` |
| The space's app list | Whether this is one app or many | Only the reported app is affected | Several apps in the space, org, or foundation failing at once: platform-side, escalate to the platform team with the evidence (`pcf-ops`) | `cf apps` |

For history beyond the log tail, take the timestamp and correlation ID to Splunk.

## Logs, in Splunk

Start from the team's catalog entry for the question when one exists (the query catalog in
`obs-logs`); otherwise:

| Question | Search shape | Healthy | Unhealthy |
|---|---|---|---|
| When did errors start, and is it worsening? | `index=<app index> sourcetype=<app> earliest=-2h \| timechart span=1m count by status` | Flat, mostly 2xx | The first minute the 5xx series leaves baseline is the onset bound; a rising slope is worsening |
| What is failing, in one request? | The same index filtered to one failing request or correlation ID, newest first | One clean request | The first exception, timeout, or pool wait in the chain; the dependency it names |
| Is it one instance or all? | `... \| stats count by instance_index, status` | Errors spread evenly | One instance carrying the errors: local; all instances together: shared cause |
| Did a dependency slow down? | The app's outbound-call log line, `timechart p95(duration) by dependency` | Flat | One dependency's latency rising before the app's errors did |

Splunk's search dialect and its traps live in `obs-logs` (its SPL reference); load it only when a
search has to be written from scratch.

## Application metrics, in Wavefront and PCF App Metrics

| Look at | It tells you | Healthy | Unhealthy |
|---|---|---|---|
| The app's request rate, error ratio, and latency percentiles (RED) | Whether users are hurting and since when | Latency and errors at baseline for this hour and weekday | Latency rising before errors: saturation; errors starting at a change time: the change |
| Per-instance container memory and CPU | Saturation and leaks | Flat, below the quota | Memory climbing to the quota then a restart: a leak or undersized quota; CPU low while latency is high: waiting on something, not working |
| The dependency's own dashboard | Whether the dependency is unhealthy on its side | Flat | Its server-side signals confirm; if they are flat, the path, region, or tenant is failing, not the dependency itself |

WQL specifics live in `obs-metrics` (its WQL reference). Wavefront is the live metrics UI for PCF
applications today; the Grafana, Mimir, Loki, and Tempo stack is additive and carries GCP workloads
and any service already instrumented with OpenTelemetry.

## Outside in

| Look at | It tells you |
|---|---|
| ThousandEyes synthetic tests for the route | Whether the failure is visible from outside, and from where |
| Akamai: the error reference number, `X-Cache`, and the WAF event log (`akamai-edge`) | Whether the edge, the cache, or a WAF rule is the failing layer before the origin |
| Moogsoft correlated alerts | Which other alerts fired together: the shape of the blast radius |

## GCP, in the Cloud Run console

| Look at | It tells you | CLI fallback |
|---|---|---|
| The service's **Revisions** tab | Which revision serves traffic and when it changed | `gcloud run revisions list --service <svc>` |
| The revision's **Logs** | Startup failures ("failed to listen on PORT"), request errors | `gcloud logging read` with the filter shapes in `gcp-ops` |
| The service's **Metrics** | Request count, latency, container instance count, memory | Cloud Monitoring; `obs-metrics` carries the Cloud Monitoring reference |

`gcp-ops` carries the read-only command shapes, the migration traps, and the rollback recommendation
form when the human decides to move traffic.

## Perishable first

Before anyone restarts, scales, or redeploys: the thread dump or heap evidence from the failing
instance, the per-instance state table, and the log tail for the failing instance. A restart
destroys all three and answers nothing.
