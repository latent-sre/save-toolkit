# State-changing command effects

Read before recommending, classifying, or approving a state-changing `cf` command or a memory/disk
resize. The parent `SKILL.md` owns human-only execution and the evidence packet; this reference
supplies each command's serving impact and artifact class for the gate's blast radius.

## Effects on cf CLI v8 (CAPI V3)

| Command | Serving impact | New artifact |
|---|---|---|
| `cf scale <app> [--process <type>] -i <n>` | adds or removes instances; running instances untouched | no |
| `cf scale <app> -m/-k/-l`, any `--process` | stops the **whole app**, then starts it: every process is down for the start-up window | no |
| Apps Manager **Scale** changing memory, disk, or log rate | applies at the next start; whether the console restarts the app is `[unverified]` — treat it as whole-app | no |
| `cf restart <app>` / `cf restage <app>` | stops every instance, then starts them: whole-app outage for the start-up window | restage always; restart when the newest package is unstaged |
| the same with `--strategy rolling` | replaces `web` instances `--max-in-flight` at a time (default 1; needs quota for the extras); every non-web process then restarts all at once | as the row above |
| `cf restart-app-instance <app> <i> --process <type>` | that one instance | no |
| No-downtime `web` memory/disk resize | the existing-droplet deployment below; new sizes reach new `web` instances only; non-web processes restart at once with their old sizes | no |
| `cf push`, including `--strategy rolling -m/-k` | stages a new droplet: a deployment under the full release gates, never a resize | yes |

## No-downtime web resize

```bash
cf curl -X POST /v3/deployments -d '{"relationships":{"app":{"data":{"guid":"<app-guid>"}}},"strategy":"rolling","options":{"memory_in_mb":<mb>,"disk_in_mb":<mb>}}'
```

With no `droplet` field the deployment runs the current droplet; it needs capi-release 1.205.0+
`[sourced]`, and its behaviour on the target foundation is `[unverified]`.

## Deployment lock

While a deployment is deploying or paused (a canary step, or a rolling `cf rollback`), scaling or
updating the `web` process fails with `Cannot scale this process while a deployment is in flight.`:
wait for it, or cancel it knowingly.

*[sourced: cloudfoundry/cli v8 `scale_command.go`, `restart_command.go`; CAPI V3 deployments]*
