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
  `cf set-health-check <app> http --endpoint /health/live --invocation-timeout 10`.
- **Slow start, not a broken app.** A crash loop after a push or restart whose logs show
  `Failed after <duration>: startup health check never passed.` and whose crash event reads
  `Instance never healthy after <duration>: <check error>` means the app did not answer its health
  check within the start `timeout` (manifest `timeout`, `cf push -t`): 60 s by default, capped by the
  foundation's `cc.maximum_health_check_timeout`, 180 s by default. Older Diego releases say
  "readiness health check" in the first line. The startup check reuses the liveness check's type,
  endpoint and invocation timeout.
  1. Rule out the look-alikes from the same evidence: an OOM kill reads `Exited with status 137`,
     not "never healthy"; a `$PORT` mismatch keeps failing however long the app is given, and the
     app's own log names another port; a platform fault reaches other apps too (the parent skill's
     boundary check).
  2. Tie the slow start to the droplet. In Apps Manager → app → Logs (`cf logs <app> --recent`),
     compare the time from start to the app's listening line on this droplet and the previous one;
     read the crash in Events (`cf events <app>`). A new dependency warm-up, a migration at boot or a
     larger classpath explains a start that now overruns; raising the timeout without that cause
     hides a regression.
  3. A human release owner may propose raising the start timeout (`timeout` / `-t`), not the
     invocation timeout, which bounds each probe (1 s by default) and fixes only a slow endpoint.

  Repeated crashes back off: three immediate restarts, then a 30 s wait that doubles up to 16 min,
  and no restarts after the 200th. Apps Manager → app → Settings → Health Check shows the check
  type and endpoint; whether it shows the start timeout is `[unverified]`.
  *[sourced: cloudfoundry/executor `depot/steps/health_check_step.go`; CF docs, manifest
  `timeout` and `health-check-invocation-timeout`, and "Using App Health Checks"; cloudfoundry/bbs
  `models/restart_calculator.go`]*

These are documented behavior shapes, not live observations. Exact target-foundation behavior
remains `[unverified]`. Changing a health check requires the exact approved-change packet in the
parent skill and human execution.

### Supporting Spring Boot services

Compare the health-check path in Apps Manager with the app's actual Actuator configuration and
Boot version. The usual health groups are `/actuator/health/liveness` and
`/actuator/health/readiness`; verify the base path, access rules and
`management.endpoint.health.probes.enabled` before treating a 404 as an application failure.
If Actuator uses a separate management port, a healthy probe can miss a broken application
listener. Check whether `management.endpoint.health.probes.add-additional-paths=true` exposes
`/livez` and `/readyz` on the main port, and match CF's paths to the endpoints actually served.
Use liveness for the restart check; an external dependency outage must not cause a restart loop.
*[sourced: [Spring Boot Actuator probes](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html#actuator.endpoints.kubernetes-probes)]*

For interrupted requests during shutdown, compare the app's
`spring.lifecycle.timeout-per-shutdown-phase` with the platform's stop grace period; a shorter
platform deadline can terminate draining requests. Gather the configuration and failure evidence
for the human release owner; Java source changes belong to the application's development owner.
*[sourced: [Spring Boot graceful shutdown](https://docs.spring.io/spring-boot/reference/web/graceful-shutdown.html)]*

## JVM memory sizing (Java buildpack)

- **The Java buildpack's memory calculator sizes the JVM from the container's `$MEMORY_LIMIT` before
  every start**: heap (`-Xmx`/`-Xms`), metaspace, thread stacks (`-Xss` × `stack_threads`, default
  250), code cache, direct memory. Three consequences:
  1. `cf scale -m/-k` stops and starts every instance itself; no restage is needed — the numbers
     are recomputed at start.
  2. Pinning `-Xmx` yourself does not opt out: since calculator v4 the container must still fit
     heap **plus** non-heap, or the app fails at start with `required memory … is greater than …
     available for allocation`. Identify the failed fit check: if non-heap overhead alone exceeds
     available memory, lowering heap cannot fix it; check the pool/thread estimates and container
     limit. If non-heap fits but an explicit `-Xmx` makes the total too large, reducing or removing
     that excessive heap pin is a valid proposal. Recalculate the full budget and verify workload
     demand and headroom before the human owner changes it; arithmetic fit alone is not readiness.
  3. The staging log line `Loaded Classes: N, Threads: 300` is the calculator's input; tune
     `stack_threads` via `JBP_CONFIG_OPEN_JDK_JRE` rather than hand-setting `-Xss`.

  A container OOM kill establishes total memory pressure, not which JVM pool caused it. The
  calculator budgets from inputs; a calculated heap cap does not prove a later kill was non-heap.
  Compare effective JVM limits, heap/native usage, class/thread estimates, and OS/cgroup limits.
  More container memory can mainly enlarge the calculated heap; it need not raise a fixed metaspace
  cap or resolve a thread limit. Diagnose before proposing a sizing change:

  | JVM `OutOfMemoryError` reason | Investigate |
  |---|---|
  | `Java heap space` / `GC overhead limit exceeded` | Heap demand and effective `-Xmx` |
  | `Metaspace` / `Compressed class space` | Class metadata demand, class-count estimate, and pool caps |
  | `unable to create native thread` | Thread count, stack size (`-Xss`), native headroom, and OS/cgroup process limits |
  | `Direct buffer memory` | Direct allocation demand and `MaxDirectMemorySize` |
  | `Requested array size exceeds VM limit` | Impossible single allocation; correct the code |

  Unlisted reasons stay open for diagnosis. *[sourced: [Oracle JDK 17 troubleshooting](https://docs.oracle.com/en/java/javase/17/troubleshoot/troubleshooting-memory-leaks.html);
  [calculator](https://github.com/cloudfoundry/java-buildpack-memory-calculator/blob/3d845d8695ed03f1315c5a66582a441c754e3870/calculator/calculator.go);
  reviewed 2026-09-09; calculator fit-check branches re-checked 2026-10-02. Exact native-thread/direct-buffer
  message text varies by JDK `[unverified]`.]*
- **The buildpack picks the JRE from its own config** (`JBP_CONFIG_OPEN_JDK_JRE`), not from the
  build file — check the two agree before blaming the code for a `ClassFormatError`. *[sourced:
  cloudfoundry/java-buildpack `docs/IMPLEMENTING_JRES.md`, `docs/jre-open_jdk_jre.md`,
  `RUBY_VS_GO_BUILDPACK_COMPARISON.md`; reviewed 2026-08-21]*
