# Cloud Foundry → Cloud Run — the concept map and its traps

Check Google's [migration recipe](https://docs.cloud.google.com/run/docs/migrate/cloud-foundry/migrate-from-cloud-foundry-to-cloud-run)
against the workload (`stack-profile` owns landing-runtime and platform-boundary decisions).

## Eligibility first

Cloud Run fits stateless HTTP/HTTP2/gRPC apps listening on `$PORT` with no unchanged CF path routing,
route-service proxy, instance addressability, startup-order dependency, or startup migrations. Path
routing across services can use an [Application Load Balancer](https://docs.cloud.google.com/run/docs/mapping-custom-domains#https-load-balancer).
Finite tasks fit Cloud Run Jobs; non-HTTP pull workers fit worker pools or instance-billed services
with `min-instances > 0` (CPU allocation alone cannot wake a scaled-to-zero service without a request).

## The map (and where each row bites)

| Cloud Foundry | Cloud Run / GCP | The trap |
|---|---|---|
| Buildpack `cf push` | `gcloud run deploy --source`: Cloud Build + Google buildpacks (Dockerfile wins if present) | Pin and test the different buildpack family |
| `cf events` | Revision list + Cloud Audit Logs | `revisions list` omits crash events; inspect Cloud Logging |
| Routes / Gorouter | Global external Application Load Balancer | Domain mappings are Preview (not production-ready due to latency); do not treat as CF route equivalents |
| Service bindings / `VCAP_SERVICES` | Migration recipe reconstructs env for Spring/Steeltoe autoconfig | `cf env` is human-only; migrate to Secret Manager / native config long-term |
| `cf scale -i N` | Min/max instances + per-instance concurrency | Retune `concurrency × instances` rather than copying instance counts |
| On-prem DB connectivity | Direct VPC egress over Interconnect/VPN | Pick network/subnet and `private-ranges-only` vs. `all-traffic`; size subnet IPs and startup probe |
| JVM warm-up | `--cpu-boost` / `--no-cpu-boost` | Extra CPU lasts through startup + 10 s and is billed; propose `min-instances` only when cold starts breach SLO |
| CF health check | Startup probe + optional liveness and HTTP/gRPC readiness | Default TCP startup timeout 240 s (max `failureThreshold × periodSeconds` 600 s); liveness is off unless configured; readiness removes failing instances from serving without restart (unless session affinity) |
| Startup migrations / `CF_INSTANCE_INDEX` singleton | Pre-deploy Cloud Run Job (migrations); Job, worker pool, or Cloud Run instance (Preview) | One task/instance is no singleton guarantee: retain migration locks and [retry-safe effects](https://docs.cloud.google.com/run/docs/jobs-retries) |
| Buildpack sidecar / colocated process | Multi-container service (1 ingress with port, up to 10 containers sharing localhost/volumes) | Add dependency health checks so app waits for collector startup; background sidecar CPU needs instance-based billing |
| OOM exit 137 | [Cloud Logging OOM evidence](../SKILL.md#oom-evidence) | Bind memory limits to the failing revision rather than grepping exit codes |
| Rollback / blue-green | [Revision traffic rollback](../SKILL.md#mitigation-you-recommend-never-run-traffic-rollback) | `--set-tags` replaces tags; `--update-tags` updates; `--to-tags` shifts percentages |

## Direct VPC egress sizing

- Direct VPC egress needs no connector, requires a `/26` or larger subnet, and consumes at least
  `2 × instance-count` IPs plus revision-update buffer (throughput up to 1 Gbps/instance; Jobs use
  task concurrency sizing).
- Egress initialization can take 60 s+: configure an HTTP startup probe exercising the real egress
  destination. Cloud NAT can add 30 s+ cold-start delay (Serverless VPC Access connector is Google's
  low-latency alternative where needed).
