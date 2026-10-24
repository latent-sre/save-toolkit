# First ten audit finding repairs

The requester authorized findings 1–10 in ledger order after the audit-only checkpoint
`7b07806e13f81d9fc8904b182b7f66d2e1db2530`. Original reports describe source at `8b4f9b78`;
this follow-up records the repairs. The [fleet roadmap](../../fleet-roadmap.md) remains the only
live backlog. Findings 11–25 are outside this repair batch.

## Changes and acceptance evidence

| Finding | Repair | Focused evidence |
|---|---|---|
| AUDIT-GRAFANA-001 | Folder/dashboard restoration compares fresh state with verified operation-written state, stops on drift or missing evidence, then uses the fresh token. Complete restore diff and existing scope/parent-move authority still apply. | `scripts/test_audit_guidance_contracts.py`: dashboard and folder contracts; original text fails. No live Grafana write. |
| AUDIT-EVAL-DOC-001 | Eval guide links to RELIABILITY-001's authoritative roadmap status instead of duplicating a stale deferral. | Guide contract; original text fails. Human run approval and acceptance remain required. |
| AUDIT-RESEARCH-001 | Canonical exact grant and validator use `mcp__plugin_githits_githits__grep`. No wildcard or extra authority. | Positive grant assertion and legacy-name mutation rejection; original source fails. Current session registry exposes `grep`, not `code_grep`; installed Claude GitHits 0.35.0 declares server `githits` at `https://mcp.githits.com`. Actual Claude dispatch remains unverified. |
| AUDIT-AUTHORING-001 | Generator preserves the two platform frontmatter references as original-dialect teaching material. Other workspace invocation text still adapts. | Both projected references equal canonical text and retain qualified Claude examples; original generator fails. Existing bare-workspace invocation test remains. |
| AUDIT-API-001 | Oracle holds an incomplete-header connection against the launched service, requires closure by one absolute deadline, then checks process survival and a complete authorized 200 response. Fixture explicitly requires a header timeout of at most ten seconds, measured with one second of scheduling tolerance. | Loopback controls cover bounded/unbounded, trickling, exited process and broken HTTP. Supervised completion covers pass, contract failure, early exit, unavailable measurement and crash. Go and Docker are absent, so a compiled Go candidate remains unverified. |
| AUDIT-CI-001 | Target selection uses the existing command tokenizer and resolves relevant arguments instead of matching command text in comments. Endpoint, org and space must precede push. | Comments, echo text, missing/unresolved arguments and late selection fail; valid command ordering and literal environment values pass. Actual supervised CF-target success/failure paths run without invoking CF. |
| AUDIT-FRONTEND-001 | URL validation rejects authority-form root paths, including parser-stripped control-character variants at the sentinel origin. | TypeScript tests execute through Node; sentinel inputs rejected, existing valid paths and HTTP(S) URLs retained. |
| AUDIT-FRONTEND-002 | Serving contract requires unqualified `no-cache` or `no-store` through quote-aware directive parsing, with matching guidance. Bare `max-age=0`, shared/stale conflicts, field-qualified and lookalike directives fail. | HTTP serving calibration: ten negative combinations plus explicit valid policies. |
| AUDIT-FRONTEND-003 | Invalid attempt counts throw before fetch/sleep; total sends must be a positive safe integer. | Nonfinite, fractional, zero, negative and unsafe integers rejected; default and single-attempt bounds checked. |
| AUDIT-GCP-001 | Age slope is not causal proof; guidance compares acknowledgement/completion, ingress/backlog and handler/lease/item evidence. Same-timestamp cohort and retention counterexamples are explicit. | Deterministic cohort calculation demonstrates rising age with successful acknowledgements; source contract rejects original inference. No GCP call. |

[verified] Focused red/green checks established the original gaps before repairs: frontend
regressions failed 12 checks before repair; the initial repaired frontend suite passed 89 tests. Independent review then found a quoted-value false positive; fourteen additional negative checks failed before the quote-aware repair, and the final frontend suite passed 106 tests. Both projection
examples and the old GitHits grant failed their new checks before repair. Four guidance contracts
failed against original content and passed after repair. These are helper and source contracts,
not measured model compliance. The oracle checks also failed five controls before repair; final integrated counts are recorded below.

## Integrated verification

[verified] Coordinated default-plus-heavy suite: **4,302 passed, 84 skipped, 4,954 subtests
passed**; 4,386 collected, zero failures, exit 0 in 95.536 seconds. Command:
`/home/hawkfire/save-toolkit/.venv/bin/python scripts/local_tests.py --heavy`.
Receipt: `/home/hawkfire/save-toolkit/.git/local-test-runs/20261024T113155Z-c6a1e03a/run.json`.
The tracked working-tree diff hash was identical before and after the run. The new tests were
collected from the working tree; the receipt does not hash untracked contents. Subsequent changes
are repair documentation and Git staging only; source hashes were checked unchanged.

[verified] Configured Ruff lint and formatting, isolated oracle syntax/name lint, mypy (35 source
files), and validation of 373 scenarios / 2,136 expectations passed. Focused oracle integration
passed 201 tests and 104 subtests before the full run. The 84 skips are 39 opt-in UI cases,
29 Windows cases, 11 external producer cases, three Docker cases and two shell/PowerShell cases.

[verified] Independent Sol source review found no remaining material issue in the first-ten
canonical fixes and tests after the quoted-cache and CF argument-resolution corrections. This
is a working-tree source review, not approval to merge or promote. The caller reviewed generated
changes and owns combined verification. Gate A passed both structural steps after staging;
all 242 links/anchors across the audit index, repair report, roadmap and eval guide resolved.

[verified] Canonical instruction growth: researcher −5 bytes; serving reference +150;
GCP skill +386; dashboard workflow +173; HTTP API reference +1,020. The Grafana growth supplies
the missing before/operation-written/live comparison and conflict recovery; GCP adds the concrete
counterexamples and corroborating measurements needed to avoid the audited causal inference.
No new runtime dependency or authority is introduced.

[unverified] Native Claude tool dispatch, live model behavior, browser deployment, production
Grafana/GCP operations and real intermediary-cache behavior are not established by these checks.
No live writes, paid evals, deployment, promotion, archive execution or findings 11–25 repairs
are included.
