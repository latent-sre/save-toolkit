---
name: service-onboarding
description: >-
  Onboard an approved new or changed service into the platform, observability, and operational-
  knowledge model. Invoke explicitly as Copilot `/service-onboarding` or Claude
  `/save-toolkit:service-onboarding`. Triggers: 'onboard this service', 'register this application',
  'complete service onboarding'. Not for read-only readiness reviews; use `service-readiness-audit`.
# Side-effect-shaped: invoke explicitly as `/save-toolkit:service-onboarding`; never auto-load.
disable-model-invocation: true
---

This is the explicit, effect-shaped onboarding workflow. For a read-only assessment of whether an
existing service is ready, use `service-readiness-audit`; do not simulate onboarding to answer an
audit question.

Use only sanitized evidence and the smallest redacted excerpt needed for each decision. Never run or
request credential-bearing reads such as `cf env`, `cf service-key`, `CF_TRACE`, or credential
endpoints. If a prohibited read would be required, record it as not run and state why.

Require the approved plan, named service and environment, owner, exact repository revision, and
authoritative service/alert definitions before starting. Work through every applicable step in
order; when one is skipped, say so explicitly and why—silence reads as “done.” This checklist grants
no permission of its own. Before any production-facing step, load `production-change-gate` and
re-enter it.

## Required on-demand skill dependencies
- `stack-profile`
- `production-change-gate`
- `obs-pipeline`
- `obs-dashboards`
- `obs-alerting`
- `ci-actions`
- `runbook`

Before each dependent checklist step, load that row's skill; the names below are executable load requirements, not decorative cross-references.

1. **Manifest & health** — version-controlled `manifest.yml`; http health-check endpoint; ≥2 instances.
2. **Instrument** — OTel SDK wired (metrics + traces + structured logs); RED metrics named per
   convention; cardinality reviewed. [load `obs-pipeline` before this step]
3. **Ship telemetry** — Alloy/collector config routes logs → Loki (and Splunk where required),
   metrics → Mimir, traces → Tempo. Prove arrival with one query per signal, quoted.
4. **Dashboard** — the service page in Grafana: top-level health → drill-down (load `obs-dashboards`).
5. **Alerts** — burn-rate alert on the SLI + one saturation alert; each linked to a runbook
   (load `obs-alerting`). No runbook, no alert.
6. **SLO** — SLI formula + target + window recorded where the team keeps them.
7. **CI/CD** — build + deploy via Actions (`ci-actions`); promotion gates on.
8. **Runbook** — check/restart/recover doc exists (`runbook`); on-call knows where it is.
9. **Knowledge closeout** — after the service and alerts are approved, emit an **evidence-bound
   handoff** to `scribe` for the service card, alert cards, operations index, and any missing/stale
   runbook. Include exact repository revision, authoritative definitions, owners, links, retained
   evidence labels/trust, the trusted approval record, and one recommended course of action. This
   checklist does not author those KB records or treat an active deployment/incident as resolved
   documentation evidence.

Return the completed/skipped steps, approval and production-gate evidence, verification results,
remaining gaps with owners, the `scribe` handoff packet, and **what was not done**. Never report an
onboarding effect as complete without evidence from its authoritative system.
