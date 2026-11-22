# Deploys, scaling, and rollback

Human release owners execute all state-changing PCF actions with approval under `production-change-gate`
(or ITO TLC approval for covered actions under the incident fast path). Confirm foundation/CLI/CAPI
behavior on non-production targets before treating assumptions as `[verified]`.

## State-changing command effects (cf CLI v8 / CAPI V3)

| Command / action | Serving impact | New artifact |
|---|---|---|
| `cf scale <app> [--process <type>] -i <n>` | Adds/removes instances without restarting survivors; unbinds App Autoscaler | No |
| `cf scale <app> -m/-k/-l` (any `--process`) | **Stops the whole app**, then starts it (full startup outage) | No |
| Apps Manager **Scale** (memory, disk, log rate) | Applies at next start (treat as whole-app outage unless confirmed otherwise); unbinds App Autoscaler | No |
| `cf restart <app>` / `cf restage <app>` | Stops every instance, then starts them (whole-app outage) | `restage` always; `restart` if newest package is unstaged |
| `cf restart` / `cf restage` with `--strategy rolling` | Replaces `web` `--max-in-flight` at a time (default 1; needs quota), then restarts all non-web processes at once | As above |
| `cf restart-app-instance <app> <i> --process <type>` | Restarts one zero-based instance `<i>` (confirm console row index) | No |
| Proposed no-downtime `web` resize (`POST /v3/deployments` with `options.memory_in_mb` / `disk_in_mb`) | Candidate to prove on target CAPI before proposing; verify droplet reuse, non-web impact, and quota | Unconfirmed until droplet reuse verified |
| `cf push` (including `--strategy rolling -m/-k`) | Stages a new droplet (full release + production gates, never a simple resize) | Yes |

- **App Autoscaler:** Manual `cf scale` or Apps Manager **Scale** unbinds App Autoscaler and leaves the
  app at the manual setting. Always check and schedule re-binding after an incident scale.
- **Deployment lock:** While a deployment or rolling `cf rollback` is in progress or paused, scaling
  or updating `web` fails with `Cannot scale/update this process while a deployment is in flight.`

## Restart vs. restage

- **`cf restart`:** Sufficient when only the running app reads the changed env var at process start.
  Confirm the newest package is already staged — an unstaged package makes `cf restart` stage new
  bytes and requires full release/production gates.
- **`cf restage`:** Required when a buildpack consumes the variable during staging (`JBP_CONFIG_*`,
  `BP_*`, `PIP_INDEX_URL`, build-time `NODE_ENV`).

## Deployment strategies

- **Blue-green:** Keep the live app (`<app>`) running while pushing `<app>-green` (`cf push <app>-green -f manifest.yml --no-route`),
  mapping a test route, smoke-testing, mapping the production route, verifying shared-route traffic
  and telemetry, unmapping `<app>`, soaking, unmapping the test route, deleting `<app>`, and renaming
  `<app>-green` to `<app>`.
  - *Single-stanza manifest override:* In CLI v7+, an app name absent from a single-stanza `manifest.yml`
    overrides the stanza's app name; multi-stanza manifests fail with `AppNotInManifestError`.
  - *`--no-route` caveat:* CF manifest docs say existing routes stay, whereas CLI v8 integration tests
    expect them removed — verify on non-prod before reusing an existing green app.
- **Rolling (`--strategy rolling`):** Replaces instances inside one app (`--max-in-flight N`, default 1)
  when overlapping old/new instances are safe.
- **Canary (`--strategy canary --instance-steps 5,10,20`):** Experimental in CAPI. Requires cf CLI
  v8.8.0+ and CAPI v3.173.0+ (`--instance-steps` needs CAPI v3.189.0+). Pauses between steps for
  `cf continue-deployment` or `cf cancel-deployment`. Quota must cover `max_in_flight` temporary
  instances plus one more while paused.

## Rollback truth and limits

- **Blue-green rollback by phase:** Pre-prod-map → delete/leave green; shared route → unmap green;
  after unmapping old app (before delete) → remap old app, verify, unmap green; after delete/rename →
  requires pushing the previous artifact and restoring non-revision settings.
- **Revision rollback (`cf rollback <app> --version <n>` or Apps Manager **Revisions → Redeploy**):**
  Deploys revision `<n>`'s droplet, env vars, start commands, and sidecars as a **new higher revision**
  (`Rolled back to revision <n>`), reverting any env change made since `<n>`. It does **not** restore
  routes, service bindings, or instance scale, and works only while the droplet is retained (defaults:
  5 droplets vs. 100 CAPI revisions). Back out a bad rollback by rolling back to the prior revision or
  rolling forward.
- **`cf cancel-deployment` is not rollback:** Resets the droplet of an active rollout (cancelling a
  rolling rollback puts the bad droplet back!), leaves env/binding changes intact, and does not
  guarantee zero downtime.
- **Irreversible effects:** Neither route nor revision rollback reverses database migrations (load
  `database-reliability` for expand/contract) or external messages/webhooks already sent.

## Deploy plan checklist

Lead plans with `draft — unapproved`, `ready`, `blocked`, or `unverified` and cover:
1. **Scope & approval:** foundation API, org, space, app, routes, artifact/manifest digest and diff,
   strategy, blast radius, release owner, and approval/change-record ID.
2. **Target facts:** current state, bindings (names only, never secrets), quotas, health checks,
   telemetry, CLI/CAPI versions, DB migrations, and prior-droplet availability.
3. **Human-run sequence:** ordered commands, hold/soak checkpoints, readback (`cf app`, routes,
   metrics/logs), and abort thresholds.
4. **Recovery & gaps:** phase-by-phase backout, non-reversible limits, and `[unverified]` assumptions.
