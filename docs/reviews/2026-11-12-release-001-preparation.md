# RELEASE-001 concrete preparation — 2026-11-12

[verified] RELEASE-001 remains incomplete. This packet prepares a pinned selector and exact source
artifact for review; it does not publish a release or establish installed-host acceptance.

## Prepared candidate

- Candidate commit: `020c43c53348c392ac84dfc7807f30554c0c907f` (local feature branch).
- Version declared by both plugin manifests: `0.52.0`.
- Local `marketplace.json` replaces the mutable relative source with a GitHub source whose
  `sha` is the full candidate commit. Its `ref` remains `main`; the explicit SHA selects the commit.
- [verified] Claude Code 2.1.322 strict marketplace validation reports success, zero errors and
  zero warnings. This validates the schema, not remote fetchability or runtime behavior.
- [verified] Candidate source archive SHA-256:
  `a8fca17e6bbae7a90465e8db90bf7713ecf560f70405e79a9066caa81e56f3cf`. All 167 measured native runtime files inside it equal the clean checkout's raw
  bytes, not only normalized-text digests. `artifact-receipt.json` lists their individual hashes.
- [unverified] The commit and selector are unpublished. Consumers cannot yet use this proposed
  remote selector. The shipping repository's current marketplace is still unchanged at `source: ./`.

## Selected harness requirement

