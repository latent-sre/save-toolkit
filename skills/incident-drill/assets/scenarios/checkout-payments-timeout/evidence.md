# Evidence pack — sanitized excerpts

Each section is one evidence file the on-call human releases to a lane. Release them in the
stages the scenario names; do not hand a lane the whole pack at once.

## 01-alert-CheckoutLatencyP95High.json

```json
{
  "alertname": "CheckoutLatencyP95High",
  "severity": "warning",
  "status": "firing",
  "startsAt": "2026-08-24T21:05:00Z",
  "labels": {
    "env": "prod",
    "org": "retail-prod",
    "space": "checkout",
    "app": "checkout",
    "team": "payments-platform"
  },
  "annotations": {
    "summary": "checkout p95 latency 2.9s above 1.5s threshold for 10 minutes",
    "expr": "histogram_quantile(0.95, sum by (le) (rate(http_server_request_duration_seconds_bucket{app=\"checkout\",route=\"/checkout\"}[5m]))) > 1.5",
    "for": "10m",
    "value": "2.9",
    "runbook_url": "https://runbooks.example.internal/checkout",
    "dashboard_url": "https://grafana.example.internal/d/checkout-overview"
  },
  "notification": {
    "route": "checkout-primary pager (warning: notify, no page)",
    "receivedAt": "2026-08-24T21:05:31Z"
  }
}
```

## 02-cf-app-checkout.txt

```text
$ cf app checkout          # sanitized excerpt supplied by the on-call human at 2026-08-24T21:12Z
Showing health and status for app checkout in org retail-prod / space checkout as oncall-reader...

name:              checkout
requested state:   started
routes:            checkout.apps.example.internal
last uploaded:     Mon 24 Aug 20:29:41 UTC 2026
stack:             cflinuxfs4
buildpacks:        python_buildpack

type:            web
sidecars:
instances:       4/4
memory usage:    512M
     state     since                  cpu    memory           disk           logging
#0   running   2026-08-24T20:31:02Z   61.3%  402.1M of 512M   288.4M of 1G   0B/s of 16K/s
#1   running   2026-08-24T20:31:05Z   58.9%  397.4M of 512M   288.4M of 1G   0B/s of 16K/s
#2   running   2026-08-24T20:31:07Z   63.0%  410.8M of 512M   288.4M of 1G   0B/s of 16K/s
#3   running   2026-08-24T20:31:09Z   60.2%  399.0M of 512M   288.4M of 1G   0B/s of 16K/s
```

## 03-cf-events-checkout.txt

```text
$ cf events checkout       # sanitized excerpt supplied by the on-call human at 2026-08-24T21:12Z
Getting events for app checkout in org retail-prod / space checkout as oncall-reader...

time                          event                       actor          description
2026-08-24T20:30:12Z          audit.app.restart           ci-deployer
2026-08-24T20:29:41Z          audit.app.droplet.create    ci-deployer    release tag v2.14.0 (pipeline checkout-deploy #1187)
2026-08-24T20:29:38Z          audit.app.update            ci-deployer    environment_json: PAYMENTS_TIMEOUT_S, INVENTORY_TIMEOUT_S, MAX_IN_FLIGHT (values not shown)
2026-08-11T14:02:10Z          audit.app.restart           ci-deployer
2026-08-11T14:01:44Z          audit.app.droplet.create    ci-deployer    release tag v2.13.2 (pipeline checkout-deploy #1142)
2026-08-04T09:40:03Z          audit.app.update            ci-deployer    health_check_http_endpoint: /healthz
```

## 04-cf-logs-recent.txt

