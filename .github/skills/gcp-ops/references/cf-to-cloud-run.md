# Cloud Foundry → Cloud Run — the concept map and its traps

Check Google's [migration recipe](https://docs.cloud.google.com/run/docs/migrate/cloud-foundry/migrate-from-cloud-foundry-to-cloud-run)
against the workload. `stack-profile` retains the pending landing-runtime and internal ownership decisions;
these capabilities select neither runtime nor change authority.

## Eligibility first

The recipe assumes HTTP/HTTP2/gRPC on `$PORT`, no unchanged CF path routing or route-service proxy,
no instance identity/addressability or startup-order dependency, and no startup side effects such
as migrations. An unmet assumption needs design assessment, not automatic Cloud Run rejection:
[Application Load Balancers can route paths across services](https://docs.cloud.google.com/run/docs/mapping-custom-domains#mapping_custom_domains_with_a_global_external_application_load_balancer).
Assess TCP routing and durable local storage separately.

Finite tasks fit jobs; continuous non-HTTP pull workers may fit worker pools after regional,
scaling and recovery checks. A service with instance-based billing and minimum instances > 0 may
also fit background work; CPU allocation alone cannot wake it from zero without a request.

## The map (and where each row bites)

| Cloud Foundry | Cloud Run / GCP | The trap |
|---|---|---|
| Buildpack `cf push` | `gcloud run deploy --source`: Cloud Build + Google buildpacks; Dockerfile takes precedence | Pin/test the different buildpack family |
| Multi-app manifest | One service YAML per app | Shared configuration needs explicit management |
| Warm app instances | Autoscaled revision instances | Scale-to-zero exposes cold starts |
| `cf events` | Revision list plus Audit Logs | `revisions list` contains no crash events; inspect logs |
| Routes/Gorouter | Global external Application Load Balancer | Domain mappings remain Preview and not production-ready due to latency; do not equate them with CF routes |
| Orgs/spaces | Projects/folders | Layout is a platform-owner decision, not a prescribed CF mapping |
| Service bindings / `VCAP_SERVICES` | Migration recipe reconstructs env for Spring/Steeltoe autoconfig | `cf env` is a human-only credential read; never pass raw values to an agent. Assess Secret Manager/native config as the longer-term alternative |
| `cf scale -i N` | Min/max instances plus per-instance concurrency | Retune concurrency × instances rather than copying counts |
| On-prem database connectivity | Direct VPC egress over interconnect/VPN | Select network/subnet and `private-ranges-only` versus `all-traffic`; account for IP demand and startup delay below |
| JVM warm-up | `--cpu-boost` / `--no-cpu-boost` | Boost supplies extra CPU during startup and 10 s afterward and is billed. Propose billed minimum instances only when measured cold starts threaten the SLO |
| CF health check | Startup probe plus optional liveness | Default TCP startup timeout 240 s; configured startup `failureThreshold × periodSeconds` limit is 600 s for non-GPU services. Include JVM and egress warm-up; liveness is off unless configured |
| Startup migrations / `CF_INSTANCE_INDEX` singleton | Pre-deploy completed job for migrations; job/worker pool candidates for singleton work | One task/instance is no singleton guarantee: retain exclusive ownership/migration locks and [retry-safe effects](https://docs.cloud.google.com/run/docs/jobs-retries) across retries and replacement instances |
| Buildpack agent / colocated process | Multi-container service: one ingress container with explicit port, up to 10 sharing networking and explicitly mounted volumes | Startup ordering needs dependency health checks; app dependency on collector startup reduces early span loss. Between-request sidecar CPU needs instance-based billing; request billing supplies CPU during requests and ingress startup |
| OOM exit 137 | [Cloud Logging OOM evidence](../SKILL.md#oom-evidence) | Bind memory observations to the failing revision rather than grep exit codes |
| Rollback/blue-green | [Revision traffic rollback](../SKILL.md#mitigation-you-recommend-never-run-traffic-rollback) | `--set-tags` replaces tags; `--update-tags` updates them; tagging alone moves no percentage traffic. `--to-tags` assigns percentages |

[Direct VPC egress](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc) needs no connector. Services/worker pools need at least 2× instance-count IPs plus
revision-update buffer; the subnet must be `/26` or larger. Jobs have different per-task allocation:
size for their concurrency rather than using the service formula. Throughput is up to 1 Gbps per
instance. Egress connections can take a minute or more at startup; use an HTTP startup probe testing
the actual egress destination with appropriate retries/period/threshold. Cloud NAT can add 30 s+
cold-start delay; a Serverless VPC Access connector is Google's startup-performance alternative,
not a universal requirement. Confirm workload-specific limits before sizing.

## Observability during coexistence

Keep the same logical service's `service.name` across runtimes and distinguish runtime with a
resource attribute. Compare both CF events and Cloud Run revisions while both serve traffic;
`obs-analysis` supplies the GCP signal references. Migration does not make either side authoritative
for the other's health.
