# Full skill audit — batch 1: authoring and governance

> **Status: review evidence, not a second backlog.** This batch audits exactly five canonical
> skills on the revision named below. Recommendations not implemented here require a new owner
> decision before they become work.

**Audit baseline:** `b9b274f237caf8ce6068812e151f8543f608c7e7`
**Batch scope:** `agent-authoring`, `agent-security`, `eng-ladder`, `language-idiom`, and
`operational-learning`
**Audit date:** 2026-08-24

## Conclusion

All five skills have clear purposes and strong safety boundaries. Three require no entrypoint
change. The smallest effective batch is three corrections:

1. Reconcile `agent-authoring`'s stale, settled statement about plugin
   `disable-model-invocation` with the current documented contract and the still-unprobed runtime.
2. Make `eng-ladder` distinguish “do not preload tiers” from a later evidence-driven altitude
   transition.
3. Make `language-idiom` distinguish one language reference from an additional applicable
   tests-first or safe-refactoring process.

No description changes, new skills, schemas, scripts, agents, graphs, or live-model retries are
justified by this batch.

## Method and evidence

### Local baseline

- `[verified]` The repository contains 30 canonical skill entrypoints totaling 192,796 Git-object
  bytes at the audit baseline. Batch 1 entrypoints range from 2,475 to 9,420 bytes and are all below
  the portable specification's recommended 5,000-token instruction budget.
- `[verified]` Every Batch 1 entrypoint and every bundled reference or asset was inspected. The
  pre-change link validator passed.
- `[verified]` `py -3 evals/run_evals.py --validate` accepted 84 scenarios: 23 direct, 61
  discovery, and 35 regression.
- `[verified]` `py -3 scripts/test_validate_fleet.py` passed 42 tests before the change.
- `[verified]` The installed Claude Code CLI reports 2.1.241.
- `[unverified]` No live routing trial was run for this batch. No routing description changed, and
  the repository rule does not require a paid after-change trial for body/reference clarifications.
  Existing run evidence is cited where it already establishes a boundary; otherwise routing remains
  unmeasured rather than being inferred from prose.

### Current external contracts

