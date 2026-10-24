# Observability dashboards skill audit

[verified] Target: `skills/obs-dashboards/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. The sole canonical file and four relevant scenarios were read completely. The workspace projection is byte-identical. No audited source changed.

## Conclusion and findings

[verified] **No material defect validated. Specification verdict: coherent; engineering verdict: partial assurance.** The skill owns operational presentation decisions and routes implementation to Grafana. Its design guidance does not establish query correctness, installed access or successful live changes.

## Contract coverage

| Contract | Evidence and assessment |
|---|---|
| Routing and scope | [verified] [SKILL.md](https://github.com/latent-sre/save-toolkit/blob/8b4f9b785e520944319e04fd8e5018d4545b6800/skills/obs-dashboards/SKILL.md), lines 3–21, distinguishes operational dashboards from application UI, alert intent and Grafana procedures. It preserves the rest of an existing dashboard when only a panel/design change is requested. Grafana handles model/version/write details, avoiding a competing implementation procedure here. |
| Reader and signal contract | [verified] Lines 23–33 starts with the reader's question, names the backend through stack-profile, and delegates query semantics to the appropriate signal skill. Request health and scheduled-work freshness have different examples rather than one generic panel prescription. |
| Missing-data interpretation | [verified] Lines 35–41 distinguishes no traffic, zero, missing telemetry and query failure. It pairs ratios with denominator context and prohibits hiding a missing numerator with zero filling. The scrape-presence expression is scoped to Prometheus-scraped targets and explicitly unconfirmed against local Mimir labels; OTLP requires a separately established presence signal. A positive presence count does not prove every target is healthy, and this report does not treat it as such. |
| Evidence and handoff | [verified] Lines 43–48 requires naming which normal/degraded/missing states were inspected. A screenshot or design is not evidence of current health, a valid query, access or a successful save. The return carries audience, panel/query requirements, units, windows and missing-data limits; no live authority is granted. |
| Callers and packaging | [verified] Observability-engineer loads this skill for questions/panels/layout; principal-engineer uses it for design requirements, and the SRE lane can use it for interpretation. The one-file bundle has no missing owned resources or generated semantic transformation. Existing Grafana findings remain in the [Grafana report](grafana.md), not duplicated as dashboard-design defects. |

## Verification coverage and limits

[verified] The [positive design scenario](../../../../evals/scenarios/discovery-obs-dashboard-design.yaml) requests layout only, while the [negative application-UI case](../../../../evals/scenarios/discovery-obs-dashboards-defers-app-ui-dashboard.yaml) selects frontend-craft instead. These measure routing, not panel usefulness. Despite their filenames, `discovery-obs-dashboards-edit-live.yaml` targets Grafana, and `obs-dashboards-records-unknown-write.yaml` explicitly loads Grafana: they do not establish this skill's design quality. The latter checks supplied UNKNOWN/reconciliation choices, not live concurrency behavior.

[sourced] [ROUTE-007](../../../fleet-roadmap.md), lines 286–299, retains the current routing campaign as outstanding; the presence of authored positive/negative cases does not mean that campaign passed. The existing unchanged-source baseline reports 4,233 tests and 4,952 subtests passing with 84 skips. [verified] No duplicate suite, live query, renderer, dashboard write or model evaluation ran for this item. Projection equality and report links were checked. [unverified] Current model selection, real-reader usability and target-specific query/presence behavior remain unestablished.

## Inspection manifest

[verified] Full reads: canonical `skills/obs-dashboards/SKILL.md`; `evals/scenarios/discovery-obs-dashboard-design.yaml`, `discovery-obs-dashboards-defers-app-ui-dashboard.yaml`, `discovery-obs-dashboards-edit-live.yaml`, `obs-dashboards-records-unknown-write.yaml`. Projection checked by byte comparison. Bounded read: roadmap 283–301. Search-only caller entries in `agents/{sre-assistant,principal-engineer,observability-engineer}.md`, scenario/test inventory. Reused prior complete agent and Grafana audits. No source repairs were made.
