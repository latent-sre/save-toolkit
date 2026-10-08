# Fleet evaluation project specification

**Status:** Accepted specification, revision 0.6; the owner accepted it on 2026-10-06 as the WP-00
scope freeze. Revision 0.6 records the WP-00 review and the owner's DEC-21 to DEC-24 decisions:
result rules from the accepted threat-model ADR, a v1 result record, the native host and account,
and Coder Eval postponed to WP-15. Revision 0.5 recorded DEC-01, DEC-02, DEC-04, DEC-10, DEC-11 and
DEC-17 to DEC-20. The owner requested the complete plan and specifications before implementation.
ITBench-Lite and SREGym are included; Microsoft AIOpsLab is a later phase. The coding track covers
repository repair, test generation and selected terminal tasks. GCP has a dedicated managed-service,
migration and GKE track. The owner approved adding UiPath Coder Eval as the first candidate to pilot
for custom agent/skill/tool regression execution; adoption depends on the specified experiment. No
integration or benchmark result is established by this planning package.

The project helps an SRE or maintainer decide whether a specific Save Toolkit candidate improves
useful work. It measures incident diagnosis, investigation with a human, live lab investigation,
code repair, test writing and the behavior of the wider fleet. Reports connect conclusions to
the exact agent, scenario, environment and evidence measured.

The first implementation slice is EVAL-011's runner sequence, which writes the v1 result record,
and a minimal local comparison over it without model calls. A first bounded incumbent/candidate
comparison follows once native readiness and that report pass. The six-task Coder Eval experiment,
which assesses runner compatibility and maintainer usefulness with the accepted graders and judge
fixed, waits until after that comparison. Broader milestones retain ITBench-Lite, SWE-bench repairs, required
SREGym exercises and the 24-case GCP evidence pilot, followed by the full 64-case GCP catalog and
bounded live cloud exercises. AIOpsLab extends the environment choices later. Cloud Run and GKE
results remain separate.

## Read the specification

| Document | Purpose |
|---|---|
| [Product requirements](product.md) | Outcomes, users, scope, all fleet lanes and traceable requirements |
| [Architecture](architecture.md) | Execution, adapters, evidence flow, host parity and trust boundaries |
| [Contracts](contracts.md) | Cases, runs, assessments, errors, provenance, cache and comparison rules |
| [Integrations](integrations.md) | Each benchmark and framework, its adapter work and adoption criteria |
| [Coder Eval adoption experiment](coder-eval.md) | Postponement and prerequisites, product boundaries, six-task pilot, evidence mapping and retain/replace/reject criteria |
| [WP-02 run plan](run-plan-wp02-native-readiness.md) | The first live run: cases, conditions, budget and stop rules for native readiness |
| [Scenario specifications](scenarios.md) | Incident pairs, coding tasks, wider-fleet cases and examples |
| [GCP evaluation track](gcp.md) | 32 paired scenario families, migration and managed services, GKE, reusable foundations and cloud lab profiles |
| [Measurement and verification](measurement.md) | Judge calibration, experiment design and acceptance tests |
| [Delivery and decisions](delivery.md) | Ordered work packages, owners, dependencies, decisions and risks |
| [Operations](operations.md) | Proposed operator workflow, lab lifecycle, costs, data and recovery |
| [Sources and baseline](sources.md) | Checked repository evidence, upstream provenance and limits |

## What is decided and what remains proposed

| Scope choice | Disposition |
|---|---|
| ITBench-Lite evidence-based incident diagnosis | Included by owner direction |
| SREGym live incident exercises | Included by owner direction |
| Microsoft AIOpsLab | Included in the later expansion phase |
| GCP managed services, migration and GKE | Included by owner direction; WP-12/13/14 deliver authored cases, native evaluation and live cloud exercises |
| Fixed and authored branching incident conversations | Both included in WP-05, with separate acceptance evidence |
| Coding evaluations for the existing software-engineer | Included; SWE-bench Verified is the proposed first dataset |
| SWT-Bench and selected Terminal-Bench tasks | Planned coding coverage, delivered after the first repair integration |
| UiPath Coder Eval | First custom behavioral-runner candidate, postponed to WP-15 after the first useful comparison (DEC-24); owner approved assessment, not permanent adoption |
| promptfoo | Candidate long-term presentation, chosen under DEC-16 in WP-15; controlled repo/log/helper/judge adversarial cases in WP-10; execution remains optional |
| DeepEval | Required judge candidate in the proposed comparison; permanent adoption is undecided |
| Inspect AI, Inspect SWE and Pydantic Evals | Existing pilot or comparison candidates; select responsibilities from evidence |
| Harbor | Candidate coding environment/executor; compare with Inspect and assess Coder Eval's existing bridge where relevant before building overlapping infrastructure |
| Deployment, model spend, credentials and lab provisioning | Selected for each implementation/run phase; none performed by this package |

External coding execution requires the DEC-13 admission decision; this specification preserves the
current agent policy and distinguishes supplied CI receipts from agent-executed verification. Result
contracts distinguish genuine task failure from instrument failure and require fresh independent
judge calls for stability measurements. WP-01 includes Windows/Linux portability acceptance.
GCP evaluation scope does not settle the production landing runtime or add agent permissions.

Requirements and acceptance criteria describe proposed behavior and remain **[unverified]** until
implemented and measured. **[verified]** claims refer only to current local observations;
**[sourced]** claims refer to the linked documentation or source. A documented capability is not
proof that a specific package release works with this fleet.

Execution status lives only in [EVAL-012 in the fleet roadmap](../fleet-roadmap.md#eval-012--plan-incident-and-coding-evaluations-for-the-fleet).
The work packages here describe delivery, not a second live backlog. EVAL-015 holds the deferred
judge-replacement comparison and EVAL-011 of the native measurement contract. An accepted ADR changes only
through a successor or its decision owner's dated amendment; implementation that changes its
contract needs one of them.

## Completion boundaries

This specification is complete when its requirements, cases, integration responsibilities,
acceptance criteria, delivery dependencies and open decisions agree. A working prototype is a
later result. Benchmark completion, a successful test suite and human acceptance are distinct.

DEC-01 places the implementation in this repository; a separate repository follows only if the
work expands and shows independent value. These plans live beside the fleet they will evaluate. The [SRE Workbench](../sre-workbench/README.md) is a separate operations product
and a possible future consumer or subject of evaluations; this project does not depend on its
implementation or select its technology stack.

Coder Eval would be a development/evaluation dependency; Workbench operations and the installed
fleet must continue to function without it.
