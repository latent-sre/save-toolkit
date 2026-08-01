## Steps
1. **Map** users, critical journeys, entry points, dependencies, and constrained resources.
2. **Auto-instrument first** with the OpenTelemetry SDK; then add **manual** spans for business-critical
   operations.
3. **Resource attributes** — set `service.name`, `service.version`, and **`deployment.environment.name`**
   (OTel semantic conventions) so signals are filterable per app/space.
   > ⚠️ **`deployment.environment` is DEPRECATED** — renamed to **`deployment.environment.name`** in
   > semconv **v1.27.0**, and stabilized in v1.41.0. Emit the `.name` form. Well-known values:
   > `development`, `staging`, `production`, `test`.
4. **RED per route** (request-driven services): request count, error count, and a latency **histogram**
   — split **success vs error** latency. Bounded labels only (method, route template, status class).
5. **USE per resource** (pools/queues/CPU/memory): utilization, saturation, errors — this is what catches
   the saturation → latency → errors cascade.
6. **Traces** — propagate W3C trace context across services. Use a **Collector tail-sampling processor**
   with explicit policies (status=error, latency threshold) to **prioritize** error and slow traces.
   > ⚠️ **Tail sampling does NOT guarantee you keep all error traces.** It is best-effort under capacity
   > limits, and it fails *silently*. Three things must hold, and none is automatic:
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
7. **Logs** — structured (JSON) carrying the trace/span IDs; redact secrets and PII before serialization; carry only approved trace/span correlation fields.
8. **Correlate** — verify metric→trace (exemplars) and trace→log (shared IDs) actually link.

## Done
Every critical journey emits RED; every constrained resource emits USE; traces propagate and correlate to
logs; **no unbounded metric label exists**; at least one SLI is computable from what you emit.
