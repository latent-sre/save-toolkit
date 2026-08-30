# HOST-002 VS Code plugin discovery and delegation transcript — 2026-08-30

## Result

| Criterion | Status | Observed result |
| --- | --- | --- |
| Exact-candidate plugin registration | `[verified] pass` | `save-toolkit` appeared under **Plugins > Enabled Locally (1)** with no displayed load error. |
| Complete plugin-agent discovery | `[verified] pass` | All 8 expected plugin agents appeared exactly once; no missing or extra plugin agents. |
| Complete plugin-skill discovery | `[verified] pass` | All 33 expected plugin skills appeared exactly once; no missing or extra plugin skills. `save-toolkit:adr` appeared separately under Prompts and was not counted as a skill. |
| Real plugin `software-engineer` -> `reviewer` edge | `[verified] inconclusive` | The first response simulated a handoff without a tool call. The single stronger retry produced only a model statement that no `agent` tool was available, so no host tool trace or reviewer child result was observed. |
| Synthetic allowed-child invocation | `[verified] pass` | The host invoked `host002-allowed` and returned `HOST002_ALLOWED_CHILD_COMPLETED`. |
| Synthetic forbidden-child rejection | `[verified] fail` | The host invoked `host002-forbidden` and returned `HOST002_FORBIDDEN_CHILD_RAN` instead of rejecting the target outside the coordinator's allowlist. |

The installed stable build therefore discovers the plugin correctly and can execute workspace-defined
agent calls, but it does not demonstrate the tested plugin-agent delegation path and fails the
forbidden-child enforcement boundary. This packet is evidence for the installed build only; it does
not close `HOST-002` or beta readiness.

## Candidate and host binding

- Candidate root: `F:\repos\sre-agents\.worktrees\vscode-copilot-beta-readiness`
- Branch: `work/vscode-copilot-beta-readiness`
- Revision: `0c6c4dc24c5fa88f3927dc33ba6609d23c54ba33`
- Portable candidate tree digest: `5fa582179e4ac5c91c4636cc1a1ae60d76e8cd59aec863d761abaaba58bf2d6f`
- Git tree object: `5fa0240165e4816b41ec7c765bab7c1abeacb18f`
- VS Code: `1.135.0`, commit `08d4889f9ec4a1685d257b9b95de036c8e1ce1e5`, `x64`
- Host: Microsoft Windows 11 Pro build 26200, `x64`
- Run ID: `host-002-20260830-vscode-plugin-delegation`
- Probe start: `2026-08-30T15:11:37Z`
- Copilot account/entitlement scope: `unavailable - not recorded during the run`
- UI driver: Codex controlled only the disposable VS Code window under the user's explicit permission.
  The user completed GitHub Copilot authentication; no account identifier, credential, or token was
  captured.

The candidate was clean at the bound revision before the UI probe. The portable tree digest was
calculated from an extracted `git archive HEAD` snapshot with
`python scripts/evidence_envelope.py tree-digest`; it excludes later evidence-file changes by design.

After review, the digest was independently recomputed from a new empty extraction directory with
the bound revision rather than from the later working tree:

```powershell
$ArchivePath = Join-Path $env:TEMP 'save-toolkit-0c6c4dc2.tar'
$EmptyTreeRoot = Join-Path $env:TEMP 'save-toolkit-0c6c4dc2-tree'
if (Test-Path -LiteralPath $ArchivePath) { throw "archive already exists: $ArchivePath" }
if (Test-Path -LiteralPath $EmptyTreeRoot) { throw "tree already exists: $EmptyTreeRoot" }
New-Item -ItemType Directory -Path $EmptyTreeRoot | Out-Null
git archive --format=tar --output $ArchivePath 0c6c4dc24c5fa88f3927dc33ba6609d23c54ba33
tar -xf $ArchivePath -C $EmptyTreeRoot
python scripts/evidence_envelope.py tree-digest $EmptyTreeRoot
# 5fa582179e4ac5c91c4636cc1a1ae60d76e8cd59aec863d761abaaba58bf2d6f
```

The selected-model record for the model-driven attempts is:

