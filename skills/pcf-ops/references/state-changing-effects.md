# State-changing command effects

Use before recommending or classifying a CF write/resize. The [parent](../SKILL.md) requires
human execution and exact approval; these effects determine blast radius and artifact class.

## Effects on cf CLI v8 (CAPI V3)

| Command | Serving impact | New artifact |
|---|---|---|
| `cf scale <app> [--process <type>] -i <n>` | adds or removes instances; running instances untouched | no |
| `cf scale <app> -m/-k/-l`, any `--process` | stops the **whole app**, then starts it: every process is down for the start-up window | no |
| Apps Manager **Scale** changing memory, disk, or log rate | applies at the next start; whether the console restarts the app is unconfirmed — treat it as whole-app | no |
| `cf restart <app>` / `cf restage <app>` | stops every instance, then starts them: whole-app outage for the start-up window | restage always; restart when the newest package is unstaged |
| the same with `--strategy rolling` | replaces `web` instances `--max-in-flight` at a time (default 1; needs quota for the extras); every non-web process then restarts all at once | as the row above |
| `cf restart-app-instance <app> <i> --process <type>` | that one instance | no |
| Proposed no-downtime `web` memory/disk resize | no supported procedure established here; verify the target API, droplet reuse and effects below before proposing a command | unconfirmed until existing-droplet reuse is established |
| `cf push`, including `--strategy rolling -m/-k` | stages a new droplet: a deployment under the full release gates, never a resize | yes |

## Existing-droplet resize prerequisites

No supported no-downtime resize procedure is established here. Rolling-deployment support does
not imply memory/disk deployment options. Obtain the target API schema and a platform-owner-supported
procedure reusing the current droplet; establish web/non-web effects, capacity/quota, verification
and rollback before handing the exact proposal to the human release owner. Missing support/impact
blocks a no-downtime claim. `cf scale -m/-k/-l` remains whole-app; substituting `cf push` creates a
new artifact requiring full release gates.

## Deployment lock

While a deployment is deploying or paused (a canary step, or a rolling `cf rollback`), scaling or
updating the `web` process fails with `Cannot scale this process while a deployment is in flight.`:
wait for it, or cancel it knowingly.
