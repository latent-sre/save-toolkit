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

## Not measured

No no-skill arm was run, so "the model does this unprompted" is inferred from the knowledge probe
and from the four Sonnet trials that happened not to load the skill, not from a controlled arm.
One task on one stack; nothing here says anything about the Spring Boot reference. Four arms ran
concurrently on one host, so wall-clock seconds are indicative only.
