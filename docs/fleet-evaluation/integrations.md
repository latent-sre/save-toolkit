# Benchmark and framework integrations

This document assigns each tool a bounded role. Capability descriptions marked [sourced] come from
the [source register](sources.md); actual fleet integration remains [unverified]. Source snapshots
and mutable documentation are discovery evidence, not package pins. Resolve versions and compatibility
before an implementation phase installs anything.

## ITBench Lite

**Role:** fixed-evidence incident diagnosis, included in scope. [sourced] The dataset supplies SRE
snapshots and fault ground truth. It cannot establish live investigation or remediation behavior.

**Adapter:** select a versioned subset; stage only observable inputs; keep answers outside the
candidate's accessible workspace; retain original IDs and an adaptation record. Map the agent's
answer into the upstream assessment input without inventing missing claims. Prefer exact entity
matching where possible; any semantic extraction or JSON repair is recorded and separately checked.

**First proof:** five selected cases spanning distinct fault mechanisms, with a correct/incorrect
answer control and an inaccessible-answer check. Include unsupported-evidence responses in calibration.
Full original scoring and the team's operational rubric appear as separate report dimensions.

## SREGym

**Role:** live diagnosis and later guided mitigation/recovery, included in scope. [sourced] The
project has a Claude Code client and selectable diagnosis/mitigation stages. Its small suite is a
candidate for pilot selection; stage selection alone does not constrain tool effects.

**Adapter:** package the exact fleet plugin, preserve role/tool/hook behavior, connect only the
reviewed lab observations, retain transcripts and submissions, and map oracle outcomes. Confirm that
the Claude launcher loads the intended plugin; the existence of a Claude client is not proof of it.
Keep Kubernetes-specific and application-level findings distinguishable for PCF/GCP applicability.

**Lifecycle:** verify healthy baseline, inject the selected fault, verify its signature, run the
assigned stages, collect artifacts, restore the environment, verify restoration and record cleanup.
An absent injected fault is an invalid exercise. Failure to reset blocks the next run. Serial
execution is the initial design; parallelism needs independent lab state and measured capacity.

**First proof:** three task types selected after host/resource review. Start with diagnosis. Add an
advisor plus lab-actor recovery profile in WP-07, recording who actually changed what. Judge system
recovery and advice quality separately. Keep upstream stage completion and fleet acceptance separate.

## Microsoft AIOpsLab

**Role:** later environment extension. [sourced] Problems combine an application, task, workload,
fault and evaluator. This supports a future need for additional workload/fault designs.

**Adapter:** reuse the logical case/run/assessment fields while retaining the AIOpsLab session and
native evaluator output. Reuse existing agents through a reviewed host bridge, not a rewrite into
another agent implementation. Define setup/reset semantics and independently constrain action tools.

**Entry criterion:** name an incident family or experiment the existing integrations do not serve
well enough, document its value and operational cost, then implement one representative task. AIOpsLab
is in the later scope; its task selection must make the added environment useful rather than duplicate
a leaderboard run.

## SWE bench Verified

**Role:** primary repository bug-repair benchmark. [sourced] Verified is a human-filtered 500-case
subset; the official harness evaluates supplied patches. We can supply patches from our agent.

