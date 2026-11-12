# Fleet roadmap

> **Status: live; working update 2026-11-02, merged-item closure.** This is the only backlog.
> Historical records supply evidence, not new work or authorization. Cleanup does not close an
> unresolved item, approve a model budget, or establish behavioral acceptance.

## Item contract

Every live item carries seven fields: **ID** (stable identifier), **Status** (`active`, `ready`,
`blocked`, `decision-needed`, or `deferred`, dated), **Owner**, **Outcome** (what done looks like, in
one or two sentences), **Next action** (the next concrete step and who takes it), **Evidence**
(one link to the record that proves current state, or `none yet`), and **SRE task** (the task a
human SRE does differently when this lands; an item that cannot name one is `deferred`). An item
leaves this file only when its Outcome is met and merged, or an owner disposition is committed.
Its removal commit is the closure record: name the ID, disposition, and supporting evidence in the
commit message or patch. The changelog is a recent summary, not a permanent closure register.

Find an older item's disposition with
`git log --first-parent -m -p -G '<ID>' -- docs/fleet-roadmap.md docs/roadmap-closed.md CHANGELOG.md`.
Inspect the removal patch; read an older closure entry with `git show <commit>:CHANGELOG.md`.
This also covers items recorded before the closed register and changelog were trimmed. Historical
records do not re-queue work.

## Repository work

### EVAL-016 — prove the Inspect orchestration matches the native batch, then decide what it replaces

**Status:** `active` (2026-11-02). `evals/inspect_fleet.py` runs the native routing and contract
trials as an Inspect task with grading unchanged; its offline tests pass, and no paid run has
compared it with `build_probe.py run`.
**Owner:** Maintainers run the paid parity comparison and approve its budget; the repository owner
decides the replacement inventory afterwards.
**Outcome:** One frozen selection run through both paths on the same model, CLI and host shows the
same per-scenario verdicts under `build_probe.py regrade`, with timing, cost and any INCONCLUSIVE
reasons recorded; a follow-up decision then names which native batch code Inspect replaces, or the
track is relabelled as scheduling only.
**Next action:** A maintainer follows the [parity run plan](fleet-evaluation/run-plan-inspect-native-parity.md)
on a host with Claude credentials and a current judge calibration, and files the comparison under
`docs/reviews/`.
**Evidence:** none yet; the [decision](decisions/2026-11-02-inspect-orchestrates-native-runner.md)
records the design and its rollback.
**SRE task:** Read one `inspect view` log of a fleet regression instead of a directory of records,
trusting it only once it is known to say what the native batch says.

### RUNNER-001 — rewrite the eval runner's core around a persisted evidence artifact

**Status:** `active` (2026-11-02); the owner accepted the
[design record](decisions/2026-11-02-probe-runner-refactor.md) for implementation. Stage 0, the
goldens, landed on PR #455 with a follow-up for native conversations and the batch view; the owner's
decisions the plan left open are recorded in the design record's amendment of 2026-11-02. Stage 1,
`evidence.json` written by every graded attempt and by a regrade of an older run through `legacy`,
landed on PR #458 and stage 2, the check registry as a package with probes marked, the two import
cycles removed and the identity widened, on PR #459. Stage 3, the evidence engine grading every
attempt in shadow with the result rules named and the attempt's life recorded, landed on PR #460.
The owner waived the shadow gate on 2026-11-03 (no private iteration ran under stage 3); stage 4,
the cut-over to the evidence engine as the one grading path, landed on PR #461. Stage 5, the
command-line split the owner brought into scope on 2026-11-03, is implemented and awaits the
owner's acceptance.
**Owner:** The human owner accepts each stage's exact candidate; a maintainer session implements the
stages in order.
**Outcome:** An attempt writes one versioned `evidence.json`; grading is a pure function of scenario
and evidence shared by live grade and regrade; the eight threat-model rules are named units with a
test each; the twelve live-only checks run as probes whose outcomes are evidence; old run directories
stay readable through a quarantined legacy loader; every CLI subcommand, saved-run interface, v1
record and result rule is unchanged.
**Next action:** `rescore` one private iteration under the stage 4 runner and `diff` against a
rescore under the stage 3 runner, and run `check-evidence` on the first iteration the stage 4
runner writes: zero changed verdicts and zero differences prove the cut-over on real runs, which the
goldens alone do not. Then accept stage 5's candidate, the last the record scopes.
**Evidence:** [Design record](decisions/2026-11-02-probe-runner-refactor.md); per-stage evidence lands
in each stage's pull request.
**SRE task:** Trust that a regrade of a saved attempt reaches the same verdict as its live grade for a
stated reason, and read which result rule produced it.

### WORKBENCH-001 — plan a shared SRE operations product for humans and agents

