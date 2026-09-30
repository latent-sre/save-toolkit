# Selected first-ten-skills repairs — 2026-09-30

The owner authorized confirmed findings **1–9** and recommendations **1–18** from the
[baseline review](README.md). All 27 selected items are implemented in canonical sources.
This record documents source repairs and local verification; it does not promote the candidate.

Base: `f505da5cacc4679a6eebe9ceebfd07108ecb226f`.
Branch: `work/first-ten-selected-fixes`.
Worktree: `F:\repos\sre-agents-review-first-ten-fixes`.
Evidence below was captured before publication; Git history records the resulting commit.
The original checkout's unrelated `CONTRIBUTING.md`
edit was left there; it was not copied into this branch. The original review snapshot remains
unchanged. Final candidate hashes and normalized byte deltas are in the
[candidate snapshot](remediation-snapshot.json).

## Confirmed findings addressed

| Original number / ID | Repair | Evidence and practical limit |
|---|---|---|
| 1 / AA-01 | `agent-authoring/references/artifact.md` accepts an observed failure or a requested new contract with acceptance cases. | Repair baselines remain mandatory; new capabilities no longer need an invented prior failure. Static inspection only. |
| 2 / BE-01 | Backend HTTP starter first establishes at least two visible records, then requires exactly one for `limit=1`. | Controlled FastAPI endpoints cover correct limits, ignored limits and sparse fixtures. This validates the starter's assertions, not any application API. |
| 3 / FE-01 | Frontend serving guidance reserves asset/API/health paths before document-navigation fallback; explains Staticfile pushstate's broad rewrite. | Linked upstream implementation supports the distinction. Missing assets, public files, deep links and a mounted UI are explicit acceptance checks; no deployed server was tested. |
| 4 / GC-02 | Cloud Run zero-percent traffic is distinguished from tagged-URL reachability. | Tags, ingress and IAM remain required observations before claiming isolation. No cloud configuration changed. |
| 5 / GC-03 | High request rate is a socket-pressure lead; HTTP/2 advice requires evidence and container h2c support, with tested rollout/backout. | Removes an unconditional mitigation. No workload or protocol trial ran. |
| 6 / GC-05 | Multi-container networking is separated from explicitly mounted shared volumes; idle-time collector CPU is addressed. | Startup ordering does not establish mounts or CPU between requests. Deployment verification remains with the owner. |
| 7 / GF-01 | Grafana hygiene validates the consumed object/list/string shapes before traversal and returns 2 for uncheckable input. | Malformed root, wrapper, nested panel, target and variable cases pass; clean/violation/V2 contracts remain intact. This is deliberately not full Grafana schema validation. |
| 8 / II-01 | Timing guidance first matches request identity and timer boundaries, retaining in-process queueing/streaming explanations. | Removes the unsupported inference that the gap must be outside the container. No incident cause is asserted. |
| 9 / II-02 | Dependency transport errors retain client configuration, trust, hostname, pooling and endpoint candidates. | Healthy/failing client comparison is explicit; volume is no longer the only client-side explanation. |

## Recommendations addressed

| Original number / ID | Change and retained boundary |
|---|---|
| 1 / AA-02 | Labels the skill-only frontmatter rules and links the separate agent contract. |
| 2 / AA-03 | Consolidates evaluation rules into the loop contract. Keeps frozen criteria, bounded trials/cost, failed evidence, held-out limits, conditional independent review and human promotion. |
| 3 / AK-01 | Broadens offload triage to request mix, purges, response cacheability and cache warmth; an unchanged activation does not clear caching. |
| 4 / AK-02 | Replaces abbreviated vendor citations with direct links and one scoped freshness/target-evidence boundary. Preserves the retry-budget discrepancy. |
| 5 / BE-02 | Makes crash/concurrency testing conditional on effects or replay-ledger behavior; simple idempotent writes retain proportionate duplicate checks. |
| 6 / CI-01 | Keeps entrypoint decisions concise and moves implementation detail to linked security/execution owners. Independent rerun authority and downstream unknowns remain in their existing reference. |
| 7 / DB-01 | Completes PostgreSQL and version-scoped SQL Server source links without changing engine policy. |
| 8 / EL-01 | Marks time horizons illustrative, so they cannot substitute for scope/decision routing. |
| 9 / FE-02 | Adds non-secret query-key scope, cache isolation/clearing, cancellation and late-response checks across logout or tenant/account/environment changes. |
| 10 / FE-03 | Separates HTML revalidation from hashed-asset immutable caching; adds old-chunk retention or bounded recovery preserving unsaved work. |
| 11 / FE-04 | Adds status announcements without focus theft and zoom/reflow checks, with documented two-dimensional-content exceptions. |
| 12 / FE-05 | Replaces row/destination/type-size quotas and aesthetic prohibitions with workflow, accessibility and measured rendering decisions. Preserves the Mantine house policy. |
| 13 / GC-01 | Requires protected output before configuration/log reads; the command guard is explicitly not output masking. Without protection, use scoped human-sanitized observations. |
| 14 / GC-04 | Separates migration-guide assumptions from platform capabilities; jobs/worker pools retain coordination and retry-safe effects rather than implying singleton execution. |
| 15 / GC-06 | Explains that work may continue after a 504; unknown write outcomes require reconciliation and the API's retry contract. |
| 16 / GF-02 | Uses the actual rate-interval formula and effective Min step/scrape inputs; unmatched query/image resolution is labelled approximate. |
| 17 / GF-03 | Deletes “idempotent-by-target”; UID/desired bytes identify state, while unknown dispatches still require readback/history reconciliation. |
| 18 / GF-04 | Centralizes dated API observations in `http-api.md`, schema rules in `json-model.md`, and decisions in the operation loop. Removes the repeated stack load while retaining endpoint-specific concurrency and recovery rules. |

