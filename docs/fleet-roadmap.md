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
