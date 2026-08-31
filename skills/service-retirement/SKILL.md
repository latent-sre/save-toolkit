---
name: service-retirement
description: >-
  Carry an approved service decommission through platform removal, telemetry and alert retirement,
  and durable operational-knowledge closeout. Invoke explicitly as Copilot `/service-retirement`
  or Claude `/save-toolkit:service-retirement`. Triggers: 'retire this service', 'decommission this
  application', 'remove this service from production'. Onboarding and material changes use
  `service-lifecycle`; read-only readiness reviews use `service-readiness-audit`.
# Side-effect-shaped: invoke explicitly; never auto-load.
disable-model-invocation: true
argument-hint: "[the approved service retirement]"
---

# Service retirement

This is the explicit, effect-shaped workflow for an approved service decommission. It coordinates
removal from platform, telemetry, alerting, and active knowledge indexes while preserving the
service's durable tombstone. The checklist grants no authority. A human release owner or separately
approved protected automation executes every live action and returns its receipt; the agent only
prepares, records, and stops on missing or ambiguous evidence.

**Entry guard:** proceed only when the caller explicitly invokes this workflow and supplies the
approved retirement plan. Otherwise stop, state that `service-retirement` is manual-only, and ask
for the missing invocation or approved plan without inventorying or preparing any retirement
action. This body-level guard remains binding on hosts that drop `disable-model-invocation`.

Require the exact service and environment, approved retirement plan and change record, full source
commit ID, authoritative deployment and observability definitions, known consumers and
dependencies, data-retention obligations, rollback or recovery plan, named executor, and approval
expiry before starting. Never request credential-bearing reads or secret values. Missing ownership,
an unknown consumer, an unclassified datastore, or an unproven recovery path is `BLOCKED`, not a
reason to infer that removal is safe.

## Load only the owning methods

- Load `stack-profile` before classifying platform ownership or removal boundaries.
- Before every production-facing step, load `production-change-gate` and re-enter it with the exact
  target, command or diff, applying human/protected automation, approval, verification, and backout.
- Load `obs-pipeline`, `obs-dashboards`, and `obs-alerting` before preparing removal of their
  respective telemetry, dashboards, or alerts.
- Load `runbook` only when preparing a runbook status or retirement update for the later `scribe`
  handoff. This workflow never writes operational knowledge itself.

## Checklist

1. **Bind scope and recovery.** Record the exact service/environment/deployment, source and artifact
   identities, applying actor, approval deadline, blast radius, data classification and retention,
   known callers and dependencies, last known-good configuration, rollback window, and recovery
   proof. A broad "retire the service" approval does not authorize undisclosed deletions.
2. **Inventory every surface.** From caller-supplied authoritative definitions, enumerate platform
   workloads, routes, schedules and bindings; pipelines and deployment credentials; telemetry
   collection, dashboards, SLOs and alerts; runbooks, service/alert cards and indexes; persistent
   data, DNS, certificates, queues, topics, repositories, and dependent services. Mark each
   `remove`, `retain`, `transfer`, `retire-record`, or `BLOCKED` with an owner. Silence is not done.
3. **Prove traffic and dependency exit.** Require evidence that inbound callers have migrated or
   stopped, asynchronous producers and consumers are drained, and no route, schedule, subscription,
   or dependency still expects the service. Unknown or conflicting evidence stops live removal.
4. **Quiesce under the production gate.** The named human or protected automation disables new work
   and traffic using the approved action, then returns a durable result. Preserve the rollback
   window and last known-good artifact/configuration. If dispatch may have occurred without a
   durable result, record `UNKNOWN`; do not retry until the named owner reconciles authoritative
   state.
5. **Remove platform presence.** Only after quiescence verification, prepare the separately gated
   removal of workloads, routes, schedules, bindings, and deployment automation. Data deletion,
   credential revocation, DNS/certificate removal, and access-path changes remain Tier 3; each
   needs its own recovery evidence and human executor.
6. **Retire observability in dependency order.** First retain the evidence needed to verify the
   decommission; then retire paging alerts and SLO evaluation, stop telemetry collection, and remove
   dashboards only as authorized. Preserve records required by retention policy and list every
   shared collector, dashboard, alert, or query deliberately left in place.
7. **Close delivery and ownership edges.** Disable or retire deployment workflows and environment
   bindings, transfer shared repositories or resources, and route access removal to the authorized
   identity owner. Never inspect, print, or copy credentials as evidence.
8. **Prepare durable knowledge closeout.** Emit an evidence-bound handoff to `scribe` that removes
   the service from active indexes but leaves its service card, alert cards, and runbooks `retired`
   rather than deleted. Include the authorizing record, exact repository revision and verified
   checkout binding, execution receipts, retained evidence labels, dependent artifacts still
   referencing the service, what was not removed, and one recommended course of action. The handoff
   asks `scribe` to select knowledge-closeout mode; this originating workflow never loads or approves
   `operational-learning` on its own discovery.
9. **Verify the terminal state independently.** Require separately supplied authoritative evidence
   that the service no longer serves traffic or scheduled work, retired alerts no longer page, the
   intended telemetry path is absent, retained shared resources still work, and durable records are
   visible as retired. A checklist author's assertion is not independent verification.

## Return contract

Return the bound target and approval, one row per inventoried surface with its disposition and
owner, every execution result or `UNKNOWN`, rollback-window status, verification evidence,
unresolved dependencies, the exact `scribe` handoff, and what was not removed. Never report the
retirement complete while any required surface is `BLOCKED`, `UNKNOWN`, or merely planned.
