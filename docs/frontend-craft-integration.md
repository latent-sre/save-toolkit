# Frontend craft: selective integration plan

Owner: toolkit owner; execution and evidence: invoking implementation session.
Authorized on 2026-10-11: commit this revised plan, then execute it. The owner's test-model
selection is Codex `gpt-6.1-sol` with medium reasoning. Acceptance of exact implementation bytes
and release remain human decisions. The live queue is [fleet-roadmap.md](fleet-roadmap.md),
item FRONTEND-001; this document supplies its scope, decisions and evidence, not a second queue.

## Baseline and outcome

Start from refreshed main `7f4cd38187cbe43cb3c1855b5d74127d843a1fb9` in an isolated worktree.
Preserve the existing branches and user work. Sources of selective additions:

- PR 357: `367808ba2b190c212a57fed66ef953ea78c3f3c6`.
- PR 358: `e6a5b3c509e6054df65ed451b88d00a97b84acbf`.
- PR 359: `61f41bda792c5a534e7eedaa1adc6d8bbd94b054`.

Deliver trustworthy serving and filter-control checks, richer product guidance without losing
main's operational contracts, and evidence distinguishing structural validity from actual
model/browser behavior. Do not merge the donor branches wholesale or close their PRs automatically.

## Decisions retained

Keep the [accepted owner decisions](decisions/2026-10-11-frontend-craft.md): existing product
choices win; React/Vue and component-system defaults remain; Mantine is allowed; one component
system per app; operator-console versus expressive-site design; concrete first-party OpenAPI,
problem/request-ID, cursor and idempotency contracts. An unrelated external API keeps its own
contract. Preserve session/identity, content-safety, accessibility, runtime configuration and
serving requirements and the entrypoint routes that load them. No platform or dependency migration.

For design exploration, use two directions when the user requests alternatives or the brief
leaves a consequential composition decision unresolved. Otherwise state one justified direction.
An existing direction or focused repair does not restart discovery; explicit delegated choice
allows the agent to select and proceed. Keep design decisions within main's owner defaults.

## Rule disposition and acceptance map

| Source or requirement | Destination | Treatment | Evidence required |
|---|---|---|---|
| Main owner/API/session/serving/framework rules | Existing core and references/assets | Retain; avoid duplicate instructions | Relevant existing checks plus source/load-path review |
| Main serving test matches only a directive name | serving-contract.mjs and asset tests | Repair actual policy verification at root and deep link | Permissive-policy red/green and legitimate-policy controls |
| PR 357 portal filter logic/calibration | Both incidents-page and incidents-console evaluators | Adapt; preserve console request-ID/cursor coverage | Both positive controls, stale/decoy negatives, supervised ambiguity classification |
| PR 358 product direction and whole-journey method | Existing design reference | Integrate only missing behavior; conditional alternatives | New-product and scoped-repair cases |
| PRs 357/358 live/historical selection and response races | live-data reference | Add conditional behavior; sessions owns auth/transport | Old response cannot overwrite current scope; paused history stays stable |
| PRs 357/358 tables, linked charts, relationship provenance | dense-data reference | Add nonduplicated interaction contract | Full-set sort/filter/selection; synchronized accessible relationship inspection |
| PR 358 interruption/reduced-motion checks | motion reference | Add behavior, not another library catalogue | Interrupted transitions end correctly; reduced motion retains control |
| PR 358 editing/persistence plus PR 357 run semantics | rich-editing reference | Add editor contract; API owns write mechanics | Undo, failed-save draft, reopen, version-bound run and unknown outcomes |
| PR 359 concise design/content wording | Matching existing reference | Transfer only a demonstrated gap | Per-rule review; no wholesale replacement |
| Duplicated generic explanation or conflicting donor defaults | None | Omit | Final source diff and disposition |

## Execution sequence

1. Commit this plan and its roadmap entry before implementation.
2. Repair serving-contract verification independently. Define supported policy forms: default
   no embedding, with an explicit expected-origin configuration for intentional embedding.
   Missing, wildcard, broad-scheme or report-only protection cannot silently pass. Unsupported
   syntax is a clear nonzero verification result, not a new evaluator result protocol. Cover
   root and deep-link HTML; do not merge separate CSP policies into an allowlist.
