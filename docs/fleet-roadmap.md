# Fleet roadmap

> **Status: live; working update 2026-09-30, integrated with `65daa521`.** This is the only backlog.
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

### AUDIT-001 — review all skills and agents and disposition the findings

**Status:** `decision-needed` (2026-10-02); all 13 groups reviewed, covering 30 skills and 9 agents
with six passes each against freshly fetched main `a2d2e57d`. The evidence records 50 confirmed
findings; thirty-eight selected repairs were implemented and locally verified, with no open material
independent review findings. Reference cleanup additionally corrects II-01 in source, bringing
source repairs to 39 of 50; its supplied-case/grader calibration and native/model verification
remain open. The remaining 11 source findings retain their original dispositions.
**Owner:** The human owner selects repairs and dispositions; the audit caller owns the review evidence.
**Outcome:** All 30 skills, then all 9 agents, receive six documented review passes in groups of
three, with each group's findings committed before the next group, and the owner can select
evidence-backed repairs, recommendations, or explicit deferrals.
**Next action:** The human owner reviews the published repairs and their verification limits,
then selects remaining repairs or explicit dispositions and the real inventory-record location.
[Earlier repair evidence](reviews/2026-10-02-fleet-audit/selected-fixes.md) and
[third](reviews/2026-10-02-fleet-audit/selected-fixes-batch-03.md) and
[fourth-batch evidence](reviews/2026-10-02-fleet-audit/selected-fixes-batch-04.md) retain exact
implementation identities. Latest full-suite verification passed 1,711 tests and 3,192 subtests,
with 19 skips. Live calibration
of the edited judge corpus and target-platform acceptance remain separately scoped.
**Evidence:** [Six-pass audit and group reports](reviews/2026-10-02-fleet-audit/README.md).
Retain this packet until the owner's dispositions and any accepted repairs no longer depend on it.
The read-only necessity and context-cost audit of all 103 bundled references on the repaired
candidate is complete: six lenses in groups of three skill bundles, each committed before the
next group. Its [action register](reviews/2026-10-02-reference-audit/recommendations.md) records
74 KEEP, 26 TRIM, one paired MERGE and two CONDITIONAL inventories. Forty records comprise two
documentation correctness defects, seven navigation-convention records, 30 optional recommendations
and one shared ownership decision. The 39 actionable reference records are implemented; the
[implementation receipt](reviews/2026-10-02-reference-audit/implementation.md) tracks its changes
and fresh verification. The inventory-location decision remains pending. REF-II-01 repairs the
original II-01 source defect; the other 11 original source findings remain separate.
**SRE task:** Identify which guidance is correct and useful, which claims lack verification, and
the smallest changes needed before relying on affected workflows.

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

### RELIABILITY-001 — accept the reliability engineering lane on representative tasks

**Status:** `active` (2026-09-30); bounded comparison completed; corrected native acceptance pending.
**Owner:** Maintainers select the exact candidate and bounded evaluation budget; `agent-engineer`
owns the lane and methods.
**Outcome:** The reliability engineer discovers supported service risks, recognizes effective
controls, designs proportionate improvements, and evaluates toil without fabricated benefit or
expanded authority.
**Next action:** Resolve the pending bounded native comparison for reviewed candidate `37bf6a6d`
against the matched current-main guidance baseline, retaining the native instrument repair.
The original twelve trials plus two separately approved corrected native trials are consumed
(USD 2.06 reported cost). The format repair passed two source samples; corrected native arms both
completed helper return/resume, but the repaired arm claimed a reread absent from its trace and both
arms had retry/deadline reasoning defects. Do not promote from structural PASS. The next source
candidate clarifies actual-access provenance and conditional timing semantics, including in the
loaded skill entrypoint; independent source review, offline asset and scenario checks pass, but no
model has exercised it. The requested two-trial, USD 3 decision is pending; no additional call is
authorized. Preserve the impossible old native case
and all failed observations as historical evidence.
**Evidence:** [Current comparison and instrument repair](reviews/2026-09-30-backlog-four/reliability.md);
the [lane decision](decisions/2026-09-21-reliability-engineer.md) retains its acceptance scope.
**SRE task:** Turn a service weakness or repeated manual intervention into supported engineering
work with an owner and a meaningful proof-of-improvement check.

### PRINCIPAL-001 — accept the principal engineering lane on representative design tasks

**Status:** `active` (2026-10-05); lane implemented at the owner's request; nine native campaigns
complete (108 Sonnet trials). On each case's latest bytes the lane passes every case it owns except
one: the new-system case fails 0/3 on a new `obs-alerting` load check, which `software-engineer`
also never meets. Platform selection reaches the lane 3/3 and passes its build case 3/3. The lane
has taken none of the reliability, small-build, design-review or fleet workflow-graph requests in
the boundary cases. On identical bytes `software-engineer` returned the same decision fields on both
design tasks:
- On the contract-change task, on the two revisions where both arms ran, the lane wrote the
  complete design record in 6/6 trials; `software-engineer` did once in 6, when it read the
  reference.
- On the new-system task, whose prompt names the record, `software-engineer` matched it on every
  scored check, 6/6.

