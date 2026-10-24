# Audit findings 11–20 repairs

The requester authorized the next ten findings in ledger order after first-batch commit
`59e7036674aca96391c988ff297cf23f7abdf124`. Original reports describe source at `8b4f9b78`;
this follow-up records the second repair batch. The [fleet roadmap](../../fleet-roadmap.md) remains
the only live backlog. Findings 21–25 are outside this batch.

## Changes and acceptance evidence

| Finding | Repair | Focused evidence and limits |
|---|---|---|
| AUDIT-GRAFANA-002 | Read-only review uses existing guarded hygiene analysis on an eligible named capture; unavailable evidence remains a gap. | Documented command allowed by Bash/PowerShell guard grammars; standalone arbitrary export helper remains denied. Original reference failed both new checks. |
| AUDIT-GRAFANA-003 | Recovery augmentation is followed by final credential masking. Recovery arguments altered by masking are omitted and explicitly marked unusable. | Real workflow entrypoint with fake HTTP and 600 KB dashboard: credential-bearing path and capture ID cannot reappear; safe named recovery remains executable. |
| AUDIT-GRAFANA-004 | Output-parent symlinks/reparse points are rejected before collection or package creation, matching readback policy. | Reproduction rejects linked parent with zero HTTP calls and no package artifacts; original completed collection/package then failed readback. Concurrent filesystem replacement remains outside this preflight guarantee. |
| AUDIT-GRAFANA-005 | Corrected YAML regex quoting for overwrite advice. | Actual scenario graders reject five unsafe overwrite syntaxes while safe refusal/create/scoped-update answers pass. Original pattern falsely accepted five unsafe variants. |
| AUDIT-LOGS-001 | Added an overall deploy error-rate SPL query grouped only by phase, linked directly from the catalog and class-based query. | Fixture checks require no error taxonomy, retain the complete request population, and leave unknown-status/empty windows unclassified. Bounded arithmetic and source shape only; no Splunk execution. |
| AUDIT-METRICS-001 | GCP guidance discovers the actual datasource/authentication/query context; syncer diagnosis applies only to an observed syncer integration. | Structured eval decision rejects unconditional syncer-first advice; actual deterministic grader calibration. No Grafana/GCP live integration claim. |
| AUDIT-PIPELINE-001 | Naming evaluation distinguishes plural discrete unitless Counter countables from singular UpDownCounter names; unit-bearing guidance stays singular. | Positive names and wrong-plurality negatives discriminate both choices. No live model evaluation. |
| AUDIT-PIPELINE-002 | Alloy reference and agent describe default v1.18.1 static validation and the imported-content assurance gap. | Pinned upstream implementation evidence from the audit; guard denial and prior read-full-or-isolated execution alternatives retained. No Alloy process run. |
| AUDIT-TRACES-001 | Semconv v1.44.0 fixture requires each attribute's actual maturity, with messaging.destination.name Development. | Actual graders check every labelled attribute/maturity; each wrong maturity fails. No live trace pipeline exercised. |
| AUDIT-PCF-001 | Withdrew unsupported deployment-options resize payload and version claim; dependent deployment guidance now requires a target-supported existing-droplet procedure. | Two source contracts fail against the original recipe/cross-reference and pass after withdrawal. Whole-app scale effects, current-droplet proof, human execution and full gates for new artifacts retained. |

## Source verification and review

