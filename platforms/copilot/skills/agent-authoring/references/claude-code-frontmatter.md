# Claude Code frontmatter — agents & skills

Read this before writing or editing the frontmatter of any agent or skill file. It is the fleet's
**single source of truth** for Claude Code frontmatter facts — drifted duplicate copies of these
facts are how a sister fleet shipped a wrong claim within one release, so platform facts live here
and only here. On any conflict with the live docs (code.claude.com/docs/en/sub-agents,
code.claude.com/docs/en/skills), the docs win — update this file, re-verify after CLI upgrades.
This fleet is a **Claude plugin**: canonical agents and skills live at repository root and the
manifest lives in `.claude-plugin/`. Project- and user-scope behavior below is comparison context,
not this fleet's enforcement surface.

## Agents

Locations: `agents/*.md` in a plugin; `agents/*.md` project-level; `~/.claude/agents/*.md`
user-level. A project-level definition shadows a user-level one of the same name.

Required: `name`, `description` (the trigger). Optional: `tools`, `disallowedTools`, `model`,
`permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`,
`isolation`, `color`, `initialPrompt`.

Authority lives in frontmatter, not in prose — the fields that carry it:

| Field | Notes |
|---|---|
| `tools` | Allowlist for built-ins **and MCP tools**. **Omitting it inherits every tool** — omission is "all tools," not "none." Exact MCP names use `mcp__<server>__<tool>`; `mcp__<server>` and `mcp__<server>__*` are server-wide patterns that **silently acquire tools the server adds later**, so grant exact entries and include `ToolSearch` when approved MCP tools may be deferred (listed by name until their schema is fetched). `Agent(worker)` scoping works only for a main-thread agent (`claude --agent`); a subagent silently ignores the type list, so at subagent depth it documents intent rather than enforcing it. Scoped specifiers like `Bash(git diff:*)` are **inert on agents** (probed: agents granted them ran `git status` exactly like bare `Bash`) — per-command scoping on an agent exists only via a `PreToolUse` hook, which is what the repo's `readonly-guard.py` is for. `AskUserQuestion`, `EnterPlanMode`, `ScheduleWakeup`, `WaitForMcpServers` are never available to a subagent, however listed. |
| `disallowedTools` | Denylist; applied before `tools` resolves. |
| `permissionMode` | `default \| acceptEdits \| auto \| dontAsk \| bypassPermissions \| plan \| manual`. Real at project scope but unused in this fleet; ignored for plugin-shipped agents. |
| `hooks` | Agent-scoped lifecycle hooks are real at project/user scope and **inert in a plugin** (probed). This fleet ships `hooks/hooks.json` session-wide and self-scopes to exact guarded `agent_type` values. Canonical agent frontmatter containing `hooks` fails validation. |
| `skills` | Preloads full skill content at startup — prefer this over putting `Skill` in `tools` when the agent needs the skill every run. Don't list a `disable-model-invocation: true` skill here. |
| `model` | Aliases `haiku \| sonnet \| opus \| fable \| inherit`, or a full ID; defaults to `inherit`. This fleet pins nothing — the whole roster inherits the session model (a deliberate, documented decision; see AGENTS.md). |
| `memory` | `user \| project \| local`. **Setting it auto-enables Read, Write, and Edit** — never add it to a read-only agent (`reviewer`, `repository-investigator`, `researcher`); it would silently widen the mandate and give the external-only researcher local access. |

Also: `maxTurns` (int), `background` (bool), `effort` (`low|medium|high|xhigh|max`), `isolation`
(`worktree`), `color`, `initialPrompt` (main-session only).

Plugin-packaged agents **ignore** `hooks`, `mcpServers`, and `permissionMode` — a guard that works
locally is silently absent once the agent ships in a plugin. Spell keys exactly: an unrecognized key
is not guaranteed to fail loudly, so a typo can silently drop what it configured.

## Skills

Locations: `skills/<name>/SKILL.md` in a plugin; `skills/<name>/SKILL.md` project-level.
Precedence for **same-named non-namespaced skills** is the **reverse** of agents: a personal
(user-level) skill overrides a project-level one — enterprise → personal → project → bundled. A
personal skill with a fleet skill's name silently shadows it; check there first when a fleet skill
"never fires." Plugin skills are namespaced (`plugin:name`) and don't participate in that chain.

