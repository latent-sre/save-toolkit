---
name: stack-profile
description: >-
  The single stack-definition point — what this team runs today, the stay-in-lane rule, and the
  platform boundary. Load before recommending any runtime, tool, or infrastructure change, and when
  choosing between observability backends. Triggers: "what's our stack", "should we use X for this",
  "can we move this to Kubernetes / the cloud", "which backend do I query". This skill bundle changes
  when the ground shifts.
argument-hint: "[the runtime, tool, or infrastructure question]"
---

# Stack profile — current facts, not aspirations

Phrased as what is true today. When the ground shifts, update this canonical skill bundle and
regenerate its projections; no other canonical stack definition should change.
Use only `[verified]`, `[sourced]`, and `[unverified]` evidence labels, and keep each claim's state
intact in transit; describe an inference in prose and label it `[unverified]` rather than inventing a
fourth state. A planned or candidate technology is never a current-stack fact until a human owner
records the decision here.

## Runtime
On-prem servers + PCF (VMware Tanzu Application Service); `cf` CLI v8 (CAPI V3) — this is what runs
today. **GCP migration is in progress**: GCP is an approved target, arriving (as planned) as
reference files inside the obs skills plus the `gcp-ops` triage skill, not as a restructure. The
landing runtime is **decision-pending** (Cloud Run is the primary candidate for TAS-shaped apps;
GKE only if a workload demands it) — do not present either as decided. [unverified — record the
runtime decision here when a human owner accepts it]. **No self-managed Kubernetes**; on-prem stays
Kubernetes-free.

## Observability decision

The incumbent and additive observability stacks coexist as first-class; no listed backend is retired
by team decision. Read the conditional observability reference for the signal inventory, query
languages, lifecycle evidence, and GCP additions.

## Read only the conditional stack facts the request needs

| If the request involves… | Read first |
|---|---|
| A broad inventory or cross-domain comparison, including "what's our stack" | All three: [Observability stack](./references/observability-stack.md), [Application and data stack](./references/application-and-data-stack.md), and [Copilot models](./references/copilot-models.md) |
| An observability backend, signal, query language, vendor lifecycle, GCP observability choice, or edge/CDN/WAF/RUM product | [Observability stack](./references/observability-stack.md) |
| A service language, framework, CI platform, tooling, or authentication design, runner/host assumption, or data-store choice | [Application and data stack](./references/application-and-data-stack.md) |
| Selecting or recording the team's current Copilot model and fallbacks | [Copilot models](./references/copilot-models.md) |

Load every matching row and no others. These references provide current facts; they do not widen
the app/ops lane, settle a pending decision, authorize a platform change, or replace target-specific
verification. The entrypoint rules remain authoritative after a reference is loaded.

## Incident response
A formal on-call rotation is in place. *[sourced: operator statement 2026-08-21]*
`incident-command` owns the current P1–P4 entry criteria, response roles, and communications cadence
and records their ratification status; load it whenever severity, roles, or incident communications
matter. Other skills consume the selected tier without copying its rubric.

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

## Model rule

No agent sets `model:` today; inheriting the session model remains the default. A Claude agent may
use a generation alias (`haiku`, `sonnet`, `opus`, `fable`, or `inherit`) only when its lane's cost
or latency profile justifies tiering, and never a full model ID. When a task needs the team's current
Copilot picker order or fallback sequence, load the conditional model reference and preserve its
verification state; that host inventory does not select a Claude agent alias.

<!-- profile canary: sp_7c2e — quoted output proves this file loaded; guarded by the tripwire test -->
