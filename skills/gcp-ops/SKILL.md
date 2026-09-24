---
name: gcp-ops
description: >-
  Investigate application-side GCP failures during the migration — Cloud Run services and
  revisions, gcloud logging reads, what-changed correlation against revision deploys, and the
  project-vs-platform boundary. Triggers: 'the Cloud Run service is 503ing', 'read the GCP logs',
  'container failed to listen on PORT', 'roll back the Cloud Run service to the previous
  revision'. Related owners: `stack-profile` (boundary and runtime decisions), obs-logs
  (log-query dialects), pcf-ops (the PCF side while both runtimes coexist).
compatibility: Requires read access to the target Cloud Run service and logs; use Cloud Console or an installed gcloud CLI
argument-hint: "[the GCP service or symptom]"
---

# GCP application-side triage (console or gcloud, read-only)

Observe the named Cloud Run service. Claude's read-only guard allows the reads below; a lane
without shell access asks the human to run them. Changes require the human release owner's exact
approval evidence.

## First look

Confirm the caller's project, service and region in **Cloud Run → Services**. In the CLI,
`gcloud config get-value project` and `gcloud config get-value run/region` show ambient target
defaults; use the caller's explicit target in every command. Configuration reads must select one
reviewed property: `project`, `core/project`, `run/region`, `compute/region`, or `compute/zone`,
using `config list` or `config get-value` without extra flags. Broad listings, section-wide reads,
account identity and credential properties are excluded; configuration can contain passwords.

| Question | Cloud Console | `gcloud` equivalent |
|---|---|---|
| Service details? | Select the service to open its details | `gcloud run services describe <service> --region <region> --project <project>` |
| All requests or some, since when, at max instances? | Service → **Metrics**: request count, request latencies, container instance count, memory utilization | No GA `gcloud` read; `request_count` by `response_code_class` through obs-metrics' Cloud Monitoring reference |
| Which revisions exist? | Service → **Revision history** | `gcloud run revisions list --service <service> --region <region> --project <project>` |
| Recent request/container errors? | Service → **Logs**; select the last hour | `gcloud run services logs read <service> --freshness=1h --limit=100 --region <region> --project <project>` |

