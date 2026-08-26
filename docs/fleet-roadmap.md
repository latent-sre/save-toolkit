# Fleet roadmap

> **Status: live.**
> This is the only document that tracks unfinished, blocked, or explicitly deferred work for the
> current fleet. Historical plans, reviews, audits, and decision records provide evidence and
> rationale; they do not independently add work to this queue.

The accepted architecture is
[`2026-07-31-multi-platform-plugin-packaging.md`](decisions/2026-07-31-multi-platform-plugin-packaging.md):
one canonical Claude plugin under `agents/`, `skills/`, and `commands/`, with generated host-native
adapters for Copilot/VS Code. Codex was retired as a distribution target on 2026-08-23
([ADR](decisions/2026-08-23-retire-codex-distribution-target.md)); it remains a supported way to
work in this repository, reading the root `AGENTS.md` like any other agent.

Closed items and their dispositions live in [`roadmap-closed.md`](roadmap-closed.md). That register
is evidence; it never re-queues work.

## Item contract

Every live item carries:

| Field | Meaning |
|---|---|
| ID | Stable identifier used by plans, reviews, and release evidence |
| Status | `ready`, `active`, `blocked`, `deferred`, or `decision-needed` |
| Outcome | Observable result rather than a list of files |
| Source | Decision or review that established the work |
| Prerequisites | Controls that must exist first |
| Acceptance | Evidence required to close the item |
| Next action | Smallest safe step that advances it |

An item leaves this file after its acceptance evidence is committed and the change is merged, or
after an explicit owner disposition is committed with the reason it is no longer work. Git history
and archived source documents retain the implementation detail.

**This file states what is still owed, not what was already proven.** Dated evidence, finding
tables, transcripts, and byte inventories belong in the linked packet under `docs/reviews/` or the
accepted record under `docs/decisions/`. An item cites its evidence; it does not restate it.

## Active runtime work

### WF-001 — establish a supported exact-dispatch boundary for Claude workflows

**Status:** `blocked`

**Outcome:** The repository carries no executable `ship-review` workflow until Claude provides a
supported way to dispatch one exact trusted workflow without granting caller-supplied workflow code.

**Source:** A version-pinned probe on Claude Code 2.1.221 found two incompatible behaviors:
`CLAUDE_WORKFLOW_NAME_ONLY=1` suppresses inline-plugin workflows, and without it a native permission
for `Workflow(save-toolkit:ship-review)` also admits the same `name` plus a caller-supplied `script`
that the resolver executes. A plugin `PreToolUse` hook can deny the override, but the resulting
launcher, hook receipt, Git-object isolation, and upgrade matrix were a bespoke security broker
disproportionate to this fleet, so the experiment was removed rather than shipped. Re-checked
2026-08-18 on 2.1.227: built-in `claude ultrareview` removes the caller-supplied workflow-body
surface but exposes no immutable reviewed-subject identity and no findings-sensitive verdict — it
exits 0 either way, bundles a mutable tree, and uploads to a paid cloud sandbox. Still blocked.
Sources and queries: the
[first-three backlog evidence packet](reviews/2026-08-18-first-three-backlog-evidence.md).

**Prerequisites:** A documented direct-dispatch API, or documented permission semantics that bind
the registered workflow implementation as well as its name. Any alternative architecture needs an
accepted decision record before implementation.

**Acceptance:** Pin the supported CLI/API version and prove before merge that (1) only the intended
trusted workflow implementation can execute; (2) same-name `script`, `scriptPath`, resume, remote,
and extra-field variants are denied before task creation; (3) candidate bytes never reach an outer
tool-bearing model; (4) reviewer lanes have structurally bounded authority; and (5) incomplete or
failed review evidence cannot become approval. Gate A and mocked JavaScript are supporting evidence,
not substitutes for the live boundary proof.

**Next action:** Monitor the ultrareview/direct-dispatch result contract for a documented immutable
candidate identity and machine-enforceable finding verdict. Do not restore `ship-review`, wrap an
exit-0 result as approval, or launch a paid/uploading probe until an owner explicitly accepts that
external data/cost boundary and the remaining guarantees can be proven.

## Repository work

### CONTEXT-001 — establish a generalized SRE operational-context contract

**Status:** `active` (2026-08-24)

**Owner:** `latent-sre` owns the architecture decision and acceptance of the exact generic-alpha
revision. `agent-engineer` owns consumer context-requirement semantics for agents/skills;
`software-engineer` owns any later resolver, validator, or onboarding-tool implementation. A team
owner becomes accountable for values and operational documents only when that team separately opts
into onboarding. No owner may approve its own unreviewed evidence.

**Outcome:** Reusable skills and agents resolve one explicit team, service, environment, and—when
needed—deployment from schema-valid team configuration, then receive only the smallest context
projection they declare. Onboarding a team supplies values, relationships, repository mappings,
platform identities, operational references, and runbooks without forking the underlying skills.
Missing or ambiguous context fails clearly; production is never an implicit target; valid context
does not grant credentials, approval, or effect authority.

**Concrete consumer:** The first consumer is the read-only `service-readiness-audit`. One unchanged
consumer contract must work across differently shaped synthetic teams, services, environments, and
platform representations before any real team onboards or effect-capable skill adopts the resolver.
Fixtures may model PCF and GCP/Cloud Run shapes already represented in the fleet, but they do not
decide the pending landing runtime, introduce self-managed Kubernetes, or rewrite platform
procedures.

**Source:** Owner direction on 2026-08-24 requested the smallest useful standardized operational
context contract. The
[`generalized SRE team and application context framework`](reviews/2026-08-24-sre-context-framework-architecture.md)
records the current-repository assessment, research, alternatives, proposed schemas, and staged plan.
The
[`source-independent SRE operational-context contract`](decisions/2026-08-24-sre-operational-context-contract.md)
is the accepted record: it disposes every load-bearing choice (service/system boundary,
environment/deployment split, central Git first source, versioned skill-side requirement sidecars,
typed references without deep merge, runbook indexing, phase-one file/CLI resolver, and the
curated-facts-only rule) and states the consequences, rejected alternatives, failure modes, and
rollback. Owner approval on 2026-08-24 authorizes **stages 1–3 only**; it does not authorize
real-team onboarding or effect-capable adoption.

