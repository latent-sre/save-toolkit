---
name: service-lifecycle
description: >-
  Take a service through its operational life on this stack: audit an existing service's readiness
  read-only, onboard a new or materially changed service, and retire one, each as a checklist a
  human executes under production-change-gate. Triggers: 'audit this service', 'onboard this
  service', 'retire this service', 'decommission this application'. Onboard and retire need an
  approved plan named in the request; without one the skill audits and lists what the plan must
  contain.
argument-hint: "[audit|onboard|retire] <service> [environment]"
---

# Service lifecycle

One service, three moments: audit what exists, onboard what is new or materially changed, retire
what is done. Every mode reads evidence and produces a checklist with owners; a human release owner
or separately approved protected automation executes every live step under
`production-change-gate` and returns its receipt. This skill changes nothing live, never writes
operational knowledge itself, and never requests a credential-bearing read; a prohibited read is
recorded as a gap.

## Pick the mode

| Mode | Runs when | Otherwise |
|---|---|---|
| **Audit** (default) | Any readiness question about an existing service | — |
| **Onboard** | The request names an approved plan, the exact service and environment, the owner, the source commit, and the authoritative service and alert definitions | Stop, name what is missing, and audit what exists instead; prepare no artifact |
| **Retire** | The request names an approved retirement plan and change record, the exact service and environment, the source commit, known consumers and dependencies, data-retention obligations, a recovery plan, the executor, and the approval expiry | Stop and name what is missing; inventory nothing. Missing ownership, an unknown consumer, an unclassified datastore, or an unproven recovery path is `BLOCKED` |

Load `stack-profile` before interpreting platform, runtime, or backend evidence. Load an owning
skill from the table below only for the surface you are on; loading it supplies expected evidence
and never expands this skill's authority. Before any production-facing step in onboard or retire,
load `production-change-gate` and re-enter it with the exact target, command or diff, applying
actor, approval, verification, and backout.

## The surfaces

Work the rows that apply. Audit inspects; onboard produces; retire dispositions each surface as
`remove`, `retain`, `transfer`, `retire-record`, or `BLOCKED`, with an owner. Silence is not done.

| Surface | Audit inspects | Onboard produces | Retire | Owning skill |
|---|---|---|---|---|
| Ownership and boundary | service owner, on-call, runtime and environment, platform escalation boundary | the same, recorded | ownership of retained shared resources transferred | `stack-profile` |
| Runtime and health | versioned deployment definition, health check, instance or revision health, crash history | `manifest.yml` or pinned Cloud Run config; a workload-appropriate health check; justified instance target, scale-to-zero preserved unless the SLO needs minimums | workloads, routes, schedules, bindings removed only after quiescence is verified | `pcf-ops` or `gcp-ops` |
| Delivery and recovery | CI promotion controls, exact rollback or roll-forward path, last recovery evidence | build and deploy via Actions with promotion gates on | deployment workflows and environment bindings disabled; access removal routed to the identity owner | `ci-actions` |
| Telemetry pipeline | structured logs, RED metrics, traces, collector path, one arrival query per signal | OTel SDK wired, cardinality reviewed, collector routing to the selected destinations, arrival proven with one quoted query per signal | collection stopped after the evidence needed to verify the decommission is retained; shared collectors left in place are listed | `obs-pipeline` |
| Dashboards | service health overview, drill-downs, owner, verification evidence | the service page: health at the top, drill-down below | removed only as authorized; shared dashboards listed | `obs-dashboards` |
| Alerts and SLOs | SLI formula, target and window, symptom-based paging, saturation coverage, runbook link, notification-path evidence | a burn-rate alert on the SLI for request-based services or a freshness, completion, or failure alert for scheduled work, a saturation alert where the signal exists, each linked to a runbook; SLI formula, target, and window recorded where the team keeps them | paging alerts and SLO evaluation retired first, in dependency order | `obs-alerting` |
| Operations knowledge | current runbook, service and alert records, escalation procedure | a check, restart, recover runbook on-call can find | records marked `retired`, never deleted; active indexes updated | `runbook` |
| Dependencies and capacity | critical dependencies, failure behaviour, limits, headroom, expiry risks | recorded on the service card | inbound callers migrated or stopped, producers and consumers drained, nothing still expects the service; unknown or conflicting evidence stops removal | owning skill |
| Data, backup, restore | backup scope plus a dated restore rehearsal; existence alone is not restore evidence | recovery path recorded | data deletion, credential revocation, DNS and certificate removal, and access-path changes stay Tier 3, each with its own recovery evidence and human executor | `database-reliability` |

Retire works the rows in a fixed order with stop rules, from traffic exit through independent
verification; read [retirement order](./references/retirement-order.md) once the entry guard has
passed and before dispositioning any surface.

## Audit findings

- **P0** exposed without required authentication, or stateful with no usable backup or recovery path.
- **P1** a current high-impact failure, or a missing control likely to prevent safe detection, mitigation, rollback, or recovery.
- **P2** a material gap with a workaround or limited blast radius.
- **P3** hygiene, maintainability, or evidence freshness.

A finding needs a cited file, record, or the minimal sanitized command output that shows it; causal
claims stay `[unverified]` until the evidence supports them. A control that exists but is absent
from the service's record is a documentation gap; one absent from both is a readiness gap. Report
them separately, and report onboarding as unverified when no record exists at all.

## Knowledge closeout

Onboard and retire both end with an evidence-bound handoff to `scribe` for the service card, alert
cards, index entry, and any missing or stale runbook: the authorizing record, exact repository
revision and checkout binding, execution receipts, retained evidence labels, what was not done, and
one recommended course of action. Audit findings travel the same route as closeout-eligible
evidence. This skill never loads `operational-learning` or authors a record.

## Return

Lead with the conclusion, dated in UTC, with the age of the oldest load-bearing evidence. Then, by
mode: **audit** returns up to three validated fixes in priority order, severity-ranked findings
with evidence and owner, checks that passed, gaps and prohibited reads not run, and a plain
statement that nothing was changed; **onboard** and **retire** return each surface's row with its
result or `UNKNOWN`, every gate verdict and receipt, unresolved dependencies, the `scribe` handoff,
and what was not done. Never report an effect complete while any surface is `BLOCKED`, `UNKNOWN`,
or merely planned, and close an onboarding by recommending its own audit as owed verification.

## Optional resolved context

When a compatible resolver implementing `sre-context-resolver/v1alpha1.4` is available, a caller
may resolve [this skill's context requirements](./context-requirements.yaml) for an explicit team,
service, and environment. Resolved context is routing input only: it tells you whether the service
is new or a change, never supplies a plan, an approval, or a credential, and missing context is a
gap, not a guess.
