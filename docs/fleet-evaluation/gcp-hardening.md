# GCP case hardening: design proposal

**Status:** Approved by the owner on 2026-10-17 with the decisions recorded below; written the same day. Nothing here changes an accepted case. It
responds to the [stress test](../reviews/2026-10-17-wp13-stress-test.md), which found that the 24
accepted pilot cases do not separate Haiku from Sonnet.

## Why the cases do not discriminate

The stress test showed the result. Reading the cases shows the cause.

- **One record settles each variant.** Each variant's decisive evidence holds a single observation
  that names the mechanism. GCP-13 A has an IAM decision reading "DENIED for that caller"; GCP-17 B
  has "validation rejected … nack sent"; GCP-25 B has a container with no log stream because it
  never started. A model that reads carefully finds that record and is done. Interpretive owner
  notes are rare (0 to 3 of 9 to 14 decisive lines), so removing them alone would change little.
- **All evidence arrives at once.** CLI cases return one compiled export from one declared read.
  Console cases put everything in the prompt. The agent never chooses what to look at, and choosing
  is where investigation skill shows.
- **Only one coherent story.** The shared evidence is neutral, and the decisive evidence points one
  way. Nothing in a variant argues for the wrong mechanism, so there is no evidence to weigh.
- **Every variant has an answer.** No live case tests holding a conclusion when the evidence does
  not support one. Overclaiming, which smaller models do more, goes unmeasured.
- **Grading needs a reader for everything.** The mechanical checks confirm that the agent stayed in
  bounds, not what it concluded. Every quality difference waits on semantic review, and two reviews
  of the same answers disagreed on about as many dispositions as separated the models.

## Design principles

1. **Measure investigation, not reading.** The agent decides which observation to request, and the
   discriminating one is not the obvious first read.
2. **No single record decides.** The mechanism follows only from combining two or three
   observations, or from a small calculation (a rate, a slope, a timeline alignment) that the
   packet does not perform for the agent.
3. **Competing explanations stay plausible** until the discriminating observation is in hand.
4. **Stay realistic.** Every hardened packet must still read as a real incident to an experienced
   SRE; no trick questions, no contradictions planted to trap.
5. **Grade behavior mechanically where possible.** Which reads were made, in what order and within
   what budget is observable without a reader. Semantic review then covers what is left.
6. **Pre-register success.** The discrimination target is fixed before any hardened run.

## Proposed mechanisms

| # | Mechanism | What it changes | What it should separate |
|---|---|---|---|
| H1 | **Budgeted read catalog** | The CLI fixture offers 5 to 7 named reads (service describe, revision logs, metrics series, IAM decision, dependency logs, change history and so on), listed in the prompt, under a budget of three. Each returns a fixed observation; a read past the budget returns "budget exhausted" and is logged. Only one or two reads discriminate | Choosing the discriminating read, and doing it before concluding |
| H2 | **Split the decisive record** | The deciding fact is spread across two reads, or must be derived (for example, backlog growth rate against arrival rate, or an age slope). No line states the mechanism | Combining evidence and doing the arithmetic |
| H3 | **A competing lead** | Each variant carries one plausible but non-causal lead: a coincident deploy, a config change or a noisy metric. It matches the wrong mechanism, and only the discriminating read rules it out | Resisting the first plausible story |
| H4 | **A third, insufficient variant (C)** | The discriminating read is unavailable or inconclusive within the budget, and the evidence supports both mechanisms. The correct answer holds the conclusion open and names the missing read and its owner | Calibration: not overclaiming |
| H5 | **Behavioral mechanical checks** | From the fixture's read log: was a discriminating read made, before the budget ran out? In C, did the answer avoid naming a single mechanism (an omission check, never a pass check)? | Moves part of the grade from reader to log |

H1 to H3 make the work harder; H4 adds a variant that rewards calibration; H5 makes grading cheaper
and more reliable. H1 needs the CLI fixture, which GCP-01's hand-written multi-read wrapper already
demonstrates. The
`sre-assistant` read-only guard admits only `gcloud run services describe`, `gcloud run revisions
describe` and `gcloud logging read`, so a catalog offers those reads with different filters (audit,
request, application and Kubernetes-event logs). Widening the guard would change the agent's real
authority and is out of scope. Console families would gain an equivalent "request observation" fixture tool.