[verified] Cloud Foundry public source was rechecked during this repair. The [capi-release 1.205.0
gitlink](https://api.github.com/repos/cloudfoundry/capi-release/contents/src/cloud_controller_ng?ref=1.205.0)
binds controller `8d3cedf014719550e56bbf4ba1804d054d1df24b`. Its [deployment message](https://github.com/cloudfoundry/cloud_controller_ng/blob/8d3cedf014719550e56bbf4ba1804d054d1df24b/app/messages/deployment_create_message.rb)
allows only `canary`, `max_in_flight`, and `web_instances` in deployment options and rejects other
keys. Retrieved file SHA-256: `fa9779e0d7ab60617a5c0ca75e133ff5ca66de7a65e76ef986fd21f98838086f`.
No request was made to a Cloud Foundry deployment target. Withdrawing the unsupported recipe
fixes the guidance; it does not establish a replacement no-downtime resize procedure.

[sourced] Version-bound Alloy and OTel source evidence is retained in the original
[pipeline](skills/obs-pipeline.md) and [traces](skills/obs-traces.md) reports. No new runtime,
authentication architecture, authority grant, or dependency is introduced.

[verified] Initial focused checks: Grafana workflow 55 passed; adjacent capture/evidence/helper
guard checks 372 passed and one skipped; create/hygiene contracts 19 passed; PCF plus existing
skill-asset checks nine passed with 89 subtests. Source review identified two initially
under-discriminating new telemetry graders; their wrong-maturity and unconditional-syncer advice
cases were reproduced and corrected. Final telemetry tests use actual graders, reject each wrong maturity and unconditional-syncer advice, and pass all four focused cases. The naming calibration also uses the actual grader. Independent Sol follow-up found both grading gaps resolved and no remaining blocker in the reviewed source changes.

## Integration correction

[verified] The first final Gate A run failed: the new overall-rate anchor was reported missing.
The heading exists, but `scripts/check_links.py` treated shorter SPL triple-backtick comments as
closing Markdown four-backtick fences, hiding later headings. A bounded supporting repair tracks
fence character and length, requires an empty closing tail, and excludes invalid backtick-bearing
opening info strings. This restores the new query link without weakening the gate or changing SPL.
Four new regression failures reproduced the problem before repair; focused link/telemetry checks
then passed 54 tests and 20 subtests. Ruff and mypy passed. Independent Sol inspection found no
blocker in the parser delta. The final default suite is rerun because executable code changed.

## Integrated verification

[verified] Final coordinated default suite: **3,569 passed, 82 skipped, 4,222 subtests passed**;
3,651 collected, zero failures, exit 0 in 19.544 seconds. Command:
`/home/hawkfire/save-toolkit/.venv/bin/python scripts/local_tests.py`.
Receipt: `/home/hawkfire/save-toolkit/.git/local-test-runs/20261024T115227Z-1d1f3bc8/run.json`.
The tracked diff hash was identical before and after the run. All 33 changed source/test/generated
files matched the separately captured verification hash snapshot afterward. The final new tests
were staged before this run, so the tracked diff includes their contents. Subsequent changes are
verification documentation only.

[verified] The initial default run passed 3,567 tests before the gate exposed the parser defect;
its receipt remains `/home/hawkfire/save-toolkit/.git/local-test-runs/20261024T114825Z-7dbf0a92/run.json`.
The final run above supersedes that evidence after the supporting executable fix.

[verified] The default suite is the required scope for these helper/test changes; no evaluator,
oracle, grader implementation, runner or shared harness changed. The scenario changes and their
focused actual-grader tests are included. The 82 skips cover 39 opt-in UI cases, 27 Windows cases,
11 external producer cases, three Docker cases and two shell/PowerShell cases.

[verified] Configured Ruff lint/format and mypy (35 files) passed. Scenario validation passed
373 specifications and 2,139 graded expectations. Generated adapters were refreshed from canonical
sources, and their byte gate is included in the passing default suite. Gate A passed both structural steps after staging the parser repair. All 194 checked links/anchors
across the audit index, repair report, roadmap and changed Grafana/SPL references resolved.
The earlier failed gate result is preserved in the integration-correction account above.

[verified] Canonical instruction byte deltas: observability agent +135; Grafana review +578;
SPL reference +826 and catalog +57; GCP monitoring +156; Alloy +32; trace semantics +202;
PCF scaling +118 and effects +415. The added context supplies the missing runnable guarded
hygiene path, actual phase-only query, integration/maturity distinctions, and explicit limits
replacing the unsupported resize recipe. No new authority or dependency is introduced.

[unverified] Live model behavior, production Grafana/GCP/CF operations, actual Splunk query
execution and native cross-platform enforcement remain outside this local repair evidence.
No paid evals, production writes, deployment, promotion or findings 21–25 repairs are included.