[sourced] Microsoft calls Local the legacy editor-specific harness, recommends Copilot for new
workflows, and describes Local as a temporary fallback for migration blockers. No firm Local removal
date was established by the fetched documentation.
[Official migration guide](https://github.com/microsoft/vscode-docs/blob/main/docs/agents/run/move-to-copilot.md).

[sourced] The current field reference says Copilot accepts neither `agents` nor `handoffs`;
`target: vscode` changes editor interpretation and does not switch the session's harness.
[Official field contract](https://github.com/microsoft/vscode-docs/blob/main/docs/agents/reference/custom-agent-file-reference.md).
The separately fetched upstream `githubCopilotAgentAttributes` at commit `d0e3b45e` contains neither
field. This is source/schema corroboration, not installed-runtime enforcement evidence.
[Upstream source](https://github.com/microsoft/vscode/blob/d0e3b45e/src/vs/workbench/contrib/chat/common/promptSyntax/languageProviders/promptFileAttributes.ts#L193-L285).

[sourced] On 2026-11-12 the owner selected **verified native Copilot delegation before release**.
Claude Code and the default Copilot harness are the intended release targets. Scoped delegation
remains a required gate. The next work is a harness-native projection with installed observations;
Local-only fields and a Copilot profile without delegation do not satisfy that choice.

## Installed acceptance matrix to execute on frozen shipping bytes

| Case | Required observation | Current state |
|---|---|---|
| Format and identity | One plugin in an isolated profile and neutral workspace; record host, extension, harness, model and installed digest; prove the correct host projection loaded | Unrun on these bytes |
| Inventory and tools | Actual current agents, skills and ADR command appear; inspect effective tools; standard SRE has no terminal capability | Unrun |
| Helper resolution | Installed helper resolves from the plugin, even with an impostor in the neutral workspace | Structural tests exist; installed run pending |
| Allowed delegation and return | Actual allowed child completes and parent uses its result, under the owner-selected Copilot contract | Native implementation and installed proof pending |
| Forbidden delegation | Host blocks a harmless synthetic forbidden target before invocation, if the chosen contract promises scoped delegation | Not established on default Copilot |
| Human ownership transition | Chosen replacement for Local handoff buttons preserves context and rechecks authority | Native implementation and installed proof pending |
| Guard behavior | Direct and delegated SRE requests show allowed reads, denied writes, and honest launch-failure/timeout behavior; other lanes remain unaffected | SessionStart fallback repaired and locally tested; installed canary pending |
| Deploy and review boundary | Synthetic deploy sentinel remains untouched; review detects the supplied break and preserves candidate files and Git state | Installed cases pending |
| Protected visual read | SRE actually receives/inspects the correct image and window through a dedicated Viewer session; missing/wrong view and denied effects remain bounded | Unrun |
| Lifecycle | Disable, re-enable and uninstall change the installed inventory without workspace copies masking the result | Unrun |
| Rollback | Install candidate, return to a previously accepted immutable artifact, and verify identity and useful behavior | No accepted immutable baseline selected |

[sourced] The earlier 0.40.0 / VS Code 1.137.0 owner-reported pass is historical evidence in README,
without a retained transcript or immutable artifact. It cannot serve as a byte-identified rollback
baseline by assertion. The removed Local-era acceptance document must not be restored unchanged.

## Distribution and owner actions

[sourced] Claude's marketplace reference supports full 40-character lowercase `sha` values on GitHub
sources and states that `sha` selects the checkout when supplied with `ref`.
[Marketplace source reference](https://code.claude.com/docs/en/plugins/marketplace-reference).

[verified] The current GitHub release list is empty, and the immutable-release setting returns
`enabled: false`, `enforced_by_owner: false`. These are read-only observations. No repository setting,
tag, release, branch publication or user's installed profile was changed.

1. Implement and verify default-Copilot native delegation. Decide whether the separate SRE terminal
   preview is part of this release. Do not silently claim its pending canary passed or omit it from acceptance.
2. Select and qualify the immutable rollback baseline. Uninstall alone does not meet the current
   backlog's rollback outcome.
3. Freeze the accepted source/selector and run the installed matrix on that exact candidate and
   rollback artifact. A changed package or harness invalidates only its affected evidence.
4. Obtain human acceptance tied to those bytes. Publication remains a separate action; if GitHub
   Releases is the chosen channel, its immutable-setting and selected-release checks apply.

The pinned source archive, proposed selector and receipt are local preparation artifacts, not a
release verdict. The live roadmap remains the only backlog.

## Current native host and corroborating conversion path

[verified] Installed VS Code is 1.146.0, commit `69047191fc427f2f92828279aae1d90d8eeda7ab`.
The separate global Copilot CLI is 1.0.78; it predates this repository's documented 1.0.85 minimum
for the `com.github.copilot/agents` plugin layout. CLI acceptance cannot be substituted for VS Code.

[sourced] At upstream commit `d0e3b45e`, `toSdkCustomAgents` reads name, description, tools, skills,
hooks, model and invocation flags; it does not read/forward `agents` or `handoffs`. Nonempty tools
are forwarded, while empty/missing tools become null. This confirms the concrete conversion seam
to investigate for native delegation, not merely the editor schema.
[Converter source](https://github.com/microsoft/vscode/blob/d0e3b45e/src/vs/platform/agentHost/node/copilot/copilotPluginConverters.ts#L205-L258).

## Native delegation feasibility

[verified] VS Code's installed built-in Copilot extension is `0.74.0`; its bundled
`@github/copilot` runtime is `1.0.73`. This differs from the separate global CLI. Local inspection
of the bundled SDK shows a shared `task` tool whose custom-agent list contains names, descriptions
and invocation flags. The custom-agent tool filter operates on tool names. This inspection did
not execute a model or establish that a forbidden child is blocked.

[sourced] The current upstream SDK's entire `CustomAgentConfig` interface has tool restrictions,
agent-scoped hooks, model settings and invocation flags, but no per-parent delegation-target list.
[SDK interface at `540dc4e1`](https://github.com/github/copilot-sdk/blob/540dc4e1/nodejs/src/types.ts#L2485-L2544).
This corroborates the converter's missing target-list mapping; the upstream interface and installed
runtime remain separate evidence.

[sourced] A `preToolUse` hook can deny a supported tool call, but command-hook timeouts continue
through normal permissions, including policy hooks. Microsoft also warns that changing hook field
names alone does not migrate the script contract.
[Current hook contract](https://github.com/microsoft/vscode-docs/blob/main/docs/agent-customization/hooks.md),
[migration details](https://github.com/microsoft/vscode-docs/blob/main/docs/agent-customization/migrate-customizations.md).
A happy-path deny hook therefore cannot establish the selected scoped-delegation guarantee.

[unverified] No supported, enforceable per-parent target restriction was identified for the default
Copilot harness. Native invocation/return and the forbidden-target control are still unrun. There
is no justified generator change yet: emitting an invented SDK field, keeping ignored Local fields,
or relying on a timeout-sensitive hook would not resolve the gap. The next design work must establish
a host-enforced native mechanism or explicitly propose a different integration for owner review;
neither is approved by the current scope selection alone.