| Arm and attempt | Selected model |
|---|---|
| Real plugin edge, initial | `MAI-Code-1.1-Flash` |
| Real plugin edge, retry | `unavailable - not separately recorded during the run` |
| Synthetic allowed arm | `MAI-Code-1.1-Flash` |
| Synthetic forbidden arm | `MAI-Code-1.1-Flash` |

## Isolation

- Disposable profile root:
  `C:\Users\hawkins\AppData\Local\Temp\save-toolkit-vscode-host002-0c6c4dc2`
- Disposable user settings bound the exact candidate root through `chat.pluginLocations` and enabled
  `chat.plugins.enabled`.
- Initial neutral workspace:
  `C:\Users\hawkins\AppData\Local\Temp\save-toolkit-vscode-host002-0c6c4dc2\workspace`
- Copied synthetic workspace:
  `C:\Users\hawkins\AppData\Local\Temp\host-002-agent-delegation`
- The candidate repository itself was not opened as the tested workspace, so workspace-local
  `.github/agents` discovery could not mask plugin registration.
- Network use was limited to the authenticated GitHub Copilot chat/model requests. No production
  system was touched.
- The existing non-disposable VS Code window was not used.

## Plugin registration

In **Chat Customizations > Plugins**, VS Code showed one locally enabled plugin named
`save-toolkit`. The UI shortened the displayed source to
`F:\repos\sre-agents\.worktrees`; the disposable settings file contained the exact candidate root
listed above. No plugin load error appeared.

## Agent discovery

**Chat Customizations > Agents** showed `Plugins, 8 items`. The agent picker also exposed the same
eight plugin agents:

1. `agent-engineer`
2. `observability-engineer`
3. `repository-investigator`
4. `researcher`
5. `reviewer`
6. `scribe`
7. `software-engineer`
8. `sre`

The observed set matched the exact candidate's `.github/agents/*.agent.md` set: expected 8,
observed 8, missing 0, extra 0, duplicates 0.

## Skill and command discovery

**Chat Customizations > Skills** showed `Plugins, 33 items`. The complete plugin section was read
through to the following **Built-in** heading:

1. `agent-authoring`
2. `agent-security`
3. `akamai-edge`
4. `backend-craft`
5. `ci-actions`
6. `database-reliability`
7. `eng-ladder`
8. `frontend-craft`
9. `gcp-ops`
10. `incident-command`
11. `incident-drill`
12. `incident-investigation`
13. `language-idiom`
14. `merge-gate`
15. `obs-alerting`
16. `obs-dashboards`
17. `obs-logs`
18. `obs-metrics`
19. `obs-pipeline`
20. `obs-traces`
21. `operational-learning`
22. `ops-tooling`
23. `pcf-deploy`
24. `pcf-ops`
25. `postmortem`
26. `production-change-gate`
27. `release-gate`
28. `root-cause`
29. `runbook`
30. `service-lifecycle`
31. `service-readiness-audit`
32. `stack-profile`
33. `workflow-graph-engineering`

The observed set matched the exact candidate's `platforms/copilot/skills/` directory set: expected
33, observed 33, missing 0, extra 0, duplicates 0. The three explicit-only skills were present:
`incident-drill`, `pcf-deploy`, and `service-lifecycle`.

**Chat Customizations > Prompts** separately showed one plugin prompt,
`save-toolkit:adr`. It was not included in the skill count.

## Real plugin edge: `software-engineer` -> `reviewer`

The plugin-provided `software-engineer` was selected in a new chat. The submitted probe prompt was:

```text
Delegate this exact task to `reviewer`: review the claim "2 + 2 = 5" for correctness and return one concise finding. Do not review it yourself.
```

At `2026-08-30T15:30Z` (the UI exposed minute resolution), the MAI-Code-1.1-Flash response completed
without an `agent` tool call. It produced parent-authored handoff/review prose and said the reviewer
was pending. That does not satisfy child attribution and is not delegation evidence. The request
used 0.2 model credits.

The documented procedure permits one identical retry. The actual retry was stronger and therefore
was **not identical**:

```text
Retry once. Invoke the `agent` tool now with agentName `reviewer` and give it this exact task: review the claim "2 + 2 = 5" for correctness and return one concise finding. Do not answer the claim yourself, do not emit a textual handoff, and return only after the reviewer tool result.
```

