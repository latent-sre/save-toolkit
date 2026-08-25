# GRADER-003 verification batch — `agent-authoring` discovery

**Conclusion:** `[verified]` Routing is correct in **12/12 trials** across all four scenarios, on
both the incumbent baseline and this candidate. `[verified]` Behavioural graders remain red: **0/4
scenarios** pass at threshold 1.0, though trial-level passes moved from **0/12 to 4/12**.
`[verified]` Every one of the **seven** failing grader instances in this batch has the graded
behaviour
**present and correct in the response** — none is a behavioural defect. The remaining reds are
string-matching artefacts, and the instrument is the cause: `contains_any` is a plain case-
insensitive substring test, which cannot express these contracts. Further word-list widening is the
treadmill `GRADER-003` warned about and was not done.

This document exists because `.eval-runs/` is gitignored. The `GRADER-003` baseline was lost that
way; the verbatim phrasings below are the part worth keeping.

## Run identity

- Batch `20260825T174112Z-498600c4`; candidate `90bd33e9d75cad29838296928a9b1998be2a8546`, clean tree.
- Claude Code CLI `2.1.245`; `--model sonnet`, resolved `claude-sonnet-5` on every trial;
  `--timeout 600`; 3 trials; threshold 1.0. Integrity check PASS. Cost USD 3.54.
- Conditions deliberately match the incumbent baseline `20260824T231543Z-53c0a77c` (Sonnet, 3
  trials, 600 s) so the numbers are comparable.
- Discovery clean room: only `Skill` and `Task` offered; `Read`, `Bash`, `Write`, `Grep`, and the
  rest denied — so every response is a tool-less routed answer, as `evals/README.md` requires.

## Result

| Scenario | Split | Trials passed | Routing | Baseline |
|---|---|---|---|---|
| `defers-code-dependency-graph` | regression | 2/3 | `[verified]` 3/3 | 0/3 |
| `loop-engineering` | regression | 0/3 | `[verified]` 3/3 | 0/3 |
| `trigger-and-shape` | regression | 1/3 | `[verified]` 3/3 | 0/3 |
| `workflow-graph` | calibration | 1/3 | `[verified]` 3/3 | 0/3 |

Routing separation held in every trial on both revisions. No trial misrouted, and no scenario is
red for a routing reason.

## Why each red fired — the response's own words

Every row below is a grader that failed while the behaviour it grades was present.

| Scenario / grader | What the response actually said | Why the match failed |
|---|---|---|
| `loop-engineering` cost budget (3/3) | `**Cost:** a token/call ceiling`; `**Cost:** token/dollar ceiling`; `**Cost:** a cap on verifier reruns` | **Label separation.** The tokens require `cost` and `ceiling`/`cap` adjacent; the response puts a markdown label between them |
| `trigger-and-shape` measure/separately (t2) | `Binary pass/fail, independent of content quality` | **Synonym.** "independent" for "separately"/"distinct" |
| `trigger-and-shape` output shape (t3) | `**Output-shape** check — schema only`; `an output-shape pass` | **Hyphenation.** `output-shape` is not the substring `output shape` |
| `workflow-graph` read-only review (t1, t2) | `**Review (read-only, independent)**`; `Independent, read-only evaluation of the candidate` | **Word order.** Tokens expect `read-only review`; the response inverts it |
| `workflow-graph` delegation edge (t2) | `## Allowed edges`; `**No edges:** … any node → effect execution`; `## Handoff / join` | **Self-inflicted.** `allowed edge` and `handoff` were *removed* from this grader to keep the prompt echo failing — see the tension below |
| `workflow-graph` human-owned effects (t2) | `**Human (effects owner)** \| Executes any authority-changing, production-facing, destructive, or external action \| Sole holder of effect authority` | **Word order.** Tokens expect `human-owned effect`; this answer is arguably better than the phrasing graded for |
| `defers-code-dependency-graph` static analysis (1 trial) | `parse each file with \`ast\``; `parse each file's AST` | **Word boundary.** Bare `AST` was replaced with spelled-out forms to stop it matching `last`/`past`/`broadcast`; that removed the form the model actually writes |

