# Skill clarity, accuracy, routing, prompt, loop, and graph audit

> **Status: historical audit and rationale, not a second backlog.** This records the complete
> owner-requested review performed on 2026-08-22. Current implementation state and the next bounded
> batch live only in [`fleet-roadmap.md`](../fleet-roadmap.md).

**Audit baseline:** `988027df7c51ca4ab1444f18502e52a26a7fee7a`
**Audit scope:** all 29 canonical skills then present under [`skills/`](../../skills)
**Current-state reconciliation:** `50b246f9edec473674d983ca7c8bdac53868ec12`, 2026-08-23

## Conclusion

The fleet was structurally strong and already used the modern skill package shape, but the audit
could not certify every skill as accurate or correctly routed. Five factual or policy
contradictions needed owner disposition, routing coverage reached only 19 of 29 skills, nine
entrypoints spent too much unconditional context, Loop Engineering was present but under-specified
at its routing and termination boundaries, and executable workflow/state graph engineering was not
yet a complete fleet capability.

The right response was staged, not a fleet-wide rewrite:

1. Correct operator-facing contradictions first.
2. Repair the routing contract and split workflows whose invocation safety differs.
3. Convert one large skill into a reviewed router pattern before repeating it.
4. Add capabilities only after ownership and a real operator need are confirmed.

This review preserves the full assessment that led to those batches. A later batch may change the
current files; it does not rewrite what the audit observed.

## Method and evidence boundary

The review used five evidence lanes and kept their provenance separate:

- **Local workspace:** canonical skill bodies, linked resources, schemas, eval scenarios, validators,
  accepted decisions, and the live roadmap. Generated Copilot and plugin projections were treated as
  consequences, not independent sources.
