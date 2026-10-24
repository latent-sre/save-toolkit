# Service lifecycle skill audit

[verified] Target: `skills/service-lifecycle/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. No material source-contract finding confirmed. Specification and engineering-quality verdicts: partial. Static lifecycle/context contracts are coherent; actual service transitions, external resolver compatibility and model adherence require independent evidence.

## Contract assessment

[verified] Audit is read-only by default; onboarding/retirement permit authorized discovery and unapproved drafts while missing identities, owners, consumers, data classification and recovery block live removal. Each surface needs an owner/disposition rather than implicit completion. Human/protected executors and production gating retain live actions; prohibited credential reads stay gaps. A missing record is distinct from an absent runtime control.

[verified] Retirement requires dependency/traffic exit, verified quiescence, separately gated resource removal, retained verification evidence, observability/ownership disposition and independent final checks. UNKNOWN attempts block retries. Shared resources need accepting owners; authoring, sending a handoff or successful context resolution cannot close the transition. Source history is retained as retired records rather than deleted. The table's alert/SLO-first wording is scoped by the observability row; the mandatory retirement-order reference fixes the whole-plan sequence and preserves evidence before telemetry removal. No consequential contradiction was confirmed.

[verified] Record transitions retain accountable ownership until independently reviewed records are read back. Changed deployments invalidate older evidence even inside a freshness window; document review cannot verify an operating procedure. Catalog mapping freshness, document review and exact-version successful execution have separate dates/meanings. Failed remediation or an unaccepted owner transfer remains pending.

[verified] The optional requirements forbid approval/credential context, require qualified owner/lifecycle and bound deployment freshness. The declared acceptance contract expects P30D to include day 30 and reject day 31, future or missing dates on a present deployment; absent optional deployment is a disclosed discovery gap. Service and deployment lifecycle assertions remain separate. The fixture producer is explicitly non-operational and cannot select actions; catalog assertions and synthetic compatibility tests do not prove a real team's ownership, deployment or retirement.

| Risk | Evidence | Result |
|---|---|---|
| Planning confused with execution authority | Entrypoint and retirement order | [verified] Draft/ready/executed evidence distinguished |
| Partial retirement reported complete | Ordered stop rules and record transitions | [verified] Receipts, independent checks and owner acceptance required |
| Stale context treated as verified service | Requirements and record-transitions reference | [verified] Dates and fixture assertions separated from operational evidence |
| Missing record treated as absent control | Audit finding rules | [verified] Documentation vs readiness gap distinction |
| External resolver/real transition correctness | No live target/resolver run in this pass | [unverified] Requires independent compatibility and service evidence |

## Read manifest and checks

[verified] Full canonical reads: `SKILL.md`, `references/record-transitions.md`, `references/retirement-order.md`, `context-requirements.yaml` (four files, 235 lines). Bounded supporting coverage: scribe/reliability caller and lifecycle-context test inventory; lifecycle scenario inventory. Earlier full caller/operational-learning/runbook/gate reads are reused. Root owns independent evaluator/resolver/test support.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_current_check.py service-lifecycle` exited 0: requirements and both references match generated copies byte for byte, entrypoint is identical, Markdown local links resolve, source diff against target is empty. Existing unchanged-source baseline is reused; no new tests, resolver executions, model calls or live actions ran in this pass.

[verified] Only this report changed for this item. No canonical/test/configuration repair, installs, commits, pushes or acceptance occurred.

[verified] Root fully read `scripts/test_service_lifecycle_context.py` (171 lines), the unapproved-retirement-draft and UNKNOWN-retirement scenario files, and the ordered retirement reference. Local tests check transition-owner slots and optional deployment freshness. Eleven external-producer tests require an explicitly selected `SRE_CONTEXT_ROOT`; they exercise boundary freshness, optional absence, forbidden approval/credential fields and non-operational fixture labeling. [sourced] The reused baseline skipped those external cases, so compatibility is not established here. Supplied-state scenarios assess draft permission, removal blockers, evidence taint and UNKNOWN reconciliation rather than real retirement. The mandatory detailed order resolves the surfaces-table shorthand; no new finding was confirmed.
