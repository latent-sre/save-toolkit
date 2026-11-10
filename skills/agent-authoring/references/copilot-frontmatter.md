# Copilot & VS Code frontmatter — agents & skills

Check the [agent field reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference)
against the installed host after upgrades. Record version/evidence on
disagreement; `RELEASE-001` owns host verification. A supported header is not proof of enforcement.

## Contents

- Agents
- Tool aliases
- Skills

## Agents

VS Code loads agent `.md` files from `.github/agents/` in a workspace and from
`com.github.copilot/agents/` in an Agent Plugins 1.0 plugin; the fleet emits the same
`<name>.agent.md` to both. Local VS Code, the VS Code Copilot harness, Copilot CLI (its own field
set), and GitHub's cloud agent have different field contracts. **The emitted `agents:` and `handoffs:`
work only on VS Code's Local harness, which VS Code calls legacy;** the Copilot harness, the default
for new sessions, accepts neither, so the subagent allowlist and handoff buttons do not apply there. An omitted `target` follows the selected editor harness, not
necessarily Local. Unsupported attributes receive editor hints; malformed supported values can
still be errors. Schema acceptance does not establish runtime enforcement.

| Field | Disposition here |
|---|---|
| `name`, `description` | Both emitted. `name` is optional (VS Code falls back to the file name; GitHub marks it optional); `description` is the trigger |
| `tools` | Tool names — aliases below. Emitted, mapped from the Claude grant |
| `agents` | **Local VS Code** subagent names; `*` allows all, `[]` prevents any. Emitted from the canonical `Agent(...)` grant. The Copilot-harness converter does not forward it; cloud enforcement is not documented. With `chat.subagents.allowInvocationsFromSubagents` off (the default), a lane running as a Local subagent cannot use its `agents:` edge. Local discovery scoping is not proof of deterministic invocation or nested-edge enforcement; `RELEASE-001` owns those host checks |
| `handoffs` | Human-selected ownership transfer — **Local VS Code only**; ignored on GitHub cloud and not forwarded by the VS Code Copilot converter. Emitted for the six lanes in `COPILOT_HANDOFFS_BY_SOURCE`, independently of `Agent(...)` grants. A handoff is a user-selected context transition, not a subagent call, approval, or delegation authority; every write-capable receiver re-checks approval and target binding, and `researcher` is never a target because handoffs carry conversation context. Neither `agents:` nor `handoffs:` is a sandbox. Each entry emits `label`, `agent`, `prompt`, and `send: true`; the optional per-handoff `model` is unused |
| `argument-hint` | Not emitted on agents; the fleet uses it on skills |
| `model` | Unused; Claude generation aliases are not Copilot model display names |
| `user-invocable` | Unused — every fleet lane is meant to be reachable by the human SRE |
| `disable-model-invocation` | Boolean, default `false`. Local VS Code excludes the agent from automatic subagent selection, but a caller's explicit `agents` list can override it; GitHub cloud uses it to prevent automatic selection. Unused on agents; do not treat it as an access boundary |
| `target` | `vscode` or `github-copilot`. In VS Code, affects editor interpretation, not which harness executes; GitHub documents it as the target environment (unset means both). Only the exported SRE command profile sets `vscode`; standard projections leave it unset. The Copilot converter does not forward it |
| `mcp-servers` | Unused — exact Claude MCP grants collapse to bare `web`, so the research lane requires separate host verification |
| `hooks` | Local agent-scoped hooks require `chat.useHooks`, workspace trust, and permitted hook sources. The Copilot harness forwards hooks separately, without that Local setting as its gate. Emitted only in the exported SRE command profile; global `hooks/copilot-hooks.json` stays empty |
| `infer` | **Retired** — replaced by `user-invocable` and `disable-model-invocation`. Never emit |

On Copilot CLI, a custom agent run as a subagent receives no `AGENTS.md` unless
`include-custom-instructions: true`; VS Code does not forward that field, and the same default there
is inferred from the shared runtime. A lane body must carry every rule it relies on.

Claude grants use full plugin names (`Agent(save-toolkit:reviewer)`); the generator projects the
same targets to bare Copilot names, removing only this plugin's namespace without widening the target set. The `README.md` roster owns the edge list.

## Tool aliases

