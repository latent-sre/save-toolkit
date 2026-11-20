---
name: pcf-ops
description: >-
  Investigate application-side PCF/TAS failures with cf app, events, logs, and routes, and
  distinguish app faults from platform-wide symptoms. Triggers: 'the app is crashing', 'why is
  my app 502-ing', 'exit code 137', 'X-Cf-RouterError'. Not for widespread Diego/Gorouter failures, which go to the platform team with evidence.
compatibility: Requires Apps Manager access to the target PCF foundation; the cf v8 equivalents need that CLI installed
argument-hint: "[the app or platform symptom]"
---

# PCF / TAS application-side triage (cf CLI v8)

Our apps run on PCF (VMware Tanzu Application Service, later Tanzu Platform for Cloud Foundry, now
Elastic Application Runtime for VMware Tanzu Platform). This skill stays on the application side:
observe the app and assemble evidence; never operate the foundation. State-changing commands belong
to a human release owner with exact approval evidence.

> **First look.** This team works in Apps Manager; `cf` v8 is the equivalent where installed.
>
> | Question | Apps Manager | `cf` equivalent |
> |---|---|---|
> | Right foundation/org/space? | foundation URL, then the org/space picker | `cf target` |
> | Running, how many instances? | **Overview** instance table: state, CPU, memory each | `cf app <app>` |
> | What changed, and who? | the app **Overview** page's events: crash, restart, scale, update, with times | `cf events <app>` |
> | What do recent logs say? | **Observability > Logs**, without pressing Play (Play starts a live stream) | `cf logs <app> --recent` |

>
> Work the rows in that order, and confirm the foundation, org, and space against the expected ones
> before reading any app or log data — evidence from the wrong target is worse than none.

These views cover only what they retain: record each one's actual interval and truncation, and an
event missing from a partial record is not excluded.

For `sre-assistant`, the command grant is bare `cf target`, `cf app <app>`, `cf events <app>`,
`cf logs <app> --recent`, and `cf revisions <app>` for the named app; no live tail, target flags,
inventory expansion, or remediation. The guard checks command syntax only: the protected, masked
output path (the username in target output included) and the target confirmation come from the
agent's own rules and caller-supplied evidence, and without them the agent asks for the Apps Manager
view or a sanitized observation. An absent or unauthenticated CLI is an access gap, never an
observed platform failure.

## App-side vs platform-side (know your lane)

- If the evidence points to an app release or configuration, continue app-side triage with the
  application owner.
- Escalate a credible platform signal even when only one app is visible. For example, hand off a
  Diego cell evacuation that coincides with loss of an instance on that cell. Ask the platform
  owner to verify cell health and whether other apps were affected. Keep wider impact unknown
  until verified.
- When several apps fail together, involve the platform and relevant dependency owners. A shared
  database, network or release can also explain broad impact.

Give the platform owner the observed foundation, org, space, app and affected routes or instances,
symptom, UTC window and trend (first observation or confirmed onset), relevant events, logs and
recent changes. Include the signal prompting escalation, such as a cell failure, widespread 502s,
certificate or clock errors, or reported SSH timeouts on port 2222, and which hypotheses remain open.

## "What changed?" — the highest-value read

A crash/OOM, restage, scale, or `audit.app.update`/`...droplet.create` in the **Overview** events at
the incident start is the prime suspect. **Application > Revisions** (`cf revisions <app>`) lists
current and stopped revisions. Correlate them with the release pipeline and repository history;
temporal alignment alone is not proof.

## Logs

`cf logs` without `--recent` is a live tail and is outside the SRE grant. `cf logs --recent` asks for
the newest 1000 log lines, and Log Cache prunes by memory and a per-source cap, so the window covered
varies with log volume; Apps Manager's **Logs** view has no guaranteed window either. For history go to
**Splunk** (`obs-analysis` has the query shapes) with the timestamp and correlation ID.

## Read only the detail the symptom needs

A human or approved network capture point supplies route headers; agents do not turn an untrusted
route into an egress request. Load every row that matches the request or the evidence so far.

| If the request involves… | Read first |
|---|---|
| App crashes, status 137, OOM evidence, JVM memory sizing, `$PORT`, or liveness/readiness health checks | [Application crashes and health checks](./references/application-crashes-and-health-checks.md) |
| `X-Cf-RouterError`, 404/502/503 interpretation, keep-alive failures, connection limits, route services, or certificate/clock-skew symptoms | [Router errors](./references/router-errors.md) |
| Recommending or classifying a restart, restage, scale, push, or rollback (including its revision evidence), or a memory/disk resize | [State-changing command effects](./references/state-changing-effects.md) |

## Drill in (read-only)

| Question | Apps Manager | `cf` |
|---|---|---|
| GUID and processes | **Overview** | *human* `cf app <app> --guid` |
| Per-instance state/CPU/mem/disk | **Overview** instances | *human* `cf curl /v3/apps/<guid>/processes/web/stats` |
| Routes | **Networking > Routes** | *human* `cf routes` |
| Services and plan | **Application > Services** | *human* `cf services`; *human* `cf service <name>` |

*human* = human-run; the guard denies that form to `sre-assistant`. `cf curl` is the current instant; for
CPU or memory **over time**, use PCF App Metrics or Grafana.

### Secrets: credential-bearing reads are human-only

Fleet agents never run `cf env`, `cf service-key`, or `CF_TRACE`; the guard denies them. A human
runs them, and if raw environment data is required, captures and sanitizes the smallest excerpt
outside the agent context, preserving its evidence label and content hash through handoff. The same
applies to singular `cf revision` and to an expanded row in Apps Manager **Application > Revisions**,
which both show environment variables; never substitute them for `cf revisions`.

Treat `cf ssh`, including database port-forwarding through an app container, as privileged shell
access, not read-only triage: recommend it only when necessary and hand the human release owner the
exact target, purpose, and rollback/exit plan. Port-forwarding needs an already-approved Tier-2/3
evidence packet and authorizes no state-changing database query.

## State-changing — human execution only

Every `cf` verb outside the read rows above, and the Revisions **Redeploy** button (a rollback), is
human-run under `production-change-gate`'s approved evidence packet; several stop the whole app.
Deployment plans use the human-invoked `/save-toolkit:pcf-deploy`. This read-only skill stops and
hands off.
