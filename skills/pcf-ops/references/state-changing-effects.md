# State-changing command effects

Use before recommending or classifying a CF write/resize. The [parent](../SKILL.md) requires
human execution and exact approval; these effects determine blast radius and artifact class.

## Effects on cf CLI v8 (CAPI V3)

| Command | Serving impact | New artifact |
|---|---|---|
| `cf scale <app> [--process <type>] -i <n>` | adds or removes instances; running instances untouched; unbinds App Autoscaler (below) | no |
| `cf scale <app> -m/-k/-l`, any `--process` | stops the **whole app**, then starts it: every process is down for the start-up window | no |
| Apps Manager **Scale** changing memory, disk, or log rate | applies at the next start; whether the console restarts the app is unconfirmed — treat it as whole-app; unbinds App Autoscaler (below) | no |
| `cf restart <app>` / `cf restage <app>` | stops every instance, then starts them: whole-app outage for the start-up window | restage always; restart when the newest package is unstaged |
| the same with `--strategy rolling` | replaces `web` instances `--max-in-flight` at a time (default 1; needs quota for the extras); every non-web process then restarts all at once | as the row above |
| `cf restart-app-instance <app> <i> --process <type>` | that one instance | no |
| Proposed no-downtime `web` memory/disk resize | candidate to prove: `POST /v3/deployments` with `options.memory_in_mb` / `options.disk_in_mb`, which current CAPI documents; verify the target API, droplet reuse and effects below before proposing a command | unconfirmed until existing-droplet reuse is established |
| `cf push`, including `--strategy rolling -m/-k` | stages a new droplet: a deployment under the full release gates, never a resize | yes |

## App Autoscaler

Manually scaling an app bound to App Autoscaler unbinds it and leaves the app at the manual setting,
so autoscaling can silently stop after an incident. Treat `cf scale` and Apps Manager **Scale** as
manual scaling; check the binding afterwards and record the re-bind as a follow-up.

## Existing-droplet resize prerequisites

Current CAPI documents `options.memory_in_mb` / `options.disk_in_mb` on `POST /v3/deployments` (null
keeps the previous web process's value; the droplet defaults to the app's current one). The minimum
CAPI version and the target foundation's support are unverified, and rolling-deployment support does
not imply them. Before proposing it, obtain the target API schema and a platform-owner-supported
procedure, and establish web/non-web effects, capacity/quota, verification and rollback; without
them there is no no-downtime claim.

## Revision evidence for a rollback recommendation

`cf revisions <app>` lists revision number, description, deployability, revision GUID and creation
time; `cf events <app>` supplies recorded event times and actors, subject to output sanitization.
Neither alone establishes the prior droplet or environment configuration: obtain a credential-free
authoritative deployment/configuration record, and keep a missing binding `[unverified]`. These
reads do not authorize a rollback.

## Deployment lock

While a deployment is deploying or paused (a canary step, or a rolling `cf rollback`), scaling or
updating the `web` process fails with `Cannot scale this process while a deployment is in flight.`
or `Cannot update this process while a deployment is in flight.`: wait for it, or cancel it knowingly.
