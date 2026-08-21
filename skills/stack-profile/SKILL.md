---
name: stack-profile
description: >-
  The single stack-definition point — what this team runs today, the stay-in-lane rule, and the
  platform boundary. Load before recommending any runtime, tool, or infrastructure change, and when
  choosing between observability backends. Triggers: "what's our stack", "should we use X for this",
  "can we move this to Kubernetes / the cloud", "which backend do I query". One file changes when the
  ground shifts.
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Stack profile — current facts, not aspirations

Phrased as what is true today. When the ground shifts, this file changes and nothing else does.

## Runtime
On-prem servers + PCF (VMware Tanzu Application Service); `cf` CLI v8 (CAPI V3) — this is what runs
today. **GCP migration is in progress**: GCP is an approved target, arriving (as planned) as
reference files inside the obs skills plus the `gcp-ops` triage skill, not as a restructure. The
landing runtime is **decision-pending** (Cloud Run is the primary candidate for TAS-shaped apps;
GKE only if a workload demands it) — do not present either as decided. [unverified — record the
runtime decision here when a human owner accepts it]. **No self-managed Kubernetes**; on-prem stays
Kubernetes-free.

## Observability — two stacks, coexisting (churn is an axiom, not an event)
| Signal | Incumbent | Additive, first-class |
|---|---|---|
| Logs | Splunk (SPL) | Loki (LogQL) |
| Metrics | Wavefront / Aria Ops for Applications — now Broadcom DX OpenExplore (WQL) | Mimir / Prometheus (PromQL) |
| Traces | — (new capability) | Tempo (TraceQL) |
| Dashboards | Grafana 13.x | Grafana 13.x |
| Alerting / correlation | Moogsoft (Dell APEX AIOps, on-prem v9.x); ThousandEyes synthetics | Grafana unified alerting |
| Pipeline | — | Alloy + OTel collectors |
| Edge / CDN / WAF / RUM | Akamai (Property Manager delivery, App & API Protector, DataStream 2 logs, mPulse RUM) | — |

Both incumbent columns stay first-class — Splunk, Wavefront, Grafana, Alloy, and Prometheus all
deepen in place; none is being retired by team decision. **Vendor lifecycle — `[sourced]`
(reviewed 2026-08-19):** the Wavefront platform continues as **Broadcom DX OpenExplore** — Broadcom
TechDocs introduces it as "a high-performance observability and analytics platform built using
Aria Operations for Applications (Wavefront) and the DX platform", with actively maintained
Wavefront release notes (February 2026) and a TAS integration, under
`techdocs.broadcom.com/us/en/ca-enterprise-software/it-operations-management/dx-openexplore/saas/`.
The 2025-10-31 end-of-availability (support.broadcom.com announcement 25153) retired the VMware
*Tanzu Observability* offering, not the platform. The team's tenant answers as DX OpenExplore —
observed 2026-08-19, UI version 250.1 with residual VMware branding `[sourced: operator
observation]`; the number fits DX OpenExplore's scheme (its release notes cite "version 235.8" in
March 2025). Still `[unverified]`: the team's entitlement/contract basis under Broadcom — the
stack owner records it here when known. As GCP workloads land, Cloud Logging / Cloud Monitoring /
Cloud Trace join as additional backends via reference files in the obs skills — additive, same as
everything else in the right column.

## Languages & CI
Services are built in **Java/JVM, Python, JavaScript/TypeScript, and Go**. Bash and PowerShell are
glue and automation, not service languages. GitHub + GitHub Actions; Bamboo is legacy.
*[sourced: operator statement 2026-08-21]*

**CI jobs authenticate from GitHub environment secrets**, not GitHub OIDC. This settles the hedge
the `ci-actions` skill carries: do not design around a GitHub-OIDC→CredHub exchange — CredHub
authenticates via UAA and no turnkey integration exists. *[sourced: operator statement 2026-08-21]*

## Frameworks
- **Backend:** **Spring Boot** on the JVM (matching the `java_buildpack_offline` in the PCF manifest
  example); **FastAPI** on Python.
- **Frontend:** **both React and Vue** are in use — neither reference in `frontend-craft` is
  surplus.

*[sourced: operator statement 2026-08-21]*

