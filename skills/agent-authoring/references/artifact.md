# Artifact altitude — author and optimize one LLM-facing artifact

An LLM-facing artifact is one layer of a system contract. First locate whether the failure belongs
to routing metadata, instructions, context assembly, a tool/output schema, orchestration, the
wrapper/model/runtime, or the evaluator. When the artifact owns the failure, edit it like code:
reproduce, make the minimal fix, and verify. *[sourced: OpenAI prompt and evaluation guidance;
Anthropic prompt/context guidance; obra/superpowers `writing-skills` empirical skill-testing]*

The source-trust gate and untrusted-data rules in `../SKILL.md` govern every step here and are not
restated. One consequence worth naming at this altitude: a clean-context subagent is not a sandbox.

## The loop

The four method steps — success criteria first, evidence matched to the change, minimal change,
retest only when step 2 calls for it — live in `../SKILL.md` and are not restated. What they leave
open is case-set sizing: for an accepted failure or explicit new behavior, add the smallest case set
that distinguishes it. One named failure regression is enough unless a specific adjacent risk
warrants another case; ordinary routing edits reuse their overlapping scenarios, and pure rewording
adds none.

## The bounds on the loop

The method steps are one iteration. The loop around them is a bounded Loop Engineering contract —
before the first iteration, write down every row:

| Contract field | This loop's term |
|---|---|
| Entry and mutable state | The named artifact plus its regression cases; nothing else is edited |
| Independent verifier | The named test/eval an agent did not author; the authoring agent never marks its own candidate passed |
| Hard iteration budget | One candidate by default; an explicitly approved optimization may evaluate two or three total |
| Hard time/cost budget | A fixed call or cost budget set with the candidate budget; reaching it stops the loop |
| Success termination | The named regression passes on identical cases and conditions for incumbent and candidate |
| No-progress termination | A tie, or a missing or inconclusive candidate result, stops the loop; neither is success |
| Safety/authority stop | Any safety, authority, or existing-regression regression stops the loop and retains the incumbent |
| Promotion authority | Human acceptance of the exact candidate PR revision; never the loop itself |
| Durable evidence | The regression case, incumbent and winning revisions, per-case results, cost, and decision in the PR |

Missing or inconclusive evidence is never success. Persist only the accepted result and its
decision evidence; scratch attempts are discarded, not a second learning system.

## Learn from an encountered failure

An observation is evidence, not a contract. A human first decides whether the behavior should be
durable; when it should, add one named regression case with its scoring rule before editing, then
run the bounded loop above — every evaluated revision counts as a candidate against its budget.
Human acceptance of the exact candidate revision is promotion; the authoring agent never merges,
deploys, or changes a live system through this loop. In this repository unfinished work goes in
`docs/fleet-roadmap.md` with one owner; elsewhere use the owning repository's authoritative
tracker. A reusable rejected approach needs a short dated decision only when rediscovery is likely.

Independent review is conditional: use it when a current finding needs independent reconciliation,
a security/authority rule requires it, or the review will supply exact-SHA production-deployment
evidence—not as a universal merge prerequisite. Add a
bounded read-only canary only when the change has a named host or runtime risk; otherwise the
deterministic and behavioral evidence is the gate.

## Choose the strongest control

| Contract | First choice |
|---|---|
| Machine-consumed response | Strict structured-output schema plus runtime validation |
| Tool name and arguments | Typed tool schema; strict mode when the host supports it |
| Fixed branch, approval, or side effect | Deterministic code or an effect/tool boundary |
| Semantic judgment, tone, or human-facing shape | Prompt instructions and a small set of representative examples |

Do not compensate for a missing schema, loader, tool gate, or evaluator by making the prose more
emphatic. Prompt-only formatting remains appropriate when the host cannot enforce a schema or the
output is intentionally free-form.

## Descriptions: scope-bearing routing metadata

`../SKILL.md` states the rule — capability or user goal, invocation conditions, meaningful
exclusions, never procedure — and the reason procedure is banned there. What it leaves open is the
fix per symptom:

| Symptom | Cause | Fix |
|---|---|---|
| Never triggers | Invocation conditions do not match real user phrasing | Add the literal phrases ("review this", "why is X slow") |
| Fires too often | Capability or exclusion boundary is too broad | Name the concrete goal and the neighboring owner it must defer to |
| Wrong lane | Two descriptions claim the same goal without a boundary | Give one owner the capability and make the other name that alternative |
| Triggers, then does the wrong steps | Description contains procedural choreography | Keep capability, invocation conditions, and exclusions; move steps to the body |

## Match the form to the failure

`../SKILL.md` carries the failure→form table and the no-nuance-clause rule. What it leaves open is
the *wrong* form each failure invites — the one that measurably backfires: soft guidance
("prefer…") for a rule broken under pressure; stronger formatting prose for wrong-shaped
machine-consumed output; a list of don'ts for wrong-shaped human-facing output; prose reminders
near the template for an omitted element; an unconditional rule plus exemption clauses for
condition-dependent behavior. Prefer a small, diverse set of canonical examples over an edge-case
laundry list, and choose the count by evaluation. Never use vague qualifiers ("be concise") — state
the threshold ("≤150 words, no preamble").

## Structural beats behavioral

When a rule is load-bearing, prefer the mechanical control and say so: explicit tool scope, strict
schemas, generated runtime projections, protected environments, gates, validators, and regression
fixtures. Prose guardrails are for cooperative behavior; structural enforcement owns invariants.

## In this fleet

- Frontmatter `name` matches the directory and uses `[a-z0-9-]`; descriptions are ≤600 UTF-8 bytes
  and carry 2–4 quoted trigger phrasings. Canonical validation enforces these constraints.
- Add an eval scenario only when the outcome is gradeable (a gate blocks, routing lands, or a refusal
  happens) — no tautological evals for prose quality.
- Treat every repository-visible eval as calibration or regression. Call a set shadow only when its
  cases are withheld by a human/protected evaluator outside the authoring checkout.
- Measure the boundary that changed: activation/routing, artifact behavior, tool choice and
  arguments, handoff/path, and final outcome are separate results. A harness denied a linked
  reference can establish activation but cannot grade the reference-dependent behavior.
- House style: scope-bearing descriptions, [verified]/[sourced]/[unverified] labels, explicit [UNTRUSTED]
  input, lead with the conclusion, and use blameless language.

## Handoffs

`../SKILL.md`'s handoff and production-gate rules apply unchanged: an agent may prepare a change but
never manufacture or infer approval. Specific to this altitude:

- Follow the [roster guidance](./roster.md) when the fix is really a lane or orchestration problem,
  rather than one artifact.
- Ownership map only—not a load: the `agent-security` skill owns the independent threat review.