[sourced] Google documents these [service details](https://docs.cloud.google.com/run/docs/managing/services),
[metrics](https://docs.cloud.google.com/run/docs/monitoring),
[revision](https://docs.cloud.google.com/run/docs/managing/revisions),
and [log views](https://docs.cloud.google.com/run/docs/logging);
the [log CLI](https://docs.cloud.google.com/sdk/gcloud/reference/run/services/logs/read) bounds age and count.

Bring back the target, revision names/traffic allocation, observation time and log window in UTC,
and a small sanitized error excerpt. A revision's existence is not proof it serves traffic or
that requests succeed. Missing CLI: use the console. An unavailable, empty or denied view leaves
the observation unknown; ask the service owner for that scoped read and its coverage. Missing
access or data is not health evidence. For a different log window, use the log
query guidance below. If the service name is unknown, use
`gcloud run services list --region <region> --project <project>`.

When the caller has not supplied the project, region or service, read the human-maintained
[references/projects.md](./references/projects.md); a placeholder row means ask the caller.

## Revisions — correlate changes with symptoms

Every deploy creates an immutable **revision** (image + env + limits + concurrency). A new
deployment takes traffic only while the service still tracks the latest revision:
an existing traffic split or previous-revision assignment persists across later deployments,
and `--no-traffic` keeps the new revision unrouted until traffic is explicitly assigned.
A human stages a rollout with
`gcloud run services update-traffic <service> --to-revisions <revision>=<percentage> --region <region> --project <project>`; `--to-latest`
instead sends 100% to the latest revision and restores automatic promotion on later deploys
*[sourced: docs.cloud.google.com/run/docs/resource-model;
docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration]*.

After listing revisions, inspect one with
`gcloud run revisions describe <revision> --region <region> --project <project>`.
As with `cf events`, a revision near symptom onset is a hypothesis, not proof of cause.

## Logs — guard-safe filter shapes

```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=<service> AND resource.labels.location=<region> AND NOT severity=DEFAULT AND NOT severity=DEBUG AND NOT severity=INFO AND NOT severity=NOTICE AND NOT severity=WARNING' --freshness=1h --limit=50 --project <project>
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=<service> AND resource.labels.location=<region> AND httpRequest.status=429' --freshness=1h --limit=50 --project <project>
```

The first read is `severity>=ERROR` spelled as exclusions of the five lower severities *[sourced:
LogSeverity, docs.cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry]*; the second
catches no-available-instance 429s, logged at WARNING. A 429 alone does not establish the cause;
correlate the message, capacity and affected revision *[sourced:
docs.cloud.google.com/run/docs/troubleshooting; reviewed 2026-09-09]*.

- Same filters in Bash and PowerShell: the PowerShell guard refuses `>`, `<` and parentheses even
  inside quotes, and Google requires parentheses whenever AND and OR are mixed. Keep the filter
  single-quoted; bound time with **`--freshness`**.
- Accept `<service>` and `<region>` only as lowercase letters, digits and inner hyphens, which the
  query language takes unquoted *[sourced: Logging query language]*; anything else is a stop-and-ask.
- Query-language detail (operators, `log_id()`, `SEARCH()`) is the `obs-logs` skill's GCP
  reference — load that for query construction; this skill owns the triage flow.

Cloud Logging's `--project` selects the log project; `resource.labels.location` selects the
Cloud Run region, not the log bucket's `--location` *[sourced:
docs.cloud.google.com/sdk/gcloud/reference/logging/read;
docs.cloud.google.com/logging/docs/api/v2/resource-list#cloud_run_revision]*.

## Reading failures

Search the logs for the message, then run its first check *[sourced:
docs.cloud.google.com/run/docs/troubleshooting; liveness probes are off unless configured,
…/run/docs/configuring/healthchecks]*:

| Code | Documented message | First check |
|---|---|---|
| Start fails | "Container failed to start. Failed to start and then listen on the port defined by the PORT environment variable." (search `listen on the port`) | The app must listen on `0.0.0.0:$PORT`, not `127.0.0.1`; the PCF `$PORT` discipline transfers exactly |
| 429 | "…aborted because there was no available instance." | Container instance count against max instances (Metrics); a raise is a change to recommend |
| 503 | "…the HTTP response was malformed or connection to the instance had an error." | In order: an [OOM](#oom-evidence) line; `LIVENESS HTTP probe failed` if a liveness probe is configured; a framework timeout shorter than the request (Node `server.setTimeout`, Gunicorn `WORKER TIMEOUT`); a Serverless VPC Access connector's throughput; over 800 requests/s per instance exhausts TCP sockets — turn on HTTP/2 |
| 504 | "…reached the maximum request timeout." | The revision's request timeout against the slow downstream call; find that call before raising the timeout |

- **Cold starts** — min-instances is a billed change to recommend, not assume.
- **Concurrency/saturation** — exact defaults vary by deploy path: `[unverified]`, read them from
  the affected revision and service configuration, don't quote memory.

### OOM evidence

Cloud Logging example: *"While handling this request, the container instance was found to be
using too much memory and was terminated."* (HTTP 500/503; exact target wording `[unverified]`).
**No exit code to grep.** Local filesystem writes count toward memory, including logs outside
`/var/log/*` and `/dev/log`. For a leak appearing after PCF migration, check these writes first;
take `resource.labels.revision_name` from the failing log, select that revision in **Revision
history**, or use the target-bound `revisions describe` command above. Read its container memory
limit before recommending a bump; the current service template may describe a later revision
*[sourced: docs.cloud.google.com/run/docs/troubleshooting; reviewed 2026-08-21]*.

## Mitigation you recommend (never run): traffic rollback

Traffic rollback routes requests to the previous healthy revision *[sourced:
docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration]*:

```bash
gcloud run services update-traffic <service> --to-revisions <previous-revision>=100 --region <region> --project <project>
```

Choose `<previous-revision>` from evidence, never creation order: the revision that served before
onset (the split in `services describe`, the deploy record, or pre-onset request logs by
`resource.labels.revision_name`) and had a normal error rate then. Put both in the packet.

Tier 2, human release owner, with the exact revision names, verification (request count by
response class on the service's Metrics tab), and a command that restores the intended prior
traffic allocation or `--to-latest` tracking policy. Traffic changes are not instantaneous —
in-flight requests may land on either revision during the transition. During a declared incident,
`incident-investigation` advises and ITO approves in the TLC under `production-change-gate`'s
incident fast path.

## Credential-bearing reads are human-only

Claude's guard denies `gcloud auth print-access-token`, `print-identity-token`,
`application-default print-access-token`, `secrets versions access` and `kms decrypt`, as it denies
`cf env`: live credentials must never meet an agent that holds egress. It also denies
`--impersonate-service-account` and `--flags-file` on every command. A human runs a genuinely
needed one and pastes the smallest sanitized excerpt.

## Provisional project/platform ownership

The GCP ownership split is **[unverified], not yet ratified**; `stack-profile` carries the working
proposal, and Google's customer/provider boundary does not settle our internal owners. Confirm the
responsible owner before recommending a change, and escalate with `pcf-ops`'s packet: symptom and
UTC timing (onset unknown if not established), scope across services/projects, checks and their
limits, shared dependencies, and the evidence the receiving owner can add. Running instances and
clean logs do not certify the service healthy; broad impact justifies involving owners without
proving fault ownership.

## Cloud Foundry → Cloud Run mapping

The concept map and migration gotchas (manifest → service YAML, routes → load balancer vs
domain-mapping preview, VCAP_SERVICES) live in
[references/cf-to-cloud-run.md](./references/cf-to-cloud-run.md) — read it before translating any
PCF habit into a GCP recommendation.
