# Research & provenance

Why the fleet is built the way it is, with sources. Current as of **2026-07-31**. Formats and product
names move fast — re-verify load-bearing specifics (and label anything you can't confirm "unverified",
per the `researcher` agent's rules).

## Format & portability (the foundation)
| Claim | Source |
|---|---|
| Claude plugins keep `.claude-plugin/plugin.json` in the manifest directory and components (`agents/`, `skills/`, `commands/`, `hooks/`) at plugin root | https://code.claude.com/docs/en/plugins-reference |
| Plugin-shipped agents ignore `hooks`, `mcpServers`, and `permissionMode`; session hooks must self-scope | https://code.claude.com/docs/en/plugins-reference |
| **Agent Skills** open standard (`SKILL.md`): `name` ≤64 lowercase-hyphen + matches dir, `description` ≤1024; `scripts/`,`references/`,`assets/`; progressive disclosure | https://agentskills.io/specification |
| Published by Anthropic **2025-12-18**, adopted across 30+ tools | https://agentskills.io , https://github.blog/changelog/2025-12-18-github-copilot-now-supports-agent-skills/ |
| GitHub Copilot CLI plugins use root `plugin.json` and may declare native `agents`, `skills`, and `hooks` paths | https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference |
| VS Code agent plugins detect both Copilot and Claude plugin layouts, but their hook locations and agent tool vocabularies differ | https://code.visualstudio.com/docs/agent-customization/agent-plugins |
| Codex plugins require `.codex-plugin/plugin.json`; custom agents are standalone TOML in `.codex/agents`, not a claimed plugin component | https://developers.openai.com/plugins/build/plugins |
| `AGENTS.md` cross-tool project-guide standard | https://agents.md |
| Claude Code `CLAUDE.md` imports other files with `@path` (recommended: `@AGENTS.md`) | https://code.claude.com/docs/en/memory |
| `PreToolUse` hooks: subagent-frontmatter `hooks:` form; block via exit-2 or `permissionDecision:"deny"` JSON; stdin gives `tool_input.command` | https://code.claude.com/docs/en/hooks |

**Implication:** author canonical Claude plugin sources once, then generate host-native projections.
Raw cross-host copies look portable but silently misstate tool and hook enforcement.

## Knowledge sources (broader grounding)
`anthropics/anthropic-cookbook` (agent/skill/eval patterns) · `ComposioHQ/awesome-claude-skills`
(community skills) · `affaan-m/ecc` (harness-native operator system; skill-first + per-language rules +
cross-harness adapters).

## Fleet adoption provenance (2026-07-17)

| Fact | Source |
|---|---|
| Fleet content adopted from the codex/cleanup implementation of the 2026-07-13 redesign | docs/superpowers/specs/2026-07-17-claude-fleet-adoption-design.md |
| Original sister-repo state grafted | latent-sre/sde-agents @ ac2e222 |
| Multi-platform plugin migration and selective reference/validator patterns reviewed | latent-sre/sde-agents @ d50eda62c4fec083f5a5b0b3980f845d7ae0d8a1 |
| Frontmatter `hooks:` fire on project-scope agents, silently ignored on plugin agents (probed) | scripts/readonly-guard.py docstring |
| `tools: Bash(...)` specifiers are inert on agents; real only in settings permission rules (probed) | scripts/readonly-guard.py docstring |
| `Agent(target)` type lists bind main-thread agents only; ignored at subagent depth | skills/agent-authoring/references/claude-code-frontmatter.md |
