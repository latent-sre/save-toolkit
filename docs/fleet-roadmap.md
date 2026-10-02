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

### EVAL-010 — choose the rubric judge by a calibration bake-off

**Status:** `decision-needed` (2026-09-30). This item authorizes no dependency change, model run, or
API spend.
**Owner:** Maintainers approve any new dependency, the API budget, and the credential used;
`agent-engineer` runs the bake-off with independent review.
**Outcome:** The rubric judge is the one that best agrees with the human-labelled calibration corpus
at equal or lower cost. Either `evals/judge.py` stays, or a library judge replaces its model-call
half under a new ADR that amends the judge contract.
**Next action:**

1. Thicken the thinnest calibration sets first. `mitigation_recommendation` and
   `compromise_preserves_evidence` have three labelled cases each (one pass, two fail). At the 0.95
   agreement threshold that means 3/3, which cannot separate two judges. New cases change the corpus
   digest, so the current judge must be recalibrated too.
2. Recalibrate the current judge on the thickened corpus with the repository `.venv` interpreter.
   The execution identity records the Python version, so a receipt made under one interpreter is
   rejected under another.
3. Score the same corpus with the same judge model and rubric text through two candidates:
   - Inspect AI's `model_graded_qa` scorer (already pinned: `inspect-ai==0.3.263` in
     `requirements-dev.txt`);
   - Pydantic Evals' LLM-judge evaluator (`pydantic-evals`, a new dependency with six runtime
     dependencies).

   Report per-rubric agreement, inconclusive judgments, cost, and the lines of `judge.py` each would
   replace.
4. Adopt a candidate only if it matches the current judge on every rubric and removes code or cost.

Limits that hold whichever judge wins:
- Both candidates call a provider API with an API key. The current judge runs `claude -p` in the
  clean room on subscription authentication.
- Structural checks stay deterministic in `evals/graders.py`; a library takes only the rubric half.
- Few-shot examples inside a library's judge prompt are not calibration evidence.

Surveyed on 2026-09-30 and left out of the comparison:
- OpenAI Evals (`evals`): last PyPI release two years ago, and OpenAI-centric.
- DeepEval: 15 runtime dependencies, including an analytics client. Whether its telemetry is on by
  default is unconfirmed.
- OpenEvals: requires `langchain`, `langchain-openai`, and `langsmith`. Reconsider it only for
  LLM-judged agent tool-call trajectories, which the build probes grade deterministically today.

**Evidence:** [Judge contract](decisions/2026-09-01-rubric-judge-evaluation-contract.md).
- The last accepted calibration receipt (2026-09-23, `claude-sonnet-5`) covers 164 labelled cases
  across eleven rubrics. Every rubric was at or above 0.95 agreement; the run made 19 live calls for
  USD 0.51.
- That receipt still binds on `65daa521` under the `.venv` Python 3.14.7, and is rejected under
  3.12.10.
- Sixteen scenarios carry rubric checks.
**SRE task:** Trust an agent's mitigation recommendation or suspected-compromise escalation because a
judge proven against human-labelled cases graded it, not because its scenario went unrun.

### PRECOMMIT-001 — decide whether software-engineer always gets a review before committing

**Status:** `blocked` (2026-10-01) on PR #294, which rewrites the same software-engineer sections.
**Owner:** The human owner decides; `agent-engineer` owns the software-engineer change and its eval.
**Outcome:** software-engineer's review trigger matches the owner's choice (on request, security, and
production deploy as today; always before commit; or non-trivial changes only), with a build scenario
proving it.
**Next action:** After #294 merges, the owner chooses the trigger; then change the one software-engineer
rule, its pinned contract test, and measure with
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
