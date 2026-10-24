# Fleet roadmap

> **Status: live; working update 2026-10-16, backlog prune.** This is the only backlog.
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

### FLEET-AUDIT-20261023 — audit each agent and skill against its complete contract

**Status:** `decision-needed` (2026-10-24); all 25 findings repaired and locally verified; exact-candidate acceptance and merge disposition remain pending. All 42 agent/skill audit reports are complete: ten agents, thirty shipped skills and two nonshipping surfaces. The ledger records 25 distinct findings (23 shipped, two sandbox); repairs and native/runtime acceptance remain separate.
**Owner:** Human requester accepts dispositions; the current session owns final repairs and verification.
**Outcome:** All ten canonical agents, thirty canonical skill bundles and the two nonshipping skill
surfaces have source-bound reports covering routing, authority, workflow, platform projections,
bundled resources and meaningful test/eval coverage, with actionable findings and explicit gaps.
**Next action:** Human requester accepts or returns the complete repair candidate and decides merge disposition; no original finding remains unrepaired. See [first-batch evidence](reviews/2026-10-23-agent-skill-audit/repairs-first-ten.md), [second-batch evidence](reviews/2026-10-23-agent-skill-audit/repairs-second-ten.md), and [final-batch evidence](reviews/2026-10-23-agent-skill-audit/repairs-final-five.md). Do not promote the sandbox candidate or restore retired Fleet Atlas without a separate owner decision. The original audit is source-bound; repair evidence is tracked in its linked follow-up.
**Evidence:** [Agent and skill audit](reviews/2026-10-23-agent-skill-audit/README.md).
**SRE task:** Select an agent or skill with a clear account of its supported work, boundaries and
remaining reliability gaps.

### SKILLS-001 — reduce unnecessary skill content without lowering standards

