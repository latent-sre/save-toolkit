# Fleet roadmap

> **Status: live; working update 2026-10-10, EVAL-011 closeout in PR #348.** This is the only backlog.
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

### PRINCIPAL-001 — accept the principal engineering lane on representative design tasks

**Status:** `active` (2026-10-08). [sourced] The owner's bar is demonstrably better design judgment
plus consistent usable records, recorded in the [acceptance packet](reviews/2026-10-07-principal-judgment-acceptance.md).
[sourced] The campaign and offline counts in this paragraph are historical receipts retained in
that packet, not fresh verification of this PR head. The approved twelve-attempt diagnostic cost USD 2.351204: eleven
completed and one builder contract attempt was interrupted by OAuth expiration. The revised
principal loaded `obs-alerting` in 3/3 tracker trials and passed all six structural trials, but
document review found material lifecycle, database-alerting, recovery and false-source claims.
The owner-approved source repair has 166 affected tests and 535 subtests passing. A separately
approved twelve-trial comparison of repaired digest `fb2fba9ac780` completed for USD 2.306003,
without interruptions or retries. Principal passed all six structural trials. Author-aware review
found all three principal tracker records address source grounding, current membership,
query-error notification/testing and preservation prerequisites; builder records leave substantive
gaps. [sourced] The [independent familiar-case trace review](reviews/2026-10-08-principal-independent-second-pass.md)
preserved its blind scores through trace reconciliation: the three
strongest tracker designs align with principal, and contract migration is tied without a detected
principal regression. This supports the stronger bar on these familiar cases, not general
superiority or implementation competence. [sourced] The
[held-out receipt and reconciliation](reviews/2026-10-08-principal-heldout-cutover.md)
records completion of the separately approved six-trial live-store cutover
campaign for USD 1.905009 on the same candidate: principal 3/3 structural PASS, builder
0/3. Its independent AI first pass, prompted addendum and trace/unmasking pass are now preserved
verbatim. [sourced] The [independent held-out trace review](reviews/2026-10-08-principal-heldout-independent-second-pass.md)
rates design judgment a tie with material findings in both arms;
principal's repeatable advantage is method and authority consistency, partly due to absent shell
authority. Two builder runs loaded design/database guidance before Write but after forbidden
read-only shell calls; misleading method-check labels must not hide those loads. All three
builder non-execution claims conflict literally with their traces. Across three cases there is
one tracker advantage and two design ties, not established general superiority or an equivalence
proof. [unverified] General superiority and exact-candidate acceptance are not established.
The original stronger acceptance bar remains open; no new trials or agent-source repairs follow
from this evidence update. The [semantic scoring proposal](../evals/proposals/principal-judgment/README.md)
is outside the active catalog until its complete-context labels are reviewed and a separately
approved calibration is accepted. [sourced] The [earlier native evaluation packet](reviews/2026-10-05-principal-engineer-evals.md)
records the lane's implementation at the owner's request and completion of nine earlier native
campaigns (108 Sonnet trials). Within those campaigns, on each case's latest measured bytes the lane
passes every case it owns except
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
**Next action:** Review the [completed held-out reconciliation and bounded follow-up](reviews/2026-10-08-principal-heldout-cutover.md#disposition-and-bounded-follow-up)
alongside the [familiar-case evidence](reviews/2026-10-07-principal-judgment-acceptance.md#independent-ai-review-and-reconciliation-2026-10-08).
Scope a repair proposal for builder adherence/reporting, shared capture/abort reasoning and the
method-check label/predicate mismatch. Keep measured sources and reports frozen; further repair
or measurement needs its own scope/budget. Preserve all campaigns separately, including the
first one's interruption. Any future judgment case must distinguish defensible trade-offs rather
than reward a shared mechanism. The current review cycle is complete; do not rerun it for a pass.
Record consistency alone does not meet the owner's bar. Automated semantic scoring still needs
reviewed labels and a new calibration after other judge/corpus changes settle. Complete the picker
assessment separately. Exact-candidate acceptance remains the owner's decision.

Retain the independent reports while this decision is open: familiar-case
[first pass](reviews/2026-10-08-principal-independent-first-pass.md) and
[trace pass](reviews/2026-10-08-principal-independent-second-pass.md); held-out
[first pass](reviews/2026-10-08-principal-heldout-independent-first-pass.md),
[prompted addendum](reviews/2026-10-08-principal-heldout-independent-addendum.md) and
[trace pass](reviews/2026-10-08-principal-heldout-independent-second-pass.md).

Open choices:
- disposition of the independently reviewed fence/abort, replay and truthful-execution-reporting
  findings; no acceptance or implementation-readiness claim follows from reviewer severity labels;
- live calibration and measurement of the prepared semantic cases for endpoint lifecycle,
  failure handling, history recovery and feasible migration evidence;
- a re-run that swaps the "design document" and "design record" wording;
- whether the 3/3 alert-guidance loads on repaired digest `fb2fba9ac780` suffice for that prerequisite;
  the previous digest's 3/3 and earlier 0/3 remain separate evidence; the written-record check stays;
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
WP-01's comparison, `evals/compare_runs.py`, merged in [PR #333](https://github.com/latent-sre/save-toolkit/pull/333)
(2026-10-08): its synthetic-bundle tests, which cover AC-01, AC-02, AC-17's attempt counts, AC-19
and AC-23, pass on Windows and in Linux CI, and the findings of an independent review and of two
Codex and Copilot review rounds are fixed. Merge `523525430a0fbb71b0e9e3a846fae8e86db90a99` completes WP-01 [verified].
WP-10 preparation (2026-10-08): the [AC-20 inventory](../evals/wider-fleet-inventory.md) names
and fills seven lane controls, the seventh accepting more than one proportionate reliability proposal; [AC-27 agent-side pairs](../evals/oracles/agent-injection/README.md)
now cover six pairs (12 cases), with 24 scripted obeying/resisting outputs and effect/format
mutations. A [natural-response extension](../evals/oracles/natural-injection/README.md) adds
three pairs with local repair/test and fake-wrapper effects; normal prose requires separate human
semantic assessment, so mechanical success alone stays INCONCLUSIVE. The judge-input surface's six
cases are in the active corpus beside `judge.py`'s per-response marker tag, landing with WP-02's
canary before WP-02 starts: they change the runner identity and the corpus, so one owner-approved
cold recalibration (181 cases) precedes WP-02's rubric check and any other rubric trial. These model-free controls do not complete WP-10 or establish candidate behavior. A draft [WP-10 run plan](fleet-evaluation/run-plan-wp10-wider-fleet-adversarial.md)
(2026-10-08, not approved) lists the 27 agent-side cases for after WP-02; none needs the judge.
**Owner:** Human owner accepts scope, run conditions and exact candidates; `agent-engineer` owns
scenario/measurement design; implementation and lab owners are assigned per delivery package.
**Outcome:** A reviewable evaluation specification covers ITBench-Lite, SREGym, repository repair,
test generation, selected terminal tasks, GCP managed-service/migration and GKE evaluations, actual
fleet integration, Coder Eval runner assessment and later Microsoft AIOpsLab, with traceable evidence,
acceptance tests, delivery phases and explicit open decisions.
**Next action:** WP-02 ran on 2026-10-08 under the accepted [specification](fleet-evaluation/README.md),
on the recorded frozen runner identity below, and its
[run record](reviews/2026-10-08-wp02-native-readiness.md) holds the results and remaining gaps:
- [verified] The owner set the operator-CLI turn limit to 40; the other four follow the plan's rule.
  The owner reworded the ambiguous retirement calibration case, and the recalibration agreed 181/181.
- [verified] All 18 trials passed the runner's identity checks, for USD 4.60. The reliability helper,
  operator CLI and canary passed 3/3; platform selection passed 1/3, a drop that follows the CLI
  change, not the runner. The incident helper (skill never loaded) and guarded triage (label checks
  stricter than the contract) failed 0/3.
- [sourced: independent trace review] The original record named eleven gaps. Its dated repair
  sections and the [EVAL-011 closeout](reviews/2026-10-10-eval-011-closeout.md) distinguish the
  repaired measurement gaps from the original observations and remaining host-coverage limits.

On 2026-10-09 the owner accepted the warm calibration receipt as meeting precondition 5, which
completes WP-02. EVAL-011's runner repairs are complete; its
[closeout evidence](reviews/2026-10-10-eval-011-closeout.md) binds the implementation, 1,425-run
comparison and 187-case rubric calibration. WP-12's GCP case design can proceed alongside. The
[Coder Eval experiment](fleet-evaluation/coder-eval.md) waits for WP-15. The owner granted the everyday
account read access to the older run folders on 2026-10-06; all 1,562 now open from it. EVAL-015
holds the deferred judge-replacement comparison. The accepted threat model and EVAL-011 closeout
define the repaired native measurement contract. This planning item
authorizes no model spend, lab provisioning or production changes.

2026-10-09, model-free work toward WP-10 and WP-12:
- WP-10's [readiness record](fleet-evaluation/run-plan-wp10-wider-fleet-adversarial.md#readiness-on-2026-10-09)
  meets preconditions 1 and 4. [verified] Rescoring all 1,401 saved runs with the frozen runner and
  with this branch's runner differs only where three owner-approved scenario changes landed after the
  freeze, and the model-free controls pass on this host once the fake-wrapper tests find their shell's
  utilities on Windows. EVAL-011's 2026-10-10 closeout supplies every case's turn limit and repairs
  PR #334's finding 5 with supervised oracle completion. Exact-case acceptance at the resulting
  digests and the live run's spend cap remain for the owner; these repairs do not complete WP-10.
- WP-12's first pair, GCP-01 startup, is authored as the pilot template: `build-gcp01-startup-{a,b}`
  for `sre-assistant`, with a fixture `gcloud` read wrapper, a hidden
  [expected-outcome record and review contract](../evals/oracles/gcp/README.md), and offline controls
  in `evals/test_gcp_cases.py`. [verified] The variants differ in five application log lines; a
  useful and a plausible-wrong answer both end INCONCLUSIVE pending human review, while a missing log
  read, a change or credential request (including forms the guard denies before the wrapper sees
  them), and a refusal FAIL; each control test fails on its mutant.
  Next: the owner reviews the template, then the other 11 pilot families follow its shape.
**Evidence:** [Requirements and specifications](fleet-evaluation/README.md), based on the owner's
2026-10-03 scope decisions and 2026-10-04 approved addition; integration and behavioral results remain unverified.
**SRE task:** Compare exact agent candidates on realistic incidents and engineering tasks, see what
improved or regressed, and distinguish failed behavior from an instrument that could not measure.

### PRECOMMIT-001 — software-engineer reviews a 3-file change before committing, unasked

**Status:** `active` (2026-10-08). The owner chose the trigger on 2026-10-07: review at 3 or more
changed files unless every change is a nit. software-engineer's Process step 5 carries it, counting
only the files changed for the task. The skip controls hold; the unasked review on a small 3-file
feature mostly does not fire.
**Owner:** The human owner decides the mechanism; `agent-engineer` owns the software-engineer rule and
its scenarios.
**Outcome:** software-engineer dispatches `reviewer` unasked on a 3-file feature in most trials, and
still skips a change below 3 files or one made only of nits, on the current CLI.
**Next action:** The owner chooses: try step 5 as a concrete action ("your next tool call is
`reviewer`"), measured interleaved against the shipped line, or accept the limit and close the item.
Every miss so far counted 3 files and skipped review as "small", whatever the wording.
**Evidence:** Sonnet on CLI 2.1.294, with the scenarios Codex's PR #332 review made exact (the feature
case asserts all three files; both nit controls touch three files):
`build-software-engineer-reviews-nontrivial-change` reviewed 1/3 with #332's original line and 0/3
with each of two rewrites; the three skip controls passed 3/3 each. The shipped line is the original
plus the counting fix and has not been run. Earlier, on CLI 2.1.292 and the previous feature case,
five wordings reviewed in 10 of 15 trials. Runs are private under `.eval-runs/precommit-20261008/`.
**SRE task:** An SRE gets an independent review of agent-written changes before they are committed
without having to ask for it each time.

## Deferred

### RELIABILITY-001 — accept the reliability engineering lane on representative tasks

**Status:** `deferred` (2026-10-08); the owner kept the lane unaccepted after the owner-approved
two-trial comparison.
- [verified] Candidate `37bf6a6d` and baseline `cecadc1b`, each rebuilt byte-identically from its
  commit, ran one native trial on `claude-sonnet-5-5` for USD 0.70 in all. Both pass the three
  structural checks.
- [sourced: independent blind trace review] Both arms pass four of the five manual criteria and
  fail the timing criterion the same way: each fixes the retry count at three and treats the
  36-second sum of timeouts as a bound on elapsed time and slot use.
- [unverified] In this one-sample-per-arm comparison, the candidate's targeted timing correction
  did not change that defect.
**Owner:** Maintainers select the exact candidate and bounded evaluation budget; `agent-engineer`
owns the lane and methods.
**Outcome:** The reliability engineer discovers supported service risks, recognizes effective
controls, designs proportionate improvements, and evaluates toil without fabricated benefit or
expanded authority.
**Next action:** None. Reopens when the owner scopes and approves a source repair for retry-count
ambiguity and timeout sums, with its own bounded comparison; one sample per arm cannot establish a
rate. The reliability lane stays shipped and unaccepted. Preserve the impossible old native case and
all failed observations as historical evidence.
**Evidence:** [Owner-approved comparison on rebuilt arms](reviews/2026-09-30-backlog-four/reliability.md#owner-approved-comparison-on-rebuilt-arms-2026-10-08),
with the earlier comparison and instrument repair in the same record; the
[lane decision](decisions/2026-09-21-reliability-engineer.md) retains its acceptance scope.
**SRE task:** Turn a service weakness or repeated manual intervention into supported engineering
work with an owner and a meaningful proof-of-improvement check.

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

### EVAL-015 — compare library judge prompts with the incumbent judge

**Status:** `deferred` (2026-10-07); split from EVAL-010 action 4 when EVAL-010 closed.
**Owner:** Maintainers approve the comparison's budget, any new dependency and its credential;
`agent-engineer` runs it as EVAL-012 WP-03 under DEC-05.
**Outcome:** Pydantic Evals' `LLMJudge` prompt and Inspect's `model_graded_qa` are scored on the
calibration corpus beside `judge.py`'s prompt; one is adopted only if it beats `judge.py` on every
rubric and removes code or cost, and a judge from another family needs a new ADR.
**Next action:** None until the owner approves the budget and dependency. Each provider API needs a
key; DEC-04's OpenRouter key is the likely one. Reuse the bake-off's `codex exec` method and corpus
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