## What stays the same

- **Accepted cases stay intact.** The hardened cases are new cases with their own ids (for example,
  `build-gcp13-identity-h-a`). The 64 accepted cases, their digests and the pilot results remain
  valid for what they measure: authority, bounded reads and careful reading.
- **Every guarantee carries over:** hidden review records, scripted useful/wrong/unavailable
  controls, the variant-isolation tests, the forbidden-command grading and the review contract.

## Authored families

GCP-13, GCP-17 and GCP-25 are authored as `build-gcpNN-<slug>-h-{a,b,c}` from
`evals/oracles/gcp/hardened/`, with review records in [HARDENED.md](../../evals/oracles/gcp/HARDENED.md).
GCP-25's pod events still distinguish a restarting container from a backing-off pull by status name,
because no realistic event stream hides that; its hardening sits one level down, where the cause of
the restart or the failed pull needs a second read and a cross-reference.

## Validation plan

1. **Pilot three families,** one per platform group, chosen among those both models passed easily:
   GCP-13 identity (CLI), GCP-17 Pub/Sub (CLI, with an arithmetic discriminator) and GCP-25
   container lifecycle (GKE, CLI). Each gets variants A, B and C.
2. **Run offline controls first.** Scripted answers that skip the discriminating read, follow the
   competing lead, or overclaim in C must fail or stay INCONCLUSIVE. Scripted careful answers must
   reach the human-review gate.
3. **Get the same review and acceptance as the catalog.** One independent review pass, then owner
   acceptance at the case digests.
4. **Run a pre-registered comparison:** Haiku against Sonnet, 3 families × 3 variants × 3 trials =
   27 trials per model (about USD 3 for Sonnet and USD 0.20 for Haiku). Blind semantic review uses
   two reviewers per answer, which also measures grading agreement.
5. **Fix the success criterion before running.** Hardening works if all three hold:
   - Sonnet's PASS count exceeds Haiku's by at least 6 of 27 trials.
   - At least one H5 behavioral check differs between the models by at least 6 of 27 trials.
   - Sonnet still passes at least 15 of 27, so the cases are hard, not broken.
   If the criterion fails, the hardening is revised or abandoned before the catalog is touched.
6. **Only after success,** harden the remaining pilot families, then decide about the catalog.

## Risks

- **Over-hardening into trick questions.** Principle 4 and the independent review are the guard; a
  case a careful SRE would call unfair is rejected.
- **Prompt-listed reads make the choice visible.** That is intended: real SREs know which
  observations exist, and the skill is choosing among them under limited time.
- **Small samples.** 27 trials per model supports counts, not rates. The criterion is set so chance
  is unlikely to meet it, but it is a screening test, not a benchmark.
- **Authoring cost.** Three hardened families is roughly the work of one catalog group plus the
  fixture extension, and the generator change is reviewed like any runner change.
- **Model dependence.** If both models later pass the hardened cases, the next lever is a longer
  branching investigation (AC-26), not more distractors.

## Decisions for the owner

| ID | Decision | Recommendation |
|---|---|---|
| H-D1 | Which mechanisms to pilot | All five (H1 to H5); H1 and H5 are the core |
| H-D2 | Pilot families | GCP-13, GCP-17 and GCP-25, as new hardened cases beside the accepted ones |
| H-D3 | Success criterion | As in validation step 5, fixed before the run |
| H-D4 | Comparison budget | 27 trials per model, cap USD 5, two blind reviewers per answer |

**Owner decisions, 2026-10-17:** H-D1 all five mechanisms; H-D2 GCP-13, GCP-17 and GCP-25 as new
hardened cases beside the accepted ones; H-D3 the criterion as proposed; H-D4 **45 trials per model**
(3 families × 3 variants × 5 trials) under a **USD 8 cap**, with two blind reviewers per answer.
The criterion's thresholds scale to 45 trials at the same proportions, fixed here before any run:
Sonnet's PASS count exceeds Haiku's by at least 10 of 45; at least one H5 behavioral check differs by
at least 10 of 45; Sonnet still passes at least 25 of 45.
