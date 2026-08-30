# Three-pass non-eval review of all 33 canonical skills

> **Status: dated review evidence, not a backlog or governing contract.** This note records what was
> observed at the revision below. It creates no work by itself; only
> [`fleet-roadmap.md`](../fleet-roadmap.md) may import an accepted recommendation and assign its owner.

- **Review baseline commit ID:** `1fb4727e9a18b9adad2cb2d498a37ef225885bde`
- **Review date:** 2026-08-26
- **Scope:** all 33 canonical `skills/*/SKILL.md` entrypoints, with the 113 bundled Markdown
  references followed where needed to resolve ownership, authority, context, and consistency
  questions
- **Boundary:** source review and deterministic structural checks only; no eval harnesses, model
  trials, routing runs, behavioral runs, generated-source edits, commits, pushes, or external
  comments

## Conclusion

The repository's structural skill layer is healthy: frontmatter, trigger counts, links, bundled-file
reachability, stale-name checks, graph contracts, canaries, fleet validation, and generated-adapter
parity all pass. The semantic layer is **partial**, not clean. Several skills give an LLM conflicting
answers about who owns an action, what authorization means, or which conditional instructions apply.

The highest-value changes are to:

1. cut the structural prompt-injection and authority risk around live Grafana writes;
2. distinguish agent assessment from human production authorization;
3. give incident closure one communications/timeline owner; and
4. standardize rollback language around a tested recovery strategy rather than requiring a reverse
   operation where none is lossless.

Instruction length by itself was not treated as a defect. A recommendation appears below only when
the wording changes routing, authority, context selection, execution, verification, or termination.
Security and production boundaries were not classified as removable prompt "fluff."

## Method

Three independent source passes were reconciled against the canonical files:

| Pass | Lens | Result |
|---|---|---|
| 1 | Trigger, authority, ownership, routing, effects, and termination | **Fail** — dashboard authority/security and an unbounded diagnosis loop remain |
| 2 | LLM readability, context economy, terminology, and observable predicates | **Partial** — several instructions have conflicting owners, vocabularies, or conditional scope |
| 3 | Cross-skill consistency, reference reachability, stack alignment, and non-eval regression guards | **Partial** — closeout, recovery, and production-gate contracts diverge |

The LLM-readability question was concrete: after loading a skill, can the model tell when it applies,
which context to load, who owns the current state, what output is required, and when to stop or hand
off? The fleet's four-theme rule supplied the organizing lens: Prompt selects and guides the owner;
Context supplies the smallest trusted state; Loop governs execution and termination; Graph governs
ownership changes.

## High-priority findings

### 1. Live dashboard work retains a structural prompt-injection path and contradictory authority

The dashboard workflow combines untrusted Editor-controlled dashboard content, an environment token,
unguarded Bash/network reach, and live mutation. The skill acknowledges that prose does not enforce
its safety rule, while the HTTP reference says both `observability-engineer` and the main session can
run the live calls:

