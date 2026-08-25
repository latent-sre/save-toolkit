# HOST-002 VS Code tool-enforcement observation

**Conclusion:** `[verified]` On VS Code 1.134.0, every tested omitted built-in tool remained in the
picker as disabled. Two disposable-profile attempts then disagreed on the same default-Agent-to-`sre`
override path: the first retained `execute` and dirtied the open generated-agent buffer, while the
corrected retry dropped `execute` on the switch and left the buffer clean. `[unverified]` Neither
attempt reached a command or host denial, so the observations establish configuration variance, not
`sre` invocation authority or host enforcement.

This supports the existing `AGENTS.md` warning at the configuration layer and sharpens its
persistence language. It does not establish an authority boundary, hook boundary, managed-policy
result, or host-side denial of an execute call.

The follow-up source inspection narrows the hook question: a plugin-wide `PreToolUse` payload has
no top-level custom-agent identity, but VS Code merges hooks from the selected custom `.agent.md`
before invoking Copilot Chat. A generated agent-scoped hook is therefore the candidate boundary;
`hooks/copilot-hooks.json` remains intentionally empty until a disposable runtime canary proves the
merge and denial behavior on this build.

## Exact evidence base

- Run: `host-002-20260824-075430`, attempt `attempt-1`.
- Target checkout: `F:\repos\sre-agents-host-002` at
  `4eae26d1534d4274774e0f404ee728989b61e688`.
- Snapshot tree SHA-256: `e53ce0e6b45b1dc79fb6c12ff944df2da853f570bfd2994ed9d4989e37d35ec2`.
- VS Code: version `1.134.0` (user setup), commit
  `110a328ea54b42367b803ec53ee0bf52ef26b419`, x64; built-in Copilot Chat `0.62.0`.
- Runtime: Windows 11 Pro `10.0.26200`, build `26200`, x64. The Help > About copy returned the
  commit SHA in its `OS` field; the transcript preserves that malformed raw value and labels the
  separate local OS observation.
- Transcript SHA-256: `d991c5c98f39cb60fec55c83c8c032aaf1e9b2886f12b71d45c7d6f472d0e112`,
  14351 bytes.
- Original operator-local evidence archive: `F:\repos\HOST-002-evidence-20260824.zip`, SHA-256
  `31dc110ad0c1d05bb1362f772893977181e74964f57f1f44a993f92115376277`, 2182308 bytes. It was
  intentionally not added to Git or the PR.
- `[verified]` The operator validated all eight JSON records with `scripts/evidence_envelope.py` and
  matched every local artifact path, byte size, and SHA-256. Sanitized transcript-bound copies of
  those eight envelopes are durable at `abb02cf` under
  [`evidence/host-002`](evidence/host-002), without the
  screenshots that exposed unrelated Chat session metadata. The retained transcript is SHA-256
  `d991c5c98f39cb60fec55c83c8c032aaf1e9b2886f12b71d45c7d6f472d0e112`, 14351 bytes; each sanitized
  copy has a new evidence ID so it cannot be confused with the operator-local original.

The run used a disposable VS Code user-data and extension directory. After rollback, the window was
closed and that exact temporary authenticated profile was deleted. The evidence archive contains
only the transcript, eight envelopes, baseline metadata, and cited screenshots; it excludes profile
state, credentials, raw logs, the target snapshot, and unrelated automation screenshots. Its local
hash is provenance for a future durable attachment, not HOST-002 closure evidence.

## Picker inventory

| Role | Enabled default groups | Omitted groups as observed | Result |
|---|---|---|---|
| `sre` | `agent`, `read`, `search` | `browser`, `edit`, `execute`, `todo`, `vscode`, `web` offered-off | `execute` is a default, not absence |
| `observability-engineer` | `agent`, `edit`, `execute`, `read`, `search` | `browser`, `todo`, `vscode`, `web` offered-off | generated `execute` matches the current dashboard write rule |
| `reviewer` | `read`, `search` | `agent`, `browser`, `edit`, `execute`, `todo`, `vscode`, `web` offered-off | omissions are defaults |
| `repository-investigator` | `read`, `search` | `agent`, `browser`, `edit`, `execute`, `todo`, `vscode`, `web` offered-off | omissions are defaults |
| `scribe` | `edit`, `read`, `search` | `agent`, `browser`, `execute`, `todo`, `vscode`, `web` offered-off | omissions are defaults |
| `researcher` | `web` | `agent`, `browser`, `edit`, `execute`, `read`, `search`, `todo`, `vscode` offered-off | local omissions are defaults |

