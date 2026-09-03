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

## JVM memory sizing (Java buildpack)

- **The Java buildpack's memory calculator sizes the JVM from the container's `$MEMORY_LIMIT` before
  every start**: heap (`-Xmx`/`-Xms`), metaspace, thread stacks (`-Xss` × `stack_threads`, default
  250), code cache, direct memory. Three consequences:
  1. `cf scale -m` needs a **restart, not a restage** — the numbers are recomputed at start.
  2. Pinning `-Xmx` yourself does not opt out: since calculator v4 the container must still fit
     heap **plus** non-heap, or the app fails at start with `required memory … is greater than …
     available for allocation`. Fix the thread count or the container size, not the heap flag.
  3. The staging log line `Loaded Classes: N, Threads: 300` is the calculator's input; tune
     `stack_threads` via `JBP_CONFIG_OPEN_JDK_JRE` rather than hand-setting `-Xss`.

  A container memory kill (the platform's out-of-memory exit, no JVM stack trace) is total RSS over
  the limit; a JVM `OutOfMemoryError` is heap exhaustion. They are diagnosed differently — the first
  is usually native memory (threads, direct buffers, metaspace), not heap.
- **The buildpack picks the JRE from its own config** (`JBP_CONFIG_OPEN_JDK_JRE`), not from the
  build file — check the two agree before blaming the code for a `ClassFormatError`. *[sourced:
  cloudfoundry/java-buildpack `docs/IMPLEMENTING_JRES.md`, `docs/jre-open_jdk_jre.md`,
  `RUBY_VS_GO_BUILDPACK_COMPARISON.md`; reviewed 2026-08-21]*
