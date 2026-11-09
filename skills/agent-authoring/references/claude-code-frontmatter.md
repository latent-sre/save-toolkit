# Claude Code frontmatter — agents & skills

Claude frontmatter contracts live here. Re-verify after CLI upgrades against the
[subagent](https://code.claude.com/docs/en/sub-agents) and
[skill](https://code.claude.com/docs/en/skills) docs and the installed host.

## Contents

- Agents
- Skills
- Tool output caps
- Fleet decisions on unused fields

## Agents

`validate_fleet.py` accepts exactly four keys in canonical agent frontmatter — `name`,
`description`, `tools`, `model` — and fails on any other. This is the fleet's selected subset,
not the full host schema; other fields are either inert in a plugin or unused here.

A plugin agent with invalid YAML can still appear under its filename while every frontmatter
field is ignored. Discovery alone does not establish that its grants or model were applied;
validate the source and generated headers before publishing (`claude plugin validate` on the plugin
directory finds unparsed agent files). The fleet's validators parse frontmatter as YAML, as the
hosts do. Double-quote a `description` containing `: `.

| Field | Disposition here |
|---|---|
| `name`, `description` | Required; `description` is the trigger and is capped at **1,024 UTF-8 bytes** by `validate_fleet.py` |
| `tools` | Allowlist for built-ins **and MCP tools**. **Omitting it inherits every tool**; a list in which no entry resolves to a tool usually fails to launch with an error naming the entries, so never rely on an empty list for a zero-tool agent. Exact MCP names are `mcp__<server>__<tool>`; `mcp__<server>` and `mcp__<server>__*` silently acquire tools the server adds later — grant exact entries and include `ToolSearch` when approved MCP tools may be deferred. `Agent(worker)` scoping enforces only for a main-thread agent (`claude --agent`); a subagent ignores the type list. Shell-command restrictions are separate from this tool list; see below. **Removed from every subagent regardless of `tools:`** — `AskUserQuestion`, `EndConversation`, `EnterPlanMode`, `ExitPlanMode` (unless the subagent's `permissionMode` is `plan`), `ScheduleWakeup`, `WaitForMcpServers`, `Workflow`; and `Agent` at the depth limit. A **background** subagent (the default for one spawned from the main conversation) keeps `Agent` below that limit and `TaskStop`, subject to its grants; its other built-ins are filtered as listed in [Available tools](https://code.claude.com/docs/en/sub-agents#available-tools). A **fork** skips tool filtering entirely and receives the main conversation's exact pool, so a fork is not a way to bound authority |
| `model` | Generation aliases `haiku \| sonnet \| opus \| fable \| inherit` only — `validate_fleet.py` rejects full IDs. No agent pins one. Cost-justified tiering may lower mechanical, high-volume lanes; review, root-cause, and authority lanes inherit. State a pin's reason in the same change. Check `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, and `CLAUDE_CODE_SUBAGENT_EFFORT` before attributing a lane result to the session model or effort. Generated Copilot adapters carry no `model` |
| `hooks`, `mcpServers`, `permissionMode` | Plugin-packaged agents **ignore** all three. The fleet ships `hooks/hooks.json` session-wide, self-scoped to exact guarded `agent_type` values; canonical frontmatter containing `hooks` fails validation |
| `initialPrompt` | Ignored for plugin subagents |
| `omitClaudeMd` | Unused here; adopting it for trusted-base review needs a `validate_fleet.py` key decision and a host check |
| `disallowedTools`, `skills`, `maxTurns`, `autoCompactWindow`, `memory`, `background`, `effort`, `isolation`, `color`, `experimental` | Supported for plugin agents, unused here. `maxTurns` and `memory` are decided against below |

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
PowerShell tool for the session unless `CLAUDE_CODE_USE_POWERSHELL_TOOL=1` is set or a settings file
adds a scoped `PowerShell(...)` permission rule. Availability depends on the host/provider configuration; see the [PowerShell tool](https://code.claude.com/docs/en/tools-reference#powershell-tool).
Use the available shell's syntax and runtime paths. A generated Copilot `execute` grant represents
host execution capability, not a promise that Bash is installed.

## Skills

Plugin skills use `plugin:name` and coexist with same-named personal/project skills.

| Field | Disposition here |
|---|---|
| `name`, `description`, `argument-hint` | The fleet's set. `description` is the trigger and loads every session; `check_links.py` caps it at the portable **1,024-character** maximum and requires a literal `Triggers:` list carrying 2–4 quoted user phrasings. Claude Code shows `<` and `>` in a description as `&lt;` and `&gt;`, so write placeholders in square brackets |
| `compatibility` | Descriptive only: up to 500 characters that Claude Code accepts but does not act on. The fleet uses it for host and access prerequisites (for example `pcf-deploy`); `check_links.py` allows it |
| `disable-model-invocation: true` | Side-effect skills (deploy): user-only invocation via `/plugin:name`, description removed from the model's context, unavailable for agent `skills:` preloading. The skill body still defers authority rather than trusting the flag |
| `allowed-tools`, `disallowed-tools` | `allowed-tools` **grants** (pre-approves) for the turn that invokes the skill, clearing on the next user message, and cannot restrict; `disallowed-tools` **removes** tools while the skill is active, clearing on the next user message — the only restricting field. Neither is used here |

### Authoring rules (the link checker enforces the direct-link and no-escaping-link rules)

| Rule | Failure it prevents |
|---|---|
| A reference file over 100 lines opens with a `## Contents` list | Partial (`head`-style) reads hide everything below the preview window |
| Bundle references one level deep from SKILL.md; sibling cross-links are fine when every file is also linked from SKILL.md (the link checker enforces the direct link; a script that a linked script loads needs none, because the model never reads it) | A chain — SKILL.md → A → B — loses the pointer to B on a partial read of A |
| No relative link that escapes the skill's own folder; duplicate shared prose between skills instead, and compose at the invocation layer | A skill ships as a self-contained folder per surface (claude.ai zip, API upload, filesystem, plugin), so an escaping link breaks silently once the folder ships alone |

### Discovery and invoked-content budgets are different contracts

Discovery names/descriptions share a budget: 1% of the context window by default
(`skillListingBudgetFraction`). On overflow names remain but least-invoked descriptions are
dropped; inspect the `/context` Skills row or `--debug` log on the actual host. Claude Code
truncates a skill's combined `description` and `when_to_use` listing at 1,536 characters by
default; the fleet's 1,024-character limit preserves portability.

An invoked body loads whole as one message and persists across turns without a re-read, so write
task-long guidance as standing instructions, not one-time steps. The 5,000-token per-skill /
25,000-token combined limits apply only to reattachment after summary compaction.

## Tool output caps

Hosts cap MCP tool results differently: bound output with pagination and filters rather than
relying on a cap.

## Fleet decisions on unused fields

| Field | Decision |
|---|---|
| `when_to_use` | Trigger phrasings live in `description` so routing has one surface to tune under the fleet's portable skill-description limit |
| `maxTurns` | A capped subagent returns partial output marked as partial, and Claude can resume it. Still unused: loop bounds are task-shaped prose rules (three-strikes, two-round review caps) that fail with a diagnosis. Revisit on an observed runaway loop |
| `memory` | Agents are stateless; durable knowledge lives in the repo. It is not a scratch workspace. Setting it auto-enables Read/Write/Edit, so it must never reach `repository-investigator` or `researcher` |
| `TodoWrite` in `tools` | Disabled by default in favour of `TaskCreate`/`TaskGet`/`TaskList`/`TaskUpdate`, so a lane listing it launches without it. Kept only as the source of Copilot's `todo`, which VS Code provisions and the cloud coding agent does not. No swap to the Task* names is planned |
