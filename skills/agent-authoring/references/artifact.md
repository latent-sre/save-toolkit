# Artifact altitude — author and optimize one LLM-facing artifact

Locate the layer that owns the failure first: routing metadata, instructions, context assembly,
tool/output schema, orchestration, wrapper/model/runtime, or the evaluator. When the artifact owns
it, edit it like code: reproduce, minimal fix, verify. `../SKILL.md`'s source-trust gate,
untrusted-data rules, and method govern every step here; a clean-context subagent is not
a sandbox.

When the entrypoint's method calls for cases, use the existing overlapping scenarios for routing
edits. For an accepted failure or new behavior, use one named regression unless a specific adjacent
risk warrants another.

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

Missing or inconclusive evidence is never success. Keep decision evidence, including failed or
inconclusive results still needed by an unresolved decision or current regression, under
CONTRIBUTING's retention rule. Discard disposable drafts when no current dependency remains.

## Evidence, review, and promotion

Freeze the scoring rule before a failure repair; compare incumbent and candidate on identical named
inputs, model, timeout, trial count, threshold, and fresh-context boundary. Report the numerator and
denominator, not one favorable transcript. A missing, inconclusive, or incomparable candidate cannot
win; a tie or safety, authority, or existing-regression loss retains the incumbent. Repository-visible
cases are calibration or regression, never hidden/held-out; a shadow result requires a human or
protected evaluator outside this authoring checkout.

Keep scratch candidates and transcripts ephemeral, and persist the regression, exact revisions,
per-case results, cost, and decision in the PR. A new grader, validator, scenario, or script names
the measured failure it prevents and its Gate A weight; unfinished work has one owner in the
repository's authoritative tracker.

An author can report a scoped named test/eval PASS. That establishes only the reported check, not
independent review or promotion; the promotion and review rules below still apply.

## Learn from an encountered failure

- An observation is evidence, not a contract: a human decides whether the behavior should be
  durable.
- If it should: one named regression case with its scoring rule before any edit, then the bounded
  loop above.
- Human acceptance of the exact candidate revision is promotion; the authoring agent never merges,
  deploys, or changes a live system through this loop.
- Unfinished work goes in `docs/fleet-roadmap.md` with one owner (elsewhere, the owning repository's
  tracker). A reusable rejected approach gets a short dated decision only when rediscovery is likely.
- Independent review is conditional — a finding needing independent reconciliation, a
  security/authority rule, or exact-SHA production-deployment evidence — not a universal merge
  prerequisite. A bounded read-only canary only for a named host or runtime risk.
- Before adding text to an always-loaded file, ask the model tools-off; if it already answers, the
  text is a tax. Prose carries the team's choices among alternatives and facts the model lacks; a
  rule the model reads and does not apply ships as a copied test or asset, not a stronger sentence.

## Examples and thresholds

Prefer a small, diverse set of canonical examples over an edge-case list, count chosen by
evaluation. No vague qualifiers: state the threshold ("≤150 words, no preamble").

## Structural beats behavioral

A load-bearing rule gets the mechanical control, and says so: explicit tool scope, strict schemas,
generated projections, protected environments, gates, validators, regression fixtures. Prose
guardrails are for cooperative behavior. Prompt-only formatting only where the host cannot enforce a
schema or the output is intentionally free-form.

## In this fleet

- `name` matches the directory and uses `[a-z0-9-]`; descriptions are ≤1,024 characters with 2–4
  quoted trigger phrasings. Canonical validation enforces both.
- Add an eval scenario only for a gradeable outcome — a gate blocks, routing lands, a refusal
  happens. No tautological prose evals.
- Every repository-visible eval is calibration or regression; "shadow" only when its cases are
  withheld by a human/protected evaluator outside the authoring checkout.
- Measure the boundary that changed: activation/routing, artifact behavior, tool choice and
  arguments, handoff/path, and final outcome are separate results. A harness denied a linked
  reference proves activation, not reference-dependent behavior.
- House style: scope-bearing descriptions, [verified]/[sourced]/[unverified] labels, explicit
  [UNTRUSTED] input, conclusion first, blameless language.

## Handoffs

`../SKILL.md`'s handoff and production-gate rules apply unchanged: an agent prepares a change but
never manufactures or infers approval. A lane or orchestration problem goes to
[roster guidance](./roster.md).
