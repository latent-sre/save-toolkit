# SKILLS-003 acceptance 3 — exercise result

**Conclusion:** `[verified]` Three of the five predeclared cases were graded by independent
fresh-context graders and passed **every** assertion — 18 of 18. `[verified]` The remaining two
cases completed and produced full designs, but the harness did not persist their transcripts, so
they could not be graded at full fidelity and their raw outputs are not retained.

**Acceptance 3 is therefore NOT met.** It requires five cases with raw outputs retained; this pass
delivers three. The shortfall is an evidence-pipeline failure, not a result about the skill — but
the item's own rule is that changing a case or candidate creates a new candidate rather than
silently extending a pass, and quietly re-running the two lost cases and keeping the second result
would be exactly that. The gap is reported rather than closed.

The frozen pre-call record is
[`2026-08-25-skills-003-acceptance-3-precall-record.md`](2026-08-25-skills-003-acceptance-3-precall-record.md),
committed at `9abdf08` before the first call, with the launch decision completed at `f898ed8`.

## Conditions as executed

| Field | Value |
|---|---|
| Skill under test | `f1afd57`, digest `sha256:f32367b1484dc0823e8bbe50cab23680a8dd27157dcb5ee5211ed459a2b28ba2` |
| Branch HEAD at launch | `12cdf3e`, working tree `[verified]` clean |
| Model | `claude-opus-5` (the 2026-08-24 development pass ran on `claude-fable-5`; its 47/47 is a **different baseline** and is not averaged with this one) |
| Trials | Exactly one per case, as frozen |
| Tree after the run | `[verified]` clean — no agent wrote a file or ran a command |
| Budget | 10 calls planned, 8 made (5 generation + 3 grading); USD 40 ceiling not reached |

## Generation

| Case | Subject | Tokens | Tool calls | Duration |
|---|---|---|---|---|
| 1 | deterministic admission, fairness, backpressure, load shed, worker liveness | 61,670 | 6 | 501 s |
| 2 | model-selected handoff with authority and taint | 61,084 | 5 | 498 s |
| 3 | fan-out/fan-in with partial failure | 62,485 | 6 | 452 s |
| 4 | approval-gated external effect, idempotency, `UNKNOWN`, reconciliation | 62,541 | 6 | 518 s |
| 5 | durable cyclic graph, replay vs resume, cancellation | 61,910 | 6 | 499 s |

`[verified]` All five produced a complete fourteen-section design. Each loaded four of the six
predicate-keyed references and explicitly skipped the review-checklist and runtime-landscape lanes
as inapplicable — the routing the skill's entrypoint is supposed to produce.

## Grading

One independent fresh-context grader per case, seeing only that case's response and its six
predeclared assertions — never the generation reasoning, never another grader's verdict.

| Case | A shape | B coverage | C no runtime | D no execution claim | E labels | F invariants | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | PASS | PASS | PASS | PASS | PASS | PASS | **6/6** |
| 2 | PASS | PASS | PASS | PASS | PASS | PASS | **6/6** |
| 5 | PASS | PASS | PASS | PASS | PASS | PASS | **6/6** |
| 3 | — | — | — | — | — | — | not gradable |
| 4 | — | — | — | — | — | — | not gradable |

The graders cited passages rather than asserting compliance. Representative findings:

- **Runtime neutrality survived an adversarial read.** Case 1's grader distinguished "DRR or
  equivalent" as an algorithm rather than a product, and noted the single OpenTelemetry citation is
  used to say the standard does *not* supply a needed attempt field — cited, not adopted. Case 5's
  grader ran a name sweep for engines, queues, databases, and frameworks and reported only false
  positives on the English words "cadence" and "restatement".
- **Evidence labels held.** Case 5 carries 35 `[unverified]` and 3 `[sourced]`; the only occurrence
  of `[verified]` is the legend, beside an explicit disclaimer that nothing in the document is.
- **The invariants were checked against text, not intent.** Case 2's closed six-member destination
  enum ("There is no seventh node reachable from `E-ROUTE`") with a per-edge taint table covering
  all fourteen edges; case 5's proof that the `decide → observe` cycle exits because every path
  increments a monotone bounded counter.

## The retention failure

`[verified]` The agent harness wrote transcripts for cases 1, 2, and 5 (≈240 KB each) and
zero-byte files for cases 3 and 4, despite both completing normally and returning full designs.
Their content existed only in the orchestrating session.

Transcribing ~60,000 characters per case by hand into the evidence store was rejected: raw output
that cannot be certified byte-faithful is worse than a declared gap, because it looks like
retention while carrying unverifiable drift.

**This is the third loss of ephemeral evidence in this line of work.** The `GRADER-003` incumbent
baseline batch was lost with a removed worktree; `.eval-runs/` is gitignored, so every eval batch
would have been lost had its findings not been copied into a committed document; and now two of
five acceptance transcripts. The common cause is that evidence is written somewhere ephemeral by
default and survives only when someone remembers to copy it. That is a fleet-level defect in how
evidence is captured, not three separate accidents, and it is proposed to the roadmap rather than
fixed here.

## What this exercise does and does not establish

`[verified]` Artifact quality at one revision, on one model, at one trial per case, for three of
five cases: the skill produces the required contract without choosing a runtime or claiming
execution evidence, and it holds the effect-safety invariants under adversarial grading.

`[unverified]` Runtime behaviour, durability, provider behaviour, effect safety, and production
readiness — nothing was executed, by construction. A strong artifact result never upgrades that
lane. Also `[unverified]`: whether cases 3 and 4 would have passed, since they were not graded.

One trial per case was the frozen design and it is also the limit: three cases at 6/6 is not a
measurement of variance. The `GRADER-003` batches in this same branch showed a scenario moving 3/3
to 1/3 with no change made to it, which is the standing reminder that a single clean trial is a
sample, not a property.
