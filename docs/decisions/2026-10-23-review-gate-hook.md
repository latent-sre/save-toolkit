# ADR: Gate software-engineer's return on the five-file review rule with a stop hook

- Date: 2026-10-23
- Status: Proposed; disposes the mechanism question in `PRECOMMIT-001` when the owner accepts it
- Decision owners: save-toolkit maintainers

## Context

`software-engineer`'s Review decision says: dispatch `reviewer` for five or more files changed by
the task unless every change is a nit, the caller declines review, or the caller owns it. Paired
native runs on 2026-10-22 (Sonnet 5.5, CLI 2.1.309) measured the unprompted case at 0/9 across
`main`, the trim candidate in PR #411, and a rewrite of the rule, while the six over-trigger
controls stayed green. The reports quote the rule and then do not spawn: "the change touches five
files, which would normally trigger one". The same agent dispatched `reviewer` 3/3 when the prompt
asked for a review. Three earlier rewrites since 2026-10-07 measured at or below 1/3.

Two facts place the failure outside the prompt. The Agent tool's own description in CLI
2.1.306–2.1.309 reads "Delegate review only when you want a read that isn't anchored on yours" and
"When in doubt, don't spawn", and a `--agent` session holding `Agent(...)` receives it. Anthropic's
hooks guidance says a prompt instruction is advisory and a `Stop` hook that blocks the turn until a
check passes is the enforcement. API-level forcing is unavailable: `tool_choice` `any` and `tool`
return 400 on the 5.5 models. Plugin agents ignore frontmatter `hooks`, so a gate lives in
`hooks/hooks.json`.

A probe on 2.1.309 established the mechanics: `claude -p --agent` runs the agent as the main thread,
so `Stop` fires there with `agent_type` set to the agent's name and `SubagentStop` does not; exit 2
blocks the return and the model continues with the hook's reason; the next `Stop` arrives with
`stop_hook_active: true`. A dispatched `software-engineer` fires `SubagentStop` instead, whose
payload carries `agent_type`, `agent_id` and `agent_transcript_path`.

A script cannot judge the nit exemption or whether the caller owns review. So the gate proposed
here is a forced reconsideration at the moment the rule applies, not a hard stop: it blocks the
return once, names the three legitimate exits, and lets the second return through.

## Options

1. **Stop and SubagentStop hook in `hooks/hooks.json`** (proposed). Deterministic, uses the fleet's
   existing hook pattern, measurable with the existing probes. Cost: one extra turn per blocked
   return; cannot tell a nit set from a feature; new state (a start snapshot) to keep.
2. **Caller dispatches `reviewer` after the return.** Already works (the caller-ownership pilot's
   mode) and needs no code. Cost: every caller must remember; direct human use gets no default
   review, which is the SRE task PRECOMMIT-001 exists for.
3. **Recommendation-only default.** Change the scenario's expectation to "names the review it
   recommends". Cost: gives up the SRE task; the measured behavior becomes the contract.
4. **Another wording.** Measured 0/9 on the latest three revisions and at or below 1/3 since
   2026-10-07. Not a candidate.

## Decision (proposed)

Add `scripts/review-gate.py`, wired for `Stop` and `SubagentStop` in `hooks/hooks.json`, with a
start snapshot taken on `SessionStart` and `SubagentStart`.

### Scope

- Agents: `software-engineer` only, matched in Python on `agent_type` as `software-engineer` or
  `save-toolkit:software-engineer`, with the read-only guard's two canaries: a guarded bare name
  under another namespace, and a guarded identity under another `agent`-named key when
  `agent_type` is absent. No hook matcher, for the reason CONTRIBUTING gives: a matcher can stop
  matching after an upstream rename without any signal.
- Events: `Stop` (the `--agent` main thread and direct use) and `SubagentStop` (a dispatched
  worker). `SessionStart` and `SubagentStart` write the snapshot; neither can block.
- Hosts: Claude Code. VS Code and Copilot keep their own hook files and are a later projection.
  The POSIX launcher ships first; the PowerShell launcher follows the `readonly-guard-hook.ps1`
  pattern before the gate is relied on from a Windows host.

### Snapshot at start

Key: `session_id`, plus `agent_id` when present. Location: `$CLAUDE_PLUGIN_DATA/review-gate/`,
falling back to the OS temp directory when that variable is unset (the eval runner's clean
environment may not export it). Content: `HEAD`, and for every path `git status --porcelain`
reports, the blob hash of its working-tree content. A directory that is not a Git repository
writes no snapshot.

### Count at stop

Changed by the task = paths whose working-tree hash differs from the snapshot, paths new or deleted
since it, and paths named by `git diff --name-only <snapshot HEAD>..HEAD` when the task committed.
A path dirty at start and byte-identical at stop is excluded. This follows the Review decision's
file-count rule: already-dirty files the task changes count; unrelated pre-existing changes do not.
Without a snapshot the count is every dirty path plus nothing from history, and the reason says the
count is approximate.

### Reviewer detection