**Status:** `active` (2026-10-02); comprehensive product specification and delivery planning.
**Owner:** Human product owner accepts scope and release decisions; implementation and
verification owners are assigned before each delivery phase.
**Outcome:** A reviewable specification covers common commands, Grafana, scripts, investigation
workflows, extensibility, and the full future product, with traceable acceptance criteria and
explicit permission, evidence, compatibility, and recovery contracts.
**Next action:** Review the [SRE Workbench planning package](sre-workbench/README.md), resolve its
phase-zero decisions, and select the first implementation slice. Planning authorizes no live
execution, credential setup, host grant changes, or production rollout. Product implementation
will have a separate repository/release decision; this roadmap remains the sole live work queue.
**Evidence:** [Product requirements and specifications](sre-workbench/README.md); requirements
come from the owner discussion on 2026-10-02. All product runtime behavior remains unverified.
**SRE task:** Run the same useful operational checks from a terminal or an agent, preserve their
evidence, and extend the tool as new operational needs appear.

### RELEASE-001 — make the toolkit installable as an immutable, rollback-tested release

**Status:** `active` (2026-11-12). The owner requires verified native delegation on the default
Copilot harness before release. A commit-pinned selector and checksummed candidate archive are
prepared; installed acceptance and an accepted immutable rollback baseline remain outstanding.
**Owner:** Maintainers accept the release; a maintainer session owns the plugin contract and
`software-engineer` owns helper/adapter repairs.
**Outcome:** An SRE installs a pinned artifact rather than whatever `main` holds, and can roll back
to a previously accepted one. The acceptance cases pass on those
exact shipping bytes, which the 2026-09-10 local-install run did not exercise.
**Next action:** Resolve the missing native per-parent target restriction, then implement and verify
the owner-selected Copilot delegation contract. Current converter/SDK research has not identified a supported mechanism;
then run the new Format acceptance case first: the plugin now declares Agent Plugins
1.0 because VS Code ranks `.claude-plugin/plugin.json` above a schema-less selector manifest, and no
installed run has yet shown which layout loads. Retire the mutable `"source": "./"` selector in `.claude-plugin/marketplace.json`
for an immutable selector or checksum, then re-run the acceptance cases on those shipping bytes: the
2026-09-10 pass was against a local `./` install, and a passing run does not carry to bytes it did
not exercise. The enforcement results that were open on VS Code 1.135.0 are superseded by that run.
Still unrun: the agent-scoped terminal-hook canary and the SRE visual-read acceptance cases, with
`hooks/copilot-hooks.json` shipping empty. Maintainers must run the exact candidate in an isolated
profile on each supported host, including a dedicated Grafana Viewer browser session. The SRE
browser grant now includes selected native/MCP viewing interactions. Structural tool checks
do not prove image delivery or helper invocation. The installed VS Code 1.138 source handles some
hook failures as warnings; the launcher's 42/43/44 protocol is not authentication or proof of
fail-closed host behavior. Keep those limits explicit until the host cases are observed.
**Evidence:** [Current preparation and selected harness](reviews/2026-11-12-release-001-preparation.md);
the 2026-09-10 VS Code 1.137.0 acceptance row in the host-support table of
[`README.md`](../README.md); HOST-002's closure commit records the owner disposition.
**SRE task:** Install a named version of the toolkit, and go back to the previous one if it regresses.

### SRE-CF-001 — complete protected SRE investigation access

**Status:** `active` (2026-09-21); selected CF reads and authentication without exposing
credentials are wanted. The caller/coverage fixes, selected browser tools and bounded Grafana
read/query helper, with its per-user credential file, are implemented; live session binding and
native acceptance remain open, and the credential file is still readable through unhooked Read tools.
**Owner:** Save Toolkit maintainers.
**Outcome:** Grafana investigation and selected CF application observations work on
Claude Code and VS Code/Copilot under an agreed, verified access policy, reusing existing SSO/session
access first and supporting personal-account authentication when needed without exposing credentials
to the LLM. Deployment actions, other production mutations, and credential-bearing diagnostic reads
remain excluded.
**Next action:** Run the bundled Grafana helper with a human-written `~/.config/save-toolkit/grafana.env`,
bind the operations-repository path, and verify one complete dashboard investigation with its controls.
Identify the existing SSO/browser/CLI session and credential mechanism, including protected personal
credentials where needed. Complete CF target/output/time bounds, browser runtime verification and an
isolated analysis path only with their matching controls. Use the
expanded host acceptance cases
for both hosts. The source update adds selected browser interactions and one installed helper grant,
not general HTTP, script, page-code or standard Copilot terminal access;
Helix/BigQuery remains an unconnected placeholder. INCIDENT-QUALITY-001 retains behavioral acceptance.
**Evidence:** [Planning context beside the agent](../agents/README.txt);
[current canonical profile](../agents/sre-assistant.md), [caller](../skills/incident-investigation/SKILL.md),
[guard source](../scripts/readonly-guard.py), and supplied-state regression fixtures under `evals/scenarios/`.
Source and offline checks do not establish native acceptance of the access policy.
**SRE task:** Delegate a scoped application-state or event-history check while investigating another
part of the incident, without delegating deployment or remediation authority.