Owner acceptance pending.
**Owner:** Maintainers select the exact candidate and approve the evaluation budget;
`agent-engineer` owns the lane and its `eng-ladder` method.
**Outcome:** The principal engineer returns design records that name supported and unseen
consumers, plan compatible staged rollout and recovery, shape new systems against the stack
profile, and leave every decision to the human owner without expanded authority. One lane is shown
to serve both design depths, or the owner splits or removes it.
**Next action:** The owner and one teammate complete the agent-picker sheet. The owner then
decides acceptance of the exact candidate, weighing the lane's consistent record, design-only
boundary and picker entry against keeping the stronger `eng-ladder` reference alone.

Open choices:
- a judged case for endpoint lifecycle, failure handling, and whether a proposed observation can
  produce the evidence its gate needs;
- a re-run that swaps the "design document" and "design record" wording;
- the alerting rule: reword it in the form that worked for `database-reliability` and re-run the
  lane's new-system case, or withdraw the rule and its check;
- re-measuring the design-review boundary once `EVAL-014` keeps routing trials out of the
  measured checkout;
- the combined versus principal-only and architect-only comparison, which the picker sheet decides.

Each further campaign states trial count, estimated cost, review hours and cost cap under DEC-04
before any call.
**Evidence:** [Native evaluation](reviews/2026-10-05-principal-engineer-evals.md); the
[lane decision](decisions/2026-10-05-principal-engineer.md) keeps its acceptance scope.
**SRE task:** Get a reviewable design or architecture record, with options, staged rollout and
recovery, and the decisions to make, before code is written.

### RELEASE-001 — make the toolkit installable as an immutable, rollback-tested release

**Status:** `active` (2026-09-20).
**Owner:** Maintainers accept the release; `agent-engineer` owns the plugin contract and
`software-engineer` owns helper/adapter repairs.
**Outcome:** An SRE installs a pinned artifact rather than whatever `main` holds, and can roll back
to a previously accepted one. The [acceptance cases](vscode-plugin-acceptance.md) pass on those
exact shipping bytes, which the 2026-09-10 local-install run did not exercise.
**Next action:** Run the new Format acceptance case first: the plugin now declares Agent Plugins
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
**Evidence:** The 2026-09-10 VS Code 1.137.0 acceptance row in the host-support table of
[`README.md`](../README.md); HOST-002's closure commit records the owner disposition.
**SRE task:** Install a named version of the toolkit, and go back to the previous one if it regresses.

### INCIDENT-QUALITY-001 — verify decision quality after the SRE contract repairs

**Status:** `decision-needed` (2026-09-07); behavioral acceptance remains on hold.
**Owner:** Maintainers select the exact candidate and evaluation budget; `agent-engineer` owns
the bounded follow-up.
**Outcome:** The advisor loads relevant guidance, dispatches a bounded helper, reconciles its
return, and advances without invented causes, timing, or current-state claims.
**Next action:** Address unsupported stage/timing/escalation conclusions and exact file resolution
before the next bounded candidate. The helper-scope repair at `c53ed2b6` used one helper in both
fresh samples; one completed the actual native return/resume sequence but failed semantic criteria
4 and 6. The second read the fixture then tried an unnecessary missing path, stopping before resume.
Preserve these failures; neither the source repair nor structural PASS establishes acceptance. See the
[selected-improvement record](reviews/2026-09-07-selected-sre-improvements.md).
The completed 24-session Sonnet campaign failed behavioral acceptance; later source merges are not
a fresh behavioral verdict. Preserve actual return/resume and sufficient-evidence recovery as
regressions. Separate decisions remain for limited Terra comparisons (zero calls; tool absence
unproved and host skills injected), six Sonnet pairs for task-sized outputs, and three pairs for
helper exchanges. These are pending choices, not permission to run them.
**Evidence:** [Second pass](reviews/2026-09-07-incident-quality-second-pass.md), its
[symptom-guidance](reviews/2026-09-06-general-incident-help.md) and
[first-repair](reviews/2026-09-06-sre-decision-quality-repairs.md) baselines, plus
[task-sized outputs](reviews/2026-09-07-task-sized-skill-outputs.md) and
[helper exchange](reviews/2026-09-07-incident-helper-exchange.md). The
[operational-contract report](reviews/2026-09-04-operational-contract-fixes.md) remains the
record-provenance evidence used by merged PR #237. Results apply to those records' named snapshots.
**SRE task:** Get a useful next check or closeout without mistaking a helper's completed assignment
or an untimed aggregate for evidence of incident recovery or cause.

### SRE-CF-001 — complete protected SRE investigation access

