# ADR: Rename `sde` to `software-engineer`

- Date: 2026-08-25
- Status: Accepted
- Decision owner: `latent-sre`

## Context

`sde` is a familiar internal abbreviation but an opaque public component name. The lane owns more
than code generation: it builds and refactors backend services, APIs, CLIs, automation, dashboards,
and web UIs; writes tests; resolves material engineering forks; and owns the bounded review/fix
loop. A name should make that ownership legible in the picker and in handoff graphs.

A bounded, target-blind Terra comparison exercised `coder` and `software-engineer` against the same
eight-agent roster and sixteen routing cases, with five fresh trials per candidate. Both names made
all 80 expected selections. The comparison therefore provides no evidence that either name improves
automatic routing. It is decision input, not native-host dispatch or release evidence; the retired
Codex/Terra evaluator remains retired.

## Evidence

[verified] In the maintainer session, `gpt-5.6-terra` ran five full fresh-context trials for each
candidate. The eight-agent roster, sixteen target-blind routing cases, prompts, and scoring
conditions stayed fixed; only the build agent's public name changed.

| Candidate | Trials | Cases per trial | Expected selections | Misses |
|---|---:|---:|---:|---:|
| `coder` | 5 | 16 | 80/80 | 0 |
| `software-engineer` | 5 | 16 | 80/80 | 0 |

The raw session transcripts were not committed, so the aggregate cannot be independently replayed
from repository artifacts. This limitation is why the result supports only a tie: it establishes no
routing advantage, native-host behavior, or release claim for either candidate.

## Decision

1. Rename the canonical agent and public component address from `sde` / `save-toolkit:sde` to
   `software-engineer` / `save-toolkit:software-engineer`.
2. Preserve the agent description, tool authority, body contract, and delegation edges. This is an
   identity migration, not a prompt or authority expansion.
3. Add `sde` to the stale-name checker after migrating live agents, skills, commands, and scenarios.
4. Update current documentation, tests, probes, and generated host adapters in the same change.
5. Leave dated decisions, reviews, and frozen evaluation baselines under `sde`; rewriting recorded
   evidence would falsify what ran. The live roadmap uses the current name.
6. Do not ship a compatibility alias. Two overlapping build agents would split routing and graph
   identity while carrying the same broad write authority.

## Alternatives considered

- **`coder`:** rejected. It was equally routable in the bounded comparison and shorter to type, but
  it understates testing, design, operational tooling, and end-to-end engineering ownership. It is
  also ordinary vocabulary, which makes a future retired-name guard noisy.
- **Keep `sde`:** rejected. It avoids migration cost but preserves the human-discoverability problem
  the maintainer explicitly chose to resolve.

## Consequences

- Explicit invocations, bookmarks, and handoffs using `save-toolkit:sde` break and must move to
  `save-toolkit:software-engineer`.
- The longer name matches the existing `prompt-engineer` and `observability-engineer` convention and
  describes the lane without opening its body.
- Generated Copilot and VS Code adapter filenames change with the canonical source.
- Tool authority, network posture, production boundaries, and the
  `software-engineer → reviewer → software-engineer` loop are unchanged.
- Historical files can still mention `sde`; current LLM-facing surfaces fail validation if it
  returns.

## Rollback

Revert the canonical agent, live references, validator maps, stale-name entry, scenarios, tests, and
generated adapters together, then regenerate once. Never restore the old canonical name while
leaving new generated adapter paths or mixed delegation targets.
