# Signal characterization — read the system before explaining it

Use this companion when the incident record lacks an exact start time, blast radius, trend, or a
trusted baseline for service health. Pull signals from the team's active logs, metrics, dashboards,
platforms, and synthetics; this reference defines what to establish, not backend query syntax.

## Golden signals

| Signal | Question |
|---|---|
| **Latency** | How long does work take? Split successful and failed requests. |
| **Traffic** | How much demand is arriving—requests, messages, or jobs per second? |
| **Errors** | What fraction fails, times out, or returns incorrect results? |
| **Saturation** | Which finite resource—CPU, memory, threads, queues, pools, or connections—is near its limit? |

Ownership map only—not a load: the `stack-profile` observability reference names which backend
serves each signal today; the `obs-*` skills own the queries. Do not assume a vendor from this file.

Use **RED**—rate, errors, duration—for request-driven services and **USE**—utilization, saturation,
errors—for resources.

## Ask what changed

Align the impact start with:

- recent deploys or releases (`cf events`, the release pipeline, and `git log`);
- configuration or feature-flag changes;
- PCF platform events such as cell evacuation, quota, or certificate rotation;
- traffic shifts, new clients, retries, or batch work;
- dependency incidents or vendor status events;
- certificate, credential, or secret expiries; and
- database migrations or data changes.

A matching timestamp makes a change a priority hypothesis, not a proven cause.

## Interpret the shape

1. **Errors and latency rise together:** inspect the application and downstream dependencies.
2. **Saturation rises, then latency, then errors:** investigate resource exhaustion, capacity, or a
   leak; check `cf app` instance memory and `cf events` for OOM restarts.
3. **Traffic rises before latency and errors:** investigate load, capacity, limits, and missing
   backpressure.
4. **Errors rise while traffic and latency stay flat:** investigate logic, deploy, or configuration
   rather than assuming load.
5. **Internal signals stay flat while users report impact:** inspect the external path, region, DNS,
   routing, and synthetic-probe or health-endpoint evidence.

Return the exact start time, blast radius, and trend—worsening, stable, or recovering—with evidence
labels. Those fields determine whether first response can continue or hypothesis investigation has
enough foundation to begin.

```text
q_iisc_9d4f
```
