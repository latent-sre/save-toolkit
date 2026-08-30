# Claude Code frontmatter — agents & skills

The fleet's single source of truth for Claude Code frontmatter facts: platform facts live here and
only here. On conflict with the live docs (code.claude.com/docs/en/sub-agents,
code.claude.com/docs/en/skills) the docs win — update this file and re-verify after CLI upgrades.
This fleet is a Claude plugin: canonical agents and skills live at repository root, the manifest in
`.claude-plugin/`; project- and user-scope behavior below is comparison context, not this fleet's
enforcement surface.

## Contents

- Agents
- Skills
- Fleet decisions on unused fields
- Quote description scalars that contain a colon

## Agents

Locations: `agents/*.md` in a plugin; `.claude/agents/*.md` project-level; `~/.claude/agents/*.md`
user-level; a project-level definition shadows a user-level one of the same name. Required: `name`,
`description` (the trigger). Optional: `tools`, `disallowedTools`, `model`, `permissionMode`,
`maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`,
`initialPrompt`. Authority lives in frontmatter, not prose:

| Field | Facts |
|---|---|
| `tools` | Allowlist for built-ins **and MCP tools**. **Omitting it inherits every tool**; `tools: []` launches a zero-tool agent (doc-checked through 2.1.223). Exact MCP names are `mcp__<server>__<tool>`; `mcp__<server>` and `mcp__<server>__*` silently acquire tools the server adds later — grant exact entries and include `ToolSearch` when approved MCP tools may be deferred. `Agent(worker)` scoping enforces only for a main-thread agent (`claude --agent`); a subagent ignores the type list. Scoped specifiers such as `Bash(git diff:*)` are **inert on agents** (probed) — per-command scoping exists only via a `PreToolUse` hook, which is what `readonly-guard.py` is. `AskUserQuestion`, `EnterPlanMode`, `ScheduleWakeup`, `WaitForMcpServers` are never available to a subagent |
| `disallowedTools` | Denylist; applied before `tools` resolves |
| `permissionMode` | `default \| acceptEdits \| auto \| dontAsk \| bypassPermissions \| plan \| manual`; real at project scope, ignored for plugin-shipped agents, unused here |
| `hooks` | Real at project/user scope, **inert in a plugin** (probed). The fleet ships `hooks/hooks.json` session-wide, self-scoped to exact guarded `agent_type` values; canonical frontmatter containing `hooks` fails validation |
| `skills` | Preloads full skill content at startup — prefer it over `Skill` in `tools` when the agent needs the skill every run; never list a `disable-model-invocation: true` skill |
| `model` | Aliases `haiku \| sonnet \| opus \| fable \| inherit`, or a full ID; defaults to `inherit`. This fleet accepts aliases only — `validate_fleet.py` rejects a full ID (a dated pin goes stale silently). No agent pins one today; tiering a routine lane down is allowed when its cost profile justifies it |
| `memory` | `user \| project \| local`. **Auto-enables Read, Write, and Edit** — never on a constrained agent (`reviewer`, `repository-investigator`, `researcher`) |
| `maxTurns`, `background`, `effort`, `isolation`, `color`, `initialPrompt` | int; bool; `low\|medium\|high\|xhigh\|max`; `worktree`; display; main-session only |

Plugin-packaged agents **ignore** `hooks`, `mcpServers`, and `permissionMode`. Spell keys exactly:
an unrecognized key is not guaranteed to fail loudly.

## Skills

Locations: `skills/<name>/SKILL.md` in a plugin; `.claude/skills/<name>/SKILL.md` project-level.
Precedence for same-named non-namespaced skills is the **reverse** of agents — enterprise →
personal → project → bundled — so a personal skill with a fleet skill's name silently shadows it;
check there first when a fleet skill "never fires". Plugin skills are namespaced (`plugin:name`) and
sit outside that chain.