- `[sourced, portable]` The [Agent Skills specification](https://agentskills.io/specification)
  requires `name` and `description`, defines `scripts/`, `references/`, and `assets/` as optional,
  recommends progressive disclosure, recommends a sub-5,000-token entrypoint, and treats
  `allowed-tools` as experimental.
- `[sourced, OpenAI-specific]` [OpenAI's current skill guidance](https://developers.openai.com/plugins/build/skills)
  says descriptions carry the workflow and trigger conditions while detailed procedure and safety
  remain in the body; supporting files need explicit load/run conditions; representative tests
  should cover direct, indirect, incomplete, negative, and unsupported-action requests; and
  activation and output quality are separate evidence layers.
- `[sourced, OpenAI model guidance]` [OpenAI's current prompting guidance](https://developers.openai.com/api/docs/guides/latest-model)
  recommends removing repeated instructions incrementally, retaining examples that encode product
  requirements, defining autonomy and approval boundaries once, and rerunning the same representative
  tasks before and after a material change.
- `[sourced, Anthropic-specific]` [Claude Code's current skill documentation](https://code.claude.com/docs/en/slash-commands)
  says invoked content persists in the conversation, may be truncated or dropped during compaction,
  and documents `disable-model-invocation` as a user-only invocation control. It also distinguishes
  pre-approval through `allowed-tools` from actual restriction.
- `[sourced, context engineering]` [Anthropic's context-engineering guidance](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  argues for the smallest high-signal context that fully specifies expected behavior; “minimal” is
  not synonymous with short.
- `[sourced, VS Code-specific]` [VS Code's current Agent Skills documentation](https://code.visualstudio.com/docs/agent-customization/agent-skills)
  implements the same three-stage loading model while adding host-specific invocation and
  experimental forked-context fields.
- `[sourced, Context7]` Context7's `/openai/skills` index corroborated the three-level loading model
  and the standard directory shape. GitHits then established from the
  [`openai/skills` README at `49f948f`](https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/README.md#L1-L3)
  that the repository is deprecated, so that result is historical corroboration, not the current
  OpenAI authority.
- `[verified, GitHits]` Exact-source inspection of
  [`anthropics/skills` at `3b3fad9`](https://github.com/anthropics/skills/tree/3b3fad96af16a10759d930941b4520ba0c40edae)
  and
  [`github/awesome-copilot` at `4742f26`](https://github.com/github/awesome-copilot/tree/4742f265959bf025882314564b364d9d7af6e2d5)
  found the repeated public pattern of concise selection metadata, predicate-linked resources, and
  deterministic validators. The repositories disagree on unknown frontmatter handling, so passing
  one repository's validator is not a portability proof.

### Vendor disagreement retained

Current official Claude documentation presents `disable-model-invocation` on plugin skills as a
supported contract. A historical upstream report
([`anthropics/claude-code#22345`](https://github.com/anthropics/claude-code/issues/22345), CLI
2.1.29) and this fleet's 2026-07-17 probe on CLI 2.1.212 observed the field ignored for
plugin-packaged skills.
No current plugin-specific visibility canary was found in the 2.1.236 release evidence, and this
batch did not spend a live call to manufacture certainty. The reference now records the documented
contract, the historical counter-evidence, and the current runtime boundary as `[unverified]`.

## Skill: `agent-authoring`

### Overall Assessment

**Minor Changes**

### Purpose

Owns LLM-facing artifact design and repair, routing metadata, tool and context contracts, bounded
Loop Engineering, and roster/delegation design without claiming source-code graph or runtime
implementation work.

### Findings

- **Routing:** The capability, invocation cues, and graph exclusions are explicit. Existing
  scenarios cover prompt/skill repair, Loop Engineering, workflow-graph selection, and a
  code-dependency near miss. Historical evidence observed the code-graph exclusion 2/2 and Loop
  Engineering activation 2/2; workflow-graph activation remained inconclusive because the
  discovery harness could not load the linked reference.
- **Instructions:** The entrypoint separates selection, evidence matching, minimal change, and
  retest scope. It avoids presenting all prompt work as a rewrite campaign.
- **Accuracy:** **Outdated** for one platform claim: the frontmatter reference described plugin
  `disable-model-invocation` as unconditionally ignored despite a newer official contract that says
  it should be honored. The actual current runtime remains **Unable to verify**.
- **Context:** Good progressive disclosure. The 9,420-byte entrypoint routes specialized artifact,
  roster, delegation, tools, context, frontmatter, and portability detail to seven focused files.
- **References / Assets / Scripts:** References are directly linked and purpose-keyed. No script or
  schema is justified for semantic prompt judgment; repository validators already own deterministic
  structure.
- **Tools:** Correctly distinguishes prose, typed schemas, tools, deterministic boundaries, and
  harness behavior.
- **Orchestration:** Bounded candidate/iteration/cost contracts and explicit promotion authority
  prevent an uncontrolled self-improvement loop.
- **Failure Handling:** Missing or inconclusive evidence cannot become success; imported artifacts
  receive static inspection unless the disposable execution boundary exists.
- **Verification:** Strong structural and scenario coverage, with the discovery/reference limitation
  stated rather than hidden.
- **Portability:** The dedicated portability reference correctly separates the portable six from
  Claude and VS Code extensions. Host enforcement is never inferred from shared syntax.

### Routing Tests

#### Should trigger

1. “My release-notes skill fires on unrelated documentation and returns prose instead of JSON.”
2. “Design a bounded Loop Engineering contract for improving this grader.”
3. “Design the agents, delegation edges, joins, authority boundaries, and termination for review.”

#### Should not trigger

1. “Map Python import cycles in this repository.”
2. “Implement this approved state graph in the runtime we already selected.”
3. “Capture the durable operational lesson from this completed restore drill.”

#### Boundary cases

1. “Design the LLM-facing node and edge contracts, but do not choose or implement a graph runtime.”
2. “The tool output is malformed; determine whether the prompt, schema, or wrapper owns it.”

**Evaluation:** `[verified]` Existing scenarios cover five of these intent shapes across positive,
negative, and boundary behavior. `[unverified]` This batch did not produce a numeric precision or
recall estimate; the current suite is a targeted regression set, not a representative traffic
sample.

### Recommended Changes

#### Change 1 — reconcile plugin invocation-control evidence

- **Problem:** The reference presented a historical runtime failure as the settled current contract.
- **Evidence:** Current official Claude docs document the field for plugin skills; historical issue
  and fleet probes observed it ignored; no current plugin-specific canary reconciles them.
- **Change:** State the documented contract, retain the historical counter-evidence, label current
  plugin enforcement `[unverified]`, and keep body-level authority deferral.
- **Expected improvement:** More accurate platform guidance without weakening the safety boundary.
- **Risk/tradeoff:** The extra qualification costs a few tokens, but prevents both false confidence
  and a false claim that the feature is permanently unsupported.

### Keep As-Is

- Keep the scope-bearing description and explicit code/dependency/knowledge-graph exclusions.
- Keep activation evidence separate from reference-dependent output evidence.
- Keep one candidate by default, hard budgets, no-progress termination, and human promotion.
- Keep frontmatter and portability facts in dedicated references rather than duplicating them in
  every skill.

## Skill: `agent-security`

### Overall Assessment

**Good**

### Purpose

Reviews agent flows for prompt injection, sensitive-data exposure, external action, least privilege,
unsafe delegation, and blast radius while separating structural controls from prose claims.

### Findings

- **Routing:** Positive triggers and concrete surfaces are clear. The skill names security review,
  prompt injection, and log/webhook exposure without claiming general application-security review.
- **Instructions:** The lethal-trifecta model supplies a compact threat path, and the five review
  questions turn it into an executable inspection method.
- **Accuracy:** **Verified** against the current local tool/guard model and **Likely correct** for the
  cited external threat models. Runtime claims must still be re-probed per host, which the skill
  requires.
- **Context:** The core threat model stays in the entrypoint; fleet integration and OWASP crosswalk
  detail load only when their predicates match.
- **References / Assets / Scripts:** Two focused references are appropriate. A deterministic script
  cannot replace the semantic source-to-sink review.
- **Tools:** Correctly treats tool absence, command guards, host isolation, schemas, and approval as
  distinct controls.
- **Orchestration:** Explicitly evaluates the trifecta per agent and across handoffs; delegation is
  not mistaken for a trust boundary.
- **Failure Handling:** Unknown runtime enforcement becomes a finding, and suspected compromise
  routes to the human security incident owner without speculative remediation.
- **Verification:** Two direct scenarios test injected log text and an injected directive aimed at a
  writer. They validate handling after selection, not discovery precision.
- **Portability:** Structural control claims are host-bound. The prose threat model is portable.

### Routing Tests

#### Should trigger

1. “Is this log-reading agent safe if it also has Bash and outbound network access?”
2. “Review this agent handoff for prompt-injection and data-exfiltration risk.”
3. “What blast radius does this MCP-enabled deployment assistant have?”

#### Should not trigger

1. “Review this web API for SQL injection in its query builder.”
2. “Triage this active production authentication outage.”
3. “Write a general threat model for the whole application repository.”

#### Boundary cases

1. “A dependency advisory affects an MCP server the agent can call; assess the agent-specific path.”
2. “The prompt says read-only, but the host tool picker may restore execute—what is actually enforced?”

**Evaluation:** `[verified]` Existing direct scenarios cover injected data in read-only and
write-capable contexts. `[unverified]` No discovery scenario establishes precision or recall for the
skill's own description.

### Recommended Changes

None. Adding generic application-security content would blur the lane; adding a schema would not
make the semantic threat analysis safer.

### Keep As-Is

- Keep the trifecta and Rule of Two as reasoning aids, not prompt-only controls.
- Keep taint across handoffs and the warning that delegation is not isolation.
- Keep structural controls separate from prose and require a concrete answer to each review question.
- Keep suspected active compromise with the human security incident owner.

## Skill: `eng-ladder`

### Overall Assessment

**Minor Changes**

### Purpose

Selects the engineering or SRE altitude that a task earns, distinguishes ownership from required
consultation, and assesses artifacts without inventing higher-level ceremony.

### Findings

- **Routing:** The description names rigor/altitude questions and excludes ordinary scoped work.
  No repository scenario directly targets this skill, so description quality is not measured.
- **Instructions:** One contradiction existed: the entrypoint said tier files were alternatives and
  to read exactly one, while selected tier files can explicitly escalate to another tier after the
  scope changes. “Do not preload” is the actual invariant.
- **Accuracy:** **Likely correct.** The ladder is an internal convention rather than a vendor
  standard; the artifact correctly presents it as this fleet's decision method.
- **Context:** Seven tier references keep detailed bars conditional. The entrypoint is a compact
  router despite serving both engineering and SRE tracks.
- **References / Assets / Scripts:** References are the right form. A scoring script would encode
  semantic judgment badly.
- **Tools:** No tool contract is needed; each selected lane owns its tools.
- **Orchestration:** Ownership-versus-consult and in-context-versus-delegated execution are explicit.
- **Failure Handling:** Lower tiers escalate on observed scope; a delegated worker returns the fork
  instead of silently self-promoting.
- **Verification:** No dedicated routing scenario exists. The eight cases below are the batch's
  static routing design set.
- **Portability:** Entirely prose and relative references; no vendor field controls behavior.

### Routing Tests

#### Should trigger

1. “How rigorous should this migration design be?”
2. “Review this proposal at the principal-engineer bar.”
3. “Is this alert investigation responder, investigator, or elite SRE work?”

#### Should not trigger

1. “Add this field to the existing endpoint using the repository's established pattern.”
2. “Triage the production alert that is firing right now.”
3. “Write a Python parser and its unit tests.”

#### Boundary cases

1. “The implementation is local, but one config choice creates a standing cross-service obligation.”
2. “A first-response investigation has now proven a shared-dependency cascading failure.”

**Evaluation:** `[unverified]` No current live or regression scenario measures these routes. The
description's explicit ordinary-work exclusion is strong static evidence but cannot produce a
precision or recall number.

### Recommended Changes

#### Change 1 — make tier loading state-dependent

- **Problem:** “Read exactly one tier” conflicted with evidence-driven escalation instructions.
- **Evidence:** `builder`, `principal`, and SRE tier references explicitly direct a move when scope
  crosses their boundary.
- **Change:** Say to load only the starting tier, never preload neighbors, and load a different tier
  only after evidence or an explicit escalation rule changes the altitude.
- **Expected improvement:** Preserves context efficiency without telling the model to ignore a
  legitimate escalation.
- **Risk/tradeoff:** A model may retain the earlier tier in context after escalation; the wording
  avoids claiming that already-loaded context can be removed.

### Keep As-Is

- Keep builder/principal/distinguished and responder/investigator/elite as separate tracks.
- Keep ownership distinct from a required senior consult.
- Keep “route down when unsure” and escalate on a named fork.
- Keep simple artifacts eligible to meet the bar without manufactured gaps.

## Skill: `language-idiom`

### Overall Assessment

**Minor Changes**

### Purpose

Routes language-level implementation, review, testing, debugging, and safe refactoring to focused
Python, Java, TypeScript, Bash, PowerShell, and Go guidance while leaving backend and UI architecture
to their owning skills.

### Findings

- **Routing:** Language triggers are concrete, and the description names backend/frontend
  ownership boundaries. Existing Java discovery and Go/Java direct scenarios establish partial
  language selection coverage.
- **Instructions:** One ambiguity existed: “load only the language file” could suppress the same
  router's tests-first or safe-refactoring process when both predicates apply.
- **Accuracy:** **Verified** for the TypeScript 5.2 disposal/polyfill claim through Context7's
  current official TypeScript documentation; **Likely correct** for the remaining language guidance,
  which is version-gated and tells the model to read the repository contract first. Deployed Java,
  Bash, PowerShell, and Python versions remain target-specific and are correctly not invented.
- **Context:** At 2,475 bytes, the entrypoint is an efficient router over eight focused references.
- **References / Assets / Scripts:** Per-language references plus two cross-language processes are
  appropriate. The language-specific commands belong in references; no shared script could validate
  arbitrary repositories reliably.
- **Tools:** The selected repository's formatter, linter, typechecker, and test runner remain
  authoritative. The skill avoids forcing one package manager or framework where a repo differs.
- **Orchestration:** Language craft composes with backend/frontend ownership rather than creating a
  new agent handoff.
- **Failure Handling:** Each reference emphasizes explicit error paths and verification. The main
  router needed only the corrected co-load rule.
- **Verification:** Three scenarios cover Java discovery and Go/Java reference reachability. Other
  languages and process co-loading are unmeasured.
- **Portability:** Plain Markdown and direct references are portable; individual tooling defaults
  are internal conventions, not Agent Skills requirements.

### Routing Tests

#### Should trigger

1. “Review this Bash script for quoting and failure-handling problems.”
2. “Fix this Python bug regression-first and keep the surrounding conventions.”
3. “Safely refactor this Go package without changing observable behavior.”

#### Should not trigger

1. “Design the authentication and retry contract for this REST API.”
2. “Redesign this dashboard's information architecture and accessibility states.”
3. “Investigate why the production service is timing out.”

#### Boundary cases

1. “Implement a typed React state machine; apply language rules, but keep UI architecture with the UI lane.”
2. “Refactor a Python API handler where the API contract must not change.”

**Evaluation:** `[verified]` Existing scenarios cover Java discovery and Go/Java direct behavior.
`[unverified]` No representative traffic sample supports numeric precision/recall, and the combined
language-plus-process load rule has no live trial.

### Recommended Changes

#### Change 1 — distinguish language selection from process composition

- **Problem:** The old absolute “only” could prevent loading `tdd.md` or `safe-refactor.md` when the
  task explicitly required one.
- **Evidence:** The same entrypoint advertises those two process references, and both are applicable
  alongside exactly one language reference.
- **Change:** Load one language reference; additionally load tests-first for new behavior/bug fixes
  or safe-refactoring for behavior-preserving reshapes; never preload unrelated languages/processes.
- **Expected improvement:** Correct process selection with bounded context.
- **Risk/tradeoff:** A qualifying task loads a second reference. That is intentional context needed
  for reliable execution, not duplication.

### Keep As-Is

- Keep repository version/tooling contracts ahead of generic defaults.
- Keep language references separate instead of one large always-loaded guide.
- Keep silent wrong-state failures and neighboring-code inspection as cross-language invariants.
- Keep backend and frontend architecture ownership explicit.

## Skill: `operational-learning`

### Overall Assessment

**Good**

### Purpose

Turns completed, evidence-bound operational discoveries into reviewable documentation changes or
owned dispositions without allowing model assertions to approve or self-promote durable knowledge.

### Findings

- **Routing:** The description requires scribe-selected closeout or explicit invocation and names
  the neighboring owners for active incidents, alert design, direct KB writing, and fleet prompt
  work. Existing positive and near-miss scenarios cover these boundaries.
- **Instructions:** The closeout sequence is explicit about revision binding, inventory,
  evidence labels, dispositions, minimal diff, and review return.
- **Accuracy:** **Verified** against the repository's live documentation-authority and disposition
  policies. This is an internal governance contract, not a vendor claim.
- **Context:** The entrypoint retains authority and disposition invariants while one policy and
  three templates load only when the closeout needs them.
- **References / Assets / Scripts:** The disposition policy is a reference; reusable card/index
  shapes are correctly assets. No script or schema is justified because target repositories may
  have different conventions and the classifications require judgment.
- **Tools:** The skill accurately reflects `scribe`'s no-Bash/no-web/no-delegation boundary and does
  not claim that prose grants authority.
- **Orchestration:** Handoffs name owner, evidence, revision, changes, gaps, and non-actions.
- **Failure Handling:** Missing or mismatched checkout binding downgrades `prepared` to `proposed` or
  `blocked`; active incidents never become retrospective KB edits.
- **Verification:** Discovery scenarios cover durable lessons, fleet-prompt deferral, and direct KB
  writing deferral. Runtime execution remains unnecessary for this batch.
- **Portability:** The method is portable prose; its paths, labels, and authorities are deliberate
  internal conventions.

### Routing Tests

#### Should trigger

1. “Knowledge closeout mode is selected; disposition the completed restore-drill findings.”
2. “Apply operational-learning closeout to this resolved incident evidence.”
3. “Capture durable operational lessons, but no authorized checkout is mounted.”

#### Should not trigger

1. “Write the approved service and alert cards from this evidence.”
2. “The production alert is firing; investigate it now.”
3. “Tune the reviewer prompt and add a named regression.”

#### Boundary cases

1. “The incident is resolved, but the target checkout SHA does not match the supplied revision.”
2. “A runbook is contradicted by a drill, but no owner has approved a documentation path.”

**Evaluation:** `[verified]` Existing discovery scenarios exercise one positive, one prompt-work
near miss, and one direct-writing near miss. `[unverified]` They are focused cases, not a traffic
distribution from which numeric precision or recall can be calculated.

### Recommended Changes

None. The current detail is safety- and authority-bearing; shortening it would remove conditions
that distinguish `prepared` from an unsupported durable claim.

### Keep As-Is

- Keep durable learning as reviewable repository state, never autonomous memory.
- Keep `prepared`, `proposed`, `blocked`, `duplicate`, and `not_applicable` explicit.
- Keep exact checkout binding and human review as separate gates.
- Keep direct KB writing with `scribe`, active incidents with `sre`, and fleet behavior with
  `prompt-engineer`.

## Architecture Findings

1. **Strong progressive disclosure:** All five skills keep specialized detail in directly linked
   resources. `language-idiom` is the clearest compact router; `agent-authoring` appropriately keeps
   shared safety and evidence rules in the entrypoint.
2. **Platform claims need three states:** Documented contract, historical/probed behavior, and
   current unprobed runtime behavior must not collapse into one sentence. The
   `disable-model-invocation` correction is the batch's concrete example.
3. **“Load only” needs an observable scope:** It should mean “do not preload irrelevant siblings,”
   not “ignore a later predicate that legitimately requires another tier or process.”
4. **Safety repetition is justified:** Evidence labels, untrusted-content posture, and human-owned
   effects recur because each skill folder is independently shippable. Centralizing them outside
   the bundle would break portability and weaken behavior when a skill ships alone.

## Routing Conflicts

- `agent-authoring` versus `operational-learning` is well separated: LLM-facing artifact failure
  versus completed operational closeout.
- `language-idiom` overlaps backend/frontend topics only at the language layer; the entrypoint
  explicitly leaves API/resiliency and UI architecture to their owners.
- `eng-ladder` can be named in many engineering discussions, but its ordinary-scoped-work exclusion
  prevents it from becoming mandatory ceremony for every task. This remains unmeasured live.
- `agent-security` is agent-flow security, not a general application-security audit. A future
  description change should name that exclusion only if real misrouting is observed.

## Shared Resource Opportunities

None recommended. The repeated safety and evidence rules are intentionally local because Agent
Skills packages must remain self-contained. A repository-global shared reference would save bytes
but make separately installed skills incomplete.

## Missing Capabilities

None established by this batch. It would be inappropriate to mint a new security, ladder, language,
or learning skill from hypothetical coverage preferences.

## Standards / Portability Issues

- `argument-hint` is useful on Claude and VS Code but is not part of the portable Agent Skills core.
- `disable-model-invocation` is host-specific and cannot carry the safety boundary by itself.
- `allowed-tools` is an experimental portable grant, not a restriction, and host support differs.
- The fleet's evidence labels, lane names, and disposition states are internal conventions.

## Evaluation Gaps

- `eng-ladder` has no dedicated routing scenario.
- `agent-security` has direct behavior checks but no own-description discovery check.
- `language-idiom` lacks discovery coverage for Bash, PowerShell, Python, TypeScript, and Go, and no
  case measures language-plus-process composition.
- Existing targeted cases cannot yield traffic-weighted precision or recall. Report those metrics
  only after a representative prompt sample and model/run contract exist.

These are evidence gaps, not automatic backlog items. The routing cases in this report are the
review set; promoting any into the executable suite requires a named observed failure or an owner-
accepted coverage contract.

## Recommended Architectural Changes

### Critical

None.

### High

None.

### Medium

- **Implemented:** Represent platform facts as documented, probed, or `[unverified]` when those
  sources disagree.

### Low

- **Implemented:** Use predicate-scoped “do not preload” language instead of absolute “load only”
  wording where legitimate escalation or process composition exists.

No further architectural work is activated by this review.
