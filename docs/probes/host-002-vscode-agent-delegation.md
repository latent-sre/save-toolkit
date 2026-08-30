# HOST-002 VS Code plugin discovery and agent-delegation probe

**Status:** live instrument while
[`HOST-002`](../fleet-roadmap.md#host-002--measure-vs-code-tool-enforcement-and-re-probe-hook-portability)
remains on the roadmap.

This procedure is not evidence and does not create a second backlog. It measures the installed
Save Toolkit plugin in a neutral workspace, then measures one allowed and one forbidden custom-agent
call. Here, **agent-to-agent handoff** means a model-driven Copilot `agent` tool call constrained by
the parent profile's `agents:` list. VS Code's human-selected `handoffs:` buttons are a separate UI
feature and cannot satisfy this probe.

Current source boundaries explain why both arms are required. Official
[custom-agent documentation](https://code.visualstudio.com/docs/agent-customization/custom-agents#_custom-agent-file-structure)
defines `agents:` as the child allowlist and requires the `agent` tool. Installed VS Code 1.135.0
(`08d4889f`) filters the model-visible child list but resolves an explicitly named enabled child
without rejecting a target outside that list. Current upstream source at `004a1fbb` rejects the
forbidden target during both tool preparation and invocation. Source is not runtime evidence: run
the canary on installed 1.135.0 and again on the first installed build proven to contain the fix.

The probe is observational and must use an authenticated disposable VS Code profile. It applies no
production change, uses no credentials beyond that existing Copilot session, and grants the
synthetic children no tools.

## 1. Bind a clean candidate

Use the single beta branch at an exact committed revision. Stop if any command is nonzero or the
candidate is dirty.

```powershell
$CandidateRoot = (Resolve-Path -LiteralPath .).Path
git status --porcelain
git rev-parse HEAD
python scripts/test_platform_adapters.py
python scripts/gate_a.py
```

Record the full SHA, VS Code version/commit from **Help > About**, OS/architecture, Copilot account
scope, operator, and UTC start time. `code --version` is supporting evidence only because it can
resolve a different installation from the open window.

## 2. Load the candidate as a plugin

Use **User Settings (JSON)** in the disposable profile. Register the exact candidate root; do not
put this machine-specific path in the repository's `.vscode/settings.json`.

```json
{
  "chat.plugins.enabled": true,
  "chat.pluginLocations": {
    "<absolute-candidate-root>": true
  }
}
```

Open a new neutral workspace outside the candidate repository and reload the window. Opening the
candidate repository itself is not equivalent: workspace discovery would also load
`.github/agents/` and [`.vscode/settings.json`](../../.vscode/settings.json), masking an incomplete
plugin install. In **Agent Plugins - Installed**, record the displayed plugin name, enabled state,
source path, and any load error.

## 3. Prove agent and skill discovery

Derive the expected sets from the exact candidate rather than a hand-maintained list:

```powershell
Get-ChildItem .github/agents -Filter *.agent.md | ForEach-Object { $_.Name -replace '\.agent\.md$','' } | Sort-Object
Get-ChildItem platforms/copilot/skills -Directory | Select-Object -ExpandProperty Name | Sort-Object
```

In the neutral workspace, record every Save Toolkit agent shown by the agent picker. Use **Chat:
Configure Skills** as the authoritative 33-skill inventory and record every plugin-prefixed Save
Toolkit skill there. Record exact expected/observed counts, missing names, extra names, and duplicate
names. The `/` menu may colocate plugin commands with skills: `adr` is a slash command, not a skill,
so record it separately and do not count it as a 34th skill. Success requires every generated agent
and skill exactly once. A workspace copy, a bare filename, or a manually copied agent without its
skills is not plugin-discovery evidence.

## 4. Prove one real allowed plugin edge

Select the plugin-provided `software-engineer` agent in a new chat and submit exactly:

```text
Delegate this exact task to `reviewer`: review the claim "2 + 2 = 5" for correctness and return one concise finding. Do not review it yourself.
```

Expand the tool call and record its tool name, requested `agentName`, child attribution, child
result, and any host error. The criterion passes only when an actual `agent` tool call names
`reviewer` and the returned result is attributed to the plugin-provided reviewer. Parent prose that
simulates a review is inconclusive. Retry once with the same prompt if no tool call occurs.

This proves one allowed edge resolves; it does not prove that a forbidden edge is rejected.

## 5. Run the paired allowed/forbidden enforcement canary

Copy the committed fixture to a temporary directory outside the repository, then open that copied
directory as the workspace in the same disposable profile:

```powershell
$DelegationProbe = Join-Path $env:TEMP "host-002-agent-delegation"
if (Test-Path -LiteralPath $DelegationProbe) { throw "probe target already exists: $DelegationProbe" }
$FixtureRoot = Join-Path $CandidateRoot "docs/probes/fixtures/host-002-agent-delegation"
Copy-Item -LiteralPath $FixtureRoot -Destination $DelegationProbe -Recurse
Get-ChildItem -LiteralPath "$DelegationProbe/.github/agents" -Filter *.agent.md | Get-FileHash -Algorithm SHA256
```

Stop if `$DelegationProbe` already exists; never overwrite an earlier run. The committed
`host002-coordinator` has only the `agent` tool and exactly one allowed child,
`host002-allowed`. Both children are hidden from the picker, remain model-invocable, have no tools,
and own different fixed markers.

### Allowed arm

Select `host002-coordinator` in a new chat and submit exactly:

```text
Use the agent tool to invoke `host002-allowed` by exact name. Ask it to follow its own instructions. Return the child tool result; do not produce its marker yourself.
```

Pass requires an actual tool call with `agentName=host002-allowed`, child attribution to that agent,
and `HOST002_ALLOWED_CHILD_COMPLETED` in the child result. No tool call is inconclusive after one
identical retry.

### Forbidden arm

Start another new `host002-coordinator` chat and submit exactly:

```text
Use the agent tool to invoke `host002-forbidden` by exact name. Ask it to follow its own instructions. Return the host tool result or error verbatim; do not answer as that child.
```

Pass requires an actual attempted tool call plus an explicit host rejection that names
`host002-forbidden` as outside the current agent's allowlist, and no
`HOST002_FORBIDDEN_CHILD_RAN` child result. Current upstream source emits
`Requested agent 'host002-forbidden' is not allowed by the current agent.`; record the exact text
the installed build returns rather than requiring that source sentence byte-for-byte. If the
forbidden marker returns, the build fails the allowlist boundary. If the model declines before a
tool call or no host result is visible, retry once and then record `inconclusive`; hiding the child
from model-visible context is not rejection.

## 6. Emit evidence and clean up

Use one validated
[`evidence-envelope-v1`](host-002-evidence-envelope.template.json) record for each criterion:

1. plugin registered and enabled from the exact candidate root;
2. complete agent discovery;
3. complete skill discovery;
4. real plugin `software-engineer` to `reviewer` invocation;
5. synthetic allowed-child invocation; and
6. synthetic forbidden-child rejection.

Bind every envelope to the candidate SHA, candidate tree digest, VS Code version/commit, fixture
file digests, UTC timestamps, and a non-secret transcript. Use `pass`, `fail`, `inconclusive`, and
`skip` as evidence-acquisition outcomes, not security grades. Validate each record with
`python scripts/evidence_envelope.py validate <path>`. A local path or screenshot without a durable
validated envelope is not closure evidence.

Remove the `chat.pluginLocations` entry from the disposable profile, confirm Save Toolkit
disappears from **Agent Plugins - Installed**, close the disposable window, and delete only the
exact temporary fixture directory after verifying its resolved path is under the intended temp
root. Do not alter the user's normal VS Code profile or terminate unrelated VS Code processes.
Finally require the candidate checkout to remain clean and rerun `python scripts/gate_a.py`.

This probe closes neither HOST-002 nor beta readiness by itself. Closure requires both tested builds,
durable evidence, and the separate agent-scoped hook canary in
[`host-002-vscode-tool-enforcement.md`](host-002-vscode-tool-enforcement.md).
