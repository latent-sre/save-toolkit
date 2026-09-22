# ADR: Add a reliability engineering lane and two focused methods

- **Date:** 2026-09-21
- **Status:** proposed; implementation authorized by the owner, exact-candidate acceptance pending
- **Decision owner:** Save Toolkit maintainers

## Context

The owner requested and approved a reliability engineer with systems-design depth for resilience
analysis, engineering improvements and toil reduction. Existing roles supply repository facts,
operational investigations, implementation, observability, documentation and independent change
review. The new responsibility is synthesizing that evidence into a reliability decision and its
verification requirements; it does not replace those owners or incident command.

## Decision

Add `reliability-engineer`, `resilience-analysis` and `toil-reduction`. Keep design judgment and
failure-path analysis in the first method and recurring-work economics in the second. Reuse
`service-lifecycle`, `root-cause`, `eng-ladder`, `database-reliability` and relevant observability
skills rather than copying their procedures.

The agent reads local evidence, prepares requested design/assessment documents, and can dispatch
bounded questions to `repository-investigator`, `sre-assistant` and `researcher`. It has no shell,
browser, direct external tools, implementation delegation or production execution. Document-only
writes are cooperative unless the host enforces the path boundary. Existing callers gain no new
agent grants; the main session or human can select this role. No new Copilot ownership handoff is
added. The guard's fleet-name inventory includes the new role for the existing credential-output
tripwire; the SRE-only command allowlist is unchanged.

The agent distinguishes observed defects, supported design risks, verification gaps and improvement
opportunities. It checks existing controls and may return no material finding within scope. The
return keeps uncertainty, target identity and evidence provenance, with a named implementation owner
and discriminating verification. It never converts a design or a test result into release approval.

## Evidence and acceptance

Authority mutation tests reject added execution, egress and implementation delegation. Generated
adapters retain the same tool/delegation posture. Offline evaluation calibration covers controls
that disprove a lead, stale evidence, missing recovery proof, negative automation economics, a
seeded source investigation, partial-helper continuation, and a document-write boundary. The
source case has an identical incumbent `sre-assistant` arm. A native helper conversation and
overlapping routing cases are specified; their traces have not been run or reviewed. The method
includes a complete fictional proposal with options, ownership, a falsifiable test and recovery.
These establish fixture and grader behavior, not model competence.

Native evaluation remains pending under `RELIABILITY-001` in the live roadmap. The owner must select
the candidate, model/host and bounded trial budget. Assess source retrieval, claim correctness,
false positives, useful next action, caller continuation and document-only behavior separately,
alongside free-form quality. Compare the incumbent and new lane on the same fixture without calling
a structurally green or single successful trial a general capability result.
The native conversation case pins its expected model to Claude Sonnet 5; all comparisons must use
the same resolved model cohort. No new evaluator framework, integration, calculator or background
process is introduced.

## Source map

Official guidance checked 2026-09-21. Recheck on authoring-method changes or relevant host changes;
host and model behavior still require their own evidence.

| Source | Adopted principle |
|---|---|
| [OpenAI skill authoring](https://learn.chatgpt.com/docs/build-skills) | Focused workflows, explicit inputs/outputs, descriptions and conditional references |
| [OpenAI evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | Task-specific outcomes, tool arguments and handoffs assessed separately |
| [Anthropic skill authoring](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | Progressive disclosure; flexible analysis and precise fragile boundaries |
| [Anthropic agent evaluations](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | Trace and outcome review; automated checks do not replace expert assessment |
| [Anthropic public skill creator](https://github.com/anthropics/skills/blob/34040c9c568585f6929bedeaad110ad08f079624/skills/skill-creator/SKILL.md) | Representative tasks and baseline comparisons; existing fleet budgets/harness remain authoritative |

SRE primary sources and inspected community examples are linked from the new skills. Community
authority, generic thresholds, rollback assumptions and arithmetic are not adopted. These are original
fleet instructions, not an installed third-party skill bundle.

## Alternatives and rollback

Expanding `sre-assistant` would join bounded operational observation with sustained design and
document writing. Adding a general architect would broaden scope beyond the requested reliability
work. A separate domain lane fits the approved outcome without cloning a seniority tier.

If evaluation does not justify the lane, retain failed evidence while the decision is open and
remove its canonical profile, methods, routing, authority expectations and fixture coverage as one
reviewed change, then regenerate adapters. Do not leave a selectable generated profile behind.
