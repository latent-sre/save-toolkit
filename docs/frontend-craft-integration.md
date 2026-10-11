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

### Implemented increments

[verified] Plan commit: `32ad1480`. Source work is isolated on
`work/frontend-craft-integration`; the donor branches and original checkout were preserved.
The plan's link check passed. A remembered `scripts/check_plan_status.py` command was unavailable
in this repository revision; it was not a passing check. Current Gate A uses check_links and
validate_fleet, and both passed on the implementation tree.

| Increment | State and evidence |
|---|---|
| Serving verification | `780c4613`: real-HTTP permissive root/deep-link regression failed twice before repair; final affected suite 51 passed. Exact supported expected sources replace directive-name-only matching. |
| Conditional product direction | `9a2ba785`: alternatives depend on caller request or a named unresolved composition choice; selected directions and focused fixes do not restart discovery. |
| Live data | `f6b7cbef`: late scope responses, historical selection, reconnect freshness, missing samples and bounded retention; named completion exercise. |
| Dense data | `847909f1`: honest collection-wide semantics, stable selection, relationship provenance and synchronized keyboard path; named completion exercise. |
| Motion | `c231d17c`: latest intent, teardown, focus, reduced motion and interrupted final states; named completion exercise. |
| Rich editing | `9375a49b`: model validation, undo, draft/save identity, conflicts, version-bound runs and unknown outcomes; named completion exercise. |

[verified] Core growth is 449 bytes (10,730 to 11,179), consisting of four conditional loading
rows. The four new references total 11,960 bytes. Main's owner-decision table, framework/API/session
references and helper assets remain intact. Sources and generated counterparts were regenerated
and checked. Growth carries the owner's accepted capability scope and explicit completion
contracts; it is not a measured model-quality improvement.

[verified] Independent static review found no material issue in the serving or instruction changes.
It identified a calibration-fixture isolation issue: five console mutants inadvertently omitted
request IDs while bar8 was expected to pass. The first expanded run retained those five failures
alongside 57 passes. The fixture was corrected independently of the oracle; final results follow.
No observed failure has been discarded or called a model failure.

[verified] Both original oracle consumers rejected the portalled button/input positives: four
expected red results. The repaired consumers and fixtures passed all 62 opt-in Python calibration
checks in 176.41 seconds: 300 rendered assertions (30 cases times four page bars and six console
bars), plus two complete supervised ambiguity classifications. Both verify the actual ambiguity
diagnostic and INCONCLUSIVE result, not just any exit 1. Console request-ID and cursor assertions
remain unchanged. The separate protocol/checking suites passed 165 tests and 67 subtests.

Commands used the project CPython 3.14.7 interpreter and Node 24.16.0. Full calibration used the
existing pinned React 19.2.8, Router 7.18.3, Testing Library 16.3.3, Vitest 4.1.11, jsdom 30.0.1
and MSW 2.15.0 dependency tree; no dependencies were installed. Set
`INCIDENTS_PAGE_NODE_MODULES` to that installed tree and `INCIDENTS_PAGE_MODE=full`, then run
`python -B -m pytest -q -s evals/test_incidents_page_oracle.py -n 2 --dist=loadscope`.
The fixtures use both consumers; older oracles can be selected through `INCIDENTS_PAGE_ORACLE`
and `INCIDENTS_CONSOLE_ORACLE` for red evidence. These checks do not exercise real-browser layout,
axe/bar6, complete accessible-name/bar4 or text-status/bar7; those oracle branches are unchanged.

### Model and product evidence boundary

[verified] Implementation/testing helpers used the selected `gpt-6.1-sol` model with medium
reasoning. That establishes the selected helper configuration, not generated-product behavior.
The installed Codex CLI is 0.162.1 and its safe login-status check reports ChatGPT login. No
credential files were opened, copied or changed, and no separate model trial was made.

[verified] The repository's native build_probe invocation and trace checks are Claude-specific;
replacing its executable with Codex cannot preserve agent/plugin/tool identity. The Inspect
pilot also does not provide a native Codex toolkit comparison. A read-only readiness pass found
no existing suitable Codex runner. A proposed one-call, 60-second instrumentation canary remained
unscheduled because a documented empty tool inventory and suppressed inherited discovery were
not established. Prompting the model not to use tools would not prove those boundaries.

