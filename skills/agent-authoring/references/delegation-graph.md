# The delegation and handoff graphs

The fleet has two directed graphs over the eight canonical agents. A model-call edge `A → B` is an
`Agent(B)` grant in `A`'s canonical `tools:` frontmatter and becomes Copilot `agents:` metadata. A
VS Code handoff edge is a separate human-selected ownership transition emitted only by the Copilot
generator. This file owns their distinction and change procedures.

## Contents

- One enforced source, one validated render
- Reading the shape
- The honest limit
- Changing an edge

## One enforced source, one validated render

| Copy | Where | Status |
|---|---|---|
| Source | `Agent(target, …)` grants in `agents/<name>.md` | Enforced by Claude on the main thread; carried into host adapters; `validate_fleet.py` fails Gate A on a missing target or a set that differs from the pinned expectation |
| Expectation | `EXPECTED_DELEGATION` in `validate_fleet.py` | Pinned in code; an edge change without it fails the source check |
| Render | The "Delegates to" column of the roster table in `AGENTS.md` | Validated by `validate_roster_graph` against the expectation; the roster table *is* the edge list — never re-tabulate edges elsewhere |
| VS Code model-call projection | `tools: [agent]` plus `agents:` in `.github/agents/*.agent.md` | Generated from the canonical grant and byte-checked |
| VS Code handoff source | `COPILOT_HANDOFFS_BY_SOURCE` in the platform-adapter generator | Separate from model calls; `test_copilot_agents_offer_the_current_roster_handoff_graph` pins every source and target, including agents with no model-delegation tool |
| VS Code handoff projection | `handoffs:` in `.github/agents/*.agent.md` | Generated and byte-checked; every edge is local, human-selected, and `send: true` so one click starts the receiver; `researcher` never appears because handoffs retain conversation context |

## Reading the shape

Read the current edges from the validated roster table, not from memory.

| Role | Agents | Why |
|---|---|---|
| Orchestrators | `software-engineer` (build lane); `sre-assistant` dispatches only a sanitized public question to `researcher` | The lanes that dispatch work |
| Universal sink | `researcher` | Every orchestrating lane reaches it for sanitized public fact-finding |
| Terminal for model calls | `reviewer`, `repository-investigator`, `scribe` | No `Agent` grant, so the model cannot dispatch onward; a user may still select a declared VS Code handoff, which starts a new owner without giving the source delegation authority |

## The honest limit

Canonical Claude `Agent(target)` enforces an edge only for a main-thread agent; at subagent depth
the list is silently ignored (probed; see
[`claude-code-frontmatter.md`](./claude-code-frontmatter.md)). VS Code has a separate `agents:`
field. The generated field scopes discovery on the currently observed host; deterministic
invocation and nested-edge enforcement are build-specific and stay unverified until `HOST-002`
observes a real allowed and forbidden call on the exact build.

Neither projection is a sandbox. Host/network isolation, tool absence, and the guard (the fleet
guide's Enforcement section) remain load-bearing. VS Code `handoffs:` are user-selected context
transitions, not subagent calls or approval. They are intentionally independent of `Agent(...)`
grants, use `send: true` to enact the selected transition without a second ceremonial confirmation,
require write-capable receivers to re-check approval and target binding, and keep external research
behind the sanitized call boundary.

## Changing an edge

A model-call edge change touches all four:

1. Edit the `Agent(...)` grant in `agents/<name>.md`.
2. Update `EXPECTED_DELEGATION` in `validate_fleet.py`.
3. Update the "Delegates to" cell in the `AGENTS.md` roster table.
4. `python scripts/generate_platform_adapters.py --write`, then `python scripts/gate_a.py` — the
   source check, the render check, and the byte-for-byte adapter gate must all pass.

A VS Code handoff edge change does **not** alter `Agent(...)` grants. In one commit:

1. Edit `COPILOT_HANDOFFS_BY_SOURCE` in the platform-adapter generator.
2. Update the exact source-target expectation and authority assertions in
   the platform-adapter tests.
3. Regenerate with `python scripts/generate_platform_adapters.py --write`.
4. Run the focused platform-adapter tests and Gate A. Keep `researcher` call-only, every handoff
   `send: true`, and every write-capable target responsible for re-checking approval.
