---
name: gcp-ops
description: >-
  Investigate application-side GCP failures during the migration — Cloud Run services and
  revisions, gcloud logging reads, what-changed correlation against revision deploys, and the
  project-vs-platform boundary. Triggers: 'the Cloud Run service is 503ing', 'read the GCP logs',
  'container failed to listen on PORT', 'roll back to the previous revision'. Ownership map
  only—not a load: the `stack-profile` skill supplies boundary facts; obs-logs owns backend
  log-query dialects; pcf-ops owns the PCF side while both runtimes coexist.
compatibility: Requires the gcloud CLI and viewer access to the target GCP project
argument-hint: "[the GCP service or symptom]"
---

# GCP application-side triage (gcloud, read-only)

The migration's Cloud Run lane. Observe the service and assemble evidence; state-changing commands
belong to a human release owner with exact approval evidence. The read-only guard allows the
specific gcloud reads below; anything else you *recommend* with the exact command and expected
output for a human to run.

Read-only first look, substituting the caller's service, region, and project:

```
gcloud config list
gcloud run services describe <service> --region <region> --project <project>
gcloud run revisions list --service <service> --region <region> --project <project>
gcloud run services logs read <service> --limit=100 --region <region> --project <project>
```

The service describe, revision list, and service-log forms above are *[sourced:
docs.cloud.google.com/sdk/gcloud/reference/run/services/describe;
docs.cloud.google.com/sdk/gcloud/reference/run/revisions/list;
docs.cloud.google.com/sdk/gcloud/reference/run/services/logs/read]*. Use `gcloud run services list`
only when the service name itself is unknown.

A failing container listening on `127.0.0.1` instead of `0.0.0.0:$PORT` is a common startup cause.
A traffic rollback is Tier 2: the human release owner executes it, verified by error rate.

Record our projects, regions, and service inventory in
[references/projects.md](./references/projects.md).

## The revision model — "what changed?" is one command

Every deploy creates an immutable **revision** (image + env + limits + concurrency). A new
deployment takes traffic only while the service still tracks the latest revision:
an existing traffic split or previous-revision assignment persists across later deployments,
and `--no-traffic` keeps the new revision unrouted until traffic is explicitly assigned.
A human stages a rollout with
`gcloud run services update-traffic <service> --to-revisions <revision>=<percentage>`; `--to-latest`
instead sends 100% to the latest revision and restores automatic promotion on later deploys
*[sourced: docs.cloud.google.com/run/docs/resource-model;
docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration]*.

The PCF `cf events` question becomes:

```bash
gcloud run revisions list --service <service>
gcloud run revisions describe <revision>
```

A new revision lining up with incident onset is the prime suspect — same discipline as `cf events`:
temporal alignment is a hypothesis, not proof.

## Logs — guard-safe filter shapes

```bash
gcloud run services logs read <service> --limit=100
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=<service> AND severity=(ERROR OR CRITICAL)' --freshness=1h --limit=50
```

Two shapes matter to this fleet specifically:

- Use **`--freshness`** for the time bound and keep the whole Logging filter in one quoted argument.
  `severity>=ERROR` is valid and guard-safe when quoted; the unquoted spelling is shell redirection
  and is denied. `severity=(ERROR OR CRITICAL)` remains a guard-safe alternate spelling.
- The Logging query language details (operators, `log_id()`, `SEARCH()`) belong to the `obs-logs`
  skill's GCP reference — load that for query construction; this skill owns the triage flow.

## Reading failures

- **"Container failed to start and listen on the port defined by the PORT environment variable"**
  — the app must listen on `0.0.0.0:$PORT`, not `127.0.0.1`
  *[sourced: docs.cloud.google.com/run/docs/troubleshooting]*. The PCF `$PORT` discipline
  transfers exactly.
- **Cold starts** — min-instances is a billed change to recommend, not assume.
- **Concurrency/saturation** — exact defaults vary by deploy path: `[unverified]`, read them from
  `services describe`, don't quote memory.
- **OOM** — exact memory-limit error text `[unverified]`; corroborate with the revision's memory
  limit from `services describe` before recommending a bump, same 137-discipline as PCF.

## Mitigation you recommend (never run): traffic rollback

Instant rollback is routing traffic to the previous healthy revision *[sourced:
docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration]*:

```bash
gcloud run services update-traffic <service> --to-revisions <previous-revision>=100
```

Tier 2, human release owner, with the exact revision names, verification (error rate on the service
dashboard), and a command that restores the intended prior traffic allocation or `--to-latest`
tracking policy. Traffic changes are not instantaneous — in-flight requests may land on either
revision during the transition.

## Credential-bearing reads are human-only

The guard denies `gcloud auth print-access-token`, `print-identity-token`,
`application-default print-access-token`, `gcloud secrets versions access`, and `gcloud kms
decrypt` for the same reason it denies `cf env`: live credentials must never meet an agent that
holds egress. A human runs them if genuinely needed and pastes the smallest sanitized excerpt.
`--impersonate-service-account` and `--flags-file` are denied on every command — identity pivots
and flag smuggling, not reads.

## Project-side vs platform-side (the boundary moved — know the new one)

On GCP this team owns more than it did on PCF: service config, revisions, project-scoped IAM and
observability are **ours**. Org policy, folder/project structure, shared VPC/networking, and IAM
above project scope sit with the cloud platform owner — Google's shared-responsibility line makes
IAM configuration and hierarchy explicitly customer-owned work *[sourced:
cloud.google.com/architecture/framework/security/shared-responsibility-shared-fate]*, and our
internal split of that customer side is **not yet ratified** (`stack-profile` carries the current
state). Escalate with the same escalation packet `pcf-ops` owns: symptom with UTC onset and trend, blast
radius across services and projects, evidence our service is healthy, what was ruled out app-side,
the platform-level signal that points past us, and `[unverified]` on every causal claim.

## Cloud Foundry → Cloud Run mapping

The concept map and migration gotchas (manifest → service YAML, routes → load balancer vs
domain-mapping preview, VCAP_SERVICES) live in
[references/cf-to-cloud-run.md](./references/cf-to-cloud-run.md) — read it before translating any
PCF habit into a GCP recommendation.
