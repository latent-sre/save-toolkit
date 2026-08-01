# Research & provenance

Why the fleet is built the way it is, with sources. Current as of **2026-08-01**. Formats and product
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

## Preserved internal source material (2026-08-01)

### PR #70 — native VS Code agents and skills experiment

This closed, unmerged experiment is retained as source material for future agent, skill, and
multi-platform packaging work. It is **not** the accepted fleet architecture and must not be merged
wholesale. Re-evaluate individual ideas against current `main`, the current platform contracts, and
the accepted decisions before adopting them.

| Field | Preserved value |
|---|---|
| Pull request | [`#70 — Move skills to .github/skills; remove generated agent projections`](https://github.com/latent-sre/sre-agents/pull/70) |
| Original branch | `claude/vscode-native-agents-skills-xy27mw` |
| Pinned commit | `9e9553b5d8586f916a672179e38ae72e226be852` |
| Annotated tag | `source-material/claude-vscode-native-agents-skills-2026-08-01` |
| Branch protection | [verified] Active ruleset [`20191052`](https://github.com/latent-sre/sre-agents/rules/20191052): updates, deletion, and force pushes blocked; no bypass actors |
| Tag protection | [verified] Active ruleset [`20191066`](https://github.com/latent-sre/sre-agents/rules/20191066): `source-material/*` updates, deletion, and force pushes blocked; no bypass actors |
| Retention reason | Nine commits remain unique to the closed experiment and contain potentially useful native-layout, identity, and validation patterns |

Unique commits, oldest first:

1. `14425878` — scrub build scaffolding from shipped skills and gate against recurrence.
2. `6b9bba2b` — gate the content-checker unit tests.
3. `eecea4ed` — remove the dangling stack-profile tripwire claim.
4. `f82a70c3` — move native skill authoring to `.github/skills/`.
5. `1906a4fb` — project native agents and prompts into `.github/`.
6. `93eac678` — strip cross-runtime skill IDs from per-runtime agent identities.
7. `72c7f9a1` — document the native layout and authoring exception.
8. `6a6a9c9b` — neutralize skill cross-references to one canonical identity.
9. `9e9553b5` — track the `.github/agents` projections.

Inspect without changing the current checkout:

```bash
git fetch origin tag source-material/claude-vscode-native-agents-skills-2026-08-01
git show source-material/claude-vscode-native-agents-skills-2026-08-01
git worktree add ../sre-agents-pr70-source source-material/claude-vscode-native-agents-skills-2026-08-01
```

The worktree starts detached at the immutable tag. Create a new branch from it before making any
changes; do not attempt to update either preserved ref.

## Fleet adoption provenance (2026-07-17)

| Fact | Source |
|---|---|
| Fleet content adopted from the codex/cleanup implementation of the 2026-07-13 redesign | docs/superpowers/specs/2026-07-17-claude-fleet-adoption-design.md |
| Original sister-repo state grafted | latent-sre/sde-agents @ ac2e222 |
| Multi-platform plugin migration and selective reference/validator patterns reviewed | latent-sre/sde-agents @ d50eda62c4fec083f5a5b0b3980f845d7ae0d8a1 |
| Frontmatter `hooks:` fire on project-scope agents, silently ignored on plugin agents (probed) | scripts/readonly-guard.py docstring |
| `tools: Bash(...)` specifiers are inert on agents; real only in settings permission rules (probed) | scripts/readonly-guard.py docstring |
| `Agent(target)` type lists bind main-thread agents only; ignored at subagent depth | skills/agent-authoring/references/claude-code-frontmatter.md |
