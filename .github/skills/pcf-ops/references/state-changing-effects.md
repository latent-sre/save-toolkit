# State-changing command effects

Read before recommending, classifying, or approving a state-changing `cf` command or a memory/disk
resize. The parent `SKILL.md` owns human-only execution and the evidence packet; this reference
supplies each command's serving impact and artifact class for the gate's blast radius.

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

No supported no-downtime resize procedure is established here. Do not send memory or disk values
as deployment options merely because the API supports rolling deployments. Before proposing a
resize command, obtain the target API schema and a platform-owner-supported procedure that reuses
the current droplet. Establish its web and non-web restart behavior, capacity/quota needs,
verification and rollback, then hand the exact scoped proposal to the human release owner.
Missing support or impact evidence blocks a no-downtime claim. Keep the whole-app effect of
`cf scale -m/-k/-l` explicit; do not substitute `cf push`, which creates a new artifact and needs
the full release gates.

## Deployment lock

While a deployment is deploying or paused (a canary step, or a rolling `cf rollback`), scaling or
updating the `web` process fails with `Cannot scale this process while a deployment is in flight.`:
wait for it, or cancel it knowingly.
