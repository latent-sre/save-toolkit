# ADR: One Claude engine, deterministic structure graders, and a calibrated rubric judge

- **Date:** 2026-09-01
- **Status:** Proposed 2026-09-01; requires Save Toolkit maintainer acceptance before merge
- **Decision owner:** Save Toolkit maintainers
- **Roadmap item:** fleet weight review steps G3 and G4
- **Supersedes:**
  [`2026-08-26-multi-engine-evaluation-contract.md`](2026-08-26-multi-engine-evaluation-contract.md)
- **Does not supersede:**
  [`2026-08-23-retire-codex-distribution-target.md`](2026-08-23-retire-codex-distribution-target.md)
  (Codex remains a way to work in this checkout and not a distribution target) or
  [`2026-08-22-agent-discovery-calibration.md`](2026-08-22-agent-discovery-calibration.md)
  (discovery remains model propensity, not a fleet contract)

## Context

The superseded ADR was accepted for an architecture that was built and never exercised. It
specified engine adapters, execution profiles, a claim matrix, an `eval-result-envelope/v1`, and a
cross-engine comparison digest, so that a Codex engine could be compared against Claude. The Codex
adapter was disabled before it made a single run, no envelope was ever consumed by a decision, and
the profile path reported cost as "unavailable". That stack was 5,504 lines the evaluator carried
without any claim resting on it.

Two of its statements are now contradicted by what the evaluator actually does:

1. **"Deterministic graders remain the automated regression gate. A model judge, if one is added
   later, is calibration evidence only, uses hand-graded fixtures, and never changes a deterministic
   verdict."** Nine of those graders were 100–400 lines of regex each, trying to decide authority,
   voice, ordering, and quotation — "did the assistant claim to act on production?" — by parsing
   English negation. They were not deterministic contracts that happened to be strict; they were
   unreliable answers to questions regexes cannot answer, and the roadmap carried standing repair
   items (GRADER-005/007/008) for exactly that.
2. **Rejected alternative: "Let a model judge decide the gate."** The reasoning given was that it
   "replaces a deterministic contract with another variable model and makes calibration look like
   promotion authority." The first half is accepted below and bounded; the second half is a rule
   this ADR keeps unchanged — nothing here promotes anything.

`[verified]` at this branch's tip: the calibrated judge reaches 140/140 agreement against a corpus
of 140 hand-labelled cases carried over from the retired graders' own adversarial tests
([record](../reviews/2026-09-01-judge-calibration.md)), and four calibration runs forced six
corrections — two of them fixtures where the retired regex had been wrong and the judge was right.

## Decision

### 1. One engine

The evaluator targets the Claude plugin host only. Engine adapters, execution profiles, the result
envelope, the claim matrix, and the comparison digest are deleted, not disabled. A future second
engine is a new decision with its own named claims, not a restoration of this machinery.

### 2. Two grader classes, split by what is being asked

| Question | Grader class | Where |
|---|---|---|
| Structure: exact fields, exact JSON, a fenced packet with exact command strings, a closed status set | Deterministic code grader | `evals/graders.py` |
| Natural-language policy: whose voice, what authority, what order, what was claimed | `rubric` grader over a named rubric | `evals/rubrics.yaml` + `evals/judge.py` |

A structural question must never be sent to the judge, and a natural-language policy question must
never be answered by a regex over negation. This is the whole of the split: the superseded ADR's
"deterministic graders are the gate" holds for everything a deterministic grader can actually
decide.

### 3. The judge decides a rubric verdict, and nothing else

A `rubric` grader's verdict is a scenario grader result like any other. It does not promote, accept,
or approve anything: **eval results never promote a candidate; only human acceptance of the exact
candidate revision does.** That invariant is unchanged and is the part of the superseded rejection
this ADR preserves in full.

The judge is bounded by five properties, each enforced in `evals/judge.py` and tested offline in
`evals/test_judge.py`:

1. **Fails closed.** A timeout, auth failure, non-zero exit, malformed envelope, unknown verdict, a
   verdict from a model other than the pinned one, or evidence not grounded in the response returns
   FAIL with a `judge inconclusive:` detail. A broken or unauthenticated judge can only produce red
   scenarios, never green ones.
2. **Grounded.** Every evidence item must be a verbatim quote from the graded response
   (whitespace-normalized). A verdict quoting text the response does not contain is inconclusive,
   not a judgment.
3. **Pinned and identified.** Calibration resolves the model alias to a concrete identity with one
   live call and refuses cached verdicts from any other model. Batch runs record the requested judge
   model, the rubrics digest, and every observed judge identity in durable evidence.
4. **Isolated.** One clean-room `claude -p` turn, no `--agent`, no `--plugin-dir`, every tool and
   MCP server denied, the untrusted response delivered on stdin between markers and labelled data.
5. **Calibrated, and calibration is not promotion.** Every rubric is measured against
   `evals/rubrics-calibration.yaml`; a run exits non-zero below 0.95 agreement on conclusive
   judgments, and any inconclusive case fails the run rather than counting as agreement. The
   corpus is hand-labelled, and a disagreement is a finding about the rubric or the corpus — never
   a reason to reword a rubric until the number goes green.

### 4. What replaces the deleted comparison claims

The superseded ADR's claim matrix existed to say which statements two engines could jointly support.
With one engine, the surviving claims are the ones a single Claude batch can support on its own:
per-scenario verdicts against a threshold, resolved model identity per trial, and the batch
integrity state. No cross-engine or portability claim may be made from this evaluator until a second
engine is separately decided and built.

## Consequences

- A rubric verdict is a model judgment, so a wrong PASS on a live scenario is possible where a regex
  would have been deterministic — but the regexes being replaced were not deterministic answers to
  these questions either, only deterministic *strings*. The calibration corpus bounds the error, and
  every verdict carries the judge's reason and verbatim evidence in the trial detail.
- Judged trials cost about three cents each on Sonnet, recorded separately from the evaluated
  agent's own spend so neither number silently changes meaning.
- `docs/rules.md`'s "Eval runner, live profile, or durable eval evidence" row points here.
- Roadmap items that tracked repairs to the deleted regex graders (GRADER-005/007/008) are
  superseded, each with a pointer to the rubric that replaced it.

## Alternatives rejected by this proposal

- **Keep the nine regex policy graders.** They were the standing source of grader-repair backlog,
  and calibration proved two of their encoded expectations simply wrong.
- **Keep the multi-engine stack disabled but present.** Dead architecture is read as a contract by
  the next session; the superseded ADR's own claim matrix was being cited for an engine that never
  ran.
- **Let the judge decide anything beyond a rubric verdict.** Promotion authority stays human, and a
  judged scenario is evidence for a person, exactly as a graded scenario always was.
- **Use the judge for structural checks too.** A model call to compare exact JSON is slower, costs
  money, and is less reliable than the equality it would replace.
- **Treat an inconclusive judge as a FAIL in calibration.** It certifies rubrics on infrastructure
  failures; agreement is computed over judgments only.

## Approval

This ADR is **not accepted**. Save Toolkit maintainers must accept it before this change merges,
because it supersedes an accepted ADR and changes what an automated eval verdict may rest on.
Acceptance covers the contract above and the offline implementation only. It does not approve any
model call, paid campaign, push, merge, release, or promotion; a live calibration or measurement run
remains separately owner-triggered with its own budget.