## The structural finding

A discovery scenario graded with `contains_any` cannot simultaneously:

1. grade only behaviours its prompt requests (`GRADER-003`'s new invariant),
2. reject a whitespace-normalized prompt echo, and
3. match the natural phrasing of a correct answer.

`workflow-graph` shows the collision directly: the words a good answer uses — "allowed edges",
"handoff" — are the prompt's words, so accepting them lets the echo pass the whole scenario, and
refusing them fails a correct answer. The `AST` row shows the same squeeze on a single token, in
both directions.

`[sourced]` The instrument is what has to change. A `regex` grader with word boundaries and a small
proximity window expresses all three at once — `\bcost\b[^.\n]{0,40}\b(ceiling|cap|limit|budget)\b`
accepts `**Cost:** token/dollar ceiling` while still failing an echo, because an echo lacks the
*structure*, not merely the words. `\bast\b` accepts `parse each file's AST` and rejects `last`.

`[unverified]` That conversion is not made here and its effect is not measured. It needs its own
candidate and one more batch under the same conditions.

## What was not done

No grader was widened after this run — every red was traced to its transcript first, as
`GRADER-003` requires, and the trace is what produced the finding above. No prompt was edited: a
discovery prompt is the routing stimulus, and the 12/12 routing evidence depends on it staying
byte-identical. No second batch, no threshold change, and no scenario moved between splits.

## Second batch — after the regex conversion

`[verified]` Batch `20260825T183911Z-ea5961ab`, candidate `95a017a` (clean tree), identical
conditions: CLI 2.1.245, `--model sonnet` resolved `claude-sonnet-5`, `--timeout 600`, 3 trials,
threshold 1.0, integrity PASS, cost USD 3.23.

| Scenario | Split | Trials | Routing | Batch 1 | Baseline |
|---|---|---|---|---|---|
| `trigger-and-shape` | regression | **3/3** | 3/3 | 1/3 | 0/3 |
| `defers-code-dependency-graph` | regression | 2/3 | 3/3 | 2/3 | 0/3 |
| `loop-engineering` | regression | 2/3 | 3/3 | 0/3 | 0/3 |
| `workflow-graph` | calibration | 2/3 | 3/3 | 1/3 | 0/3 |

Trial-level: **9/12**, against 4/12 before the conversion and 0/12 on the incumbent. Routing
remains `[verified]` 12/12 with no misroute in any trial of any batch.

`[verified]` All three remaining reds were traced to their transcripts, and all three are again the
behaviour being present in a form the grader did not admit — none is a behavioural defect:

| Scenario | What the response wrote | Gap |
|---|---|---|
| `defers-code-dependency-graph` t3 | ``Grep each file for `^import ` `` | A grep-based extraction, never naming AST or static analysis — a legitimate method the technique list did not admit |
| `loop-engineering` t2 | `\| Iterations \| e.g., <= 5 propose-verify passes \|` | The cap stated as a **number**, more concrete than any noun in the pattern |
| `workflow-graph` t1 | `\| Node \| Role \| Tools/authority \|` | Singular. A `contains_all` on the literal `nodes` missed it — a grader the first conversion never reached |

Each was generalized along the axis it exposed rather than by adding tokens: method family
(grep/regex extraction counts), numeric bounds (comparators and digits count), and number and
inflection (lookaheads, which also preserved the `authority` and `termination` assertions that a
narrower node/edge pattern would have silently dropped).

`[verified]` Against all 24 retained transcripts from both batches, every scenario is 6/6 on every
positive grader, and each keeps at least one grader the whitespace-normalized prompt echo fails.
`[unverified]` This is retrodiction over the transcripts the patterns were derived from. The trend
across three measurements — 0/12, 4/12, 9/12 — supports the instrument diagnosis, but only a third
batch on unseen trials would show these three scenarios green for a behavioural reason.

## Third batch — and the finding that stops the widening

`[verified]` Batch `20260825T192519Z-4b6fe947`, candidate `16a236d` (clean tree), same conditions,
integrity PASS, cost USD 3.88.

| Scenario | Split | Batch 3 | Batch 2 | Batch 1 | Baseline |
|---|---|---|---|---|---|
| `defers-code-dependency-graph` | regression | **3/3** | 2/3 | 2/3 | 0/3 |
| `loop-engineering` | regression | 2/3 | 2/3 | 0/3 | 0/3 |
| `trigger-and-shape` | regression | 1/3 | **3/3** | 1/3 | 0/3 |
| `workflow-graph` | calibration | 2/3 | 2/3 | 1/3 | 0/3 |

Trial-level **8/12**, against 9/12 in batch 2. Routing is `[verified]` 12/12 for the third
consecutive batch — 36/36 trials across every revision, with no misroute anywhere.

**The trend is not monotonic, and that is the result.** `trigger-and-shape` went 3/3 then 1/3 with
**no change made to it between the two batches**, failing a grader this work never touched. Its 3/3
was not a fixed defect; it was a sample. The same applies in reverse to the 9/12: batch 2 was
luckier than batch 3, not better than it.

`[verified]` The three new reds are the same class yet again — behaviour present, form unadmitted:
`| Cost | ~$2 / 200k tokens total |` (the cost bound as a literal dollar amount, exactly the
numeric form that was generalized for *iterations* and not for cost); "Fixed test corpus" and
"Test cases (one focused set...)" for a grader wanting `focused case`; and a roster whose review
lane is "Independent Review ... Sees only the final artifact", where read-only is implied by scope
rather than stated next to the word review.

**Why widening cannot converge here.** These scenarios are conjunctions: every positive grader must
pass in every one of three trials at threshold 1.0.

| Scenario | Positive graders | Grader-trials at 3 trials | P(clean sweep) at 97% each | at 99% each |
|---|---|---|---|---|
| `loop-engineering` | 7 | 21 | 0.53 | 0.81 |
| `trigger-and-shape` | 6 | 18 | 0.58 | 0.83 |
| `workflow-graph` | 4 | 12 | 0.69 | 0.89 |
| `defers-code-dependency-graph` | 1 | 3 | 0.91 | 0.97 |

Even graders that are individually 97% faithful leave `loop-engineering` a coin flip. The
routing-only scenario, with one grader, is the one that reached 3/3 — and it is reliable *because*
it is short, not because its grader is better written. No amount of vocabulary work moves a
scenario whose ceiling is set by the length of its conjunction.

`[verified]` The instrument diagnosis from batch 1 still holds and the regex conversion was worth
making: thirteen reds have now been traced across three batches and not one was a behavioural defect.
But instrument quality was never the whole constraint. **Contract shape is**, and no further
grader edit was made after this batch.

**Options, for an owner decision — none taken here:**

1. **Shorten the conjunctions.** Keep two or three load-bearing graders per discovery positive and
   retire the rest. Cheapest, and it directly raises the ceiling.
2. **Drop the threshold below 1.0** for these scenarios, making 2/3 the pass bar and accepting that
   discovery measures a propensity, as `evals/README.md` already says of agent-target discovery.
3. **Move the behavioural contracts to direct mode**, where the component has tools and can emit a
   determinate artifact instead of prose — the option `GRADER-003` considered and set aside when no
   direct `agent-authoring` scenario existed. Most work; also the most durable.

The regression split stays red until one is chosen. That is an honest red: it reflects a contract
the suite cannot satisfy, not a fleet defect.

## Fourth batch — the new shape, measured

`[verified]` Batch `20260825T214004Z-ab8dff39`, candidate `ce0278a` (clean tree), same conditions
as every prior batch: CLI 2.1.245, `--model sonnet` resolved `claude-sonnet-5`, `--timeout 600`,
3 trials. Integrity PASS. Cost USD 3.44.

| Scenario | Split | Threshold | Bar | Trials | Routing | Verdict |
|---|---|---|---|---|---|---|
| `defers-code-dependency-graph` | regression | 1.0 | 3/3 | 3/3 | 3/3 | **PASS** |
| `loop-engineering` | regression | 0.66 | 2/3 | 3/3 | 3/3 | **PASS** |
| `trigger-and-shape` | regression | 0.66 | 2/3 | 3/3 | 3/3 | **PASS** |
| `workflow-graph` | calibration | 0.66 | 2/3 | 3/3 | 3/3 | **PASS** |

**4/4 scenarios, 12/12 trials.** Across five measurements under identical conditions the trial
series is **0/12 → 4/12 → 9/12 → 8/12 → 12/12**, and routing is now `[verified]` **48/48** across
every revision with no misroute in any trial of any batch.

**What this does and does not show.** It shows the trimmed discovery shape passes cleanly on unseen
trials, which the previous shape never did in three attempts. It does **not** show that the
threshold relaxation helped: every scenario passed 3/3, so the 2-of-3 bar absorbed nothing and the
same result would have been reached at threshold 1.0. Option 2 is verifiably in force — the bar
computes to 2 of 3, confirmed against `run_evals.py:1113` — and it was simply not exercised here.
Claiming otherwise would repeat the error this item was opened to fix.

`[unverified]` The three direct contracts are still unmeasured; they remain `calibration` until a
`--mode direct --match agent-authoring` batch gives them a measured pass. The grader corrections
made after this batch (the widened Mermaid arrow, the `go list` word boundary, the `scoring`
inflection) are pure widenings applied to scenarios that already passed, so they cannot have turned
a pass into a fail — but they are `[unverified]` in the sense that no batch has exercised the
widened forms.

## Fifth batch — the direct contracts, measured

`[verified]` Batch `20260825T225402Z-8ff050e2`, candidate `b8dea04` (clean tree), `--mode direct`,
same conditions otherwise. Integrity PASS. Cost USD 2.70.

| Contract | Trials | Skill fired | Verdict |
|---|---|---|---|
| `agent-authoring-loop-contract` | 3/3 | 3/3 | **PASS** — promoted to `regression` |
| `agent-authoring-trigger-and-shape-contract` | 3/3 | 3/3 | **PASS** — promoted to `regression` |
| `agent-authoring-roster-graph-contract` | 2/3 | 3/3 | stays `calibration` |

**8/9 trials.** The skill fired 3/3 on every contract, so invocation is clean and no red is a
routing failure. Two contracts earned a measured pass and left `calibration`; the third did not,
and is recorded as measured rather than promoted.

**The one red is the fourteenth traced, and the fourteenth with the behaviour present.** Trial 3
wrote `- **V**: read-only lane by design — this is the independent-review boundary`, which is
exactly the contract. The `read-only … review` proximity grader allowed 40 characters between the
two terms; the gap was **42**. It missed by two characters.

The window is now 80. That is safe for a reason worth stating rather than assuming: this grader is
**not** this scenario's echo-rejector — the arrow grader is — and the prompt already matched this
grader at 40, so widening costs no echo rejection. `[verified]` the full set still rejects the
prompt echo after the change.

`[unverified]` No batch has exercised the widened window, so the roster contract has not earned
promotion and stays `calibration`. Same for the other post-batch widenings (the Mermaid arrow forms,
the `go list` boundary, the `scoring` inflection): each is a pure widening applied to a scenario
that already passed, so none can have turned a pass into a fail, but none has been measured.

**Running totals across five batches.** Discovery trials `0/12 → 4/12 → 9/12 → 8/12 → 12/12`;
routing `[verified]` **48/48** with no misroute in any trial of any batch; **fourteen reds traced,
zero behavioural defects**. Total measured spend on this item: USD 20.79.
