# Default Copilot harness: agent and skill migration research

Research date: 2026-11-14. Repository baseline: `171a59bc`.
Tracks [COPILOT-HARNESS-001](../fleet-roadmap.md#copilot-harness-001--decide-fleet-delegation-on-the-default-copilot-harness).
Follow-up: [three-harness comparison](2026-11-14-three-harness-comparison.md) adds independent
Terra research, the scoped-task-hook candidate and its limits, and current Claude/Codex contracts.

## Finding and scope

Owner-selected comparison scope: default Copilot, Claude Code, and Codex. OpenCode is excluded
for now. Compare delegation support separately from enforcement of allowed child targets, and
distinguish a selected main agent from a nested child. This research scope does not add Codex
as a release target or change the existing Claude Code and default Copilot release decision.

[sourced] This migration has a deadline: VS Code now says the Local harness will be removed by
February 2027. This supersedes the timing uncertainty in the
[November 12 preparation report](2026-11-12-release-001-preparation.md).
The default Copilot harness uses a different runtime, so choosing the same model does not preserve
Local customization behavior. [Migration guide](https://code.visualstudio.com/docs/agents/run/move-to-copilot).

[verified] The repository has nine canonical agents, 24 skills, and one command. Most skill
content can remain. The substantial migration work is in the Copilot generator, tool references,
delegation, and hook contracts. Six generated agents contain delegation allowlists; six contain
Local handoffs, with ten handoff entries. The canonical graph remains in the existing roster and
source grants; this report does not redefine its edges.

[unverified] The release blocker remains host-enforced restriction of each parent's allowed
child agents. No suitable field was identified in the inspected converter, SDK configuration,
or public documentation. This is a bounded research finding, not proof that every possible host
integration lacks the capability. A prompt asking an agent to obey the graph is insufficient for
the owner's selected requirement.

[verified] No `code`, `code-insiders`, or `copilot` executable was found on this workspace's PATH.
This report contains source inspection and an offline hook probe, not installed-host acceptance.
No runtime files were changed, no plugin was installed, and no paid eval was started.

## What needs to change

| Area | Evidence and implication | Migration direction |
| --- | --- | --- |
| Delegation and handoffs | [sourced] Default Copilot does not support the Local `agents:` and `handoffs:` fields. Its native subagent tool is `task`. [Agent reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference), [subagent guide](https://code.visualstudio.com/docs/agents/run/subagents). | Establish enforceable target selection and parent continuation before shipping delegating profiles. Keep canonical role boundaries; do not treat deleting unsupported fields as completion. |
| Tool aliases | [sourced] `read`, `search`, `edit`, `execute`, `web`, `agent`, and `todo` remain documented aliases. Client tools use qualified references such as `browser/<tool>`. [Agent reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference). | Preserve valid aliases. Resolve the seven currently unqualified SRE browser references against the installed host's advertised inventory. Do not mechanically replace the frontmatter `agent` alias with `task`. |
| Tool instructions | [verified] The generated researcher body still instructs it to use `ToolSearch`, but its generated tool list is only `[web]`; `adapt_text` does not translate that instruction. | Make discovery instructions match the host's actual discovery capability and approved MCP tools. Verify both discovery and a real read invocation. Do not add broad tools merely to satisfy a literal tool name. |
| Empty tool lists | [sourced] The inspected VS Code converter changes an empty tool array to `null`; the SDK describes `null` as all tools. [Converter, lines 205–258](https://github.com/microsoft/vscode/blob/a389cd7c5195662c3e3998d4ba10604ff5cdaa70/src/vs/platform/agentHost/node/copilot/copilotPluginConverters.ts#L205), [SDK configuration](https://github.com/github/copilot-sdk/blob/cf045793958ce674259c557f7769788f94ee20c9/nodejs/src/types.ts#L2485). | Reject accidental empty grants during generation and test effective tool availability. Do not use `tools: []` as a no-tools profile on this conversion path. |
| Agent identity | [sourced] The converter generates opaque `vscode-agent-…` runtime names from resource identity and keeps the authored name as display metadata. [Converter identity function](https://github.com/microsoft/vscode/blob/a389cd7c5195662c3e3998d4ba10604ff5cdaa70/src/vs/platform/agentHost/node/copilot/copilotPluginConverters.ts#L110). | Bind delegation and ADR checks to verified installed identities. Test a workspace agent with a matching display name; name text alone must not establish authority. |
| Repository instructions | [sourced] The CLI documents `include-custom-instructions` and `strict-tools-list`, but neither is forwarded by the inspected VS Code converter. [CLI agent guide](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli), [converter](https://github.com/microsoft/vscode/blob/a389cd7c5195662c3e3998d4ba10604ff5cdaa70/src/vs/platform/agentHost/node/copilot/copilotPluginConverters.ts#L205). | Measure instruction delivery and tool inventory in both selected agents and spawned children. A CLI recipe is not evidence of VS Code behavior. |
| Hooks | [verified] The preview uses `PreToolUse`; the script reads snake_case payload fields. A camelCase probe is allowed by that parser. Details below. | Keep a verified compatibility contract or adapt the event, input parser, and output together. Keep standard SRE terminal access absent until the preview's independent acceptance succeeds. |

[sourced] `target` selects an authoring schema, not the executing harness. Adding it cannot fix
delegation semantics. [Agent reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference).

[verified] The generated SRE body is 24,851 characters against the repository's 25,000-character
working cap: only 149 characters remain. Migration should replace obsolete instructions or use
existing linked references, rather than append another general policy block.

## Skills and the ADR command

[verified] All 24 skill names match their directories and fit the documented name limit; their
descriptions also fit. All use `argument-hint`; four have `compatibility`; only `pcf-deploy` has
`disable-model-invocation: true`. None currently uses agent skill preloads or `context: fork`.

[sourced] The existing `SKILL.md` structure and bundled relative references remain supported.
`argument-hint` is supported on skills even though it is not a Copilot agent field. Preserve the
manual-only deployment setting. Plugin skill names receive a namespace at invocation; do not
insert that namespace into the skill's bare `name`. `context: fork` is experimental and changes
execution context; it is not a required migration step.
[Skill guide](https://code.visualstudio.com/docs/agent-customization/agent-skills).

[sourced] Agent-level `skills` can preload entire named skill bodies into the agent's starting
context. [SDK skill configuration](https://github.com/github/copilot-sdk/blob/cf045793958ce674259c557f7769788f94ee20c9/nodejs/src/types.ts#L2519).
Recommendation: retain progressive loading initially. Add a preload only for a measured missing
method, and do not preload the manual-only deployment workflow as a migration shortcut.

[verified] The plugin already uses a root `plugin.json`, canonical `skills/`, and
`com.github.copilot/` projections. ADR is a plugin command, not a workspace prompt file.
[sourced] Current plugin packaging still supports commands, so the prompt-file-to-skill migration
does not by itself require converting ADR.
[Plugin reference](https://code.visualstudio.com/docs/agents/reference/agent-plugin-reference).

Recommendation: retain all 24 methods and ADR's selected-writer preflight. Test automatic skill
selection, explicit invocation, installed reference resolution, and command authority separately.
Repository-local copies can conceal missing installed resources; use a neutral workspace for
plugin acceptance. Bundled scripts still need the repository's supported Python and dependencies;
plugin discovery does not install them.

## Hook probe and enforcement limits

[verified] A subprocess invoked the existing guard with a synthetic command string as JSON input.
The command was never executed; its sentinel file was absent before and after the probe.

| Input to `readonly-guard.py --copilot` | Result |
| --- | --- |
| `tool_name: runInTerminal`, `tool_input.command: touch <sentinel>` | Exit 43, deny |
| `tool_name: Bash`, same command data | Exit 43, deny |
| `toolName: bash`, `toolArgs.command: touch <sentinel>` | Exit 42, allow |

[verified] The cause is the parser at `scripts/readonly-guard.py:1268–1299`: it does not read
`toolName` or `toolArgs`. The preview currently emits the compatibility event `PreToolUse`, and
the global Copilot hook configuration is empty. Therefore this probe demonstrates a migration
trap, not an established bypass in a shipped default-harness session.

[sourced] Copilot distinguishes camelCase native events from compatibility aliases, including
their payload formats. Hook timeouts fall back to normal permission processing, including policy
hooks. `subagentStart` can supply context; its documented output is not a deny-before-spawn
decision. [Hook reference](https://docs.github.com/en/copilot/reference/hooks-reference).

Recommendation: preserve the verified alias until a complete adapter is tested. Cover input
translation, scoped identity, deny output, malformed input, launcher failure, and timeout. Do not
claim a timeout-sensitive hook is the host-enforced delegation boundary. A command guard also
cannot establish the absence of other write-capable tools.

## Why the delegation question remains open

[sourced] The inspected `CustomAgentConfig` has tool grants, prompts, hooks, model settings, and
skill loading, but no per-parent custom-agent target allowlist. Session controls for included or
excluded built-in agents are a different scope. Tool-name filters restrict tools, not the child
argument supplied to a shared delegation tool.
[SDK types](https://github.com/github/copilot-sdk/blob/cf045793958ce674259c557f7769788f94ee20c9/nodejs/src/types.ts#L2485),
[session filters](https://github.com/github/copilot-sdk/blob/cf045793958ce674259c557f7769788f94ee20c9/nodejs/src/types.ts#L3216).

The next investigation must find an enforceable host mechanism and demonstrate rejection before
an unauthorized child starts. Visibility flags, model instructions, and removing all delegation
do not satisfy the owner's selected outcome. If the mechanism is unavailable, record the precise
upstream capability gap and return a design decision to the owner; do not silently weaken the
requirement or invent unsupported frontmatter.

## Bounded implementation and acceptance sequence

1. Prepare offline generator changes for supported fields, qualified tool references, and
   host-specific discovery instructions. Add focused fixtures for the concrete conversion risks.
   Keep Claude sources and projections consistent and keep the delegation blocker explicit.
2. On an authorized installed VS Code host, record the editor, extension, bundled runtime,
   harness, plugin revision, and effective tool inventory. Begin with a nondelegating
   repository-investigator canary and a disposable allowed/forbidden delegation probe. This is
   an experiment, not a no-delegation release fallback.
3. Once target enforcement is proven, migrate the delegating profiles and run the acceptance
   cases below against the exact candidate artifact. Reuse successful evidence unless its
   relevant inputs change.
4. Release through RELEASE-001 with an immutable rollback artifact and owner acceptance.

| Acceptance case | Required observation |
| --- | --- |
| Installed discovery | Nine agents, 24 skills, and ADR load from the intended plugin, without workspace copies masking it. |
| Effective capabilities | Every role has its intended tools; read-only lanes lack writes; standard SRE lacks terminal execution; researcher retains its external-source scope. |
| Delegation success | An allowed child starts, receives the bounded task, returns evidence, and the parent continues. |
| Delegation rejection | A forbidden child is rejected before invocation, including matching-name workspace agents, aliases, nested calls, and built-in fallback routes. |
| Instruction delivery | Critical rules reach both directly selected agents and children; AGENTS.md delivery is observed rather than inferred. |
| Skill invocation | Ordinary skills trigger appropriately; `pcf-deploy` does not auto-trigger and remains explicitly invocable. |
| Installed resources | Linked references and bundled scripts resolve from the installed package with the supported interpreter. |
| Browser tools | Qualified references resolve and return usable page/image evidence with intended scope. |
| Hook contract | Allowed/denied commands, malformed input, missing interpreter, crash, and timeout produce documented outcomes; fail-open cases remain visible. |
| Session transitions | Agent selection, model changes, and session resume preserve required tool and instruction boundaries. |
| ADR authority | Intended selected writers can use ADR; read-only agents cannot gain edit authority through the command. |

[unverified] None of these installed-session cases is claimed passed by this research. Upstream
source inspection and repository structural checks cannot substitute for them.

## Evidence and reproducibility

- [verified] `scripts/generate_platform_adapters.py` passed its existing consistency check at
  the research baseline. This checks current generated output, not compatibility with the new host.
- [verified] After documenting the findings, `.venv/bin/python scripts/gate_a.py` passed both
  structural steps. The report and roadmap are the only changed files.
- [verified] The offline hook probe used only synthetic command data; no credential or live
  service was involved.
- [sourced] VS Code converter snapshot:
  `a389cd7c5195662c3e3998d4ba10604ff5cdaa70`.
- [sourced] Copilot SDK snapshot: `cf045793958ce674259c557f7769788f94ee20c9`, carrying
  the CLI `1.0.112-0` snapshot. These are upstream research pins, not the installed release target.
- [unverified] Historical Windows acceptance and prior runtime versions in the November 12
  report do not establish the behavior of a current installation.

Disposition: keep COPILOT-HARNESS-001 active. The immediate priority is proving the delegation
boundary while preparing the bounded adapter corrections; a wholesale rewrite of skill content
is not supported by the findings.


## Agent-authoring update and offline generation guard

[sourced] The owner requested a Copilot agent-authoring repair after the tool-mapping investigation.
This amendment changes the authoring method and reference, and rejects empty mapped tool lists;
it does not enable skill preloads, provision MCP, change browser mappings, install a client,
or establish a new delegation boundary. The earlier Local-field cleanup remains part of the
same uncommitted candidate on `work/copilot-harness-frontmatter`.

[verified] The authoring entry point now binds the executing harness/client before frontmatter
changes. Its Copilot reference covers all documented default-harness fields, distinguishes editor
recognition from runtime forwarding, and corrects the earlier inference about VS Code child
instruction delivery. Tool guidance separates documented qualified references from proven call
success, records researcher integration gaps, and keeps intentional mapping omissions explicit.
The preload procedure checks workspace and installed-plugin resolution, direct and delegated use,
required references, context cost, and trusted review guidance. No fleet preload is enabled.

[verified] A single fresh-context reference application per variant used the same four-part task:
scribe preload design; classification of eight Copilot fields; empty/browser/MCP tool mapping;
and researcher discovery. The incumbent could not classify six fields or supply preload syntax
from the reference. The candidate classified all eight and supplied the bounded preload and host
verification procedure without inventing MCP identifiers. Both preserved the installed-host gap.
These are reference-retrieval samples, not a reliability estimate or native Copilot acceptance.
The candidate sample still echoed a blanket tool-list claim from the old portable footer; the
footer was narrowed to require selected-host evidence, without claiming a repeated behavioral run.

[verified] Before the generator guard, six empty-list render cases and one output-preservation
case failed. Cases cover missing tools, an empty array, only Skill, an unknown grant, only an
unmapped MCP tool, and SRE shell grants removed by the standard profile. After the change, both
tests pass with six subtests. Generation fails before replacing existing output; the preservation
check compares all generated file paths and bytes. Nonempty profiles still need mapping and
runtime verification: this guard does not resolve partial mapping loss or default-tool additions.

[verified] Relative to repository baseline `5bdbb980`, the authoring entry point grows from
9,512 to 10,393 bytes (+881); its Copilot reference grows from 9,291 to 13,365 (+4,074).
The extra reference content supplies previously missing field distinctions, a preload application
example, mapping failure behavior, and installed acceptance criteria. It loads for Copilot
composition work rather than expanding every fleet agent body. Canonical agent grants are unchanged.

[sourced] Upstream refresh found VS Code main at `776b518e720e780fb590f29872473f90bda9e079`,
two commits beyond the prior pin; the compared changes do not alter the inspected converter,
client-tool mapping, or launcher files. Copilot SDK main remained
`cf045793958ce674259c557f7769788f94ee20c9`.
[Comparison](https://github.com/microsoft/vscode/compare/a389cd7c5195662c3e3998d4ba10604ff5cdaa70...776b518e720e780fb590f29872473f90bda9e079).
The earlier pinned links therefore still describe the inspected mapping path, not an installed
host. No native Copilot model call or reliability-campaign spend occurred in this amendment.

[verified] Final offline verification: affected suites **105 passed / 548 subtests**; Ruff and
mypy pass. The coordinated default suite passes **4,580 tests, 85 skips, 4,406 subtests**, exit 0
in 28.627 runner seconds. Receipt:
`.git/local-test-runs/20261115T060813Z-1234ca8d/run.json`.
Source endpoints were identical, with tracked diff SHA-256 `d49f66bbdc785d3631efcd3c7526c4e30e397534bfdc5b481ae4c9638194ffbd`.
This verification paragraph is a subsequent evidence-only documentation update; no executable,
canonical skill or generated adapter bytes changed after that suite. Native Copilot acceptance
and per-parent target enforcement remain unverified.


### Active-guide cleanup

[sourced] The owner requested removal of old material from the authoring guide. [verified]
The active Copilot reference now omits the legacy Local field catalog, deprecated `infer`,
Local target/preview instructions, and compatibility-history discussion. The entry point routes
Copilot authors to current fields, mapping, preload and host checks. Supported skill hints,
canonical Claude guidance, current unforwarded-field limitations, and unresolved enforcement
requirements remain. Historical findings stay in the research records.

[verified] This follow-up changes prose and regenerated reference copies only. The Copilot
reference is now 12,251 bytes, down 1,114 from the preceding authoring candidate. The full-suite
receipt above belongs to that preceding candidate; its executable files are unchanged.
Fresh adapter checks pass **56 tests / 282 subtests**, and Gate A passes both structural steps.
No installed-host or live behavioral result is claimed for this cleanup.
