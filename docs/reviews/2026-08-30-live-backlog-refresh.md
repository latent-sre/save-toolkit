# Live backlog refresh — 2026-08-30

**Status:** Historical evidence captured on 2026-08-30. The
[`fleet roadmap`](../fleet-roadmap.md) is the only live backlog; this packet records why its status
and next-action text changed and does not queue work independently.

## Boundary

- `[verified]` Local `main` and refreshed `origin/main` were identical at
  `41406af0d0b18f1b07441e0194ae2d7e7c4e6438` after `git fetch --prune origin` and
  `git pull --ff-only origin main`.
- `[verified]` GitHub reported no open pull requests. Published or local branches below are evidence
  or work in progress, not merged-main behavior.
- `[verified]` `work/live-doc-cleanup` was one local commit ahead of that base. Its existing change
  already closed GRAPH-002, unblocked GRAPH-003, and repaired current-tense documentation gates.
- `[verified]` Dirty or separately owned worktrees were inspected read-only and not modified.

## Dispositions

| Item | Refreshed evidence | Tracker consequence |
|---|---|---|
| `GRAPH-002` | PR #193 merged at `4a745fb311ad7df83ec6aeaf3268356ce4780db5`; its four hosted checks were green, and `graph-sandbox/` is tree-identical to remediation revision `56ebece6d34d30eaa2b6bf5725a1d4a70ecb25f9` | Closed; retain the earlier full fault matrix as historical evidence only |
| `GRAPH-003` | Its sole blocking implementation is on main | Ready; measure current sandbox output rather than relabelling historical GRAPH-002 samples |
| `CONTEXT-001` | Save-toolkit main has both consumer sidecars; sre-context main has two synthetic tenants; two exact, unmerged cross-repository follow-ups remain | Active; replace the obsolete build instructions with review, merge, and paired exact-revision verification |
| `ROUTE-003` | Both named routing surfaces materially changed after deferral | Ready; the reopen trigger fired, but no paid or retrying measurement is implied |
| `GRAPH-004` | Owner-accepted scope and implementation exist on a published branch; local implementation is continuing | Active; stop asking for a need or owner and finish the existing isolated candidate |
| `SKILL-001` | The candidate screen remains valid, but no `backend-craft` work branch exists | Active; select the next one-skill slice instead of claiming it is already in progress |
| `HOST-002` | Installed VS Code 1.135.0 recognizes `agents:` but lacks current upstream's deterministic named-target rejection | Active; test the installed/first-containing-build boundary, without claiming source inspection is a live invocation |
| `WF-001` | Installed Claude Code 2.1.251 changed `scriptPath` permission order but still documents dynamic workflow scripts rather than immutable exact-workflow binding | Blocked; refresh the evidence date without manufacturing an unblock |
| `EVAL-007` | The next action is an owner choice between two grading architectures | Decision-needed; no implementation starts until that choice is made |

## Repository and sibling evidence

### CONTEXT-001

`[verified]` On refreshed save-toolkit main, both
`skills/service-readiness-audit/context-requirements.yaml` and
`skills/service-lifecycle/context-requirements.yaml` exist and both skills link their sidecars.
Commit `ff451f2b` introduced the pair. The current asset test covers the lifecycle sidecar's
non-operational source, prohibited action selection, forbidden credential/approval paths, and
production-gate language.

`[verified]` Refreshed `latent-sre/sre-context` main is
`903ac830155059d2d357e7f446378752ea8f5a38` and its resolver tests exercise both synthetic
`tenant-alpha` and `tenant-beta`. Producer branch
`work/context-001-lifecycle-contract` remains at
`458f39c24c5523d2f159c373786e05e9072a5b3b`; it adds the lifecycle mirror and paired resolver/CLI
coverage. Consumer branch `work/context-001-close-contract-gap` remains at
`96e1784d3e8977732ddf7e3df4f012b04f69e55a`; it strengthens the already-present lifecycle safety
test. Neither branch has a pull request. Branch publication is not closure.

### ROUTE-003

`[verified]` The deferred closeout used merged revision `09e775b`. After it, commit `f1afd574`
introduced `workflow-graph-engineering`; `afb6f846`, `ee80ba67`, `bbc228ad`, and `c6d928c9` changed
the service-readiness route, its related lifecycle vocabulary, or the evaluator surface. This
satisfies the roadmap's own material route/evaluator change trigger. The previous timeouts remain
evidence and do not authorize tuning or repeated retries.

### GRAPH-004

