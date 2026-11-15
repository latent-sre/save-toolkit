# Copilot, Claude Code, and Codex: current agent and skill contracts

Research completed on 2026-11-14 America/Chicago (2026-11-15 UTC).
Repository baseline: `171a59bc17cf14d501746a6562f85edcd92e9446`.
Three independent Terra agents researched one harness each; the main session reconciled their
findings against repository files and primary sources. OpenCode is excluded by owner direction.
This report supports [COPILOT-HARNESS-001](../fleet-roadmap.md#copilot-harness-001--decide-fleet-delegation-on-the-default-copilot-harness)
and supplements the [Copilot migration analysis](2026-11-14-copilot-harness-migration-research.md).

## Decision-relevant result

[sourced] All three support delegation. Their customization and enforcement contracts differ,
so a common agent description does not establish equivalent permissions. Copilot's native
delegation tool is `task`; Claude uses `Agent`; Codex exposes agent lifecycle tools.
[Copilot](https://code.visualstudio.com/docs/agents/run/subagents),
[Claude](https://code.claude.com/docs/en/sub-agents),
[Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents).

[unverified] None of this research establishes the fleet's complete allowed-child graph as
enforced across all nesting levels on the intended installations. Claude documents a main-thread
restriction but excludes nested target lists; Copilot and Codex need further evidence for an
equivalent restriction. This does not mean delegation itself is unavailable.

Recommendation: retain the canonical roles and skill methods. Describe and test separately:
whether a child can be launched, which child the parent may launch, what tools the child has,
what instructions it receives, and how control returns. Avoid a generic promise that all five
properties travel with a portable agent file.

## Comparison

| Contract | Default VS Code Copilot | Claude Code | Codex |
| --- | --- | --- | --- |
| Agent definition | [verified] VS Code converts Markdown into SDK configuration; some authored fields are dropped. | [sourced] Markdown agent definitions; plugin-specific field restrictions apply. | [sourced] Local custom roles use TOML, not Claude agent frontmatter. |
| Named-child restriction | [verified] No corresponding field identified in the inspected converter/SDK type. [unverified] Other host mechanisms remain to prove. | [sourced] `Agent(names)` constrains a selected main `--agent`; nested agents ignore the names. | [unverified] No documented per-parent target allowlist identified in this review. |
| Child capability controls | [sourced] Tool lists and runtime permissions; empty tools become unrestricted on the inspected conversion path. | [sourced] Tool grants, filtering, and session permissions; omitted tools inherit the available pool. | [sourced] Selected feature groups can be disabled; parent sandbox, approvals, provider, and MCP configuration are inherited. |
| Nested execution | [unverified] Do not apply Local's depth settings to default Copilot. | [sourced] Default depth is three; waiting depends on foreground/background and execution mode. | [unverified] No portable depth limit established for the installed runtime. |
| Skills | [sourced] Progressive discovery, explicit invocation, optional agent preloads. | [sourced] Progressive discovery and optional agent preloads. | [sourced] Progressive discovery; inherited availability does not prove every loaded parent body is preloaded in a fresh child. |
| Deployment workflow policy | [sourced] `disable-model-invocation` supports manual-only skills. | [sourced] Manual-only flag also excludes preloading. | [sourced] Explicit-only policy is expressed in `agents/openai.yaml`; direct translation needs verification. |

Sources for the table: [Copilot converter](https://github.com/microsoft/vscode/blob/a389cd7c5195662c3e3998d4ba10604ff5cdaa70/src/vs/platform/agentHost/node/copilot/copilotPluginConverters.ts#L205),
[Copilot SDK](https://github.com/github/copilot-sdk/blob/cf045793958ce674259c557f7769788f94ee20c9/nodejs/src/types.ts#L2485),
[Claude subagents](https://code.claude.com/docs/en/sub-agents),
[Claude skills](https://code.claude.com/docs/en/skills),
[Copilot skills](https://code.visualstudio.com/docs/agent-customization/agent-skills),
[Codex role schema](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Codex skills](https://learn.chatgpt.com/docs/build-skills).

## Copilot: migration work and a candidate enforcement mechanism

[verified] Research resolved the same upstream snapshots as the earlier report:
VS Code `a389cd7c5195662c3e3998d4ba10604ff5cdaa70` (November 14), SDK
`cf045793958ce674259c557f7769788f94ee20c9` (November 13). They are source pins, not
installed-host versions. The converter omits `agents`, `handoffs`, `strict-tools-list`, and
`include-custom-instructions`; its runtime agent identifiers are resource-derived rather than
authored display names. [Converter](https://github.com/microsoft/vscode/blob/a389cd7c5195662c3e3998d4ba10604ff5cdaa70/src/vs/platform/agentHost/node/copilot/copilotPluginConverters.ts#L110).

[sourced] An agent-scoped pre-tool hook can inspect and deny `task` calls. This is a candidate
for target policy, not evidence of a complete boundary. Timeouts fall back to normal permission
handling. Subagent hook payloads document identity fields, although some are conditional and the
SDK marks them optional. The built-in general-purpose agent omits start/stop lifecycle events;
those events cannot supply universal auditing or instruction injection.
[Hook reference](https://docs.github.com/en/copilot/reference/hooks-reference),
[agent-scoped hooks](https://code.visualstudio.com/docs/agent-customization/hooks),
[SDK identity fields](https://github.com/github/copilot-sdk/blob/cf045793958ce674259c557f7769788f94ee20c9/nodejs/src/types.ts#L1954).

[unverified] To assess that candidate, capture actual task arguments and scoped hook identity,
attempt every relevant forbidden route, and force a timeout. A successful ordinary denial does
not resolve a timeout or a bypass through another route. Do not widen SRE terminal access to
conduct this investigation.

[sourced] Standalone CLI documents different repository-instruction defaults for directly
selected versus delegated agents. VS Code does not forward the CLI's opt-in field, so it needs
its own child-delivery probe. [CLI instruction behavior](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli#applying-your-repositorys-custom-instructions-to-a-custom-agent).

[verified] Existing concrete adapter findings remain: seven unqualified browser references,
the researcher's literal `ToolSearch` instruction with a generated `[web]` grant, and the hook
parser's incompatibility with native camelCase inputs. The earlier report contains the exact
inventory and harmless offline probe. These are bounded adaptation tasks, independent of a
wholesale skill rewrite.

## Claude: preserve the working format and its documented limits

[verified] Standalone `claude --version` returned **2.1.325**. The repository already records
the main-thread-only `Agent(target)` restriction in its README and frontmatter reference;
this is confirmed existing knowledge, not new drift.

[sourced] Plugin agents ignore their own `hooks`, `mcpServers`, and `permissionMode` fields.
Conversation forks inherit the parent's exact tool pool; they are unsuitable as a substitute for
a restricted named worker. [Subagent contract](https://code.claude.com/docs/en/sub-agents).

[sourced] Skill `allowed-tools` pre-approves tools rather than narrowing them;
`disallowed-tools` removes tools while the skill is active. Neither should be casually substituted
for the fleet's agent grants. [Skill tool access](https://code.claude.com/docs/en/skills#restrict-tool-access).

[sourced] Since 2.1.277, direct `AGENTS.md` discovery depends on other instruction files and
configuration. [Instruction loading](https://code.claude.com/docs/en/memory#use-an-existing-agentsmd).
[verified] Our root `CLAUDE.md` already imports `@AGENTS.md`. Reconciliation withdrew an initial
suggestion that the new discovery rules demonstrated guidance loss here. [unverified] Delivery
to exceptional child contexts and installed plugin sessions still needs observation.

[sourced] The Claude Code VS Code extension bundles its own CLI. A standalone CLI version
does not prove extension behavior. [Extension versus CLI](https://code.claude.com/docs/en/vs-code#vs-code-extension-vs-claude-code-cli).
Recommendation: preserve the current canonical format and imports; test selected-main,
nested-child, and fork behavior separately. Do not claim the named-child graph is enforced
inside nested workers.

## Codex: newer capability controls, unchanged distribution decision

[verified] Installed `codex --version` returned **0.169.0**. Its feature list showed legacy
`multi_agent` enabled/deprecated and `multi_agent_v2` disabled/stable. These observations do
not determine the runtime of every app or IDE surface. This research session itself successfully
used three Terra children and received their results; that proves this session's delegation,
not the standalone CLI's custom-role boundary.

[sourced] Current local role files support switches disabling shell, apps, plugins, memories,
and permission-request capabilities. The newer controls qualify any blanket historical claim
that roles cannot reduce capabilities. They do not document an arbitrary exact tool allowlist or
replace inherited MCP configuration. [Role schema](https://learn.chatgpt.com/docs/agent-configuration/subagents).

[sourced] Codex skills have their own discovery paths and optional `agents/openai.yaml` metadata.
`policy.allow_implicit_invocation: false` controls automatic selection, not permission to perform
an action. [Skill packaging](https://learn.chatgpt.com/docs/build-skills).

[verified] The accepted [Codex distribution retirement ADR](../decisions/2026-08-23-retire-codex-distribution-target.md)
and generator still prohibit reviving the retired `.codex/agents` output without a new decision.
This research does not change that. The relevant future question is whether newer capability
switches plus host isolation can meet the local-only/external-only contract at acceptable upkeep
cost. It is not an immediate instruction to build another adapter.

[sourced] CLI, Codex IDE, hosted Work, and a provider harness are distinct surfaces. Current
Codex concurrency configuration counts spawned threads separately from the primary thread.
[Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
[IDE integration](https://learn.chatgpt.com/docs/codex/ide).
[unverified] Exact limits and supported features must be bound to the tested client; do not
borrow limits from the Responses API or this research session.

## Next work, in priority order

1. **Prove the Copilot delegation boundary.** Use a neutral workspace and disposable profiles
   to test an allowed child and forbidden custom, built-in, nested, and matching-name targets.
   Include scoped-hook timeout behavior and actual parent continuation.
2. **Prepare the concrete Copilot adapter fixes.** Correct tool references and discovery prose,
   protect against empty grants, and keep hook event, input, and output contracts together.
   The existing migration report defines the specific changes; this turn did not implement them.
3. **Run focused Claude compatibility checks.** Verify actual tools and instructions in selected
   main and nested agents, the documented nested-target limitation, and skill manual invocation.
   Preserve accepted source behavior unless a check identifies a material difference.
4. **Keep Codex comparative until a new distribution decision.** If reconsidered, first test
   exact local/external isolation and explicit-only skill policy with current role controls.

For each native test record: host surface, editor/CLI and bundled-runtime version, model,
configuration, immutable candidate revision, effective tools, observed instructions, and result.
Use harmless sentinels and record whether rejection happens before the prohibited action.
Observe skill references from the installed package so workspace copies cannot mask failures.

## Evidence limits and reconciliation

[verified] Only documentation was changed. No package installation, infrastructure change,
or standalone installed-harness model/eval run was performed. Research delegation used the
three Terra agents authorized by the owner. No additional agents were spawned.

[verified] Two initial findings were narrowed before inclusion: the existing Claude import
prevents claiming guidance loss merely from automatic discovery rules; current Copilot docs
and SDK types include child identity fields, so an older missing-identity issue cannot establish
their blanket absence today. Source-level capabilities remain distinct from installed behavior.

[unverified] Release readiness remains open. Research and structural checks do not promote
the candidate, alter release targets, or establish cross-harness permission equivalence.
