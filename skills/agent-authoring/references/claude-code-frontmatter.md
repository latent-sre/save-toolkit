# Claude Code frontmatter — agents & skills

The fleet's single source of truth for Claude Code frontmatter facts: platform facts live here and
only here. On conflict with the live docs (code.claude.com/docs/en/sub-agents,
code.claude.com/docs/en/skills) the docs win — update this file and re-verify after CLI upgrades.

## Contents

- Agents
- Skills
- Fleet decisions on unused fields
- Quote description scalars that contain a colon

## Agents

`validate_fleet.py` accepts exactly four keys in canonical agent frontmatter — `name`,
`description`, `tools`, `model` — and fails on any other. Every remaining documented field is
either inert in a plugin or decided against below.

| Field | Disposition here |
|---|---|
| `name`, `description` | Required; `description` is the trigger and is capped at **1,024 UTF-8 bytes** by `validate_fleet.py` |
| `tools` | Allowlist for built-ins **and MCP tools**. **Omitting it inherits every tool**; `tools: []` launches a zero-tool agent (doc-checked through 2.1.223). Exact MCP names are `mcp__<server>__<tool>`; `mcp__<server>` and `mcp__<server>__*` silently acquire tools the server adds later — grant exact entries and include `ToolSearch` when approved MCP tools may be deferred. `Agent(worker)` scoping enforces only for a main-thread agent (`claude --agent`); a subagent ignores the type list. Scoped specifiers such as `Bash(git diff:*)` are **inert on agents** (probed) — per-command scoping exists only via a `PreToolUse` hook, which is what `readonly-guard.py` is. `AskUserQuestion`, `EnterPlanMode`, `ScheduleWakeup`, `WaitForMcpServers` are never available to a subagent |
| `model` | Generation aliases `haiku \| sonnet \| opus \| fable \| inherit` only — `validate_fleet.py` rejects a full ID (a dated pin goes stale silently). No agent pins one today; tiering a routine lane down is allowed when its cost profile justifies it |
| `hooks`, `mcpServers`, `permissionMode` | Plugin-packaged agents **ignore** all three (probed). The fleet ships `hooks/hooks.json` session-wide, self-scoped to exact guarded `agent_type` values; canonical frontmatter containing `hooks` fails validation |
| `disallowedTools`, `skills`, `maxTurns`, `memory`, `background`, `effort`, `isolation`, `color`, `initialPrompt` | Real on the platform, unused here. `skills:` preloads full skill content at startup — prefer it over `Skill` in `tools` if an agent ever needs a skill every run, and never list a `disable-model-invocation: true` skill. `maxTurns` and `memory` are decided against below |

## Skills

Precedence for same-named non-namespaced skills is the **reverse** of agents — a personal skill
carrying a fleet skill's name silently shadows it, so check there first when a fleet skill "never
fires"; plugin skills are namespaced (`plugin:name`) and sit outside that chain.

| Field | Disposition here |
|---|---|
| `name`, `description`, `argument-hint` | The fleet's set. `description` is the trigger and loads every session; `check_links.py` caps it at **600 UTF-8 bytes** and requires a literal `Triggers:` list carrying 2–4 quoted user phrasings |
| `disable-model-invocation: true` | Side-effect skills (deploy, onboard): user-only invocation via `/plugin:name`, description removed from the model's context, unavailable for agent `skills:` preloading. `[verified 2026-08-25, CLI 2.1.243]` by a paired disposable-plugin canary; earlier builds (2.1.29, 2.1.212) ignored it for plugin-shipped skills, so the skill body still defers authority rather than trusting the flag |
| `allowed-tools`, `disallowed-tools` | `allowed-tools` **grants** (pre-approves) while the skill is active and cannot restrict; `disallowed-tools` **removes** tools while the skill is active, clearing on the next user message — the only restricting field. Neither is used here |
| `user-invocable: false`, `when_to_use`, `arguments`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell` | Available on the platform, unused here; `when_to_use` is decided against below |

### Portability

Six fields survive outside Claude Code, and the portable set can only grant authority, never
restrict it — the map is [skill portability](./skill-portability.md).

### Hook scoping is a fleet decision

Hook matchers can express an agent-scoped hook; the read-only guard deliberately does not use one.
A matcher that stops matching after an upstream rename silently skips the hook and fails **open**;
the guard runs on every Bash call and scopes itself in Python, so the same rename trips a canary and
fails **closed**.

### Authoring rules that are checkable

| Rule | Failure it prevents |
|---|---|
| A reference file over 100 lines opens with a `## Contents` list | Partial (`head`-style) reads hide everything below the preview window |
| Bundle references one level deep from SKILL.md; sibling cross-links are fine when every file is also linked from SKILL.md (the link checker enforces the direct link) | A chain — SKILL.md → A → B — loses the pointer to B on a partial read of A |
| No relative link that escapes the skill's own folder; duplicate shared prose between skills instead, and compose at the invocation layer | A skill ships as a self-contained folder per surface (claude.ai zip, API upload, filesystem, plugin), so an escaping link breaks silently once the folder ships alone |
| No time-sensitive prose ("before August 2026, use X"); superseded guidance goes under an "old patterns" heading or gets a date-stamped fact | Silent staleness |

### Discovery and invoked-content budgets are different contracts

[verified against the installed CLI 2.1.241, 2026-08-24] Discovery listing (every model-invocable
name and description together, 1% of context — 8,000 characters by default) and invoked bodies
(5,000 tokens per skill, 25,000 total) are separate budgets, so moving conditional detail out of
`SKILL.md` reduces invoked context, not discovery-listing cost: a body-size screen, a
discovery-listing measurement, and a description-routing edit are three separate decisions with
three verification rules.

## Fleet decisions on unused fields

Considered, not overlooked; reopen only with a reason.

| Field | Decision |
|---|---|
| `when_to_use` | Trigger phrasings live in `description` so routing has one surface to tune; both share the 1,536-character cap |
| `maxTurns` | Loop bounds are task-shaped prose rules (three-strikes, two-round review caps) that fail with a diagnosis; a turn cap fails mid-thought. Revisit on an observed runaway loop |
| `memory` | Agents are stateless; durable knowledge lives in the repo. Setting it auto-enables Read/Write/Edit, so it must never reach `reviewer`, `repository-investigator`, or `researcher` |

## Quote description scalars that contain a colon

A plain (unquoted) `description:` containing `: ` or a colon-bearing token such as
`save-toolkit:<name>` parses in the runtime and in `validate_fleet.py` but fails `claude plugin tag`
with "Unexpected token", blocking the release path [probed 2026-08-02, CLI 2.1.220].
**Double-quote the whole scalar**; the rendered string is identical, so routing and evals are
unaffected. Internal `\"` escapes are fine — the four descriptions that carry them are
byte-identical in canonical and Copilot form and `claude plugin tag --dry-run` completes on this
tree [probed 2026-08-19, CLI 2.1.236].
