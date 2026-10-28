# Claude Code frontmatter — agents & skills

Claude frontmatter contracts live here. Re-verify after CLI upgrades against the
[subagent](https://code.claude.com/docs/en/sub-agents) and
[skill](https://code.claude.com/docs/en/skills) docs and the installed host.

## Contents

- Agents
- Skills
- Tool output caps
- Fleet decisions on unused fields
- Quote description scalars that contain a colon

## Agents

`validate_fleet.py` accepts exactly four keys in canonical agent frontmatter — `name`,
`description`, `tools`, `model` — and fails on any other. This is the fleet's selected subset,
not the full host schema; other fields are either inert in a plugin or unused here.

A plugin agent with invalid YAML can still appear under its filename while every frontmatter
field is ignored. Discovery alone does not establish that its grants or model were applied;
validate the source and generated headers before publishing.

| Field | Disposition here |
|---|---|
| `name`, `description` | Required; `description` is the trigger and is capped at **1,024 UTF-8 bytes** by `validate_fleet.py` |
| `tools` | Allowlist for built-ins **and MCP tools**. **Omitting it inherits every tool**; a list in which no entry resolves to a tool usually fails to launch with an error naming the entries, so never rely on an empty list for a zero-tool agent. Exact MCP names are `mcp__<server>__<tool>`; `mcp__<server>` and `mcp__<server>__*` silently acquire tools the server adds later — grant exact entries and include `ToolSearch` when approved MCP tools may be deferred. `Agent(worker)` scoping enforces only for a main-thread agent (`claude --agent`); a subagent ignores the type list. Shell-command restrictions are separate from this tool list; see below. **Removed from every subagent regardless of `tools:`** — `AskUserQuestion`, `EndConversation`, `EnterPlanMode`, `ExitPlanMode` (unless the subagent's `permissionMode` is `plan`), `ScheduleWakeup`, `WaitForMcpServers`, `Workflow`; and `Agent` at the depth limit. A **background** subagent keeps `Agent` below that limit and `TaskStop`, subject to its grants; its other built-ins are filtered as listed in [Available tools](https://code.claude.com/docs/en/sub-agents#available-tools). A **fork** skips tool filtering entirely and receives the main conversation's exact pool, so a fork is not a way to bound authority |
| `model` | Generation aliases `haiku \| sonnet \| opus \| fable \| inherit` only — `validate_fleet.py` rejects full IDs. No agent pins one. Cost-justified tiering may lower mechanical, high-volume lanes; review, root-cause, and authority lanes inherit. State a pin's reason in the same change. Resolution order: the call's `model`, then frontmatter `model`, then `CLAUDE_CODE_SUBAGENT_MODEL`, then the session model; a family alias in the call or frontmatter resolves to the session's exact model when it is that family. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` ignores the first two, so check both variables before attributing a lane result to the session model. A fork always runs on the session model. Generated Copilot adapters carry no `model` |
| `hooks`, `mcpServers`, `permissionMode` | Plugin-packaged agents **ignore** all three. The fleet ships `hooks/hooks.json` session-wide, self-scoped to exact guarded `agent_type` values; canonical frontmatter containing `hooks` fails validation |
| `initialPrompt` | Ignored for plugin subagents |
| `omitClaudeMd` | Supported for plugin subagents: omits user, project, and local CLAUDE.md files from initial context; managed policy remains. Ignored when the agent is the main session. Unused here; adopting it for trusted-base review needs a `validate_fleet.py` key decision and a host check |
| `disallowedTools`, `skills`, `maxTurns`, `autoCompactWindow`, `memory`, `background`, `effort`, `isolation`, `color`, `experimental` | Supported for plugin agents, unused here. `skills:` preloads the first 32 distinct skills at startup; use it only for a skill needed every run, never one with `disable-model-invocation: true`. `autoCompactWindow` selects a 100,000–1,000,000-token window; `experimental.cacheTtl` accepts `5m` or `1h`. These are behavior choices, not required compatibility fields. `maxTurns` and `memory` are decided against below |

Scoped Bash specifiers in agent `tools:` did not narrow commands on the hosts tested. In `disallowedTools`,
`Bash(git push *)` removes Bash entirely. The same entry in settings `permissions.deny`
instead denies matching commands while retaining Bash;
it applies to both the main conversation and subagents
([available tools](https://code.claude.com/docs/en/sub-agents#available-tools)). Such a rule
matches the command text, not the program, so it is not a security boundary: `git -C . push origin
main` passes a `Bash(git push *)` deny ([Bash rule limits](https://code.claude.com/docs/en/permissions#bash-rule-limits)).
The fleet's `PreToolUse` hook supplies its agent-specific command policy through `readonly-guard.py`;
how that guard scopes itself is maintainer detail in the Save Toolkit repository's `CONTRIBUTING.md`.

Canonical plugin delegation grants use full names: `Agent(save-toolkit:reviewer, save-toolkit:scribe)`.
Bare targets did not match plugin agent identities on the hosts tested; the
generator projects the same targets to bare Copilot names. The validator rejects unqualified or
foreign-plugin grants.

On native Windows, `PowerShell` is a separate shell tool and needs its own grant; `Bash` does not
grant it. With Git Bash installed, any Bash deny rule, even a scoped one, silently disables the
PowerShell tool for the session. Availability depends on the host/provider configuration; see the [PowerShell tool](https://code.claude.com/docs/en/tools-reference#powershell-tool).
Use the available shell's syntax and runtime paths. A generated Copilot `execute` grant represents
host execution capability, not a promise that Bash is installed.

## Skills

Plugin skills use `plugin:name` and coexist with same-named personal/project skills. For missed
invocations, inspect overlapping triggers and discovery-listing omissions separately.

| Field | Disposition here |
|---|---|
| `name`, `description`, `argument-hint` | The fleet's set. `description` is the trigger and loads every session; `check_links.py` caps it at the portable **1,024-character** maximum and requires a literal `Triggers:` list carrying 2–4 quoted user phrasings |
| `compatibility` | Descriptive only: up to 500 characters that Claude Code accepts but does not act on. The fleet uses it for host and access prerequisites (for example `pcf-deploy`); `check_links.py` allows it |
| `disable-model-invocation: true` | Side-effect skills (deploy): user-only invocation via `/plugin:name`, description removed from the model's context, unavailable for agent `skills:` preloading. Older builds ignored it for plugin-shipped skills, so the skill body still defers authority rather than trusting the flag |
| `allowed-tools`, `disallowed-tools` | `allowed-tools` **grants** (pre-approves) for the turn that invokes the skill, clearing on the next user message, and cannot restrict; `disallowed-tools` **removes** tools while the skill is active, clearing on the next user message — the only restricting field. Neither is used here |
| `user-invocable: false` | Hides the menu entry and prevents typed slash invocation; automatic loading remains available unless disabled separately. Unused here |
| `when_to_use`, `arguments`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell` | Available on the platform, unused here. `background` applies only to `context: fork`; `when_to_use` is decided against below |

### Authoring rules (only the direct-link rule is enforced)

| Rule | Failure it prevents |
|---|---|
| A reference file over 100 lines opens with a `## Contents` list | Partial (`head`-style) reads hide everything below the preview window |
| Bundle references one level deep from SKILL.md; sibling cross-links are fine when every file is also linked from SKILL.md (the link checker enforces the direct link) | A chain — SKILL.md → A → B — loses the pointer to B on a partial read of A |
| No relative link that escapes the skill's own folder; duplicate shared prose between skills instead, and compose at the invocation layer | A skill ships as a self-contained folder per surface (claude.ai zip, API upload, filesystem, plugin), so an escaping link breaks silently once the folder ships alone |
| No time-sensitive prose ("before August 2026, use X"); superseded guidance goes under an "old patterns" heading | Silent staleness |

### Discovery and invoked-content budgets are different contracts

Discovery names/descriptions share a budget: 1% of the context window by default
(`skillListingBudgetFraction`), or a fixed character count from `SLASH_COMMAND_TOOL_CHAR_BUDGET`;
8,000 characters is only the fallback. On overflow names remain but least-invoked descriptions
are dropped; inspect the `/context` Skills row, `/doctor`, or `--debug` log on the actual host.
Claude Code truncates a skill's combined `description` and `when_to_use` listing at 1,536
characters. The fleet's stricter 1,024-character skill-description limit preserves portability;
the separate agent-description byte limit above is repository policy, not a host runtime limit.

An invoked body loads whole as one message and persists across turns. The 5,000-token per-skill /
25,000-token combined limits apply to reattachment after summary compaction: the most recent
invocation of each skill is reattached, truncated to those budgets. Moving conditional detail to
references reduces invoked context, not discovery cost; do not treat compaction limits as
per-invocation truncation.

## Tool output caps

Claude Code caps an MCP tool result at 25,000 tokens by default (`MAX_MCP_OUTPUT_TOKENS`). A
successful foreground call returning text only is saved to a file and replaced by its path once over
50,000 characters, whatever that token setting; a server raises one tool's threshold with
`_meta["anthropic/maxResultSizeChars"]`, up to 500,000. A call moved to a background task reports
through its task notification instead. Other hosts differ: bound output with pagination and filters
rather than relying on a cap.

## Fleet decisions on unused fields

| Field | Decision |
|---|---|
| `when_to_use` | Trigger phrasings live in `description` so routing has one surface to tune under the fleet's portable skill-description limit |
| `maxTurns` | A capped subagent returns partial output marked as partial, and Claude can resume it. Still unused: loop bounds are task-shaped prose rules (three-strikes, two-round review caps) that fail with a diagnosis. Revisit on an observed runaway loop |
| `memory` | Agents are stateless; durable knowledge lives in the repo. It is not a scratch workspace. Setting it auto-enables Read/Write/Edit, so it must never reach `repository-investigator` or `researcher` |
| `TodoWrite` in `tools` | Disabled by default in favour of `TaskCreate`/`TaskGet`/`TaskList`/`TaskUpdate`, none yet shown to reach a subagent, and a partially unresolved list launches without it. Kept only as the source of Copilot's `todo`, which VS Code provisions and the cloud coding agent does not. No swap to the Task* names is planned |

## Quote description scalars that contain a colon

A plain (unquoted) `description:` containing `: ` or a colon-bearing token such as
`save-toolkit:<name>` parses in the runtime and in `validate_fleet.py` but fails `claude plugin tag`
with "Unexpected token", blocking the release path.
**Double-quote the whole scalar**; internal `\"` escapes are fine.
