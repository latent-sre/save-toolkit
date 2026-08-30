# ADR: Canonical Claude plugin with generated host adapters

- Date: 2026-07-31
- Status: Accepted
- Decision owners: save-toolkit maintainers
- Sister-lab input: `latent-sre/sde-agents@d50eda62c4fec083f5a5b0b3980f845d7ae0d8a1`

## Context

The fleet was directly edited under `.claude/` and relied on project-scope agent hooks. The requested
distribution model is a plugin shared across Claude Code, GitHub Copilot/VS Code, and Codex. Those
hosts do not share agent frontmatter, component namespace, hook payloads, or per-agent enforcement.
A raw directory mirror would therefore preserve text while silently changing authority.

The migration also exposed a load-bearing platform fact: Claude ignores `hooks`, `mcpServers`, and
`permissionMode` on plugin-shipped agents. Keeping the old hooks in agent frontmatter would present a
guard that never runs.

## Decision

1. `agents/`, `skills/`, and `commands/` are canonical authored source.
2. Claude loads those sources directly through `.claude-plugin/plugin.json`; guarded Bash is enforced
   by a plugin-level `hooks/hooks.json` that self-scopes to exact agent identities.
3. `scripts/generate_platform_adapters.py` transactionally generates and byte-checks:
   `.github/agents/`, `.codex/agents/`, `platforms/copilot/skills/`, and
   `plugins/save-toolkit/skills/`.
   (Post-decision: the plugin id was later renamed from `sre-agents` to `save-toolkit`; see
   [`2026-08-05-save-toolkit-rename.md`](2026-08-05-save-toolkit-rename.md). Codex distribution
   projections were later retired; remaining generated roots are `.github/agents/` and
   `platforms/copilot/skills/` — see
   [`2026-08-23-retire-codex-distribution-target.md`](2026-08-23-retire-codex-distribution-target.md).)
4. Copilot/VS Code guarded roles receive no execute tool because their plugin contract cannot enforce
   Claude's agent-specific command allowlist.
5. Codex agents are standalone TOML, not a claimed plugin component. They request sandbox mode from
   canonical write authority and disclose that parent permissions and inherited tools can be wider.
   A conflict-safe installer is explicit and never overwrites unmanaged roles.
6. Side-effect-shaped skills use host-native invocation policy. Copilot frontmatter and Codex
   `agents/openai.yaml` make the generated copies explicit-only. Claude's
   `disable-model-invocation: true` expresses invocation intent but is not treated as the
   load-bearing safety boundary; the skill body, human approval gates, and outer permissions remain
   authoritative.
7. Generated drift, manifest parity, hook wiring, authority, exact MCP grants, and installer collision
   behavior are structural gates.
8. The root `plugin.json` deliberately remains in the supported Copilot plugin format. Current VS
   Code [auto-detects the plugin format](https://code.visualstudio.com/docs/agent-customization/agent-plugins#_plugin-formats):
   adding the Agent Plugins 1.0 `$schema` changes discovery semantics rather than adding inert
   validation metadata. Agent Plugins 1.0 would require portable skills under root `skills/` and
   Copilot-specific agents and hooks under `com.github.copilot/`; this fleet instead selects its
   generated `.github/agents/`, `platforms/copilot/skills/`, and Copilot hook file explicitly.
   `validate_platform_contracts` rejects a mixed-format manifest. A future Agent Plugins migration
   must move every producer and consumer together rather than changing the schema alone.

## Alternatives considered

- **Keep `.claude/` project scope:** strongest match to the old guard, but does not satisfy plugin
  distribution and duplicates installation conventions.
- **Copy Claude files unchanged to every host:** rejected; it creates false tool/hook controls and
  host-incompatible invocation syntax.
- **Maintain four authored fleets:** rejected; semantic and security drift becomes inevitable.
- **Use symlinks:** rejected for Windows portability, packaging behavior, and link/reparse attack
  surface.

## Consequences

- Claude remains the richest enforceable agent contract. Other adapters are intentionally narrower or
  explicitly cooperative where the host lacks equivalent controls.
- Every canonical change creates a larger generated diff; generated markers and linguist attributes
  keep review focused on source.
- VS Code beta installs can use **Chat: Install Plugin From Source** or an isolated local
  `chat.pluginLocations` entry. Opening this repository as the workspace is a separate projection
  smoke path, not proof that plugin installation works.
- Plugin/CLI upgrades must rerun the host validators and the manual runtime probe before their pins or
  contract claims change.

## Rollback

Before release, rollback is a normal revert of this migration. After release, preserve the canonical
root sources, remove marketplace publication references, and temporarily distribute Claude with
`--plugin-dir` while host adapters are repaired. Never restore per-agent plugin hooks as a substitute
for the session hook; that would silently disarm guarded Bash.
