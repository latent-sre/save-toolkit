# Application crashes and health checks

Read when the symptom involves an app crash, exit status, OOM evidence, `$PORT`, or a liveness or
readiness check. The parent `SKILL.md` owns the application/platform boundary, evidence labels,
human approval, and the state-changing-command stop; this file grants no execution authority.

## Exit codes (`cf events` / `cf app`)

- `Exited with status 137` = **SIGKILL** (128+9). **Not proof of OOM.** Corroborate before
  recommending memory changes. Diego appends **`(out of memory)`** when Garden reported an OOM event:

  ```text
  APP/PROC/WEB: Exited with status 137 (out of memory)     <- OOM, corroborated
  APP/PROC/WEB: Exited with status 137                     <- SIGKILL; cause unverified
  ```

  Check the app's Events list in Apps Manager (or `cf events <app>`, `app.crash` ->
  `exit_description`), recent logs, and memory versus quota (the Overview instance table, `cf app`,
  or `/v3/apps/<guid>/processes/web/stats` -> `usage.mem` vs `mem_quota`). Those show the current
  instant; PCF App Metrics or Wavefront shows whether memory climbed steadily or spiked. On foundations
  where Garden uses containerd, a real OOM can surface as bare 137, so absence of the suffix does not
  disprove OOM. *[sourced: cloudfoundry/executor `run_step.go`; garden-runc-release issue #112]*
- The app must listen on the platform-assigned **`$PORT`**, or health checks fail and it crash-loops.
  A starting/down/failing pattern after a push is a hypothesis, not proof of memory or port failure.

## Health checks (`cf set-health-check` / manifest)

- Types: **`port`** (TCP on `$PORT`), **`http`** (GET an endpoint, must return `200`—preferred for
  web), **`process`** (process alive only—for workers / `--no-route`).
- **Liveness** (default type `port`): on failure CF considers the instance crashed and stops and
  restarts it.
- **Readiness** (default type `process`): on failure CF removes the instance from the route pool but
  does not restart it.
- Slow `/health` timing out? A human release owner may propose raising the invocation timeout:
  `cf set-health-check <app> http --endpoint /healthz --invocation-timeout 10`.

These are documented behavior shapes, not live observations. Exact target-foundation behavior
remains `[unverified]`. Changing a health check requires the exact approved-change packet in the
parent skill and human execution.