Tool names include the seven aliases below and `<server>/<tool>` for a specific MCP tool.
`<server>/*` selects a whole server and `*` everything; on GitHub cloud `[]` means no tools;
`github/*` and `playwright/*` are built in there. An empty tools array is not portable: upstream
VS Code Copilot conversion maps both an empty and missing list to `null` (all tools). Keep explicit,
nonempty grants and verify actual host provisioning before claiming tool absence.

`read` (`Read`), `search` (`Grep`, `Glob`), `edit` (`Write`, `Edit`, `NotebookEdit`), `execute`
(`Bash`, `PowerShell`), `web` (`WebFetch`, `WebSearch`; VS Code only, not applicable on Copilot cloud
agent), `agent` (`Agent`), and `todo` (`TodoWrite`).

`todo` goes to builders and the reviewer for bounded investigation; VS Code provisions it and the
cloud coding agent does not.

`EnterWorktree` / `ExitWorktree` have **no Copilot alias** and are deliberately unmapped — the
projection drops them rather than substituting `execute`, which would widen authority on a host
that cannot narrow it again. Which Copilot tools each fleet agent receives, and why, is maintainer
detail in the Save Toolkit repository's `docs/copilot-projection.md`.

## Skills

This fleet's workspace projection lives at `.github/skills/`; the installed plugin reads canonical `skills/`
under Agent Plugins 1.0. Installed plugin skills keep their `save-toolkit:` names; the `.github/` workspace copies use bare
names.

The [VS Code skill header reference](https://code.visualstudio.com/docs/agent-customization/agent-skills#_header-required)
documents invocation behavior; the [Agent Skills specification](https://agentskills.io/specification)
defines portable metadata. Verify installed-plugin discovery separately.

Every fleet skill emits `name` (leave plugin namespacing to the host), `description` (at most 1,024
characters), and `argument-hint` (ignored on Copilot cloud). `compatibility` carries host and access
prerequisites (for example `pcf-deploy`) and is descriptive, not an access check. `user-invocable`
stays unset so every fleet skill is reachable by the human. Experimental `context` is unused; adopt it only after a bounded host
check of the skill's ownership and evidence-return contract.

| Field | Disposition here |
|---|---|
| `disable-model-invocation` | Optional, default `false`. `true` disables automatic loading; used by `pcf-deploy` for manual-only invocation. Setting this to `true` together with `user-invocable: false` disables both entry paths |
| `allowed-tools` | Experimental in the portable specification: a space-separated list of pre-approved tools, with implementation-dependent support. Copilot CLI documents it as tool pre-approval; VS Code's skill-header table does not document it, and enforcement on an installed host is unverified. Fleet policy avoids tool preapproval: **do not use**; do not treat it as a restricting allowlist |

### Portable frontmatter

Host-specific fields may be rejected by packaging or ignored at runtime; do not assume a control
survives projection. The portable six are `name`, `description`, `license`, `compatibility`,
`metadata`, and `allowed-tools`. This fleet writes `compatibility` as one single-line scalar so the
local gate measures its 500-character limit exactly.

Outside the portable specification, which does not mean unsupported by every other host:

- `argument-hint` is used on every fleet skill; VS Code recognizes it, the portable spec does not.
- `disable-model-invocation` makes `pcf-deploy` explicit-only on Claude and VS Code; that invocation
  gate does not travel in portable metadata.
- Other nonportable fields are unused here; agent-file `disallowedTools` and `hooks` do not
  establish skill-header restrictions.

Portable `allowed-tools` preapproves tools; it does not restrict them. Ignored fields remove their
controls, and VS Code tool lists are user-overridable defaults, not an enforcement boundary.

| Host / spec | Limit | Scope |
|---|---|---|
| GitHub Copilot custom agents | 30,000 characters of Markdown below one `.agent.md` frontmatter | Per generated profile, including its host contract — not an aggregate fleet budget, not a skill-body limit; GitHub does not define "character" (code points vs UTF-16 units), so report the official contract and the counting semantics separately |
| Agent Skills specification | `description` ≤1,024 characters; `SKILL.md` recommended under 5,000 tokens and 500 lines, resources on demand | Authoring recommendations, not body validators |

Before publishing to the portable spec, strip to the portable six and preserve dropped
invocation/authority boundaries in the body. Prose remains cooperative; it does not replace a host
control lost during publication.