```text
$ cf logs checkout --recent     # sanitized excerpt (order ids redacted), supplied by the on-call human at 2026-08-24T21:36Z
2026-08-24T21:33:12.41Z [RTR/3] OUT checkout.apps.example.internal - [2026-08-24T21:32:42.301Z] "POST /checkout HTTP/1.1" 502 0 24 "-" "storefront/7.2" "10.0.4.17:41522" "10.0.9.31:61042" x_forwarded_for:"-" x_forwarded_proto:"http" vcap_request_id:"[REDACTED]" response_time:30.104 gorouter_time:0.002 app_id:"[REDACTED]" app_index:"1" x_cf_routererror:"-"
2026-08-24T21:33:12.42Z [APP/PROC/WEB/1] ERR checkout order=[REDACTED] dependency_timeout=payments after=30.0s
2026-08-24T21:33:14.10Z [APP/PROC/WEB/2] ERR checkout order=[REDACTED] dependency_timeout=payments after=30.0s
2026-08-24T21:33:15.77Z [RTR/1] OUT checkout.apps.example.internal - [2026-08-24T21:33:00.884Z] "POST /checkout HTTP/1.1" 200 312 2874 "-" "storefront/7.2" "10.0.4.17:41530" "10.0.9.28:61042" x_forwarded_for:"-" x_forwarded_proto:"http" vcap_request_id:"[REDACTED]" response_time:14.882 gorouter_time:0.002 app_id:"[REDACTED]" app_index:"0" x_cf_routererror:"-"
2026-08-24T21:33:16.03Z [APP/PROC/WEB/0] OUT checkout order=[REDACTED] authorized=[REDACTED] reserved=[REDACTED]
2026-08-24T21:33:20.02Z [RTR/0] OUT checkout.apps.example.internal - [2026-08-24T21:32:49.917Z] "POST /checkout HTTP/1.1" 502 0 24 "-" "storefront/7.2" "10.0.4.18:53012" "10.0.9.33:61042" x_forwarded_for:"-" x_forwarded_proto:"http" vcap_request_id:"[REDACTED]" response_time:30.097 gorouter_time:0.002 app_id:"[REDACTED]" app_index:"3" x_cf_routererror:"-"
2026-08-24T21:33:20.03Z [APP/PROC/WEB/3] ERR checkout order=[REDACTED] dependency_timeout=payments after=30.0s
2026-08-24T21:33:41.55Z [RTR/2] OUT checkout.apps.example.internal - [2026-08-24T21:33:41.550Z] "GET /healthz HTTP/1.1" 200 0 41 "-" "diego-healthcheck" "10.0.9.31:33120" "10.0.9.31:61042" x_forwarded_for:"-" x_forwarded_proto:"http" vcap_request_id:"[REDACTED]" response_time:0.004 gorouter_time:0.001 app_id:"[REDACTED]" app_index:"2" x_cf_routererror:"-"
2026-08-24T21:34:02.88Z [RTR/2] OUT checkout.apps.example.internal - [2026-08-24T21:33:50.100Z] "POST /checkout HTTP/1.1" 200 312 2874 "-" "storefront/7.2" "10.0.4.17:41544" "10.0.9.31:61042" x_forwarded_for:"-" x_forwarded_proto:"http" vcap_request_id:"[REDACTED]" response_time:12.780 gorouter_time:0.002 app_id:"[REDACTED]" app_index:"2" x_cf_routererror:"-"
2026-08-24T21:34:44.19Z [RTR/1] OUT checkout.apps.example.internal - [2026-08-24T21:34:14.071Z] "POST /checkout HTTP/1.1" 502 0 24 "-" "storefront/7.2" "10.0.4.18:53040" "10.0.9.28:61042" x_forwarded_for:"-" x_forwarded_proto:"http" vcap_request_id:"[REDACTED]" response_time:30.118 gorouter_time:0.002 app_id:"[REDACTED]" app_index:"1" x_cf_routererror:"-"
2026-08-24T21:34:44.20Z [APP/PROC/WEB/1] ERR checkout order=[REDACTED] dependency_timeout=payments after=30.0s
2026-08-24T21:35:30.67Z [APP/PROC/WEB/0] ERR checkout order=[REDACTED] dependency_timeout=payments after=30.0s
2026-08-24T21:35:30.68Z [RTR/0] OUT checkout.apps.example.internal - [2026-08-24T21:35:00.551Z] "POST /checkout HTTP/1.1" 502 0 24 "-" "storefront/7.2" "10.0.4.19:44210" "10.0.9.33:61042" x_forwarded_for:"-" x_forwarded_proto:"http" vcap_request_id:"[REDACTED]" response_time:30.121 gorouter_time:0.002 app_id:"[REDACTED]" app_index:"0" x_cf_routererror:"-"
# note from on-call: every 502 in the window carries response_time ~30.1s and a matching
# dependency_timeout=payments app line; no crash, restart, or x_cf_routererror entries; /healthz stays 200.
```

## 05-grafana-checkout-overview.md