[unverified] Four-product generation, rendered aesthetics, browser keyboard/reflow behavior and
the small-repair comparison remain pending. The new references contain named completion
exercises; they are not executable product fixtures or executed trials. No 16-build campaign,
hidden model substitution, new runtime adapter or dependency installation was performed.
The approved code/guidance scope can be reviewed independently; native Codex comparison needs a
separately scoped compatible invocation, isolation and receipt path plus calibrated fixtures.
The caller has asked whether to extend that runtime scope; absent that choice, this remains an
explicit FRONTEND-001 acceptance gap, not an excuse to change Claude's established contracts.

Sources for the readiness distinction: local evals/probe/cli.py and invocation.py, the safe local
CLI help, and the [official Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
Framing semantics were checked against [CSP3 parsing](https://www.w3.org/TR/CSP3/#parse-serialized-policy)
and [frame-ancestors](https://www.w3.org/TR/CSP3/#directive-frame-ancestors); the repaired verifier
deliberately rejects unsupported policy combinations rather than claiming browser equivalence.

### Final local verification

[verified] Implementation commits end at `b4f8af032ad677568d556cf2ea66ecfe17314eaa`.
The independently reviewed and full-suite-tested candidate is
`72d3ba287364386e3c26586209c6a407290af7f4` (tree
`07a4a89313ac09ff8253de9072097dafa4eb3488`); its additional changes are evidence/roadmap text.
Independent static review approved the code/guidance scope with no validated findings. That
verdict does not establish product behavior or replace human candidate acceptance.

| Final check | Result and limits |
|---|---|
| Gate A | 2/2 structural steps passed |
| build_probe validate | 245 existing specs, 1,093 graded expectations validated; no new product trial |
| Ruff check / format | Passed; 24 format-discovery files unchanged |
| mypy | Passed on 44 configured source files; changed calibration test also passed its focused type check |
| Coordinated heavy suite | `python -B scripts/local_tests.py --heavy -rs`: exit 0, 2,565 passed, 82 skipped, 4,986 subtests passed |
| Runtime/identity | CPython 3.14.7, 10 workers/loadfile; 259.568 seconds wall time; HEAD unchanged and clean before/after |
| Oracle calibration | Separate opt-in full MSW run: 62 passed, 300 rendered assertions and two supervised classifications |
| Final source comparison | Generated parity and whitespace passed; remote main refreshed again and remained `7f4cd381` |

Full-suite receipt: Git common directory `local-test-runs/20261011T074102Z-a36fa784/run.json`,
with pytest.log and junit.xml beside it. Scratch red/green logs and the oracle file/dependency
receipt are retained outside the measured worktree at the primary repository's
`.tmp/frontend-integration-evidence-32ad1480/`. The move preserved their contents and left the
measured checkout clean.

The 82 suite skips consist of 62 opt-in UI calibration checks (executed separately above) and
20 platform/external checks: POSIX/symlink behavior, CI-only shell requirements, external producer
acceptance and Docker/Claude smoke checks. Ten Starlette/AnyIO deprecation warnings were reported;
they are warnings, not passed or failed assertions. No claim is made for the unexecuted checks.

The final evidence-record commit changes only this document and the roadmap after that run;
it does not change the tested implementation. Steps 1–4 are implemented with the evidence above.
Step 5's guidance is implemented, but its required per-capability behavioral proof remains pending;
named prose exercises do not satisfy that requirement. Step 6 remains pending compatible Codex
measurement and runnable product fixtures; step 7's local code review and verification cover the
candidate identified above, while human acceptance remains open. No push,
merge, deployment or donor-PR closure occurred.

### Rescan corrections

[verified] A fresh review of `fbe35e4` found a false filter failure, a remaining serving false
acceptance inherited from main, and the step-5 completion mismatch corrected above. The owner's
follow-up authorized fixing them. These corrections are working-tree changes after `fbe35e4`;
the earlier clean-commit receipt does not verify the new bytes.

- Both incident UI oracles now recognize an accessible name whose displayed selection changes,
  using an escaped, anchored pattern learned from the observed selection. Fixed names retain
  exact matching. Ambiguous, unsupported or replaced control identity is an inconclusive
  measurement; a recognized control showing stale state remains a candidate failure.
- Root and deep-link HTML responses now require the exact `text/html` media type. Charset
  parameters and case differences are accepted; an HTML-looking substring in another MIME type
  is insufficient. The HTTP negatives preserve the app body, caching and security headers.
- Adding the missing cursor negative exposed another oracle defect: a missing second row raised
  a lookup error before the cursor assertion, yielding INCONCLUSIVE. Console bar9 now asserts
  cursor transmission first and checks visible second-page content with a nonthrowing query.
  Its supervised negative requires candidate FAIL; identity-limitation cases require INCONCLUSIVE.
- The calibration README now covers both consumers and their actual checks. Step 5 retains its
  original behavioral-proof requirement instead of treating written exercises as execution.

[verified] Baseline reproduction rejected all twelve working dynamic-name combinations: button,
input and punctuation-bearing names, in both consumers and both transport modes. Five invalid
MIME cases passed the old seven-check serving contract; the repaired asset suite passed 59 tests.
The first cursor-negative calibration exposed the lookup-error classification defect and is
retained as failed evidence. Superseded exploratory runs are not final verification results.

Scratch reproduction logs and source identities are retained outside the candidate at the primary
repository's `.tmp/frontend-rescan-fixes/`. Final verification of these working-tree changes is
recorded below. Native browser behavior, per-capability exercises and the Codex product comparison
remain unverified; these evaluator repairs do not establish those outcomes.

[verified] Final rescan-fix verification used the selected `gpt-6.1-sol` helpers with medium
reasoning and the existing project dependencies; no installation or native product trial occurred.

| Check | Result |
|---|---|
| Serving assets | 59 passed; five negative MIME cases reproduced false acceptance before repair |
| Bounded UI calibration | 85 passed, one intentional page-only cursor skip; 525.31 seconds |
| Full MSW page calibration | 42 passed, one intentional cursor skip; 156.56 seconds |
| Full MSW console calibration | 43 passed; 176.16 seconds; combined full result is 85 passed and one skipped |
| Independent static review | No remaining concrete findings after the cursor-classification correction |
| Ruff / configured format / configured mypy | Passed; 24 format-discovery files and 44 typed source files |
| Scenario validation | 245 scenarios and 1,093 graded expectations validated |
| Coordinated heavy suite | 2,573 passed, 106 skipped, 4,986 subtests passed; exit 0 in 324.374 seconds |

Full calibration ran the two consumer selections independently with `-n 0 -k incidents-page`
and `-n 0 -k incidents-console`; their 43 deselections each are the other consumer, not untested
cases. Each mode covers 380 oracle checks across 38 fixtures and nine supervised classifications.
The whole calibration-batch timeout increased from 240 to 360 seconds after observing a batch
approach 232 seconds including startup. The successful bounded run had already loaded the old
240-second limit; full mode exercised the final 360-second envelope. Individual assertions and
supervised checks retain their original limits.

The final heavy receipt is Git common directory
`local-test-runs/20261011T130713Z-8e516851/run.json`. It records a dirty working tree based on
`fbe35e4`, with unchanged HEAD, status and tracked diff hash before/after. Seven execution-file
SHA-256 hashes are preserved in `.tmp/frontend-rescan-fixes/final-before.json` and
`final-after.json`; the final evidence and roadmap update follows that run without changing those
execution files. The 106 skips are 86 opt-in UI checks (85 passed and one intentionally inapplicable
page cursor check in each separate mode above) and 20 platform/external checks. Ten Starlette/AnyIO
deprecation warnings remain.

An additional direct-file `mypy evals/test_incidents_page_oracle.py` invocation outside the
configured target list reported three typing errors in unchanged `probe_testkit.py`. The same
errors reproduced with an exact scratch copy of the pre-fix test file. Configured mypy passed;
this unrelated helper-typing cleanup is not included in these fixes.