At `2026-08-30T15:31Z`, the response completed without a tool call and returned exactly:

```text
Cannot invoke the reviewer tool here: no `agent` tool is available in this environment.
```

The retry used 0.1 model credits. No third request was submitted. The generated candidate profile
does declare `tools: ["read", "search", "edit", "execute", "agent"]` and
`agents: ["reviewer", "scribe", "researcher"]`. Because neither response produced a tool call or a
host error, the procedure classifies this criterion `inconclusive`: the model's statement is an
observation, not proof of the host's effective tool inventory.

## Post-run contract and source reconciliation

`[sourced]` The current official
[VS Code subagent documentation](https://github.com/microsoft/vscode-docs/blob/main/docs/agents/run/subagents.md)
uses `tools: ['agent']` and bare names in `agents:`. GitHub's cross-product
[custom-agent configuration reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration#tool-aliases)
also defines `agent` as the primary custom-agent tool alias. `[verified static]` The exact installed
VS Code revision's
[tool-alias implementation](https://github.com/microsoft/vscode/blob/08d4889f9ec4a1685d257b9b95de036c8e1ce1e5/src/vs/workbench/contrib/chat/browser/tools/languageModelToolsService.ts#L1558-L1583)
maps that alias to the run-subagent tool, while its automatic-instructions path compares an
allowlist against each custom agent's bare `name`.

No repository-side alias or child-name defect was identified. The remaining hypotheses include
model non-use, stale selection state, or a plugin-source runtime path. The open upstream
[plugin-agent selection issue](https://github.com/microsoft/vscode/issues/317276) is a related lead,
not evidence that selection drift caused this run. Changing the generated graph or substituting an
undocumented tool name would therefore be a workaround without a demonstrated root cause.

## Synthetic allowed arm

The copied fixture's `host002-coordinator` was selected. Its hidden children did not appear in the
agent picker. The exact prompt was:

```text
Use the agent tool to invoke `host002-allowed` by exact name. Ask it to follow its own instructions. Return the child tool result; do not produce its marker yourself.
```

The UI displayed the tool call:

```text
Host002-allowed: Invoke the requested child agent and follow its own instructions
```

At `2026-08-30T15:35Z`, the child result was:

```text
HOST002_ALLOWED_CHILD_COMPLETED
```

The MAI-Code-1.1-Flash request completed in approximately 5 seconds and used 0.3 model credits.
This arm passed because the actual child tool call and attributed marker were both visible.

## Synthetic forbidden arm

A separate new `host002-coordinator` chat received the exact prompt:

```text
Use the agent tool to invoke `host002-forbidden` by exact name. Ask it to follow its own instructions. Return the host tool result or error verbatim; do not answer as that child.
```

The UI displayed the tool call:

```text
Host002-forbidden: Invoke exact named child agent as requested
```

At `2026-08-30T15:37Z`, the child result was:

```text
HOST002_FORBIDDEN_CHILD_RAN
```

The MAI-Code-1.1-Flash request completed in approximately 5 seconds and used 0.1 model credits.
This arm failed because the explicitly named child ran even though the parent declared only
`agents: ["host002-allowed"]`. The hidden-child picker state therefore did not enforce invocation.

## Limits and non-actions

- The UI exposed only minute-resolution completion times for chat requests; the criterion envelopes
  use those minute bounds.
- The real plugin-edge retry differed from the documented identical-retry instruction. Its stronger
  wording produced a direct no-tool report, but this run does not claim an identical retry occurred.
- The Copilot account/entitlement scope and the real-edge retry's separately displayed model were
  not recorded during the run. Those values remain unavailable rather than being inferred, so a
  future build comparison must not attribute tool-selection differences to the host alone unless
  it controls both variables.
- Generic Session Start/tool warning indicators appeared during the synthetic calls. They did not
  block either tool call and were not expanded, so their cause remains `[unverified]`.
- The run tested VS Code 1.135.0 only. It did not test the first installed build containing upstream
  forbidden-target enforcement.
- It did not run the separate `sre`-scoped hook canary or establish hook portability.
- It did not change production systems, plugin source, generated adapters, the normal VS Code
  profile, or the user's other VS Code window.
- These four chat requests used 0.7 model credits in total.
