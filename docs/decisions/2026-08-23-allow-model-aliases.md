# Allow a per-agent model generation alias; keep the ban on full model IDs

- **Date:** 2026-08-23
- **Status:** Accepted
- **Decision owner:** `latent-sre`
- **Supersedes:** the "No `model:` pins" Hard rules bullet in AGENTS.md and its `docs/rules.md`
  index row, replacing a blanket ban with a narrowed one.

## Decision

An agent may set `model:` to a **generation alias** — `haiku`, `sonnet`, `opus`, `fable`, or
`inherit`. A **full model ID** (for example `claude-opus-4-1-20250805`) fails validation.

`scripts/validate_fleet.py` enforces it: `model` joins `KNOWN_AGENT_FIELDS`, and a new check
rejects any value outside `MODEL_ALIASES`. Default behaviour is unchanged — an agent with no
`model:` inherits the session model, and no agent in the fleet pins one today.

## Why

The old rule banned every pin, for one stated reason: *"a pin, even a valid one, goes stale
silently."* That reason is true of full IDs and false of aliases. An alias names a tier and tracks
whatever model currently occupies it; a dated ID keeps pointing at one model long after the fleet
has moved on, and nothing errors. Banning both to stop one of them cost a capability the roster
reference had already identified as lost:

> *"That removes per-agent synchronization and lineup maintenance, but it also prevents cheaply
> tiering routine agents separately from judgment-heavy agents."*
> — `skills/agent-authoring/references/roster.md`, before this change

The same reference named the exit condition — "changing that policy would require an explicit fleet
decision and validator change" — which is exactly this ADR plus the `validate_fleet.py` change.

The trigger was concrete: fan-out work over this repository ran on Sonnet by explicit per-subagent
override, while the fleet's own eight agents had no equivalent. Tiering a high-volume mechanical
lane down while leaving review and root-cause lanes on the session model is ordinary cost
management, and nothing about it risks the staleness the original rule targeted.

## Consequences

- `validate_fleet.py` gains `MODEL_ALIASES` and one check. Red-to-green evidence, taken against a
  real agent file rather than a fixture: `agents/sre.md` pinned to
  `model: claude-opus-4-1-20250805` fails with *"model must be one of fable, haiku, inherit, opus,
  sonnet — a full model ID goes stale silently"*, exit 1; the same file pinned to `model: sonnet`
  returns *"Fleet validation: PASS (8 agents, plugin and adapters consistent)"*, exit 0.
- Two focused tests in `scripts/test_validate_fleet.py` cover both directions.
- **A pin is Claude-only.** Generated Copilot/VS Code adapters carry no model concept, so the
  projection omits it. This is the ordinary host-authority asymmetry the fleet already states
  everywhere: a control or setting proven on one host is not proven on another.
- **Guidance, not just permission** (`roster.md`): tier *down* lanes whose work is high-volume and
  mechanical; leave judgment-heavy lanes — review, root cause, authority decisions — inheriting. A
  pin is a claim about a lane's difficulty, so state why in the same change and remove it when the
  reason stops holding.
- No behaviour changes for any existing agent: none pins a model, and `inherit` remains the default.

## Alternatives considered

- **Keep the blanket ban.** Rejected: it prevents a legitimate, low-risk optimization in order to
  stop a failure mode that only the full-ID form exhibits.
- **Allow full IDs too.** Rejected: that is precisely the staleness the original rule was written
  against, and an eval campaign needing an exact model can pin it in the eval harness — where the
  pin is scoped to a run and reviewed with its results — rather than in a fleet definition that
  outlives it.
- **Allow `effort:` in the same change.** Deliberately deferred. `effort` (`low`…`max`) is a second
  tiering lever with the same stable-enum property and no staleness risk, but it was not part of
  the decision requested; it is a one-line follow-on to `KNOWN_AGENT_FIELDS` when wanted.

## Reopen trigger

Aliases stop tracking tiers (an alias is retired or its meaning changes), or a lane needs an exact
model in a fleet definition rather than in a scoped eval run — either would need a fresh decision,
because both reintroduce the staleness this rule preserves protection against.
