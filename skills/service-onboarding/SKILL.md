---
name: service-onboarding
description: >-
  Onboard a service onto the platform and the observability stack — or audit an existing one against
  the standard. Invoke explicitly as Copilot `/service-onboarding` or Claude
  `/sre-agents:service-onboarding`. Triggers: 'onboard this service', 'bring X up to standard',
  'audit this service'. Works the checklist in order; audit mode reports evidence-cited findings and
  the top three fixes.
# Side-effect-shaped: invoke explicitly as `/sre-agents:service-onboarding`; never auto-load.
disable-model-invocation: true
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

> **Audit evidence boundary.** Report sanitized commands and only the minimal redacted output excerpt
> needed to prove each finding; identify every redaction with a typed marker such as
> `[REDACTED:token]`. Prefer an access-controlled source link over copied telemetry, and include only
> the smallest excerpt needed when a link cannot carry the review. Never run or request
> credential-bearing reads such as `cf env`, `cf service-key`, `CF_TRACE`, or credential endpoints.
> If a prohibited read would be required, record it as not run and state why; do not weaken the finding.

Work through every step in order; when one is skipped, say so explicitly and why — silence reads
as "done." This checklist grants no permission of its own — a step being on the list is not
approval to run it. Before any prod-facing step, load its gate from the dependency block below
(`production-change-gate`) and re-enter it.

## Required on-demand skill dependencies
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

**Audit mode** (bringing an existing service up to standard): run the checks below and report like
a code review of the service — severity-ranked, evidence-cited, **no finding without the command
output that proves it**. End with the top three fixes — not a list of thirty.

Checks (run what applies; list what you couldn't run and why): route/auth exposure · app hygiene
(crash counts, instance flapping, memory headroom via `cf app`) · certificate expiry ·
service-backup existence (**a backup that has never been restored is a hope, not a backup**) ·
monitoring gaps (steps 3–7 above, absent) · manifest drift vs running config · capacity headroom ·
platform-deprecation notices.

Output: `[P0]`–`[P3]` findings, each with the evidence (command + output) and the one-line fix.
**P0 = exposed without auth, or stateful and unbacked-up.**
