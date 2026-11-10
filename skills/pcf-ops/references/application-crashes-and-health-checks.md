# Application crashes and health checks

Apply the [parent scope, evidence and human-execution rules](../SKILL.md); this reference grants no
access or change authority. Foundation-specific behavior remains unconfirmed until observed.

## Exit codes (`cf events` / `cf app`)

- `Exited with status 137` = **SIGKILL** (128+9). **Not proof of OOM.** Corroborate before
  recommending memory changes. Diego appends **`(out of memory)`** when Garden reported an OOM event:

  ```text
  APP/PROC/WEB: Exited with status 137 (out of memory)     <- OOM, corroborated
  APP/PROC/WEB: Exited with status 137                     <- SIGKILL; cause unverified
  ```

  Check Apps Manager Events (`cf events <app>`, `app.crash` → `exit_description`), recent logs,
  and Overview memory/quota (`cf app`; human-only `/v3/apps/<guid>/processes/web/stats`, `usage.mem`
  versus `mem_quota`). These are current snapshots; use PCF App Metrics/Wavefront for trends.
  A missing suffix does not disprove OOM.
- The app must listen on the platform-assigned **`$PORT`**, or health checks fail and it crash-loops.
  A starting/down/failing pattern after a push is a hypothesis, not proof of memory or port failure.

## Health checks (manifest; `cf set-health-check` for liveness only)

- Types: **`port`** (TCP on `$PORT`), **`http`** (GET an endpoint, must return `200`—preferred for
  web), **`process`** (process alive only—for workers / `--no-route`).
- **Liveness** (default type `port`): on failure CF considers the instance crashed and stops and
  restarts it.
- **Readiness** (default type `process`; manifest only, `cf set-health-check` has no readiness
  option): on failure CF removes the instance from the route pool but does not restart it.
- Slow `/health` timing out? A human release owner may propose raising the invocation timeout:
  `cf set-health-check <app> http --endpoint /health/live --invocation-timeout 10`.
- **Startup timeout:** `Failed after <duration>: startup health check never passed.` plus
  `Instance never healthy after <duration>: <check error>` means the startup check did not pass
  within manifest `timeout` / `cf push -t` (default 60 s; foundation
  `cc.maximum_health_check_timeout` caps it, default 180 s). Older Diego logs say "readiness health
  check". Startup reuses liveness type, endpoint and invocation timeout.
  1. Rule out the look-alikes from the same evidence: an OOM kill reads `Exited with status 137`,
     not "never healthy"; a `$PORT` mismatch keeps failing however long the app is given, and the
     app's own log names another port; a platform fault reaches other apps too (the parent skill's
     boundary check).
  2. In Apps Manager Logs (`cf logs <app> --recent`), compare start-to-listening time on current
     and previous droplets; check Events (`cf events <app>`). Investigate changed dependency
     warm-up, boot migration or classpath before proposing a timeout that hides the regression.
  3. A human release owner may propose raising the start timeout (`timeout` / `-t`), not the
     invocation timeout, which bounds each probe (1 s by default) and fixes only a slow endpoint.

  Repeated crashes back off: three immediate restarts, then a 30 s wait that doubles up to 16 min,
  and no restarts after the 200th. Apps Manager → app → Settings → Health Check shows the check
  type and endpoint; whether it shows the start timeout is unconfirmed.

Health-check changes require the parent's exact approved-change packet and human execution.

### Supporting Spring Boot services

A separate management port can stay healthy while the app listener fails; check the main port.
Liveness governs restart, so a dependency check in it turns a dependency outage into a restart loop.

For interrupted requests during shutdown, compare the app's
`spring.lifecycle.timeout-per-shutdown-phase` with the platform's stop grace period; a shorter
platform deadline can terminate draining requests. Gather the configuration and failure evidence
for the human release owner; Java source changes belong to the application's development owner.

## JVM memory sizing (Java buildpack)

- The Java buildpack memory calculator uses `$MEMORY_LIMIT` at each start for heap (`-Xmx`),
  metaspace, stacks (`-Xss` × `stack_threads`, default 250), code cache and direct memory:
  1. `cf scale -m/-k` stops and starts every instance itself; no restage is needed — the numbers
     are recomputed at start.
  2. A pinned `-Xmx` still must fit with non-heap or startup fails:
     `required memory … is greater than … available for allocation`. If non-heap alone exceeds
     memory, lowering heap cannot fix it; check pool/thread estimates and container limit.
     If non-heap fits but the heap pin makes the total too large, propose reducing/removing it.
     Recalculate the full budget and check workload demand/headroom before a human changes it;
     arithmetic fit alone is not readiness.
  3. The staging log line `Loaded Classes: <n>, Threads: <n>` is the calculator's input; tune
     `stack_threads` via `JBP_CONFIG_OPEN_JDK_JRE` rather than hand-setting `-Xss`.

  Container OOM identifies total pressure, not the responsible JVM pool; calculated heap does not
  prove a later kill was non-heap. Compare effective JVM limits, heap/native use, class/thread
  estimates and OS/cgroup limits. More container memory may mainly enlarge heap without changing
  a fixed metaspace cap or thread limit. Diagnose the pool before sizing.
- **The buildpack picks the JRE from its own config** (`JBP_CONFIG_OPEN_JDK_JRE`), not from the
  build file — check the two agree before blaming the code for a `ClassFormatError`. On Java
  buildpack v5, `BP_JAVA_VERSION` takes precedence and the default JRE is 17, not v4's 8; confirm
  which buildpack the foundation ships.
