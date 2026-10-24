# Agent and skill audit

[verified] Review target: `8b4f9b785e520944319e04fd8e5018d4545b6800`, the candidate in [PR #419](https://github.com/latent-sre/save-toolkit/pull/419). The human requested a complete, careful audit with each item documented before moving to the next. This branch changes review documents, not the audited prompts or helpers.

## Scope and method

[verified] The shipped fleet contains 10 canonical agents and 30 canonical skills. The skill bundles contain 167 files, including references, templates, scripts and test assets. Generated Claude and Copilot surfaces are checked against their canonical source. Two additional reports distinguish the sandbox workflow-graph candidate and retired Fleet Atlas guidance from shipped capabilities.

Each item is read in full together with its bundled files and relevant callers, platform projections, authority rules and tests. The report separates specification consistency, engineering quality and actual behavioral evidence. A defect needs a concrete trigger, observable consequence and source evidence; documented limitations and accepted team decisions are not automatically findings. The next item starts only after the preceding report is saved and checked.

[unverified] Offline checks and prompt inspection do not establish live model routing, instruction-following, installed-host enforcement or production behavior. Paid live evals and production actions are outside this audit. Material vendor facts needing current verification are recorded as source questions rather than silently assumed.

## Baseline evidence

[verified] The unchanged candidate source passed the coordinated default-plus-heavy suite: 4,233 tests and 4,952 subtests passed, with 84 skips. Gate A, configured Ruff lint/format, mypy (35 files), and validation of 373 scenario specifications/2,136 expectations passed. This evidence establishes the exercised mechanical contracts; each report names where semantic or host evidence is still absent.

[unverified] Skips include optional UI calibration, Windows/PowerShell, external service-context producer acceptance and opt-in Docker checks. The separate Codex Security deep scan could not start because the session lacked its required managed filesystem permission profile. This audit does not substitute a completed deep security scan.

## Progress

Resumed on 2026-10-24 at the requester's instruction, with explicitly selected Sol review assistance. **33 of 42 items documented; 9 remain**. All ten canonical agents and 23 canonical skill bundles are complete; these bundles contain 137 fully inspected canonical files.

The next item is `python-craft`. Each item is documented and checked before proceeding. Repairs remain deferred until the audit is complete. Checkpoints `dabc3d3b`, `143cca77`, and `719f8af9` preserve the earlier 19-, 24-, and 27-report states. The earlier five repairs remain separately published in PR #419.

### Canonical agents

| Item | Report and disposition |
|---|---|
| `agent-engineer` | [Complete](agents/agent-engineer.md); no material defect validated; behavioral/host evidence partial |
| `observability-engineer` | [Complete](agents/observability-engineer.md); shared P2 AUDIT-GRAFANA-001 and P3 AUDIT-PIPELINE-002; runtime evidence partial |
| `principal-engineer` | [Complete](agents/principal-engineer.md); no new material defect validated; acceptance remains deferred |
| `reliability-engineer` | [Complete](agents/reliability-engineer.md); shared P3 AUDIT-EVAL-DOC-001; behavior assurance partial |
| `repository-investigator` | [Complete](agents/repository-investigator.md); no material defect validated; current-host assurance partial |
| `researcher` | [Complete](agents/researcher.md); P2 AUDIT-RESEARCH-001; native provider registration unverified |
| `reviewer` | [Complete](agents/reviewer.md); no material defect validated; host/review-quality assurance partial |
| `scribe` | [Complete](agents/scribe.md); no material defect validated; document/host assurance partial |
| `software-engineer` | [Complete](agents/software-engineer.md); no additional source defect; PRECOMMIT-001 behavior gap remains open |
| `sre-assistant` | [Complete](agents/sre-assistant.md); no additional source defect; protected-access and incident-quality gaps remain |

### Canonical skills

| Item | Report and disposition |
|---|---|
| `agent-authoring` | [Complete](skills/agent-authoring.md); P3 AUDIT-AUTHORING-001 in workspace teaching examples |
| `akamai-edge` | [Complete](skills/akamai-edge.md); no material finding; vendor facts checked, routing/account assurance partial |
| `api-craft` | [Complete](skills/api-craft.md); shared P3 AUDIT-API-001 in Go timeout oracle |
| `ci-actions` | [Complete](skills/ci-actions.md); shared P3 AUDIT-CI-001 in deployment-target oracle |
| `database-reliability` | [Complete](skills/database-reliability.md); no material finding; version claims sourced, runtime assurance partial |
| `eng-ladder` | [Complete](skills/eng-ladder.md); no material finding; consult/design-quality assurance partial |
| `frontend-craft` | [Complete](skills/frontend-craft.md); P3 AUDIT-FRONTEND-001/002/003 in bundled helpers/checks |
| `gcp-ops` | [Complete](skills/gcp-ops.md); P2 AUDIT-GCP-001 in Pub/Sub causal inference |
| `go-craft` | [Complete](skills/go-craft.md); no new finding; shared AUDIT-API-001 and known BACKEND-002 limits |
| `grafana` | [Complete](skills/grafana.md); shared P2 AUDIT-GRAFANA-001, new P3 002/003/004/005 |
| `incident-investigation` | [Complete](skills/incident-investigation.md); no new finding; existing behavioral acceptance gaps remain |
| `obs-alerting` | [Complete](skills/obs-alerting.md); no new finding; arithmetic and vendor checks bounded |
| `obs-dashboards` | [Complete](skills/obs-dashboards.md); no new finding; design and live-operation evidence kept distinct |
| `obs-logs` | [Complete](skills/obs-logs.md); P3 AUDIT-LOGS-001 in overall-rate query fallback |
| `obs-metrics` | [Complete](skills/obs-metrics.md); P3 AUDIT-METRICS-001 in assumed Grafana authentication path |
| `obs-pipeline` | [Complete](skills/obs-pipeline.md); P3 AUDIT-PIPELINE-001/002 in eval criterion and Alloy validation guidance |
| `obs-traces` | [Complete](skills/obs-traces.md); P3 AUDIT-TRACES-001 in eval attribute maturity |
| `operational-learning` | [Complete](skills/operational-learning.md); no new finding; evidence and disposition contracts reconciled |
| `operator-cli` | [Complete](skills/operator-cli.md); no new finding; bounded fault-injection oracle assessed |
| `pcf-deploy` | [Complete](skills/pcf-deploy.md); shared AUDIT-PCF-001; other version claims qualified |
| `pcf-ops` | [Complete](skills/pcf-ops.md); P3 AUDIT-PCF-001 in version-bound resize recipe; target runtime unverified |
| `postmortem` | [Complete](skills/postmortem.md); no new finding; artifact checks distinguished from narrative quality |
| `production-change-gate` | [Complete](skills/production-change-gate.md); P3 AUDIT-GATE-001 in approval-expiry calibration |
| `python-craft` | Pending |
| `resilience-analysis` | Pending |
| `root-cause` | Pending |
| `runbook` | Pending |
| `service-lifecycle` | Pending |
| `stack-profile` | Pending |
| `toil-reduction` | Pending |

### Nonshipping skill surfaces

| Item | Report and disposition |
|---|---|
| `sandbox/workflow-graph-engineering` | Pending; candidate remains unpromoted |
| `archive/fleet-atlas` | Pending; retired guidance remains historical |

## Findings and disposition

| Finding | Severity | Evidence |
|---|---|---|
| AUDIT-GRAFANA-001 — dashboard/folder rollback guidance can erase intervening edits | P2 | [Observability engineer](agents/observability-engineer.md); [Grafana bundle](skills/grafana.md) |
| AUDIT-EVAL-DOC-001 — evaluation guide retains a superseded reliability deferral | P3 | [Reliability engineer](agents/reliability-engineer.md) |
| AUDIT-RESEARCH-001 — exact GitHits grant retains replaced grep method name | P2 | [Researcher](agents/researcher.md); [provider registry evidence](evidence/githits-tool-catalog.json) |
| AUDIT-AUTHORING-001 — workspace projection strips namespaces from Claude teaching examples | P3 | [Agent authoring](skills/agent-authoring.md) |
| AUDIT-API-001 — Go timeout oracle accepts lexical presence without effective timeout | P3 | [API craft](skills/api-craft.md) |
| AUDIT-CI-001 — deployment-target oracle accepts commented commands | P3 | [CI actions](skills/ci-actions.md) |
| AUDIT-FRONTEND-001 — sentinel collision admits a protocol-relative config URL | P3 | [Frontend craft](skills/frontend-craft.md) |
| AUDIT-FRONTEND-002 — serving predicate overclaims cache freshness | P3 | [Frontend craft](skills/frontend-craft.md) |
| AUDIT-FRONTEND-003 — nonfinite retry counts disable the attempt bound | P3 | [Frontend craft](skills/frontend-craft.md) |
| AUDIT-GCP-001 — oldest-message age slope overstates acknowledgment/causal evidence | P2 | [GCP operations](skills/gcp-ops.md) |
| AUDIT-GRAFANA-002 — review instructions skip available guarded hygiene analysis | P3 | [Grafana](skills/grafana.md) |
| AUDIT-GRAFANA-003 — truncation recovery reintroduces masked authentication values | P3 | [Grafana](skills/grafana.md); [reproductions](evidence/grafana-transport-reproductions.md) |
| AUDIT-GRAFANA-004 — symlinked output parent fails after successful package creation | P3 | [Grafana](skills/grafana.md); [reproductions](evidence/grafana-transport-reproductions.md) |
| AUDIT-GRAFANA-005 — broken overwrite regex accepts unsafe conflict advice | P3 | [Grafana](skills/grafana.md) |
| AUDIT-LOGS-001 — overall deploy-rate fallback loops back to a class-grouped query | P3 | [Logs](skills/obs-logs.md) |
| AUDIT-METRICS-001 — GCP query guidance assumes an unestablished Grafana syncer | P3 | [Metrics](skills/obs-metrics.md) |
| AUDIT-PIPELINE-001 — naming eval retains a blanket no-plurals criterion | P3 | [Pipeline](skills/obs-pipeline.md) |
| AUDIT-PIPELINE-002 — Alloy validation guidance misstates remote-import behavior | P3 | [Pipeline](skills/obs-pipeline.md); [observability engineer](agents/observability-engineer.md) |
| AUDIT-TRACES-001 — semantics eval calls a Development attribute stable | P3 | [Traces](skills/obs-traces.md) |
| AUDIT-PCF-001 — resize payload is rejected by the controller at its advertised minimum | P3 | [PCF operations](skills/pcf-ops.md); [deployment](skills/pcf-deploy.md) |
| AUDIT-GATE-001 — approval calibration omits required validity evidence | P3 | [Production gate](skills/production-change-gate.md) |

Findings are recorded in the individual reports and deduplicated here as the audit proceeds. The [fleet roadmap](../../fleet-roadmap.md) remains the sole live backlog; this evidence packet does not authorize fixes or promotion.
