# Copilot & VS Code frontmatter — agents & skills

The fleet's single source of truth for VS Code / GitHub Copilot frontmatter facts. Check live docs
and the installed host; when they disagree, record the version and evidence instead of assuming
the documented field is enforced. Re-verify after host upgrades.

Facts below are **doc-checked (2026-09-09; Skills refreshed 2026-09-10)**. Hook loading and failure
handling were inspected in installed VS Code 1.138.0 / bundled Copilot Chat 0.66.0 on 2026-09-19;
that is source evidence, not a live invocation test. `RELEASE-001` owns installed-host
verification; treat a key's presence here as permission to author, never as proof it enforces.

## Contents

- Agents
- Handoff entries
- Tool aliases
- Skills
- Hook events and shape
- Plugin manifest formats
- Fleet decisions on unused fields

## Agents

VS Code loads agent `.md` files from `.github/agents/` in a workspace and from
`com.github.copilot/agents/` in an Agent Plugins 1.0 plugin; the fleet emits the same
`<name>.agent.md` to both. A key the host does not support is **ignored, not rejected**, which is
why one file serves both targets.

| Field | Disposition here |
|---|---|
| `name`, `description` | Both emitted. `name` is optional (VS Code falls back to the file name; GitHub marks it optional); `description` is the trigger and the chat-input placeholder |
| `tools` | Tool or tool-set names — aliases below. Emitted, mapped from the Claude grant |
| `agents` | Agent names available as subagents; `*` allows all, `[]` prevents any. Emitted from the same `Agent(...)` grant that feeds the delegation graph |
| `handoffs` | Human-selected ownership transfer — **VS Code only**; explicitly *"not supported for Copilot cloud agent on GitHub.com"*. Emitted for the five lanes in `COPILOT_HANDOFFS_BY_SOURCE` |
| `argument-hint` | **VS Code only**; unsupported on Copilot cloud alongside `handoffs`. Not emitted on agents; the fleet uses it on all skills |
| `model` | Single model name or a prioritized array. Unused — mirrors the Claude side, where no agent pins one |
| `user-invocable` | Boolean, default `true`; `false` hides the agent from the chat dropdown. Unused — every fleet lane is meant to be reachable by the human SRE |
| `disable-model-invocation` | Boolean, default `false`. In VS Code it prevents the agent being invoked **as a subagent by other agents**; on GitHub it stops Copilot cloud agent from selecting the agent automatically. Unused on agents today, and the one host key that could turn the delegation graph's inbound edges into enforcement rather than documented intent |
| `target` | `vscode` or `github-copilot`. Only the exported SRE command profile sets `vscode`; standard projections leave it unset |
| `mcp-servers` | MCP server config JSON for Copilot targets. Unused — `researcher`'s exact Claude MCP grants collapse to bare `web`, so the cited-research lane is materially weaker here than on Claude |
| `hooks` | Agent-scoped hooks; the installed 1.138.0 loader requires `chat.useHooks`, workspace trust, and permitted hook sources. The older `chat.useCustomAgentHooks` setting is absent in that build. Emitted only in the separately exported SRE command profile; global `hooks/copilot-hooks.json` stays empty |
| `metadata` | GitHub only; not used by VS Code or other IDE custom agents. Unused |
| `infer` | **Retired** — replaced by `user-invocable` and `disable-model-invocation`. Never emit |

Claude grants use full plugin names (`Agent(reviewer)`); the generator projects the
same targets to bare Copilot names. The delegation-graph reference owns the edge list.

## Handoff entries

Each entry in `handoffs`. VS Code only — the whole key is inert on Copilot cloud.

| Field | Disposition here |
|---|---|
| `label` | Display text on the handoff button. Emitted |
| `agent` | Target agent identifier to switch to. Emitted |
| `prompt` | Prompt text sent to the target. Emitted |
| `send` | Boolean, default `false`; `true` auto-submits so one click starts the receiver. Emitted `true` |
| `model` | Optional model for the handoff, formatted `Model Name (vendor)`. Unused — consistent with pinning no model anywhere |