### EVAL-012 — plan incident and coding evaluations for the fleet

**Status:** `active` (2026-10-27). The owner accepted [specification](fleet-evaluation/README.md)
revision 0.6 on 2026-10-06 as the scope freeze, amended for WP-13's completion boundary on
2026-10-18. By work package:
- WP-01 complete: `evals/compare_runs.py`, merged in
  [PR #333](https://github.com/latent-sre/save-toolkit/pull/333) at `52352543`.
- WP-02 complete on 2026-10-09: [run record](reviews/2026-10-08-wp02-native-readiness.md); the
  [EVAL-011 closeout](reviews/2026-10-10-eval-011-closeout.md) binds the repaired native
  measurement contract.
- WP-08 implementation candidate prepared: adapter, host credential proxy, independent verifier,
  smoke gates and offline tests; [implementation and verification evidence](reviews/2026-10-25-wp08-adapter.md).
  Live smoke and paid trials have not run; exact-candidate acceptance remains with the owner.
- Complex-campaign preparation is in progress under the [implementation plan](fleet-evaluation/implementation-complex-campaigns.md):
  WP-08 has a separate [ten-case hard-task proposal](fleet-evaluation/wp08-complex-proposal.md);
  WP-04 has a pinned [source/admission packet](fleet-evaluation/wp04-case-review.md);
  WP-05 has [18 authored execution profiles over six incident families](../evals/incident-conversations/README.md),
  with native ordered-session support and offline controls. WP-09 has separate
  [five-case SWT](fleet-evaluation/wp09-swt-run-plan.md) and
  [five-case Harbor/Terminal-Bench](fleet-evaluation/wp09-terminal-runplan.md) proposals,
  native author/independent verifier adapters and executable model-free smoke commands. The standalone
  [campaign report](fleet-evaluation/campaign-report.md) preserves measurement, billing and review gaps.
  [Integrated preparation evidence](reviews/2026-10-25-complex-campaign-preparation.md) records the
  offline controls and repaired review findings. These are preparation milestones, not accepted
  benchmark outcomes; exact-case acceptance and live gates remain open.
- WP-10 in progress: the [first step](reviews/2026-10-10-wp10-first-step.md), its
  [case acceptance](reviews/2026-10-10-wp10-case-acceptance.md), and its [saved-trace review](reviews/2026-10-15-wp10-saved-trace-review.md) are approved; the
  [Luna continuation](reviews/2026-10-15-luna-reliability-gcp01.md) is complete at run level, with
  exact quotation, the reliability exception-path explanation and GCP-01 B's factual findings open.
  The [current four-model continuation](reviews/2026-10-25-wp10-continuation.md) completed
  all 44 planned attempts, retaining four instrument gaps and separate semantic proposals.
  Mechanical passes do not close the observed reasoning failures or human acceptance.
  The [88-attempt repair comparison](reviews/2026-10-25-wp10-handoff-repairs.md) is complete
  at run and AI-review level. Retry reasoning improved on Sonnet/Luna in the sample;
  Terra remains unresolved, and the unsupported GCP rewrite was withdrawn. Keep its
  incumbent/candidate evidence separate from the earlier baseline and human acceptance.
- WP-12 complete on 2026-10-17: all 64 GCP cases accepted at `9147ff91`
  ([pilot and template](../evals/oracles/gcp/README.md), [catalog](../evals/oracles/gcp/CATALOG.md)).
- WP-13 complete on 2026-10-18 under its [run plan](fleet-evaluation/run-plan-wp13-gcp-native-pilot.md):
  the [pilot](reviews/2026-10-17-wp13-gcp-pilot-review.md), the
  [stress test](reviews/2026-10-17-wp13-stress-test.md), the
  [hardened comparison](reviews/2026-10-17-wp13-hardened-comparison.md) and the
  [catalog baseline](reviews/2026-10-18-wp13-catalog-baseline.md); branching moved to BRANCH-001.
- The [Windows preparation and completion audit](reviews/2026-10-27-eval012-windows-preparation.md)
  binds fresh WP-04/08/09 source packets and retains failed Windows checks. Docker accepts
  a size option but did not enforce it in the bounded write probe; the host is not qualified.
  Windows fixture repairs have focused passing evidence; symlink privilege, native signal
  qualification and the intermittent publication-lock diagnosis remain open in that audit.
- WP-03 remains deferred under EVAL-015. WP-06/07's SREGym and recovery work, WP-11's later
  AIOpsLab expansion and WP-14's live GCP exercises retain their delivery/acceptance requirements.
- WP-15's [Coder Eval experiment](fleet-evaluation/coder-eval.md) waits for the first useful comparison.

**Owner:** The human owner accepts scope, run conditions and exact candidates; a maintainer session owns
scenario and measurement design; implementation and lab owners are assigned per delivery package.
**Outcome:** A reviewable evaluation specification covers ITBench-Lite, SREGym, repository repair,
test generation, selected terminal tasks, GCP managed-service/migration and GKE evaluations, actual
fleet integration, Coder Eval runner assessment and later Microsoft AIOpsLab, with traceable evidence,
acceptance tests, delivery phases and explicit open decisions.
**Next action:**
- Execute the owner's [follow-through plan](fleet-evaluation/run-plan-followthrough.md): shared
  Sonnet/Sol/Luna/Terra testing support first, then WP-04 on Linux and Windows, EVAL-005,
  ROUTE-007, HANDOVER-001, WP-09 and WP-10. The owner approved USD 40 aggregate testing
  spend; exact runtime evidence, human tabletops and candidate acceptance remain distinct.
  The owner previously deferred Windows WP-04 and Docker-based WP-09 execution and now
  requests their preparation. The measured quota failure and Windows verification gaps must
  be resolved before execution; preparation does not accept a new host or candidate. Bounded Codex subscription
  runs are explicitly approved, with dollar costs remaining unknown.
  [Follow-through evidence](reviews/2026-10-25-followthrough.md) records the four-model
  smoke and five-case Linux WP-04 pilot, preserving technical failures, mapping gaps
  and unmeasured upstream/human assessments.
- WP-08/09: resolve the observed hard-quota failure on the selected Windows Docker Desktop
  engine, with an owner-approved host amendment if needed. Repair/qualify Windows checks and
  review the exact implementation and complex-case/run-plan amendment. Freeze
  the accepted dataset/selection, licences, CLI, plugin and image identities using the
  [operator commands](fleet-evaluation/wp08-operator.md). Then start the approved
  [run plan](fleet-evaluation/run-plan-wp08-swebench-repair.md)'s model-free smoke, first paid trial
  and remaining nine Claude tasks as separate owner-started steps. Other models retain their own
  approvals; WP-09 follows WP-08.
- WP-04/05: complete exact case/review admission and bounded native run conditions after integrated
  offline verification. WP-09 requires pinned compatible images and per-case model-free smoke before
  exact-candidate/model/spend acceptance; Harbor is already the selected Terminal-Bench runner.
- WP-13: none; complete. Use its cases as a regression check when a skill or agent changes.
  Haiku's inconsistent `gcp-ops` loading limits any skill fix measured on Haiku.
- WP-10: review the retained repair candidate and bound 88-attempt comparison. Resolve the
  remaining Terra, GCP B and quotation/instrument gaps or select broader qualification;
  human acceptance names the exact candidate. No further campaign is scheduled automatically.
- Before any rubric-graded campaign: one owner-approved judge recalibration, because the clean-room
  auth-failure fix (`1d92654f`) changed the judge identity.
- Runner follow-ups, not blocking: unittest `--option=value` spellings and SHA-spelled Git ranges
  fail their detectors (0/303 and 0/909 in saved traces).

The follow-through request authorizes its bounded testing within USD 40 total. It does not
authorize lab provisioning or production change.
**Evidence:** [Specification](fleet-evaluation/README.md); per-package records are linked under Status.
Integration and behavioral results remain unverified.
**SRE task:** Compare exact agent candidates on realistic incidents and engineering tasks, see what
improved or regressed, and distinguish failed behavior from an instrument that could not measure.

### FRONTEND-003 — define the team's GUI mix after the first runs of the rewritten skill

**Status:** `active` (2026-10-11). The owner said on 2026-10-11 that the team's GUI work is a mix
of the skill's five archetypes and that the mix is defined after a few runs, not up front; the
rewritten `frontend-craft` therefore weights the archetypes evenly and defers the deep capability
references ([decision](decisions/2026-10-11-frontend-craft-generalized.md)).
**Owner:** The human owner decides the weighting and the first add-on; a maintainer session owns the
skill's archetype table and build scenarios.
**Outcome:** After the first few real GUI tasks, the archetype table reflects the kinds of GUI the
team builds most, the greenfield recommendations follow that weighting, and the first deep
capability reference (charts and grids, live data, forms, or editors) is chosen and scheduled.
**Next action:** Whoever runs `frontend-craft` on a real task records the archetype, the kit set and
the deploy target the caller chose, in the packet; after the first three to five, the owner reviews
them beside the proof packet and picks the weighting and the add-on.
**Evidence:** [Rendered proof of the skill's defaults](reviews/2026-10-11-frontend-craft-proof/README.md);
no real-task runs yet.
**SRE task:** An SRE building a GUI gets defaults tuned to the kind of GUI the team builds most,
and a deep reference for the capability they reach for first.

### BACKEND-002 — add go-craft beside python-craft

**Status:** `active` (2026-10-18). A single-file `go-craft` candidate is authored and composed with
`software-engineer`, `api-craft` and `operator-cli`; HTTP-specific Go guidance stays in the API
reference ([decision](decisions/2026-10-11-backend-craft.md)).
**Owner:** The human owner accepts the candidate; a maintainer session owns the skill.
**Outcome:** `go-craft` covers writing, refactoring and testing Go across services, CLIs and
libraries, measured against build scenarios the way `python-craft` is, and `api-craft` and
`operator-cli` load it for Go changes.
**Next action:** Review the candidate and select a bounded language-specific build comparison
that can test whether its guidance improves Go work beyond the model's baseline.
**Evidence:** Three authored discovery cases and a required Go-skill load in the existing
[Go HTTP build](../evals/build-scenarios/build-software-engineer-go-incidents-api.yaml).
These are unmeasured; the HTTP oracle does not establish Go-language skill benefit. No dedicated
Go-language build comparison or native routing result exists yet.
**SRE task:** An SRE changing a Go service or tool gets the team's Go conventions applied without
asking for them.

### EVAL-005 — the observability engineer's Grafana write lands, and only that write

**Status:** `active` (2026-11-12). Local qualification is repaired: clean candidate `020c43c5`
passed the full heavy suite (4,883 passed, 312 capability/other skips). Its two bounded Sonnet
trials remain FAIL (13/15 and 12/15). Both save the panel with description and `No samples` and
leave the datasource unchanged. Both correct refusals exposed further regex false negatives, now repaired offline;
one post-write query is empty, the other trial queries only before saving and omits evidence labels.
Correction commit `a51ce151` passed the final default suite (3,972 tests, 270 skips), with independent
static approval; it has not had a new native campaign.
A controlled replay reproduced the minute-alignment empty-range mechanism; the fixture now requires
one-minute-old finite data. A fresh model-free fixture passes all six query controls and seven
service checks, without establishing native acceptance or the original empty request's exact cause.
Readiness candidate `2bce1b29` has static approval, but its new full heavy gate failed four Windows
timeout-cleanup controls (4,879 passed, 312 skipped). Those four pass in the focused four-worker
check; the intermittent failure's cause remains unconfirmed and qualification is still failed.
**Owner:** The human owner approves each repair run; a maintainer session repairs the scenario and runs it.
**Outcome:** [`build-obs-dashboard-write-honours-the-carve-out`](../evals/build-scenarios/build-obs-dashboard-write-honours-the-carve-out.yaml)
fails only on agent behavior: its refusal-wording check accepts measured correct refusals, and
its post-write query check fails only when the query did not return the persisted panel's data.
Required panel presentation is explicit in the task rather than inferred from advisory guidance.
**Next action:** Resolve or disposition the intermittent Windows timeout-cleanup failure before
another paid campaign. Retain strict service-state and post-write query checks and bind any further run to
the repaired readiness scenario. Preserve request/response timing; the controlled reproduction
does not recover the original native request's phase. Post-write execution
and evidence-label misses remain behavioral failures. The three-call continuation is complete;
a further campaign needs a new frozen selection and finite budget. Historical results stay unchanged.
**Evidence:** [Repair and bounded follow-through](reviews/2026-11-12-eval-005-repair.md);
[November 11 continuation](reviews/2026-11-11-eval-005-continuation.md);
[offline refusal repair](reviews/2026-10-25-eval-005-repair.md);
[historical run record](reviews/2026-10-18-eval-005-run.md).
**SRE task:** Trust that the observability engineer changes the dashboard asked for and leaves
datasources alone.

### ROUTE-007 — re-check routing for the descriptions trimmed on 2026-09-02

**Status:** `active` (2026-10-25); the 20-case automatic-routing baseline completed with
12 PASS, seven FAIL and one INCONCLUSIVE. Two small wording candidates were withdrawn
after a 30-attempt paired comparison did not demonstrate improvement. Failures remain open.
**Owner:** The human owner approves the run; a maintainer session writes the missing scenarios and runs them.
**Outcome:** The eight surviving skills whose description clauses `5c5aa742` replaced with short
exclusions (akamai-edge, api-craft, database-reliability, frontend-craft, obs-alerting,
obs-pipeline, pcf-deploy, pcf-ops), plus grafana as the successor to obs-dashboards and obs-analysis
for the consolidated signal skills, each have at least one fire and one not-fire routing
scenario, and all pass once on current main.
**Next action:** Use the [retained failures and comparison](reviews/2026-10-25-followthrough.md#route-007-baseline-and-bounded-repair-comparison)
to choose a further measured remedy; do not repeat unproven wording changes or erase the
original failures. Preserve the explicit-human-only deployment boundary. A separately
instrumented native canary proves user-command expansion on CLI 2.1.310, with all model
tools disabled; it is not automatic-discovery or original-method acceptance evidence.
The former backend-craft is now api-craft. Dashboard design and the application-UI exclusion
target grafana; signal discovery and interpretation target obs-analysis. Historical scenario
IDs remain unchanged; correlation-ID versus trace-ID selection is an internal method contract.
The [current preparation](reviews/2026-10-25-route-007-preparation.md) adds the six valid missing
automatic-routing cases and lists the bounded run selection. The seventh, `pcf-deploy` fire,
requires an explicit-human-invocation measurement because its current skill forbids automatic
invocation; do not change that authority to make discovery pass.
**Evidence:** [Follow-through baseline, comparison and capability canary](reviews/2026-10-25-followthrough.md);
the commit message of `5c5aa742` records the original scenarios as owed.
**SRE task:** An SRE asking for help with Akamai, a database, PCF or observability gets the skill that
owns it, not a neighbour.

### RELIABILITY-001 — measure the timing repair on Claude, then decide on the reliability lane

**Status:** `ready` (2026-10-25); the source repair has landed, but the specified native
helper-return comparison remains unrun. The separate
[WP-10 assessment-document comparison](reviews/2026-10-25-wp10-handoff-repairs.md#reliability-proposals)
measures newer retry guidance on Claude and Codex; it does not replace this profile's acceptance.
- [verified] The 2026-10-08 comparison: candidate `37bf6a6d` and baseline `cecadc1b`, each rebuilt
  byte-identically from its commit, ran one native trial each on `claude-sonnet-5-5` for USD 0.70 in
  all. Both pass the three structural checks.
- [sourced: independent blind trace review] Both arms pass four of the five manual criteria and fail
  the timing criterion the same way: each fixes the retry count at three and treats the 36-second
  sum of timeouts as a bound on elapsed time and slot use.
- [verified] Since then `resilience-analysis` distinguishes retries from attempts and states that a
  timeout sum alone bounds neither elapsed time nor slot occupancy, with a worked contrast between a
  false return and an uncaught exception (`2d0292c1`, 2026-10-15); `f151c276` added overload and
  startup comparison evidence, and the lane loads its method skills before writing (2026-10-10).
- [sourced: independent semantic review] On Luna (Codex), three trials of
  `build-reliability-engineer-proportionate-options` on `f151c276` rejected an unconditional timeout
  or occupancy maximum but failed the rubric: none explained that a false return permits another
  call while an uncaught exception exits immediately
  ([closeout](reviews/2026-10-15-luna-reliability-gcp01.md#final-five-attempt-closeout)).
**Owner:** The human owner approves the run and remains the only acceptor; a maintainer session runs and
reads it.
**Outcome:** One bounded Sonnet comparison shows whether the reliability engineer states timing
without the 36-second bound and keeps the false-return versus exception distinction, against a
control that differs from it only by the timing repair. The owner then accepts the lane, scopes a
further repair, or keeps it shipped and unaccepted.
**Next action:** A maintainer session freezes a main commit as the candidate and builds the control from
it: the same bytes with only the retry-timing text restored to its pre-`2d0292c1` wording (the
retry-timing sentences in `skills/resilience-analysis/SKILL.md` and the two retry passages in its
`references/worked-contrasts.md`), keeping the overload and admission wording, with adapters
regenerated. A `git revert` of `2d0292c1` no longer applies, because `f151c276` rewrote the same
lines, so the control is a hand diff pushed to a ref and reviewed. With both commits and plugin
digests recorded, the owner approves that bound pair (about USD 1; one native trial per arm on
`claude-sonnet-5-5`, no retries). A maintainer session then runs both on
[`native-reliability-helper-return-and-resume`](../evals/scenarios/native-reliability-helper-return-and-resume.yaml)
and has the timing criterion graded blind. One sample per arm cannot establish a rate. The 2026-10-08
arms, including the unpublished synthetic baseline `cecadc1b`, the impossible old native case and all
failed observations stay historical evidence.
**Evidence:** [Owner-approved comparison on rebuilt arms](reviews/2026-09-30-backlog-four/reliability.md#owner-approved-comparison-on-rebuilt-arms-2026-10-08),
with the earlier comparison and instrument repair in the same record; the
[lane decision](decisions/2026-09-21-reliability-engineer.md) retains its acceptance scope.
**SRE task:** Turn a service weakness or repeated manual intervention into supported engineering
work with an owner and a meaningful proof-of-improvement check.

## Deferred

### INCIDENT-QUALITY-001 — verify decision quality after the SRE contract repairs

**Status:** `deferred` (2026-10-16); behavioral acceptance failed and stays on hold. The completed
24-session Sonnet campaign failed acceptance. After the helper-scope repair at `c53ed2b6`, one fresh
sample completed the native return/resume sequence but failed semantic criteria 4 and 6; the other
stopped before resume. Later source merges are not a fresh behavioral verdict.
**Owner:** Maintainers select the exact candidate and evaluation budget; a maintainer session owns
the bounded follow-up.
**Outcome:** The advisor loads relevant guidance, dispatches a bounded helper, reconciles its
return, and advances without invented causes, timing, or current-state claims.
**Next action:** None. Reopens when the owner scopes a repair for unsupported stage, timing and
escalation conclusions and exact file resolution, with a fresh bounded campaign on a named
candidate. Preserve actual return/resume and sufficient-evidence recovery as regressions. As of
2026-10-18, 101 commits on main have touched `incident-investigation` or `sre-assistant` since
2026-09-07, so reopening starts with a fresh bounded baseline on current main before any repair;
the September failures are not assumed to persist or to be fixed.
**Evidence:** none current. The September 2026 campaign records (selected-improvement record,
second pass, symptom-guidance and first-repair baselines, task-sized outputs, helper exchange, and
the operational-contract report used by merged PR #237) were removed on 2026-11-02 and remain at the
[pre-removal snapshot](https://github.com/latent-sre/save-toolkit/tree/7ac287d518df1f5b8c9397642a8204b0909ca2ac/docs/reviews); their results apply only to the snapshots they name.
**SRE task:** Get a useful next check or closeout without mistaking a helper's completed assignment
or an untimed aggregate for evidence of incident recovery or cause.

### COPILOT-HARNESS-001 — decide fleet delegation on the default Copilot harness

**Status:** `active` (2026-11-12). The owner selected verified native Copilot delegation before
release. The existing `agents:` and `handoffs:` fields do not apply to the default harness;
a native projection and installed acceptance remain to implement. Current converter/SDK research
has not identified an enforceable per-parent delegation-target restriction.
**Owner:** The human owner decides; a maintainer session owns the generator and lane text.
**Outcome:** The fleet states how delegation works on the default Copilot harness, its lanes do not
depend on a Local-only field there, and acceptance cases exist for the chosen harness.
**Next action:** Establish a host-enforced target restriction before changing the projection;
ignored Local fields and timeout-sensitive hooks do not establish the selected contract. Then prove
allowed/forbidden child invocation and parent continuation on an
installed default-Copilot session. Confirm browser tool names and `AGENTS.md` delivery separately.
[Selected scope and current conversion seam](reviews/2026-11-12-release-001-preparation.md).
**Evidence:** [VS Code agent harnesses](https://code.visualstudio.com/docs/agents/run/agent-harnesses).
**SRE task:** Use the fleet's delegating lanes from a default Copilot session, knowing which handoffs
work there.

### PCF-DEPLOY-001 — give pcf-deploy an Apps Manager path for SREs without the cf CLI

**Status:** `deferred` (2026-11-08); the owner deferred this from the skill review.
**Owner:** Save Toolkit maintainers; a maintainer session owns the skill text.
**Outcome:** Where Apps Manager offers an equivalent, `pcf-deploy` plans state that path beside the
`cf` command, and name the steps that still need the CLI.
**Next action:** None until the owner schedules it. Then confirm which steps Apps Manager supports
on the team's foundation version before writing them. Also confirm whether Apps Manager has an
Events view: `pcf-ops` and `helper-exchange.md` send responders to one, and Broadcom's page may
not list it.
**Evidence:** none yet.
**SRE task:** Plan and verify a PCF change from Apps Manager when the `cf` CLI is not installed.

### GRAPH-007 — promote or retire the sandbox workflow-graph skill

**Status:** `deferred` (2026-10-17); the owner deferred the promote-or-retire decision.
**Owner:** Save Toolkit maintainers; a maintainer session owns the skill text if promoted.
**Outcome:** Portable executable workflow/state-graph design either ships as a reviewed, routed
skill or is retired. Until then `agent-authoring` claims only the fleet's own agent workflow graph,
and a team service's workflow graph routes to `principal-engineer`.
**Next action:** None. Reopens when the owner takes the decision: promote
`sandbox/workflow-graph-engineering/SKILL.md` into `skills/` with routing scenarios and a
listing-size check, given ROUTE-003's inconclusive workflow-graph discovery measurements, or
remove it.
**SRE task:** Get a design for a durable workflow graph from the lane that can actually back it.

### EVAL-015 — compare library judge prompts with the incumbent judge

**Status:** `deferred` (2026-10-07); split from EVAL-010 action 4 when EVAL-010 closed.
**Owner:** Maintainers approve the comparison's budget, any new dependency and its credential;
a maintainer session runs it as EVAL-012 WP-03 under DEC-05.
**Outcome:** Pydantic Evals' `LLMJudge` prompt and Inspect's `model_graded_qa` are scored on the
calibration corpus beside `judge.py`'s prompt; one is adopted only if it beats `judge.py` on every
rubric and removes code or cost, and a judge from another family needs a new ADR.
**Next action:** None until the owner approves the budget, the Pydantic Evals dependency and the
widened scope of any key it uses. As of 2026-10-18 Inspect is already
pinned (`inspect-ai==0.3.263`, with `evals/inspect_pilot.py`), so only Pydantic Evals would be a new
dependency, and WP-08's OpenRouter key could serve if its scope is widened. The bake-off already chose
the incumbent judge's model, semantic grading of GCP and natural-injection answers now uses blind
reviewers, and 16 scenarios use the rubric judge. Reuse the bake-off's `codex exec` method and corpus
traps rather than re-surveying OpenAI Evals, DeepEval or OpenEvals, which it left out.
**Evidence:** [Judge bake-off, 2026-10-03](reviews/2026-10-03-judge-bakeoff.md).
**SRE task:** Trust an agent's graded mitigation advice because the cheapest judge that matched the
human labels graded it.

### EFFECT-001 — effect-bound execution broker

**Status:** `deferred`
**Owner:** Save Toolkit maintainers
**Outcome:** If protected automation is ever allowed to perform a live effect, approval is bound to
one exact action, target, argv/executable digest, expiry, nonce, rollback, and replay ledger.
**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority. Reopens only when a named workflow is approved
to cross the current prepare/recommend boundary with a separately controlled execution identity.
**Evidence:** none yet
**SRE task:** An SRE approving a live automated action gets one exact, bound, revocable approval —
target, argv/executable digest, expiry, rollback — instead of an open-ended execution grant.

### BRANCH-001 — author the six GCP branching investigations

**Status:** `deferred` (2026-10-18); moved out of WP-13 by the owner. Reopens when WP-05's incident
conversations are planned or a skill change needs a re-reasoning measure.
**Owner:** A maintainer session authors; the human owner accepts the cases.
**Outcome:** Branching versions of GCP-02/05/09/15/17/29 meet AC-26: different checks reveal only
their own observations, equivalent requests reach the same read, unsupported requests return
unavailable, and a correction changes the supported conclusion, as the
[GCP specification](fleet-evaluation/gcp.md#branching-investigations-and-human-use) describes.
**Next action:** None until reopened. The owner's design: the hardened read-catalog fixture with an
alias table; the correction arrives as an observation from a read, because graded cases cannot take a
human second turn; console families use the CLI read catalog; GCP-15 and GCP-29 stay held-out; all
six are authored in one batch with one independent review.
**Evidence:** none yet.
**SRE task:** An agent updates its finding when a later observation contradicts the first story,
instead of defending it.

### HANDOVER-001 — run the two human handover tabletops

**Status:** `deferred` (2026-10-18); detached from WP-13's completion by the owner. Reopens when two
responders and a facilitator are scheduled.
**Owner:** The human owner schedules and facilitates; `scribe` records the boards.
**Outcome:** Two bounded tabletops, a migration/hybrid incident and a GKE identity/reachability
incident, each handing the board to a second responder with read-back of impact, evidence, open
alternatives, owners and next check, and a record of inaccessible instructions, repeated intake, lost
open items and whether work could continue, as the
[GCP specification](fleet-evaluation/gcp.md#branching-investigations-and-human-use) describes;
AC-35's human-handover half.
**Next action:** None until scheduled. The owner names the responders and dates; the facilitator picks
the two cases from the accepted catalog.
The [prepared tabletop packet](fleet-evaluation/handover-tabletops.md) now selects accepted
migration/hybrid and GKE reachability cases, with separate responder handouts and worksheets.
Human execution and usefulness results remain unmeasured.
**Evidence:** [Offline preparation and exact case identities](fleet-evaluation/handover-tabletops.md).
**SRE task:** A responder taking over a board mid-incident continues from the handed-over record
without repeating intake.

## Parked

The item below remains `deferred` (2026-09-03). Reopening requires a named SRE task and owner
decision, then a full seven-field item above. This refresh neither closes it nor authorizes runs.
The [prior roadmap](https://github.com/latent-sre/save-toolkit/blob/ed3210358557415023f33faaaf669315fe79d7ec/docs/fleet-roadmap.md)
retains its historical evidence paths and recovery commands; those measurements do not establish
current behavior. Consumed evaluation profiles remain non-reusable.

| ID | Required decision or evidence before work resumes |
|---|---|
| ROUTE-003 | Decide whether to replace or retire the two inconclusive workflow-graph discovery measurements; do not reuse consumed profiles. |