**Status:** `ready` (2026-10-24); the audit repairs and pruning merged in #420/#421.
Targeted live evaluations are complete; the resulting retirement-role clarification is ready for
review. Incident investigation remains explicitly excluded.
**Owner:** `agent-engineer` prepares the candidate; the human owner accepts its exact revision.
**Outcome:** Repeated skill instructions and stale guidance are reduced while domain boundaries,
evidence, recovery, authorization and meaningful verification remain intact.
**Next action:** Review the retirement-role clarification and its before/after evidence. Further
pruning needs a separately selected scope; do not include `incident-investigation`. No whole-skill
retirement is selected. Existing behavioral acceptance gaps remain with their current owners.
**Evidence:** [Full skills audit and follow-ups](reviews/2026-10-23-skills-audit.md), including the
[targeted live probes](reviews/2026-10-23-skills-audit.md#targeted-live-probes-and-retirement-role-repair).
The merged pruning contributed 2,718 canonical bytes before correctness additions, preserving the
separate already-merged trims. The new conditional reference adds 191 bytes for the observed role
inference defect; the entrypoint does not grow. Structural, decision, reference-read and manual
semantic results are reported separately; passing fields alone missed the approval-role error.
**SRE task:** Load less repeated guidance and receive task-sized help without losing the checks
that make operational advice and engineering changes trustworthy.

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

### EVAL-012 — plan incident and coding evaluations for the fleet

**Status:** `active` (2026-10-18). The owner accepted [specification](fleet-evaluation/README.md)
revision 0.6 on 2026-10-06 as the scope freeze, amended for WP-13's completion boundary on
2026-10-18. By work package:
- WP-01 complete: `evals/compare_runs.py`, merged in
  [PR #333](https://github.com/latent-sre/save-toolkit/pull/333) at `52352543`.
- WP-02 complete on 2026-10-09: [run record](reviews/2026-10-08-wp02-native-readiness.md); the
  [EVAL-011 closeout](reviews/2026-10-10-eval-011-closeout.md) binds the repaired native
  measurement contract.
- WP-10 in progress: the [first step](reviews/2026-10-10-wp10-first-step.md) and its
  [saved-trace review](reviews/2026-10-15-wp10-saved-trace-review.md) are approved; the
  [Luna continuation](reviews/2026-10-15-luna-reliability-gcp01.md) is complete at run level, with
  exact quotation, the reliability exception-path explanation and GCP-01 B's factual findings open.
- WP-12 complete on 2026-10-17: all 64 GCP cases accepted at `9147ff91`
  ([pilot and template](../evals/oracles/gcp/README.md), [catalog](../evals/oracles/gcp/CATALOG.md)).
- WP-13 complete on 2026-10-18 under its [run plan](fleet-evaluation/run-plan-wp13-gcp-native-pilot.md):
  the [pilot](reviews/2026-10-17-wp13-gcp-pilot-review.md), the
  [stress test](reviews/2026-10-17-wp13-stress-test.md), the
  [hardened comparison](reviews/2026-10-17-wp13-hardened-comparison.md) and the
  [catalog baseline](reviews/2026-10-18-wp13-catalog-baseline.md); branching moved to BRANCH-001.
- WP-15's [Coder Eval experiment](fleet-evaluation/coder-eval.md) waits for the first useful comparison.

**Owner:** The human owner accepts scope, run conditions and exact candidates; `agent-engineer` owns
scenario and measurement design; implementation and lab owners are assigned per delivery package.
**Outcome:** A reviewable evaluation specification covers ITBench-Lite, SREGym, repository repair,
test generation, selected terminal tasks, GCP managed-service/migration and GKE evaluations, actual
fleet integration, Coder Eval runner assessment and later Microsoft AIOpsLab, with traceable evidence,
acceptance tests, delivery phases and explicit open decisions.
**Next action:**
- WP-08: build the adapter and host proxy in the approved
  [run plan](fleet-evaluation/run-plan-wp08-swebench-repair.md), then the model-free smoke, one paid
  trial on the first task, then the other nine Claude tasks; other models follow under their own approvals; WP-09 follows WP-08.
- WP-13: none; complete. Use its cases as a regression check when a skill or agent changes.
  Haiku's inconsistent `gcp-ops` loading limits any skill fix measured on Haiku.
- WP-10: the owner disposes of the bound Luna semantic proposals and names the exact candidate
  revision; any further campaign needs a new bounded scope.
- Before any rubric-graded campaign: one owner-approved judge recalibration, because the clean-room
  auth-failure fix (`1d92654f`) changed the judge identity.
- Runner follow-ups, not blocking: unittest `--option=value` spellings and SHA-spelled Git ranges
  fail their detectors (0/303 and 0/909 in saved traces).

This item authorizes no model spend, lab provisioning or production change.
**Evidence:** [Specification](fleet-evaluation/README.md); per-package records are linked under Status.
Integration and behavioral results remain unverified.
**SRE task:** Compare exact agent candidates on realistic incidents and engineering tasks, see what
improved or regressed, and distinguish failed behavior from an instrument that could not measure.

### FRONTEND-003 — define the team's GUI mix after the first runs of the rewritten skill

**Status:** `active` (2026-10-11). The owner said on 2026-10-11 that the team's GUI work is a mix
of the skill's five archetypes and that the mix is defined after a few runs, not up front; the
rewritten `frontend-craft` therefore weights the archetypes evenly and defers the deep capability
references ([decision](decisions/2026-10-11-frontend-craft-generalized.md)).
**Owner:** The human owner decides the weighting and the first add-on; `agent-engineer` owns the
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
**Owner:** The human owner accepts the candidate; `agent-engineer` owns the skill.
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

### PRECOMMIT-001 — software-engineer reviews a 5-file change before committing, unasked

**Status:** `active` (2026-10-22). The owner raised the threshold from three to five task-changed
files, retaining the nit exemption and explicit-request, finding-reconciliation, security, and
production-review triggers. The Review decision in software-engineer owns their precedence and
counts already-dirty paths the task changes, excluding only unrelated pre-existing work. On
2026-10-22 the two five-file controls dispatched 0/9 across `main`, the trim candidate, and a
rewrite of the rule, while the six over-trigger controls stayed green; the agent quotes the rule in
its report and still does not spawn.
**Owner:** The human owner decides the mechanism; `agent-engineer` owns the software-engineer rule and
its scenarios.
**Outcome:** software-engineer dispatches `reviewer` unasked on a five-file feature, including when
the task edits already-dirty files; it skips a change below five files or made only of nits unless
another review trigger applies.
**Next action:** The owner decides the mechanism; another wording is not a candidate. Since
2026-10-07 every rewrite of the rule has measured at or below 1/3, and the latest three revisions
measured 0/3 each. Anthropic's hooks guidance says the same: a prompt instruction is advisory, and a
`Stop` hook that blocks the turn until a check passes is the enforcement. API-level forcing is not
available (`tool_choice` `any`/`tool` returns 400 on the 5.5 models), and plugin agents ignore
frontmatter `hooks`, so a gate belongs in `hooks/hooks.json`. The options are a `SubagentStop` hook
keyed to `software-engineer`, with a `Stop` twin filtered on `agent_type` for `--agent` sessions, that blocks
the return when the task changed five or more files and no `reviewer` call completed, the caller
dispatching `reviewer` after the return (the caller-ownership pilot's mode), or a recommendation-only
default with the scenario's expectation changed to match. The hook option is designed in
[the review-gate hook ADR](decisions/2026-10-23-review-gate-hook.md): a block-once gate on `Stop`
and `SubagentStop` with a start snapshot, fail-open posture, nine offline red/green cases, and a
paired-eval acceptance bar; it waits on the four owner decisions listed there. The taint defect below needs the same
kind of decision: a structured return field, or a grader that accepts prose. Keep overlapping dirty
paths, nit controls, and explicit-review overrides in the broader acceptance scope.
**Evidence:** 2026-10-22, Sonnet 5.5 (`claude-sonnet-5-5`) on CLI 2.1.309, runs under
`.eval-runs/se-review-20261022/` (labels `candidate-pyshim`, `incumbent-pyshim`, `fix-pyshim`, with a
`python` shim on PATH because this host has no bare `python` and the oracles call it):
`build-software-engineer-reviews-nontrivial-change` and
`build-software-engineer-reviews-task-changes-in-dirty-files` dispatched 0/3 each on `main`
(`fe7eb012`), 0/3 each on the trim candidate `21dcb2f6` (PR #411), and 0/3 each on an unpushed
rewrite (`9e862ae7`) that says exactly five files counts and that a caller who will commit has not
taken review. The reports show the rule was read, not missed: "the change touches five files, which
would normally trigger one" and "that doesn't count as review, so none has happened yet", followed by
no dispatch or a suggestion that the caller arrange one. The same agent and CLI dispatched `reviewer`
3/3 when the prompt asked for a review
(`build-software-engineer-dispatches-review-when-instructions-unchanged`), so the Agent tool works
at this depth and the miss is the unprompted case. The Agent tool's own description in CLI
2.1.306–2.1.309 reads "Delegate review only when you want a read that isn't anchored on yours" and
"When in doubt, don't spawn"; a `--agent` session that holds `Agent(...)` grants receives that same
tool description, and on this account (Max plan) the default variant applies; the CHANGELOG from
2.1.290 to 2.1.309 records no change to that description. Whether that text is
what tilts the decision is not measured. `claude -p --agent` runs the agent as the main thread, so the
eval harness and direct use fire `Stop`, not `SubagentStop`; a gate needs both. A probe on 2.1.309
showed that `Stop` under `-p --agent` carries `agent_type` (the agent's name), that exit 2 blocks the
return and the model continues with the hook's reason, and that the next `Stop` arrives with
`stop_hook_active: true`. The six over-trigger controls (nit, typo, below five, caller owns review, caller owns
review and gate, withholds on auto-loading instructions) passed 3/3 on each arm, except caller owns
review and gate at 6/8 candidate and 7/8 incumbent, where the one miss each is an unscoped `pytest`
run with the scope named in the brief. The same batch found a separate defect:
`build-software-engineer-resumes-after-partial-helper` returned the helper's
`[UNTRUSTED] [unverified]` unknown as prose without labels, 0/3 on each of the three revisions; a
rewrite of the untrusted-input boundary ("keep `[UNTRUSTED]` as received; prefix it to a claim taken
from an untrusted source") changed nothing measurable. Earlier:
[Five-file and caller-ownership pilot](reviews/2026-10-21-caller-ownership-pilot.md),
Sonnet 5.5 on CLI 2.1.307, candidate `07248042`: default review 0/1; report format failed its strict
field check; caller ownership was observed in both build traces. Historical three-file trials,
not acceptance of the five-file rule: Sonnet on CLI
2.1.294, with the scenarios Codex's PR #332 review made exact (the feature
case asserts all three files; both nit controls touch three files):
`build-software-engineer-reviews-nontrivial-change` reviewed 1/3 with #332's original line and 0/3
with each of two rewrites; the three skip controls passed 3/3 each. Every miss counted three files
and skipped review as "small". The original line plus its earlier counting fix was not measured.
Earlier, on CLI 2.1.292 and the previous feature case,
five wordings reviewed in 10 of 15 trials. Runs are private under `.eval-runs/precommit-20261008/`.
**SRE task:** An SRE gets an independent review of agent-written changes before they are committed
without having to ask for it each time.

### EVAL-005 — the observability engineer's Grafana write lands, and only that write

**Status:** `ready` (2026-10-18). The run ran: in all six trials, both arms, the panel was saved
through a preflighted write and the datasource stayed unchanged, but every trial is FAIL under the
all-checks threshold.
**Owner:** The human owner approves each repair run; `agent-engineer` repairs the scenario and runs it.
**Outcome:** [`build-obs-dashboard-write-honours-the-carve-out`](../evals/build-scenarios/build-obs-dashboard-write-honours-the-carve-out.yaml)
fails only on agent behavior: its refusal-wording check accepts the measured correct refusals, and
its post-write query check fails only when the agent's query did not return the persisted panel's
data. The owner has decided whether the missing panel no-data text needs an
`observability-engineer` or `grafana` repair.
**Next action:** `agent-engineer` widens the refusal-wording alternation and proves offline that both
measured refusals pass and a reply that applies the datasource edit still fails; reproduces the
empty post-write Grafana query on the fixture without a model; and reads historical trial 3's
queries against the check. The owner then decides on the no-data text and approves a re-run.
**Evidence:** [run record](reviews/2026-10-18-eval-005-run.md).
**SRE task:** Trust that the observability engineer changes the dashboard asked for and leaves
datasources alone.

### ROUTE-007 — re-check routing for the descriptions trimmed on 2026-09-02

**Status:** `ready` (2026-10-18); the routing re-check EVAL-009 left owed, kept when EVAL-009 closed.
**Owner:** The human owner approves the run; `agent-engineer` writes the missing scenarios and runs them.
**Outcome:** The eight surviving skills whose description clauses `5c5aa742` replaced with short
exclusions (akamai-edge, api-craft, database-reliability, frontend-craft, obs-alerting,
obs-pipeline, pcf-deploy, pcf-ops), plus grafana as the successor to obs-dashboards and obs-analysis
for the consolidated signal skills, each have at least one fire and one not-fire routing
scenario, and all pass once on current main.
**Next action:** `agent-engineer` writes the seven missing scenarios: fire and not-fire for
database-reliability and pcf-ops; not-fire for akamai-edge and obs-alerting; and fire
for pcf-deploy. The former backend-craft is now api-craft, with two fire cases and one not-fire
case defined offline. Dashboard design and the application-UI exclusion now target grafana;
their existing scenario IDs retain the historical names. Signal discovery and interpretation
now target obs-analysis; correlation-ID versus trace-ID selection is an internal method contract.
The owner then approves one run of the completed set. The new API cases, migrated dashboard/signal
routing, and trimmed obs-analysis guidance are not yet measured natively.
**Evidence:** none yet; the commit message of `5c5aa742` records the scenarios as owed.
**SRE task:** An SRE asking for help with Akamai, a database, PCF or observability gets the skill that
owns it, not a neighbour.

### HANDOFF-002 — the blocks-unapproved graders stop false-redding

**Status:** `ready` (2026-10-18); narrowed by the owner to the grader fix. The label-restatement rule
it also proposed is dropped: across the handoff build probes on 2026-09-30 it landed in 0 to 2 of 3
trials on every arm, the no-rule controls included, and AGENTS.md adds a handoff body rule only when
a probe shows the agent failing without it. The gap itself stays known and unremedied: every arm
dropped a restated helper label in at least one trial, against the AGENTS.md rule to preserve
labels in transit, and no wording tried closed it. A new remedy needs a handoff build probe showing
it lands before it enters an agent body.
**Owner:** `agent-engineer` owns the graders.
**Outcome:** `agent-direct-handoff-software-engineer-blocks-unapproved` grades blocking without false
reds: its `not_regex` graders accept a statement that nothing changed ("I changed nothing") and a
conditional plan that waits for approval ("once approved, I will apply the patch"), and its fields
grader is not tripped by a field name repeated in prose.
**Next action:** `agent-engineer` narrows the patterns and proves each fix offline on scripted
responses that show the false red before and the pass after, plus a true unapproved edit that still
fails; no model run is needed.
**Evidence:** [the scenario](../evals/scenarios/agent-direct-handoff-software-engineer-blocks-unapproved.yaml);
its graders are unchanged since 2026-09-30 apart from `max_turns`.
**SRE task:** An SRE trusts that a red on this check means the agent edited without approval, not
that it said so in a harmless sentence.

### RELIABILITY-001 — measure the timing repair on Claude, then decide on the reliability lane

**Status:** `ready` (2026-10-18); facts corrected by the owner. The source repair the deferral waited
for has landed, and nothing has measured it on Claude.
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
**Owner:** The human owner approves the run and remains the only acceptor; `agent-engineer` runs and
reads it.
**Outcome:** One bounded Sonnet comparison shows whether the reliability engineer states timing
without the 36-second bound and keeps the false-return versus exception distinction, against a
control that differs from it only by the timing repair. The owner then accepts the lane, scopes a
further repair, or keeps it shipped and unaccepted.
**Next action:** `agent-engineer` freezes a main commit as the candidate and builds the control from
it: the same bytes with only the retry-timing text restored to its pre-`2d0292c1` wording (the
retry-timing sentences in `skills/resilience-analysis/SKILL.md` and the two retry passages in its
`references/worked-contrasts.md`), keeping the overload and admission wording, with adapters
regenerated. A `git revert` of `2d0292c1` no longer applies, because `f151c276` rewrote the same
lines, so the control is a hand diff pushed to a ref and reviewed. With both commits and plugin
digests recorded, the owner approves that bound pair (about USD 1; one native trial per arm on
`claude-sonnet-5-5`, no retries). `agent-engineer` then runs both on
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

### PRINCIPAL-001 — accept the principal engineering lane on representative design tasks

**Status:** `deferred` (2026-10-16); the lane stays shipped and unaccepted. Across three measured
cases there is one tracker advantage and two design ties, not established general superiority or
an equivalence proof; principal's repeatable advantage is method and authority consistency. The
review cycle is complete.
**Owner:** Maintainers select the exact candidate and approve the evaluation budget;
`agent-engineer` owns the lane and its `eng-ladder` method.
**Outcome:** The principal engineer returns design records that name supported and unseen
consumers, plan compatible staged rollout and recovery, shape new systems against the stack
profile, and leave every decision to the human owner without expanded authority. One lane is shown
to serve both design depths, or the owner splits or removes it.
**Next action:** None. Reopens when the owner scopes a repair for builder adherence/reporting,
shared capture/abort reasoning and the method-check label/predicate mismatch, or approves
calibration of the [semantic scoring proposal](../evals/proposals/principal-judgment/README.md).
Each campaign states trial count, estimated cost, review hours and cost cap under DEC-04 before
any call. Do not rerun the completed review cycle; exact-candidate acceptance remains the owner's
decision. Retain the [held-out reconciliation](reviews/2026-10-08-principal-heldout-cutover.md#disposition-and-bounded-follow-up),
the [familiar-case packet](reviews/2026-10-07-principal-judgment-acceptance.md) and the independent
reports while this item is deferred: familiar-case
[first pass](reviews/2026-10-08-principal-independent-first-pass.md) and
[trace pass](reviews/2026-10-08-principal-independent-second-pass.md); held-out
[first pass](reviews/2026-10-08-principal-heldout-independent-first-pass.md),
[prompted addendum](reviews/2026-10-08-principal-heldout-independent-addendum.md) and
[trace pass](reviews/2026-10-08-principal-heldout-independent-second-pass.md).
**Evidence:** [Native evaluation](reviews/2026-10-05-principal-engineer-evals.md); the
[lane decision](decisions/2026-10-05-principal-engineer.md) keeps its acceptance scope.
**SRE task:** Get a reviewable design or architecture record, with options, staged rollout and
recovery, and the decisions to make, before code is written.

### INCIDENT-QUALITY-001 — verify decision quality after the SRE contract repairs

**Status:** `deferred` (2026-10-16); behavioral acceptance failed and stays on hold. The completed
24-session Sonnet campaign failed acceptance. After the helper-scope repair at `c53ed2b6`, one fresh
sample completed the native return/resume sequence but failed semantic criteria 4 and 6; the other
stopped before resume. Later source merges are not a fresh behavioral verdict.
**Owner:** Maintainers select the exact candidate and evaluation budget; `agent-engineer` owns
the bounded follow-up.
**Outcome:** The advisor loads relevant guidance, dispatches a bounded helper, reconciles its
return, and advances without invented causes, timing, or current-state claims.
**Next action:** None. Reopens when the owner scopes a repair for unsupported stage, timing and
escalation conclusions and exact file resolution, with a fresh bounded campaign on a named
candidate. Preserve actual return/resume and sufficient-evidence recovery as regressions. As of
2026-10-18, 101 commits on main have touched `incident-investigation` or `sre-assistant` since
2026-09-07, so reopening starts with a fresh bounded baseline on current main before any repair;
the September failures are not assumed to persist or to be fixed.
**Evidence:** [Selected-improvement record](reviews/2026-09-07-selected-sre-improvements.md);
[second pass](reviews/2026-09-07-incident-quality-second-pass.md), its
[symptom-guidance](reviews/2026-09-06-general-incident-help.md) and
[first-repair](reviews/2026-09-06-sre-decision-quality-repairs.md) baselines, plus
[task-sized outputs](reviews/2026-09-07-task-sized-skill-outputs.md) and
[helper exchange](reviews/2026-09-07-incident-helper-exchange.md). The
[operational-contract report](reviews/2026-09-04-operational-contract-fixes.md) remains the
record-provenance evidence used by merged PR #237. Results apply to those records' named snapshots.
**SRE task:** Get a useful next check or closeout without mistaking a helper's completed assignment
or an untimed aggregate for evidence of incident recovery or cause.

### LIFECYCLE-001 — operational context and service records stay true for a real service

**Status:** `deferred` (2026-10-16); CONTEXT-001 merged in. Consumer and producer repairs are
verified and independently reviewed against fixtures; no real-service records exist to accept
them against. The owner removed the retirement-order and record-transition references on
2026-10-24 because existing team processes cover that work; their acceptance campaign is dropped.
**Owner:** Save Toolkit maintainers; `agent-engineer` owns consumer requirements and
`software-engineer` owns producer/resolver implementation.
**Outcome:** Explicit team, service, environment, and deployment selectors produce the smallest
schema-valid context projection, failing closed on missing or ambiguous context and granting no
authority. Record maintenance and retirement remain with the team's existing processes.
**Next action:** None. Reopens when the owner selects a critical service, environment and record
repository. Then review and integrate the `sre-context` candidate `3433f98e` on
`work/lifecycle-001-status-projection`, based on `be29c942` (seven unmerged prerequisite commits
ahead of producer main `903ac830`), with this consumer, and verify navigation, freshness,
and ownership on that service. Fixture-only
resolution grants no live authority; catalog dates do not establish `last_verified`. The candidate
was committed on 2026-09-30; rebase it onto producer main and rerun its tests before review.
**Evidence:** [Consumer/producer tests and remaining acceptance](reviews/2026-09-30-backlog-four/lifecycle.md),
[lifecycle requirements](../skills/service-lifecycle/context-requirements.yaml), the
[accepted context-contract scope](decisions/2026-08-24-sre-operational-context-contract.md), and
the context refresh in the [selected-improvement record](reviews/2026-09-07-selected-sre-improvements.md).
**SRE task:** State team, service, environment, and deployment once, and know whether the service
record still applies to the deployment being operated.

### GRAPH-007 — promote or retire the sandbox workflow-graph skill

**Status:** `deferred` (2026-10-17); the owner deferred the promote-or-retire decision.
**Owner:** Save Toolkit maintainers; `agent-engineer` owns the skill text if promoted.
**Outcome:** Portable executable workflow/state-graph design either ships as a reviewed, routed
skill or is retired. Until then `agent-engineer` claims only the fleet's own agent workflow graph,
and a team service's workflow graph routes to `principal-engineer`.
**Next action:** None. Reopens when the owner takes the decision: promote
`sandbox/workflow-graph-engineering/SKILL.md` into `skills/` with routing scenarios and a
listing-size check, given ROUTE-003's inconclusive workflow-graph discovery measurements, or
remove it.
**SRE task:** Get a design for a durable workflow graph from the lane that can actually back it.

### EVAL-015 — compare library judge prompts with the incumbent judge

**Status:** `deferred` (2026-10-07); split from EVAL-010 action 4 when EVAL-010 closed.
**Owner:** Maintainers approve the comparison's budget, any new dependency and its credential;
`agent-engineer` runs it as EVAL-012 WP-03 under DEC-05.
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
**Owner:** `agent-engineer` authors; the human owner accepts the cases.
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
**Evidence:** none yet.
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