## Hosts & runners
On-prem hosts and self-hosted Actions runners are **RHEL 9+**. GitHub-hosted Linux runners are
Ubuntu. Both classes are in active use, so portable shell
must run on both: the effective **bash floor is 5.1**, past every pre-4.4 workaround.
*[sourced: operator statement 2026-08-21; confirm exact minor versions on the target]*

## Data stores
**PostgreSQL and SQL Server** are the operated engines, **all on-prem today**. Some applications
embed **SQLite**; treat it as something to be aware of, not an engine the team operates — the one
rule worth carrying is that a SQLite file behind a multi-instance app on PCF's ephemeral disk is
not shared and not durable. MySQL exists but is minor; **MariaDB and Oracle are not used**.
A managed cloud database is a possible future addition alongside the GCP migration, but
nothing is running there now: treat cloud-database guidance as not-yet-applicable rather than
optional. Engine-specific migration, locking, and failover mechanics remain `[unverified]` per
target until captured against a real instance. *[sourced: operator statement 2026-08-21]*

## Incident response
A formal on-call rotation is in place, with a four-tier severity ladder:

| Tier | Meaning |
|---|---|
| **P1** | Critical |
| **P2** | High |
| **P3** | Medium |
| **P4** | Low |

Use these names directly — `incident-command`, `obs-alerting`, and `postmortem` refer to this
ladder rather than inventing their own. Entry criteria per tier are **not yet recorded here**;
capture them when the incident owner confirms them. *[sourced: operator statement 2026-08-21]*

## Change management
Change records live in **both BMC Remedy and Jira**. `production-change-gate` refers to "the formal
change record" generically; name whichever system governs the change in hand rather than assuming
one. *[sourced: operator statement 2026-08-21]*

## Documentation home
**The team-owned GitHub repository is the living source.** Confluence still holds operational
documentation and is actively being drained into the repo — one direction, import only. Both
therefore exist today, but they are not co-equal homes: a page in Confluence is a source to import,
not a destination to write to.

What follows for the document lanes: `scribe` authors into the repository (it has no web tools and
could not reach Confluence anyway), `runbook` owns the import path, and
`skills/runbook/scripts/confluence_to_runbook.py` is live working software, not a migration
leftover. Never write new operational documentation into Confluence.
*[sourced: operator statement 2026-08-21]*

## Stay in lane
Stay in the app/ops lane; hand platform-internal problems to the platform team. GCP managed
services are now in-lane **for the migration** (Cloud Run, Cloud Logging/Monitoring/Trace,
Secret Manager); do not propose self-managed Kubernetes anywhere, and do not propose GKE while the
landing-runtime decision is pending — flag the need instead. On-prem/PCF infra-layer fixes remain
out of lane.

## The platform boundary
We own our apps up to the platform edge; we do not operate the platform. On PCF: BOSH, Ops Manager,
Diego cells, Gorouter, CredHub/UAA, and foundation upgrades belong to the platform team. When a
problem is platform-side (many apps failing at once, failing cells, Gorouter-wide 5xx), recognize it
and escalate with evidence — timestamps, blast radius, `cf` output showing our app healthy — do not
operate BOSH. On GCP the boundary moves and is **not yet ratified**: the team owns more (service
config, revisions, project-scoped observability), while org policy, folder/project structure,
shared networking, and IAM beyond project scope sit with the cloud platform owner. Treat that split
as [unverified] until recorded here; the `gcp-ops` skill carries the working boundary rules. Akamai
delivery and WAF config is team-owned change-managed work (see the `akamai-edge` skill); Akamai the
platform — the edge network itself — is Akamai's.

## Copilot models (recorded here once, never in agent files — no agent pins a model)
Selection rule: primary = the strongest Claude model in the team's Copilot picker at ship time;
middle fallback = the next approved Claude model; final fallback = the org's default non-Claude model.
Recorded ordered list: Claude Sonnet 5 (copilot) → Claude Opus 4.8 (copilot) → GPT-5.4 (copilot).
[unverified — confirmed for the team license tier in Phase 5; re-record the complete ordered list when it changes]

<!-- profile canary: sp_7c2e — quoted output proves this file loaded; guarded by the tripwire test -->