- **Context7:** current Anthropic Claude Code documentation. It describes a skill description as a
  concise statement of what the skill does and when it applies, recommends natural-language trigger
  keywords, and recommends moving large detail into directly linked supporting files. See
  [Claude Code skills](https://code.claude.com/docs/en/slash-commands).
- **Official OpenAI documentation:** descriptions state the workflow and triggering conditions;
  detailed procedure, format, and safety instructions stay in the body. Supporting resources are
  linked from `SKILL.md` with explicit load/run conditions. See
  [Build skills](https://developers.openai.com/plugins/build/skills).
- **GitHits:** current public OSS implementation and community evidence. OpenAI's plugin evaluator
  warns when a description omits what/when, exceeds the always-loaded budget, or when a large
  `SKILL.md` fails to use linked references for progressive disclosure. See
  [`openai/plugins` evaluator at `11c74d6`](https://github.com/openai/plugins/blob/11c74d6ba24d3a6d48f54a194cd00ef3beea18f9/plugins/plugin-eval/src/evaluators/skill.js#L140-L214).
  GitHits also surfaced Obra Superpowers' stricter trigger-only rule and its reported before/after
  observation. The exact pin does not retain the named triggering-test fixture, trial conditions, or
  result artifact, so this is not a reproducible measured evaluation or a universal specification. See
  [`writing-skills` at `b36e082`](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/writing-skills/SKILL.md#L94-L104).
- **Portable specifications and framework guidance:** the Agent Skills specification, current OpenAI Agents
  SDK orchestration/guardrail/tracing guidance, LangGraph graph/persistence/interrupt guidance, and
  Anthropic's agent architecture guidance. These establish portable concepts; none makes a
  particular runtime mandatory for this repository.

Evidence labels retain their repository meaning: `[verified]` means observed or run locally,
`[sourced]` means bound to a file or external source, and `[unverified]` names a remaining gap.

## Highest-priority accuracy and authority findings

The following table records both the audit-time finding and its later disposition. That distinction
matters: finding 4 was correctly deferred until stronger upstream evidence appeared, then closed
when that evidence became available.

| # | Audit-time finding | Required correction | Current-main disposition |
|---|---|---|---|
| 1 | `production-change-gate` required four dashboard-write conditions, including a committed applied JSON record, while the accepted dashboard ADR had withdrawn that condition because Grafana version history is the durable record. | Define the dashboard exception once and route authority and procedure to their owners. Add a focused cross-file regression if the condition list remains duplicated. | **Closed.** [`production-change-gate`](../../skills/production-change-gate/SKILL.md) now points to the `observability-engineer` authority and `obs-dashboards` procedure without copying a competing condition list. |
| 2 | The production gate used the classic branch-protection endpoint universally and treated its `404` as proof that no protection applied. Rulesets and non-repository effect paths made that evidence unsound and added unrelated ceremony to live operations. | Bind the load-bearing control to the effect path: repository rules for code history, protected environments for deployment credentials, and least-privilege IAM/change authority for manual live actions. Do not make branch protection a universal production prerequisite. | **Closed.** The current gate asks for protected-environment evidence only for a deployment and least-privilege actor/credential evidence for another planned action; it explicitly says branch protection is not a production-action boundary. Focused production-gate scenarios cover missing execution authority. |
| 3 | [`stack-profile`](../../skills/stack-profile/SKILL.md) said P1-P4 criteria were unrecorded while [`incident-command`](../../skills/incident-command/SKILL.md) presented exact impact thresholds, paging, and cadence as policy. | Obtain owner ratification and keep the rubric in one canonical skill; every other skill consumes it rather than copies it. | **Closed.** The owner ratified the rubric on 2026-08-23. `incident-command` owns the rubric and records ratification; `stack-profile` points to it. |
| 4 | A Grafana 13.2 security floor was inferred from advisory metadata that did not then name authoritative affected or fixed versions. | Keep least privilege, but do not claim a version floor until Grafana or its CNA data names affected ranges and the deployed patch is known. | **Closed after the defer condition became true.** Grafana's CNA record now names affected ranges. [`grafana-alerting.md`](../../skills/obs-alerting/references/grafana-alerting.md) records them, refuses to turn 13.2 into a universal floor, and leaves the production 13.1 patch `[unverified]`. |
| 5 | [`gcp-ops`](../../skills/gcp-ops/SKILL.md) said quoted `severity>=ERROR` was denied while the focused guard corpus allowed the quoted form and denied only the unquoted redirect-shaped spelling. | Correct only that wording and rerun the allow/deny corpus; do not broaden the guard. | **Closed.** The skill now distinguishes quoted allow from unquoted deny and preserves the narrow guard contract. |

## Skill-authoring and package assessment

The repository already followed the modern package model well:

- `[verified]` `scripts/check_links.py` passed and every bundled resource was reachable from its
  owning `SKILL.md`.
- `[verified]` All 29 entrypoints were below 500 lines; the largest was 184 lines.
- `[verified]` All 77 Markdown references were below 500 lines; the largest was 449 lines.
- `[verified]` The root [`schemas/`](../../schemas) used JSON Schema 2020-12, versioned IDs, an
  explicit catalog, and closed fixed-shape objects. The evidence envelope intentionally retained
  open `source`, `environment`, and `isolation` metadata maps under the compatibility policy in
  [`schema-compatibility.md`](../schema-compatibility.md).
- Assets were reusable templates or starter material rather than prose mislabeled as assets.

The portable [Agent Skills specification](https://agentskills.io/specification) supports the same
division:

| Resource | Use it for | Do not use it for |
|---|---|---|
| `SKILL.md` | Selection boundary, invariants, core method, and explicit routing to detail | Every provider variant, long example, or reference table |
| `references/` | Conditional domain detail, APIs, provider procedures, edge cases, and schemas an agent reads | Executable helpers or files copied into output unchanged |
| `scripts/` | Deterministic validation, extraction, transformation, or repeatable operations | Prose that the model must understand as policy |
| `assets/` | Templates, starter configuration, images, and other reusable output material | Hidden instructions or ordinary reference prose |
| root `schemas/` | Versioned, machine-consumed, cross-skill or safety-critical contracts | A schema for every human-readable answer merely for symmetry |

A schema should therefore be added only when a consumer, safety boundary, or interoperability
contract benefits from machine validation. Adding one mechanically to every skill would be ceremony,
not modernization.

### Description doctrine

The old local rule said “trigger only, never workflow.” That was too absolute:

- `[sourced]` The Agent Skills specification requires what the skill does **and** when to use it.
- `[sourced]` Current Anthropic documentation uses the same capability-plus-use-condition shape and
  recommends specific natural-language keywords to improve triggering.
- `[sourced]` OpenAI's official skill guidance and pinned plugin evaluator both require enough
  workflow/capability and triggering information for selection while keeping detailed procedure out
  of the description and warning against long always-loaded metadata.
- `[sourced]` Obra Superpowers reports an observation in which a workflow summary in metadata
  overrode the detailed skill body. The pinned tree does not retain enough fixture and result
  evidence to reproduce that comparison. The observation supports excluding procedure, but it does
  not justify deleting the capability boundary models use to discriminate skills.

The reconciled local rule is:

> **Description = concise capability or user goal + invocation conditions + meaningful exclusions.
> Never put step-by-step procedure or tool choreography in it.**

This preserves the community warning while matching current portable and vendor guidance. Because a
description is routing code, changes still require focused positive and near-miss measurements; this
rule does not authorize a blind fleet-wide rewrite.

## Clarity, prose, and unconditional context

At the audit baseline, canonical `SKILL.md` bodies totaled **231,622 bytes**. Nine met the roadmap's
“oversized unconditional body” criterion:

- `agent-security`
- `ci-actions`
- `database-reliability`
- `incident-command`
- `ops-tooling`
- `pcf-deploy`
- `pcf-ops`
- `production-change-gate`
- `stack-profile`

The then-live `SKILL-001` inventory was stale: it still named eight, included
`operational-learning`, and omitted `production-change-gate` and `stack-profile`. Its acceptance
criterion therefore could not be used unchanged.

The good pattern already existed in `obs-logs`, `obs-metrics`, `obs-traces`, `akamai-edge`, and
`eng-ladder`: keep authority and safety invariants in the entrypoint, then use predicate-keyed links
for conditional provider detail, examples, and long decision tables.

Specific audit-time prose and scope findings were:

- Remove forced “Announce at start” narration from `root-cause` and `ops-tooling`; it spends output
  tokens without improving the task result.
- Split the multi-topic `ops-tooling` body behind conditional references and remove “sonnet by
  default”; the fleet intentionally inherits the session model.
- Either scope `frontend-craft` to the team's stack or move TanStack/sidebar defaults behind a stack
  reference rather than call them universal UI requirements.
- For database migrations, require a tested recovery strategy—backout, roll-forward, restore, or
  expand-contract—not a reverse migration script when reversal would be more destructive.

## Routing assessment

Routing correctness was not fully demonstrated.

- `[verified]` The suite contained 76 structurally valid scenarios.
- `[verified]` Only 19 of 29 skills were direct targets.
- `[unverified]` No scenario directly targeted `agent-authoring`, `backend-craft`, `ci-actions`,
  `eng-ladder`, `frontend-craft`, `incident-command`, `obs-pipeline`, `ops-tooling`, `pcf-ops`, or
  `service-onboarding`.

That gap did not prove those skills misrouted. It meant route correctness for them was unmeasured.

The clearest unsafe combination was `service-onboarding`: one manual, effect-shaped workflow also
advertised a discoverable read-only audit, even though the two modes have different invocation
safety, inputs, effects, and success criteria. The recommended split was:

- **`service-readiness-audit`:** discoverable, read-only, evidence-cited findings, with no onboarding
  effects.
- **`service-onboarding`:** manual invocation, approved plan, and the existing onboarding and scribe
  handoff effects.

`ROUTE-002`, the existing `obs-logs`/`obs-alerting` collision, was already live backlog and was not
duplicated by this audit.

## Prompt engineering, Loop Engineering, and graph engineering

Prompt engineering was already first class in [`prompt-engineer`](../../agents/prompt-engineer.md)
and [`agent-authoring`](../../skills/agent-authoring/SKILL.md). A second prompt-engineering skill
would add routing ambiguity. The needed improvements were narrower:

- replace the obsolete trigger-only doctrine with the reconciled description rule;
- add discovery cases for “skill fires too often,” “wrong output shape,” and “design an agent
  workflow graph”;
- keep activation quality separate from output/behavior quality; and
- add a near miss so a code, import, dependency, knowledge, or GraphRAG request does not route to
  prompt engineering.

### Loop Engineering

The owner clarified on 2026-08-23 that **Loop Engineering is a separate first-class discipline**,
not shorthand for prompt engineering and not merely a cycle in an executable graph. The fleet
already named it in [`roster.md`](../../skills/agent-authoring/references/roster.md), and
[`artifact.md`](../../skills/agent-authoring/references/artifact.md) already supplied part of its
prompt/skill learning method. The audit gap was narrower but material: routing metadata did not make
the capability discoverable, and the general loop contract did not consistently require budgets,
termination, and promotion authority.

A bounded Loop Engineering contract names:

- the entry state and the state one iteration may change;
- the gather/action/verification stages and a verifier independent of the action's assertion;
- hard iteration, elapsed-time, cost, and candidate budgets appropriate to the loop;
- success, no-progress, safety/authority, and exhaustion termination conditions;
- missing or inconclusive evidence as a non-success outcome; and
- who may promote the result plus the durable evidence that supports that decision.

This contract applies both to prompt/eval improvement loops and to lane or system-control loops, but
their artifacts and verification targets differ. It also keeps two nearby concepts separate:

- [`operational-learning`](../../skills/operational-learning/SKILL.md) records a completed task's
  durable discovery and disposition; it is not an autonomous optimizer or the loop runtime.
- An executable workflow graph may contain retries or bounded cycles, but graph topology and state
  transitions do not by themselves supply the improvement loop's verifier, promotion rule, or
  outcome comparison.

The smallest correction is to expose and complete Loop Engineering in `agent-authoring` and its
roster reference, then measure both a distinguishing Loop Engineering request and the combined
over-trigger/wrong-shape case. A second loop skill would duplicate the current owner unless future
routing evidence shows a genuinely distinct user surface.

“Graph engineering” covers three distinct contracts and should not be treated as one vague lane:

1. **Roster/delegation graph.** Already present in
   [`delegation-graph.md`](../../skills/agent-authoring/references/delegation-graph.md): which agents
   exist, who can delegate, and which authority boundaries apply. It needs description and routing
   coverage, not a second implementation.
2. **Executable workflow/state graph.** Not complete. A future capability must cover typed input,
   state, output, node and edge contracts; deterministic versus model-selected edges; fan-out/fan-in
   and partial failure; retries, timeouts, idempotency, compensation, and unknown outcomes; approval
   interrupts before effects; durable checkpoints, resume, cancellation, supersession, and replay;
   bounded cycles and termination; trace lineage and taint; and graph-level path/outcome evals.
3. **Code/dependency/knowledge graph.** Repository atlases, dependency graphs, runtime topology, and
   GraphRAG have different inputs, provenance, and success criteria. They belong to a separate
   `codebase-atlas` capability if owner need is confirmed.

The portable method should come before a runtime choice. The deeper
[`2026-08-23 prompt, Context, Loop, and workflow-graph research refresh`](2026-08-23-prompt-loop-graph-engineering-research.md)
rechecks that conclusion against current OpenAI and Anthropic primary guidance, Context7 framework
contracts, and GitHits source and tests at named commits. It distinguishes manager-owned tools from
handoffs, deterministic from model-selected edges, and checkpointed graph progress from exactly-once
external effects. It also records the missing effect journal, reconciliation, `UNKNOWN` outcome,
resume/replay, approval, taint, observability, and graph-level eval contracts. The evidence supports
a portable contract first; it does not select LangGraph or any other runtime. Anthropic's still-valid
guidance likewise favors the simplest composable pattern whose measured outcome justifies its
complexity, while its current product-specific runtime guidance is treated as implementation
evidence rather than a universal architecture.

## SRE capability assessment

The audit identified possible gaps in this priority order, subject to owner confirmation:

1. **Service-level resilience and disaster recovery:** application/configuration recovery,
   dependency failover, foundation or region loss, RTO/RPO rehearsal, and evidence-bound drills.
2. **Capacity and performance engineering:** load models, saturation/headroom, autoscaling
   validation, representative load tests, bottleneck attribution, and growth forecasts.
3. **Network, DNS, TLS, and certificate operations:** live authority only if this team owns those
   layers; otherwise diagnosis and escalation boundaries.
4. **Vulnerability and upgrade campaigns:** advisory triage, patch ordering, compatibility,
   rollback, and post-upgrade verification.
5. **GCP cost and quota engineering:** only after the landing runtime and ownership split are
   ratified.

**Owner disposition (2026-08-23): hold the five listed additions; security incident response
remains rejected below.** None is active roadmap work. Reopen a held candidate only after a renewed
owner request names the operator need, ownership boundary, authority, and evidence required for
acceptance.

**Owner disposition:** do not add security incident response. The team does not own containment,
eradication, credential rotation, or security-event recovery. Preserve the existing narrow contract:
recognize suspected compromise, preserve evidence, and hand it to the human security incident owner.

Do not add Kubernetes/GKE operations while the landing runtime is decision-pending and self-managed
Kubernetes remains outside the team's lane.

## Staged remediation map

| Batch | Purpose | Audit disposition |
|---|---|---|
| 0 — correctness | Resolve the five operator-facing contradictions, with finding 4 waiting for authoritative version evidence. | Closed on current `main`; finding 4 closed only after its evidence condition became true. |
| 1 — routing contract | Adopt the reconciled description doctrine, split readiness audit from effect-shaped onboarding, complete the bounded Loop Engineering contract, and add prompt/loop/graph positive and near-miss cases. | Approved next bounded batch. |
| 2 — context reduction | Convert `incident-command` as the single reviewed router pattern, then process the remaining confirmed monoliths in bounded commits. | Tracked by `SKILL-001`; remeasure after Batch 1 rather than trust the stale eight-skill inventory. |
| 3 — capability decisions | Consider the SRE candidates and a portable executable workflow-graph method. | **Held.** No capability, runtime, or lane is active work; reopen only through a renewed owner decision with a concrete consumer and authority boundary. |

For every batch: edit canonical sources only; run focused tests owned by the changed contract; run
affected live routing scenarios only when routing content changes; regenerate projections once; and
run Gate A once at the push boundary.

## Audit-time verification boundary

Fresh checks at the audit baseline:

- `evals/run_evals.py --validate`: **76 scenarios valid**.
- `evals/test_graders.py`: **392/392 passed**.
- `evals/test_run_evals.py`: **73 passed** outside the Windows temporary-directory sandbox.
- `scripts/check_links.py`: passed.
- `scripts/test_canary_tokens.py`: **6 passed**.
- `scripts/test_runbook_schema.py`: **3 passed**.
- `scripts/test_readonly_guard.py`: **20 passed**.

No paid/full live routing campaign was run, so behavioral routing stayed `[unverified]` where no
current run existed. Gate A was not run during the read-only audit because the checkout began with
pre-existing deletions across generated projection roots; regenerating them would have disturbed
work outside the audit. Historical optimization-branch measurements were used only as prior evidence,
not as a substitute for remeasuring the canonical baseline.

## Batch 1 implementation evidence

The 2026-08-23 candidate `e00d821de7ccf43d158233734607b8c5b8d74156` added the service split,
description doctrine, Loop Engineering contract, and five routing scenarios. Focused static checks
passed: 25 policy tests, 28 link tests with one platform skip, 39 fleet tests, 38 adapter tests with
two platform skips, 82 structurally valid eval scenarios, link and fleet validators, and strict
Claude plugin validation. Removing the roster's no-progress termination deliberately failed the
new focused contract test; restoring it passed.

The bounded live run `20260823T053852Z-1e677acb` used Claude CLI 2.1.241, Sonnet 5, two trials, a
180-second ceiling, a clean plugin snapshot, and the exact candidate SHA:

- The code/dependency-graph near miss completed 2/2 without invoking `agent-authoring` and named the
  local repository-investigation lane instead. This is positive exclusion evidence.
- The Loop Engineering case invoked `save-toolkit:agent-authoring` in 2/2 trials. Both then lacked a
  terminal result: the skill correctly pointed to `references/artifact.md`, while the discovery
  session allowed only `Skill` and `Task`; nested agents inherited no usable `Read` tool and could
  not load the reference. Activation is therefore `[verified]`, while the response graders remain
  `[unverified]` rather than failed.
- The workflow-graph case also ran 2/2. Both trials timed out at 180 seconds without an attempted or
  completed target invocation or a terminal result, so that case is `[unverified]`, not failed.
- The service cases were not selected in this run. A second prompt-tuning or paid retry loop was not
  started.

This exposes an evaluator boundary, not evidence for moving conditional reference content back into
`SKILL.md`. Discovery routing and post-route behavior need distinct outcomes: an observed target
invocation can establish activation, while behavior that needs a denied reference remains
inconclusive and belongs in a direct/component-capable evaluation. The graph and service routing
cases remain `[unverified]` on the measured Batch 1 candidate until that evaluator boundary is
resolved.

One independent review of successor `926d0c0cbe8154562f94dc1470537c557acc35b5` found three P1
issues: a duplicate unbounded loop-until-dry definition, an inaccurate statement that the graph
trials had not run, and a Loop Engineering case whose older trigger cues could mask discoverability.
The reviewed successor was not mergeable as written. The next candidate makes both loop definitions
use K plus a hard maximum, corrects the run record, names Loop Engineering in routing metadata, adds
a distinguishing discovery case, and strengthens the focused regression to reject the old forms.
