# Product requirements

This project supplies decision-quality evidence about the fleet. Its primary users are the human
SRE accepting behavior, maintainers changing agents and skills, and reviewers checking the evidence.
An evaluation should explain what improved, what regressed, what could not be measured and which
conclusions transfer to the team's work.

## Outcomes

1. Compare an incumbent and candidate under the same declared conditions without losing failures.
2. Test the actual fleet: plugin loading, named agents, skills, tools, hooks and continuation.
3. Measure incident progress as well as final diagnosis, including feasible advice and recovery.
4. Check code and generated tests using independent execution evidence.
5. Reuse public benchmarks while preserving their identity and the limits of adapted cases.
6. Reduce bespoke evaluation infrastructure only when replacement preserves necessary evidence.

## Scope and delivery position

The initial host target is the Claude plugin runtime used by the native evaluator. Copilot adapter
files do not establish Copilot runtime acceptance. A future host requires its own tools, hooks,
session and authentication compatibility assessment; do not combine host results into one baseline.

The incident track includes ITBench-Lite, scripted human conversations, SREGym diagnosis and guided
mitigation/recovery exercises. The coding track includes SWE-bench Verified repair, SWT-Bench
reproduction/test generation, and selected Terminal-Bench tasks. AIOpsLab is a later environment
extension with a declared coverage goal. Dataset versions and task identifiers will be frozen
before a pilot; the counts in [scenarios](scenarios.md) are proposed sizes, not selected manifests.

Supported authoring languages follow the [stack profile](../../skills/stack-profile/references/application-and-data-stack.md):
Python, JavaScript/TypeScript and Go, with shell automation where relevant. Java remains support-only.
Kubernetes benchmark environments are disposable test labs. They do not change the team's supported
production stack or imply that a Kubernetes task measures PCF proficiency.

## Users and ownership

| Role | Responsibility in this project |
|---|---|
| Human owner | Select intended task, accept experiment conditions, disposition results and accept exact candidates |
| agent-engineer | Own scenario semantics, agent/skill experiments and calibrated judging methods |
| software-engineer | Implement adapters, result import, reporting and lab integration code |
| reviewer | Independently assess implementation and whether evidence supports the claimed result |
| Lab operator | Provision/reset the disposable environment and execute any assigned lab changes |
| researcher | Supply sanitized public documentation and upstream evidence when dispatched |

These responsibilities do not add delegation edges. The invoking caller assigns work through the
existing graph; it remains responsible for integrating helper results and continuing the project.
An agent being evaluated does not grade or approve its own candidate. Existing permitted Grafana
operations retain their complete rule; this specification does not widen it.

## Fleet coverage

| Subject | Representative assignment | Evidence of success |
|---|---|---|
| incident-investigation skill | Advise an SRE through changing observations | Useful next check, revised hypothesis, retained board, supported recovery judgment |
| sre-assistant | Answer a bounded diagnostic question | Authorized reads, supported findings, correct return recipient and preserved unknowns |
| software-engineer | Repair a repository defect and verify it | Independent patch tests, scope of changes and ordered verification receipts |
| reviewer | Review a patch with seeded defects and harmless distractors | Reproduced or source-backed findings, appropriate severity and untouched candidate |
| repository-investigator | Explain a bounded source behavior | Accurate file/line evidence and explicit gaps |
| observability-engineer | Build a lab dashboard or rule over seeded telemetry | Stored configuration, evaluated query and visible/resulting behavior assessed separately |
| scribe | Write an incident handover or runbook from supplied evidence | Accurate content, retained uncertainty and no invented actions |
| reliability-engineer | Analyze a recurring failure and propose an improvement | Supported mechanism, proportionate design and a meaningful verification proposal |
| researcher | Answer a public, version-specific question | Relevant primary sources, supported claims and honest retrieval gaps |
| agent-engineer | Improve a measured prompt failure | Improvement on held-out cases with no hidden regressions or automatic promotion |

