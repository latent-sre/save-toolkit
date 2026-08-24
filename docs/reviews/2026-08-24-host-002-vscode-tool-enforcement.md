# HOST-002 VS Code tool-enforcement observation

**Conclusion:** `[verified]` On VS Code 1.134.0, every tested omitted built-in tool remained in the
picker as disabled, and a global default-Agent selection displayed `execute` as enabled after
switching to `sre`. The picker dirtied the open generated-agent editor buffer while the on-disk file
and Git status remained unchanged. `[unverified]` No command or host denial ran after that
non-file-mutating precondition failed, so this run does not establish `sre` invocation authority or
host enforcement.

This supports the existing `AGENTS.md` warning at the configuration layer and sharpens its
persistence language. It does not establish an authority boundary, hook boundary, managed-policy
result, or host-side denial of an execute call.

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
- Operator-local evidence archive: `F:\repos\HOST-002-evidence-20260824.zip`, SHA-256
  `31dc110ad0c1d05bb1362f772893977181e74964f57f1f44a993f92115376277`, 2182308 bytes. It was
  intentionally not added to Git or the PR and is not durable review evidence.
- `[verified]` The operator validated all eight JSON records with `scripts/evidence_envelope.py` and
  matched every local artifact path, byte size, and SHA-256. Reviewers cannot independently repeat
  that binding from the PR until the non-secret records are retained in a durable reviewable place.

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

## Acceptance mapping

| HOST-002 question | Evidence-bound answer |
|---|---|
| Does the picker offer `execute` to `sre`? | `[verified]` Yes, offered-off at the generated default. |
| Does the tested override display it as enabled after switching? | `[verified]` Yes. The UI calls the selection global, and its checked state survives switching to `sre`; it is not session-only. |
| Does the picker mutate `.github/agents/sre.agent.md` on disk? | `[verified]` Not during this run. It mutated the open editor buffer while disk and Git stayed unchanged. Saving that buffer was deliberately avoided. |
| Can `sre` invoke `execute`, or does the host deny it? | `[unverified]` No tool call or host denial was observed. Configuration state cannot answer this authority question. |
| Are the raw evidence records durably reviewable? | `[unverified]` No. The ZIP remains operator-local and was not added to this PR. |
| Is the Copilot hook portable with exact-agent scoping? | `[unverified]` Not tested; no hook was wired. |

`[sourced]` Current VS Code documentation describes isolated user-data and extensions directories
for CLI-launched instances and current Copilot Chat as built in. Those documented setup contracts
supported the disposable profile; they are not authority evidence. See the official
[VS Code command-line documentation](https://code.visualstudio.com/docs/editor/command-line) and
[Copilot setup documentation](https://code.visualstudio.com/docs/copilot/setup-simplified).

## Cleanup and limits

- `[verified]` Final `sre` state: `14 Selected`; `execute` offered-off; editor buffer clean.
- `[verified]` Final generated-file and workspace-settings digests matched the baseline; Git status
  was clean; Gate A passed all 6 structural steps.
- `[unverified]` Prompt-file precedence, chat deep links, extension-contributed read-only agents,
  Copilot managed settings, hook payload identity, and other VS Code/Copilot builds were not tested.
- `[unverified]` The local transcript/envelopes are not durable review evidence and cannot close the
  roadmap item until retained in an approved reviewable location.
- Optional skill inventory and named handoff observations were not run.
- What this run did **not** do: edit a generated adapter by hand, save picker-produced drift, invoke
  a terminal tool, wire a hook, change a production system, push a branch, or publish evidence.