3. Repair both active incident UI oracles. Reproduce the limitation in each consumer, transfer
   the portal fix, calibrate native/custom controls and stale/decoy cases, and exercise ambiguous
   control measurement through the complete supervised result path. Share code only if the
   disposable harness can load it without a new packaging mechanism.
4. Refine design.md and minimal entrypoint loading guidance. Do not change routing metadata
   solely to broaden wording. Preserve everyday page/form fixes and backend/Grafana exclusions.
5. Introduce live-data, dense-data, motion and rich-editing guidance as separate coherent
   increments, matching the existing ADR. Define a named completion exercise before each edit;
   prove the relevant behavior per increment instead of postponing all checking to the end.
6. Prepare and calibrate product exercises, measure fixture cost, then freeze a bounded comparison
   before either model arm runs. Use the owner-selected model/reasoning. Both arms use identical
   evaluator bytes and conditions; only the frontend bundle varies. Do not compare through
   different grader versions. No arbitrary sixteen-build commitment.
7. Review and verify the integrated candidate, record per-case results and unresolved limits,
   regenerate projections and commit reviewed increments. No push, merge, deployment, PR closure
   or change to live systems is included in this instruction.

Steps 2 and 3 have disjoint write ownership and may run concurrently after step 1. One integrator
owns source integration, generated outputs, the roadmap, evidence and final coordinated suite.

## Product coverage and measurement

| Product | Observable acceptance |
|---|---|
| Team site | Find owner/help/guide; keyboard navigation; long/missing content; coherent primary and secondary views |
| Incident workspace | Consistent service/time across views; stable historical selection; gaps/staleness; failed-panel recovery |
| Automation builder | Branch and invalid connection; undo; save/reopen; failed/conflicting-save recovery; simulation versus real execution |
| Service catalog | Honest whole-collection filtering/sorting/selection; ownership and dependency evidence; context-preserving return; non-graph path |
| Existing-product repair | Narrow change preserves selected framework, identity and unaffected behavior without restarting design discovery |

Reuse existing fixtures where they establish the named outcome; extend only real gaps. Before
model trials, demonstrate that each mechanical check rejects its named broken control. Screenshots
support appearance, interaction checks support behavior, and agent-authored tests are not an
independent oracle. No string-presence tests masquerading as prompt-behavior verification.

Freeze exact candidate/baseline and evaluator identities, model and medium reasoning, tools,
fixtures, limits, repetition count and total budget in the evidence below before calls. Use one
candidate initially. Estimate costs from observed fixture timing and available runner data;
record assumptions explicitly. If the selected runtime/model or a required measurement is
unavailable, retain the exact failure as a gap; do not silently substitute another model or
claim that deterministic fixture tests establish generated-product quality.

## Acceptance and stop rules

- Any existing safety, API, session, accessibility or serving regression blocks that increment.
- A measurement error is not a candidate success. A tie or inconclusive comparison retains main
  for the claimed improvement; do not retry until green.
- Appearance cannot offset incorrect behavior. Report visual, functional, accessibility and
  operational-contract results separately; human review selects aesthetic preference.
- Changing candidate bytes invalidates affected comparison results. Retain exact identities.
- Keep independent repairs even if a broader guidance experiment is rejected.
- Human acceptance alone promotes the final candidate; no evaluator approves deployment.

## Verification and rollback

Run focused red/green, affected tests and calibration per change. Run scenario validation,
applicable lint/format/type checks, canonical/projection parity and link checks. At the final
code/oracle boundary, the integrator runs the coordinated heavy suite once, plus Gate A, in the
verified project Python environment. Investigate failures and distinguish environment limits.
Record entrypoint/reference byte deltas separately from reusable asset sizes. Review for lost
rules, duplicate prose, orphaned references and fixture/live-data confusion.

Each implementation increment is separately revertible. Regenerate projections after reverting
canonical text/assets; never hand-edit generated copies. Donor branches remain intact. Keep
comparison evidence while FRONTEND-001's acceptance depends on it, under the retention policy.

## Execution evidence

[verified] Plan baseline fetched 2026-10-11; implementation has not begun at this plan commit.
[verified] Earlier review reproduced a permissive CSP accepted by main and two portal positives
rejected by main's page oracle but accepted by PR 357. These are starting evidence, not final-byte
acceptance. The console consumer needs its own reproduction.
[unverified] Model-generated product improvement, complete four-product behavior and browser
accessibility remain unestablished until the execution records below say otherwise.
