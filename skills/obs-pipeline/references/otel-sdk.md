# OTel SDK instrumentation method

Installs, agent flags and app launches belong to `software-engineer` or the human build/deploy owner.
The guard denies installs/app execution for `sre-assistant`; unguarded Bash does not give
`observability-engineer` ownership of service builds.
Respect `stack-profile`'s authoring/support boundary: Java source, manual-span and dependency
changes belong to the application's development owner; this fleet supports its deployed instrumentation.

Commands are `[sourced]` to the linked OpenTelemetry docs; the uv bootstrap was checked 2026-09-09.
Exact-target behavior remains `[unverified]` until a canary proves it.

## Steps

Scoped fixes apply only steps affecting the changed path in the existing setup; service-wide
instrumentation uses the full method.

1. **For service-wide design, map** users, journeys, entry points, dependencies, and constrained resources.
2. **For service-wide instrumentation, auto-instrument first** with the SDK; then add **manual** spans for critical
   operations. The zero-code entry points *[sourced: opentelemetry.io/docs/zero-code/]*:

   For Python, use the repository's managed environment and lock workflow; never install into
   system Python. The [upstream uv bootstrap](https://opentelemetry.io/docs/zero-code/python/troubleshooting/#bootstrap-using-uv)
   below records dependencies in the project. Review the dependency/lock diff and reproduce from
   the lock before deployment; use the established equivalent for a library using Poetry.

   ```sh
   # Python — in the uv project
   uv add opentelemetry-distro opentelemetry-exporter-otlp
   uv run opentelemetry-bootstrap -a requirements | uv add --requirement -
   uv run opentelemetry-instrument --traces_exporter otlp --metrics_exporter otlp \
     --logs_exporter otlp --service_name my-service python app.py

   # Java — agent JAR (Spring Boot starter and Quarkus extension also exist)
   java -javaagent:./opentelemetry-javaagent.jar -jar my-app.jar
   ```

   Standard env config either way: `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`
   (gRPC 4317 / HTTP 4318), `OTEL_EXPORTER_OTLP_PROTOCOL`.

   **Spring Boot: identify the installed path before troubleshooting.**

   - `-javaagent` instruments bytecode at startup without source changes and has the widest
     library coverage. PCF's Java buildpack can inject it; check buildpack config for duplicates.
   - The library-mode starter (`io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter`,
     versions via `opentelemetry-instrumentation-bom`) fits native images, unacceptable agent
     startup overhead, another incompatible monitoring agent, or `application.yml` configuration
     (including declarative YAML). Docs list Spring Boot 2.6+/3.1+; upstream also tests Boot 4,
     reviewed against instrumentation 2.31.1 on 2026-08-24.

   Use one path. Refer dependency changes to the application's development owner.
   *[sourced: opentelemetry.io zero-code Java Spring Boot starter pages;
   opentelemetry-java-instrumentation repo]* Which path the team's services
   use today is `[unverified]` — read the build file and the buildpack config.
3. **Resource attributes** — set `service.name`, `service.version`, and **`deployment.environment.name`**
   (OTel semantic conventions) so signals are filterable per app/space.
   > ⚠️ **`deployment.environment` is DEPRECATED** — renamed to **`deployment.environment.name`** in
   > semconv **v1.27.0**, and stabilized in v1.41.0. Emit the `.name` form. Well-known values:
   > `development`, `staging`, `production`, `test`.

   An unset `service.name` falls back to **`unknown_service:<executable>`** *[sourced: semconv
   resource/service]* — an `unknown_service` series in any backend is an instrumentation defect to
   file, not a service. Identity is the trio `service.namespace` + `service.name` +
   `service.instance.id`; `deployment.environment.name` deliberately does NOT participate in
   identity (prod and staging with the same trio are "the same service" — filter by environment,
   don't fork the name). Keep `service.name` identical across PCF and Cloud Run while a service
   straddles the migration, with the runtime as a separate resource attribute.
   HTTP semconv has been **stable since v1.23.0** (`url.*`, `client.*`/`server.*` replaced the old
   `net.*` forms) *[sourced: opentelemetry.io HTTP-conventions-stable announcement]* — new
   dashboards and queries key on the stable names, and an old exporter emitting pre-stable names is
   a migration flag, not a pattern to copy.
4. **RED per route** (request-driven services): request count, error count, and a latency **histogram**
   — split **success vs error** latency. Bounded labels only (method, route template, status class).
5. **USE per resource** (pools/queues/CPU/memory): utilization, saturation, errors — this is what catches
   the saturation → latency → errors cascade.
6. **Traces** — propagate W3C context across services. Change sampling policy/topology only when in scope.
   Where **Collector tail sampling** is used, explicit policies (status=error, latency threshold)
   **prioritize** error/slow traces, subject to every constraint below:
   > ⚠️ **Tail sampling does NOT guarantee you keep all error traces.** It is best-effort under capacity
   > limits. Check these conditions:
   > - **Upstream sampling:** record the effective SDK/head sampler and propagated parent decision.
   >   A collector cannot recover spans never exported by the SDK. Check this before tuning tail
   >   policies; do not increase sampling outside the authorized scope.
   > - **Routing:** *all spans of a trace MUST reach the same collector instance*, or policies evaluate
   >   on a fragment. This needs a two-layer topology — a **load-balancing exporter** layer in front of
   >   the tail-sampling layer. Deploying tail sampling behind a plain round-robin LB is the classic
   >   silent misconfiguration.
   > - **Capacity:** `num_traces` (default **50,000**) is how many traces are held in memory. *"When a
   >   new trace arrives, the oldest trace is removed"* — it can be **dropped before it is ever
   >   sampled**. **Watch `otelcol_processor_tail_sampling_sampling_trace_dropped_too_early`**; that
   >   metric is how the "guarantee" visibly fails.
   > - **Decision window:** `decision_wait` (default **30s**). Spans arriving after it miss the
   >   decision — long or slow traces are exactly the failure mode, and they're the ones you wanted.
   >   The processor's `decision_cache` (sampled/non-sampled LRU) lets a late span inherit an
   >   earlier keep decision — a documented mitigation, not a guarantee; size it and keep watching
   >   the dropped-too-early metric. *[sourced: opentelemetry-collector-contrib
   >   `tailsamplingprocessor` README]*
7. **Logs** — structured (JSON) carrying the trace/span IDs; redact secrets and PII before serialization; carry only approved trace/span correlation fields.
8. **Correlate** — verify metric→trace (exemplars) and trace→log (shared IDs) actually link.

## Done

Scoped fix: bounded test/canary proof of the changed boundary, with target limits and untested stages.
This proves no service-wide coverage.
Service-wide design: RED on critical request journeys, USE on constrained resources, propagated
traces correlated to logs, **no unbounded metric label**, and an SLI computable from emitted signals.
