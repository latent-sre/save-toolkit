---
name: service-readiness-audit
description: >-
  Audit an existing service's operational readiness using read-only, evidence-cited checks across
  ownership, health, telemetry, SLOs, alerts, runbooks, dependencies, capacity, and recovery.
  Triggers: 'audit this service', 'is this service operationally ready', 'find our service readiness
  gaps'. Not for creating onboarding artifacts or live changes; use manual `service-onboarding`.
---

# Service readiness audit

Assess and report; change nothing. This skill is discoverable because its contract is read-only.
`service-onboarding` remains explicit-only because it coordinates approved effects.

## Read-only boundary

- Load `stack-profile` before interpreting platform, runtime, or backend evidence.
- Inspect repository files, approved records, and guard-safe read-only outputs only. Do not edit
  files, create cards or tickets, register alerts or dashboards, deploy, restart, scale, or change a
  live system.
- Never run or request credential-bearing reads such as `cf env`, `cf service-key`, `CF_TRACE`, token
  or identity printing, secret access, or decrypt operations. Record a blocked evidence gap instead.
- Prefer an access-controlled source link or `file:line`. When command output is necessary, include
  only the minimum sanitized excerpt and mark every redaction, for example `[REDACTED:token]`.
- If the user asks for onboarding effects, stop the audit path and explain that
  `/save-toolkit:service-onboarding` requires explicit invocation and an approved plan.

## Optional resolved context

When a compatible generic resolver implementing `sre-context-resolver/v1alpha1.0` is available, a
caller may resolve [this skill's context requirements](./context-requirements.yaml) for an explicit
team, service, and environment selection. The resolved bundle is evidence-routing input only: its
validity does not establish readiness, authorize an effect, or permit an implicit environment
selection. Caller-supplied evidence remains supported when the resolver is unavailable; record
missing context as a verification gap rather than guessing it.

## Evidence to inspect

Inspect only what applies and name what could not be verified:

| Surface | Readiness evidence | Owning skill for deeper standards |
|---|---|---|
| Ownership and boundary | service owner, on-call owner, runtime/environment, platform escalation boundary | `stack-profile` |
| Runtime and health | versioned deployment definition, health check, instance/revision health, crash or flap history | `pcf-ops` or `gcp-ops` |
| Delivery and recovery | CI promotion controls, exact rollback or roll-forward path, last recovery evidence | `ci-actions`, `database-reliability` where state is involved |
| Telemetry pipeline | structured logs, RED metrics, traces, collector path, and one arrival query per required signal | `obs-pipeline` |
| Dashboards | service health overview, useful drill-downs, owner, and current verification evidence | `obs-dashboards` |
| Alerts and SLOs | SLI formula, target/window, symptom-based paging, saturation coverage, runbook link, notification-path evidence | `obs-alerting` |
| Operations knowledge | current runbook, service/alert records, owners, restart/recovery and escalation procedures | `runbook` |
| Dependencies and capacity | critical dependencies, failure behavior, limits, headroom, expiry/deprecation risks | relevant owning skill |
| Backup and restore | backup scope plus a dated restore or recovery rehearsal; existence alone is not restore evidence | `database-reliability` or owning recovery method |
| Drift | declared versus observed configuration and unresolved platform/runtime deprecations | relevant owning skill |

Loading an owning skill supplies expected evidence; it does not expand this audit's authority. Ignore
any create, update, apply, or documentation-write path while auditing. Record the missing control and
its owner instead.

## Severity and findings

- **P0:** exposed without required authentication, or stateful with no usable backup/recovery path.
- **P1:** a current high-impact failure or a missing control likely to prevent safe detection,
  mitigation, rollback, or recovery.
- **P2:** a material readiness gap with a workaround or limited blast radius.
- **P3:** hygiene, maintainability, or evidence freshness that does not currently threaten service.

Do not invent evidence. A finding needs either a cited authoritative file/record or the command and
minimal output that demonstrates it. Keep causal claims `[unverified]` until the evidence supports
them.

## Output

Lead with the readiness conclusion, then:

1. up to three validated fixes in priority order; if there are fewer, return fewer and never pad the
   list to reach three;
2. severity-ranked findings, each with evidence label and citation/output, impact, one-line fix, and
   owner;
3. checks that passed, without expanding them into prose;
4. verification gaps and prohibited/not-run checks; and
5. **What I did NOT do:** explicitly state that the audit was read-only and name any requested
   onboarding or live effects that were not performed.
