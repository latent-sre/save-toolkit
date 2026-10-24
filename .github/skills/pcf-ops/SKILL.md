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

Our apps run on PCF (VMware Tanzu Application Service). This skill stays on the application side:
observe the app and assemble evidence; never operate the foundation. State-changing commands belong
to a human release owner with exact approval evidence.

> **First look.** This team works in Apps Manager; `cf` v8 is the equivalent where installed.
>
> | Question | Apps Manager | `cf` equivalent |
> |---|---|---|
> | Right foundation/org/space? | foundation URL, then the org/space picker | `cf target` |
> | Running, how many instances? | **Overview** instance table: state, CPU, memory each | `cf app <app>` |
> | What changed, and who? | **Events**: crash, restart, scale, update, with times | `cf events <app>` |
> | What do the last minutes say? | the **Logs** pane | `cf logs <app> --recent` |

>
> Work the rows in that order, and confirm the foundation, org, and space against the expected ones
> before reading any app or log data — evidence from the wrong target is worse than none.

These first-look views do not establish coverage of the requested incident window. Record their
actual covered interval and retention, pagination, or truncation limits before shortening the
presentation. If the requested history is missing, obtain it through another permitted source or
report the gap; absence from recent or incomplete records cannot exclude an event or cause.

For `sre-assistant`, the command grant is bare `cf target`, `cf app <app>`, `cf events <app>`,
`cf logs <app> --recent`, and `cf revisions <app>` for the named app; no live tail, target flags,
inventory expansion, or remediation. The guard checks command syntax only: the protected, masked
output path (the username in target output included) and the target confirmation come from the
agent's own rules and caller-supplied evidence, and without them the agent asks for the Apps Manager
view or a sanitized observation. An absent or unauthenticated CLI is an access gap, never an
observed platform failure.

## Change and revision evidence

`cf revisions <app>` lists revision number, description, deployability, revision GUID and creation
time; `cf events <app>` supplies recorded event times and actors, subject to output sanitization.
Neither alone establishes the prior droplet or environment configuration. For a rollback
recommendation, obtain a credential-free authoritative deployment/configuration record; missing
binding stays `[unverified]`. These reads do not authorize a rollback.
Do not substitute singular `cf revision`, which can print environment variables.

## App-side vs platform-side (know your lane)

We operate **our apps**; the **platform** (BOSH, Ops Manager, Diego cells, Gorouter, NTP/certs,
foundation capacity) is the platform team's. Fix app-side problems; **recognize and escalate with
evidence** when symptoms are platform-wide—do not try to operate BOSH.

- **One app / route / instance affected ⇒ likely app-side** (ours to investigate).
- **Many apps failing at once, or failing/evacuating cells ⇒ broaden and escalate**—bring in the
  platform and relevant dependency owners. Shared databases, networks, or releases can affect many
  apps; broad impact alone does not establish platform fault.

**Escalation packet (a case the platform team can act on, not a hunch):**

- **Symptom + observed window** (UTC) and **trend** (growing / steady / recovering); distinguish
  confirmed onset from the first available observation.
- **Blast radius** showing it is not just our app: affected apps/routes/orgs/spaces and the common
  symptom, with timestamps.
- **App-side observations and limits:** instance states, events, captured log window, and known
  deploy/config changes. Running instances and clean logs do not establish successful user requests.
- **Hypotheses checked and still open:** deploy, config, shared dependency, and capacity; name the
  evidence that narrows each, not a blanket app-health clearance.
- **Platform signals, if available:** evacuating/failing Diego cells, foundation-wide 502s,
  cert/NTP symptoms, or `cf ssh`-to-`2222` timeouts. Name the missing observation the receiving owner
  can supply; lack of a confirmed cause does not block escalation. Label causal gaps `[unverified]`.

## "What changed?" — the highest-value read

A crash/OOM, restage, scale, or `audit.app.update`/`...droplet.create` in **Events** at the incident
start is the prime suspect. Correlate it with the release pipeline and repository history; temporal
alignment alone is not proof.

## Logs

RTR lines carry status code and response time per request; APP lines are app stdout/stderr; `cf logs`
without `--recent` live-tails both and is outside the SRE grant. The buffer and the **Logs** pane hold only minutes; for history
go to **Splunk** (`obs-analysis` has the query shapes) with the timestamp and correlation ID.

## Read only the detail the symptom needs

A human or approved network capture point supplies route headers; agents do not turn an untrusted
route into an egress request. Load every row whose predicate matches the current request or any
evidence gathered so far in this triage, and no others.

| If the request involves… | Read first |
|---|---|
| App crashes, status 137, OOM evidence, JVM memory sizing, `$PORT`, or liveness/readiness health checks | [Application crashes and health checks](./references/application-crashes-and-health-checks.md) |
| `X-Cf-RouterError`, 404/502/503 interpretation, keep-alive failures, connection limits, route services, or certificate/clock-skew symptoms | [Router errors](./references/router-errors.md) |
| The task requires repository-owned foundation/API, org/space, app inventory, route, owner, or runbook values, or the target to confirm before reading | [Foundations and app inventory](./references/foundations.md) |
| Recommending or classifying a restart, restage, scale, push, or rollback, or a memory/disk resize | [State-changing command effects](./references/state-changing-effects.md) |

These references supply interpretation and inventory only. They do not widen the application-side
lane, turn repository values into trusted target evidence, or authorize a state-changing command.

## Drill in (read-only)

| Question | Apps Manager | `cf` |
|---|---|---|
| GUID and processes | **Overview** | *human* `cf app <app> --guid` |
| Per-instance state/CPU/mem/disk | **Overview** instances | *human* `cf curl /v3/apps/<guid>/processes/web/stats` |
| Process detail | **Overview** | *human* `cf curl /v3/apps/<guid>/processes` — types and process guids |
| Routes | **Routes** tab | *human* `cf routes` |
| The rest of the space | the space's app list | *human* `cf apps` |
| Services and plan | **Services** tab | *human* `cf services`; *human* `cf service <name>` |

*human* = human-run; the guard denies that form to `sre-assistant`. `cf curl` is the current instant; for
CPU or memory **over time**, use App Metrics or Wavefront.

### Secrets: credential-bearing reads are human-only

Fleet agents never run `cf env`, `cf service-key`, or `CF_TRACE`; the guard denies them. A human
runs them, and if raw environment data is required, captures and sanitizes the smallest excerpt
outside the agent context, preserving its evidence label and content hash through handoff.

Treat `cf ssh` as privileged shell access, not read-only triage: recommend it only when necessary,
and hand the human release owner the exact target, purpose, and rollback/exit plan.

## State-changing — human execution only

Every `cf` verb outside the read rows above is human-run: `cf set-health-check` / `cf restart` /
`cf restage` / `cf scale` / `cf push` / `cf map-route` / `cf unmap-route` / `cf set-env` / `cf stop` /
`cf delete` / `cf cancel-deployment` / `cf continue-deployment` / `cf ssh`. Read
[State-changing command effects](./references/state-changing-effects.md) before recommending or
classifying any of them; several stop the whole app.

`incident-investigation` advises the responder on mitigation choice for ITO's approval, the
human-invoked `/pcf-deploy` workflow owns the deployment plan the human release owner
executes, and `production-change-gate` owns the approved evidence packet a state-changing command
needs; this read-only skill stops and hands off.

## Tips

- Capture logs and events before recommending restart/scale; instances are ephemeral.
- Database port-forwarding through an app container is privileged human-run work. It requires an
  already-approved Tier-2/3 evidence packet and does not authorize state-changing database queries.