**Prerequisites:** The accepted ADR names the schema/contract owner, resolver owner, source
repository and permissions, generic fixture policy, representational platform shapes, and the alpha
compatibility window. No real team or service values are prerequisites. Reinspect the exact consumer
skill, generator/package behavior, dependency policy, and current schema catalog before naming
implementation files. Any third-party validator or YAML parser is pinned in `requirements-dev.txt`
and follows the CI/Gate A dependency rule. No central repository, schema, resolver, MCP server,
skill rewrite, or live discovery job is created solely from this roadmap entry.

**Acceptance:** All conditions are required and retain separate evidence labels. (1) **Architecture:**
the accepted ADR disposes every decision and retains its deliverables, boundaries, rollout, rollback,
and non-goals; a design review is not runtime proof. (2) **Source contracts:** immutable versioned
JSON Schema 2020-12 contracts exist for the minimum Team, Service, optional System, Environment,
Deployment, Repository, Integration/Resource, Runbook metadata, consumer requirement, and
resolved-bundle shapes; unknown objects fail closed, and formats plus YAML duplicate keys are tested
with the selected validator rather than assumed. (3) **Semantic resolver:** an explicit source root
and canonical selectors produce deterministic, byte-bounded output with fixture taint and qualified
provenance; duplicate IDs/aliases, broken or kind-wrong refs, forbidden cycles, zero/multiple
deployments, missing required paths, implicit production, secret-bearing fields, traversal, and
nondeterministic output have named red-first regressions. (4) **Identity and repositories:** catalog
IDs, display names, typed/scoped aliases, platform IDs, telemetry mappings, and runtime instance IDs
stay distinct; repositories are first-class and `other` never becomes an untyped escape hatch.
(5) **Generic portability proof:** at least two explicitly synthetic team fixtures, multiple services
and repositories, production-classified and non-production environments, and at least two platform
representations validate without a team-specific schema or skill branch, and the same
`service-readiness-audit` requirement contract resolves representative selections while refusing
missing or ambiguous ones. (6) **Context behavior:** required and alternative JSON Pointer paths fail
closed, optional absence stays explicit, and a fresh-context exercise demonstrates deterministic
lookup within declared depth/byte budgets without claiming exact source identity or production
correctness. (7) **Truth and safety:** no secret or copied live state ships; an effect-capable path
separately proves that context cannot default to production, approve an action, supply a credential,
or bypass the production/effect gate. (8) **Onboarding and operations:** synthetic acceptance proves
a new team can add its records and receive clear validation output without editing a generalized
skill, with ownership, migration, stale-link diagnostics, recovery, and troubleshooting documented.
(9) **Integrated verification:** focused schema/resolver/consumer regressions, affected routing or
behavior checks, adapter regeneration where canonical skill bytes change, strict plugin validation,
`git diff --check`, Gate A at the push boundary, and independent exact-revision review all pass,
each stating what it proves and what remains unverified.

**Closure:** Merge the accepted generic alpha and its exact synthetic evidence, record the supported
alpha contract and next migration boundary, then close the item. Fleet-wide adoption, federation,
Backstage/MCP adapters, automatic discovery, live reconciliation, or a general overlay language are
separately justified work and do not silently expand this item.

**Next action:** Create the approved private `latent-sre/sre-context` repository and implement stages
1–3: contract skeleton, first synthetic-tenant read-only proof, and second synthetic-tenant
portability proof. No team-specific values are required. Do not onboard a real team or rewrite fleet
skills beyond the accepted generic consumer contract in this stage.

### DRILL-001 — apply the `incident-drill` evaluation backlog

**Status:** `ready` (2026-08-25)

**Owner:** `agent-engineer` owns the skill text, references, and templates; `software-engineer`
owns the bundled scripts. Human acceptance of the exact revision remains with `latent-sre`.

**Outcome:** The `incident-drill` skill's authoring path stops producing scenarios that leak their
own ground truth or that cannot be dispatched end to end, and its retro lands somewhere teardown
cannot delete.

**Source:** A three-case evaluation on 2026-08-25 measured the skill against a no-skill baseline.
Setup scored 10/10 verified against the produced directory and the retro method 10/10 against 8/10,
but scenario authoring scored **8/10 against a 10/10 baseline**, losing on ground-truth leakage into
downstream packets and on a lane chain half-marked "do not dispatch". The fifteen-item backlog and
the evidence behind each item are in the
[iteration-1 evaluation](reviews/2026-08-25-incident-drill-skill-evaluation.md).

**Prerequisites:** None. The skill ships as evaluated; this item changes it.

**Acceptance:** Backlog items 1–8 applied (the two authoring failures, the undocumented pack format,
the retro's destination, the drill card, the separate ground-truth file, the Windows path-length
guard, and the tool-grant cross-check); the two non-discriminating authoring assertions replaced; a
rerun of the same three cases showing the authoring case no longer leaks ground truth and produces a
runnable chain, with the cost delta recorded; Gate A, links, canary, `test_check_links.py`, and
strict plugin validation green; projections regenerated once.

**Next action:** Apply items 1–3 first — they are the ones that made the authoring case lose — then
rerun that case before touching the rest.

### GRAPH-001 — engineer the fleet itself as an executable workflow graph

