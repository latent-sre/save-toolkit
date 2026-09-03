# backend-craft trim: before/after evidence (2026-09-02)

Measured on the maintainer's Windows host with the fixture-backed build probe
`evals/build-scenarios/build-software-engineer-incidents-api.yaml`, one scenario, five trials per
arm, four arms run concurrently. The probe drives `claude -p --agent save-toolkit:software-engineer`
in a seeded FastAPI repository and grades the running app with a probe-owned oracle the agent never
sees. Cited by the PR that carries the trim and by the scenario's own header.

## Provenance

| Item | Value |
|---|---|
| Scenario and oracle bytes | commit `217b97aa` (the oracle's `limit=200` defect noted below was fixed after the campaign, so later runs are not comparable to these without re-running the incumbent) |
| Incumbent plugin root | detached worktree at `217b97aa`; `plugin_inputs_dirty: false`; `backend-craft` bundle 44,608 B |
| Candidate plugin root | detached worktree at `8fad4774`; `plugin_inputs_dirty: false`; `backend-craft` bundle 16,528 B |
| Models observed | `claude-sonnet-5`, `claude-opus-5` (one model per arm, recorded from the trace) |
| Trials | 5 per arm; timeout 900 s per trial; `--permission-mode dontAsk`; no container |
| Raw runs | `.eval-runs/build/backend-craft-2026-09-02/` (gitignored, private) |

Twenty trials completed; none INCONCLUSIVE.

## Totals

| Arm | Scores (of 18) | Total | Skill loaded | Tokens, all five trials | Median seconds |
|---|---|---|---|---|---|
| Incumbent, Sonnet | 14, 13, 14, 14, 14 | 69/90 | 4/5 | 5,681,944 | 267 |
| Trimmed, Sonnet | 13, 13, 14, 14, 13 | 67/90 | 2/5 | 4,129,531 | 180 |
| Incumbent, Opus | 15, 15, 15, 15, 17 | 77/90 | 5/5 | 7,767,316 | 456 |
| Trimmed, Opus | 17, 15, 15, 15, 15 | 77/90 | 5/5 | 6,860,170 | 426 |

The two-point Sonnet difference is the `backend-craft was loaded` check itself (4/5 versus 2/5),
a routing coin-flip in the `software-engineer` agent; on every oracle check the two Sonnet arms are
identical. Opus totals are identical. The trimmed bundle cost 27% fewer tokens on Sonnet and 12%
fewer on Opus for the same outcomes.

## Per-check pass counts (passed / 5)

| Check | Inc. Sonnet | Trim Sonnet | Inc. Opus | Trim Opus |
|---|---|---|---|---|
| Cursor pagination: 250 unique incidents walked, default page bounded, limit capped | 0 | 0 | 5 | 5 |
| `?status=` filters; invalid value is a 4xx problem+json | 0 | 0 | 0 | 0 |
| Unknown id is a 404 in the RFC 9457 shape | 0 | 0 | 1 | 1 |
| `internal_note` never crosses the API boundary | 5 | 5 | 5 | 5 |
| Detail carries the vendor's on-call owner | 5 | 5 | 5 | 5 |
| Vendor that sleeps 20 s surfaces as a fast 5xx problem+json | 0 | 0 | 1 | 1 |
| `/healthz` under 2 s while the vendor is hung | 5 | 5 | 5 | 5 |
| Suite green when the probe runs it; an incidents test executed; a test command ran | 5 | 5 | 5 | 5 |
| Packet Changed and Verified slots | 5 | 5 | 5 | 5 |
| Surgical changes; nothing committed; no `.agents/` | 5 | 5 | 5 | 5 |
| `backend-craft` loaded | 4 | 2 | 5 | 5 |
| No `eng-ladder` load; no reviewer dispatch | 5 | 5 | 5 | 5 |

### The filter check, reclassified by its evidence

The oracle requested `limit=200` for the filtered page. Three Opus builds capped `limit` lower and
answered 422, which the oracle counted as a failure of the filter. Those are oracle defects, not
build defects; the oracle now requests `limit=40`.

| Arm | Cap stricter than the oracle (false fail) | Invalid value answered, but not as problem+json | No `{data}` envelope at all |
|---|---|---|---|
| Incumbent, Sonnet | 0 | 0 | 5 |
| Trimmed, Sonnet | 0 | 1 | 4 |
| Incumbent, Opus | 1 | 4 | 0 |
| Trimmed, Opus | 2 | 3 | 0 |

## What the trials say

- **Both models already produce, with or without the skill:** a response model that keeps the
  internal field out, a timeout on the vendor call, `/healthz` independent of the vendor, tests that
  pass, a surgical change, and the review packet. A tools-off knowledge probe the same day gave the
  same answer: Sonnet and Opus reproduced every general API-design rule in the incumbent SKILL.md.
- **Cursor pagination lands on Opus and not on Sonnet, in both arms.** Opus paginated 10/10; Sonnet
  0/10, including the six trials in which Sonnet loaded the skill and read `fastapi.md` and
  `consuming-apis.md`. On Sonnet the rule is read and not applied.
- **One RFC 9457 shape everywhere lands almost nowhere: 2 of 20 trials.** The incumbent carries a
  prose section with a worked JSON example; the candidate carries a one-line table row. Same result
  both ways, so the form of the sentence is not the lever. FastAPI's default error path is the path
  of least resistance and the rule loses to it.
- **The skill is loaded by Opus every time and by Sonnet 6 of 10 times.** `software-engineer`'s
  body says to load the layer skill before backend code; Sonnet skips it 40% of the time.
- **The trim regressed nothing** on any check for either model, at 37% of the bytes.

## Decision and follow-ups

The trimmed `backend-craft` stays (accepted by the maintainer in PR #221). Follow-ups, none of them
started here:

1. The problem+json rule needs a structural control, not a stronger sentence: a bundled
   `problem.py` asset (FastAPI handlers for `HTTPException`, `RequestValidationError`, and a generic
   5xx) and the Spring `@RestControllerAdvice` counterpart that the agent installs rather than
   remembers. Re-measure with this scenario.
2. Sonnet's 40% skip of the layer-skill load is a routing finding for `software-engineer`, not for
   the skill.
3. Two Opus builds answered a hung vendor with `200` and a null owner (graceful degradation). The
   oracle demands a 5xx; whether degrading is the house rule is a decision to record in the skill.

## The no-skill arm (run afterwards, same day)

Ten more trials from a detached worktree at `bdfc4f83`, which is the trimmed tree with
`skills/backend-craft/` deleted in a local commit that was never pushed. Every Skill call in
those trials answered `<tool_use_error>Unknown skill: save-toolkit:backend-craft</tool_use_error>`
(verified from the raw traces: 0 successful loads, 12 errored attempts), so the arm is clean.

| Arm | Scores (of 18) | Total | Skill loaded | Tokens, five trials |
|---|---|---|---|---|
| No skill, Sonnet | 13, 13, 13, 13, 13 | 65/90 | 0/5 | 3,847,020 |
| No skill, Opus | 13, 13, 13, 13, 13 | 65/90 | 0/5 | 5,048,522 |

| Check | No skill, Sonnet | No skill, Opus |
|---|---|---|
| Cursor pagination | 0 | 0 |
| `?status=` filter (all five: no `{data}` envelope) | 0 | 0 |
| 404 as problem+json | 0 | 0 |
| Vendor timeout as 5xx problem+json | 0 | 0 |
| `internal_note` kept out; owner fetched; `/healthz` fast; tests; packet; surgical; no commit | 5 | 5 |

Read against the two skill arms above:

- **The skill's whole measured effect is cursor pagination on Opus**: 0/5 without it, 5/5 with
  either bundle. Both Opus skill arms score 77/90 to the no-skill arm's 65/90, and 10 of those 12
  points are the pagination check and the load check; the other two are the single problem+json
  passes.
- **On Sonnet the skill has no measured effect.** The three Sonnet arms are identical on every
  oracle check; their totals differ only by the load check (4/5, 2/5, 0/5).
- **The error contract lands 2 of 30 trials across all arms**, so it is not a question of which
  bundle carries the sentence.
- **Reading the skill costs tokens**: Opus spent 26% more with the trimmed bundle than with none,
  and 54% more with the full one; Sonnet 7% and 48%.

Grader provenance for this arm: the trials were graded live at `fdc50cdc`, whose
`skill_loaded` check credited attempted loads; all thirty runs were regraded at `2b9492d5`, which
re-parses the raw trace and credits a load only on a non-error tool result. The regrade changed
only the load check in the no-skill arm (10 spurious passes became fails); every other verdict
is unchanged, and the oracle's `limit` fix does not apply to regrades because command checks keep
their live verdicts.

## The contract-as-test arm (2026-09-03)

Eight trials against `62991d39`, which adds `assets/test_http_contract.py` (four tests: cursor
page, 404 as problem+json, invalid query as problem+json, unexpected error as problem+json),
`assets/problem_fastapi.py`, `assets/ProblemAdvice.java`, a three-step "install the contract
before you build" section in the skill, and the layer-skill load moved to `software-engineer`'s
Process step 1. The Opus arm was stopped by the maintainer after three trials.

| Arm | Scores (of 18) | Skill loaded first | Assets read | Contract test copied |
|---|---|---|---|---|
| Contract, Sonnet | 18, 14, 14, 14, 14 | 4/5 | 1/5 | 1/5 |
| Contract, Opus (3 trials) | 18, 15, 18 | 3/3 | 2/3 | 0/3 (built the handlers inline) |

- **When the assets were read, the build passed every check: 3 of 3 trials, both models.** The
  first perfect trials of the campaign, and the first time Sonnet paginated or emitted
  problem+json in sixteen attempts. Sonnet's perfect trial copied the test into the repository and
  ran pytest ten times; Opus's two read the test and wrote the handlers to satisfy it.
- **When the assets were not read, the result was the old one** (14 on Sonnet, 15 on Opus), with
  the skill loaded and its body read.
- **The Process step 1 move worked for loading**: Sonnet loaded the skill as its first call in 4
  of 5 trials, against 2 of 5 and 4 of 5 in the earlier arms.
- **The install step is the remaining flaky link**: followed 3 times in 8. It sits after the
  house-contract table; the trials that skipped it read the table and built from that.

Decision: the assets stay. Next change, unmeasured: make the install step the first thing in the
skill body, before the table, and name the contract test as the acceptance criterion in
`software-engineer`'s "Verifiable goals" bullet, so the step is reached from the agent body as
well as from the skill. Re-measure with this probe, five and five.

## Not measured

One task on one stack; nothing here says anything about the Spring Boot reference. The no-skill
arm ran on the fixed oracle (`limit=40`) while the skill arms ran on the original, so its filter
column is comparable only through the reclassification above (every no-skill failure was the
missing envelope, not the cap). Up to four arms ran concurrently on one host, so wall-clock
seconds are indicative only.