`[verified]` The picker also registered all eight expected custom agents with exact labels and no
missing or unexpected custom role. This is packaging evidence, not authority enforcement.

## Persistence and override observations

1. `[verified]` Disabling declared `sre.read` persisted after reopening the picker: the banner fell
   from `14 Selected` to `7 Selected`. Re-enabling it restored `14 Selected`.
2. `[verified]` The generated file's disk SHA-256, workspace settings SHA-256, and clean Git status
   remained fixed during that toggle. The original Step 3 instrument did not inspect the active
   editor buffer, so it could not identify the exact non-disk persistence store.
3. `[verified]` The built-in Agent picker explicitly said its selection applied globally to all
   chat sessions using the default agent. Enabling `execute` produced `52 Selected`.
4. `[verified]` Switching to `sre` retained `execute` and produced `23 Selected`, outranking the
   generated `sre` default.
5. `[verified]` The open generated `sre.agent.md` buffer became dirty and showed
   `tools: [execute, read, agent, vscodeGeneral/usages, search]`; its on-disk SHA-256 remained
   `ed1bc2c68c3359b3e81f03ac7bb914300dea0980bfbf394455c11533bbffea24` and Git remained clean.
6. `[verified]` The command-observation precondition failed at that point, so no prompt or terminal
   command was submitted. The result is a global/buffer-mutating configuration path, not a
   session-only path and not evidence of invocation authority or command denial.

The procedure now requires the editor's dirty state and visible `tools:` line at every toggle, and
requires **File: Revert File** for a dirty unsaved generated buffer. Disk-only checks remain, but no
longer stand in for editor-buffer cleanliness.

## Corrected Step 4 reprobe (2026-08-25)

`[verified]` A new authenticated disposable profile retried only the missing invocation path at
revision `463fcd56cf0017374a60228bf4530d67007bb84a`. The built-in Agent picker already showed
`execute` checked at `52 Selected` and again labelled that state global. Switching to `sre` in the
same new Chat session restored the custom agent's `14 Selected` set with `execute` offered-off. The
custom-agent picker warned that changing the tools would also change the custom-agent file.

The generated editor tab stayed clean at `tools: ["read", "search", "agent"]`; its on-disk SHA-256
remained `e49532a82d126ea56bf7beb1363121d386d542840df4788af3e14d9304e3e73e`; Git remained clean;
and the disposable profile still had no `settings.json`. Because `execute` did not survive the
switch, the procedure classified this as a measured negative for the tested override path and did
not submit the command. Invocation authority therefore remains `[unverified]`.

The raw transcript and validated `inconclusive` envelope are retained as
[`2026-08-25-invocation-reprobe-transcript.md`](evidence/host-002/2026-08-25-invocation-reprobe-transcript.md)
and [`2026-08-25-session-override-reprobe.json`](evidence/host-002/2026-08-25-session-override-reprobe.json).
The same-build disagreement is material: picker history or profile state affects this path, and a
third identical retry would not resolve invocation authority.

## Acceptance mapping

| HOST-002 question | Evidence-bound answer |
|---|---|
| Does the picker offer `execute` to `sre`? | `[verified]` Yes, offered-off at the generated default. |
| Does the tested override display it as enabled after switching? | `[verified]` Not consistently. Attempt 1 retained it and dirtied the buffer; attempt 2 dropped it and kept the buffer clean. Neither is a stable session-only override. |
| Does the picker mutate `.github/agents/sre.agent.md` on disk? | `[verified]` Neither attempt changed disk. Attempt 1 mutated the open editor buffer; attempt 2 did not. Saving a generated buffer was deliberately avoided. |
| Can `sre` invoke `execute`, or does the host deny it? | `[unverified]` No tool call or host denial was observed. Configuration state cannot answer this authority question. |
| Are the raw evidence records durably reviewable? | `[verified]` The non-secret transcripts and nine validated envelopes are durable at `abb02cf` under `docs/reviews/evidence/host-002`. |
| Is the Copilot hook portable with exact-agent scoping? | `[verified static]` Installed 1.134.0 source merges hooks from the enabled custom agent matching the selected mode. The global `PreToolUse` payload carries no custom-agent identity, so `hooks/copilot-hooks.json` cannot self-scope. Runtime merge and denial remain `[unverified]`; no real hook was wired. |

