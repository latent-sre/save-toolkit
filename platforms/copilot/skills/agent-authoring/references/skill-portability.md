# Skill portability — which frontmatter survives off Claude Code

[doc-checked 2026-08-05] A skill has **two** audiences, and they accept different frontmatter. The
portable Agent Skills specification that other hosts implement accepts six fields. Claude Code
accepts those plus a larger Claude-only set. A field from the Claude-only set is not a small
compatibility wrinkle: Anthropic's own packaging script **rejects** a skill that carries one when
publishing to the portable spec, and a host that merely ignores it silently drops whatever it
configured.

This matters here because this fleet ships a Claude plugin *and* generates Copilot/VS Code and Codex
adapters. The generator is what absorbs the difference; this file is the map of what it has to
absorb. `claude-code-frontmatter.md` remains the source of truth for what each field *does* — this
file only records where each one is honored.

## Contents

- The portable six
- Claude-only fields
- What this means for the generated adapters
- Checking a skill before publishing to the portable spec

## The portable six

Accepted by the Agent Skills spec and by Claude Code:

| Field | Note |
|---|---|
| `name` | Lowercase letters, numbers, hyphens; ≤64 chars; no reserved words |
| `description` | The trigger. Non-empty; ≤1,024 chars in the spec |
| `license` | Accepted, not acted on by Claude Code |
| `compatibility` | Environment requirements; ≤500 chars |
| `metadata` | Free-form object for your own tooling; Claude Code ignores it |
| `allowed-tools` | Grants (pre-approves) tools while the skill is active |

## Claude-only fields

Honored by Claude Code, rejected or ignored elsewhere. Every one of these the fleet uses is listed
with why it is safe for us:

| Field | Fleet use | Off-Claude behavior |
|---|---|---|
| `argument-hint` | Most skills | Not in the spec; dropped |
| `disable-model-invocation` | `pcf-deploy`, `service-onboarding` | Dropped — so the side-effect gate it expresses does **not** travel; the generated adapters carry that intent in host-native form instead |
| `user-invocable` | not used | Dropped |
| `disallowed-tools` | not used | Dropped — note this is the *restricting* field, so a skill relying on it is unrestricted off Claude |
| `context`, `agent`, `background` | not used | Dropped; forked-subagent behavior is Claude-only |
| `paths`, `shell`, `model`, `effort`, `hooks`, `when_to_use`, `arguments` | not used | Dropped |

The pattern worth internalizing: **the portable set can only grant, never restrict.** `allowed-tools`
travels; `disallowed-tools` does not. Any authority a skill expresses through a Claude-only field is
authority that vanishes when the folder is published to the portable spec, and it vanishes
*silently*.

## What this means for the generated adapters

The generator does not attempt field-level equivalence, because there is none. It preserves intent in
each host's own vocabulary and states the difference in the adapter itself:

- A skill marked `disable-model-invocation` keeps that frontmatter for Copilot, while the Codex
  projection expresses the same policy through its per-skill agent-policy file.
- Host authority differences (Copilot's omitted `execute`, Codex's `sandbox_mode` and its lack of a
  per-agent tool allowlist) are stated in every generated adapter rather than papered over.

So a fleet control is only as strong as the host it is proven on. Re-read the enforcement notes in
`AGENTS.md` before assuming a Claude-side restriction reached another host.

## Checking a skill before publishing to the portable spec

If a skill is ever published outside this plugin, strip it to the portable six and confirm the skill
body still carries the behavior any dropped field used to enforce. A skill whose safety depended on
`disable-model-invocation` or `disallowed-tools` must state that boundary in its own prose, because
off Claude there is nothing else holding it.
