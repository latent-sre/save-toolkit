# ADR: Retire the agent-engineer lane; agent-authoring owns its work

- Date: 2026-11-02
- Status: accepted for implementation by the repository owner's instruction on 2026-11-02; the
  implementing candidate still requires the normal human acceptance decision
- Decision owners: repository owner

## Context

`agent-engineer` was a plugin agent for the fleet's own prompts, agents, skills, evals, roster and
agent workflow graph. `agent-authoring` rule 3 admits a roster role only for "a distinct tool posture,
durable domain lane, or routing split the current agents cannot own".

- [verified] Its method was the skill's: its steps were to load `agent-authoring` and apply the
  artifact method as the skill defines it. The skill already held the failure-layer rule (rule 2),
  the roster justification and ADR rule (rule 3), the reviewer and software-engineer handoffs, and the
  exact-candidate promotion rule. Only the gate/guard-rewording guardrail and the return contract were
  unique to the agent.
- [verified] Its tools (local reads, unguarded Bash, Edit, Write, worktrees, Skill, Agent) matched a
  maintainer session without web tools, so it held no distinct tool posture.
- [verified] No agent granted `Agent(...)` dispatch to it; it was reachable only by main-session
  delegation or direct selection. Its declared primary surface was this fleet, which maintainers change
  from sessions in this repository, where `AGENTS.md` and `CLAUDE.md` already load.
- [verified] Repository records show it dispatched only as an evaluation subject
  ([principal-engineer evaluation](../reviews/2026-10-05-principal-engineer-evals.md)) and once not
  dispatched where a case expected it
  ([operational-docs consolidation](../reviews/2026-10-24-operational-docs-consolidation.md)).
- [sourced: delegated transcript scans, 2026-11-02] The 21 sessions with the most commits here were
  scanned for dispatches in both the tool-call and task-start channels, with the detector first proven
  on a known dispatch and on mutated copies. The plugin's agents were available in three of those
  sessions; all three were read from start to finish and none dispatched this agent. Its only
  dispatches in any scanned transcript were evaluation trials. The plugin's agents were absent from
  every scanned portion of the other eighteen; one of those could not be read and two were not scanned.
- [sourced] The [2026-10-23 audit](../reviews/2026-10-23-agent-skill-audit/agents/agent-engineer.md)
  found no defect against the agent's own contract; it did not assess whether the lane was needed.

## Decision

We will remove `agents/agent-engineer.md` and its generated adapters. `agent-authoring` handles
prompt, agent, skill, grader, roster and fleet workflow-graph work in the invoking session, and its
handoffs carry the agent's gate/guard-rewording guardrail. Routing that named the lane
(`principal-engineer`, `operational-docs` and its references, `agent-authoring`) names the skill.

The validator's tool and delegation pins, the credential-tripwire inventory, the `README.md` roster and
their tests drop the lane. Its direct and build evaluation cases and their oracle test are retired; the
three discovery cases that named it as the alternative owner now expect `agent-authoring`. Live
planning documents that used it as an owner label name a maintainer session. Dated run plans, accepted
ADRs and review records keep their historical references; relative links to the removed files are
pinned to the revisions those records describe.

## Consequences

- One routing target for fleet-authoring requests instead of an agent and a skill, one fewer agent
  description in every session's context, and less roster maintenance.
- No isolated-context lane for long prompt or evaluation loops; a general-purpose subagent with the
  skill loaded substitutes. No Copilot picker entry or structured return contract for this work.
- WP-10's first-step lane set loses `agent-direct-agent-engineer-heldout-contamination`. Its
  [2026-10-10 acceptance](../reviews/2026-10-10-wp10-case-acceptance.md) and results remain; WP-10's
  remaining work does not reference it.
- The three retargeted discovery cases have not run against their new expectation; that routing is
  unmeasured.
- Reopen a lane through a new ADR if fleet-authoring requests route to `principal-engineer` or
  `reviewer` instead of the skill, or if isolated long-running authoring loops become a recurring need.

<!-- ADRs are append-only once accepted. Only the decision owner may amend an accepted ADR, adding a
     dated "Amended:" line that names the change. Anyone else writes a new ADR and marks this one
     "superseded by <YYYY-MM-DD>-<slug>". -->