## Verification

- [verified] Before repair, the new focused regression run reported **16 failures**: two sparse
  pagination cases and fourteen malformed-input subtests; four tests and three malformed-input
  subtests already passed. This reproduced the false pass and unhandled/incorrect exit behavior.
- [verified] After repair, `pytest scripts/test_backend_craft_assets.py scripts/test_dashboard_hygiene.py -q`
  passed **111 tests and 17 subtests**. The only warning was the existing Starlette/AnyIO
  `BlockingPortal` deprecation.
- [verified] Static review found no actionable defects in the executable and documentation changes;
  it does not establish runtime task-following or live target behavior.
- [verified] The first integrated run found only generated-output drift and an assertion tied to
  the promotion rule's old heading: **1,249 passed, 2 failed, 8 skipped, 2,075 subtests passed**.
  Adapters were then regenerated. The assertion now checks the loop contract's human acceptance
  and explicit prohibition on authoring-loop merges, deployments and live changes.
- [verified] Regeneration reported **168 adapter files**, followed by **Platform adapters: PASS**.
  Gate A passed **2/2 structural steps**.
- [verified] Final `pytest -q -rs`: **1,250 passed, 8 skipped, 2,076 subtests passed**,
  exit 0 in 260.50 seconds. One existing Starlette/AnyIO deprecation warning remains.
  The eight skips were three Windows directory-symlink cases, two unavailable/local-only shell
  hook checks, and three opt-in Docker/Claude smoke or immutability cases. These skipped paths
  were not verified on this host; no model call or download was enabled for this batch.
- [verified] Final independent static follow-up found no actionable defects in the relocated
  authority assertion or evidence wording. Candidate hashes still match the checked source/test/
  generated bytes; `git diff --check` is clean. The original checkout's `CONTRIBUTING.md` hash
  matches the review baseline's pre-existing edit.

The selected source changes need extra text where the original contract omitted a decision-changing
condition: session isolation, SPA assets/caching, Cloud Run reachability/protocol/CPU, query fidelity,
and malformed-input handling. Consolidation removes duplicated evaluation, CI and Grafana procedures;
longer direct URLs are evidence cost rather than new operating policy. The snapshot separates prose,
helper and test deltas so total growth is not mistaken for prose simplification.

Changed canonical prose is **+5,242 normalized bytes / +18 lines** overall. Within it, the artifact
reference is **−582 bytes / −12 lines**, the CI bundle **−386 bytes / −6 lines**, and the frontend
design reference **−799 bytes / −9 lines**. The total is larger because the selected missing
contracts and source links outweigh the removed repetitions.

## Remaining owner decisions

Confirmed **10 / II-03** (alert fire/window wording), recommendation **19 / II-04** (candidate
quota) and recommendation **20 / II-05** (incident prose consolidation) were outside the selected
batch and remain unchanged. The incident entrypoint is unchanged; only the two selected diagnostic
bullets in `signal-patterns.md` were repaired.

[unverified] No live cloud/database/Grafana/browser action, deployment, external effect or model
evaluation was performed. Vendor sources establish documented behavior; historical target observations
remain bound to their original target/date. Local checks do not prove deployed behavior or model
compliance. `SKILL-REVIEW-010` remains the single roadmap item for acceptance and the three open items.