## Installed hook-scoping evidence (2026-08-25)

`[verified static]` The exact installed VS Code 1.134.0 / Copilot Chat 0.62.0 bytes were inspected:

- `workbench.desktop.main.js`: SHA-256
  `c42e51f29028d282efaa4b88d7b9e528518123462501b18689d2f05984299ce3`, 18,905,436 bytes;
- Copilot `dist/extension.js`: SHA-256
  `e7e76ceb884e8e63e126fcbe871d8ac471ab278043e5a3657b75009218cde2bf`, 19,135,979 bytes.

The workbench bundle first obtains shared hooks, then uses the selected mode name to find the
enabled custom agent and merges that agent's `hooks` into the request. The Copilot bundle builds
`PreToolUse` input from `tool_name`, `tool_input`, and `tool_use_id` plus the common timestamp,
event, optional session, and transcript fields. It does not add a top-level custom-agent identity.
`SessionStart` has a separate `agent_type` input, but that is not the `PreToolUse` boundary and must
not be used to claim tool-call scoping.

`[sourced]` Current official VS Code documentation shows `hooks:` in custom-agent frontmatter and
describes the common and event-specific input fields. The current documentation mentions
`chat.useCustomAgentHooks`; that literal is absent from the installed 1.134.0 workbench bundle,
which merges agent hooks directly. The documentation and installed implementation therefore agree
on the agent-scoped shape but not on how enablement is surfaced. A runtime canary is required before
the fleet relies on it. See the official
[custom-agent documentation](https://code.visualstudio.com/docs/copilot/customization/custom-agents)
and [hooks reference](https://code.visualstudio.com/docs/copilot/customization/hooks).

`[sourced upstream]` `microsoft/vscode` commit
[`08a1ad0`](https://github.com/microsoft/vscode/tree/08a1ad01b35e41b7412e2290c010cda68bdf6333)
matches the installed control flow. `ChatService.collectHooks` merges only the enabled custom
agent whose name matches the selected mode; `ChatHookService.executePreToolUseHook` then supplies
only the tool name, input, and use ID plus the common fields. See
[`chatServiceImpl.ts`](https://github.com/microsoft/vscode/blob/08a1ad01b35e41b7412e2290c010cda68bdf6333/src/vs/workbench/contrib/chat/common/chatService/chatServiceImpl.ts#L1514-L1542)
and
[`chatHookService.ts`](https://github.com/microsoft/vscode/blob/08a1ad01b35e41b7412e2290c010cda68bdf6333/extensions/copilot/src/extension/chat/vscode-node/chatHookService.ts#L350-L362).
Parsing tests preserve an embedded `PreToolUse` hook, but no upstream end-to-end test was found that
switches between two top-level custom agents and proves hook isolation. That missing runtime case is
why Step 7 remains required rather than treating the source trace as closure.

`[sourced]` Current VS Code documentation describes isolated user-data and extensions directories
for CLI-launched instances and current Copilot Chat as built in. Those documented setup contracts
supported the disposable profile; they are not authority evidence. See the official
[VS Code command-line documentation](https://code.visualstudio.com/docs/editor/command-line) and
[Copilot setup documentation](https://code.visualstudio.com/docs/copilot/setup-simplified).

## Cleanup and limits

- `[verified]` Both attempts ended at `sre`'s `14 Selected` state with `execute` offered-off and a
  clean editor buffer.
- `[verified]` Final generated-file and inspected settings state matched each attempt's baseline;
  Git status was clean before evidence files were written; the original run's Gate A passed all 6
  structural steps.
- `[unverified]` Prompt-file precedence, chat deep links, extension-contributed read-only agents,
  Copilot managed settings, hook payload identity, and other VS Code/Copilot builds were not tested.
- `[unverified]` Invocation authority and agent-scoped hook runtime behavior remain open. The global
  hook payload's missing custom-agent identity is established statically; no fleet hook was wired.
- Optional skill inventory and named handoff observations were not run.
- What this run did **not** do: edit a generated adapter by hand, save picker-produced drift, invoke
  a terminal tool, wire a hook, change a production system, push a branch, or publish evidence.