Core fields: `name`, `description` (the trigger), `argument-hint`. Behavior switches:

- `disable-model-invocation: true` — for side-effect skills (deploy, onboard): user-only via
  `/plugin:name`, description removed from the model's context, not preloadable via an agent's `skills:`.
  Binding at project scope; **ignored for plugin-shipped skills** (anthropics/claude-code#22345;
  last verified against CLI 2.1.212, 2026-07-17). Set it for intent either way, but in a plugin
  make the skill's own content defer authority rather than trusting the flag.
- `user-invocable: false` — background-knowledge skills, hidden from the `/` menu.
- `allowed-tools` **grants** (pre-approves, no permission prompt) while the skill is active — it
  does **not** restrict availability. Takes bare tool names or permission-rule specifiers
  (`Bash(git add *)`).
- `disallowed-tools` **removes** tools while the skill is active (clears on the next user message) —
  this is the restricting field.

Also available: `when_to_use`, `arguments`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`,
`shell` — not exhaustive; see code.claude.com/docs/en/skills for the current table.

Keep descriptions lean — they load into context every session.

## Platform environment facts

Perishable — probed/doc-checked against the CLI 2.1.220 era; re-verify after upgrades.

- **`${CLAUDE_PLUGIN_DATA}`** [doc-checked 2026-07-30] — per-plugin persistent, writable data
  directory (`~/.claude/plugins/data/{id}/`), created on first reference and surviving plugin
  updates; exported to hook processes. It is the place for generated state, caches, or installed
  dependencies — never write into the plugin tree itself, which an update overwrites.
- **`CLAUDE_ENV_FILE`** [doc-checked 2026-07-30] — available to `SessionStart` hooks: append
  `export` lines to it to persist environment variables for the session's later Bash commands.
  Append, never truncate — other hooks share the same file.
- **`/doctor`** [doc-checked 2026-07-30] — a bundled skill (was a built-in command before v2.1.205):
  diagnoses setup and flags unused skills/MCP servers/plugins against their context cost. Reports
  first and asks before changing. `claude doctor` from the terminal is the read-only form.
- **`/verify`** [doc-checked 2026-07-30] — a bundled skill (v2.1.145+) that builds and runs the app
  to confirm a change does what it should. Since v2.1.215 it runs only when the user invokes it,
  never autonomously.

## Fleet decisions on unused fields

Fields the fleet deliberately does not use — considered, not overlooked. Reopen only with a reason:

- **`when_to_use`** — trigger phrasings live in `description` so routing has one surface to tune.
  Both fields share the same listing cap (platform limit **1,536 characters** [doc-checked, CLI
  2.1.220 era]), so splitting saves nothing. This fleet holds *agent* descriptions to a tighter
  budget than the platform allows: the repo's `validate_fleet.py` fails any agent `description` over
  **1024 UTF-8 bytes**, so size to that, not to the platform ceiling.
- **`maxTurns`** — loop bounds are task-shaped prose rules (three-strikes, two-round review caps),
  which fail with a diagnosis; a turn cap fails mid-thought. Revisit if a runaway loop is observed.
- **`memory`** — agents are stateless by design; durable knowledge lives in the repo (runbooks,
  docs). And setting `memory` auto-enables Read/Write/Edit, so it must never reach `reviewer`,
  `repository-investigator`, or `researcher`.

## Plain-scalar descriptions and the CLI's stricter parser

A plain (unquoted) `description:` whose value contains `: ` (colon-space) or a colon-bearing token
parses fine in the runtime and in the repo's `validate_fleet.py` but can fail `claude plugin tag` with
"Unexpected token", **blocking the release path** — observed 2026-08-02 on CLI 2.1.220, while
`claude plugin validate --strict` and sibling descriptions with a simple `: ` passed. [probed on
CLI 2.1.220] This bites us directly: several descriptions name a component as `save-toolkit:<name>`
after a colon. **Double-quote the whole scalar** when a description embeds such a namespaced
reference; the rendered string is identical, so routing and evals are unaffected. Quoting works only
while the text needs no internal escapes — the adapter generator copies the raw value, so `\"`
sequences would land literally in the generated projections; a description that would need escaped
quotes gets a punctuation reword instead.