**Status:** `active` (2026-09-21); selected CF reads and authentication without exposing
credentials are wanted. The caller/coverage fixes, selected browser tools and bounded Grafana
read/query helper are implemented; live credential/session binding and native acceptance remain open.
**Owner:** Save Toolkit maintainers.
**Outcome:** Grafana investigation and selected CF application observations work on
Claude Code and VS Code/Copilot under an agreed, verified access policy, reusing existing SSO/session
access first and supporting personal-account authentication when needed without exposing credentials
to the LLM. Deployment actions, other production mutations, and credential-bearing diagnostic reads
remain excluded.
**Next action:** Configure the bundled Grafana helper through a human-controlled credential launcher,
bind the operations-repository path, and verify one complete dashboard investigation with its controls.
Identify the existing SSO/browser/CLI session and credential mechanism, including protected personal
credentials where needed. Complete CF target/output/time bounds, browser runtime verification and an
isolated analysis path only with their matching controls. Use the
[expanded host acceptance cases](vscode-plugin-acceptance.md#expanded-investigation-acceptance-pending)
for both hosts. The source update adds selected browser interactions and one installed helper grant,
not general HTTP, script, page-code or standard Copilot terminal access;
Helix/BigQuery remains an unconnected placeholder. INCIDENT-QUALITY-001 retains behavioral acceptance.
**Evidence:** [Planning context beside the agent](../agents/README.txt);
[current canonical profile](../agents/sre-assistant.md), [caller](../skills/incident-investigation/SKILL.md),
[guard source](../scripts/readonly-guard.py), and supplied-state regression fixtures under `evals/scenarios/`.
Source and offline checks do not establish native acceptance of the access policy.
**SRE task:** Delegate a scoped application-state or event-history check while investigating another
part of the incident, without delegating deployment or remediation authority.

### CONTEXT-001 — establish a generalized SRE operational-context contract

**Status:** `active` (2026-09-07).
**Owner:** Maintainers accept the generic alpha; `agent-engineer` owns consumer requirements and
`software-engineer` owns producer/resolver implementation.
**Outcome:** Explicit team, service, environment, and deployment selectors produce the smallest
schema-valid context projection. Missing or ambiguous context fails closed and grants no authority.
**Next action:** Obtain the owner's selected critical service, environment, and approved record
location, then prepare the smallest real-service slice through the existing contract. The newer
producer passes the current consumer's fixture requirements; it still prohibits operational data
and action selection. Verify real-service navigation, freshness/missing records, ownership, and
handoff before claiming usability. Do not replay the old consumer patch as proof of current coverage.
**Evidence:** Refreshed 2026-09-07 in the
[selected-improvement record](reviews/2026-09-07-selected-sre-improvements.md); the
[accepted scope](decisions/2026-08-24-sre-operational-context-contract.md) governs acceptance:

- [verified] Local source at `0450ea58`: the [consumer sidecar](../skills/service-lifecycle/context-requirements.yaml)
  declares `v1alpha2`; the current authority-path checks are in the [asset test](../scripts/test_skill_assets.py).
- [verified] Local producer branch `work/context-001-lifecycle-review` at `be29c942` is seven
  commits ahead of refreshed producer main `903ac830`; its mirror is `v1alpha2`, superseding the old
  `458f39c` compatibility assessment. Its 86 offline tests and an explicit fixture resolve against
  this consumer passed. The all-state PR query for the newer branch returned none.
- [unverified] No real service has been selected or made operational through that fixture-only
  producer. Compatibility, producer merge, service onboarding, and live usability are distinct claims.

**SRE task:** State team, service, environment, and deployment once instead of repeating context.

### SKILL-001 — make confirmed oversized skills conditional routers

**Status:** `active` (2026-09-07); one skill per slice, probe before routing changes.
**Owner:** Maintainers approve each slice; `agent-engineer` executes.
**Outcome:** Skills load only needed guidance. A component contract outranks the byte screen or
probe; reducing bytes alone does not prove better behavior.
**Next action:** Review the owner-approved incident-investigation repairs and conditional-detail
candidate in [PR #248](https://github.com/latent-sre/save-toolkit/pull/248), recorded in the
[quality round](reviews/2026-09-08-quality-round.md#approved-incident-skill-repairs--2026-09-09).
The core is 7.4% smaller after restoring and clarifying the five opening questions; reference-read
scenarios and example checks are repaired, but fresh judge calibration and paired native behavior
are unverified.
Select their budget before behavioral acceptance. `agent-authoring` remains queued; this slice does
not authorize another skill's cut.
The owner-approved Terra prompt comparison now records supplied source and same-session updates;
opening coverage improved in its single paired sample, while direction-change checkpoint selection
still failed and the candidate inferred a database destination. See the quality round's
[Terra follow-up](reviews/2026-09-08-quality-round.md#terra-source-input-follow-up--2026-09-09).
**Evidence:** [verified] UTF-8/LF entrypoint sizes at `ed321035`, measured 2026-09-07. Six exceed
the existing 7,800-byte screen (the old list of three is obsolete):

| Skill | Bytes |
|---|---:|
| [incident-investigation](../skills/incident-investigation/SKILL.md) | 16,904 |
| [agent-authoring](../skills/agent-authoring/SKILL.md) | 9,392 |
| [service-lifecycle](../skills/service-lifecycle/SKILL.md) | 8,639 |
| [pcf-deploy](../skills/pcf-deploy/SKILL.md) | 8,635 |
| [gcp-ops](../skills/gcp-ops/SKILL.md) | 8,187 |
| [runbook](../skills/runbook/SKILL.md) | 7,845 |

**SRE task:** Get the needed guidance with less irrelevant context and response delay.

### LIFECYCLE-001 — a service record stays true for the whole service life

**Status:** `blocked` (2026-09-30); consumer/producer repairs verified and independently reviewed;
real-service records are unavailable for operational acceptance.
**Owner:** Save Toolkit maintainers.
**Outcome:** Change, remediation, refresh, and retirement each have an owner who keeps the service
record current or visibly marks it stale.
**Next action:** Review and integrate both exact candidates: this consumer and the separate
`sre-context` candidate `3433f98e` on `work/lifecycle-001-status-projection`, based on `be29c942` (seven unmerged
prerequisite commits ahead of refreshed producer main `903ac830`). The producer now projects
service/deployment lifecycle and owners through immutable `v1alpha6`; the consumer rejects missing
service lifecycle/owner fields. Then use the owner's selected service, environment and record
repository to verify change, remediation, refresh and retirement ownership/readback. The owner has
confirmed that no such records are currently available; resume that acceptance when they exist.
Catalog dates do not establish execution-backed `last_verified`; fixture-only resolution grants
no live authority.
**Evidence:** [Consumer/producer tests and remaining acceptance](reviews/2026-09-30-backlog-four/lifecycle.md)
and [lifecycle requirements](../skills/service-lifecycle/context-requirements.yaml).
**SRE task:** Know whether a service record still applies to the deployment being operated.

### QUALITY-001 — close the remaining platform and observability quality findings

**Status:** `decision-needed` (2026-09-08).
**Owner:** Maintainers decide whether and when to run the batch; `agent-engineer` executes with
independent review.
**Outcome:** The fifteen platform and observability P2 findings from the 2026-09-08 quality round are
fixed at source with their primary sources cited, or dispositioned, and the touched skills are
re-measured against the round's iteration-1 baseline on Sonnet and Opus.
**Next action:** Owner selects the batch (first two by behavioural evidence: the pcf-ops startup
health-check timeout crash loop and the obs-alerting Splunk scheduled-alert window), then the same
method as the merged batches: reconfirm each finding at source, implement from exact specs, review,
after-run. No model run is authorized by this item.
**Evidence:** [Quality round record](reviews/2026-09-08-quality-round.md) (analysis counts, the two
behaviourally confirmed misses, and the open list); the lane reports are private under
`.eval-runs/quality-20260908/analysis/`.
**SRE task:** Get correct first checks for a PCF crash loop, a Splunk alert window, a Cloud Run 429, an
Akamai purge, and a Wavefront alert from the skills instead of from memory.

### GRAPH-004 — use the fleet knowledge atlas for change impact and investigation guidance

**Status:** `decision-needed` (2026-09-30); both workflows implemented; expanded compatibility
comparison independently approved; exact-candidate human acceptance pending.
**Owner:** Save Toolkit maintainers; the implementing lane owns the atlas and `agent-engineer` its consumer guidance.
**Outcome:** An SRE can trace affected fleet guidance and verification before a change, or find
relevant canonical guidance during an investigation, with bounded, current, cited results.
**Next action:** Obtain human acceptance of the exact integrated candidate for both workflows and
its independently reviewed compatibility corrections.
Runtime `c9fb5bf7` passes the full suite and all seven real-tree atlas checks. The comparison captures
35 actual CLI cases per version; 2,161 individually justified proposals match with zero unexpected
or unused exceptions. Preserve exact donor `21dc443b` from closed-unmerged PR #205 and the failed
intermediate observations. First-adoption consumer stop/resume is verified; generated navigation
cannot establish live service state, and measured compatibility does not promote the candidate.
**Evidence:** [Recovered donor, selected uses and acceptance matrix](reviews/2026-09-30-backlog-four/graph-004.md).
**SRE task:** Find the right operational guidance and understand the recorded consequences of changing it.

### GRAPH-006 — complete the typed atlas prerequisite for GRAPH-004

**Status:** `decision-needed` (2026-09-30); typed pipeline and regression requirements implemented;
compatibility disposition independently approved; GRAPH-004 human acceptance pending.
**Owner:** Save Toolkit maintainers; implementing lane owns the typed extraction/verification pipeline.
**Outcome:** One selector-safe typed pipeline and shared artifact verifier serve build, check and
query, preserving donor semantics with explicit reviewed corrections and reversible v2 output.
**Next action:** Obtain the same exact-candidate human acceptance as GRAPH-004.
The recovered revision-2 design's thirteen requirements and seventeen named regressions have
mapped evidence, including typed proof replay, bounded projections, source-history checks,
semantic comparison and a real-tree CI contract. Retain the measured limits and rollback scope;
offline test results do not establish human acceptance or live operational truth.
**Evidence:** [Design recovery and compatibility contract](reviews/2026-09-30-backlog-four/graph-004.md).
**SRE task:** Trust atlas citations, ownership, freshness and missing-result distinctions while navigating guidance.

### EVAL-012 — plan incident and coding evaluations for the fleet

**Status:** `active` (2026-10-06); WP-00 is complete: the owner accepted specification revision 0.6
on 2026-10-06 as the scope freeze. It records the WP-00 review and the owner's
2026-10-06 decisions DEC-21 to DEC-24: result rules from the accepted threat-model ADR (EVAL-011), a
v1 result record written by the runner, native runs under the owner's everyday account with
inherited folder permissions, and the Coder Eval assessment postponed to WP-15 after the first useful
comparison. It adds the first [run plan](fleet-evaluation/run-plan-wp02-native-readiness.md).
Revision 0.5 recorded DEC-01, DEC-02, DEC-04, DEC-10, DEC-11 and DEC-17 to DEC-20 on 2026-10-05.
Implementation has not started.
**Owner:** Human owner accepts scope, run conditions and exact candidates; `agent-engineer` owns
scenario/measurement design; implementation and lab owners are assigned per delivery package.
**Outcome:** A reviewable evaluation specification covers ITBench-Lite, SREGym, repository repair,
test generation, selected terminal tasks, GCP managed-service/migration and GKE evaluations, actual
fleet integration, Coder Eval runner assessment and later Microsoft AIOpsLab, with traceable evidence,
acceptance tests, delivery phases and explicit open decisions.
**Next action:** EVAL-011's runner sequence lands, including the v1 record, under the accepted
[specification](fleet-evaluation/README.md); WP-01 builds the
minimal comparison over v1 records against a committed synthetic bundle; and WP-02 runs under its
run plan, whose budget the owner approved on 2026-10-06 with a USD 20 cap. WP-12's GCP case design can proceed alongside. The
[Coder Eval experiment](fleet-evaluation/coder-eval.md) waits for WP-15. The owner granted the everyday
account read access to the older run folders on 2026-10-06; all 1,562 now open from it. EVAL-010
retains judge-adoption ownership and EVAL-011 the native measurement contract. This planning item
authorizes no model spend, lab provisioning or production changes.
**Evidence:** [Requirements and specifications](fleet-evaluation/README.md), based on the owner's
2026-10-03 scope decisions and 2026-10-04 approved addition; integration and behavioral results remain unverified.
**SRE task:** Compare exact agent candidates on realistic incidents and engineering tasks, see what
improved or regressed, and distinguish failed behavior from an instrument that could not measure.

### EVAL-011 — bring the eval runner into line with the accepted threat model

**Status:** `active` (2026-10-06); the owner accepted the threat-model ADR on 2026-10-06, with result
rules added from the EVAL-012 WP-00 review. The runner changes below are implemented on
`work/eval-012-wp00-eval-011-runner`, one branch and one PR with EVAL-012 WP-00, awaiting review.
**Owner:** Save Toolkit maintainers review each runner change; `agent-engineer` owns the runner repairs
with independent review.
**Outcome:** The runner meets the accepted [threat-model ADR](decisions/2026-10-03-eval-harness-threat-model.md),
including its result rules. Measurement failures are inconclusive and never hide a supported failure,
and results record the runner revision, CLI version and host platform. Every in-scope defect from the
2026-10-03 inventory of `evals/build_probe.py` is fixed or has an owner disposition.
**Next action:** Maintainers review the one PR. Every runner edit changes the scenario digest, so the
changes landed as one sequence, each gated by rescoring saved runs with the base and candidate
runners (`--rescore`, `--rescore-diff`) and explaining every difference in its commit message. After
merge, record the frozen runner revision before EVAL-012 records comparison baselines. Implemented:
- The comparison: `--rescore` grades saved runs into a new directory without writing them;
  `--rescore-diff` lists every verdict that differs between two rescores.
- Result rules: three-state checks, each check type classed as forbidding or requiring; forbidding
  checks evaluated on runs cut short; a supported failure wins; cleanup failures recorded beside the
  verdict; a requested `--threshold` cannot lower a scenario that has a forbidding check.
- Grading machinery, in process: a grader crash is inconclusive and stops its scenario; an unknown
  grader is rejected at validation. Rescoring all 85 saved campaigns (1,317 runs) found no grader
  crash on real candidate output.
- Turn limits: an optional `max_turns` reaches the CLI as `--max-turns`, and stopping there is a
  completed run; the wall clock and the native spend cap remain instrument guards.
- Attempts and cost: replaced and incomplete attempts are kept; an authentication failure exits 4
  and stops the batch; unknown trial and judge cost stays null; `--max-batch-usd` stops scheduling
  (EVAL-012 AC-18).
- Identity: the runner revision is recorded; trials from different CLI versions or hosts never
  pool; the PowerShell guard hook is in the plugin digest.
- Record and folders (EVAL-012 DEC-22 and DEC-23): one
  [v1 record](fleet-evaluation/contracts.md#result-record-v1) per attempt, in run folders that inherit
  the permissions of `.eval-runs/`.
- The unused `--container` mode is removed.

Remaining:
- Oracle protocol: 16 oracles exit 1 to fail, which an uncaught exception also produces, and 7 of
  them run candidate code (operator-cli, obs-burn-rules, pager-webhook, pcf-deploy-job and three
  python-craft), so each needs candidate errors caught as FAIL before a crash can mean INCONCLUSIVE.
- Turn-limit values: no scenario declares one, so a looping candidate still reaches the wall clock.
  Saved runs give turn counts for 105 of 207 current scenarios (per-scenario maximum: median 6,
  90th percentile 20, highest 72); choosing values is the evaluation owner's call.
- Calibration receipts still sum an unpriced judge call as zero. The judge's identity binds
  `judge.py` and `clean_room.py`, so the fix rides with the next owner-triggered recalibration.
- Split `evals/build_probe.py` along its inventory seams with no verdict change, once the 2026-10-03
  inventory (PR #310) supplies them.
**Evidence:** [PR #310](https://github.com/latent-sre/save-toolkit/pull/310); the amended ADR's
Context records the 2026-10-06 source findings behind the result rules.
[PR #321](https://github.com/latent-sre/save-toolkit/pull/321) runs the component tests on four
workers with `PYTHONDONTWRITEBYTECODE=1`, since a `.pyc` written by one worker reads as plugin drift
to another worker's native trial. The intermittent `NativeConversationRunTests` failure (a native
trial INCONCLUSIVE before its first launch) did not reproduce in twelve local four-worker runs; its
cause is unconfirmed, so a recurrence reopens it here.
**SRE task:** Read an eval INCONCLUSIVE as "the instrument could not measure", trust that it never hides
a recorded failure, and know which host and CLI a PASS or FAIL was measured on.

### EVAL-010 — choose the rubric judge by a calibration bake-off

**Status:** `decision-needed` (2026-10-03). A first bake-off ran on subscription judges with owner
approval and found no replacement for the current judge. This item authorizes no dependency change,
API spend, or model call.
**Owner:** Maintainers approve any new dependency, API budget, or credential, trigger each live
calibration or measurement run with its own budget, and own the calibration labels; `agent-engineer`
runs approved measurements with independent review.
**Outcome:** The rubric judge is the one that best agrees with the human-labelled calibration corpus
at equal or lower cost; action 2 decides whether that agreement must hold over repeated uncached
runs. [sourced: owner decision, 2026-10-04] `evals/judge.py` judges with the latest Sonnet: each
calibration requests the `sonnet` alias (the default), its receipt pins the concrete model that
answered, and trials use only that model. When a new Sonnet ships, recalibrate with
`--resolve-identity` before the old model retires, and move the native scenarios' `expected_model`
pins to it. Cached verdicts are keyed by the requested alias. After the alias moves, a calibration
with any live call fails on the model check, and a fully cached one says it did not check. Only
the probe confirms the move; when it reports one, delete `.eval-runs/judge-calibration/judge-cache`
and recalibrate. The code accepts a receipt for any concrete model; calibrating the previous Sonnet
by name is the fallback only while a new one fails calibration. A judge from another family needs a
new ADR that amends the judge contract.
**Next action:**

1. Recalibrate each host after any rubric, corpus, or judge-source change and after each new Sonnet.
   Each recalibration is a live run: the owner triggers it and sets its budget (about 165 calls per
   host on a cold cache), as the 2026-09-01 judge ADR requires. The measuring host holds a passing
   Sonnet 5.5 receipt for the current rubric and corpus bytes (see Evidence); every other host needs
   its own.
2. Decide whether a calibration receipt must come from repeated uncached runs. The 2026-09-23
   receipt's 164/164 included cached PASS verdicts on three cases that live runs judged FAIL. After
   the owner review, the relabelled retry case drew PASS in two of ten judgments, and one of those
   draws failed a live calibration (14/15) until the rubric carried the missing case context.
   Sonnet 5.5's first calibration passed, yet two of the three uncached repeats that followed would
   have failed one: `gate_blocks_action` at 16/17 once, and an inconclusive evidence quote twice.
3. Thicken `mitigation_recommendation` and `compromise_preserves_evidence`. Three cases each cannot
   separate judges, and new cases change the corpus digest, so a recalibration follows.
4. Optional, needs an API key: score Pydantic Evals' `LLMJudge` prompt and Inspect's
   `model_graded_qa` on the same corpus. Adopt one only if it beats `judge.py`'s prompt on every
   rubric and removes code or cost.
5. Decide whether evidence grounding should tolerate punctuation differences. Sonnet 5.5 quoted a
   semicolon as a comma in six of eight judgments of one case. The owner chose to reword that case
   (2026-10-04), so calibration no longer exercises the weakness, but a live response can still
   draw the same INCONCLUSIVE. Relaxing the rule is a judge-contract change that needs an ADR.

[verified] Measured on 2026-10-03: OpenAI judges run without an API key through `codex exec` on a
ChatGPT login, once an output-schema description stops them wrapping evidence in quotation marks.
On first runs, counting contract-valid verdicts only, GPT-6.1 Sol agreed with 161 of 164 labels,
GPT-6 Luna with 159 of 161 and GPT-5.6 Terra with 118 of 119; Luna had 3 and Terra 45 inconclusive
results. None cleared every rubric. [unverified] Luna, at about a twentieth of Sol's list price,
is a candidate second-opinion judge, not a replacement.

Limits that hold whichever judge wins:
- Provider APIs need an API key; the current judge and the `codex exec` arm run on subscription
  logins.
- Structural checks stay deterministic in `evals/graders.py`; a candidate takes only the rubric half.
- Few-shot examples inside a library's judge prompt are not calibration evidence.

Surveyed on 2026-09-30 and left out of the comparison:
- OpenAI Evals (`evals`): last PyPI release two years ago, and OpenAI-centric.
- DeepEval: 15 runtime dependencies, including an analytics client. Whether its telemetry is on by
  default is unconfirmed.
- OpenEvals: requires `langchain`, `langchain-openai`, and `langsmith`. Reconsider it only for
  LLM-judged agent tool-call trajectories, which the build probes grade deterministically today.

**Evidence:** [Judge bake-off, 2026-10-03](reviews/2026-10-03-judge-bakeoff.md); contract in the
[rubric-judge ADR](decisions/2026-09-01-rubric-judge-evaluation-contract.md).
- [verified] Sonnet 5.5 (`claude-sonnet-5-5`, requested as `sonnet`) on `main` at `7dd770e1`:
  receipt `20261004T051704Z`, 165 live calls, USD 2.44 at list price, every rubric at or above 0.95
  (165 cases across eleven rubrics). Three uncached repeats: `gate_blocks_action` 17, 17 and 16 of
  17; `incident_companion_response` 19/20, 20/21 and 20/20 with case #151 inconclusive twice;
  `no_blind_retry_after_unknown` 15/15 each time. Three cases were defective; no label changed:
  - #4: the `human_handover` paragraph lacked the supplied fact that Riley confirmed the flag value,
    and the PASS response itself asserted two facts the scenario never supplied ("the agreed
    recovery window", "the dependency owner is unassigned"). Judges split by strictness: Sonnet 5
    passed it 12 of 12 times, Luna failed it 4 of 4.
  - #46: "a dry-run plan to deploy build 99 after approval" did not say who deploys. Every Claude
    judgment read it as the assistant deploying (FAIL) and every OpenAI judgment as a plan for
    someone else (PASS). It now names the release owner.
  - #151: Sonnet 5.5 quoted a semicolon as a comma in six of eight judgments, which the
    verbatim-evidence rule makes inconclusive.

  On the repaired bytes, receipt `20261004T063536Z` agrees with all 165 labels. Three uncached
  repeats over `incident_companion_response` and `no_inline_deploy_commitment` score 50/50 each.
  A disagreement that splits by judge family or strictness pointed at the case, not the judge, in
  all three.
- Sixteen scenarios carry rubric checks.
**SRE task:** Trust an agent's mitigation recommendation or suspected-compromise escalation because a
judge proven against human-labelled cases graded it, not because its scenario went unrun.

### EVAL-013 — repair the accepted-implementation routing case

**Status:** `ready` (2026-10-05); `discovery-reliability-defers-accepted-implementation` fails 0/3
on main `8d7ecda1` and 0/3 on the principal candidate, with nothing dispatched on either tree. In
two of the candidate trials the session searched the measured checkout before deciding (`EVAL-014`).
**Owner:** `agent-engineer` owns the scenario; maintainers approve any paid re-run.
**Outcome:** The case measures whether accepted implementation work reaches `software-engineer` and
passes on main, or carries an owner disposition.
**Next action:** `agent-engineer` checks whether a routing scenario can seed a fixture. If it can,
seed a minimal checkout worker and its tests so dispatch is the reasonable action; if not, reword the
prompt so it does not depend on code the workspace lacks. Prove the case offline, then re-run three
Sonnet trials on main with the DEC-04 figures stated first.
**Evidence:** [Principal-engineer evaluation, base-state section](reviews/2026-10-05-principal-engineer-evals.md#the-neighbour-red-is-the-base-state).
**SRE task:** Hand over an accepted change and know the routing check truthfully shows whether it
reaches the implementation lane.

### EVAL-014 — keep routing trials out of the measured checkout

**Status:** `ready` (2026-10-06). Routing trials run in an empty repository, yet the plugin root,
the measured checkout, is readable from them.
- Of 38 principal-campaign routing traces, the main session searched the checkout before choosing
  an agent in 6. In 2 of those it read this repository's `evals/` fixtures.
- None of 54 build traces reached the checkout outside `skills/`.

**Owner:** `agent-engineer` owns the runner; maintainers approve any paid re-run.
**Outcome:** A trial can read the plugin's shipped skills but not the rest of the checkout, so a
routing verdict cannot be shaped by the repository's own evals, docs or history.
**Next action:** Find how the plugin root becomes readable to the trial. Then test serving the run
from a staged copy of only the shipped plugin inputs: agents, skills, commands, hooks and
manifests. Prove offline that a trial can no longer list `evals/`. Then re-run the design-review
and accepted-implementation routing cases with the DEC-04 figures stated first.
**Evidence:** [Principal-engineer evaluation, checkout-read section](reviews/2026-10-05-principal-engineer-evals.md#routing-trials-can-read-the-measured-checkout).
**SRE task:** Trust that a routing result reflects the agent descriptions, not files the test
happened to find.

### PRECOMMIT-001 — decide whether software-engineer always gets a review before committing

**Status:** `decision-needed` (2026-10-05). PR #294 closed unmerged; software-engineer keeps preparing
production changes for the human release owner.
**Owner:** The human owner decides; `agent-engineer` owns the software-engineer change and its eval.
**Outcome:** software-engineer's review trigger matches the owner's choice (on request, security, and
production deploy as today; always before commit; or non-trivial changes only), with a build scenario
proving it.
**Next action:** The owner chooses the trigger; then change the one software-engineer rule, its pinned
contract test, and measure with
`build-software-engineer-hands-uncommitted-work-to-reviewer`.
**Evidence:** [`build-software-engineer-hands-uncommitted-work-to-reviewer`](../evals/build-scenarios/build-software-engineer-hands-uncommitted-work-to-reviewer.yaml)
(the handoff works 3/3 when asked; main's reviewer ran code in place 0/3 clean).
**SRE task:** An SRE gets an independent review of agent-written changes before they are committed
without having to ask for it each time.

## Deferred

### REVIEWER-001 — the reviewer reads the history of every changed file

**Status:** `deferred` (2026-10-01).
**Owner:** `agent-engineer`.
**Outcome:** In branch reviews the reviewer runs `log -n 10 <base> -- <each changed path>` before
judging a change, on Sonnet and Opus.
**Next action:** Measure on a fixture whose base history holds a deliberate earlier change the
candidate reverts; the current fixtures have one base commit, so the read finds nothing and its
2/3 Sonnet rate (3/3 Opus) says little about value.
**Evidence:** [`build-reviewer-reproduces-in-scratch`](../evals/build-scenarios/build-reviewer-reproduces-in-scratch.yaml)
(`contract: reads the history of the changed files`).
**SRE task:** A reviewer catches a change that silently undoes deliberate earlier work.

### HANDOFF-002 — restated helper claims keep their labels, and the handoff graders stop false-redding

**Status:** `deferred` (2026-09-30).
**Owner:** Save Toolkit maintainers; `agent-engineer` owns the graders and the label wording.
**Outcome:** An agent that restates a helper's unknown in its report keeps `[UNTRUSTED] [unverified]`
on it, and `agent-direct-handoff-software-engineer-blocks-unapproved` grades blocking without false reds.
**Next action:** Fix the blocks-unapproved graders first: they false-red on a conditional
post-approval plan, on "I changed nothing", and on a field name repeated in prose. Then decide
whether label restatement deserves a body rule: across the seven handoff build probes on 2026-09-30
it landed in 0 to 2 of 3 trials on every arm, including main and the no-handoff controls, so no
current wording carries it.
**Evidence:** [`build-sre-assistant-handles-partial-research`](../evals/build-scenarios/build-sre-assistant-handles-partial-research.yaml)
and its six sibling handoff probes in `evals/build-scenarios/`.
**SRE task:** An SRE reading an agent's report can tell which restated claims came unverified from an
untrusted helper without re-reading the helper's return.

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

### FRESHNESS-001 — review and retire vendor-fact date stamps in skills

**Status:** `deferred` (2026-09-19).
**Owner:** Save Toolkit maintainers.
**Outcome:** The ~60 `reviewed`/`re-checked`/`Sources reviewed` dates across 28 skill files are
triaged: removed where the claim is stable or a file-level header already covers it, kept in one
consistent format where the date bounds reliance on volatile vendor behavior. No inline
`doc-checked` stamps remain anywhere (the two in `agent-authoring` were removed 2026-09-19).
**Next action:** None until an owner confirms scope — all stamps, or volatile-vendor claims only.
The 2026-09-19 inventory grouped every stamp by file and date (freshest: 2026-09-09 Cloud Trace IAM
and `gcp-ops` troubleshooting; oldest: 2026-07-14 ThousandEyes/Grafana); reuse it rather than
re-scanning. Reopens as a single cleanup slice with adapter regeneration and Gate A.
**Evidence:** none yet
**SRE task:** Read skill guidance without stale-looking confirmation dates eroding trust in the
cited vendor facts.

## Parked

All seven items below remain `deferred` (2026-09-03). Reopening requires a named SRE task and owner
decision, then a full seven-field item above. This refresh neither closes them nor authorizes runs.
The [prior roadmap](https://github.com/latent-sre/save-toolkit/blob/ed3210358557415023f33faaaf669315fe79d7ec/docs/fleet-roadmap.md)
retains their historical evidence paths and recovery commands; those measurements do not establish
current behavior. Consumed evaluation profiles remain non-reusable.

| ID | Required decision or evidence before work resumes |
|---|---|
| WF-001 | Prove dispatch of an exact trusted `ship-review` workflow without caller-supplied workflow code. Re-probe only on a material host/contract change. |
| ROUTE-006 | EVAL-009 decides whether the retired observability-to-incident deferral case needs replacement; only then judge the disputed handoff phrasing. |
| ROUTE-003 | Decide whether to replace or retire the two inconclusive workflow-graph discovery measurements; do not reuse consumed profiles. |
| ROUTE-004 | Decide whether the surviving Mantine positive at threshold 1.0 suffices, or needs a replacement calibration case. |
| EVAL-005 | The [dashboard probe](../evals/build-scenarios/build-obs-dashboard-write-honours-the-carve-out.yaml) now seeds real Prometheus data. Remaining proof is a Windows Docker comparison at an approved exact revision: three Sonnet trials per side, no retries. |
| EVAL-007 | Resolve the closure contract for an incident-response verdict based on meaning: a structural or relation-based grader plus a clean guidance-removal counterfactual. |
| EVAL-009 | Reconcile the old fleet-weight/PR #224 prerequisites against current main before authorizing a new corpus baseline and judge calibration. Decide description ownership-map wording and injection-refusal coverage; include the eleven-description routing follow-up. |
