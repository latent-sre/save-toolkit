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

## Closed items

One row per closed item. The row is the disposition; the linked document is evidence, never a task
list. An item with no surviving evidence document closed into a live contract instead, named here.

| Item | Closed | Disposition and evidence |
|---|---|---|
| `SAFE-001` | 2026-08-01 | Research trust zones split into local-only and external-only roles, and evidence normalized. Contracts: [`local-external-research-separation`](decisions/2026-07-31-local-external-research-separation.md) and [`schema-compatibility.md`](schema-compatibility.md) |
| `IMPROVE-001` | 2026-08-01 | Bounded improvement lifecycle. Its executables were parked at tag `pre-trim-2026-08-02` and no record advances past `observed`/`rejected` while they are — [closure](reviews/2026-08-01-fleet-improvement-closure.md) |
| `VERIFY-001` | 2026-08-02 | Executable verification isolated. Contract: [`verification-sandbox.md`](verification-sandbox.md) |
| `PROTECT-001` | 2026-08-05 | Repository protection and distinct promotion identity — [closure](reviews/2026-08-05-protect-001-closure.md) |
| `HOST-001` | 2026-08-06 | Host installation proof — [closure](reviews/2026-08-06-host-001-closure.md) |
| `ADAPT-001` | 2026-08-06 | Sibling-repo adaptations; its review history records defects Gate A was green over — [closure](reviews/2026-08-06-adapt-001-closure.md) |
| `SWEEP-001` and `MUTATION-001` | 2026-08-21 | Closed by **explicit owner disposition**, not a closure review: `not_applicable` as live work, owner `latent-sre`. No survivor count established a broken contract; the disposition does not assert every survivor was harmless. Diagnostic: [fleet mutation sweep](reviews/2026-08-15-fleet-mutation-sweep.md) |
| `EVAL-002` | 2026-08-22 | Agent-target discovery is calibration, never a regression gate — [ADR](decisions/2026-08-22-agent-discovery-calibration.md) |
| `REVIEW-001` | 2026-08-22 | Independent exact-SHA review is required for a production deployment of new bytes, not for every merge — [ADR](decisions/2026-08-22-production-review-boundary.md) |
| `NAV-001` | 2026-08-22 | Incident-navigation rejected and archived — [ADR](decisions/2026-08-22-incident-navigation-archive.md) |
| `GCPOPS-001` | 2026-08-22 | Canonical `gcp-ops` now states that a quoted `severity>=ERROR` filter is guard-safe while the unquoted shell-redirection spelling is denied, and the focused guard corpus locks both outcomes. Correction commit `c989103`, final PR head `f5235c1`, merged in PR [#137](https://github.com/latent-sre/save-toolkit/pull/137) at `e96e741` |
| `RELEASE-001` | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. The custom publication workflow, request/workflow contracts, release-specific tests, runbook, and the standalone four-host probe were never activated and had no named consumer; they were retired rather than maintained. The `release-gate` skill, manifest versions, and changelog history remain. Historical design ADR: [`superseded`](decisions/2026-08-11-immutable-release-promotion.md). Reopen only when a named consumer requires an immutable selector and rollback-capable release |
| `STATE-001` | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. It described a future durable-execution control plane with no named workflow, implementation, or active dependency; handoffs and learning derive ownership and completion from Git, pull requests, tests/evals, and evidence. Reopen only when a named workflow must survive process or session loss and replay from version-bound artifacts would be unsafe or materially costly |
| `EVAL-001` | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. Its only named trigger was a release decision, the parked suite no longer matches the current plugin identity or roster, and Codex stopped being a distribution target — no fleet component runs on Sol, so the trigger can no longer fire. Tag `pre-trim-2026-08-02` preserves the historical bytes — [ADR](decisions/2026-08-23-retire-codex-distribution-target.md) |
| `AUDIT-002` (Batch 1) | 2026-08-23 | `not_applicable` by **explicit owner disposition**, owner `latent-sre`. Implementation and review corrections merged in PR [#141](https://github.com/latent-sre/save-toolkit/pull/141) at merge commit `09e775b`, final head `11b8041`. Batch 1 selected no graph runtime, added no unconsumed schema, and activated no SRE capability addition; two positive-route reliability gaps moved to deferred `ROUTE-003` rather than triggering retries against unchanged bytes. Evidence: [`2026-08-22 skill clarity, routing, prompt, loop, and graph audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md) |
| `DOCTOR-001` | 2026-08-23 | Installed-layout `fleet_doctor` now separates checkout and plugin evidence, validates each payload's first authenticated guard answer and independently trusted launcher bytes, and degrades repository-only checks outside a checkout. Final head `505f9b5`, merged in PR [#152](https://github.com/latent-sre/save-toolkit/pull/152) at `e76d38b` |
| `GRADER-002` | 2026-08-24 | Direct-skill trials explicitly request the exact `Skill` invocation and still require its completed tool result; availability-only metadata and inline answers fail closed. Implementation commit `ec6e583`, paired approved/missing-authority evidence matched the committed evaluator digest, merged in PR [#155](https://github.com/latent-sre/save-toolkit/pull/155) at `24e62b0` |

The local Sol evaluator decision is recorded separately in
[`2026-08-01-local-sol-conformance.md`](decisions/2026-08-01-local-sol-conformance.md).

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

## Active runtime work

### WF-001 — establish a supported exact-dispatch boundary for Claude workflows

**Status:** `blocked`

**Outcome:** The repository carries no executable `ship-review` workflow until Claude provides a
supported way to dispatch one exact trusted workflow without granting caller-supplied workflow code.

**Source:** A version-pinned probe on Claude Code 2.1.221 found two incompatible behaviors. Setting
`CLAUDE_WORKFLOW_NAME_ONLY=1` suppresses inline-plugin workflows, so the trusted workflow cannot be
loaded. Without that flag, a native permission for `Workflow(save-toolkit:ship-review)` also admits
an input containing the same `name` plus caller-supplied `script`; the resolver executes that script
override. A plugin `PreToolUse` hook can deny the override, but the resulting launcher, hook receipt,
Git-object isolation, and upgrade matrix were a bespoke security broker disproportionate to this
fleet. That experiment was removed rather than shipped as a fragile control plane.

**Upstream check (2026-08-18):** Claude Code 2.1.227's built-in `claude ultrareview` removes the
caller-supplied workflow-body surface but exposes no immutable reviewed-subject identity and no
findings-sensitive verdict — it exits 0 either way, bundles a mutable tree, and uploads to a paid
cloud sandbox. Still blocked. Sources and queries: the
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

**Owner:** `latent-sre` owns the architecture decision and acceptance of the exact generic-alpha revision.
`prompt-engineer` owns consumer context-requirement semantics for agents/skills; `sde` owns any
later resolver, validator, or onboarding-tool implementation. A team owner becomes accountable for
values and operational documents only when that team separately opts into onboarding. No owner may
approve its own unreviewed evidence.

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
context contract, a central-repository assessment, and 24 architecture deliverables before
implementation. The dated
[`generalized SRE team and application context framework`](reviews/2026-08-24-sre-context-framework-architecture.md)
records the current-repository assessment; separate Context7, GitHits, and official-standard
research; alternatives; proposed entity and requirement schemas; resolution, identity, provenance,
validation, safety, examples, exclusions, and the staged plan. It recommends a central Git authoring
repository first while keeping the logical contract source- and transport-independent.

**Decision required:** Accept or revise these load-bearing choices before implementation:

1. `Service` is the deployable/operable unit; optional `System` represents a composite application.
2. `Environment` is a logical safety/policy profile; a separate `Deployment` binds a service to its
   PCF, Cloud Run, Kubernetes, endpoint, deployment, and observability identities.
3. The first source is a separate central Git repository, while the resolver contract permits
   approved federated sources later without changing skills.
4. Skills own versioned context-requirement sidecars; team data owns values; an undocumented skill
   frontmatter key is not introduced.
5. V1 removes duplication through typed references and has no general inheritance or deep merge.
6. Runbooks may live centrally or with their owning service repository; the registry indexes both
   and never copies executable automation definitions.
7. A file/CLI resolver is phase one. Backstage, commercial catalogs, federation, generated
   discovery, and MCP are later adapters or decisions, not prerequisites.
8. Git stores curated facts and references only. Live state remains in its authoritative system,
   and platform-generated identifiers carry qualified names and freshness/provenance.

The
[`source-independent SRE operational-context contract`](decisions/2026-08-24-sre-operational-context-contract.md)
now records the accepted generic contract, consequences, rejected alternatives, failure modes,
rollback, and staged scope. Owner approval on 2026-08-24 authorizes stages 1–3 only; it does not
authorize real-team onboarding or effect-capable adoption.

**Prerequisites:** An accepted decision record names the schema/contract owner, resolver owner,
source repository and permissions, generic fixture policy, representational platform shapes, and the
alpha compatibility window. No real team or service values are prerequisites. Reinspect the exact
consumer skill, generator/package behavior, dependency policy, and current schema catalog before
naming implementation files. Any third-party validator or YAML parser is pinned in
`requirements-dev.txt` and follows the CI/Gate A dependency rule. No central repository, schema,
resolver, MCP server, skill rewrite, or live discovery job is created solely from this roadmap entry.

**Acceptance:** All conditions are required and retain separate evidence labels:

1. **Architecture:** The accepted ADR disposes every decision above and retains the proposal's 24
   deliverables, rejected alternatives, static/live boundary, secrets boundary, rollout, rollback,
   and explicit non-goals. A design review is not runtime proof.
2. **Source contracts:** Immutable versioned JSON Schema 2020-12 contracts exist for the minimum
   Team, Service, optional System, Environment, Deployment, Repository, Integration/Resource,
   Runbook metadata, consumer requirement, and resolved-bundle shapes. Known objects fail closed;
   formats and YAML
   duplicate keys are tested with the selected validator rather than assumed.
3. **Semantic resolver:** Exact source/revision and canonical selectors produce deterministic,
   byte-bounded output with source provenance. Duplicate IDs/aliases, broken or kind-wrong refs,
   forbidden cycles, zero/multiple deployments, missing required paths, implicit production,
   secret-bearing fields, traversal, and nondeterministic output have named red-first regressions.
4. **Identity and repositories:** Catalog IDs, display names, typed/scoped aliases, platform IDs,
   telemetry mappings, and runtime instance IDs remain distinct. Repositories are first-class and
   every service relationship states one or more provisional roles plus why the repository matters;
   `other` never becomes an untyped escape hatch.
5. **Generic portability proof:** At least two explicitly synthetic team fixtures, multiple services,
   multiple repositories, production-classified and non-production environments, and at least two
   platform representations validate without a team-specific schema or skill branch. The same
   `service-readiness-audit` requirement contract resolves representative selections and refuses
   missing/ambiguous selections. Fixture sources require explicit opt-in, use reserved example
   locators, preserve a non-operational marker, and prohibit action selection.
6. **Context behavior:** Required and alternative JSON Pointer paths fail closed; optional absence
   remains explicit; the resolver expands only requested references within declared depth/byte
   budgets. A fresh-context exercise demonstrates deterministic lookup and preserved canonical
   facts, provenance, target classification, and omissions; it does not claim production
   correctness from structural green.
7. **Truth and safety:** The repository contains no secret or copied live state. Qualified platform
   mappings and external locators name their authority and validation evidence where freshness is
   material. An effect-capable path separately proves that context cannot default to production,
   approve an action, supply a credential, or bypass the existing production/effect gate.
8. **Onboarding and operations:** Synthetic acceptance proves that a new team can add
   team/service/environment/deployment, repository, integration/observability, Jira/Confluence, and
   runbook references and receive clear validation output without editing a generalized skill. Real
   onboarding is a later team-owned adoption step using the identical contracts. Ownership, schema
   migration, stale-link diagnostics, source-repository recovery, and resolver troubleshooting are
   documented.
9. **Integrated verification:** Focused schema/resolver/consumer regressions, affected offline
   routing or behavior checks, adapter generation where canonical skill bytes change, strict plugin
   validation, `git diff --check`, Gate A at the push boundary, and independent exact-revision
   correctness/security plus roadmap-plan conformance review all pass. Each result states what it
   proves and what remains unverified.

**Closure:** Merge the accepted generic alpha and its exact synthetic evidence, record the supported
alpha contract and next migration boundary, then move `CONTEXT-001` to the closed table. Fleet-wide
adoption, federation, Backstage/MCP adapters, automatic discovery, live reconciliation, or a general
overlay language are separately justified work and do not silently expand this item.

**Next action:** Create the approved private `latent-sre/sre-context` repository and implement stages
1–3: contract skeleton, first synthetic-tenant read-only proof, and second synthetic-tenant
portability proof. No team-specific values are required. Do not onboard a real team or rewrite fleet
skills beyond the accepted generic consumer contract in this stage.

### HOST-002 — measure VS Code tool enforcement and re-probe hook portability

**Status:** `active` (2026-08-24) — a disposable authenticated VS Code 1.134.0 profile measured the
picker's configuration and buffer-write behavior, but no `execute` call or host denial ran and the
raw transcript/envelopes remain operator-local. Invocation authority and durable review evidence
therefore remain open acceptance gaps.

**Outcome:** The guarded roles' VS Code posture rests on observed host behavior rather than
inference, and the fleet knows whether the read-only guard is portable to that host or whether
policy-delivered Copilot managed settings are the only real control there.

**Source:** A 2026-08-12 scan on two evidence bases. `[verified]` from the installed VS Code
1.133.0 bundle (`workbench.desktop.main.js`, build `a5b500951314efd502d07465bd138dfbd714a960`): the
generator's tool-set vocabulary and its Claude→VS Code equivalence table match the host's enums;
`disable-model-invocation` is a recognized key; `runSubagent` delegation is unscoped; the hook
surface (`chat.useClaudeHooks` and friends) exists. `[sourced]` at one remove — upstream
`microsoft/vscode` @ `0157e11` and `vscode-docs` @ `95cc3b3b`, read by the research lane and not
confirmed here: omitting a tool sets an explicit `false`; session selection outranks the agent
file; only extension agents are read-only; the picker writes the user's change back; a prompt
file's `tools:` outranks a referenced agent's. Those sources predict configuration precedence; they
do not establish invocation authority on the current host.

**Current environment:** `[verified]` On 2026-08-24, `code --version` reported VS Code 1.134.0,
commit `110a328ea54b42367b803ec53ee0bf52ef26b419`, x64. The installed extension list contains
development, operations, Claude, and OpenAI tooling, but neither GitHub Copilot extension named
above. This establishes only that the approved probe cannot start here, not any tool-enforcement
behavior.

**Measured evidence (2026-08-24):** `[verified]` The
[`HOST-002 VS Code tool-enforcement packet`](reviews/2026-08-24-host-002-vscode-tool-enforcement.md)
records VS Code 1.134.0 at commit `110a328ea54b42367b803ec53ee0bf52ef26b419` with built-in Copilot
Chat 0.62.0. Every tested omitted built-in tool remained offered but disabled. `sre` offered
`execute` off by default; enabling it in the built-in Agent picker was explicitly global, survived
the switch to `sre`, and dirtied the open generated-agent editor buffer without changing its
on-disk digest. This proves a configuration/write-back path only. No command was submitted after
that clean-file precondition failed, so whether `sre` can invoke `execute` or the host denies it is
`[unverified]`. The buffer, picker defaults, file digests, Git status, and Gate A 6/6 were restored.
The transcript and envelopes are bound by local hashes but are not yet in a durable reviewable
location, so they cannot close HOST-002. Hook identity/portability remains unverified and no hook
was wired.

**Prerequisites:** Use an installed VS Code build with the GitHub Copilot tools surface and an
authenticated disposable test profile or other approved non-production session. The probe is
observational: it changes no live system, and it neither authorizes nor implies a Copilot hook
implementation.

**Acceptance:** A dated packet and durable, non-secret transcript/envelopes record whether the tools
picker offers `execute` to `sre`; whether an override changes the configuration; whether the active
generated buffer or on-disk file changes; and whether a safe invocation runs or receives an explicit
host denial. It states the exact build and keeps configuration evidence separate from invocation
authority. An operator-local artifact and hash are not closure evidence. Any hook-portability
finding is evidence only; wiring a Copilot hook is separate work needing its own review.

**Next action:** Run the corrected probe in a new disposable profile. Keep the generated editor
buffer clean, then observe the safe `git status --short` call or an explicit host denial and retain
the non-secret transcript/envelopes in an approved durable review location without adding the
operator-local ZIP. Do not populate `hooks/copilot-hooks.json` before a separate probe shows that
its payload can scope to an exact agent identity.

### SKILL-001 — make confirmed oversized skills conditional routers

**Status:** `active` (2026-08-24) — all nine Phase 1 router slices are merged: `incident-command` in
PR #142, `ops-tooling` in #143, `agent-security` in #145, `ci-actions` in #146, `pcf-deploy` in #147,
`pcf-ops` in #149, `production-change-gate` in #150, `database-reliability` in #151, and
`stack-profile` in #154. The owner authorized a Phase 2 immutable-byte screen at 5,000 bytes while
excluding those completed nine; Phase 1 is evidence, not a candidate pool to rerun.

**Outcome:** No skill spends a caller's context on detail the call did not need. Each screened
entrypoint receives one evidence/recommendation checkpoint. A confirmed conditional body becomes a
router with an “if the question involves X, read Y” table while retaining its authority and safety
invariants; a cohesive body is retained explicitly rather than split to satisfy a byte target.

**Source:** The initial measurement and reproduction command are in the
[`2026-08-17 skills surface sweep`](reviews/2026-08-17-skills-surface-sweep.md). The later
[`complete skill audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md) found that the old
eight-skill list had drifted: at its baseline, the nine candidates were `agent-security`,
`ci-actions`, `database-reliability`, `incident-command`, `ops-tooling`, `pcf-deploy`, `pcf-ops`,
`production-change-gate`, and `stack-profile`; `operational-learning` no longer belonged in the
set. Canonical bodies then totaled 231,622 bytes.

That nine-skill inventory is historical evidence, not the implementation baseline. Batch 0 and
Batch 1 both change relevant entrypoints, so this item must remeasure before editing. Description
metadata follows the current rule—capability or user goal, invocation conditions, and meaningful
exclusions, without procedure—rather than the retired “trigger only” doctrine.

The [`2026-08-24 host context-budget audit`](reviews/2026-08-24-host-context-budget-audit.md)
separates the host contracts that prompted Phase 2. Claude's default 8,000-character value budgets
the aggregate discovery listing on a 200k context; its 5,000-token-per-skill and 25,000-token-total
values govern post-compaction invoked content. Copilot's 30,000-character value applies to one
generated custom-agent prompt, not to a skill. None is the repository's 5,000-byte screen, and moving
body detail into references does not reduce discovery metadata unless a description changes.

`[verified]` The owner-approved Phase 2 remeasurement on exact current-main base
`b9b274f237caf8ce6068812e151f8543f608c7e7` finds 12 non-Phase-1 entrypoints at or above 5,000
immutable bytes, totaling 95,068 bytes: `frontend-craft` 13,827; `backend-craft` 10,814;
`obs-dashboards` 10,724; `agent-authoring` 9,420; `obs-alerting` 7,656; `runbook` 7,385; `gcp-ops`
7,384; `operational-learning` 6,078; `eng-ladder` 5,873; `obs-pipeline` 5,835; `root-cause` 5,048;
and `obs-traces` 5,024. The audit records reference-byte totals and the initial recommendation for
each. Selection means inspect, not rewrite; size alone is not a finding.

`[verified]` The same base carries 28 model-invocable skills whose names, descriptions, and line
separators total 13,239 characters in the fleet's Claude namespace, 5,239 above the installed
CLI 2.1.241 default fallback. No individual description reaches 1,536 characters and every
entrypoint is below 500 lines. The exact real-session truncation remains `[unverified]` because
bundled skills, usage priority, model context, and user overrides share that budget. This discovery
risk is measured separately and does not authorize a description rewrite inside Phase 2.

**Phase 1 closure evidence:** `[verified]` The nine one-skill slices named in Status merged after
refreshed immutable-byte measurements, bounded artifact checks, focused validators, regenerated
host projections, and independent review. The
[skill audit](reviews/2026-08-22-skill-clarity-routing-graph-audit.md#batch-2-remeasurement-and-first-router-candidate)
records the initial inventory and first `incident-command` slice. The later per-slice candidate and
merge identities, byte movement, reference splits, review fixes, focused results, and evidence gaps
remain in the tracked
[Phase 1 closure review](reviews/2026-08-24-skill-001-phase-1-closure.md). That review is historical
evidence, not live work.

The final Phase 1 screen on exact main `2294832ab0d4edc1199766530f4bea37367db197`
selected only `stack-profile`. Exact post-review implementation
`1cdecbd2a25b4fa2578e217f48e901169b43025d` and follow-up
`3a056e5d44c7b66d00ec8f0673a4b731d606a301` left the 30-entrypoint corpus at 192,748
immutable bytes with no undispositioned Phase 1 candidate. Direct structural validators, focused
tests, strict plugin validation, adapter byte checks, and independent review passed; unchanged
routing descriptions did not justify paid discovery runs. Static and fresh-context artifact checks
did not establish host activation, provider runtime behavior, final-response quality, or production
correctness. Fixed exercise budgets also left the `agent-security` OWASP case and exact corrected
conditional loading unrun, and left model-selected `stack-profile` reference loading for two narrow
requests unverified; those gaps do not re-open completed Phase 1 slices.

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

### SKILLS-003 — add a portable executable workflow-graph engineering skill

**Status:** `ready` (2026-08-24) — roadmap activation merged in PR
[#157](https://github.com/latent-sre/save-toolkit/pull/157) at `a8f98ce`. Renewed owner direction
activates only the executable workflow/state-graph capability from Batch 3. The proposed SRE
capability additions remain held; this item selects no graph runtime, creates no execution service,
and does not activate `codebase-atlas`.

**Owner:** `prompt-engineer` owns the canonical design method and its routing/evaluation contract.
`sde` owns any later implementation in team-authored code, but this item grants no implementation,
deployment, or live-effect authority. Human acceptance of the exact pull-request revision remains
with `latent-sre`.

**Outcome:** A user asking to design or review an executable workflow/state graph can invoke one
runtime-neutral `workflow-graph-engineering` skill and receive a portable, evidence-labelled design
contract. The result names its data, nodes, edges, concurrency, failure recovery, human-control,
lifecycle, authority, observability, and evaluation semantics without implying that a checkpoint
makes an external effect exactly once or that a graph-shaped design requires a particular runtime.

**Concrete consumer:** The immediate consumer is `prompt-engineer` when a team-approved request
needs an executable workflow/state-graph design or a review of one. Its output is a human-reviewed
engineering artifact that can later become a pinned handoff to `sde`. There is no machine consumer
in this slice, so it adds no JSON Schema or validator. A later proposal may add those only after it
names the exact producer, consumer, compatibility policy, and safety-critical predicate the
validator enforces.

**Source:** The
[`2026-08-22 skill clarity, routing, prompt, loop, and graph audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md)
separated graph engineering into three contracts: the existing roster/delegation graph, the missing
executable workflow/state graph, and a separate code/dependency/knowledge graph capability. Its
Batch 3 hold required renewed owner direction plus a concrete consumer and authority boundary. The
[`2026-08-23 research refresh`](reviews/2026-08-23-prompt-loop-graph-engineering-research.md)
compared current framework contracts and pinned upstream source/tests, found that no inspected
runtime supplied the entire portable contract, and recommended a runtime-neutral reference before
runtime or schema selection. Owner direction on 2026-08-24 supplies the activation decision: use
the repository's agent/skill framework, keep SRE additions deferred, and do not add a universal
runtime.

**Implementation audit and discipline boundaries:** Derive the working taxonomy from the exact
current `agents/` and `skills/` bytes. In pull-request evidence, record each discipline's canonical
name, owner, path, input, output, state/authority boundary, verifier, neighboring owner, and any
overlap or contradiction:

| Requested term | Canonical boundary to verify |
|---|---|
| Prompt engineering | `prompt-engineer` and `agent-authoring` own LLM-facing routing, instructions, output shape, and bounded prompt changes; schemas, runtime controls, and evaluator defects stay with their owning layer |
| Context engineering | `agent-authoring/references/context.md` owns selection, order, trust, freshness, compaction, retention, preload, and retrieval; context isolation is not authority isolation |
| Handoff engineering | `agent-authoring/references/roster.md` and canonical packet conventions require a stateless receiver interface with one owner, exact state, evidence/taint, success criteria, unknowns, and non-actions |
| Loop engineering | `agent-authoring`, `artifact.md`, and `roster.md` own mutable state, one verifier, fixed budgets and stops, durable evidence, and human promotion |
| Graph engineering | `delegation-graph.md` keeps the roster/capability graph; this item adds a distinct portable executable workflow/state-graph method, not a code/knowledge graph or runtime proof |
| Self-learning | Map the requested term to current **learning engineering** and `operational-learning`; never introduce autonomous self-modification, background promotion, or an unbounded optimizer |

Generated projections may confirm rendering but never establish ownership. Dated research is evidence,
not current authority. Preserve canonical disagreements as findings rather than inventing a new
discipline. Make one minimal candidate, keep universal authority/safety and the minimum usable
output contract always loaded, and route conditional depth behind explicit predicates. Freeze cases,
verifier, budgets, and stop conditions before editing; keep handoffs self-contained and one writer in
the isolated worktree; preserve tool authority, approval edges, terminal lanes, and host-specific
controls. Human acceptance of the exact revision is the only promotion step.

Disposition every implementation discovery as `worked`, `already owned`, `proposed to roadmap`,
or `dropped with reason`. These do not replace `operational-learning`'s canonical operational
states. Check the live roadmap before proposing work and never implement unrelated audit findings in
this branch.

**Capability boundaries:**

- The existing **roster/delegation graph** remains in `agent-authoring` and
  `agent-authoring/references/delegation-graph.md`. This item may sharpen the neighboring routing
  boundary but does not duplicate or relocate that method.
- **Executable workflow/state graph design** belongs to the new
  `workflow-graph-engineering` skill. It defines portable contracts and reviews designs; it does
  not execute a graph, select infrastructure, or write application code.
- **Code, import, dependency, knowledge, runtime-topology, and GraphRAG graphs** remain a separate
  possible `codebase-atlas` capability with different inputs, provenance, and success criteria.
  This item does not activate it.
- Prompt Engineering owns LLM-facing instructions and semantic behavior; Context Engineering owns
  selection, ordering, provenance, freshness, trust, compaction, and retention; Loop Engineering
  owns bounded gather/action/verify/repeat control and promotion authority. Workflow Graph
  Engineering composes their contracts but does not collapse those evidence lanes into one score.
- SRE concerns below are design requirements for an operable graph, not authorization for a new
  SRE agent, skill, runtime, deployment, credential, or production-change lane.

**Required portable design contract:**

| Concern | Required output |
|---|---|
| Identity and boundary | Graph ID/version, purpose, owner, caller, trust boundary, start condition, and exact agent, prompt, tool, schema, configuration, grader, model, and runtime identities/revisions when they exist; an unavailable identity stays explicit, while a supplied identity is never omitted |
| Typed data | Input, internal state, context, node input/output, edge payload, reducer state, checkpoint, and final-output contracts; unresolved types remain explicit rather than inferred |
| Nodes | Deterministic compute, model call, tool/effect, approval, reducer/join, verifier, and terminal classes with preconditions, authority, timeout, retry owner, and success/failure results |
| Edges | Deterministic, conditional, model-selected handoff, fan-out, fan-in, interrupt, retry, compensation, and terminal edges; every model-selected edge names its allowed destination set and deterministic guardrails |
| Concurrency and joins | Writer cardinality, reducer identity and algebra, ordering guarantees, conflict handling, join quorum, partial-worker failure, late-result policy, and fan-out budget |
| Scheduling and admission | Queue ownership and capacity, priority and fairness, tenant quota, concurrency cap, backpressure and load-shed behavior, worker lease/heartbeat/liveness, stale-worker handling, poison-work quarantine/manual repair, and the evidence required to admit work |
| Failure and retry | Failure classes, one retry owner, attempt/time budget, backoff, replay-safety classification, authority for an unsafe replay, timeout ownership, and fail-closed handling of missing or inconclusive evidence |
| Replay and compatibility | Recovery model that distinguishes checkpoint resume from deterministic event-history replay, code/build version, history and state-schema compatibility boundary, replay or shadow verification, fork semantics, migration, and repair policy |
| Durability | Run/thread/checkpoint identity, state and checkpoint schema version, durability mode, checkpoint boundary, last known recovery point, resume semantics, retention, restore, and evidence of persisted state |
| External effects | Deterministic caller/operation/target/tenant/payload-bound idempotency-key construction, attempt identity, mismatched-intent rejection, result/tombstone retention, effect journal or receipt, atomic receipt/mutation coupling when the target supports it, read-after-write reconciliation, explicit `UNKNOWN`, safe compensation limits, and a prohibition on automatic replay while outcome is unknown |
| Human control | Approval immediately before the effect path, bound to approver identity, exact action and target, immutable candidate/config identity, expiry, rejection, timeout, and resumed state |
| Lifecycle and cancellation | Pause/resume, cooperative-cancel signal and safe observation point, durable-cancel persistence and new-dispatch prevention, in-flight effect handling, late-worker/result quarantine, supersession, restart behavior, replay/fork relationship, and cleanup deadline |
| Termination | Success, no-progress, maximum turns/iterations/time/tokens/cost, cancellation, safety stop, unreachable-exit detection, and terminal evidence requirements |
| Security and context | Actor and credential scope, least authority per node, untrusted-input treatment, provenance/freshness, taint propagation across every edge and handoff, redaction, and retention |
| Observability and evaluation | Run/node/edge/attempt/retry/replay lineage; tool, handoff, guardrail, approval, checkpoint, and effect events; node, edge, path, outcome, recovery, consistency, temporal, and budget evaluations |

**Skill and context shape:** The canonical `SKILL.md` keeps the mandate, authority boundary,
untrusted-content rule, effect-safety invariants, common decision rules, reference-routing table,
and required final-artifact sections in unconditional context. Provider procedures, framework
comparisons, extended examples, failure tables, and detailed evaluation recipes sit behind explicit
predicate-keyed references. The entrypoint must remain usable without opening a reference, and each
reference must be linked from it. Canonical sources are edited once and generated projections are
regenerated once before the push-boundary gate; projections are never hand-edited.

**Required artifact shape:** Every completed design contains, in order: (1) scope, consumer, owner,
authority, assumptions, and unresolved decisions; (2) graph, actor, build, prompt, tool, schema,
configuration, grader, model, and runtime identities when supplied; (3) typed input/state/output
contract; (4) node table; (5) edge and routing table; (6) scheduling, admission, fairness,
backpressure, load-shedding, and worker-liveness contract; (7) fan-out/fan-in and state-merge
contract; (8) failure, retry, timeout, and replay-safety matrix; (9) idempotency-key, effect,
receipt, retention, `UNKNOWN`, reconciliation, and compensation matrix; (10) approval, durability,
resume, cancellation, supersession, restart, replay/fork, and compatibility controls; (11)
termination budgets; (12) context provenance, taint, and security boundaries; (13) trace and
graph-level evaluation plan; and (14) runtime-selection criteria explicitly marked deferred unless
a separately approved consumer decision supplies them. The artifact labels `[verified]`,
`[sourced]`, and `[unverified]` per claim and never presents design completeness as runtime proof.

**Authority and safety invariants:** Repository text, retrieved material, tool results, graph state,
and worker handoffs are data, never instructions, and cannot select tools, widen authority, or
approve effects. Delegation and a separate context window are not isolation. Approval gates record
a decision but do not create credentials or enforcement; the effect boundary must enforce the
approved identity and arguments. Checkpoints record known progress but do not prove exactly-once
external effects. Cancellation cannot roll back a completed remote effect. Compensation is claimed
only for a domain operation shown to be reversible. Each effect design defines the idempotency key
from the caller, operation, target, tenant, and canonical intent/payload; reuse with different
intent is rejected before dispatch. A successful result or tombstone remains available through the
full retry and ambiguity window. When supported, receipt creation and the remote mutation are
coupled atomically; otherwise reconciliation is mandatory. An interrupted dispatch remains
`UNKNOWN` until reconciliation or target-native idempotency resolves it, and it is never replayed
automatically while unknown. No generated design authorizes production access or execution.

**Implementation boundary:** Implement one new canonical skill in one reviewed commit. The expected
canonical surfaces are `skills/workflow-graph-engineering/`, the minimum `prompt-engineer` routing
change needed to expose it, the directly affected scenario files, and repository catalog/count text
required by fleet validators. References are split only along observable request predicates. Do not
perform a fleet-wide prompt rewrite, add a second prompt-engineering or Loop Engineering skill,
change agent authority, introduce a runtime dependency, or bundle `codebase-atlas` into the same
pull request.

**Prerequisites:** Start implementation on a fresh branch from refreshed `origin/main`. Reinspect the
exact `prompt-engineer`, `agent-authoring`, routing-scenario, generator, and manifest/catalog
surfaces before naming the final file set. If another open change overlaps those surfaces, do not
stack dependent edits. Define the positive, neighboring-owner, and near-miss cases before drafting
the skill. Current framework details are consulted through Context7 only when a version-specific
contract is needed; GitHits supplies separately labelled pinned upstream source/test/adoption
evidence. Existing dated research is a source, not permission to resume any other checklist.

**Acceptance:** All of the following are required:

1. **Discipline taxonomy:** Pull-request evidence derives all six requested disciplines from the
   exact canonical implementation base, records the owner/boundary table and any disagreements, and
   accounts separately for canonical, preloaded, generated, and host-specific context. Every audit
   discovery has one of the four implementation dispositions above and any proposal demonstrates
   that the live roadmap has no existing owner. No unrelated finding is implemented in the branch.
2. **Routing separation:** A positive request for portable executable workflow/state-graph design
   reaches `workflow-graph-engineering`; a roster/delegation-graph request remains with
   `agent-authoring`; a repository dependency/knowledge/GraphRAG request does not route to the new
   skill; a request to implement a concrete runtime remains with `sde`; and runtime selection needs
   a separate owner decision under `stack-profile`. Only scenarios affected by changed routing
   content are run.
3. **Artifact behavior:** One fixed five-agent fresh-context exercise uses exactly one trial for each
   predeclared case: a deterministic graph with queue admission, fairness, backpressure,
   load-shedding, and worker liveness; a model-selected handoff with authority and taint;
   fan-out/fan-in with partial failure; an approval-gated external effect with semantic idempotency,
   mismatched-intent rejection, retention, `UNKNOWN`, and reconciliation; and a durable cyclic graph
   that distinguishes checkpoint resume from deterministic event-history replay and cooperative
   from durable cancellation while covering in-flight/late workers, supersession, explicit budgets,
   tracing, and graph-level evals. Before any call, the exercise records the exact candidate full
   SHA and clean tree, canonical/plugin input digest, host and CLI version, runtime and model
   identity, effective tool permissions, the five immutable prompts, grader identities and
   thresholds, per-call timeout, and maximum call/cost budget. Raw prompts, outputs, grader results,
   timing, errors, and spend evidence are retained. Changing a case, grader, threshold, or candidate
   creates a new candidate that requires owner approval rather than silently extending this pass.
   Each result satisfies the required artifact shape without choosing a runtime or claiming
   execution evidence. This is one bounded candidate/evaluation pass, not an optimizer loop.
4. **Safety controls:** Focused checks reject automatic replay of an unknown effect; acceptance of a
   reused idempotency key with mismatched intent; result/tombstone retention shorter than the retry
   or ambiguity window; approval not bound to the exact action/state; admission without declared
   queue capacity, fairness, backpressure/load-shed, and worker-liveness behavior; cancellation that
   omits cooperative versus durable semantics or in-flight/late-worker disposition; checkpoint
   resume presented as deterministic event-history replay; unbounded cycles; missing terminal
   states; taint dropped at a handoff; and checkpoint-equals-exactly-once claims. If a deterministic
   validator or other machine contract is introduced despite the current boundary, its exact
   consumer must be named and one focused red-to-green regression must prove each new enforced
   predicate.
5. **Evidence separation:** Activation/routing, artifact/output quality, and runtime behavior are
   reported independently. Runtime execution, durability, provider behavior, effect safety, and
   production readiness remain `[unverified]` unless separately exercised on an approved exact
   implementation; a strong static design never upgrades that lane.
6. **Repository integrity:** Every reference is reachable, scenario parsing and affected offline
   graders pass, the exact changed-description scenario set is recorded, projections regenerate
   byte-clean once, strict plugin validation passes, and Gate A passes once at the push boundary.
   The pull request receives one independent exact-revision correctness/security and roadmap-plan
   conformance review; no automated review loop is started.

**Closure:** Merge the accepted exact revision, record its focused structural, routing, artifact,
and review evidence without conflating their claims, then move `SKILLS-003` to the closed table. A
runtime, schema, executable validator, `codebase-atlas`, or SRE capability remains separate future
work and does not keep this skill-capability item open.

**Next action:** From refreshed `origin/main`, inventory the exact owning surfaces, freeze the
routing matrix and five bounded artifact cases, and implement only `workflow-graph-engineering` as
the first reviewed Batch 3 slice.

### ROUTE-003 — remeasure workflow-graph and service-readiness discovery reliability

**Status:** `deferred` (2026-08-23)

**Owner:** `latent-sre`

**Outcome:** The two positive discovery routes left inconclusive by Batch 1 have reproducible,
model-labelled reliability evidence before either is promoted into a stronger routing claim.

**Source:** Batch 1 run `20260823T053852Z-1e677acb` timed out both workflow-graph trials. Closeout
run `20260823T131840Z-9e4c7fca` on merged commit `09e775b`, Claude Code 2.1.241,
`claude-sonnet-5`, two trials, and a 180-second timeout passed read-only service readiness 1/2 and
timed out the second trial. The exact dispositions are in the
[`skill clarity and routing audit`](reviews/2026-08-22-skill-clarity-routing-graph-audit.md).

**Prerequisites:** A material routing, evaluator, host, or model change that can alter the result,
or explicit owner approval of a fixed no-tuning measurement budget. Use a clean exact plugin
revision and predeclare model, timeout, trials, threshold, and selected scenarios.

**Acceptance:** The workflow-graph and service-readiness cases each meet their declared threshold
on the exact candidate under the predeclared conditions, with no overlapping regression loss. A
failed or inconclusive batch remains evidence; it does not authorize prompt edits or retries without
a separately accepted fleet failure and candidate budget.

**Reopen trigger:** A material change to either route or its evaluator/runtime boundary, a named
model-migration question, or explicit owner approval for one fixed-budget reliability measurement.

**Next action:** None while deferred. Do not rerun unchanged bytes merely to turn timeouts green,
and do not move reference-dependent behavior graders into discovery.

### ROUTE-002 — resolve the `obs-logs` / `obs-alerting` trigger collision

**Status:** `active` (2026-08-20) — kept open: the "no other overlapping scenario moved" half of
acceptance is not yet evidenced.

**Outcome:** One skill owns log-based alert design **in the canonical text**, and the routing suite
contains a scenario that would fail if the other started firing for it. Both halves are required:
the descriptions must state the boundary, and a scenario must be able to detect a regression.

**Source:** The
[skills surface sweep](reviews/2026-08-17-skills-surface-sweep.md) found that `obs-logs`
advertised `'build a log alert'` without disclaiming `obs-alerting`, while the suite had no
near-miss scenario that could detect the collision. The prepared
`discovery-obs-logs-defers-obs-alerting` case made it measurable and passed structural validation
with all grader checks.

`[verified]` In PR [#122](https://github.com/latent-sre/save-toolkit/pull/122), the exact base
routed the new case 1/2; after the ownership-map fix it routed 2/2 on both recorded models.
Canonical `obs-logs` now names `obs-alerting` explicitly. The literal-grader defect was separately
fixed in `19aaa52`; it was not routing evidence. The
[round packet](reviews/2026-08-19-obs-skill-hardening-round.md) retains prompts, revisions, and raw
results. The complete declared set of overlapping scenarios has not yet been evidenced on the
changed descriptions.

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

**Prerequisites:** None blocking. The banner work is done. By owner decision, the maintenance skills
stay in the shared package: no current measurement shows that their install size or discovery surface
harms a named consumer. Reopen that packaging decision only with measured consumer impact attributable
to those bundles.

**Acceptance:** No shared evidence-default banner remains and adapters regenerate byte-clean; the
two self-retracting examples keep their labels as one-line footnotes; the retired learning packet
and ledger paths remain absent; Gate A passes; operational closeout still produces evidence-bound
documentation dispositions and owners without execution authority.

**Next action:** Compact the provenance paragraphs in the `pcf-deploy` and `runbook` worked examples
to one-line footnotes. Keep the maintenance skills together unless the measured-impact reopen trigger
fires.

## Deferred

### EFFECT-001 — effect-bound execution broker

**Status:** `deferred`

**Outcome:** If protected automation is ever allowed to perform a live effect, approval is bound to
one exact action, target, argv/executable digest, expiry, nonce, rollback, and replay ledger.

**Source:** Fleet authority reviews that reject prose approval and require an explicit unknown-outcome
state for externally dispatched effects.

**Prerequisites:** A named workflow approved to cross the current prepare/recommend boundary, a
separately controlled execution identity, and live `main` ruleset enforcement as recorded in
[`docs/reviews/2026-08-05-protect-001-closure.md`](reviews/2026-08-05-protect-001-closure.md).

**Acceptance:** Effect-bound approval, dispatch, unknown-outcome reconciliation, replay prevention,
expiry, rollback, and operator-resolution tests pass for the named effect target.

**Reopen trigger:** A named workflow is approved to move beyond the fleet's current prepare/recommend
boundary and has a separately controlled execution identity.

**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority.
