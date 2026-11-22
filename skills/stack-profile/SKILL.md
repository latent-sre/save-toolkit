---
name: stack-profile
description: >-
  What this team runs today: the current stack, which stacks it authors versus only supports, the
  stay-in-lane rule, and the platform boundary. Load before editing code in a support-only stack
  (Java/JVM), before recommending any runtime, tool, or infrastructure change, and when choosing
  between observability backends. Triggers: "what's our stack", "should we use X for this", "can we
  move this to Kubernetes / the cloud", "which backend do I query".
argument-hint: "[the runtime, tool, or infrastructure question]"
---

# Stack profile — current facts, not aspirations

Estate facts as operated today; never promote planned candidates until a human owner records the
decision here. Business context: stock trading firm (orders, accounts, markets, exchanges — never
retail examples); most incidents trace to dependencies (order management, trading apps, quote plant).

## Runtime and platform boundaries

- **Production today:** On-prem servers + **PCF** (Tanzu Application Service / Elastic Application
  Runtime). **Apps Manager** is primary (many SREs lack `cf` CLI; skills lead with UI views and give
  `cf` v8 / CAPI V3 fallback; without a protected path, `sre-assistant` runs no raw `cf` commands).
- **Cloud migration (decision-pending):** GCP is approved; **Cloud Run** is the primary candidate for
  TAS-shaped apps and **GKE only if workload demands it** — never present either as decided or
  propose GKE. **No self-managed Kubernetes** anywhere (on-prem stays Kubernetes-free).
- **Ownership boundaries:**
  - *PCF:* Team owns apps to the edge; platform team owns BOSH, Ops Manager / Foundation Core, Diego
    cells, Gorouter, CredHub/UAA, and upgrades (`pcf-ops`).
  - *GCP (split unratified):* Team owns service config, revisions, and project observability (Cloud
    Run, Cloud Logging/Monitoring/Trace, Secret Manager); cloud platform owner holds org policy,
    folders/projects, shared networking, and cross-project IAM (`gcp-ops`).
  - *Akamai:* Property Manager & WAF config are team-owned change-managed (`akamai-edge`); edge network is Akamai's.

## Observability stack (incumbent and additive coexist)

Both tiers are first-class; neither is retired. Incident order: **Apps Manager** -> **Grafana** ->
**Splunk** -> **PCF App Metrics** (GCP Cloud Logging/Monitoring/Trace join additively as workloads
land; on PCF, incumbent tools lead unless additive instrumentation exists).

| Signal | Incumbent | Additive, first-class |
|---|---|---|
| Logs | Splunk (SPL) | Loki (LogQL) |
| Metrics | PCF App Metrics | Mimir / Prometheus (PromQL) |
| Traces | — (new capability) | Tempo (TraceQL) |
| Dashboards | Grafana 13.3.x (self-managed) | same instance |
| Alerting / synthetics | Moogsoft Onprem v9.x (Dell; 9.2 supported line), ThousandEyes | Grafana unified alerting |
| Pipeline | — | Alloy + OTel collectors |
| Edge / CDN / WAF / RUM | Akamai (Property Manager, App & API Protector, DataStream 2 [dest. unconfirmed], mPulse) | — |

- Grafana recovery copies in team repos prove neither Git Sync, provisioning ownership, backup
  freshness, nor restore readiness, and authorize no live write.
- Owner chose Grafana `gcx` for `sre-assistant` read-only migration (protected execution, admission,
  and redirect checks remain pending); bundled `grafana_read.py` stays the admitted path (no
  terminal grant, live write, vendor skill bundle, or Grafana MCP server).

## Application, CI, and data stack

- **Languages:** **Java/JVM, Python, JS/TS, Go** (Bash/PowerShell for glue). **Java/JVM is
  support-only** (operate/troubleshoot Java/Spring Boot; never write, build, test, or run Java
  locally — return source changes to the app owner).
- **CI & auth:** **GitHub + GitHub Actions on GitHub Enterprise Cloud (`github.com`)**, not
  Enterprise Server/`ghe.com` (Bamboo is legacy); verify repo environment reviewers per target.
  **CI uses GitHub environment secrets, never GitHub OIDC** (never propose GitHub-OIDC->CredHub;
  CredHub uses UAA and CF mTLS instance identity).
- **Runners:** Self-hosted on-prem **RHEL 9+**; GitHub-hosted **`runs-on: ubuntu-latest`** (**Bash 5.1** floor).
- **Frameworks & stores:** **FastAPI** default backend (`api-craft` HTTP; `operator-cli` CLI); React
  focus, Vue in use (`frontend-craft`). Operated DBs: **PostgreSQL and SQL Server on-prem** (MySQL
  minor; **no MariaDB/Oracle**; SQLite/PCF disk is ephemeral/non-shared; managed cloud DBs are future
  candidates, not current estate).

| Language | Format & lint | Types & static checks | Tests | Runtime / packaging |
|---|---|---|---|---|
| Python | `ruff` (lint + format, `B` rules) | `mypy`/`pyright`; `dataclasses`/`pydantic` | `pytest` (`parametrize`, fixtures, `tmp_path`, `monkeypatch`, injected clock) | `uv` (`poetry` libs); no system `pip install` |
| TS / JS | Existing linter / `frontend-craft` React/Vue kit | `strict`, no `any`, narrow `unknown`, branded IDs, exhaustive unions | Vitest/Jest + Testing Library + MSW + Playwright | Repo package manager, lockfile, `tsconfig` |
| Go (`go-craft`) | `gofmt` / `goimports` | `go vet`, `golangci-lint` (`staticcheck`, `govet`, `errcheck`, `ineffassign`, `unused`) | Table-driven `t.Run`; `go test -race` | `go.mod` directive; SIV (`/v2`) |
| Bash | `shellcheck` | `#!/usr/bin/env bash`, `set -Eeuo pipefail`, `shopt -s inherit_errexit` | `bats` | Bash 5.1 floor |
| PowerShell | PSScriptAnalyzer (`Error` on approved verbs, `ShouldProcess`, no aliases/`Invoke-Expression`/plaintext secrets) | `[CmdletBinding()]`, `SupportsShouldProcess`, objects on stdout | Pester 6 (`BeforeAll`/`BeforeEach`) | Explicitly target PS 5.1 vs 7+ |

## Operations, docs, roles, and Copilot models

- **Ops & docs:** Formal on-call; existing bridge/TLC run by ITO; severity setter unrecorded. Changes
  live in **both BMC Remedy and Jira** (name governing system per target). **Team GitHub repo is the
  living doc source** (`scribe`); Confluence is one-way import-only (`operational-docs`).
- **Copilot model policy:** `primary` = strongest Claude model in team Copilot picker; `middle fallback`
  = next approved Claude model; `final fallback` = org default non-Claude model. **Ordered model
  names are unconfirmed** without dated team-picker & license evidence (never use vendor examples or
  convert display names to native Claude aliases).

| Term / role | Team meaning and boundary |
|---|---|
| Blast radius | Affected users/services/envs; small scope never lowers a change tier |
| Golden signals | Latency, traffic, errors, saturation (RED = reqs; USE = resources) |
| Human release owner | Assigned prod executor/rollback owner (default holder unrecorded) |
| Platform team | Owns PCF foundation internals; fleet escalates rather than operating |
| Security incident owner | Owns suspected compromise escalation; preserve state instead of restarting |
| ITO / TLC (Techline Chat) | ITO runs bridge/TLC, pages teams, approves incident changes; no standing IC |
