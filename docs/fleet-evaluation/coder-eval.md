# Coder Eval adoption experiment

The owner approved adding UiPath Coder Eval to the specification on 2026-10-04. It is the first
candidate to pilot for custom agent/skill/tool regression execution in WP-02. Permanent adoption,
native compatibility and maintenance benefit remain [unverified]. This document specifies the
experiment; it does not authorize implementation, model spend or environment provisioning.

Use the exact project and revision in the [source register](sources.md#coder-eval-evidence).
The current native runner remains the reference until an alternative earns its named responsibilities.

## Product boundaries

| Product or component | Responsibility |
|---|---|
| Save Toolkit | Versioned agent roles, skills, investigation methods, delegation and authority |
| SRE Workbench | Operational checks, target resolution, limits, output protection and equivalent CLI/MCP observations |
| Evaluation system | Representative cases, frozen experiments, independent assessment, evidence preservation and comparisons for human decisions |
| Coder Eval, if accepted | Selected task execution, interaction capture and result collection behind a replaceable adapter |
| Benchmark or lab | Its tasks, environment and original verifier, with adaptation limits retained |

The unit under test is the versioned agent plus skills, context, tools and host configuration. A
framework's model label or copied prompt does not establish that identity. Coder Eval belongs in
development/evaluation workflows; Workbench operations and installed fleet behavior do not depend
on it. The evaluation product can deliver value before Workbench is implemented.

Keep one canonical case source, one authoritative evidence bundle and one selected presentation
path. Share independent checks through artifact mappings. Do not create a second operational console,
general-purpose result ledger or permanent mirror of the native runner without a distinct consumer.

## Integration contract

1. **Actual subject:** load the canonical plugin and preserve agent/skill selection, permitted and
   denied tools, hooks, helper return, parent continuation and resume. Record host-added instructions,
   authentication and prompt append/replace semantics. Use AC-03/04/05 to establish claim scope.
   If a supported adapter cannot preserve it, assess an external agent plugin or thin native bridge.
   An incompatible SDK profile can produce bounded artifact evidence, but cannot claim native parity.
2. **Single execution ownership:** declare who owns scheduling, repetition, retries, deadlines,
   cancellation and environment lifecycle. Expose necessary inner limits and attempts. If Harbor is
   selected for a benchmark environment, assess the existing upstream bridge before writing another;
   it does not itself prove compatibility with our chosen tasks or admit external code execution.
3. **Independent assessment:** retain the accepted native graders and judge. Keep specialized
   incident, authority and evidence checks outside Coder Eval's typed criterion schema initially.
   A successful command or skill-engagement signal does not establish a correct investigation.
   Use independent expected outcomes; avoid making the response-selection matcher the only oracle.
4. **Artifacts:** retain original per-replicate `task.json`, its trace/artifact references and resolved
   configuration lineage, together with native records. Preserve upstream terminal status, per-check
   errors, evaluated/not-evaluated state, gating and scores. Map separately to the fleet's
   [assessment contract](contracts.md#execution-and-assessment), retaining differences and omissions.
   Upstream gating and weighted score are distinct; neither replaces fleet blocking dispositions.
5. **Cost and recovery:** keep candidate/helper/judge/simulator attribution and cost completeness;
   unknown spend never becomes zero. Distinguish fresh trials, replay, rescoring and retries.
   Preserve partial evidence and test interrupted collection/publication and relocated evidence links.
6. **Isolation and authority:** declare and test the actual execution environment. A temporary
   workspace or supported Docker option is not proof of containment. Existing tool grants,
   protected-output requirements, manual model sessions and DEC-13 external-code admission remain
   applicable. Offline adapters/controls can run in CI; this plan adds no model-in-CI exception.

## Experiment sequence

### 1. Model-free measurement controls

Freeze correct, incorrect and unavailable-result controls independently of either importer. Feed
both mapping paths equivalent evidence, including a correct repair, a plausible repair with a
regression, and an environment failure. Preserve upstream records while requiring the same applicable
fleet verdicts, denominators, decisive evidence references and original spend.

Include task-budget exhaustion versus provider/runner outage, an omitted artifact versus collector
loss, wrong candidate identity, denied tools, missing criterion results, cached output, nested
repetitions and interrupted publication. Missing evidence stays explicit. These controls establish
measurement behavior and reporting, not model capability. Material mapping errors stop live trials.

### 2. Host compatibility and six-task feasibility pilot

Run the AC-03/04/05 native canaries before the task comparison; stop on material incompatibility and
record the failed opportunity. Select six tasks before seeing results:

| Cases | Purpose | Independent evidence |
|---|---|---|
| Two team-authored coding tasks | Repair an operator-tool defect; preserve an already correct behavior | Hidden repair/regression checks and patch/command receipts |
| Two operational investigations | One PCF evidence case and one GCP managed-service/migration case with target/access ambiguity | Withheld good/bad/unavailable controls, supported next steps and retained uncertainty |
| Two skill/tool/helper tasks | Unhinted skill/tool selection; helper return followed by parent continuation | Actual runtime events, successful/denied tool results and evidence used in the final answer |

Use the same frozen fleet candidate, concrete model, host/authentication path, permissions, inputs,
limits and scorer identities across native and Coder Eval arms. Record unavoidable differences as
experimental variables. Alternate runner order, reset workspaces and preserve all failed attempts.
Partition operational families from tuning material. Team-authored coding cases keep this pilot
independent of external benchmark admission; later external tasks still require DEC-13 and AC-25.

The proposed bounded pilot is six tasks x two runners x two repetitions = 24 task trials. This is
a feasibility sample, not evidence of statistical superiority or rare-event safety. Canaries,
helpers, judges and any simulator calls are additional and need their own predeclared counts and
budget. Do not enable dialog simulation for this pilot. Actual execution requires its own run plan.

A runner comparison holds the agent fixed and measures runner influence. A later agent/skill/tool
improvement claim needs a separate matched incumbent/candidate comparison through the selected
compatible path, with grading fixed. Do not attribute a wrapper, permission or model change to a
better skill. Candidate-dependent runner effects require further investigation before transfer claims.

### 3. Maintainer usefulness and maintenance

Present the controlled correct/regression/unavailable outputs without naming the runner to a
reviewer who did not author their expected outcomes. Require the correct disposition (accept, repair
or insufficient evidence) and identification of the decisive evidence; measure time and manual transcript
reconstruction. An apparently attractive score must not conceal missing measurement or a blocking failure.

Have a second maintainer author equivalent versions of two selected tasks from their canonical case
definitions using each runner's documentation. Alternate order to reduce learning bias. Record
authoring/debugging time, bespoke code, human intervention, evidence retrieval and replay effort.
Treat these small-sample observations as practical feasibility evidence, not general productivity claims.

Before trials, record the practical benefit required under DEC-16: less owned implementation and
manual work, or one named missing capability at an accepted maintenance cost. Compare against the
smallest native/Inspect extension that meets the same need. Inventory what adoption removes, retains
and adds, including dependencies, adapters, checks, case mappings, report paths, upgrades and rollback.

## Operational and Workbench applicability

A representative GCP task can ask the agent to investigate an order-service error increase, retain
the correct project/service/revision, use traffic/error observations, and handle a denied read without
inventing a result. Assess supported next steps and handover quality independently of invocation count.
Use only the selected lane's admitted interfaces; otherwise supply reviewed observations.

[sourced] Coder Eval's CLI fixtures record calls and return matched canned outputs, but are stateless
and do not proxy a real executable. They can test interpretation and command construction. Changing
observations require an authored stateful fixture meeting AC-26; a model-simulated conversation is a
separate experiment. See the [pinned evidence](sources.md#coder-eval-evidence).

Fixture results do not establish live Google Cloud behavior, Workbench command correctness or
CLI/MCP equivalence. Workbench's own deterministic contract tests own those implementation claims;
later evaluations exercise the actual interface and assess whether agents use its observations
effectively. WP-14 still owns live-cloud evidence. The six-task pilot does not complete the 24-case
GCP pilot, 64-case catalog, branching profiles, human tabletops or any benchmark milestone.

## Adoption and exit criteria

AC-36/37 and DEC-16 record one of these dispositions, with evidence rather than framework preference:

| Disposition | Required basis | Consequence |
|---|---|---|
| Adopt named responsibilities | Native and measurement compatibility pass; independent outcomes discriminate; maintainer evidence meets the predeclared benefit | Pin the selected release, choose one presentation path and remove accepted superseded orchestration while retaining native conformance/rollback evidence |
| Retain a limited role | A useful artifact-only or other bounded capability passes while broader parity/benefit is absent | Label the narrow claim and consumer; native acceptance remains authoritative |
| Reject adoption | Evidence weakens, parity requires an unacceptable subject change, or integration costs lack the declared benefit | Keep the native path and capability requirements; preserve findings and remove disposable experimental dependencies when their retention need ends |

A supported early rejection can complete the adoption assessment without completing 24 trials; name
the failed gate and unmeasured cases. An unfinished assessment cannot be called rejection merely to
close WP-02. Its other native acceptance checks remain required under every disposition.
Native-backed work can proceed once the separate readiness checks in [delivery](delivery.md#work-packages)
pass, even while this assessment remains open. That does not admit the alternative runner.

Select reporting after this evidence: promptfoo remains a presentation/adversarial-authoring
candidate, Coder Eval's report may suffice, or a minimal local view may be retained. Reports must
still pass Windows/Linux import and relocation acceptance. Judge replacement remains EVAL-010's
separate decision; the coding environment remains DEC-06's decision. No tool score promotes a fleet
candidate. Implementation status belongs only to [EVAL-012](../fleet-roadmap.md#eval-012--plan-incident-and-coding-evaluations-for-the-fleet).
