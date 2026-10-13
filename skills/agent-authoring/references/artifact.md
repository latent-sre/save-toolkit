# Artifact altitude — author and optimize one LLM-facing artifact

For a repair, first locate the owning layer (the entrypoint's rule 2). When the artifact owns it,
edit it like code: reproduce, minimal fix, verify. New work starts from the requested behavior
and success criteria, without an invented failure.

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
| Promotion authority | Human acceptance of the exact candidate PR revision; never the loop itself |
| Durable evidence | The regression case, incumbent and winning revisions, per-case results, cost, and decision in the PR |

Keep decision evidence, including failed or inconclusive results still needed by an unresolved
decision or current regression, under the fleet's retention rule (Save Toolkit `CONTRIBUTING.md`). Discard disposable drafts when
no current dependency remains.

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
- Human acceptance of the exact candidate revision is promotion; the authoring agent never merges,
  deploys, or changes a live system through this loop.
- Unfinished work goes in `docs/fleet-roadmap.md` with one owner (elsewhere, the owning repository's
  tracker). A reusable rejected approach gets a short dated decision only when rediscovery is likely.
- Independent review is conditional — a finding needing independent reconciliation, a
  security/authority rule, or exact-SHA production-deployment evidence — not a universal merge
  prerequisite. A bounded read-only canary only for a named host or runtime risk.

## Writing the artifact

Omit explanations the model already knows; retain the team's choices, missing facts, and
decision-changing instructions. A tools-off knowledge answer does not establish task compliance.
Remove a behavioral instruction only when representative task evidence or an enforced replacement
supports the removal; known facts and reliable execution are different claims. A rule the model
reads and does not apply ships as a copied test or asset, not a stronger sentence.

Prefer a small, diverse set of canonical examples over an edge-case list, count chosen by
evaluation. No vague qualifiers: state the threshold ("≤150 words, no preamble").

## Tool contracts

A tool's name, description, inputs, and output shape are the interface the model reasons over.

- Namespace by domain (`cf_restart_app`, `splunk_search`) so intent is unambiguous; the
  description carries the capability and when to call it.
- Bound output with pagination, range selection, and filters, and make errors steer the next call.
- Promote a shell command to a dedicated tool when the action needs gating, auditing, staleness
  checks, or rendering; start with the shell for breadth.
- Tool sprawl has no portable threshold: load coherent sets on demand or split authority across
  lanes. Never hide unrelated contracts behind one giant `action` enum to reduce the count.

## Structural beats behavioral

A load-bearing rule gets the mechanical control, and says so: explicit tool scope, strict schemas,
generated projections, protected environments, gates, validators, regression fixtures. Prose
guardrails are for cooperative behavior. Prompt-only formatting only where the host cannot enforce a
schema or the output is intentionally free-form.

## In this fleet

- Add an eval scenario only for a gradeable outcome — a gate blocks, routing lands, a refusal
  happens. No tautological prose evals.
- Measure the boundary that changed: activation/routing, artifact behavior, tool choice and
  arguments, handoff/path, and final outcome are separate results. A harness denied a linked
  reference proves activation, not reference-dependent behavior.
