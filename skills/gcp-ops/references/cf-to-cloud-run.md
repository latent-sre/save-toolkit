# Cloud Foundry → Cloud Run — the concept map and its traps

Google publishes an official migration guide set for exactly this move *[sourced:
docs.cloud.google.com/run/docs/migrate/cloud-foundry/migrate-from-cloud-foundry-to-cloud-run]*.
Sources reviewed 2026-08-07 via indirect retrieval of the official pages; re-verify before
committing a migration decision to a packet.

## Eligibility first

An app qualifies for the straightforward path when it "must use HTTP or HTTP/2 (including gRPC)
and listen for traffic based on the PORT environment variable", stateless *[sourced: migration
overview page]*. TCP-routed apps, apps writing local state, and long-running background workers
need redesign or Cloud Run jobs — flag them early, don't discover them at cutover.

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
| `cf rollback` / blue-green | `gcloud run services update-traffic --to-revisions <rev>=100`; tag-based blue/green is `gcloud beta` *[sourced: run/docs/rollouts-rollbacks-traffic-migration]* | The GA path is revision-percentage traffic; the tag workflow still carries `beta` |

## Observability during coexistence

While both runtimes serve traffic, one incident can span them. Keep service names identical across
runtimes in telemetry (`service.name`), tag the runtime as a resource attribute, and expect the
"what changed" sweep to cover **both** `cf events` and `gcloud run revisions list` until the PCF
side is dark. The obs skills' GCP references cover where the signals land.
