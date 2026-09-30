# Artifact altitude — author and optimize one LLM-facing artifact

For a repair, locate the layer that owns the failure first: routing metadata, instructions, context assembly,
tool/output schema, orchestration, wrapper/model/runtime, or the evaluator. When the artifact owns
it, edit it like code: reproduce, minimal fix, verify. New work starts from the requested behavior
and success criteria, without an invented failure. `../SKILL.md`'s source-trust gate,
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
| Test/eval evidence | Freeze the scoring rule before edits. For repairs, compare incumbent and candidate on identical named inputs, model, timeout, trial count, threshold, and fresh-context boundary. Report numerator and denominator, not one favorable transcript. An author may report a named test/eval PASS with command, exact candidate, and scope; a self-authored grader is not independent review. |
| Hard iteration budget | One candidate by default; an explicitly approved optimization may evaluate two or three total; every evaluated revision counts |
| Hard time/cost budget | A fixed call or cost budget set with the candidate budget; reaching it stops the loop |
| Success termination | Failure repair: incumbent demonstrates the named failure and candidate passes on identical cases and conditions. New behavior: candidate meets the frozen criterion. Existing passing regressions stay green |
| No-progress termination | A tie, or a missing, inconclusive, or incomparable candidate result, stops the loop and retains the incumbent; none is success |
| Safety/authority stop | Any safety, authority, or existing-regression regression stops the loop and retains the incumbent |
| Promotion authority | Human acceptance of the exact candidate PR revision; the authoring loop never merges, deploys, or changes a live system |
| Durable evidence | The regression case, incumbent and winning revisions, per-case results, cost, and decision in the PR |

Missing or inconclusive evidence is never success. Keep decision evidence, including failed or
inconclusive results still needed by an unresolved decision or current regression, under
CONTRIBUTING's retention rule. Discard disposable drafts when no current dependency remains.

## Evidence, review, and promotion

Repository-visible cases are calibration or regression, never hidden/held-out; a shadow result
requires a human or protected evaluator outside this authoring checkout.

A new grader, validator, scenario, or script names either the observed failure it prevents or the
requested new contract and its acceptance cases. Only a repair requires a reproduced incumbent failure.
Independent review is conditional — a finding needing independent reconciliation, a security/authority
rule, or exact-SHA production-deployment evidence — not a universal merge prerequisite. Use a bounded
read-only canary only for a named host or runtime risk.

## Learn from an encountered failure

- An observation is evidence, not a contract: a human decides whether the behavior should be
  durable.
- If it should: one named regression case with its scoring rule before any edit, then the bounded
  loop above.
- Unfinished work goes in `docs/fleet-roadmap.md` with one owner (elsewhere, the owning repository's
  tracker). A reusable rejected approach gets a short dated decision only when rediscovery is likely.
- Omit explanations the model already knows; retain the team's choices, missing facts, and
  decision-changing instructions. A tools-off knowledge answer does not establish task compliance.
  Remove a behavioral instruction only when representative task evidence or an enforced replacement
  supports the removal; known facts and reliable execution are different claims.

## Examples and thresholds

Prefer a small, diverse set of canonical examples over an edge-case list, count chosen by
evaluation. No vague qualifiers: state the threshold ("≤150 words, no preamble").

## Structural beats behavioral

A load-bearing rule gets the mechanical control, and says so: explicit tool scope, strict schemas,
generated projections, protected environments, gates, validators, regression fixtures. Prose
guardrails are for cooperative behavior. Prompt-only formatting only where the host cannot enforce a
schema or the output is intentionally free-form.

## In this fleet

- **Skill frontmatter:** `name` matches the directory and uses `[a-z0-9-]`; descriptions are ≤1,024
  characters with 2–4 quoted trigger phrasings. Canonical validation enforces both. For agents, use
  the separate [agent frontmatter contract](./claude-code-frontmatter.md#agents).
- Add an eval scenario only for a gradeable outcome — a gate blocks, routing lands, a refusal
  happens. No tautological prose evals.
- Measure the boundary that changed: activation/routing, artifact behavior, tool choice and
  arguments, handoff/path, and final outcome are separate results. A harness denied a linked
  reference proves activation, not reference-dependent behavior.
- House style: scope-bearing descriptions, [verified]/[sourced]/[unverified] labels, explicit
  [UNTRUSTED] input, conclusion first, blameless language.

## Handoffs

`../SKILL.md`'s handoff and production-gate rules apply unchanged: an agent prepares a change but
never manufactures or infers approval. A lane or orchestration problem goes to
[roster guidance](./roster.md).
