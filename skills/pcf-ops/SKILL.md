---
name: pcf-ops
description: >-
  Investigate application-side PCF/TAS failures and plan human-executed PCF deploys, blue-green
  cutovers, scaling, and rollbacks. Triggers: 'the app is crashing', 'why is my app 502-ing',
  'deploy this app to PCF', 'roll back or scale this PCF app'. Not for foundation-wide Diego/Gorouter
  repairs (escalate to the platform team with evidence) or gate verdicts (production-change-gate).
compatibility: Requires Apps Manager access to the target PCF foundation; the cf v8 equivalents need that CLI installed
argument-hint: "[the app, platform symptom, or deploy/rollback plan]"
---

# PCF / TAS operations and deploy planning (cf CLI v8)

Our apps run on PCF (VMware TAS / Elastic Application Runtime). Stay on the application side:
observe the app, distinguish app faults from platform-wide symptoms, and prepare deploy, scale, or
rollback plans. Never operate foundation internals (BOSH, Ops Manager, Diego cells, Gorouter,
CredHub/UAA), and **never execute state-changing commands** — a human release owner runs them after
approval under `production-change-gate`.

## First look (Apps Manager & `cf` v8)

The team works primarily in Apps Manager; `cf` v8 is the equivalent where installed. Confirm the
target foundation, org, and space before reading any app data.

| Question | Apps Manager | `cf` equivalent |
|---|---|---|
| Right foundation/org/space? | Foundation URL, then org/space picker | `cf target` |
| Running, how many instances? | **Overview** instance table: state, CPU, memory each | `cf app <app>` |
| What changed, and who? | App **Overview** events: crash, restart, scale, update, with times | `cf events <app>` |
| What do recent logs say? | **Observability > Logs**, without pressing Play (live stream) | `cf logs <app> --recent` |

- `sre-assistant` may run only bare `cf target`, `cf app <app>`, `cf events <app>`, `cf logs <app> --recent`,
  and `cf revisions <app>` (never live `cf logs` tails or target-changing flags), and must mask
  authentication usernames before returning output. Ask the human for Apps Manager views or sanitized
  excerpts when CLI access or output protection is unavailable.
- `cf logs --recent` and Apps Manager **Logs** pull from Log Cache (capped at ~1,000 lines and pruned
  by memory, not time). Record the interval actually covered, and use **Splunk** (`obs-analysis`) for history.
- A crash/OOM, restage, scale, or `audit.app.update` / `droplet.create` in **Overview** events or
  **Application > Revisions** (`cf revisions <app>`) at onset is the first change lead to check.

## Drill in & credential-bearing reads (human-only)

| Question | Apps Manager | Human-run `cf` |
|---|---|---|
| GUID and processes | **Overview** | `cf app <app> --guid` |
| Per-instance state/CPU/mem/disk | **Overview** instances | `cf curl /v3/apps/<guid>/processes/web/stats` |
| Routes | **Networking > Routes** | `cf routes` |
| Services and plan | **Application > Services** | `cf services`; `cf service <name>` |

- Never run or request `cf env`, `cf service-key`, `CF_TRACE`, singular `cf revision`, or an
  expanded row in Apps Manager **Application > Revisions** (they expose environment variables and
  credentials). A human captures and sanitizes only the smallest needed excerpt outside agent context.
- Treat `cf ssh` (including database port-forwarding) as privileged Tier-2/3 shell access, never
  read-only triage; hand the human release owner the exact target, purpose, and exit/rollback plan.
- For CPU or memory over time (since `cf curl` is instantaneous), use **PCF App Metrics** or Grafana.

## App-side vs. platform-side escalation

If evidence points to an app release or config, continue app-side triage with the application owner.
Escalate a credible platform signal (Diego cell evacuation coinciding with instance loss, widespread
502s across apps, Gorouter cert/clock-skew errors, SSH port 2222 timeouts) to the platform team with
the observed foundation, org, space, app, affected routes/instances, UTC window/trend, relevant
events/logs/changes, and open hypotheses.

## Read the matching reference

| Need | Reference |
|---|---|
| Crashes, exit status 137, OOM, `$PORT`, health checks, Spring Boot management port, or Java buildpack memory sizing | [Application crashes and health checks](./references/application-crashes-and-health-checks.md) |
| `X-Cf-RouterError`, 404/502/503, keep-alive races, connection limits, route services, or cert/clock-skew | [Router errors](./references/router-errors.md) |
| State-changing command effects, restart vs. restage, blue-green/rolling/canary deploy plans, scaling, or rollback limits | [Deploys, scaling, and rollback](./references/deploys-scaling-and-rollback.md) |
