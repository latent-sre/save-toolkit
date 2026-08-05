# Claude Code frontmatter — agents & skills

Read this before writing or editing the frontmatter of any agent or skill file. It is the fleet's
**single source of truth** for Claude Code frontmatter facts — drifted duplicate copies of these
facts are how a sister fleet shipped a wrong claim within one release, so platform facts live here
and only here. On any conflict with the live docs (code.claude.com/docs/en/sub-agents,
code.claude.com/docs/en/skills), the docs win — update this file, re-verify after CLI upgrades.
This fleet is a **Claude plugin**: canonical agents and skills live at repository root and the
manifest lives in `.claude-plugin/`. Project- and user-scope behavior below is comparison context,
not this fleet's enforcement surface.

## Contents

- Agents
- Skills
- Platform environment facts
- Fleet decisions on unused fields
- Plain-scalar descriptions and the CLI's stricter parser

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

### Progressive disclosure: the three levels and their budgets

[doc-checked 2026-08-05, platform Agent Skills overview] A skill loads in three stages, and the
budget differs per stage. Authoring to the wrong stage is how a skill gets expensive:

| Level | When it loads | Budget | Content |
|---|---|---|---|
| 1 — metadata | always, at startup | ~100 tokens per skill | `name` + `description` |
| 2 — instructions | when the skill is triggered | **under 5k tokens** | the SKILL.md body |
| 3 — resources | only when a file is actually read | **none until accessed** | bundled reference, asset, and script files |

Two consequences worth authoring against:

- **The 5k-token Level-2 figure is the real target for a SKILL.md body**, not a line count. Measure
  the body, not the bundle.
- **Bundled content that is not read costs nothing**, so there is no practical limit on it. When a
  body approaches its budget, move the subset-only material — long procedures, lookup tables, worked
  examples, tool-specific syntax — into a linked bundle file. That is a genuine saving, not a shuffle:
  a script run through Bash returns only its output to context, and its source never enters at all.

### Portability: which frontmatter survives outside Claude Code

[doc-checked 2026-08-05] The Agent Skills spec that other hosts implement accepts only six fields:
`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`. Everything else this
fleet uses — `argument-hint`, `disable-model-invocation`, `user-invocable`, `context`, `agent`,
`paths`, `shell` — is **Claude-only**, and Anthropic's own packaging script rejects a skill that
carries them when publishing to the portable spec. That is fine here (we ship a Claude plugin and
generate the other hosts), but it is the reason a skill cannot simply be copied to a non-Claude host
and be expected to behave the same.

### Recent platform changes worth knowing

[doc-checked 2026-08-05, CLI 2.1.193–2.1.222 changelog] Perishable — re-verify after upgrades:

- **`context: fork` skills now run in the background by default** (2.1.218). Add `background: false`
  to keep the old inline-result behavior. This fleet uses neither field today.
- **Booleans accept `yes`/`no`/`on`/`off`/`1`/`0`** case-insensitively (2.1.218), not just
  `true`/`false`. Keep writing `true` — the repo's checker pins the literal.
- **`${user_config.*}` in a shell-form hook command is rejected** (2.1.218, shell-injection fix); use
  the exec form or read `CLAUDE_PLUGIN_OPTION_<KEY>` from the hook environment. Our hook uses
  neither.
- **Hook matcher semantics tightened**: hyphenated matchers are exact-match (2.1.195),
  comma-separated matchers now fire (2.1.216), and a single-segment `dir/**` matches only one level
  (2.1.214). Our `PreToolUse` matcher is the plain tool name `Bash`, so none of these apply.
- **A colon is reserved in agent names** (2.1.214) for the `plugin-name:agent-name` form; existing
  names keep working. Our kebab-case rule already forbids it.
- **Re-invoking the same skill no longer re-appends its full text** (2.1.202) — a token-bloat fix,
  nothing to change.
- **Agent frontmatter hooks now require accepted workspace trust** (2.1.218). Irrelevant here: plugin
  agents ignore `hooks` entirely, which is why this fleet's guard lives in `hooks/hooks.json`.
- **`claude plugin validate --strict` flags unrecognized manifest fields** with typo suggestions
  (2.1.142+), and `metadata` is recognized rather than flagged (2.1.222). The Claude manifest carries
  a `$schema` pointer to the published plugin-manifest schema for editor validation; it has no
  runtime effect.

A note on hook scoping, since the changelog invites it: matchers can express an agent-scoped hook.
This fleet deliberately does **not** use that for the read-only guard. A matcher that fails to match
— after an upstream rename, say — silently skips the hook and fails **open**. The guard instead runs
on every Bash call and scopes itself in Python, so the same rename trips a canary and fails
**closed**. Keep it that way; the extra invocations are cheap, a disarmed guard is not.

### Authoring rules that are checkable

[doc-checked 2026-08-05, platform skill-authoring best practices] Rules with an objective pass/fail,
so they can be audited rather than argued:

- **SKILL.md body under 500 lines** — the line-based companion to the 5k-token budget. Split into
  bundle files when approaching it.
- **A reference file over 100 lines opens with a `## Contents` list.** Claude may *partially* read a
  long file (previewing with `head`-style reads); without a contents list at the top it cannot see
  what the rest of the file holds, so material below the preview window is effectively invisible.
- **Keep bundle references one level deep from SKILL.md.** The anti-pattern is a *chain* — SKILL.md
  points at A, A points at B, and B holds the answer — because partial reads of A can drop the
  pointer to B. Sibling cross-links between bundle files are fine as long as every file is also
  linked directly from SKILL.md; this repo's link checker already requires that direct link, so the
  depth-1 discovery path is enforced rather than assumed.
- **Descriptions are third person.** The description is injected into the system prompt; "I can help
  you…" or "You can use this to…" causes discovery problems. Quoted *user* phrasings inside a
  `Triggers:` list are not first person and are correct as-is.
- **Names are noun phrases or gerunds** (`processing-pdfs`, `pdf-processing`), never vague
  (`helper`, `utils`, `tools`, `data`).
- **Forward slashes in every path**, even for Windows readers; a backslash path errors on Unix.
- **Fully qualified MCP tool names in prose** — `ServerName:tool_name`. A bare tool name may not
  resolve when several MCP servers are present. (Agent `tools:` frontmatter uses the different
  `mcp__<server>__<tool>` form — see the Agents table above.)
- **No time-sensitive prose.** Don't write "before August 2026, use X." Put superseded guidance under
  an "old patterns" heading, or date-stamp the fact the way this file does.
- **Build evaluations before writing extensive instructions** — measure the gap without the skill
  first, so the content answers a real failure instead of an imagined one.

### Why a skill may not link outside its own folder

[doc-checked 2026-08-05] A skill is distributed as a **self-contained folder** and is installed
per-surface: uploaded as a zip on claude.ai, uploaded separately through the API, placed on the
filesystem for Claude Code, or shipped inside a plugin. Custom skills explicitly do **not** sync
across surfaces. So a relative link that escapes the skill directory resolves on the authoring
machine and breaks the moment that folder is zipped, uploaded, or installed alone — the failure is
silent, because nothing checks it at load time. This is the contract the repo's link checker
enforces, and it is why shared prose is duplicated between skills rather than factored into a
common file.

Composition is expressed at the **invocation** layer instead: an agent (or a user) combines skills
for a multi-step task, and each skill stays an independently shippable unit. The dependency graph
lives in descriptions and routing, never in filesystem links between skill folders.

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