```markdown
# Grafana `checkout-overview` — values read off the panels by the on-call human (synthetic)

Panels sampled at 15-minute points, prod, all four instances. SLO: availability 99.5% (30-day),
p95 latency < 1.5 s. Error budget burn rate = observed 5xx fraction ÷ 0.5%.

| Time (UTC) | req/s | 5xx / all | p95 latency | in-flight checkouts per instance (avg / max) | burn rate |
|---|---|---|---|---|---|
| 20:00 | 42 | 0.3% | 0.61 s | 1.9 / 3 | 0.6× |
| 20:15 | 43 | 0.3% | 0.63 s | 2.0 / 3 | 0.6× |
| **20:31 — deploy of v2.14.0 completes (all four instances restarted)** | | | | | |
| 20:45 | 44 | 0.4% | 0.88 s | 3.1 / 5 | 0.8× |
| **20:58 — payments instance #2 restarted (payments team's change, not ours)** | | | | | |
| 21:00 | 58 | 1.1% | 2.1 s | 5.6 / 8 | 2.2× |
| **21:05 — `CheckoutLatencyP95High` (warning) fires** | | | | | |
| 21:20 | 71 | 2.6% | 5.4 s | 7.8 / 8 | 5.2× |
| 21:35 | 79 | 4.2% | 8.4 s | 8.0 / 8 | 8.4× |

Read at 21:36Z by the on-call human: in-flight checkouts are pinned at the `MAX_IN_FLIGHT` cap of
8 on every instance; the 5xx series is entirely 502s; CPU and memory are flat; no instance
restarts since 20:31. The `CheckoutErrorRateSLOBurn` page rule (burn rate > 8× over 5 m and > 2×
over 1 h) is expected to fire at about 21:38Z.
```

## 06-payments-dependency-dashboard.md

```markdown
# Payments team dashboard `payments-authorizations` — read by the on-call human at 21:40Z (synthetic)

The payments service is owned by the payments team (pager `payments-primary`). Its SLO is p99
authorization latency < 6 s and availability 99.9%. Their dashboard shows:

| Time (UTC) | authorizations/s | p50 | p99 | p99.9 | 5xx | requests exceeding 10 s |
|---|---|---|---|---|---|---|
| 20:00 | 40 | 0.42 s | 4.8 s | 5.6 s | 0.02% | 0.00% |
| 20:45 | 42 | 0.43 s | 4.9 s | 5.7 s | 0.02% | 0.00% |
| **20:58 — payments instance #2 restarted after a memory alert; it rejoined the pool at 20:59** | | | | | |
| 21:00 | 55 | 0.45 s | 5.0 s | > 10 s (panel caps) | 0.02% | 0.8% |
| 21:20 | 68 | 0.47 s | 5.1 s | > 10 s (panel caps) | 0.02% | 0.8% |
| 21:35 | 76 | 0.48 s | 5.1 s | > 10 s (panel caps) | 0.02% | 0.8% |

Per-instance breakdown at 21:35: instances #0, #1, #3 show 0.00% of requests exceeding 10 s;
instance #2 shows 3.2% of its requests never completing within the panel's 10 s cap (they hold
the connection open until the caller gives up). Payments' p99 is inside its SLO, so no payments
alert has fired. The payments on-call has not been paged.
```

## 07-post-mitigation-readings.md

```markdown
# Post-mitigation readings — Grafana `checkout-overview` and logs, read by Alex (synthetic)

Rolling restage completed 22:01:09Z (4/4 running). Verification window per the gate: 5 minutes
after 4/4 running, then hold.

| Time (UTC) | req/s | 5xx / all | p95 latency | in-flight per instance (avg / max of 8) | burn rate vs 0.5% |
|---|---|---|---|---|---|
| 21:50 (pre-change) | 81 | 4.4% | 8.6 s | 8.0 / 8 | 8.8× |
| 21:58 (2 of 4 restaged) | 80 | 2.1% | 4.1 s | 5.9 / 8 | 4.2× |
| 22:05 | 79 | 0.9% | 1.1 s | 2.6 / 4 | 1.8× |
| 22:15 | 77 | 0.5% | 0.66 s | 2.3 / 4 | 1.0× |
| 22:30 | 72 | 0.4% | 0.62 s | 2.1 / 3 | 0.8× |
| 22:45 | 66 | 0.4% | 0.60 s | 1.9 / 3 | 0.8× |

- `CheckoutErrorRateSLOBurn` resolved at 22:12:05Z (burn under 2× over 5 m) and has not re-fired.
- `CheckoutLatencyP95High` resolved at 22:17:00Z.
- Logs 22:05–22:45: `dependency_timeout=payments after=2.0s` lines at roughly 0.8% of checkouts
  (the accepted CHK-4412 regression class, now bounded at 2 s); the remaining 502s are those. No
  `after=30.0s` lines since 22:01. No inventory errors. CPU 19–23%, memory ~300 M per instance.
- Payments-primary paged at 21:50Z; acknowledged 21:58Z; they restarted payments instance #2 at
  22:20Z, after which "requests exceeding 10 s" on their dashboard reads 0.00% (22:30 onward) and
  checkout's `after=2.0s` lines fall to about 0.05%.
```
