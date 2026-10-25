# Copilot & VS Code frontmatter — agents & skills

Check documented fields against the installed host after upgrades. Record version/evidence on
disagreement; `RELEASE-001` owns host verification. A supported header is not proof of enforcement.

## Agents

VS Code loads agent `.md` files from `.github/agents/` in a workspace and from
`com.github.copilot/agents/` in an Agent Plugins 1.0 plugin; the fleet emits the same
`<name>.agent.md` to both. Unsupported keys are **ignored, not rejected**.

| Field | Disposition here |
|---|---|
| `name`, `description` | Both emitted. `name` is optional (VS Code falls back to the file name; GitHub marks it optional); `description` is the trigger and the chat-input placeholder |
| `tools` | Tool or tool-set names — aliases below. Emitted, mapped from the Claude grant |
| `agents` | Agent names available as subagents; `*` allows all, `[]` prevents any. Emitted from the canonical `Agent(...)` grant. It scopes discovery on the observed host; deterministic invocation and nested-edge enforcement stay unverified until `RELEASE-001` observes a real allowed and forbidden call on the exact build |
| `handoffs` | Human-selected ownership transfer — **VS Code only**; explicitly *"not supported for Copilot cloud agent on GitHub.com"*. Emitted for the six lanes in `COPILOT_HANDOFFS_BY_SOURCE`, independently of `Agent(...)` grants. A handoff is a user-selected context transition, not a subagent call, approval, or delegation authority; every write-capable receiver re-checks approval and target binding, and `researcher` is never a target because handoffs carry conversation context. Neither `agents:` nor `handoffs:` is a sandbox |
| `argument-hint` | **VS Code only**; unsupported on Copilot cloud alongside `handoffs`. Not emitted on agents; the fleet uses it on all skills |
| `model` | Single model name; VS Code also accepts a prioritized array. Unused; Claude generation aliases are not Copilot model display names |
| `user-invocable` | Boolean, default `true`; `false` hides the agent from the chat dropdown. Unused — every fleet lane is meant to be reachable by the human SRE |
| `disable-model-invocation` | Boolean, default `false`. In VS Code it prevents the agent being invoked **as a subagent by other agents**; on GitHub it stops Copilot cloud agent from selecting the agent automatically. Unused on agents; enforcement remains unverified |
| `target` | `vscode` or `github-copilot`. Only the exported SRE command profile sets `vscode`; standard projections leave it unset |
| `mcp-servers` | MCP server config JSON for Copilot targets. Unused pending host verification — `researcher`'s exact Claude MCP grants collapse to bare `web`, so the cited-research lane is materially weaker here than on Claude |
| `hooks` | Agent-scoped hooks; the loader requires `chat.useHooks`, workspace trust, and permitted hook sources. Do not prescribe the older `chat.useCustomAgentHooks` setting. Emitted only in the separately exported SRE command profile; global `hooks/copilot-hooks.json` stays empty |
| `metadata` | GitHub only; not used by VS Code or other IDE custom agents. Unused |
| `infer` | **Retired** — replaced by `user-invocable` and `disable-model-invocation`. Never emit |

Claude grants use full plugin names (`Agent(save-toolkit:reviewer)`); the generator projects the
same targets to bare Copilot names, removing only this plugin's namespace without widening the target set. The `AGENTS.md` roster owns the edge list.

## Handoff entries

VS Code only; entries in `handoffs`:

| Field | Disposition here |
|---|---|
| `label` | Display text on the handoff button. Emitted |
| `agent` | Target agent identifier to switch to. Emitted |
| `prompt` | Prompt text sent to the target. Emitted |
| `send` | Boolean, default `false`; `true` auto-submits so one click starts the receiver. Emitted `true` |
| `model` | Optional model for the handoff, formatted `Model Name (vendor)`. Unused — follows the unpinned agent-model policy above |

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
| `web` | `WebFetch`, `WebSearch` | yes — VS Code only; not applicable on Copilot cloud agent |
| `agent` | `Agent` | yes |
| `todo` | `TodoWrite` | yes — builders and the reviewer for bounded investigation. VS Code provisions it; the cloud coding agent does not. `TodoWrite` itself is disabled by default on Claude Code and stays only as this mapping's source |

`EnterWorktree` / `ExitWorktree` have **no Copilot alias** and are deliberately unmapped — the
projection drops them rather than substituting `execute`, which would widen authority on a host
that cannot narrow it again. Which Copilot tools each fleet agent receives, and why, is maintainer
detail in the Save Toolkit repository's `docs/copilot-projection.md`.

## Skills

Copilot discovers workspace skills from `.github/skills`, `.claude/skills`, and `.agents/skills`,
and personal skills from `~/.copilot/skills`, `~/.claude/skills`, and `~/.agents/skills`. This fleet's
workspace projection lives at `.github/skills/`; the installed plugin reads canonical `skills/`
under Agent Plugins 1.0. Installed plugin skills keep their `save-toolkit:` names; the `.github/` workspace copies use bare
names.

The [VS Code skill header reference](https://code.visualstudio.com/docs/agent-customization/agent-skills#_header-required)
documents invocation behavior; the [Agent Skills specification](https://agentskills.io/specification)
defines portable metadata. Verify installed-plugin discovery separately.

| Field | Disposition here |
|---|---|
| `name` | Required; 1–64 lowercase letters, digits, or hyphens; no leading, trailing, or consecutive hyphens. Must match the parent directory. Emitted on all skills; leave plugin namespacing to the host |
| `description` | Required; what the skill does and when to use it, at most 1,024 characters. Emitted; the fleet enforces the same character limit |
| `argument-hint` | Emitted on all skills; ignored on Copilot cloud |
| `user-invocable` | Optional, default `true`. `false` hides the skill from the slash-command menu while allowing automatic loading. Unused — keep every fleet skill reachable by the human |
| `disable-model-invocation` | Optional, default `false`. `true` disables automatic loading; used by `pcf-deploy` for manual-only invocation. Setting this to `true` together with `user-invocable: false` disables both entry paths |
| `context` | **Experimental**, unused; no current adoption requirement. Default is inline; `fork` runs the skill in a dedicated subagent context and returns only its final result to the parent. Requires `github.copilot.chat.skillTool.enabled`; adopt only after a bounded host check of the skill's ownership and evidence-return contract |
| `compatibility` | Optional portable metadata, 1–500 characters describing environment requirements. Used for host and access prerequisites (for example `pcf-deploy`); descriptive, not an access check |
| `metadata` | Optional portable string-to-string mapping. Unused |
| `license` | Optional. Unused; the plugin manifest carries MIT |
| `allowed-tools` | Experimental in the portable specification: a space-separated list of pre-approved tools, with implementation-dependent support. VS Code's skill-header table does not document it; Copilot enforcement is unverified. Fleet policy avoids tool preapproval: **do not use**; do not treat it as a restricting allowlist |

Hook entry shape, PreToolUse decisions, launcher behavior, and manifest format detection are host
contract for the guard and generator, not authoring frontmatter; they live in the Save Toolkit
repository's `docs/vscode-plugin-acceptance.md`.
