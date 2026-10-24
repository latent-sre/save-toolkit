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
  Garden with containerd can report real OOM as bare 137: a missing suffix does not disprove OOM.
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

Compare Apps Manager paths with actual Actuator config/Boot version. Usual groups are
`/actuator/health/liveness` and `/actuator/health/readiness`; verify base path, access and
`management.endpoint.health.probes.enabled` before interpreting 404. A separate management port
can remain healthy while the app listener fails. Check whether
`management.endpoint.health.probes.add-additional-paths=true` exposes `/livez`/`/readyz` on the main
port; match CF to served endpoints. Liveness governs restart: avoid dependency-driven restart loops.

For interrupted requests during shutdown, compare the app's
`spring.lifecycle.timeout-per-shutdown-phase` with the platform's stop grace period; a shorter
platform deadline can terminate draining requests. Gather the configuration and failure evidence
for the human release owner; Java source changes belong to the application's development owner.

## JVM memory sizing (Java buildpack)

- The Java buildpack memory calculator uses `$MEMORY_LIMIT` at each start for heap (`-Xmx`/`-Xms`),
  metaspace, stacks (`-Xss` × `stack_threads`, default 250), code cache and direct memory:
  1. `cf scale -m/-k` stops and starts every instance itself; no restage is needed — the numbers
     are recomputed at start.
  2. Since calculator v4, pinned `-Xmx` still must fit with non-heap or startup fails:
     `required memory … is greater than … available for allocation`. If non-heap alone exceeds
     memory, lowering heap cannot fix it; check pool/thread estimates and container limit.
     If non-heap fits but the heap pin makes the total too large, propose reducing/removing it.
     Recalculate the full budget and check workload demand/headroom before a human changes it;
     arithmetic fit alone is not readiness.
  3. The staging log line `Loaded Classes: N, Threads: 300` is the calculator's input; tune
     `stack_threads` via `JBP_CONFIG_OPEN_JDK_JRE` rather than hand-setting `-Xss`.

  Container OOM identifies total pressure, not the responsible JVM pool; calculated heap does not
  prove a later kill was non-heap. Compare effective JVM limits, heap/native use, class/thread
  estimates and OS/cgroup limits. More container memory may mainly enlarge heap without changing
  a fixed metaspace cap or thread limit. Diagnose the pool before sizing:

  | JVM `OutOfMemoryError` reason | Investigate |
  |---|---|
  | `Java heap space` / `GC overhead limit exceeded` | Heap demand and effective `-Xmx` |
  | `Metaspace` / `Compressed class space` | Class metadata demand, class-count estimate, and pool caps |
  | `unable to create native thread` | Thread count, stack size (`-Xss`), native headroom, and OS/cgroup process limits |
  | `Direct buffer memory` | Direct allocation demand and `MaxDirectMemorySize` |
  | `Requested array size exceeds VM limit` | Impossible single allocation; correct the code |

  Unlisted reasons stay open for diagnosis. Exact native-thread/direct-buffer message text may vary
  by JDK.
- **The buildpack picks the JRE from its own config** (`JBP_CONFIG_OPEN_JDK_JRE`), not from the
  build file — check the two agree before blaming the code for a `ClassFormatError`.
