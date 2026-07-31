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
On-prem servers + PCF (VMware Tanzu Application Service); `cf` CLI v8 (CAPI V3). **No Kubernetes.**
GCP is under evaluation for late 2026 — not a target today; if it lands it arrives as reference
files inside the obs skills, not as a restructure.

## Observability — two stacks, coexisting (churn is an axiom, not an event)
| Signal | Incumbent | Additive, first-class |
|---|---|---|
| Logs | Splunk (SPL) | Loki (LogQL) |
| Metrics | Wavefront / VMware Aria Operations for Applications (WQL) | Mimir / Prometheus (PromQL) |
| Traces | — (new capability) | Tempo (TraceQL) |
| Dashboards | Grafana 13.x | Grafana 13.x |
| Alerting / correlation | Moogsoft (Dell APEX AIOps, on-prem v9.x); ThousandEyes synthetics | Grafana unified alerting |
| Pipeline | — | Alloy + OTel collectors |

## Languages & CI
Python, Bash, PowerShell first (Go/TS where a repo already uses them). GitHub + GitHub Actions.

## Stay in lane
Do not suggest Kubernetes, cloud-managed services, or infra-layer fixes. Stay in the app/ops lane;
hand platform-internal problems to the platform team.

## The platform boundary
We own our apps up to the platform edge; we do not operate the platform. BOSH, Ops Manager, Diego
cells, Gorouter, CredHub/UAA, and foundation upgrades belong to the platform team. When a problem is
platform-side (many apps failing at once, failing cells, Gorouter-wide 5xx), recognize it and
escalate with evidence — timestamps, blast radius, `cf` output showing our app healthy — do not
operate BOSH.

## Copilot models (recorded here per spec Section 3, not in five agent files)
Selection rule: primary = the strongest Claude model in the team's Copilot picker at ship time;
middle fallback = the next approved Claude model; final fallback = the org's default non-Claude model.
Recorded ordered list: Claude Sonnet 5 (copilot) → Claude Opus 4.8 (copilot) → GPT-5.4 (copilot).
[unverified — confirmed for the team license tier in Phase 5; re-record the complete ordered list when it changes]

<!-- profile canary: sp_7c2e — quoted output proves this file loaded; guarded by the tripwire test -->
