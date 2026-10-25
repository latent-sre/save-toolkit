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

Observe the named Cloud Run service through an authorized, protected read/output path. Before
`describe` or log reads, establish that credentials in environment variables (including
`VCAP_SERVICES`), logs and errors are removed before reaching the model. The guard admits command
syntax; it does not mask output. Without that protection or shell access, the human uses the
console or CLI and returns scoped, sanitized observations. Never request raw configuration or
credential dumps. Changes require the human release owner's exact approval evidence.

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
| All requests or some, since when, at max instances? | Service → **Metrics**: request count, request latencies, container instance count, memory utilization | No GA `gcloud` read; `request_count` by `response_code_class` through obs-analysis' Cloud Monitoring reference |
| Which revisions exist? | Service → **Revision history** | `gcloud run revisions list --service <service> --region <region> --project <project>` |
| Recent request/container errors? | Service → **Logs**; select the last hour | `gcloud run services logs read <service> --freshness=1h --limit=100 --region <region> --project <project>` |

The log CLI bounds age and count.

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
and `--no-traffic` keeps the new revision out of the service URL's percentage-based allocation.
Tagged revision URLs can still receive requests; check tags and request logs as well as percentages.
A human stages a rollout with
`gcloud run services update-traffic <service> --to-revisions <revision>=<percentage> --region <region> --project <project>`; `--to-latest`
instead sends 100% to the latest revision and restores automatic promotion on later deploys.

After listing revisions, inspect one with
`gcloud run revisions describe <revision> --region <region> --project <project>`.
As with `cf events`, a revision near symptom onset is a hypothesis, not proof of cause.

### Startup failures

Compare three observations explicitly: the last successful start, the failed revision's starts,
and new starts of the serving revision. For each, retain its UTC time, warm-up duration, dependency
errors and whether listening actually began; mark unavailable observations as gaps. An earlier
ready state does not establish current startup capacity, and a configured or logged bind address
does not prove an open listener. Revision-level successful requests do not identify which instances
served them; do not assign them to existing or newly started instances without that evidence.

When a shared dependency delays startup, return who checks that dependency and over which observed
interval, how the serving revision's new starts/capacity and request errors should be monitored,
and the recovery evidence needed before the release owner considers another attempt. Keep missing
comparisons, current capacity and recovery evidence explicit.

## Logs — guard-safe filter shapes

```bash
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=<service> AND resource.labels.location=<region> AND NOT severity=DEFAULT AND NOT severity=DEBUG AND NOT severity=INFO AND NOT severity=NOTICE AND NOT severity=WARNING' --freshness=1h --limit=50 --project <project>
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=<service> AND resource.labels.location=<region> AND httpRequest.status=429' --freshness=1h --limit=50 --project <project>
```

The first read keeps ERROR and higher severities using PowerShell-safe exclusions; the second
captures 429s logged at WARNING. Correlate the message, capacity and revision before assigning cause.
Keep the single quotes, freshness and count bounds. Accept `<service>` and `<region>` only as
lowercase letters, digits and inner hyphens; otherwise stop and ask. `--project` selects the log
project; `resource.labels.location` selects the Cloud Run region.
Distinguish the requested filter/window/limit from the returned export's demonstrated coverage;
record unknown truncation or sampling instead of assuming the request was applied.

For historical UTC windows, other filter shapes, shell restrictions or log bucket/view selection,
load `obs-analysis` and its **Cloud Logging dialect** reference; it owns those mechanics and sources.

## Reading failures

Search the logs for the message, then run its first check (liveness probes are off unless
configured):

| Code | Documented message | First check |
|---|---|---|
| Start fails | "Container failed to start. Failed to start and then listen on the port defined by the PORT environment variable." (search `listen on the port`) | The app must listen on `0.0.0.0:$PORT`, not `127.0.0.1`; the PCF `$PORT` discipline transfers exactly |
| 429 | "…aborted because there was no available instance." | Container instance count against max instances (Metrics); a raise is a change to recommend |
| 503 | "…the HTTP response was malformed or connection to the instance had an error." | In order: an [OOM](#oom-evidence) line; `LIVENESS HTTP probe failed` if configured; a framework timeout shorter than the request (Node `server.setTimeout`, Gunicorn `WORKER TIMEOUT`); VPC connector throughput. Over 800 requests/s per instance might exhaust TCP sockets; confirm evidence of that bottleneck and container support for [HTTP/2 cleartext (`h2c`)](https://docs.cloud.google.com/run/docs/configuring/http2#before_you_configure) before recommending HTTP/2 |
| 504 | "…reached the maximum request timeout." | Compare the revision's request timeout with the slow downstream call. A [504 can leave application work running](https://docs.cloud.google.com/run/docs/configuring/request-timeout); check completion/effects and retry safety before recommending a retry or timeout increase |

- **Cold starts** — min-instances is a billed change to recommend, not assume.
- **Concurrency/saturation** — exact defaults vary by deploy path: read them from
  the affected revision and service configuration, don't quote memory.

### OOM evidence

Cloud Logging example: *"While handling this request, the container instance was found to be
using too much memory and was terminated."* (HTTP 500/503; exact target wording is unconfirmed).
**No exit code to grep.** Writes to the default writable container filesystem count toward memory,
including logs outside `/var/log/*` and `/dev/log`. For a leak after PCF migration, check these writes first;
take `resource.labels.revision_name` from the failing log, select that revision in **Revision
history**, or use the target-bound `revisions describe` command above. Read its container memory
limit before recommending a bump; the current service template may describe a later revision.

## Pub/Sub backlogs and GKE pull failures: read the deciding signal first

A growing Pub/Sub backlog looks the same on backlog size alone whether subscribers are too slow for
the arrival rate or a subset of messages fails on every delivery. Before choosing, read
`subscription/oldest_unacked_message_age` beside `num_undelivered_messages`: an oldest age rising as
fast as wall-clock time shows that the oldest cohort has not cleared during that window, not why.
A large same-publish-time cohort can keep age rising at wall-clock rate while acknowledgements
succeed; a long-running leased message can do the same. Slower age growth alone does not prove
completion either: retention expiry can advance the oldest timestamp. Compare acknowledgement/
completion rates with ingress and backlog trends, then inspect handler failures, lease behavior,
and repeated message IDs with failed delivery or acknowledgement evidence before assigning a
failing subset or capacity cause. When an export, sink or view lacks one of these, name the missing
observation and who can read it from Cloud Monitoring; do not infer the cause from the other alone.

For `ImagePullBackOff` or `ErrImagePull` on GKE, establish that the referenced image address and tag
exist in the referenced registry, from the build's push record or the registry itself, before
attributing the failure to access: a missing image and a denied pull both back off. The pull event's
message separates them (`not found` versus `403 Forbidden`); when that message is unavailable, the
push record is the next deciding read.

## Mitigation you recommend (never run): traffic rollback

Traffic rollback routes requests to the previous healthy revision:

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

Claude's fleet credential tripwire denies `gcloud auth print-access-token`, `print-identity-token`,
`application-default print-access-token`, `secrets versions access` and `kms decrypt`, as it denies
`cf env`, across roster lanes: live credentials must never meet an agent that holds egress.
The separate `sre-assistant` gcloud allowlist also denies `--impersonate-service-account` and
`--flags-file`; those flag checks do not cover other lanes. Task authority and protected-output
requirements still apply. A human runs a genuinely needed credential-bearing read and returns
the smallest sanitized excerpt.

## Provisional project/platform ownership

The GCP ownership split is **unconfirmed, not yet ratified**; `stack-profile` carries the working
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
