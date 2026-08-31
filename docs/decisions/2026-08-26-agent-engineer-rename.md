# ADR: Rename `prompt-engineer` to `agent-engineer`

- Date: 2026-08-26
- Status: Accepted
- Decision owner: Save Toolkit maintainers

## Context

`prompt-engineer` is a recognizable industry role and an accurate name for one seventh of what the
lane owns. Its own description claims prompts, agents, skills, tool and grader descriptions, bounded
Loop Engineering, agent roster and delegation graphs, and portable executable workflow/state-graph
designs. Prompt text is one artifact class among those; the roster tier — splitting and merging
lanes, orchestration shape, handoff contracts, context budgets — and the graph tier are at least as
distinctive, and `agent-authoring`'s `roster.md` is 19KB about exactly that work.

This is the same defect that rejected `coder` in the
[`software-engineer` rename](2026-08-25-software-engineer-rename.md): a name that understates the
lane's ownership makes the picker and the handoff graph less legible than the artifacts themselves.

Two facts constrain how much weight to put on routing. That rename's bounded target-blind comparison
scored `coder` and `software-engineer` at 80/80 each across five fresh trials, establishing no
routing advantage for either name; it was decided on human discoverability. And this lane's tool
posture is `software-engineer`'s exactly, minus two delegation edges — so the usual tool-scope
justification for a distinct agent does not differentiate it. What differentiates it is the loop
(reproduce → diagnose the owning layer → minimal edit → incumbent-versus-candidate → human
promotion), wrapper bisection, and being the disposition policy's named destination for accepted
fleet failures. `agent-engineer` names the artifacts that loop operates on.

## Evidence

`[unverified]` No routing comparison was run for this rename. The prior rename's tie is the only
measured input, and it measured different candidates on a different lane; it supports the general
claim that a name change of this kind does not move automatic routing, not a claim about
`agent-engineer` specifically. This decision rests on human legibility, as its predecessor did.

`[verified]` Tool authority, delegation edges, description text, and body contract are unchanged in
this migration: `Read, Grep, Glob, Bash, Edit, Write, Skill, Agent(researcher)` and
`EXPECTED_DELEGATION["agent-engineer"] == {"researcher"}`, checked by `validate_fleet.py` and
`test_graph_contracts.py`.

## Decision

1. Rename the canonical agent and public component address from `prompt-engineer` /
   `save-toolkit:prompt-engineer` to `agent-engineer` / `save-toolkit:agent-engineer`.
2. Preserve the agent description, tool authority, body contract, and delegation edges. This is an
   identity migration, not a prompt or authority change.
3. Add `prompt-engineer` to the stale-name checker after migrating live agents, skills, commands,
   and scenarios.
4. Update current documentation, tests, probes, scenarios, and generated host adapters in the same
   change.
5. Leave dated decisions, reviews, and frozen evaluation baselines under `prompt-engineer`;
   rewriting recorded evidence would falsify what ran. The live roadmap uses the current name.
6. Do not ship a compatibility alias. Two overlapping names would split routing and graph identity
   across the same authority.

## Alternatives considered

- **Keep `prompt-engineer`:** the incumbent, and defensible. Every candidate is a lateral trade —
  `agent-engineer` understates prompts and evals the way `prompt-engineer` understates agents and
  graphs — and by this lane's own promotion rule a tie retains the incumbent. Rejected because the
  maintainer chose to resolve the same discoverability problem the `sde` rename resolved, and
  because the understated tiers here (roster, graph) are the ones a reader is least likely to guess
  from the name.
- **`agent-architect`:** rejected. It reads the roster and graph tiers well but loses the artifact
  tier, which is the lane's highest-volume work — fixing one description or one output contract.
- **`fleet-engineer`:** rejected. `fleet` is internal vocabulary that means nothing in a picker
  outside this repository.
- **Split the lane into two agents** (an artifact tier and a roster/graph tier, matching a
  `prompt-engineer` plus `multi-agent-architect` split used elsewhere): rejected here. That is
  a roster change, not a rename, and it would need its own justification against the agent-versus-
  skill rule. The body already routes the three altitudes through skills; nothing observed requires
  an ownership boundary between them.

## Consequences

- Explicit invocations, bookmarks, and handoffs using `save-toolkit:prompt-engineer` break and must
  move to `save-toolkit:agent-engineer`.
- Retiring the name here removes one of the three role-name collisions that
  [the Codex retirement ADR](2026-08-23-retire-codex-distribution-target.md) had to write defensive
  cleanup instructions around; `repository-investigator` and `researcher` still collide, and that
  dated ADR keeps its original wording as evidence of what was true when it was written.
- Generated Copilot and VS Code adapter filenames change with the canonical source:
  `.github/agents/prompt-engineer.agent.md` becomes `.github/agents/agent-engineer.agent.md`.
- Tool authority, network posture, production boundaries, and the disposition-policy edge that
  routes accepted fleet failures into this lane are unchanged.
- Historical files can still mention `prompt-engineer`; current LLM-facing surfaces under `agents/`,
  `skills/`, `commands/`, and `evals/scenarios/` fail validation if it returns.

## Rollback

Revert the canonical agent, live references, validator maps, stale-name entry, scenarios, tests, and
generated adapters together, then regenerate once. Never restore the old canonical name while
leaving new generated adapter paths or mixed delegation targets.
