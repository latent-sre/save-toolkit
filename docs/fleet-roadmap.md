# Fleet roadmap

> **Status: live; working update 2026-11-22, pre-refactor eval records retired.** This is the only backlog.
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

<a id="sre-cf-001--complete-protected-sre-investigation-access"></a>

### SRE-CF-001 — complete protected Grafana investigation access

**Status:** `active` (2026-11-13); the owner selected Grafana `gcx` for the read-only Grafana
access migration. The owner removed CF work from this ticket on 2026-11-14;
the identifier is retained for tracking, and existing CF command policy is unchanged.
[verified] A loopback-only qualification probe showed `gcx` 1.7.1 following a cross-host redirect
and forwarding a synthetic bearer token. No production credential was used. The latest upstream
release remains 1.7.1; protected destination/redirect enforcement is a blocking acceptance gap.
No redirect-control flag is verified for this release.
The local guard rejects direct `gcx` execution; protected agent execution, guarded/native
acceptance, and setup on supported hosts remain pending.
The caller/coverage fixes, selected browser tools and bundled Grafana helper are implemented;
the helper remains the existing admitted path during migration. Its credential file is still
readable through unhooked Read tools, and changing CLI does not establish credential isolation.
**Owner:** Save Toolkit maintainers.
**Outcome:** Grafana investigation works on
Claude Code and VS Code/Copilot under an agreed, verified access policy, reusing existing SSO/session
access first and supporting personal-account authentication when needed without exposing credentials
to the LLM. Deployment actions, other production mutations, and credential-bearing diagnostic reads
remain excluded.
**Next action:** A maintainer maps the required Grafana reads and queries to exact
CLI operations, repeats pinned installation checks on supported hosts, and establishes target/org binding,
output/time bounds, redirect rejection and a protected authentication path before changing the guard. The human
configures a read-only identity through the selected authentication path. Verify one complete dashboard
investigation, including credential/output and denied-effect controls, before retiring helper paths.
Bind the operations-repository path. Complete browser runtime
verification and an isolated analysis path only with their matching controls; retain both-host
acceptance. This selection adds no general CLI/HTTP/script grant or standard Copilot terminal access.
Helix/BigQuery remains an unconnected placeholder. INCIDENT-QUALITY-001 retains behavioral acceptance.
**Evidence:** [Planning context beside the agent](../agents/README.txt);
[current canonical profile](../agents/sre-assistant.md), [caller](../skills/incident-investigation/SKILL.md),
[guard source](../scripts/readonly-guard.py), and supplied-state regression fixtures under `evals/scenarios/`.
[Official gcx installation](https://grafana.com/docs/grafana/latest/ai-tools/grafana-cli/gcx/installation/)
and [authentication](https://grafana.com/docs/grafana/latest/ai-tools/grafana-cli/gcx/authentication/)
document the selected setup path.
Source and offline checks do not establish native acceptance of the access policy.
**SRE task:** Delegate a scoped Grafana dashboard or alert-state check while investigating another
part of the incident, without delegating deployment or remediation authority.

### BACKEND-002 — add go-craft beside python-craft

**Status:** `active` (2026-10-18). A single-file `go-craft` candidate is authored and composed with
`software-engineer` and `api-craft`; HTTP-specific Go guidance stays in the API
reference ([decision](decisions/2026-10-11-backend-craft.md)).
**Owner:** The human owner accepts the candidate; a maintainer session owns the skill.
**Outcome:** `go-craft` covers writing, refactoring and testing Go across services, CLIs and
libraries, measured against build scenarios the way `python-craft` is, and `api-craft` loads it
for Go changes.
**Next action:** Resolve the [PR #498 review findings](https://github.com/latent-sre/save-toolkit/pull/498#issuecomment-6879589379) before candidate acceptance: two P1 oracle false passes (unbounded worker and incorrect debounce timing) and one P2 timer-drain compatibility issue. [verified] The oracle counterexamples were reproduced at `8a0dd5d2`; the candidate was not changed. Then select a bounded comparison that measures Go guidance benefit beyond the model baseline; reference-content and negative-routing coverage remain open.
**Evidence:** Three authored discovery cases and a required Go-skill load in the existing
[Go HTTP build](../evals/build-scenarios/build-software-engineer-go-incidents-api.yaml).
These are unmeasured; the HTTP oracle does not establish Go-language skill benefit. No dedicated
Go-language build comparison or native routing result exists yet.
**SRE task:** An SRE changing a Go service or tool gets the team's Go conventions applied without
asking for them.

### EVAL-005 — the observability engineer's Grafana write lands, and only that write

**Status:** `active` (2026-11-12; pre-refactor trial results retired 2026-11-22 after skill
consolidation). Pre-refactor evaluator/cleanup repairs and six-slot Sonnet comparison records were
superseded by subsequent `grafana`, `obs-analysis`, and `observability-engineer` changes; fresh
acceptance requires a new bounded run on current `main`.
**Owner:** The human owner approves each repair run; a maintainer session repairs the scenario and runs it.
**Outcome:** [`build-obs-dashboard-write-honours-the-carve-out`](../evals/build-scenarios/build-obs-dashboard-write-honours-the-carve-out.yaml)
fails only on agent behavior: its refusal-wording check accepts measured correct refusals, and
its post-write query check fails only when the query did not return the persisted panel's data.
Required panel presentation is explicit in the task rather than inferred from advisory guidance.
**Next action:** When scheduled, run a fresh bounded baseline of [`build-obs-dashboard-write-honours-the-carve-out`](../evals/build-scenarios/build-obs-dashboard-write-honours-the-carve-out.yaml)
on current `main` before accepting or further tuning `observability-engineer`, `grafana`, or `obs-analysis`.
**Evidence:** Pre-refactor EVAL-005 run and repair packets were removed on 2026-11-22 and remain at the
[pre-removal snapshot](https://github.com/latent-sre/save-toolkit/tree/812aab80c4336f629679b25dc86f839d1969ff52/docs/reviews);
their results apply only to the pre-consolidation commits they name.
**SRE task:** Trust that the observability engineer changes the dashboard asked for and leaves
datasources alone.

### ROUTE-007 — re-check routing for the descriptions trimmed on 2026-09-02

**Status:** `active` (2026-10-25; pre-refactor routing baseline retired 2026-11-22 after skill
consolidation). The pre-consolidation 20-case baseline and withdrawn wording comparison no longer
measure the current skill set.
**Owner:** The human owner approves the run; a maintainer session writes any missing scenarios and runs them.
**Outcome:** The surviving consolidated skills (`akamai-edge`, `api-craft`, `database-reliability`,
`frontend-craft`, `grafana`, `obs-analysis` absorbing `obs-alerting` and `obs-pipeline`, and
`pcf-ops` absorbing `pcf-deploy`) each have at least one fire and one not-fire routing scenario,
and all pass once on current `main`.
**Next action:** Measure automatic routing against current `main` with a fresh bounded baseline,
preserving explicit-human-only deployment boundaries for production changes.
**Evidence:** Pre-refactor routing baseline and preparation packets were removed on 2026-11-22 and
remain at the
[pre-removal snapshot](https://github.com/latent-sre/save-toolkit/tree/812aab80c4336f629679b25dc86f839d1969ff52/docs/reviews);
the commit message of `5c5aa742` records the original scenario requirement.
**SRE task:** An SRE asking for help with Akamai, a database, PCF or observability gets the skill that
owns it, not a neighbour.

### RELIABILITY-001 — preserve retry-count uncertainty and qualify the native assessment

**Status:** `active` (2026-11-13; pre-refactor native comparisons retired 2026-11-22). Earlier
bounded comparison runs measured pre-consolidation candidates (retaining numerical-reasoning and
retry-assumption gaps at the time) and no longer measure current `main`.
**Owner:** The human owner remains the only exact-candidate acceptor; a maintainer session owns
the evidence and any separately scoped follow-up.
**Outcome:** Preserve timing and retry-count assumptions plus conditional return/exception
behavior through a real helper exchange, then let the human accept the exact candidate or
retain the lane shipped and unaccepted.
**Next action:** When reopened, start from a fresh bounded baseline on current `main` and scope any
repair around justified bounds, attempt-duration assumptions, and supplied-control coverage while
preserving the current denied-tool policy.
**Evidence:** Pre-refactor RELIABILITY-001 comparison and WP-10/backlog-four packets were removed on
2026-11-22 and remain at the
[pre-removal snapshot](https://github.com/latent-sre/save-toolkit/tree/812aab80c4336f629679b25dc86f839d1969ff52/docs/reviews).
The [lane decision](decisions/2026-09-21-reliability-engineer.md) retains its acceptance scope; no
result promotes the lane.
**SRE task:** Turn a service weakness or repeated manual intervention into supported engineering
work with an owner and a meaningful proof-of-improvement check.

## Deferred

### FRONTEND-003 — define the team's GUI mix after the first runs of the rewritten skill

**Status:** `deferred` (2026-11-14); the owner deferred tuning until evidence from three to five real GUI projects is available. The owner said on 2026-10-11 that the team's GUI work is a mix
of the skill's five archetypes and that the mix is defined after a few runs, not up front; the
rewritten `frontend-craft` therefore weights the archetypes evenly and defers the deep capability
references ([decision](decisions/2026-10-11-frontend-craft-generalized.md)).
**Owner:** The human owner decides the weighting and the first add-on; a maintainer session owns the
skill's archetype table and build scenarios.
**Outcome:** After the first few real GUI tasks, the archetype table reflects the kinds of GUI the
team builds most, the greenfield recommendations follow that weighting, and the first deep
capability reference (charts and grids, live data, forms, or editors) is chosen and scheduled.
**Next action:** No dedicated tuning work until three to five real GUI projects provide evidence. During normal frontend work, record the archetype, chosen kit set and deployment target in the project packet. Once that evidence exists, the owner reviews it beside the proof packet and reopens the weighting and first-add-on decision.
**Evidence:** [Rendered proof of the skill's defaults](reviews/2026-10-11-frontend-craft-proof/README.md);
no real-task runs yet.
**SRE task:** An SRE building a GUI gets defaults tuned to the kind of GUI the team builds most,
and a deep reference for the capability they reach for first.

### EVAL-012 — plan incident and coding evaluations for the fleet

**Status:** `deferred` (2026-11-14; pre-refactor campaign records retired 2026-11-22); the owner deferred the umbrella evaluation programme during backlog triage. Earlier pre-consolidation run records were removed on 2026-11-22; harness specs, adapters, and contracts remain in the repository below:
- WP-01 complete: `evals/compare_runs.py`, merged in
  [PR #333](https://github.com/latent-sre/save-toolkit/pull/333) at `52352543`.
- WP-02 / EVAL-011 runner baseline complete: the
  [EVAL-011 closeout](reviews/2026-10-10-eval-011-closeout.md) binds the repaired native
  measurement contract.
- WP-08 implementation candidate prepared (adapter, host credential proxy, independent verifier,
  smoke gates, and offline tests); live smoke and paid trials have not run, and exact-candidate
  acceptance remains with the owner.
- Complex-campaign preparation under the [implementation plan](fleet-evaluation/implementation-complex-campaigns.md):
  WP-05 has [18 authored execution profiles over six incident families](../evals/incident-conversations/README.md)
  plus the [owner disposition](../evals/incident-conversations/review-v2/owner-disposition.json),
  and WP-09 has [five-case SWT](fleet-evaluation/wp09-swt-run-plan.md) and
  [five-case Harbor/Terminal-Bench](fleet-evaluation/wp09-terminal-runplan.md) proposals and
  adapters; the standalone [campaign report](fleet-evaluation/campaign-report.md) preserves
  measurement, billing, and review interfaces.
- WP-04/05, WP-10, and WP-13 pre-refactor trial results and Windows preparation records are
  retired in the working tree; WP-12's 64 GCP cases remain in
  ([pilot and template](../evals/oracles/gcp/README.md), [catalog](../evals/oracles/gcp/CATALOG.md)),
  and WP-15's [Coder Eval experiment](fleet-evaluation/coder-eval.md) waits for the first useful
  comparison. WP-03 remains deferred under EVAL-015.

**Owner:** The human owner accepts scope, run conditions and exact candidates; a maintainer session owns
scenario and measurement design; implementation and lab owners are assigned per delivery package.
**Outcome:** A reviewable evaluation specification covers ITBench-Lite, SREGym, repository repair,
test generation, selected terminal tasks, GCP managed-service/migration and GKE evaluations, actual
fleet integration, Coder Eval runner assessment and later Microsoft AIOpsLab, with traceable evidence,
acceptance tests, delivery phases and explicit open decisions.
**Next action:** None until the owner reopens a named work package for a concrete candidate or evaluation decision. On reopening, select its bounded scope, runtime and applicable budget under [the follow-through plan](fleet-evaluation/run-plan-followthrough.md) or [WP-08 operator commands](fleet-evaluation/wp08-operator.md), recalibrate the judge before any rubric-graded campaign (`1d92654f` changed judge identity), and capture a fresh baseline on current `main`. Independently tracked tickets retain their own dispositions.
**Evidence:** [Specification](fleet-evaluation/README.md); [EVAL-011 closeout](reviews/2026-10-10-eval-011-closeout.md). Pre-refactor WP-02, WP-04/05, WP-08, WP-10, WP-13, follow-through, and Windows-prep records were removed on 2026-11-22 and remain at the [pre-removal snapshot](https://github.com/latent-sre/save-toolkit/tree/812aab80c4336f629679b25dc86f839d1969ff52/docs/reviews); integration and behavioral results remain unverified on current `main`.
**SRE task:** Compare exact agent candidates on realistic incidents and engineering tasks, see what
improved or regressed, and distinguish failed behavior from an instrument that could not measure.

### EVAL-016 — prove the Inspect orchestration matches the native batch, then decide what it replaces

**Status:** `deferred` (2026-11-13); the owner deferred the Inspect AI parity comparison during
backlog review. `evals/inspect_fleet.py` runs the native routing and contract trials as an Inspect
task with grading unchanged; its offline tests passed, but no paid run has compared it with
`build_probe.py run`. The native runner remains the acceptance reference.
**Owner:** Maintainers run the paid parity comparison and approve its budget; the repository owner
decides the replacement inventory afterwards.
**Outcome:** One frozen selection run through both paths on the same model, CLI and host shows the
same per-scenario verdicts under `build_probe.py regrade`, with timing, cost and any INCONCLUSIVE
reasons recorded; a follow-up decision then names which native batch code Inspect replaces, or the
track is relabelled as scheduling only.
**Next action:** None until the owner chooses to resume Inspect adoption and approves a bounded
parity comparison. Then a maintainer follows the
[parity run plan](fleet-evaluation/run-plan-inspect-native-parity.md) on a host with Claude
credentials and a current judge calibration, and files the comparison under `docs/reviews/`.
**Evidence:** none yet; the [decision](decisions/2026-11-02-inspect-orchestrates-native-runner.md)
records the design and its rollback.
**SRE task:** Read one `inspect view` log of a fleet regression instead of a directory of records,
trusting it only once it is known to say what the native batch says.

### WORKBENCH-001 — plan a shared SRE operations product for humans and agents

**Status:** `deferred` (2026-11-13); the owner deferred the tool during backlog review and
identified its planning package as needing revision before work resumes.
**Owner:** Human product owner accepts scope and release decisions; implementation and
verification owners are assigned before each delivery phase.
**Outcome:** A reviewable specification covers common commands, Grafana, scripts, investigation
workflows, extensibility, and the full future product, with traceable acceptance criteria and
explicit permission, evidence, compatibility, and recovery contracts.
**Next action:** None until the owner reopens planning. First revise the
[SRE Workbench planning package](sre-workbench/README.md) with the owner, resolve its phase-zero
decisions, and select the first implementation slice. Planning authorizes no live execution,
credential setup, host grant changes, or production rollout. Product implementation will have a
separate repository/release decision; this roadmap remains the sole live work queue.
**Evidence:** [Product requirements and specifications](sre-workbench/README.md); requirements
come from the owner discussion on 2026-10-02. All product runtime behavior remains unverified.
**SRE task:** Run the same useful operational checks from a terminal or an agent, preserve their
evidence, and extend the tool as new operational needs appear.

### RELEASE-001 — make the toolkit installable as an immutable, rollback-tested release

**Status:** `deferred` (2026-11-13); the owner deferred immutable-release work during backlog
review. The owner requires verified native delegation on the default
Copilot harness before release. A commit-pinned selector and checksummed candidate archive are
prepared; installed acceptance and an accepted immutable rollback baseline remain outstanding.
An isolated development-registration preflight is prepared, but Computer Use denied Visual Studio
Code inspection; inventory and installed-format acceptance remain unverified.
**Owner:** Maintainers accept the release; a maintainer session owns the plugin contract and
`software-engineer` owns helper/adapter repairs.
**Outcome:** An SRE installs a pinned artifact rather than whatever `main` holds, and can roll back
to a previously accepted one. The acceptance cases pass on those
exact shipping bytes, which the 2026-09-10 local-install run did not exercise.
**Next action:** None until the owner reopens release work. Then resolve the missing native
per-parent target restriction, and implement and verify
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
**Evidence:** [current preparation and selected harness](reviews/2026-11-12-release-001-preparation.md);
the pre-refactor handoff packet was removed on 2026-11-22 and remains at the
[pre-removal snapshot](https://github.com/latent-sre/save-toolkit/tree/812aab80c4336f629679b25dc86f839d1969ff52/docs/reviews);
the 2026-09-10 VS Code 1.137.0 acceptance row in the host-support table of
[`README.md`](../README.md); HOST-002's closure commit records the owner disposition.
**SRE task:** Install a named version of the toolkit, and go back to the previous one if it regresses.

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
release. [verified] The projection now omits Local-only `agents`, `handoffs`, `argument-hint`,
and `advancedOptions` agent fields; the handoff map is retired and skill/command hints remain.
[verified] Agent-authoring now covers the default-harness field contract, tool mapping and preload
checks; the renderer rejects empty mapped tool lists before replacing generated files.
Native delegation enforcement and installed acceptance remain to implement. Current converter/SDK research
has not identified an enforceable per-parent delegation-target restriction.
**Owner:** The human owner decides; a maintainer session owns the generator and lane text.
**Research scope:** Copilot, Claude Code, and Codex; OpenCode excluded for now. This comparison
does not change the selected release targets.
**Outcome:** The fleet states how delegation works on the default Copilot harness, its lanes do not
depend on a Local-only field there, and acceptance cases exist for the chosen harness.
**Next action:** Establish a host-enforced target restriction before shipping the delegating
projection; ignored Local fields and timeout-sensitive hooks do not establish the selected
contract. Prepare bounded generator corrections for qualified browser tools, discovery
instructions, and the hook payload contract. Then prove allowed/forbidden child invocation,
parent continuation, effective tool grants, and instruction delivery in an installed
default-Copilot session. Follow the acceptance matrix in the
[migration research](reviews/2026-11-14-copilot-harness-migration-research.md).
**Evidence:** [verified] Nine agents, 24 skills, and one command inspected; offline hook probe
found a camelCase-payload migration trap. [sourced] Current converter/SDK inspection still found
no per-parent target allowlist; VS Code now schedules Local removal by February 2027.
[Research and pinned sources](reviews/2026-11-14-copilot-harness-migration-research.md),
[three-Terra harness comparison](reviews/2026-11-14-three-harness-comparison.md),
[selected scope](reviews/2026-11-12-release-001-preparation.md).
[unverified] Current installed-harness behavior remains to test.
**SRE task:** Use the fleet's delegating lanes from a default Copilot session, knowing which handoffs
work there.

### PCF-DEPLOY-001 — give pcf-deploy an Apps Manager path for SREs without the cf CLI

**Status:** `deferred` (2026-11-08); the owner deferred this from the skill review (`pcf-deploy`
was later merged into `pcf-ops`).
**Owner:** Save Toolkit maintainers; a maintainer session owns the skill text.
**Outcome:** Where Apps Manager offers an equivalent, `pcf-ops` deployment plans state that path beside the
`cf` command, and name the steps that still need the CLI.
**Next action:** None until the owner schedules it. Then confirm which steps Apps Manager supports
on the team's foundation version before writing them. Also confirm on the team's foundation that
app events appear on the app **Overview** page, as Broadcom documents; `pcf-ops` now sends
responders there instead of to a separate Events view.
**Evidence:** [sourced] Broadcom's [Elastic Application Runtime 10.4 Apps Manager guide](https://techdocs.broadcom.com/us/en/vmware-tanzu/platform/elastic-application-runtime/10-4/eart/manage-apps.html)
places app events on the Overview page and logs under Observability > Logs, and documents no
separate Events view; the 11.0 guide matches. The team's console is unverified.
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
The prepared tabletop packet (in Git history) now selects accepted
migration/hybrid and GKE reachability cases, with separate responder handouts and worksheets.
Human execution and usefulness results remain unmeasured.
**Evidence:** Offline preparation and exact case identities (in Git history).
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