## Tool aliases

Valid Copilot values: the seven aliases below, plus `<server>/<tool>` for a specific MCP tool,
`<server>/*` for a whole server, `["*"]` for everything, and `[]` to disable all tools. `github/*`
and `playwright/*` ship out of the box.

| Alias | Claude tools mapped to it | Used |
|---|---|---|
| `read` | `Read` | yes |
| `search` | `Grep`, `Glob` | yes |
| `edit` | `Write`, `Edit`, `NotebookEdit` | yes |
| `execute` | `Bash`, `PowerShell` | yes |
| `web` | `WebFetch`, `WebSearch` | yes — VS Code only; not applicable on Copilot cloud agent [sourced: docs.github.com custom-agents-configuration] |
| `agent` | `Agent` | yes |
| `todo` | `TodoWrite` | yes — builders and the reviewer for bounded investigation. VS Code provisions it [verified by the owner 2026-09-13]; the cloud coding agent does not [sourced: docs.github.com custom-agents-configuration]. `TodoWrite` itself is inert on Claude Code 2.1.268+ and stays only as this mapping's source |

`EnterWorktree` / `ExitWorktree` have **no Copilot alias** and are deliberately unmapped — the
projection drops them rather than substituting `execute`, which would widen authority on a host
that cannot narrow it again.

`sre-assistant` deliberately receives **no** `execute` in the standard projection. Its Claude profile
uses a session-wide Bash/PowerShell guard; acceptance of the VS Code agent-scoped equivalent has
not been established, so the default retains tool absence.

The standard projection also withholds individual terminal tools. A separately exported VS Code
command preview grants only `execute/runInTerminal` and `execute/getTerminalOutput`, sets
`target: vscode`, and adds agent-scoped hooks with Windows/POSIX launchers. It is not an accepted
replacement without a human decision on its best-effort guard and installed-host evidence.
The preview's explicit `--copilot` guard mode uses agent-hook scoping, not Claude's `agent_type`.

### Capability choices

| Lane | Current Copilot capability and reason |
|---|---|
| `software-engineer`, `agent-engineer` | Read/search/edit/execute, scoped delegation, and todo; already able to build and test with the host's shell |
| `observability-engineer` | The same capability groups; already able to query Grafana through commands without a Grafana MCP, under its existing change authority |
| `reviewer` | Read/search/edit/execute, evidence helpers, and todo; execution stays in its established verification environment |
| `sre-assistant` | Read/search, researcher delegation, and selected native/MCP browser viewing interactions under read-only session controls; the command preview adds only terminal execution/output for reviewed reads |
| `repository-investigator`, `scribe` | File investigation or document edits; shell execution is outside their assignments |
| `researcher` | Public web access; no local files or shell. Adding exact Context7/GitHits tools needs the target host's registered tool IDs, not wildcard MCP grants. On Copilot cloud agent `web` does not apply, so researcher has no working tool there; route cited research through VS Code or Claude |

Do not broaden `execute` or use `tools: ["*"]` merely to fix a missing interpreter, credential,
or hook path. Copilot's execution tools use the configured terminal; a separate Claude PowerShell
grant is not needed to run PowerShell through Copilot. Tool presence permits execution, not
production changes or access beyond the human's assignment.

Browser investigation grants are exclusive to the SRE lane. The generator derives native VS Code
`openBrowserPage`, `navigatePage`, `readPage`, `screenshotPage`, `clickElement`, `hoverElement` and
`typeInPage` from the corresponding exact canonical Playwright capabilities. These native names
were checked against upstream `browserChatToolReferenceNames.ts` on 2026-09-21; installed-host
availability still needs verification. There is no wildcard, dialog, upload or page-code grant.
MCP still needs a registered server; native VS Code uses a shared integrated-browser page.
Neither frontmatter nor a viewing-only prompt enforces read-only account rights, secret masking,
origin confinement or image delivery. The Grafana visual reference owns those prerequisites.