- [`agent-security/SKILL.md`](../../skills/agent-security/SKILL.md#the-lethal-trifecta) says prompt
  wording cannot repair a complete sensitive-data + untrusted-content + external-action trifecta.
- [`observability-engineer.md`](../../agents/observability-engineer.md#observability-engineer) grants
  unguarded Bash, environment credentials, and dashboard writes while admitting no hook enforces the
  credential restrictions.
- [`obs-dashboards/SKILL.md`](../../skills/obs-dashboards/SKILL.md#dashboard-content-is-untrusted-input)
  says live dashboard content reaches a command-capable session and that nothing enforces the prose
  boundary.
- [`http-api.md`](../../skills/obs-dashboards/references/http-api.md) says "the main session can run
  them too," contradicting the sole invoked-agent exception in [`AGENTS.md`](../../AGENTS.md).
- [`service-onboarding/SKILL.md`](../../skills/service-onboarding/SKILL.md#required-on-demand-skill-dependencies)
  loads `obs-dashboards` rather than transferring dashboard ownership to `observability-engineer`.

**Recommended direction:** remove the main-session mutation grant. Make every owner other than an
invoked `observability-engineer` read/prepare/handoff-only. Put live operations behind a
destination-pinned typed tool that parses dashboard JSON outside model context, exposes only exact
dashboard operations, and uses a narrowly scoped token. Until that structural boundary exists, keep
the agent prepare-only and require human execution.

### 2. `production-change-gate` reads as though the skill grants authorization

The [`production-change-gate` description](../../skills/production-change-gate/SKILL.md) says
"Authorize" and "this gate authorizes," while the body says the agent only classifies, prepares,
recommends, and records a human decision. Its `APPROVED | BLOCKED` output can therefore be read as
agent-granted production authority.

**Recommended direction:** describe the capability as assessing and recording supplied human
authorization evidence. Separate `agent assessment: SATISFIED | BLOCKED` from
`human authorization: present | missing`, and preserve the exact target, actor, expiry, execution-time
binding, and result receipt.

### 3. Incident closure has two owners and two state vocabularies

[`incident-command/SKILL.md`](../../skills/incident-command/SKILL.md#shared-control-boundary) assigns
communications and the authoritative timeline to incident command, then later tells `sre` to send the
resolution update and return that timeline. Its
[`command-and-communications` reference](../../skills/incident-command/references/command-and-communications.md)
keeps those duties in command, while
[`recovery-lifecycle.md`](../../skills/sre-ladder/references/recovery-lifecycle.md) returns only the
technical record. The command surface says `monitoring`; the technical record says
`monitoring-recovery`.

**Recommended direction:** incident command or the caller owns the status block, communications,
timeline, and resolution update. SRE returns the technical recovery evidence. Define the mapping from
command status `monitoring` to technical state `monitoring-recovery` once.

### 4. Rollback terminology can require an unsafe reverse operation

[`database-reliability`](../../skills/database-reliability/SKILL.md#migration-safety) correctly allows
a demonstrably lossless backout, roll-forward, compensation, restore/PITR, or expand/contract path.
[`release-gate`](../../skills/release-gate/SKILL.md#checklist),
[`runbook`](../../skills/runbook/SKILL.md#authoring-rules), and
[`production-change-gate`](../../skills/production-change-gate/SKILL.md#checklist) revert to exact
reversibility or "how to undo it." That wording can pressure a model to invent a destructive reverse
script merely to satisfy a required slot.

**Recommended direction:** make **tested recovery strategy** the umbrella contract. Require exact
reverse steps only when they are demonstrably lossless; otherwise require the tested roll-forward,
compensation, or restore path.

## Additional contract and consistency findings

1. **Database production actions use an abbreviated approval contract.**
   [`database-reliability`](../../skills/database-reliability/SKILL.md#database-reliability) accepts a
   shortened human-approved packet without the canonical gate's expiry, execution-time rebinding, or
   `executed | not executed | UNKNOWN` reconciliation. Consume the canonical
   `production-change-gate` verdict and result for every production database effect.

2. **Operational closeout has competing ownership paths.**
   [`living-runbooks.md`](../../skills/runbook/references/living-runbooks.md) calls the intake the
   SRE's closeout dispositions; [`restore-drill.md`](../../skills/database-reliability/references/restore-drill.md)
   tells the database lane to write results directly into a runbook; and
   [`postmortem`](../../skills/postmortem/SKILL.md#operational-learning-closeout) requires
   `operational-learning` even though [`scribe`](../../agents/scribe.md#pick-one-primary-mode) permits
   one primary mode. Use one topology everywhere: originating lanes return unclassified evidence;
   the caller invokes scribe knowledge-closeout mode; scribe loads `operational-learning`, and loads
   `runbook` only for a dispositioned procedure change.

3. **`root-cause` can mutate source during a diagnosis-only request and lacks a full bounded loop.**
   [`root-cause/SKILL.md`](../../skills/root-cause/SKILL.md#the-loop) permits adding a log line while
   saying no behavior changes yet. Its three-strikes rule bounds failed fixes, not hypothesis tests,
   instrumentation edits, elapsed time, or no-progress investigation. Make diagnosis read-only by
   default; require explicit edit authority for instrumentation and name hypothesis/time limits plus
   success, no-progress, safety, authority, and `INCONCLUSIVE` terminals.

4. **The merge gate sends operational documentation to the wrong owner.**
   [`merge-gate/SKILL.md`](../../skills/merge-gate/SKILL.md#checklist) sends affected operational
   guidance to `observability-engineer`. Route runbooks and operating documentation to `scribe`; use
   `observability-engineer` only for telemetry, alerts, SLOs, and dashboards.

5. **`ops-tooling` can ask `software-engineer` to delegate to itself.**
   [`ops-tooling`](../../skills/ops-tooling/SKILL.md#entry-gate) assumes build and review both spawn
   agents, and its [`build` reference](../../skills/ops-tooling/references/build.md) unconditionally
   says to spawn `software-engineer`. The natural owning `software-engineer` context cannot delegate
   to itself. State that an already-invoked software engineer is the builder; only a coordinator with
   the required edge spawns one, while independent review remains a separate reviewer dispatch.

6. **The frontend core makes conditional greenfield/React defaults universal.**
   [`frontend-craft`](../../skills/frontend-craft/SKILL.md) says its core applies to every UI while
   mandating dark-first styling, a house visual language, TanStack Query, and TanStack Router. Its
   [`design-language`](../../skills/frontend-craft/references/design-language.md) and
   [`Vue`](../../skills/frontend-craft/references/vue.md) references say the existing brand, router,
   and stack win. Move greenfield aesthetics and framework-specific choices behind observable
   predicates; preserve universal accessibility, resilience, and verification rules in the entry.

7. **The backend core makes HTTP rules universal to workers and schedulers.**
   [`backend-craft`](../../skills/backend-craft/SKILL.md) routes APIs, workers, and schedulers, then
   says OpenAPI, `/v1`, problem+json, and real endpoint requests apply to every backend task. Split
   universal service rules from the HTTP/API contract and load the latter only for an HTTP surface.

8. **Readiness-audit predicates and output language are unresolved.**
   [`service-readiness-audit`](../../skills/service-readiness-audit/SKILL.md#evidence-to-inspect) uses
   "relevant owning skill" for dependencies, capacity, and drift, then directs the model to load that
   unspecified owner. Replace those cells with named observable predicates or record an evidence gap.
   Rename its read-only output from "validated fixes" to "recommended remediations."

9. **Workflow runtime selection is both excluded and accepted.**
   [`workflow-graph-engineering`](../../skills/workflow-graph-engineering/SKILL.md#read-only-the-lane-the-request-needs)
   excludes runtime choice but routes "which runtime should we use" to a reference before deferring
   the decision. A named runtime inside a graph-design request may load compatibility facts; a
   standalone selection request should stop and hand off to `stack-profile`.

10. **PowerShell guidance chooses secret providers outside the stack-selection boundary.**
    [`powershell.md`](../../skills/language-idiom/references/powershell.md#secrets--signing) directly
    recommends Azure Key Vault or HashiCorp Vault while
    [`stack-profile`](../../skills/stack-profile/SKILL.md#stay-in-lane) names GCP Secret Manager for
    the current migration. Keep `Get-Secret` mechanics provider-neutral or load `stack-profile`
    before selecting a provider.

## LLM-readability and context-economy improvements

- Convert the 1,181-character ownership paragraph in
  [`eng-ladder`](../../skills/eng-ladder/SKILL.md#mode-1--route-a-task) into
  `predicate → owner → consult target → returned artifact → stop/escalation` rows. Preserve the
  required-consult invariant.
- Move detailed SLI/SLO/burn-rate mechanics out of the always-loaded
  [`obs-alerting`](../../skills/obs-alerting/SKILL.md) entrypoint and keep the conditional calculation
  rules in its burn-rate reference.
- Remove loading choreography from routing descriptions. In particular,
  [`frontend-craft`](../../skills/frontend-craft/SKILL.md) says its ownership list is "not a load"
  while also saying `language-idiom` is loaded alongside it.
- Keep positive output recipes short and named. Where builder skills say "review packet," either
  define the required slots locally or consistently name the owning agent's final evidence packet.

## Skill accounting

Direct changes are recommended in 18 skills:

`backend-craft`, `database-reliability`, `eng-ladder`, `frontend-craft`, `incident-command`,
`language-idiom`, `merge-gate`, `obs-alerting`, `obs-dashboards`, `ops-tooling`, `postmortem`,
`production-change-gate`, `release-gate`, `root-cause`, `runbook`, `service-onboarding`,
`service-readiness-audit`, and `workflow-graph-engineering`.

No material issue was found in the other 15 entrypoints during these passes:

`agent-authoring`, `agent-security`, `akamai-edge`, `ci-actions`, `gcp-ops`, `incident-drill`,
`obs-logs`, `obs-metrics`, `obs-pipeline`, `obs-traces`, `operational-learning`, `pcf-deploy`,
`pcf-ops`, `sre-ladder`, and `stack-profile`.

"No material issue found" is bounded to this static review; it is not a runtime-behavior claim.

## Verification record

[verified] The review inventory contained 33 canonical skill entrypoints and 113 Markdown reference
files. Generated roots were used only for parity checks, never as canonical sources.

[verified] These non-eval checks passed against the review baseline:

- `py -3 scripts/gate_a.py` — `Gate A: PASS`, 7/7 structural steps green;
- `python scripts/test_check_links.py` — 33 tests, 1 skipped;
- `python scripts/test_validate_fleet.py` — 49 tests;
- `python scripts/test_platform_adapters.py` — 29 tests, 2 skipped;
- `python scripts/test_canary_tokens.py` — 6 tests;
- `python scripts/test_graph_contracts.py` — 10 tests; and
- `python scripts/test_check_stale_names.py` — 13 tests.

The six focused suites total 140 passing tests with three documented platform skips. Passing
structural checks do not resolve semantic authority, ownership, or LLM-readability conflicts.

[unverified] No live host, Grafana instance, credential boundary, network-egress control, Claude
runtime, or Copilot runtime was probed. No eval harness or model trial was run. The inspection phase
changed no files; this note is the only repository change made to record its result.
