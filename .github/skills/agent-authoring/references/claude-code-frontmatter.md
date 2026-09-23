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
| `tools` | Allowlist for built-ins **and MCP tools**. **Omitting it inherits every tool**; `tools: []` launches a zero-tool agent (doc-checked through 2.1.223). Exact MCP names are `mcp__<server>__<tool>`; `mcp__<server>` and `mcp__<server>__*` silently acquire tools the server adds later — grant exact entries and include `ToolSearch` when approved MCP tools may be deferred. `Agent(worker)` scoping enforces only for a main-thread agent (`claude --agent`); a subagent ignores the type list. Scoped specifiers such as `Bash(git diff:*)` are **inert on agents** (probed) — per-command scoping exists only via a `PreToolUse` hook, which is what `readonly-guard.py` is. **Removed from every subagent regardless of `tools:`** — `AskUserQuestion`, `EndConversation`, `EnterPlanMode`, `ExitPlanMode` (unless the subagent's `permissionMode` is `plan`), `ScheduleWakeup`, `WaitForMcpServers`, `Workflow`; and `Agent` at the depth limit. A **background** subagent keeps `Agent` below that limit and `TaskStop`, subject to its grants; its other built-ins are filtered as listed in [Available tools](https://code.claude.com/docs/en/sub-agents#available-tools). This is the documented contract, not a fresh installed-host probe. A **fork** skips tool filtering entirely and receives the main conversation's exact pool, so a fork is not a way to bound authority |
| `model` | Generation aliases `haiku \| sonnet \| opus \| fable \| inherit` only — `validate_fleet.py` rejects a full ID (a dated pin goes stale silently). No agent pins one today; tiering a routine lane down is allowed when its cost profile justifies it |
| `hooks`, `mcpServers`, `permissionMode` | Plugin-packaged agents **ignore** all three (probed). The fleet ships `hooks/hooks.json` session-wide, self-scoped to exact guarded `agent_type` values; canonical frontmatter containing `hooks` fails validation |
| `initialPrompt` | Ignored for plugin subagents `[sourced: code.claude.com/docs/en/sub-agents]` |
| `omitClaudeMd` | Real from Claude Code v2.1.271: launches the subagent without user, project, and local CLAUDE.md files. A candidate for `reviewer`, whose trusted-base review cannot stop a candidate's fleet guide from auto-loading; plugin-subagent behavior is `[unverified]`, and adopting it needs a `validate_fleet.py` key decision |
| `disallowedTools`, `skills`, `maxTurns`, `memory`, `background`, `effort`, `isolation`, `color`, `experimental` | Real on the platform, unused here. `skills:` preloads full skill content at startup — prefer it over `Skill` in `tools` if an agent ever needs a skill every run, and never list a `disable-model-invocation: true` skill. `maxTurns` and `memory` are decided against below |

Canonical plugin delegation grants use full names: `Agent(reviewer, scribe)`.
Bare targets do not match plugin agent identities on the probed Claude Code 2.1.261 host; the
generator projects the same targets to bare Copilot names. The delegation-graph reference owns the
probe boundary and the validator rejects unqualified or foreign-plugin grants.

On native Windows, `PowerShell` is a separate shell tool and needs its own grant; `Bash` does not
grant it. Availability depends on the host/provider configuration; see the [PowerShell tool](https://code.claude.com/docs/en/tools-reference#powershell-tool).
Use the available shell's syntax and runtime paths. A generated Copilot `execute` grant represents
host execution capability, not a promise that Bash is installed.

## Skills

Plugin skills are namespaced (`plugin:name`) and always load beside personal and project skills,
even under the same name `[sourced: code.claude.com/docs/en/skills]`. A fleet skill that "never
fires" usually lost to a personal or other-plugin skill with overlapping triggers, or had its
description dropped from the discovery listing (see the listing budget below).

| Field | Disposition here |
|---|---|
| `name`, `description`, `argument-hint` | The fleet's set. `description` is the trigger and loads every session; `check_links.py` caps it at the portable **1,024-character** maximum and requires a literal `Triggers:` list carrying 2–4 quoted user phrasings |
| `compatibility` | Descriptive only: up to 500 characters that Claude Code accepts but does not act on. The fleet uses it for host and access prerequisites (akamai-edge, gcp-ops, pcf-ops, pcf-deploy); `check_links.py` allows it |
| `disable-model-invocation: true` | Side-effect skills (deploy): user-only invocation via `/plugin:name`, description removed from the model's context, unavailable for agent `skills:` preloading. `[verified 2026-08-25, CLI 2.1.243]` by a paired disposable-plugin canary; earlier builds (2.1.29, 2.1.212) ignored it for plugin-shipped skills, so the skill body still defers authority rather than trusting the flag |
| `allowed-tools`, `disallowed-tools` | `allowed-tools` **grants** (pre-approves) while the skill is active and cannot restrict; `disallowed-tools` **removes** tools while the skill is active, clearing on the next user message — the only restricting field. Neither is used here |
| `user-invocable: false`, `when_to_use`, `arguments`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell` | Available on the platform, unused here; `when_to_use` is decided against below |

### Portability

Six fields survive outside Claude Code, and the portable set can only grant authority, never
restrict it — the map is [skill portability](./skill-portability.md).

### Hook scoping is a fleet decision

Hook matchers can express an agent-scoped hook; the read-only guard deliberately does not use one.
A matcher can silently stop matching after an upstream rename. The guard instead runs on every
Bash or PowerShell call and scopes itself in Python. PowerShell uses a separate literal-command
grammar and native launcher; it is not parsed as arbitrary POSIX shell code. Its canaries deny a guarded name under a changed plugin
namespace, or a recognized guarded identity in another top-level key containing `agent` when
`agent_type` is absent. A renamed key such as `role` is not detected. Re-probe the live PreToolUse
payload after host upgrades; offline tests cover known shapes, not every upstream rename.

### Authoring rules (only the direct-link rule is enforced)

| Rule | Failure it prevents |
|---|---|
| A reference file over 100 lines opens with a `## Contents` list | Partial (`head`-style) reads hide everything below the preview window |
| Bundle references one level deep from SKILL.md; sibling cross-links are fine when every file is also linked from SKILL.md (the link checker enforces the direct link) | A chain — SKILL.md → A → B — loses the pointer to B on a partial read of A |
| No relative link that escapes the skill's own folder; duplicate shared prose between skills instead, and compose at the invocation layer | A skill ships as a self-contained folder per surface (claude.ai zip, API upload, filesystem, plugin), so an escaping link breaks silently once the folder ships alone |
| No time-sensitive prose ("before August 2026, use X"); superseded guidance goes under an "old patterns" heading or gets a date-stamped fact | Silent staleness |

### Discovery and invoked-content budgets are different contracts

The discovery listing (every model-invocable name and description together) is one budget: 1% of
the model's context window by default (`skillListingBudgetFraction`), or a fixed character count
from `SLASH_COMMAND_TOOL_CHAR_BUDGET`; 8,000 characters is only the fallback. On overflow every
name stays and the least-invoked skills lose their descriptions, visible only in the `/context`
Skills row, `/doctor`, or the `--debug` log `[sourced: code.claude.com/docs/en/skills, settings,
env-vars]`. The installed CLI computes about 6,000 characters for a current 200K-window model and
30,000 for 1M `[unverified: read from the 2.1.280 bundle, undocumented]`; the fleet's descriptions
alone exceed 6,000, so on a 200K host some drop. An
invoked skill body is a separate contract: it loads whole into the conversation as a single message
and stays there across later turns. The 5,000-tokens-per-skill / 25,000-combined figures apply only
when a summary compacts the conversation — Claude Code then re-attaches the most recent invocation
of each skill, keeping only the first 5,000 tokens of each, with re-attached skills sharing a
combined 25,000-token budget `[sourced: code.claude.com/docs/en/skills, 2026-09-08]`. So moving
conditional detail out of `SKILL.md` reduces invoked context and what survives compaction, not
discovery-listing cost — and there is no per-invocation truncation to design around: a body-size
screen, a discovery-listing measurement, and a description-routing edit are three separate decisions
with three verification rules.

## Fleet decisions on unused fields

Considered, not overlooked; reopen only with a reason.

| Field | Decision |
|---|---|
| `when_to_use` | Trigger phrasings live in `description` so routing has one surface to tune under the 1,024-character cap |
| `maxTurns` | Since Claude Code v2.1.246 a capped subagent returns partial output marked as partial, and Claude can resume it. Still unused: loop bounds are task-shaped prose rules (three-strikes, two-round review caps) that fail with a diagnosis. Revisit on an observed runaway loop |
| `memory` | Agents are stateless; durable knowledge lives in the repo. It is not a scratch workspace. Setting it auto-enables Read/Write/Edit, so it must never reach `repository-investigator` or `researcher` |
| `TodoWrite` in `tools` | Inert on Claude Code 2.1.268+ — disabled by default in favour of `TaskCreate`/`TaskList`/`TaskUpdate`, none yet shown to reach a subagent, and a partially unresolved list launches without it. Kept only as the source of Copilot's `todo`, which VS Code provisions [verified by the owner 2026-09-13] and the cloud coding agent does not [sourced: docs.github.com custom-agents-configuration]. No swap to the Task* names is planned: on current models they are off by default too, until the session opts in with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` [sourced: code.claude.com/docs/en/tools-reference] |

## Quote description scalars that contain a colon

A plain (unquoted) `description:` containing `: ` or a colon-bearing token such as
`save-toolkit:<name>` parses in the runtime and in `validate_fleet.py` but fails `claude plugin tag`
with "Unexpected token", blocking the release path [probed 2026-08-02, CLI 2.1.220].
**Double-quote the whole scalar**; the rendered string is identical, so routing and evals are
unaffected. Internal `\"` escapes are fine — the four descriptions that carry them are
byte-identical in canonical and Copilot form and `claude plugin tag --dry-run` completes on this
tree [probed 2026-08-19, CLI 2.1.236].
