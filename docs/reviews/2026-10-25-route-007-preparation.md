# ROUTE-007 offline preparation

[verified] Six missing discovery scenarios are prepared against main `b4bb96a7` on
`work/eval-multimodel-followthrough`. No agent, skill, adapter, or authority changes were made.
The seventh requested scenario, automatic positive discovery of `pcf-deploy`, conflicts with
its current manual-only contract. This preparation does not close ROUTE-007 or establish model
behavior. The human owner remains the acceptor of the exact measured candidate.

## Added cases

All six have a four-turn bound, ordinary trading-service tasks, and unhinted prompts.

| Case ID | Target | Expected result / alternative |
|---|---|---|
| `discovery-database-reliability-blocking-query` | database-reliability | fire |
| `discovery-database-reliability-defers-app-crash` | database-reliability | not-fire / pcf-ops |
| `discovery-pcf-ops-app-crash` | pcf-ops | fire |
| `discovery-pcf-ops-defers-foundation-repair` | pcf-ops | not-fire / main session |
| `discovery-akamai-edge-defers-backend-log-query` | akamai-edge | not-fire / obs-analysis |
| `discovery-obs-alerting-defers-signal-query` | obs-alerting | not-fire / obs-analysis |

[verified] The foundation case asks only for a reply about platform ownership and evidence
after application observations have already been supplied. `main_session` permits supporting
skills but requires an answer without agent delegation; the forbidden application-triage
skill must still remain absent. There is no platform-team agent to name as the alternative.

## Bounded current-target selection

[verified] The following 20 distinct IDs cover the existing API cases, one positive and one
negative for each automatically invocable surviving description, the manual deployment
negative, the historical dashboard-design/application-UI pair now targeting `grafana`, and
an explicit pair for the consolidated `obs-analysis` signal skill. Pass each ID separately
to `build_probe.py run --scenario ID`; the runner accepts one ID per invocation. Use one
trial per ID on the frozen candidate, with the caller's approved model and remaining budget.
These are selection inputs, not an authorization for additional calls or retries.
Their declared turn limits sum to 111 for one trial each; this is an offline bound, not
measured usage or a price estimate.

| Current target | Fire case IDs | Not-fire case IDs |
|---|---|---|
| akamai-edge | `discovery-akamai-edge-reference-error` | `discovery-akamai-edge-defers-backend-log-query` |
| api-craft | `discovery-api-craft-http-api`; `discovery-api-craft-http-client` | `discovery-api-craft-defers-scheduled-job` |
| database-reliability | `discovery-database-reliability-blocking-query` | `discovery-database-reliability-defers-app-crash` |
| frontend-craft | `discovery-frontend-craft-weighs-mantine-in-tailwind-app` | `discovery-frontend-craft-defers-observability-dashboard` |
| obs-alerting | `discovery-obs-alerting-splunk-saved-search` | `discovery-obs-alerting-defers-signal-query` |
| obs-pipeline | `discovery-obs-pipeline-alloy-exporter` | `discovery-obs-pipeline-not-reading-signals` |
| pcf-deploy | blocked by manual-only invocation | `discovery-manual-deploy-does-not-autofire` |
| pcf-ops | `discovery-pcf-ops-app-crash` | `discovery-pcf-ops-defers-foundation-repair` |
| grafana | `discovery-obs-dashboard-design` | `discovery-obs-dashboards-defers-app-ui-dashboard` |
| obs-analysis | `discovery-obs-logs-cloud-logging` | `discovery-obs-logs-defers-obs-alerting` |

[verified] Additional existing routing cases remain available but are outside this bounded
selection: `discovery-obs-pipeline-not-grafana-datasource`, `discovery-grafana-dashboard-reading`,
`discovery-grafana-not-logql`, `discovery-grafana-silence`,
`discovery-obs-dashboards-edit-live`, `discovery-obs-logs-correlation-id`,
`discovery-obs-logs-defers-live-page`, `discovery-obs-metrics-cloud-monitoring`, and
`discovery-obs-traces-cloud-trace`.

## Obsolete targets and blocked measurement

[verified] Canonical skill files and scenario targets establish the current map:

- Former `backend-craft` is `api-craft`.
- Former `obs-dashboards` routes to `grafana`; historical dashboard scenario IDs remain unchanged.
- Former `obs-logs`, `obs-metrics`, and `obs-traces` route to `obs-analysis`; historical signal
  scenario IDs remain unchanged. Correlation-ID versus trace-ID selection is method behavior,
  rather than discovery of two separately installed skills.
- `obs-analysis` remains installed. It must not be treated as a retired target or replaced
  with `grafana` for general signal queries. The roadmap's consolidated-signal wording is
  ambiguous; current canonical skills and YAML targets resolve the selection above.

[verified] `skills/pcf-deploy/SKILL.md` sets `disable-model-invocation: true` and requires
explicit human invocation through `/save-toolkit:pcf-deploy`. An unhinted positive routing
case would demand behavior forbidden by that contract. No knowingly impossible YAML was added.

[verified] `evals/probe/catalog.py:scenario_prompt` implements `skill:` pins by prepending a
request to call the Skill tool. It does not implement native human slash-command expansion.
`pcf-deploy-requires-gate` is an existing skill-pinned behavioral contract, not a positive
description-discovery measurement. Its existence does not prove manual invocation works.

[unverified] A valid successor measurement would explicitly submit the human command
`/save-toolkit:pcf-deploy` with a bounded request to draft an unapproved blue-green plan for a
named fictional TAS test app, keeping target gaps visible and executing no changes. First
confirm that the chosen native host expands that human command and records completed skill
invocation with the manual-only frontmatter intact. Then bind the command, candidate digest,
turn/cost limit, trace evidence, and draft-only behavioral assertions in a dedicated
explicit-request contract. Keep it separate from unhinted discovery. This requires a host
invocation capability check; changing the skill to permit automatic loading is not authorized.

## Offline evidence and remaining work

[verified] Using `/home/hawkfire/save-toolkit/.venv/bin/python` (Python 3.14.8):

- `evals/build_probe.py validate` exited 0: 405 specs, including 111 routing specs, and
  2,256 graded expectations.
- `-m pytest -q evals/test_probe_catalog.py evals/test_probe_assessment.py` exited 0:
  63 tests passed and 860 subtests passed. These checks exercise catalog acceptance, unhinted
  routing prompts, current target resolution, and positive/negative routing grading.

[verified] No model calls, credential reads, full suite, or commit occurred in this preparation.
[unverified] Native host acceptance and model routing remain unmeasured. No completion rate or
native routing result follows from these offline checks. The invoking caller owns the approved model run, budget accounting, trace
review, roadmap disposition, and retention link for this report while ROUTE-007 remains open.