`[verified]` Published `origin/work/graph-004-fleet-atlas` was
`0828418c566a929329a83cf6b3d162348adf49fa`. Its committed decision packet records owner acceptance,
names `fleet-atlas` rather than a general code/GraphRAG atlas, and changes the roadmap item to ready.
The local isolated branch had advanced to `8f4937933f2dd2367a526be62188913576fb13ef`, two commits
ahead of the published ref, with an untracked generated-view directory and no pull request. That
makes the live state `active`, not `decision-needed`, but does not make the candidate merged or
accepted.

### SKILL-001

`[verified]` A Git-object measurement on exact main found 33 entrypoints totaling 225,466 immutable
bytes. The seven non-Phase-1 candidates other than dispositioned `agent-authoring` remain
`obs-dashboards` 11,419, `backend-craft` 11,123, `runbook` 9,561,
`workflow-graph-engineering` 8,622, `incident-drill` 8,154, `obs-alerting` 7,755, and the accepted
`gcp-ops` candidate 7,679 bytes. No local or remote `backend-craft` Phase 2 branch exists.

## Host and public-source evidence

### HOST-002

`[verified static]` Installed VS Code is 1.135.0 at source revision
`08d4889f9ec4a1685d257b9b95de036c8e1ce1e5`. Its installed bundle carries
`allowedSubagents`, but the exact upstream source for that revision sets
`allowedSubagents: undefined` in `runSubagentTool.ts` and contains no
`validateSubagentAllowed` call.

`[sourced]` Current official VS Code documentation defines custom-agent `agents:` as an allowlist,
with `[]` disabling subagent use and an explicit list restricting named targets:
[`subagents.md`](https://github.com/microsoft/vscode-docs/blob/main/docs/agents/run/subagents.md).
GitHits source inspection at `microsoft/vscode@004a1fbb` found deterministic rejection in both
prepare and invoke paths at
[`runSubagentTool.ts`](https://github.com/microsoft/vscode/blob/004a1fbb/src/vs/workbench/contrib/chat/common/tools/builtinTools/runSubagentTool.ts).
The current-source contract and installed-source absence agree that an installed-build canary is
still required; neither proves a live forbidden invocation on this host.

### WF-001

`[verified]` Installed Claude Code is 2.1.251. No paid or uploading ultrareview run was launched.

`[sourced]` Current official Claude Agent SDK documentation exposes `Workflow` as dynamic local or
remote execution and returns `scriptPath`; exact skill names can separately be selected or invoked,
but those skill controls do not bind one immutable Workflow implementation:
[`Workflow` tool](https://code.claude.com/docs/en/agent-sdk/typescript) and
[`Agent SDK skills`](https://code.claude.com/docs/en/agent-sdk/skills).
GitHits inspection of `anthropics/claude-code@f1af9b1f` found that 2.1.251 fixed the Workflow tool
reading and quoting an out-of-scope `scriptPath` before permission evaluation. That is an important
permission-order fix, not the exact trusted-workflow binding or findings-sensitive ultrareview
verdict WF-001 requires.

### EVAL-007

`[verified]` The repository already supplies deterministic `exact_fields`, `exact_json`, and
`embedded_exact_json` graders. An LLM judge would add a nondeterministic grader policy. The item can
therefore proceed only after the owner chooses the output contract; calling it ready hides that
load-bearing decision.

## Verification of the tracker change

`[verified]` On the complete working tree after the roadmap correction:

- `python scripts/check_plan_status.py`, `python scripts/check_evidence_refs.py`, and
  `python scripts/check_links.py` passed.
- `python scripts/test_plan_status.py` passed 19 tests; `python scripts/test_check_links.py` passed
  39 tests with one platform-specific skip; `python scripts/test_check_evidence_refs.py` passed 3
  tests.
- `python scripts/test_skill_asset_contracts.py` passed 7 tests.
- `python evals/test_graders.py` passed 1,364 checks, and `python evals/run_evals.py --validate`
  validated 136 scenarios. These are offline contract checks, not model-behavior measurements.
- `python scripts/gate_a.py` passed all eight structural steps. Gate A does not prove semantic
  freshness, host invocation authority, external branch acceptance, or model behavior.
- `git diff --check` and a separate trailing-whitespace check for this new untracked packet passed.

## Non-actions and remaining uncertainty

- No external branch was merged, rebased, pushed, or deleted; no pull request was opened.
- No live model campaign, paid call, VS Code forbidden-target invocation, hook canary, upgrade, or
  production action ran.
- GRAPH-004 and Copilot worktrees retain their separate ownership and dirty-state boundaries.
- Structural checks can validate roadmap shape and links, but they cannot prove that external branch,
  host, or product state is still current; every such fact above is dated and revision-bound.