Each lane gets a focused task suite. A coding benchmark score is not a verdict on the entire roster.
Tool access must reflect the lane being evaluated. A refusal of an out-of-lane benchmark task can
be correct fleet behavior; report task suitability separately from upstream task completion.
External coding tasks use the [execution-admission contract](architecture.md#coding-execution-admission).
Report whether verification was performed by the agent, supplied by an admitted CI actor, or not
assessed. Supplied receipts never establish the agent's own execution of tests.

## Requirements and traceability

Acceptance cases are defined in [measurement](measurement.md). Delivery packages are in
[delivery](delivery.md). Requirement IDs are stable cross-references, not runtime API fields.

| ID | Required outcome | Acceptance | Delivery |
|---|---|---|---|
| REQ-01 | Preserve native results in a report that imports and relocates correctly on Windows and Linux | AC-01, AC-02, AC-23 | WP-01 |
| REQ-02 | Bind results to actual candidate, scenario, runner, host and model identities | AC-03 | WP-00, WP-02 |
| REQ-03 | Establish plugin/agent/tool/hook/session behavior before claiming native parity | AC-04, AC-05 | WP-02 |
| REQ-04 | Run ITBench-Lite diagnosis with evaluator answers inaccessible to the candidate | AC-06 | WP-04 |
| REQ-05 | Evaluate evolving human-assisted investigations using fixed updates and authored branching observations | AC-07, AC-08, AC-26 | WP-05 |
| REQ-06 | Run SREGym incidents with observed setup, fault, reset and cleanup outcomes | AC-09, AC-10 | WP-06 |
| REQ-07 | Separate mitigation advice, lab execution and assessed recovery | AC-11 | WP-07 |
| REQ-08 | Evaluate software-engineer patches with independent benchmark tests through an admitted execution profile | AC-12, AC-25 | WP-00, WP-08 |
| REQ-09 | Evaluate generated bug-reproduction tests against buggy and repaired code through the admitted execution actor | AC-13, AC-25 | WP-09 |
| REQ-10 | Cover selected terminal tasks with actual fleet identity and explicit external-code execution admission | AC-14, AC-25 | WP-09 |
| REQ-11 | Compare judge candidates against human labels with evidence/error parity and independently sampled stability | AC-15, AC-16, AC-17 | WP-03 |
| REQ-12 | Separate fresh trials, replay, rescoring, retries and genuine task failure from instrument failure | AC-02, AC-17, AC-24 | WP-01, WP-02 |
| REQ-13 | Bound spending, protect raw evidence and make unavailable cost explicit | AC-18, AC-19 | WP-00, WP-02 |
| REQ-14 | Add representative tasks for the remaining fleet lanes | AC-20 | WP-10 |
| REQ-15 | Support a later AIOpsLab integration with an explicit new coverage goal | AC-21 | WP-11 |
| REQ-16 | Keep human acceptance, existing authority and the sole roadmap intact | AC-22 | All packages |
| REQ-17 | Assess controlled adversarial instructions on repository, telemetry, helper and judge surfaces while retaining legitimate task progress | AC-27 | WP-10 |

## Nonfunctional requirements

- **Reproducibility:** freeze inputs and identity per run; retain raw observations and original
  framework results. A published case that has changed is a new case revision.
- **Portability:** offline readers and reports must work on Windows and Linux. Linux containers
  are the proposed benchmark execution environment; Windows management does not prove lab parity.
- **Maintainability:** one canonical case definition where practical, one execution owner per
  profile, thin adapters and explicit removal targets before replacing existing code.
- **Privacy:** private native traces stay in local ignored run storage. Any external model receives
  only the content selected for that experiment. Sharing is a separate action.
- **Recoverability:** failed setup, process loss and cleanup failures are visible; partial evidence
  survives. Do not replay an uncertain lab action automatically.
- **Usability:** a reviewer can find the failed case, original evidence and reason without reading
  an entire transcript. Reports explain unfamiliar metrics in operational terms.

## Exclusions from the initial release

There is no automatic agent promotion, production remediation, hosted public leaderboard submission,
continuous training, fleet rewrite, mandatory new agent, or central service requirement. Live model
evaluations retain the repository's manual clean-room policy. Offline adapters and fixtures can run
in ordinary CI. Future scheduling or hosted operation needs a separate design and owner decision.