Read the subagent's transcript (`agent_transcript_path`) on `SubagentStop` and the session
transcript (`transcript_path`) on `Stop`. A completed review is an assistant `tool_use` named
`Agent` or `Task` whose `input.subagent_type` is `save-toolkit:reviewer` or `reviewer`, followed by
a `tool_result` for the same id that is not an error and whose `toolUseResult.status` is absent or
not `async_launched`. The transcript can lag the turn, so the read is retried three times a second
apart before concluding that no review ran. `last_assistant_message` is never consulted: it can
claim a review that did not happen.

### Decision rule

Block when all of these hold: the agent is `software-engineer`; `stop_hook_active` is false; the
count is at or above the threshold; no completed review was found. The threshold is one constant in
the script, `REVIEW_FILE_THRESHOLD = 5`, and a test asserts that the agent body's Review decision
names the same number, so the two cannot drift apart. The block is exit 2 with this reason:

> save-toolkit review gate: this task changed N files (threshold 5) and no `reviewer` dispatch
> completed. Before returning, do one of: dispatch `save-toolkit:reviewer` with the target, base and
> candidate, untracked scope, and your verification; or state in the report that every change is a
> nit and name them; or state that the caller declined or owns review, quoting the brief. Then
> return.

Everything else allows. Allowing is exit 0 with empty stdout; when the gate could not measure, it
allows and attaches `hookSpecificOutput.additionalContext` saying why, so the condition is visible
in the transcript without an error notification.

### Failure posture

Fail open. The read-only guard fails closed because its failure mode is a credential read; this
gate's failure mode is one missed reminder, and the caller's own gate still stands. The launcher
keeps the guard's distinct exit codes (42 allow, 43 block, 44 indeterminate) so a stand-in
interpreter exiting 0 is not mistaken for an allow, and the existing `SessionStart` preflight
already reports a missing interpreter. `SAVE_TOOLKIT_REVIEW_GATE=0` disables the gate for a
session, for callers that own review by contract and want no extra turn.

## Consequences

- One deterministic prompt at the right moment, for every return that meets the rule. The agent
  can still decline; the hook makes the decision explicit instead of silent, and the second return
  passes with whatever it says.
- Nit-only five-file tasks (two of the controls) get the block once. Whether the reason pushes them
  into spawning is the main over-trigger risk and is measured before acceptance.
- Every `software-engineer` return reads the transcript once and runs `git status`; the cost is
  milliseconds. Blocked returns cost one extra model turn.
- The transcript's `toolUseResult.status` field and `agent_type` on `SessionStart` are observed, not
  documented. Both are canaried: a recorded transcript fixture pins the shape, and an unrecognized
  shape fails open with an `additionalContext` note rather than blocking.
- The eval runner loads the plugin with `--plugin-dir`, so the existing probes measure the gate as
  shipped; no new scenario is needed for the first measurement.

## Verification

Offline, in `scripts/test_review_gate.py` and `scripts/test_hook_wiring.py`, each case red before
the change and green after:

1. A payload for another agent, or for the main loop with no `agent_type`, allows.
2. Four changed files and no review allows; five blocks with the reason above.
3. Five changed files and a completed `reviewer` `tool_use`/`tool_result` pair allows; a pair whose
   status is `async_launched` blocks.
4. `stop_hook_active: true` allows regardless of count.
5. A file dirty at start and untouched is not counted; dirty at start and edited is; a file changed
   in a commit made during the task is.
6. No Git repository, no snapshot, an unreadable transcript, and a transcript of unrecognized shape
   each allow and attach `additionalContext`.
7. The namespace canaries block a guarded bare name under a foreign namespace.
8. `hooks.json` registers `Stop`, `SubagentStop`, `SessionStart` and `SubagentStart` entries that
   call the gate through the distinct-exit-code launcher, and no entry carries an agent matcher.
9. The threshold constant equals the number in the agent body's Review decision.

Live, before acceptance: paired runs with `evals/build_probe.py run --model sonnet`, candidate with
the gate against `main` without it, three trials each, on
`build-software-engineer-reviews-nontrivial-change`,
`build-software-engineer-reviews-task-changes-in-dirty-files`, and the six over-trigger controls.
Acceptance: the two dispatch probes rise from 0/3 to at least 2/3 each, every control keeps its
`main` result, and the blocked trials' transcripts show the reason delivered once. A `python` shim
is on PATH for the oracles on this host.

## Rollout and recovery

The change ships in `hooks/hooks.json`, `scripts/review-gate.py`, the launcher scripts, the tests,
and a CONTRIBUTING line under guard scoping. Rollback is reverting that commit; the snapshot files
under `$CLAUDE_PLUGIN_DATA/review-gate/` are inert without the hook and can be deleted.

## Decisions for the owner

1. Fail open, as proposed, or fail closed like the read-only guard.
2. Block once, as proposed, or block until the report contains one of the three exits in a
   detectable form, which needs a machine-readable review field in the packet.
3. The acceptance bar above, or a different trial count.
4. Windows in the first change, or after the POSIX measurement.