| Field | Facts |
|---|---|
| `name`, `description`, `argument-hint` | Core; `description` is the trigger and loads every session — keep it lean |
| `disable-model-invocation: true` | Side-effect skills (deploy, onboard): user-only invocation via `/plugin:name`, description removed from the model's context, unavailable for agent `skills:` preloading. `[verified 2026-08-25, CLI 2.1.243]` by a paired disposable-plugin canary; earlier builds (2.1.29, 2.1.212) ignored it for plugin-shipped skills, so the skill body still defers authority rather than trusting the flag |
| `user-invocable: false` | Background-knowledge skills hidden from the `/` menu |
| `allowed-tools` | **Grants** (pre-approves) while the skill is active; does not restrict. Bare names or permission-rule specifiers (`Bash(git add *)`) |
| `disallowed-tools` | **Removes** tools while the skill is active (clears on the next user message) — the restricting field |
| `when_to_use`, `arguments`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell` | Available; not exhaustive — see the docs table |

### Progressive disclosure: three levels, three budgets

[doc-checked 2026-08-05]

| Level | Loads | Budget | Content |
|---|---|---|---|
| 1 — metadata | Always, at startup | ~100 tokens per skill | `name` + `description` |
| 2 — instructions | When the skill is triggered | **under 5k tokens** | The SKILL.md body |
| 3 — resources | Only when a file is read | None until accessed | Bundled reference, asset, and script files |

Measure the body against the 5k-token Level-2 figure, not a line count. Unread bundled content
costs nothing: move subset-only material (long procedures, lookup tables, worked examples,
tool-specific syntax) into linked bundle files; a script run through Bash returns only its output.

### Portability

Six fields survive outside Claude Code, and the portable set can only grant authority, never
restrict it — the map is [skill portability](./skill-portability.md); this file owns what each field
does.

### Hook scoping is a fleet decision

Hook matchers can express an agent-scoped hook; the read-only guard deliberately does not use one.
A matcher that stops matching after an upstream rename silently skips the hook and fails **open**;
the guard runs on every Bash call and scopes itself in Python, so the same rename trips a canary and
fails **closed**.

### Authoring rules that are checkable

[doc-checked 2026-08-05]

| Rule | Failure it prevents |
|---|---|
| SKILL.md body under 500 lines; split into bundle files when approaching it | The documented authoring limit (the separate 5k-token figure is the portable spec's) |
| A reference file over 100 lines opens with a `## Contents` list | Partial (`head`-style) reads hide everything below the preview window |
| Bundle references one level deep from SKILL.md; sibling cross-links are fine when every file is also linked from SKILL.md (the link checker enforces the direct link) | A chain — SKILL.md → A → B — loses the pointer to B on a partial read of A |
| Descriptions in third person; quoted *user* phrasings in a `Triggers:` list are correct as-is | "I can help you…" in the system prompt breaks discovery |
| Names are noun phrases or gerunds (`processing-pdfs`), never `helper`, `utils`, `tools`, `data` | Vague names do not route |
| Forward slashes in every path | Backslash paths error on Unix |
| Fully qualified MCP tool names in prose — `ServerName:tool_name` (agent `tools:` uses `mcp__<server>__<tool>`) | A bare name may not resolve with several servers present |
| No time-sensitive prose ("before August 2026, use X"); superseded guidance goes under an "old patterns" heading or gets a date-stamped fact | Silent staleness |
| Build evaluations before writing extensive instructions | Content that answers an imagined failure instead of a real one |

### Skill discovery and invoked-content budgets are different contracts

[doc-checked 2026-08-24 against code.claude.com/docs/en/skills; verified against the installed CLI
2.1.241]

| Contract | Facts |
|---|---|
| Discovery metadata (aggregate) | Model-invocable names and descriptions form one listing budgeted at 1% of context — four characters per token, 200,000-token fallback, so 8,000 characters by default. Over budget, names remain and lower-priority descriptions shorten or drop. `skillListingBudgetFraction` and `SLASH_COMMAND_TOOL_CHAR_BUDGET` change it |
| Routing metadata (per skill) | `description` plus `when_to_use` capped at 1,536 characters (`skillListingMaxDescChars`); splitting across both buys no space |
| Invoked body (lifecycle) | Enters as one persistent message; identical reinvocation adds an already-loaded note, changed content appends again; after compaction the newest invocation of each skill is reattached, up to 5,000 tokens per skill and 25,000 total, newest first |

Moving conditional detail out of `SKILL.md` reduces invoked context, not discovery-listing cost;
a body-size screen, a discovery-listing measurement, and a description-routing edit are three
separate decisions with three verification rules.

### Why a skill may not link outside its own folder

[doc-checked 2026-08-05] A skill ships as a self-contained folder per surface (claude.ai zip, API
upload, filesystem, plugin) and does not sync across surfaces, so a relative link that escapes the
folder breaks silently once the folder is shipped alone. The link checker enforces this; shared
prose is duplicated between skills rather than factored into a common file, and composition happens
at the invocation layer — descriptions and routing, never filesystem links between skill folders.

## Fleet decisions on unused fields

Considered, not overlooked; reopen only with a reason.

| Field | Decision |
|---|---|
| `when_to_use` | Trigger phrasings live in `description` so routing has one surface to tune; both share the 1,536-character cap. Agent descriptions are held to **1,024 UTF-8 bytes** by `validate_fleet.py` |
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
