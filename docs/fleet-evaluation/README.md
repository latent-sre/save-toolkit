# Fleet evaluation project specification

**Status:** Proposed specification, revision 0.2, 2026-10-03. The owner requested the complete
plan and specifications before implementation. ITBench-Lite and SREGym are included; Microsoft
AIOpsLab is a later phase. The coding track covers repository repair, test generation and selected
terminal tasks. No integration or benchmark result is established by this planning package.

The project helps an SRE or maintainer decide whether a specific Save Toolkit candidate improves
useful work. It measures incident diagnosis, investigation with a human, live lab investigation,
code repair, test writing and the behavior of the wider fleet. Reports connect conclusions to
the exact agent, scenario, environment and evidence measured.

The first implementation slice will compare saved native results without model calls. The first
behavioral milestones will exercise selected ITBench-Lite cases and SWE-bench repairs through the
actual fleet. SREGym is a required delivery milestone with its own lab readiness work. AIOpsLab
extends the environment choices later; it does not block those milestones.

## Read the specification

| Document | Purpose |
|---|---|
| [Product requirements](product.md) | Outcomes, users, scope, all fleet lanes and traceable requirements |
| [Architecture](architecture.md) | Execution, adapters, evidence flow, host parity and trust boundaries |
| [Contracts](contracts.md) | Cases, runs, assessments, errors, provenance, cache and comparison rules |
| [Integrations](integrations.md) | Each benchmark and framework, its adapter work and adoption criteria |
| [Scenario specifications](scenarios.md) | Incident pairs, coding tasks, wider-fleet cases and examples |
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
| Fixed and authored branching incident conversations | Both included in WP-05, with separate acceptance evidence |
| Coding evaluations for the existing software-engineer | Included; SWE-bench Verified is the proposed first dataset |
| SWT-Bench and selected Terminal-Bench tasks | Planned coding coverage, delivered after the first repair integration |
| promptfoo | Comparison integration in WP-01; controlled repo/log/helper/judge adversarial cases in WP-10 |
| DeepEval | Required judge candidate in the proposed comparison; permanent adoption is undecided |
| Inspect AI, Inspect SWE and Pydantic Evals | Existing pilot or comparison candidates; select responsibilities from evidence |
| Harbor | Candidate runner for coding tasks; compare with Inspect before adopting overlapping infrastructure |
| Deployment, model spend, credentials and lab provisioning | Selected for each implementation/run phase; none performed by this package |

External coding execution requires the DEC-13 admission decision; this specification preserves the
current agent policy and distinguishes supplied CI receipts from agent-executed verification. Result
contracts distinguish genuine task failure from instrument failure and require fresh independent
judge calls for stability measurements. WP-01 includes Windows/Linux portability acceptance.

Requirements and acceptance criteria describe proposed behavior and remain **[unverified]** until
implemented and measured. **[verified]** claims refer only to current local observations;
**[sourced]** claims refer to the linked documentation or source. A documented capability is not
proof that a specific package release works with this fleet.

Execution status lives only in [EVAL-012 in the fleet roadmap](../fleet-roadmap.md#eval-012--plan-incident-and-coding-evaluations-for-the-fleet).
The work packages here describe delivery, not a second live backlog. EVAL-010 retains ownership of
judge adoption and EVAL-011 of the native measurement contract. Accepted ADRs stay immutable;
implementation that changes their contracts needs a successor decision.

## Completion boundaries

This specification is complete when its requirements, cases, integration responsibilities,
acceptance criteria, delivery dependencies and open decisions agree. A working prototype is a
later result. Benchmark completion, a successful test suite and human acceptance are distinct.

The implementation repository remains a named decision. These plans live beside the fleet they
will evaluate. The [SRE Workbench](../sre-workbench/README.md) is a separate operations product
and a possible future consumer or subject of evaluations; this project does not depend on its
implementation or select its technology stack.
