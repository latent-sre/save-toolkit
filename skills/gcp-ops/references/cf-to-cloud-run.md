# Cloud Foundry → Cloud Run — the concept map and its traps

Google's [Cloud Foundry migration guide](https://docs.cloud.google.com/run/docs/migrate/cloud-foundry/migrate-from-cloud-foundry-to-cloud-run)
provides a migration recipe. Check its assumptions against the workload and current platform capabilities.

## Eligibility first

The guide assumes the application:

- Uses HTTP or HTTP/2 (including gRPC).
- Listens for traffic based on the `PORT` environment variable.
- Doesn't carry over Cloud Foundry path-based routing to different applications unchanged.
- Doesn't require legacy Cloud Foundry "route services" for proxying traffic.
- Doesn't require an instance ID or a particular startup order.
- Doesn't need individual instances to be addressable.
- Can be started without side-effects to the environment, for example, starting a database migration.

An unmet recipe assumption calls for design assessment, not automatic rejection of Cloud Run.
For example, an [Application Load Balancer can route paths to multiple Cloud Run services](https://docs.cloud.google.com/run/docs/mapping-custom-domains#mapping_custom_domains_with_a_global_external_application_load_balancer).
TCP-routed apps and apps writing durable local state need separate runtime/storage assessment.
Distinguish background workload lifecycles before proposing a destination:

- Finite tasks that run to completion are candidates for **Cloud Run jobs**.
- Continuous, non-HTTP pull workers are candidates for **Cloud Run worker pools**; check regional
  availability, scaling and recovery requirements. A service with **instance-based billing and
  minimum instances greater than zero** can also fit background work when its service contract fits;
  CPU allocation alone does not wake a service from zero without a request.

These are workload candidates, not the team's accepted landing runtime; `stack-profile` retains
that decision. *[sourced: [Cloud Run resource types](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run),
[billing](https://docs.cloud.google.com/run/docs/configuring/cpu-allocation), and
[autoscaling](https://docs.cloud.google.com/run/docs/about-instance-autoscaling); reviewed 2026-09-20]*

## The map (and where each row bites)

| Cloud Foundry | Cloud Run / GCP | The trap |
|---|---|---|
| `cf push` (buildpacks) | `gcloud run deploy --source` — Cloud Build + Google Cloud buildpacks; Dockerfile wins if present *[sourced: run/docs/deploying-source-code]* | Different buildpack family; pin and test the build, don't assume CF buildpack behavior carries over |
| `manifest.yml` | One **service YAML per app** *[sourced: migrate-configuration page]* | A multi-app manifest becomes N files; shared config duplicates unless templated |
| App instance | Revision instance (autoscaled) | Scale-to-zero default → cold starts where CF kept instances warm |
| `cf events` | `gcloud run revisions list` + Cloud Audit Logs | Nothing emits crash events into `revisions list`; crash evidence is in the logs |
| Routes / Gorouter | Global external Application Load Balancer in front of Cloud Run (recommended); **domain mappings are Preview and "not production-ready due to latency issues"** *[sourced: run/docs/mapping-custom-domains]* | The "just map the route" instinct lands on the preview feature; production routing is an ALB design task |
| Orgs / spaces | Projects (+ folders per environment) | No official CF→GCP org-structure table exists — `[unverified]`; our folder/project layout is a platform-owner decision, record it in `stack-profile` when ratified |
| Service bindings / `VCAP_SERVICES` | Hand-constructed env: the migration doc has you rebuild a `VCAP_SERVICES` value (obtained via `cf env`, a **human-run** credential read) for Spring/Steeltoe autoconfig *[sourced: migrate-configuration page]* | Credentials transit a human, never an agent; long-term, replace VCAP parsing with Secret Manager + native config |
| `cf scale -i N` | `--min-instances` / `--max-instances`, concurrency per instance | CF thinking sizes instances; Cloud Run sizes **concurrency × instances** — retune, don't transliterate |
| Reaching the on-prem databases (all of them are on-prem per `stack-profile`) | **Direct VPC egress** (`--network`, `--subnet`, `--vpc-egress=private-ranges-only` or `all-traffic`) over the interconnect/VPN — no connector, and network cost scales to zero with the service *[sourced: run/docs/configuring/vpc-direct-vpc; reviewed 2026-08-21]* | Each instance takes an IP: "reserve at least 2X the number of IP addresses, plus a buffer", `/26` subnet minimum, ~1 Gbps per instance, and "connection establishment delays of a minute or more on instance startup" have been observed. With Cloud NAT in the path the docs steer back to a Serverless VPC Access connector (30 s+ cold starts otherwise). Size the subnet before the first migration, not after the first outage |
| JVM warm-up on a `cf push` (instance stays warm) | `--cpu-boost`: extra CPU "during instance startup time and for 10 seconds after the instance has started"; `--no-cpu-boost` to disable *[sourced: run/docs/configuring/services/cpu; reviewed 2026-08-21]* | Scale-to-zero exposes JVM startup latency. CPU boost is billed for startup; recommend billed `--min-instances` only when measured cold starts threaten the SLO. |
| Health check (`cf set-health-check`, manifest `health-check-type`) | **Startup probe** (a TCP probe with a 240 s timeout unless configured; `failureThreshold` × `periodSeconds` at most 600 s) plus an optional **liveness probe**, off unless configured *[sourced: run/docs/configuring/healthchecks]* | Size the startup probe for JVM start plus the Direct VPC egress connect delay above; Google recommends "a HTTP startup probe that tests a connection to an egress destination" *[sourced: run/docs/configuring/vpc-direct-vpc]* |
| Run-on-start migrations (Flyway/Liquibase) or `CF_INSTANCE_INDEX`-gated singleton work | A **Cloud Run job** completed before the deploy for migrations; a job or worker pool is a candidate for singleton work | A runtime choice is not a singleton guarantee. Preserve migration locks or other exclusive ownership and [retry-safe/idempotent effects](https://docs.cloud.google.com/run/docs/jobs-retries) across executions, retries and replacement instances; one task or pool instance is insufficient |
| Buildpack-injected agent / sidecar process in one container | **Multi-container service**: one ingress container with an explicit port; up to 10 containers share a network namespace and can use explicitly mounted shared volumes. Startup ordering requires health checks on dependencies *[sourced: [multi-container services](https://docs.cloud.google.com/run/docs/deploying#deploying_multiple_containers_to_a_service)]* | Make the app depend on the collector's startup health check to reduce early span loss. A sidecar needing CPU between requests after startup requires instance-based billing; request-based billing supplies CPU during request processing and ingress startup |
| Container OOM → exit 137 in `cf events` | Read [OOM evidence](../SKILL.md#oom-evidence) | Cloud Logging replaces exit-code grepping |
| `cf rollback` / blue-green | Read the [revision traffic rollback procedure](../SKILL.md#mitigation-you-recommend-never-run-traffic-rollback) | Stable `update-traffic` supports `--set-tags` / `--update-tags` for revision URLs and `--to-tags` for traffic percentages. Assigning a tag alone does not move percentage traffic; `--set-tags` replaces existing tags *[sourced: docs.cloud.google.com/sdk/gcloud/reference/run/services/update-traffic]* |

## Observability during coexistence

While both runtimes serve traffic, one incident can span them. Keep service names identical across
runtimes in telemetry (`service.name`), tag the runtime as a resource attribute, and expect the
"what changed" sweep to cover **both** `cf events` and `gcloud run revisions list` until the PCF
side is dark. The obs skills' GCP references cover where the signals land.
