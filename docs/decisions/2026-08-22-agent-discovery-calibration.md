# Agent discovery is model-labelled calibration

**Status:** accepted 2026-08-22; disposes `EVAL-002`.

## Decision

Classify every Claude discovery scenario whose target is an agent as `calibration`, never
`regression`. These cases measure whether a headless main session chooses to delegate before it can
measure which agent it selects. That inline-versus-delegate choice is a model/host propensity, not a
fleet contract.

Keep the 23 existing agent-discovery prompts as optional diagnostics. Every live result must name
the model, Claude CLI version, plugin revision, and trial count. Run one only for a named host/model
question and stop at the declared count; it does not block merge, release, or a description change.
Direct-agent scenarios remain the behavioral contract after explicit selection. They do not prove
description routing, and their current coverage is not complete enough to claim otherwise.

The validator rejects `mode: discovery` plus `target.kind: agent` plus `split: regression`. A focused
red-first test proves that rule. The nine existing agent-discovery regression cases move to
calibration; no prompt, grader, agent description, or execution path changes.

## Evidence

On 2026-08-22 the investigation recorded `routing saw []` for all 23 agent-target discovery cases
under the session model. Focused controls established that this was not a missing plugin, tool, or
detector:

- Opus 5 dispatched 0/3 for `sde`, 0/3 for `observability-engineer`, and 0/3 for `sre` on the edited
  tree (`20260822T192621Z-8f12df60`, `20260822T192824Z-0ade0996`, and
  `20260822T193550Z-f275ff9b`). The responses still loaded relevant skills and satisfied the
  substantive keyword graders.
- Opus 5 also dispatched 0/3 for the same `sre` scenario on pristine main
  `007fcc601fbcd74296d80456adbebeeb96a16626` (`20260822T194152Z-69f2665d`).
- Sonnet 5 emitted the expected `save-toolkit:sre` dispatch in 3/3 trials on the edited-tree control
  (`20260822T195008Z-5170eca5`). One completed and passed; two reached the 300-second timeout while
  the subagent was still working, so the batch verdict was `INCONCLUSIVE`, not 3/3 PASS.
- Init traces listed all eight plugin agents and the `Task`/`Skill` tools. The Sonnet traces and a
  forced probe emitted the exact `Agent` plus `subagent_type` event recognized by the parser.

The clean room deliberately starts in an empty Git root outside the repository, so project
`AGENTS.md` and `CLAUDE.md` routing instructions are absent. Pinning a model would make only that
model's propensity repeatable; adding a dispatch instruction would stop measuring an ordinary,
unhinted request. Neither creates a fleet-owned routing contract.

At the default three trials, reclassification reduces the visible regression run from 37 scenarios
and 111 model processes to 28 scenarios and 84 processes. The 27 removed calls represented 135
minutes of configured timeout budget per full run. Existing paired Opus/Sonnet evidence answers the
decision, so acceptance requires no additional paid run.

## Reopen trigger

Revisit only when a host exposes a deterministic agent-selection contract, or a real consumer
failure under a named host/model shows that autonomous delegation is required. Start with one focused
scenario and a fixed budget; do not restore a fleet-wide dispatch sweep or convert every calibration
case into a direct test.