**Adapter:** stage the task's repository revision and issue, load software-engineer, retain the diff
and trace, then have the DEC-13 admitted execution actor apply the patch and run checks in a clean
verification environment. Follow the [coding admission contract](architecture.md#coding-execution-admission);
the canonical agent does not gain permission to run external code merely by entering a container.
Do not expose reference fixes or evaluator-only tests to it. Preserve required repair/regression
outcomes and actor-bound receipts. Distinguish an invalid environment from a wrong patch.

**First proof:** 10 selected cases, expandable to 20 after environment/cost measurements. Choose
several repositories and defect types; fix the selection before viewing candidate scores. Treat this
as a pilot subset, not the complete benchmark. Assess reproduction, scope, self-verification and
review separately, only where the admitted profile can exercise them. Static authoring followed by
CI verification does not pass a check requiring the agent's own foreground test execution.

## SWT Bench

**Role:** bug reproduction and test generation after the repair adapter. [sourced] These tasks
transform repair problems into test-writing assignments.

**Adapter:** ask the selected agent for tests without giving it the fix. The DEC-13 admitted execution
actor runs them against buggy and repaired revisions in controlled environments and returns bound
receipts. A valid reproduction fails for the
intended behavior before the fix and passes afterward. Setup failure, unconditional failure, an
import crash unrelated to the defect and a test that passes on both arms do not qualify.

**First proof:** five cases, with intentionally useless test controls. Measure useful reproduction,
not the number of assertions or whether the agent says it reproduced the issue. Review relevance to
the reported defect and retain any accepted alternative test strategy.

## Terminal Bench

**Role:** selected coding/debugging/operator-tool tasks after a runner decision. [sourced] Harbor
supports terminal-agent benchmarks and custom agents. Its ability to load a skill does not establish
our complete plugin's behavior.

**Adapter:** choose tasks fitting the software-engineer lane, supported languages and DEC-13 execution
profile. Reuse upstream verification through its admitted actor, protect hidden material and capture
artifacts. Declare exclusions for tasks requiring production operations, unavailable interactive
execution or unsupported authoring languages before execution. An omitted capability stays explicit.

**First proof:** five tasks with one known success and one known failure control each. Choose one
executor, Inspect-based or Harbor, after comparing task support, parity, evidence and maintenance.
The project does not adopt both orchestration layers by default.

## promptfoo

**Role:** candidate comparison presentation/import and WP-10 controlled adversarial cases; direct
SDK execution is optional. WP-01 delivers a minimal local comparison; final presentation is chosen
under DEC-16 in WP-15. Do not maintain two dashboards without a distinct consumer need.
[sourced] `promptfoo import` reads only promptfoo eval JSON or OpenAI Evals JSONL, so native records
would need a converter, and its telemetry is on by default (`PROMPTFOO_DISABLE_TELEMETRY=1`).
[sourced] The Python provider supports an existing runner wrapper. The Claude Agent SDK provider
supports local plugins and records tool activity. Its default TaskOutput redaction can affect raw
background-helper transcripts; verify the selected configuration against native behavior.

Start by importing saved native outputs. Verify counts, verdicts, provenance, cost and inconclusive
states before adding a model provider. Any direct SDK integration first passes WP-02. Disable
candidate-response cache reuse for fresh trials and make one layer own repetitions. WP-10 freezes
reviewed repo/log/helper/judge attack pairs and completes AC-27. Generated attacks remain candidate
fixtures until reviewed; preserve their injection surface and intended failure. Authoring or importing
those fixtures does not require adopting the SDK execution path.

Official promptfoo authoring skills are optional tooling for authoring lanes. Review their fit before
installation; do not replace semantic fleet rubrics with keyword checks merely because a generic
example uses them. Generation, grading, telemetry, sharing and configured providers are distinct data
paths. Verify opt-outs and destinations for the selected release.

## DeepEval and Pydantic Evals

**Role:** semantic judge candidates in EVAL-015's deferred comparison. [sourced] DeepEval
G-Eval accepts custom evaluation steps and thresholds. Pydantic Evals offers rubric judgments and
configurable input visibility. Neither default demonstrates the existing evidence-quote/calibration
contract.

Compare the current judge, Inspect, Pydantic Evals and DeepEval in two experiments: equivalent
transport/output validation, and native judging methods against human labels. Keep exact steps,
thresholds, model and visible inputs frozen. Stability measurements require fresh independent judge
calls, with cache receipts checked under AC-17. A model's numerical score is not a confidence estimate.
DeepEval errors/skips need explicit INCONCLUSIVE mapping; strict mode is still model judging.

The selected implementation must preserve quote validation, identity, calibration and spend evidence,
and either remove maintenance or improve decision quality at an accepted cost. Keep the incumbent
if no candidate earns adoption. Disable telemetry where supported and validate the actual release's
behavior; opt-out does not prevent deliberate model-provider calls or result uploads.

## UiPath Coder Eval

**Role:** first candidate to pilot for custom agent, skill and tool regression execution, in WP-15
after the first useful comparison (DEC-24). The owner approved this assessment on 2026-10-04; its
[prerequisites](coder-eval.md#postponement-and-prerequisites) come first. It can later serve relevant WP-10 and WP-12/13
cases if accepted; it supplies execution infrastructure rather than the required incident/GCP catalog.

[sourced] Declarative tasks, agent adapters, variant experiments, command/skill criteria and result
artifacts support this proposed role. The [source register](sources.md#coder-eval-evidence) pins the
inspected revision and records the limits. Native fleet compatibility remains [unverified].

**Adapter:** preserve canonical plugin loading, actual permissions/session behavior, independent
fleet assessments and original per-replicate artifacts. Try the external agent-plugin seam or a
thin native bridge before copying prompt bodies or changing framework internals. Keep specialized
incident/authority assessment outside its typed criterion schema initially. All mappings use the
existing [contracts](contracts.md); upstream status, criterion errors and unavailable measurements
must survive import.

**First proof:** the [six-task adoption experiment](coder-eval.md#experiment-sequence), with model-free
controls before live compatibility trials, the incumbent grader/judge fixed, and a maintainer's
ability to reach a correct disposition measured. Complete AC-36/37 and record DEC-16. Adoption must
name what it removes or uniquely enables; retain a narrower artifact-only role or reject it if the
evidence or maintenance case fails. Neither rejection nor a missing capability reduces the approved
benchmark/GCP scope. The independent coding verifier and DEC-13 admission remain in force.

## Inspect AI and Inspect SWE

**Role:** existing candidate infrastructure for scheduling, logs, sandboxed coding and scoring.
[verified] The current pilot is artifact-only and omits native checks; see [baseline](sources.md).

Extend only where a named behavior can be tested. Record a replacement inventory before moving
scheduling or lifecycle code. Remove the replaced implementation after parity and accepted migration;
do not leave permanent duplicate paths without distinct consumers. Keep a rollback to the native
runner and its original artifacts.
Compare the smallest native/Inspect extension with the Coder Eval pilot where responsibilities
overlap. Existing dependency pins do not require choosing Inspect, and a successful Coder Eval
custom-task pilot does not select a coding environment or demonstrate all benchmark support.

## GCP sources and adapters

The dedicated [GCP track](gcp.md#reusable-foundations) uses selected gcpdiag diagnostic references,
Cloud Run samples and OpenTelemetry sidecar examples as proposed foundations. They are not ready
fleet benchmarks or automatic correctness oracles. WP-12 freezes cases; WP-13 uses the same native
adapter and reporting; WP-14 admits the named cloud profile and independent checks. A gcpdiag skip or
API error is a diagnostic limitation, and its Cloud Run deployment tree does not cover every
application-code failure. Preserve tool-specific scope and collect only reviewed sanitized outputs.

## Hypothesis and additional tools

Property-based testing is an optional method for checking parser, mapping and aggregation invariants
without model calls. Add it when concrete input variability warrants it. AgentEvals and garak remain
research options, not required dependencies. They need a named coverage or maintenance benefit before
joining this plan's implementation scope.
