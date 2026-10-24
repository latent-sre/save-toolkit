# OTel SDK instrumentation method

Installs, agent flags and app launches belong to `software-engineer` or the human build/deploy owner.
The SRE guard denies them; observability's unguarded Bash does not transfer build ownership.
Under `stack-profile`, Java source, manual spans and dependencies remain with the application
owner; this fleet supports deployed instrumentation. Target behavior needs canary evidence.
`obs-analysis` owns span/status/attribute/sampling interpretation; this reference covers emission.

## Steps

Apply only changed-path steps for scoped fixes; service-wide work uses the full method.

1. **Inspect existing instrumentation before selecting a path.** Compare zero-code versus
   library/manual coverage, compatibility and overhead; preserve the existing path unless change
   is justified. Python uses the managed environment/lock workflow, never system installation;
   review dependency/lock diffs before deployment.

   For Spring Boot, inspect build and buildpack configuration, not an assumed team standard:
   - `-javaagent` instruments bytecode at startup with broad library coverage. PCF can inject it;
     check for duplicate agents.
   - `io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter` with
     `opentelemetry-instrumentation-bom` suits native images, unacceptable agent overhead,
     incompatible agents or `application.yml`/declarative YAML configuration. Docs list Boot
     2.6+/3.1+; instrumentation 2.31.1 also tests Boot 4.
   Use one path; application owners handle dependency changes.

2. **Resource identity:** emit `service.name`, `service.version`, `deployment.environment.name`.
   The latter replaces deprecated `deployment.environment` (semconv 1.27.0, stable 1.41.0);
   standard values include `development`, `staging`, `production`, `test`.

   Unset names fall back to `unknown_service:<executable>`; investigate that as missing identity.
   Identity combines `service.namespace`, `service.name`, `service.instance.id`, excluding
   environment. Filter by environment rather than forking the name. Keep the same logical
   `service.name` across PCF/Cloud Run, with runtime in a separate resource attribute.
   Stable HTTP conventions (since 1.23.0) use `url.*`, `client.*`/`server.*` instead of old `net.*`
   forms; pre-stable output needs migration assessment, not copying into new queries/dashboards.

3. **Traces:** propagate W3C context; change sampling/topology only within scope. Tail policies
   prioritize errors/slow traces but cannot guarantee retention:
   - Check effective SDK/head sampler and parent decision first: collectors cannot recover spans
     never exported. Do not increase sampling beyond the assignment.
   - All trace spans must reach the same sampling collector. One needs no routing tier; multiple
     collectors require trace-ID affinity, not round-robin. Upstream recommends a load-balancing
     exporter before the sampling tier; see [scaling guidance](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/tailsamplingprocessor/README.md#scaling-collectors-with-the-tail-sampling-processor).
   - `num_traces` defaults to 50,000 in memory; new arrivals can evict oldest traces before sampling.
     Watch `otelcol_processor_tail_sampling_sampling_trace_dropped_too_early`.
   - `decision_wait` defaults to 30s; late spans miss the decision. The sampled/non-sampled LRU
     `decision_cache` can preserve an earlier keep decision for late spans, not guarantee it.
     Size capacity/cache and monitor drops rather than promising every error trace.

4. **Correlation:** emit structured logs with approved trace/span fields; verify actual exemplar
   metric→trace and shared-ID trace→log links, not merely signal coexistence.

## Done

A scoped fix needs bounded canary/test proof at the changed boundary, with target limits and
untested stages; it establishes no service-wide coverage. Service-wide design covers RED journeys,
USE resources, propagated traces/log correlation, bounded metric labels and a computable SLI.