## Skills

Copilot discovers workspace skills from `.github/skills`, `.claude/skills`, and `.agents/skills`,
and personal skills from `~/.copilot/skills`, `~/.claude/skills`, and `~/.agents/skills`. This fleet's
workspace projection lives at `.github/skills/`; the installed plugin reads canonical `skills/`
under Agent Plugins 1.0. The directory is tracked and regenerated from canonical `skills/`.
The former `platforms/copilot/skills/` root is retired. The custom `chat.agentSkillsLocations`
override is removed; the [current discovery docs](https://code.visualstudio.com/docs/agent-customization/agent-skills#_create-a-skill)
deprecate it in favor of supported directories.

The [VS Code skill header reference](https://code.visualstudio.com/docs/agent-customization/agent-skills#_header-required)
documents invocation behavior; the [Agent Skills specification](https://agentskills.io/specification)
defines portable metadata. Both were checked against the current docs on 2026-09-10, with VS Code
1.137.0 installed. A valid header does not prove installed-plugin discovery or runtime enforcement.

| Field | Disposition here |
|---|---|
| `name` | Required; 1–64 lowercase letters, digits, or hyphens; no leading, trailing, or consecutive hyphens. Must match the parent directory. Emitted on all skills; leave plugin namespacing to the host |
| `description` | Required; what the skill does and when to use it, at most 1,024 characters. Emitted; the fleet enforces the same character limit |
| `argument-hint` | Emitted on all skills; ignored on Copilot cloud |
| `user-invocable` | Optional, default `true`. `false` hides the skill from the slash-command menu while allowing automatic loading. Unused — keep every fleet skill reachable by the human |
| `disable-model-invocation` | Optional, default `false`. `true` disables automatic loading; used by `pcf-deploy` for manual-only invocation. Setting this to `true` together with `user-invocable: false` disables both entry paths |
| `context` | **Experimental**, unused. Default is inline; `fork` runs the skill in a dedicated subagent context and returns only its final result to the parent. Requires `github.copilot.chat.skillTool.enabled`; adopt only after a bounded host check of the skill's ownership and evidence-return contract |
| `compatibility` | Optional portable metadata, 1–500 characters describing environment requirements. Used by `akamai-edge`, `gcp-ops`, `pcf-ops`, and `pcf-deploy`; descriptive, not an access check |
| `metadata` | Optional portable string-to-string mapping. Unused; no fleet requirement for per-skill author/version metadata |
| `license` | Optional. Unused — the plugin manifest already carries MIT, and the field would repeat across every projected bundle |
| `allowed-tools` | Experimental in the portable specification: a space-separated list of pre-approved tools, with implementation-dependent support. VS Code's skill-header table does not document it; Copilot enforcement is unverified. Fleet policy remains **do not use**; do not treat it as a restricting allowlist |

## Hook events and shape

The SRE command profile uses `PreToolUse`; the standard projection has no hooks. The decision
payload is compatible with what `readonly-guard.py` emits for Claude.

| Event | Claude equivalent |
|---|---|
| `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `Stop` | same names |
| `SubagentStart`, `SubagentStop` | also supported by Claude; payload and scoping need host-specific checks |

A hook entry declares `type: "command"` and at least one of `command`, `windows`, `linux`, or
`osx`; an OS-specific command overrides the default. `timeout` (seconds, default 30), `cwd`, and
`env` are optional. See the [hook reference](https://code.visualstudio.com/docs/agents/reference/hooks-reference).

`PreToolUse` returns `hookSpecificOutput.permissionDecision` — `allow` \| `deny` \| `ask` — with
`permissionDecisionReason`. The launcher translates the guard's 42/43/44 protocol into host JSON;
those codes distinguish a responding guard from an ordinary interpreter failure, but do not
authenticate an executable against a malicious PATH replacement. `--copilot` relies on attachment
to the SRE agent, not Claude's `agent_type`; never register that mode globally.

**[verified, installed source 2026-09-19]** VS Code 1.138.0 registers `chat.useHooks` with default
`true`; effective settings and organization policy can disable or restrict it. Its agent loader
also checks workspace trust. The older opt-in setting still appears in retrieved documentation;
do not prescribe it for 1.138.0. Plugin delivery separately requires enabled plugin support and
an enabled plugin. `chat.useClaudeHooks` concerns Claude hook files, not this VS Code agent profile.

The installed agent-frontmatter parser does not perform plugin-hook `${CLAUDE_PLUGIN_ROOT}`
substitution. Export the command profile on the execution host: its hook `env` binds
`SAVE_TOOLKIT_GUARD_DIR` to the exporting installation's absolute scripts path. Re-export after
moving that installation or changing host; do not commit that machine-specific profile.
The inspected Windows hook executor selects PowerShell; its command uses `$env:` expansion.
The POSIX command uses a quoted shell variable, and each launcher resolves the guard beside itself.

**[verified, installed source; live behavior unverified]** Explicit `deny` and exit 2 block
PreToolUse. Other nonzero exits and launch exceptions are warnings; timeouts are not guaranteed
to block. Exit 0 with invalid JSON provides no permission decision. The launcher denies invalid
guard responses once it runs, but cannot enforce anything when it never starts. This is a
best-effort command check, not a fail-closed sandbox. Read-only service credentials and the OS
identity remain the effective bounds on live access; a canary is repository acceptance evidence,
not a VS Code prerequisite.

## Plugin manifest formats

VS Code detects the format in this order: a root `plugin.json` declaring the Agent Plugins 1.0
`$schema`; then `.claude-plugin/plugin.json` (Claude format); then `.plugin/plugin.json`; then a
root `plugin.json` without a schema (Copilot selector format). *[verified:
code.visualstudio.com/docs/agent-customization/agent-plugins, 2026-09-23]* A repository that ships
`.claude-plugin/plugin.json` and a schema-less root manifest is therefore loaded as a Claude plugin:
canonical agents and hooks, not the Copilot projection.

| Format | Shape | Status |
|---|---|---|
| Agent Plugins 1.0 | Root `plugin.json` with `$schema: https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` and metadata only (the schema forbids other top-level keys); skills from `skills/`, MCP from `mcp.json`, Copilot-specific agents, commands, rules and `hooks/hooks.json` under `com.github.copilot/`. **What this fleet ships** | Published 2026-08-12; Copilot CLI discovers `com.github.copilot/agents/` from v1.0.85 |
| Copilot (selector) | Root `plugin.json` naming component paths — `agents`, `skills`, `hooks` | Supported, but outranked by `.claude-plugin/plugin.json` |

`generate_platform_adapters.py` requires the 1.0 `$schema`, rejects any other top-level manifest
key, writes the projected agents to `com.github.copilot/agents/`, and copies
`hooks/copilot-hooks.json` to `com.github.copilot/hooks/hooks.json`. The plugin reads canonical
`skills/`, so plugin skills keep their `save-toolkit:` names; the `.github/` copies are workspace
customizations for this repository and keep the bare-name rewrite.

## Fleet decisions on unused fields

| Field | Why unused |
|---|---|
| `model`, handoff `model` | No lane pins a model on any host; a dated pin goes stale silently |
| `user-invocable` | The fleet serves a human SRE; keep agents in the picker and skills in the slash-command menu through the default `true` |
| `target` | Unset for standard projections; the locally exported command profile targets VS Code explicitly |
| `license` | Redundant with the manifest, multiplied across every projected bundle |
| `infer` | Deprecated upstream |
| Skill `context`, `metadata` | No current adoption requirement; forked execution needs a bounded host check before changing a skill's execution model |
| `allowed-tools` | Fleet policy avoids tool preapproval; Copilot support is not established by the portable specification |
| Agent `hooks`, `mcp-servers`, `disable-model-invocation` | Hooks appear only in the SRE command export; MCP mapping and agent invocation flags remain unadopted pending host verification. The skill invocation flag is already used by `pcf-deploy` |