**Status:** `active` (updated 2026-08-25). Accepted fixes are published for exact-revision review in
[PR #165](https://github.com/latent-sre/save-toolkit/pull/165); the candidate remains unpromoted
until owner acceptance of that head.

**Owner:** `agent-engineer` owns the fleet's design contract and its review; `latent-sre` accepts
the exact revision. Each accepted finding is implemented by the owner of the surface it names
(`software-engineer` for validators and harness code, `agent-engineer` for agent and skill text),
never by this item directly.

**Outcome:** The fleet's agents and skills are described once as an executable workflow/state graph
in the `workflow-graph-engineering` fourteen-section shape: agents and gate skills as nodes with
stated authority; `Agent(...)` grants as deterministic edges; description-driven selection as
model-selected edges with an explicit allowed destination set; handoff packets as edge payloads
carrying evidence and taint; gate skills and the dashboard write rule as approval nodes bound to an
approver, exact action, and candidate identity; the human executor as the effect boundary with an
explicit `UNKNOWN` outcome; terminal lanes and delegation chains with termination evidence and
budgets; and discovery/direct evals mapped to edge and node evaluations. Rows the fleet cannot fill
are recorded as "not stated" findings, each dispositioned to an owner or a roadmap item.

**Source:** Owner direction on 2026-08-24 ("our skills and agents to be graph engineering"), staged:
apply the contract to the fleet first, then widen the capability. Method:
`workflow-graph-engineering` from `SKILLS-003`. Prior art that must not be duplicated: the validated
roster/delegation graph in
[`delegation-graph.md`](../skills/agent-authoring/references/delegation-graph.md) and the handoff
packet conventions in [`roster.md`](../skills/agent-authoring/references/roster.md).

**Boundaries:** No workflow runtime or exact-dispatch mechanism is selected or restored — `WF-001`
stays blocked and is recorded as the deferred runtime decision in section 14. No agent gains tools,
delegation edges, or effect authority through this item. The contract references the roster table
for edges and never becomes a fourth copy of the edge list. A finding becomes fleet text or a
validator only through its owner's separate change with focused evidence.

**Evidence:** The draft contract and its **request changes** verdict, all eleven ranked findings, and
the full rejection detail are in
[`2026-08-24-graph-001-fleet-workflow-graph-contract.md`](reviews/2026-08-24-graph-001-fleet-workflow-graph-contract.md).
A synthetic P3→P1 incident worked end to end through the real lanes is in the
[incident drill retro](reviews/2026-08-25-graph-001-incident-drill-retro.md), which confirmed F1, F2,
F5, F6, F9, and F10 in practice and added four findings. Dispositions: F1, F2, F4, F5, F6, F8, F9,
F10 and drill findings N1–N3 are `worked` in the candidate; F3's measurement is `already owned` by
`ROUTE-003` (its policy half worked, with no alias pin added); F7 is `verified 2026-08-25` by
`HOST-002`; F11's schema is `already owned` and deliberately deferred by `SKILLS-003`, its dirty-tree
binding worked; N4 is `dropped with reason` as coordinator practice folded into F10. The candidate's
paired incumbent/candidate eval runs, suite digest, and frozen plugin images are recorded in PR #165;
earlier NO-GO and intermediate reruns are historical and are not promotion evidence. Focused harness,
graph, release, observability, guard, doctor, platform, evaluator, and validator suites, generated
adapter checks, `git diff --check`, and Gate A are green on the candidate. The security-fix method's
read-only bypass review was limited to the incident-drill boundary: the launcher is still not a
sandbox, so live drill use is blocked unless the caller provides and attests to a disposable
credential-free OS identity with constrained egress, destroyed before retry after timeout.

**Prerequisites:** Satisfied — the `workflow-graph-engineering` method merged at `f1afd57` (closed
2026-08-26; see the closed table), so there is an exact revision to cite. The first review ran
against that method's candidate branch as a draft, labelled `[unverified]` until re-run on the
merged revision.

**Acceptance:** (1) A dated packet under `docs/reviews/` carries the fourteen-section contract for
the fleet with file-and-line citations and labels, plus ranked review findings; (2) every finding has
a disposition (`worked`, `already owned`, `proposed to roadmap`, `dropped with reason`) and, where
proposed, a roadmap item with an owner; (3) any live control that lands ships in its own change with
the focused red-to-green evidence `CONTRIBUTING.md` requires; (4) `WF-001` remains unchanged unless
separately accepted.

**Next action:** `latent-sre` reviews and accepts the exact PR #165 head revision before promotion.
Resolve any current review finding or failed check on that revision. F7, F11, N4, `GRAPH-002`, and
`WF-001` are out of scope for this item.

### INCIDENT-001 — keep active-incident ownership in SRE through terminal recovery

**Status:** `active` (2026-08-25) — the ownership contract merged in PR #164 and the first typed
record merged in PR #167. Three accepted late-review gaps are being addressed on
`work/incident-state-v2-review-fixes` from refreshed `origin/main`: record-last enforcement,
tilde-fenced competing records, and unknown or fractional recovery progress.

**Owner:** `agent-engineer` owns the fleet prompt, context, loop, and graph contract; `latent-sre`
accepts the exact revision. Human incident command and release owners retain their existing live
authority.

**Outcome:** One typed `sre` lane owns a reliability incident from triage through sustained recovery
and a named terminal state. It loads observability, platform, and database skills as context inside
that lane. Its only agent call during the incident is a bounded sanitized public research question
that returns to the same loop. After terminal resolution, the caller starts observability,
engineering, and documentation as separate next-phase tasks; SRE does not dispatch them.

**Source:** Owner direction on 2026-08-25 accepted the four-theme standard — Prompt selects and
guides the owner, Context equips it, Loop governs work and termination, and Graph governs ownership
transitions — and specifically chose sustained SRE incident ownership over combining SRE with the
steady-state observability or documentation lanes. This accepts the SRE slice of `GRAPH-001` F4;
it does not activate the held SRE capability additions from `SKILLS-003`.

**Prerequisites:** Fresh branch from refreshed `origin/main`; current agent, skill, graph-validator,
and eval behavior inspected before editing; one focused regression frozen and run on the incumbent
before the candidate.

**Acceptance:** (1) canonical `sre` delegation, `EXPECTED_DELEGATION`, and the roster expose only
`researcher`; (2) SRE and `incident-command` keep `investigating`, `mitigating`, and
`monitoring-recovery` nonterminal and require sustained same-signal evidence for `resolved`; (3)
`observability-engineer`, `software-engineer`, and `scribe` are named as caller-dispatched next-phase owners, not
live SRE delegates; (4) the same two-trial direct-SRE case, model, timeout, prompt, and graders fail
the incumbent and pass the one candidate; (5) affected offline tests, generated projections, strict
fleet validation, and Gate A pass, with main-thread-only `Agent(target)` enforcement reported as the
host boundary; (6) `monitoring-recovery` responses retain operator prose and end with exactly one
`incident-state/v2` JSON record that closes the state, owner, recovery window, production authority,
and post-terminal caller-dispatch relationships; (7) integer seconds preserve fractional-minute
progress, paired nulls preserve unknown progress without invention, and competing backtick or tilde
JSON records fail closed.

**Next action:** Require the frozen fractional and unknown-progress incumbent cases to fail at 0/2,
the one exact candidate to pass both at 2/2 under the same model and timeout, all affected offline
and structural checks to pass, and `latent-sre` to accept the exact follow-up PR head before
promotion.

### GRAPH-002 — add a runtime-specific implementation lane for executable graphs

**Status:** `decision-needed` (2026-08-24)

**Owner:** `software-engineer` owns implementation; `agent-engineer` owns the skill text that
carries runtime-specific references; `stack-profile`'s decision owner names the runtime.

**Outcome:** `software-engineer` can implement an accepted `workflow-graph-engineering` design
contract against a named runtime — checkpointer and interrupt patterns, reducer and fan-out
primitives, idempotent effect handlers, cancellation, replay or shadow verification — with pinned
upstream references and the design's evaluation plan (recovery, temporal, consistency, budget)
executed as tests.

**Source:** Owner direction on 2026-08-24 (stage 2). The
[`2026-08-23 research refresh`](reviews/2026-08-23-prompt-loop-graph-engineering-research.md)
records that no inspected runtime supplies the whole portable contract, which is why selection
follows the design and a concrete consumer rather than preceding them.

**Decision required:** the first consumer graph (a team-approved workflow, not the fleet itself while
`WF-001` is blocked), the runtime candidates admissible under `stack-profile`'s landing runtime
decision, and whether references live in a new skill or under an existing `software-engineer`-loaded
craft skill.

**Prerequisites:** The `workflow-graph-engineering` method merged at `f1afd57` (closed 2026-08-26; see the closed table) — satisfied; a named consumer graph with an accepted design contract;
a `stack-profile` runtime decision with an owner; `researcher`/GitHits evidence pinned to exact
upstream revisions.

**Acceptance:** One synthetic consumer graph implemented from its contract, passing the contract's
recovery, temporal, consistency, and budget evaluations under independent verification bound to the
exact revision; no production deployment authority is created.

**Next action:** Owner names the consumer and the admissible runtimes; then scope the reference set
and open the implementation slice.

### GRAPH-003 — operate running graphs: indicators, failure planes, runbooks, and alerts

**Status:** `decision-needed` (2026-08-24)

**Owner:** `observability-engineer` for indicators, dashboards, and alert design; `scribe`/`runbook`
for operating documents; `sre` remains the live-incident lane. No new agent.

**Outcome:** The owning observability and operations skills carry graph-specific material
(run/node/edge/attempt lineage, per-failure-plane indicators, queue and worker health, `UNKNOWN`
effect backlog, approval wait, checkpoint age, replay canaries, and the runbook branches per failure
class) as references inside their existing skills rather than a new SRE capability.

**Source:** Owner direction on 2026-08-24 (stage 2). Requirements are enumerated in section 8 of the
[`2026-08-23 research refresh`](reviews/2026-08-23-prompt-loop-graph-engineering-research.md). The
2026-08-23 owner disposition that held the five SRE capability additions is unchanged; this item is
an operating reference for graphs, not one of those additions.

**Decision required:** confirm that this direction is the renewed owner request the hold requires for
graph operations specifically, and name the first graph the team will operate.

**Prerequisites:** `GRAPH-002`'s consumer exists or a team-operated graph is named; otherwise the
references would describe a system nobody runs.

**Acceptance:** References added under the owning skills with a discovery near-miss keeping a live
graph outage with `sre`; one synthetic runbook and alert set reviewed against the research
requirements; no new agent, tool, or credential.

**Next action:** Owner confirms scope and names the first operated graph.

### GRAPH-004 — `codebase-atlas`: code, dependency, knowledge, and GraphRAG graphs

**Status:** `decision-needed` (2026-08-24)

**Owner:** to be named; `repository-investigator` is the nearest lane for local source structure.

**Outcome:** A separate capability with its own inputs, provenance, and success criteria for
import/dependency graphs, runtime topology, knowledge graphs, and GraphRAG — kept distinct from
`workflow-graph-engineering` (executable graphs) and `agent-authoring` (roster graphs), both of which
already carry near-miss scenarios that keep these requests out.

**Source:** Owner direction on 2026-08-24 (stage 2). The
[`2026-08-22 audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md) split graph engineering
into three contracts and deferred this one pending confirmed owner need.

**Decision required:** the operator need (which questions the atlas must answer), whether output is a
static analysis artifact or a retrieval index, the provenance and freshness contract, and the
consumer.

**Prerequisites:** none technical; a named need and owner.

**Acceptance:** to be defined with the decision; at minimum a positive discovery scenario, the two
existing near-miss scenarios remaining green, and no overlap with `workflow-graph-engineering`.

**Next action:** Owner names the need; until then no implementation.

### HOST-002 — measure VS Code tool enforcement and re-probe hook portability

**Status:** `active` (2026-08-25). F7's installed-Claude-CLI visibility gap is closed; the VS Code
boundary remains open.

**Outcome:** The guarded roles' VS Code posture rests on observed host behavior rather than
inference, and the fleet knows whether the read-only guard is portable to that host or whether
policy-delivered Copilot managed settings are the only real control there.

**Source:** A 2026-08-12 scan on two evidence bases: `[verified]` findings from the installed VS Code
1.133.0 bundle (tool-set vocabulary and Claude→VS Code equivalence match the host's enums;
`disable-model-invocation` is recognized; `runSubagent` delegation is unscoped; the hook surface
exists) and `[sourced]` findings at one remove from upstream `microsoft/vscode` @ `0157e11` and
`vscode-docs` @ `95cc3b3b` on configuration precedence. Those sources predict precedence; they do not
establish invocation authority on the current host.

**Evidence:** Three dated packets, each stating its exact build and keeping configuration evidence
separate from invocation authority.
[VS Code tool enforcement (2026-08-24)](reviews/2026-08-24-host-002-vscode-tool-enforcement.md):
every tested omitted built-in tool remained offered but disabled; enabling `execute` in the built-in
Agent picker was explicitly global and dirtied the generated-agent buffer without changing its
on-disk digest, proving a configuration/write-back path only. No command was submitted, so
invocation authority stayed `[unverified]`. The 2026-08-25 corrected reprobe on the same build
recorded a **measured negative** for that override path — switching to `sre` restored the custom
agent's set with `execute` offered-off — which disagrees with the prior same-build result and means
repeating the picker sequence cannot resolve the criterion. Sanitized transcripts and nine validated
envelopes are under [`docs/reviews/evidence/host-002`](reviews/evidence/host-002).
[`disable-model-invocation` on the Claude CLI (2026-08-25)](reviews/2026-08-25-host-002-disable-model-invocation-cli.md):
a paired disposable plugin canary on Claude Code 2.1.243 hid the guarded skill from model invocation
(`NOT_VISIBLE`, no Skill call) while explicit `/plugin:skill` invocation returned the marker. That
closes `GRAPH-001` F7 for that build without weakening the manual-only skills' body-level checks; it
establishes nothing about VS Code or Copilot hook identity. Hook scoping is `[verified static]` only:
VS Code 1.134.0 merges the selected custom agent's `hooks` before sending the request, and its
plugin-wide `PreToolUse` payload carries no custom-agent identity, so the viable candidate is a
generated `sre`-scoped hook rather than a self-scoping entry in `hooks/copilot-hooks.json`. No real
fleet hook is wired.

**Prerequisites:** An installed VS Code build with the GitHub Copilot tools surface and an
authenticated disposable test profile or other approved non-production session. The probe is
observational: it changes no live system, and it neither authorizes nor implies a Copilot hook
implementation.

**Acceptance:** A dated packet and durable, non-secret transcript/envelopes record whether the tools
picker offers `execute` to `sre`; whether an override changes the configuration; whether the active
generated buffer or on-disk file changes; and whether a safe invocation runs or receives an explicit
host denial. An operator-local artifact and hash are not closure evidence. Any hook-portability
finding is evidence only; wiring a Copilot hook is separate work needing its own review. Exact-agent
scope may be established by a hook attached to the selected custom agent; the global hook payload
does not need to invent an identity field it does not carry.

**Next action:** Run the probe's distinct agent-scoped hook canary in a disposable VS Code profile:
the custom canary must deny a harmless terminal request with its fixed marker, while the built-in
Agent control remains unaffected. Keep invocation authority open until a real tool call or host
denial is observed. Do not run a third identical picker retry, substitute a prompt-file override, or
populate `hooks/copilot-hooks.json`.

### SKILL-001 — make confirmed oversized skills conditional routers

**Status:** `active` (2026-08-24). Phase 1 is complete and closed as evidence; Phase 2 is the live
work.

**Outcome:** No skill spends a caller's context on detail the call did not need. Each screened
entrypoint receives one evidence/recommendation checkpoint. A confirmed conditional body becomes a
router with an "if the question involves X, read Y" table while retaining its authority and safety
invariants; a cohesive body is retained explicitly rather than split to satisfy a byte target.

**Source:** The initial measurement and reproduction command are in the
[`2026-08-17 skills surface sweep`](reviews/2026-08-17-skills-surface-sweep.md); the
[`complete skill audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md) corrected the
drifted candidate list. Description metadata follows the current rule — capability or user goal,
invocation conditions, and meaningful exclusions, without procedure — not the retired "trigger only"
doctrine. The
[`2026-08-24 host context-budget audit`](reviews/2026-08-24-host-context-budget-audit.md) separates
the host contracts that prompted Phase 2: Claude's 8,000-character default budgets the aggregate
discovery listing, its 5,000-token-per-skill and 25,000-token-total values govern post-compaction
invoked content, and Copilot's 30,000-character value applies to one generated custom-agent prompt.
None is the repository's 5,000-byte screen.

**Phase 1 (closed evidence):** The nine one-skill router slices merged in PRs #142, #143, #145, #146,
#147, #149, #150, #151, and #154. Per-slice candidate and merge identities, byte movement, reference
splits, review fixes, and the evidence gaps that remain open elsewhere are in the
[Phase 1 closure review](reviews/2026-08-24-skill-001-phase-1-closure.md). That review is historical
evidence; the nine skills are excluded from Phase 2 and are not a candidate pool to rerun.

**Phase 2 screen:** `[verified]` On exact base `b9b274f237caf8ce6068812e151f8543f608c7e7`, twelve
non-Phase-1 entrypoints sit at or above 5,000 immutable bytes, totaling 95,068: `frontend-craft`
13,827; `backend-craft` 10,814; `obs-dashboards` 10,724; `agent-authoring` 9,420; `obs-alerting`
7,656; `runbook` 7,385; `gcp-ops` 7,384; `operational-learning` 6,078; `eng-ladder` 5,873;
`obs-pipeline` 5,835; `root-cause` 5,048; `obs-traces` 5,024. Selection means inspect, not rewrite;
size alone is not a finding. Separately, `[verified]` the same base carries 28 model-invocable skills
whose discovery metadata totals 13,239 characters, 5,239 above the installed CLI 2.1.241 default
fallback; no individual description reaches 1,536 characters. Exact real-session truncation remains
`[unverified]`, and this discovery risk does not authorize a description rewrite inside Phase 2.

**Prerequisites:** All Phase 1 slices are closed. Phase 2 starts from refreshed exact `origin/main`,
excludes the completed nine skills, and processes one screened entrypoint only after its
evidence/recommendation checkpoint. Description edits follow the routing-content change playbook.

**Acceptance:** The exact-base remeasurement names every non-excluded entrypoint at or above 5,000
immutable bytes. Each receives one committed disposition: a confirmed router either drops below the
screen or routes more reference bytes than it retains, with every target reachable through
`check_links`; a retained entrypoint records why no clean conditional boundary exists. Rerunning the
recorded measurement returns no **undispositioned** candidate. Entrypoints retain all authority and
safety invariants. Each changed description passes the 600-byte and `Triggers:` contracts and has an
after-change overlapping scenario run; a previous-revision baseline is required only for an existing
scenario that returns red. Gate A green.

**Next action:** Inspect `frontend-craft` alone on the exact Phase 2 base because it is the largest
selected entrypoint and already owns substantial routable reference depth. Present its retained
invariants, proposed conditional boundaries, expected byte movement, and recommendation before
changing its bytes. Do not start a second skill, requeue a completed Phase 1 skill, rewrite discovery
descriptions, or combine the already-owed `eng-ladder` after-change run with this checkpoint.

### EVIDENCE-001 — stop losing measurement evidence by default

**Status:** `ready` (2026-08-25)

**Owner:** `agent-engineer` owns the eval and acceptance evidence paths; `latent-sre` accepts the
exact revision.

**Outcome:** Evidence from a paid measurement survives the session that produced it, without
depending on someone remembering to copy it into a committed document.

**Source:** Three losses in one line of work, all `[verified]`: the `GRADER-003` incumbent baseline
batch `20260824T231543Z-53c0a77c` vanished with a removed worktree; `.eval-runs/` is gitignored, so
all three verification batches would have been lost had their findings not been hand-copied into
[the batch record](reviews/2026-08-25-grader-003-verification-batch.md); and the acceptance 3
harness persisted three of five agent transcripts, leaving two completed cases ungradable
([result](reviews/2026-08-25-skills-003-acceptance-3-result.md)). Each loss cost either a re-run or
a permanent gap in an acceptance record. The common cause is that measurement output lands
somewhere ephemeral by default and survives only by an unenforced human habit.

**Prerequisites:** None. This is repository tooling, not a fleet-authority change.

**Acceptance:** A paid measurement's evidence is committed by construction, not by convention.
Minimally: a documented capture step that extracts the durable summary from a batch or exercise
into `docs/reviews/` before the ephemeral store can be reclaimed; a check that a roadmap item citing
a batch ID can resolve it to committed evidence; and a stated retention boundary saying what is
deliberately *not* kept — raw transcripts are large and may carry untrusted content, so the
requirement is the summary, the identities, and the verbatim phrasings a future reader would
otherwise have to re-run to recover. Do not solve this by committing raw transcripts wholesale.

**Next action:** Inventory where each measurement type currently writes — `.eval-runs/`, agent task
output files, session scratchpads — and which of those the repository can reach at the moment a run
finishes. Propose the capture step against that inventory before writing any tooling.

### GRADER-003 — repair the `agent-authoring` discovery behavioural graders

**Status:** `active` (2026-08-25) — `latent-sre` approved **all three** shapes, and they compose:
direct mode now carries the behavioural contracts at full strength, discovery keeps a routing floor
of three-to-four graders, and the discovery positives run at `threshold: 0.66` because discovery
measures a propensity rather than a contract. Applied and **measured**: see the two batches below. The instrument defect is diagnosed and fixed, and a
second, larger constraint was then measured: **contract shape**. Five discovery batches under
identical conditions gave 0/12, 4/12, 9/12, 8/12, **12/12**; `trigger-and-shape` went 3/3 then 1/3
**with no change made to it**, so the 9/12 was a lucky sample rather than progress, and the closing
12/12 is the new shape. Routing is `[verified]` **48/48** across every revision with no misroute
anywhere. **Fifteen** reds traced, zero behavioural defects. Evidence:
[the verification batches](reviews/2026-08-25-grader-003-verification-batch.md).

**Owner:** `agent-engineer` owns the evaluator text; `latent-sre` accepts the exact revision.

**Outcome:** The four `agent-authoring` discovery scenarios grade what a correctly routed response
actually contains, so a red in that set means a routing or behaviour defect rather than evaluator
vocabulary.

**Source:** The `SKILLS-003` implementation packet dispositioned this `proposed to roadmap` and it
was never filed. Its incumbent baseline run `20260824T231543Z-53c0a77c`, taken on `origin/main`
bytes with no candidate present (Sonnet, 3 trials, 600 s), scored **0/4 scenarios and 0/12 trials
with no routing failure in any trial** — every red a behavioural `contains_any` on vocabulary the
real transcripts did not use. A description edit cannot change response content, so this is an
incumbent evaluator defect that the SKILLS-003 change neither caused nor fixed. Evidence:
[the SKILLS-003 packet](reviews/2026-08-24-skills-003-workflow-graph-engineering.md).

**What the defect actually was.** `[verified]` by reading each scenario against its own prompt: in
every case the grader demanded vocabulary the prompt never requested. `loop-engineering` asked for
"hard iteration/candidate/time/cost budgets" and "promotion authority" while grading for
`maximum iterations` and `human acceptance`; `trigger-and-shape` asked to "name the adoption and
stop conditions" while grading only for `adoption authority`; `workflow-graph` asked for "allowed
edges" and "handoff/join" while grading for `delegation edge`. These are exactly the terms the
baseline recorded as red. No transcript was needed to see it, which is why the lost batch stopped
mattering.

**Treatment applied.** One `not_fire` near miss (`defers-code-dependency-graph`) became
routing-only, the structural twin of the workflow-graph case. The three positives keep their
behavioural contracts — the graded response is `agent-authoring`'s own — with their graders moved
to what the prompt requests. **Prompts were not edited**: a discovery prompt is the routing
stimulus, so changing one re-opens the routing measurement, and the existing evidence (12/12
correct, no routing failure on either revision) had to survive. `[verified]` the diff touches only
grader term-sets, comments, `threshold`, `success_criteria`,
and three new scenario files -- **not** prompts. An earlier revision of this sentence said "only grader term-sets
and comments", which the same diff falsified: a threshold is a scoring rule, and changing it changes
what red means. Corrected after review rather than left standing.

**Guard against recurrence.** `test_discovery_positives_grade_only_what_the_prompt_requests`
requires each positive to declare, in `_AGENT_AUTHORING_BEHAVIOR_PROMPT_TERMS`, the prompt terms
carrying its graded behaviours — the `_OBS_BEHAVIOR_PROMPT_TERMS` shape. It is deliberately *not*
derived from grader tokens: a grader should demand artifact-level vocabulary the prompt does not
contain, because that is what keeps a prompt echo from passing. Two findings came out of building
it, both `[verified]`: bare `"AST"` matched `last`/`past`/`broadcast` under substring matching and
is now spelled out; and in two scenarios a single grader was silently the only one rejecting the
prompt echo, so widening it with the prompt's own wording let the echo pass the whole set. Both are
recorded in the scenario comments.

**Prerequisites:** None outstanding. The two the packet implied are resolved: the baseline
transcripts are `[verified]` gone — that batch ran in the since-removed `.worktrees/graph-program`
and is absent from every `.eval-runs` directory here — and the treatment chosen does not need them,
because the mismatch is visible in each scenario against its own prompt. Any *further* grader
widening does need a transcript first.

**Measured results.** Three candidate batches plus the incumbent baseline. Same model, trials,
timeout, and threshold throughout (Sonnet, 3 trials, 600 s, threshold 1.0); the CLI differed —
2.1.241 for the incumbent baseline, 2.1.245 for the three candidates:

| Batch | Candidate | Trials green | Routing | Cost |
|---|---|---|---|---|
| `20260824T231543Z-53c0a77c` (incumbent) | `origin/main` bytes | 0/12 | 12/12 | — |
| `20260825T174112Z-498600c4` | `90bd33e` | 4/12 | 12/12 | USD 3.54 |
| `20260825T183911Z-ea5961ab` | `95a017a` | 9/12 | 12/12 | USD 3.23 |
| `20260825T192519Z-4b6fe947` | `16a236d` | 8/12 | 12/12 | USD 3.88 |

**Finding 1 — the instrument (fixed).** `contains_any` is a plain substring test and cannot express
these contracts. Fifteen reds were traced to their transcripts across six batches and **not one was
a behavioural defect**: they were defeated by a markdown label, a hyphen, word order, a word
boundary, an unadmitted method, a numeric bound, and a singular. Eight graders moved to bounded
`regex`; `workflow-graph`'s delegation-edge behaviour now grades structurally, because a correct
answer's words there are the prompt's own words and no token can both match the answer and reject
the echo.

**Finding 2 — the contract shape.** This is what moved the item to `decision-needed`; the owner
has since chosen all three shapes, so the item is `active` again. These
scenarios are conjunctions: every positive grader must pass in all three trials. `loop-engineering`
has 7 positive graders, so 21 grader-trials — even at 97% per grader-trial its chance of a clean
sweep is 0.53. `trigger-and-shape` is 0.58. The one scenario that reached 3/3,
`defers-code-dependency-graph`, has a single grader. The ceiling is set by conjunction length, not
by grader quality, which is why the third batch went down rather than up. No further grader edit was
made after that batch: widening cannot fix this.

**Acceptance:** Instrument work is complete and three times measured: `test_graders` 665/665,
`--validate` OK at 94 scenarios, Gate A 6/6, generator byte-clean,
`claude plugin validate . --strict` PASS, the prompt-alignment invariant proven red for its named
reason, and every batch recorded with transcripts summarised in a committed document rather than in
gitignored `.eval-runs/`. The regression split stays red until the contract shape is decided — an
honest red reflecting a contract the suite cannot satisfy, not a fleet defect.

**Applied (2026-08-25).** Three direct-mode contracts were added —
`agent-authoring-loop-contract`, `agent-authoring-trigger-and-shape-contract`, and
`agent-authoring-roster-graph-contract` — each `calibration` until a measured pass, per
`evals/README.md`. The three discovery positives keep only an identity grader, an echo-rejector,
and their anti-pattern guards, and each **names the direct scenario that now holds its contract**.
`test_trimmed_discovery_positives_have_a_direct_contract` enforces the pairing in both directions:
it fails if a paired contract is missing, and it fails if a discovery case is re-inflated back into
a contract. Both failure modes were proven red for their named reason and restored. Offline:
`test_graders` 726/726, `--validate` OK at 97 scenarios (30 direct), Gate A 6/6, generator
byte-clean, `claude plugin validate . --strict` PASS.

**Measured (2026-08-25).** Two batches under the standing conditions. Discovery
`20260825T214004Z-ab8dff39` on `ce0278a`: **4/4 scenarios, 12/12 trials, routing 12/12**, USD 3.44 —
the trimmed shape passes cleanly on unseen trials, which the old shape never did in three attempts.
Direct `20260825T225402Z-8ff050e2` on `b8dea04`: **8/9 trials**, skill fired 3/3 on every contract,
USD 2.70; `agent-authoring-loop-contract` and `agent-authoring-trigger-and-shape-contract` measured 3/3 and
`agent-authoring-roster-graph-contract` measured 2/3. A second direct batch
`20260825T233556Z-5fb69d7b` then measured **3/3, 3/3, and 2/3** — `roster-graph-contract` improved
because the widened proximity window fixed its two-character miss, and **`trigger-and-shape-contract`
went 3/3 → 2/3 with no change made to it**. That is the whole argument for not promoting on one
clean batch, and it is why `7c88f57` reverted the promotion made on batch 5: the reverted scenario
is precisely the one that later measured 2/3. **All three stay `calibration`** — and under
`AGENTS.md` promotion is not an eval outcome at all, only human acceptance of the exact revision. Its single red is the fourteenth traced on this item and the fourteenth with
the behaviour present: a `read-only … review` proximity grader allowed 40 characters and the answer
put 42 between them. Discovery trials across five batches: `0/12 → 4/12 → 9/12 → 8/12 → 12/12`;
routing `[verified]` **48/48**; **fourteen reds traced, zero behavioural defects**.

**Stated rather than implied:** the threshold relaxation made **no observable difference**. Every
discovery scenario passed 3/3, so the 2-of-3 bar absorbed nothing and `threshold: 1.0` would have
given the same result. Option 2 is verifiably in force — the bar computes to 2 of 3 against
`run_evals.py:1113` — and was simply not exercised. `[unverified]` the post-batch widenings (the
80-char proximity window, the Mermaid arrow forms, the `go list` boundary, the `scoring`
inflection) have not been measured; each is a pure widening on a scenario that already passed, so
none can have turned a pass into a fail.

**Measured (2026-08-26).** Batch `20260826T000538Z-2b8d7cc5` closed the last gap: the two graders
rewritten on this branch but never measured — `defers-code-graph` (sole grader, `split: regression`,
so it gates) and `defers-runtime-selection` — both returned **3/3**, and all three regression
scenarios in that suite passed 3/3. 14 of 15 trials passed; the fifteenth was a clean 600 s harness
timeout that produced no response, so the batch verdict is `INCONCLUSIVE` rather than PASS.
**No grader on this branch is reasoning-only any more.** Routing is `[verified]` 62/62 conclusive.

**Accepted (2026-08-26).** `latent-sre` accepted the exact PR #170 head `9079ab3`. That is the
promotion step `AGENTS.md` reserves to a human; no eval result contributed to it. On merge,
`SKILLS-003` moves to the closed table — its independent exact-revision review requirement is met
by the four review rounds on this branch, all bound to stated revisions.

**Next action:** Merge PR #170. Then move `SKILLS-003` to the closed table with its structural,
routing, artifact, and review evidence recorded separately rather than conflated. `GRADER-003`
keeps its remaining item — the three direct contracts stay `calibration`, and promoting any of them
is a separate owner decision, not an eval outcome. `EVIDENCE-001` stays `ready` and is worth taking
before the next paid run. If accepted, close the
GRADER-003 instrument and shape work and leave one follow-up: a batch that exercises the widened
graders, which would let `agent-authoring-roster-graph-contract` earn `regression`. Do not widen a
grader further without reading the transcript that failed it, and do not edit a discovery prompt —
it is the routing stimulus and the 48/48 routing evidence depends on it staying byte-identical.

### ROUTE-003 — remeasure workflow-graph and service-readiness discovery reliability

**Status:** `deferred` (2026-08-23)

**Owner:** `latent-sre`

**Outcome:** The two positive discovery routes left inconclusive by Batch 1 have reproducible,
model-labelled reliability evidence before either is promoted into a stronger routing claim.

**Source:** Batch 1 run `20260823T053852Z-1e677acb` timed out both workflow-graph trials. Closeout
run `20260823T131840Z-9e4c7fca` on merged commit `09e775b`, Claude Code 2.1.241, `claude-sonnet-5`,
two trials, and a 180-second timeout passed read-only service readiness 1/2 and timed out the second
trial. The exact dispositions are in the
[`skill clarity and routing audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md).

**Prerequisites:** A material routing, evaluator, host, or model change that can alter the result, or
explicit owner approval of a fixed no-tuning measurement budget. Use a clean exact plugin revision
and predeclare model, timeout, trials, threshold, and selected scenarios.

**Acceptance:** The workflow-graph and service-readiness cases each meet their declared threshold on
the exact candidate under the predeclared conditions, with no overlapping regression loss. A failed
or inconclusive batch remains evidence; it does not authorize prompt edits or retries without a
separately accepted fleet failure and candidate budget.

**Reopen trigger:** A material change to either route or its evaluator/runtime boundary, a named
model-migration question, or explicit owner approval for one fixed-budget reliability measurement.

**Next action:** None while deferred. Do not rerun unchanged bytes merely to turn timeouts green, and
do not move reference-dependent behavior graders into discovery.

### ROUTE-002 — resolve the `obs-logs` / `obs-alerting` trigger collision

**Status:** `active` (2026-08-20) — kept open: the "no other overlapping scenario moved" half of
acceptance is not yet evidenced.

**Outcome:** One skill owns log-based alert design **in the canonical text**, and the routing suite
contains a scenario that would fail if the other started firing for it. Both halves are required: the
descriptions must state the boundary, and a scenario must be able to detect a regression.

**Source:** The [skills surface sweep](reviews/2026-08-17-skills-surface-sweep.md) found that
`obs-logs` advertised `'build a log alert'` without disclaiming `obs-alerting`, while the suite had no
near-miss scenario that could detect the collision. `[verified]` In PR
[#122](https://github.com/latent-sre/save-toolkit/pull/122) the exact base routed the new case 1/2;
after the ownership-map fix it routed 2/2 on both recorded models, and canonical `obs-logs` now names
`obs-alerting` explicitly. The literal-grader defect fixed in `19aaa52` was not routing evidence. The
[round packet](reviews/2026-08-19-obs-skill-hardening-round.md) retains prompts, revisions, and raw
results.

**Prerequisites:** None structural. The remaining verification needs the live runner.

**Acceptance:** Both conditions are required: (1) canonical text disambiguates ownership by removing
the conflicting trigger or naming `obs-alerting`; and (2) the deferral scenario and every other
overlapping scenario pass after the edit. Run a prior-revision baseline only for a red scenario.

**Next action:** Establish the missing half of acceptance — run the *other* overlapping
`obs-alerting`/`obs-logs` scenarios against the changed descriptions and show they remain green. If
one is red, run that scenario at the prior revision to attribute it. Then close. Do not close on the
defer scenario alone.

### SURFACE-001 — trim the user-facing surface (banner, retracted examples, shipped maintenance bytes)

**Status:** `ready` (2026-08-13; progress 2026-08-23) — remaining: the two example-footnote
compactions. The maintenance skills remain bundled by owner decision.

**Outcome:** A user who opens any canonical skill reaches actionable content within a few lines: the
shared evidence-default banner is gone, worked examples carry provenance as a single footnote instead
of a paragraph retracting the example, retired learning packet/ledger machinery no longer ships in
every install, and the packaging question for maintenance skills has a recorded decision.

**Source:** The 2026-08-13 owner review measured the same four-line banner on all 29 then-current
entrypoints, about 249 lines of provenance boilerplate, and two worked examples that retracted
themselves: the `pcf-deploy` manifest interaction and `runbook` footer. The banner and retired
learning packet/ledger paths were removed. The owner retained the maintenance bundles because no
named consumer impact had been measured; only the two footnote compactions remain.

**Prerequisites:** None blocking. By owner decision the maintenance skills stay in the shared
package: no current measurement shows that their install size or discovery surface harms a named
consumer. Reopen that packaging decision only with measured consumer impact attributable to those
bundles.

**Acceptance:** No shared evidence-default banner remains and adapters regenerate byte-clean; the two
self-retracting examples keep their labels as one-line footnotes; the retired learning packet and
ledger paths remain absent; Gate A passes; operational closeout still produces evidence-bound
documentation dispositions and owners without execution authority.

**Next action:** Compact the provenance paragraphs in the `pcf-deploy` and `runbook` worked examples
to one-line footnotes. Keep the maintenance skills together unless the measured-impact reopen trigger
fires.

## Deferred

### EFFECT-001 — effect-bound execution broker

**Status:** `deferred`

**Outcome:** If protected automation is ever allowed to perform a live effect, approval is bound to
one exact action, target, argv/executable digest, expiry, nonce, rollback, and replay ledger.

**Source:** Fleet authority reviews that reject prose approval and require an explicit
unknown-outcome state for externally dispatched effects.

**Prerequisites:** A named workflow approved to cross the current prepare/recommend boundary, a
separately controlled execution identity, and live `main` ruleset enforcement as recorded in
[`docs/reviews/2026-08-05-protect-001-closure.md`](reviews/2026-08-05-protect-001-closure.md).

**Acceptance:** Effect-bound approval, dispatch, unknown-outcome reconciliation, replay prevention,
expiry, rollback, and operator-resolution tests pass for the named effect target.

**Reopen trigger:** A named workflow is approved to move beyond the fleet's current prepare/recommend
boundary and has a separately controlled execution identity.

**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority.
