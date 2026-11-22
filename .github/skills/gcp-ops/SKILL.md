---
name: gcp-ops
description: >-
  Investigate application-side GCP failures during the migration — Cloud Run services and
  revisions, gcloud logging reads, what-changed correlation against revision deploys, and the
  project-vs-platform boundary. Triggers: 'the Cloud Run service is 503ing', 'read the GCP logs',
  'container failed to listen on PORT', 'roll back the Cloud Run service to the previous
  revision'. Related owners: `stack-profile` (boundary and runtime decisions), obs-analysis
  (log-query dialects), pcf-ops (the PCF side while both runtimes coexist).
compatibility: Requires read access to the target Cloud Run service and logs; use Cloud Console or an installed gcloud CLI
argument-hint: "[the GCP service or symptom]"
---

# GCP application-side triage (console or gcloud, read-only)

Observe the named Cloud Run service through an authorized read path that keeps credentials
(env vars including `VCAP_SERVICES`, Secret Manager values, raw configs) out of agent context. When
CLI access or output masking is unavailable, ask the human for Console or sanitized excerpts.
Changes require human release owner approval under `production-change-gate`.

## First look

Confirm the caller's explicit project, service, and region (`--project <project> --region <region>`).
Use `gcloud config get-value project` / `run/region` only for single properties if needed, never full
config dumps. Ask the caller or check the team's inventory if the service is unnamed.

| Question | Cloud Console | `gcloud` equivalent |
|---|---|---|
| Service details? | **Cloud Run → Services** → select service | `gcloud run services describe <service> --region <region> --project <project>` |
| Traffic / latency / max instances? | Service → **Metrics** (count, latency, instances, memory) | Use Cloud Monitoring (`request_count` via `obs-analysis`). Note: `request_count` excludes 429s rejected at max instances — count `httpRequest.status=429` in request logs |
| Which revisions exist? | Service → **Revision history** | `gcloud run revisions list --service <service> --region <region> --project <project>` |
| Recent errors? | Service → **Logs** (last hour) | `gcloud run services logs read <service> --freshness=1h --limit=100 --region <region> --project <project>` |

List services if unknown: `gcloud run services list --region <region> --project <project>`. Report the
target, revision names/traffic splits, UTC window, and sanitized error excerpts.

## Revisions — correlate changes with symptoms

Every deploy creates an immutable **revision** (image, env, limits, concurrency). A new deploy
receives traffic **only if** the service still tracks latest: pinned percentage splits persist across
later deploys until `--to-latest` is set, and `--no-traffic` keeps a new revision off the main URL.
Check tagged revision URLs separately — they serve requests independently of main percentage splits.
Inspect a specific revision with `gcloud run revisions describe <revision> --region <region> --project <project>`.

## Logs — guard-safe filter shapes

```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=<service> AND resource.labels.location=<region> AND NOT severity=DEFAULT AND NOT severity=DEBUG AND NOT severity=INFO AND NOT severity=NOTICE AND NOT severity=WARNING' --freshness=1h --limit=50 --project <project>
```

Keep single quotes, `--freshness`, and `--limit`, and validate `<service>`/`<region>` as lowercase
alphanumeric/hyphen identifiers. This PowerShell-safe filter keeps `ERROR+` and omits `429` aborts
logged at `WARNING` — query `httpRequest.status=429` separately when checking capacity rejections.
For historical UTC windows, bucket/view selection, and Cloud Logging dialect details, load `obs-analysis`.

## Reading failures

| Code | Documented message | First check |
|---|---|---|
| Start fails | `"Container failed to start. Failed to start and then listen on the port defined by the PORT environment variable."` | Listen on `0.0.0.0:$PORT`, not `127.0.0.1` |
| 429 | `"…aborted because there was no available instance."` | Check instance count vs. max instances; below max points to traffic burst, slow startup, or long requests |
| 500 | `"…no available instance"` or `"…instance could not start successfully"` | Below-max burst (check min instances, startup time, retries) vs. startup/Secret Manager failure (read startup logs) |
| 503 | `"…the HTTP response was malformed or connection to the instance had an error."` | Check in order: [OOM](#oom-evidence); `LIVENESS HTTP probe failed`; framework timeout shorter than request (`server.setTimeout`, Gunicorn `WORKER TIMEOUT`); VPC connector or >800 rps/instance TCP socket exhaustion (verify container `h2c` support before recommending HTTP/2) |
| 503 | `"…probably has reached its maximum container instance limit."` | Instance count vs. max instances and CPU; recommend raising max instances or lowering concurrency |
| 504 | `"…reached the maximum request timeout."` | Compare revision request timeout against slow downstream call; check retry safety before raising timeout (work may still complete) |

If errors appear across multiple services/jobs simultaneously, check for a **billing spend cap**
banner (resuming can take up to 30 minutes after lifting). Read concurrency/limits from the revision
config rather than quoting defaults.

### OOM evidence

Cloud Logging reports: *"While handling this request, the container instance was found to be using
too much memory and was terminated."* (HTTP 500/503; **no exit code 137 to grep**). Writes to the
default writable container filesystem count toward memory (regional ephemeral-disk volume quota
starts at 0 GiB until requested). Read the failing `resource.labels.revision_name` via
`revisions describe` before recommending a memory bump — the current service template may show a newer revision.

## Mitigation you recommend (never run): traffic rollback

Match failing `httpRequest.requestUrl` to serving `resource.labels.revision_name` and compare current
vs. last known-good routing (service splits, tagged URLs, upstream LB host/path rules). Confirm the
target revision has capacity and compatibility before recommending a write:

- **Tagged URL only:** `--update-tags <tag>=<revision>` (retire new tags only with caller agreement).
- **Service URL:** `<previous-revision>=100` (or restore prior split; use `--to-latest` only after confirming latest):

```bash
gcloud run services update-traffic <service> --to-revisions <revision>=80,<previous-revision>=20 --region <region> --project <project>
```

Human release owners execute this Tier 2 change under `production-change-gate` (ITO approves in TLC
for declared incidents); read back effective routes and verify responses + 429 logs afterward.

## Cloud Foundry → Cloud Run mapping

Read [references/cf-to-cloud-run.md](./references/cf-to-cloud-run.md) before translating PCF habits
into GCP designs or triage.
