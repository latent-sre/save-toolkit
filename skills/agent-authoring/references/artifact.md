# Artifact altitude — author and optimize one LLM-facing artifact

## The bounds on the loop

Before the first iteration, write down every row:

| Contract field | This loop's term |
|---|---|
| Entry and mutable state | The named artifact plus its regression cases; nothing else is edited |
| Test/eval evidence | An author may report a named test/eval PASS with its command, exact candidate, and scope. A self-authored grader is not independent review and never promotes a candidate. |
| Hard iteration budget | One candidate by default; an explicitly approved optimization may evaluate two or three total; every evaluated revision counts |
| Hard time/cost budget | A fixed call or cost budget set with the candidate budget; reaching it stops the loop |
| Success termination | Failure repair: incumbent demonstrates the named failure and candidate passes on identical cases and conditions. New behavior: candidate meets the frozen criterion. Existing passing regressions stay green |
| No-progress termination | A tie, or a missing or inconclusive candidate result, stops the loop; neither is success |
| Safety/authority stop | Any safety, authority, or existing-regression regression stops the loop and retains the incumbent |
| Promotion authority | Human acceptance of the exact candidate revision is promotion; never the loop itself |
| Durable evidence | The regression case, incumbent and winning revisions, per-case results, cost, and decision in the PR |

Apply `CONTRIBUTING.md` retention: keep failed/inconclusive evidence while a decision or regression
depends on it; discard drafts with no current dependency.

## Evidence, review, and promotion

Freeze the scoring rule before a failure repair; compare incumbent and candidate on identical named
inputs, model, timeout, trial count, threshold, and fresh-context boundary. Report the numerator and
denominator, not one favorable transcript. Repository-visible cases are calibration or regression,
never hidden/held-out; a shadow result requires a human or protected evaluator outside this
authoring checkout. A new grader, validator, scenario, or script names the measured failure it
prevents.

## Learn from an encountered failure

- An observation is evidence, not a contract: a human decides whether the behavior should be
  durable.
- If it should: one named regression case, plus another only for a specific adjacent risk, with
  its scoring rule frozen before any edit, then the bounded loop above.
- This loop authorizes no merge, deployment or live-system change.
- Unfinished work goes in `docs/fleet-roadmap.md` with one owner (elsewhere, the owning repository's
  tracker). A reusable rejected approach gets a short dated decision only when rediscovery is likely.
- Independent review is conditional — a finding needing independent reconciliation, a
  security/authority rule, or exact-SHA production-deployment evidence — not a universal merge
  prerequisite. A bounded read-only canary only for a named host or runtime risk.

## Writing the artifact

Keep guidance that changes a decision. Use the [failure-to-repair table](../SKILL.md#2-match-the-form-to-the-failure)
to choose the repair. A regression test checks task behavior. An asset helps produce a repeatable
result. Enforce fixed authority and effect boundaries where the action runs.

Before removing a behavioral instruction, check representative task evidence or verify its enforced
replacement. A knowledge answer with tools disabled only establishes recall.

## Tool contracts

- Promote a shell command to a dedicated tool when the action needs gating, auditing, staleness
  checks, or rendering; start with the shell for breadth.
- Tool sprawl has no portable threshold: load coherent sets on demand or split authority across
  lanes. Never hide unrelated contracts behind one giant `action` enum to reduce the count.

## In this fleet

- Add scenarios for gradeable outcomes, not tautological prose checks.
- Measure the boundary that changed: activation/routing, artifact behavior, tool choice and
  arguments, handoff/path, and final outcome are separate results. A harness denied a linked
  reference proves activation, not reference-dependent behavior.

## Context and handoffs

Send a cold-start packet, not a transcript: invoking caller and human owner separately, intent,
source/state, success criteria, scope, source trust, unknowns, and the return fields the receiver's
agent body defines. Preserve targets, windows, and observed values.

Bind evidence to its subject, method, source, and time. Reading export E verifies its bytes;
`[sourced] export E reports 4/4 at 09:40` does not verify current health. Missing chronology or state
stays unknown.

Empty, malformed, partial, timed-out, or killed returns leave dependent work incomplete: seek the
missing evidence, continue independent work, escalate a material gap precisely, and reconcile UNKNOWN
effects before retry.

Fork or rewind only when the runtime defines replay and effect semantics. Never replay an external
side effect by assumption; otherwise correct in place and record the divergence.
