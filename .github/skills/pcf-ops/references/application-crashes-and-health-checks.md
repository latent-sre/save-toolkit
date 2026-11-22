# Application crashes and health checks

Foundation-specific limits remain unconfirmed until observed on the target foundation.

## Exit codes (`cf events` / `cf app`)

- `Exited with status 137` = **SIGKILL** (128+9), **not proof of OOM**. Garden appends
  **`(out of memory)`** when an OOM event was reported (`APP/PROC/WEB: Exited with status 137 (out of memory)`).
  Corroborate with `cf events <app>` (`app.crash` → `exit_description`), recent logs, and Overview
  memory/quota (`usage.mem` vs. `mem_quota` in `/v3/apps/<guid>/processes/web/stats`), plus PCF App
  Metrics or Grafana for trends. A missing suffix does not rule out OOM.
- Every routed app must listen on the platform-assigned **`$PORT`** (not a hardcoded port or `127.0.0.1`),
  or health checks fail and instances crash-loop.

## Health checks (`manifest.yml`; `cf set-health-check` for liveness only)

- Types: **`port`** (TCP on `$PORT`, liveness default), **`http`** (`GET` returning `200`, preferred
  for web), **`process`** (process alive only, readiness default / `--no-route` workers).
- **Liveness** failure restarts the instance; **readiness** (manifest-only, not configurable via
  `cf set-health-check`) failure removes the instance from the route pool without restarting it.
- **Startup timeout:** `Failed after <duration>: startup health check never passed.` / `Instance never healthy after <duration>`
  means the startup probe (which reuses liveness type, endpoint, and 1 s default `--invocation-timeout`)
  failed within manifest `timeout` / `cf push -t` (default 60 s; foundation `cc.maximum_health_check_timeout`
  caps it, default 180 s). Older Diego logs call this "readiness health check".
  1. Check for OOM (`137 (out of memory)`), wrong listen port (`$PORT`), or platform signals.
  2. Compare start-to-listening time across current and prior droplets before proposing a larger
     `timeout` (`-t`) — investigate changed boot warm-up, migrations, or classpath first.
  3. Only raise `--invocation-timeout` (`cf set-health-check <app> http --endpoint /health/live --invocation-timeout 10`)
     when the endpoint itself is slow to answer; raising `timeout` (`-t`) governs total startup time.
- Repeated crashes back off: 3 immediate restarts, then 30 s doubling up to 16 min, and stop after
  the 200th crash.

### Supporting Spring Boot services

A separate management actuator port can stay healthy while the main app listener fails; check the
main port. Putting a dependency check inside liveness turns a dependency outage into a restart loop.
For cut-off requests during shutdown, compare `spring.lifecycle.timeout-per-shutdown-phase` with the
platform stop grace period. Java source changes stay with the application owner.

## JVM memory sizing (Java buildpack)

- The Java buildpack memory calculator uses `$MEMORY_LIMIT` at each start to size heap (`-Xmx`),
  metaspace, stacks (`-Xss` × `stack_threads`, default 250), code cache, and direct memory:
  1. `cf scale -m/-k` stops and starts every instance; numbers recompute at start with no restage needed.
  2. A pinned `-Xmx` still must leave room for non-heap or startup fails (`required memory … is greater than … available for allocation`).
     If non-heap alone exceeds the limit, adjust pool/thread estimates or container memory; if only
     the `-Xmx` pin overflows, reduce or remove it.
  3. The staging log line `Loaded Classes: <n>, Threads: <n>` drives the calculator; tune thread count
     via `JBP_CONFIG_OPEN_JDK_JRE` rather than hand-setting `-Xss`.
- Container OOM reflects total pressure, not which JVM pool leaked; diagnose the pool before raising `-m`.
- The buildpack selects the JRE from its own config (`JBP_CONFIG_OPEN_JDK_JRE` on v4, default 8;
  `BP_JAVA_VERSION` takes precedence on v5, default 17), not the build file — check agreement before
  blaming code for `ClassFormatError`.
