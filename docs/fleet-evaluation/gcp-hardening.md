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
| H5 | **Behavioral mechanical checks** | From the fixture's read log: was a discriminating read set served within the budget? A miss caps the trial at INCONCLUSIVE; the semantic review decides between INCONCLUSIVE and FAIL. Reported against each variant's chance baseline. | Which reads a model chooses under a budget; reported, not a success-criterion part |

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

- **Read check.** Each variant names one or more read sets; the check passes when every read of any
  one set was served. In C the set is both deciding sources, so holding the conclusion open is
  graded only after both gaps were seen. HARDENED.md records, per variant, how often a random choice
  of three reads passes: 0.20 to 0.80, about 22 of 45 trials over the comparison. A miss is
  recorded as unmeasured and caps the disposition at INCONCLUSIVE; the misses are reported per
  model and variant against that baseline.
- **Repeats and other queries.** Repeating a read returns the same observation without using budget,
  and an off-catalog `logging read` is refused without being recorded as a change request.
- **Variant C review rule.** The reviewer brief carries the rule for leans, empty reads and gated
  options; there is no mechanical omission check.
- **Direct fixture reads.** A shell command that reads the fixture script or its state fails the
  trial, because it would return every observation without spending budget. Read, Grep and Glob
  calls are not covered by a check; the run's review scans every tool input for the fixture's
  `bin/` or `state/` paths and reports any trial that touched them as INCONCLUSIVE.
- **Known limits.** In GCP-13 A and B either deciding read settles the boundary alone, so its read
  check is near chance; its discrimination rests on the absence inference in A and on semantic
  review. GCP-25's pod events still distinguish a restarting container from a backing-off pull by
  status name, because no realistic event stream hides that; its read check targets the cause, and
  A's cause is stated by one log line, so A measures careful reading more than investigation.

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

**Owner acceptance, 2026-10-17:** the nine hardened cases, after the independent review's fixes, at
case digests GCP-13 `fe843334d4a8` / `70d98555da09` / `83a910786c08`, GCP-17 `1ba58ee45e74` /
`ea989d91afdf` / `9a0b7e00577a` and GCP-25 `882c22c61844` / `7449cf594346` / `bb93038103a3` (A / B /
C). A documentation recheck the same day supported the packets' platform claims except one hidden
source note, which overstated that Cloud Run invocations are never audit-logged; the note was
corrected without changing any case.

**Result, 2026-10-17:** the criterion is not met. The PASS gap (16) and Sonnet's PASS count (30) hold;
no H5 behavioral check differs by 10. See the [hardened comparison](../reviews/2026-10-17-wp13-hardened-comparison.md).

**Owner decisions, 2026-10-17, after the result:** the nine cases are accepted at the digests the
oracle-protocol fix produced (listed in the comparison record, finding 4). R-D1: revise the hardening.
A Fable 5.1 review drafts the revision and recommends how to settle R-D2 and R-D3 before they are applied.

**Owner decisions, 2026-10-18, revision:**

- R-D1: revise per the Fable 5.1 revision proposal. GCP-13 A's omitted-lines summary is reworded;
  GCP-25 C's two platform-owner coverage notes are removed, so its empty Pod-event and container-log
  reads are bare; the variant C omission check is dropped; a read-check miss caps the disposition at
  INCONCLUSIVE instead of failing the trial. No other read output changes.
- R-D2: the numeric-slip rule in the [GCP review contract](../../evals/oracles/gcp/README.md),
  wording confirmed. "A wrong fact told to others" means a fact given to an owner as a basis for
  action.
- R-D3: each next check and unknown in the family records is marked required or optional, with a
  reason for each required item; HARDENED.md lists them separately. GCP-13 B's unknown "whether
  other former direct readers of the bucket are affected" is optional. After the independent review,
  three marks changed for consistency: GCP-25 A's "whether 6.2.0 starts once v7 is present" and the
  recovery or effects items in GCP-13 C and GCP-17 C are required; GCP-25 A's "where v7 should ship"
  is optional.
- Acceptance: the nine revised cases are accepted at case digests GCP-13 `f4c68bdd80f5` /
  `0c9a52a9b91d` / `ffc81b5949d7`, GCP-17 `7b3168dd6b2f` / `39b84ded6dcc` / `b214903e069c` and GCP-25
  `43893c034f78` / `3be96bf937be` / `a921880b4d8c` (A / B / C).

**Revised criterion, fixed before any run.** Arms: Haiku and Sonnet, 45 trials each (3 families × 3
variants × 5), interleaved per case, serial, no retries, the same frozen worktree and plugin digest,
and the same Claude Code version for both arms. Opus is optional and outside the criterion. Two blind
reviewers per answer, the same reviewer model for both slots, and one brief carrying the variant C
rule, the disposition rule and the required-item rule. Combination: a mechanical integrity FAIL
(change request, edit, delegation, forbidden command, direct fixture read) stays FAIL; a read-check
miss (the read-check row unmeasured with exit 20) caps at INCONCLUSIVE; otherwise the stricter of the
two reviews. A trial whose grading stopped on an instrument fault is void, reported, and counts toward
no part. The revision is accepted if all four hold:

| Part | Threshold | Baseline (2026-10-17 run) |
|---|---|---|
| R1 PASS gap | Sonnet PASS minus Haiku PASS >= 10 of 45 under the primary rule **and** under the either-reviewer-PASS view | 16 and 14 |
| R2 Sonnet floor | Sonnet PASS >= 25 of 45 | 30 |
| R3 Grading agreement | The two blind reviewers give the same disposition on >= 125 of 135 answers (>= 83 of 90 if Opus is not run) | 115 of 135 |
| R4 Spread | Sonnet PASS > Haiku PASS in at least 6 of the 9 variants | 8 of 9 |

Reported, not criteria: read-check misses per model and variant against the chance baseline; numeric
slips noted per model; INCONCLUSIVE causes by required item. Decision rule: if all four hold, proceed
to validation step 6. If R1, R2 and R4 hold but R3 fails, revise the brief wording only and re-review
the same answers, with no new trials. If R1 or R2 fails, the owner decides between redesign and
abandonment.

**Owner decision, 2026-10-18, closing the pilot:** the hardening is accepted on the first comparison and
the re-review (R3 met at 118 of 120). The run on the revised cases was recorded mechanically and its
blind review deferred, so R1, R2 and R4 were not re-scored on the revised cases. See the
[comparison record](../reviews/2026-10-17-wp13-hardened-comparison.md).

**Owner decisions, 2026-10-18, after acceptance:** validation step 6 is retired. Families are hardened
on demand, when a fix-and-measure needs a discriminating case in a family whose static case sits at
ceiling. The six branching investigations are built on this fixture: an alias table so equivalent
requests reach the same read, and a second-turn correction that changes the supported conclusion;
they need no WP-05 capability. Future comparisons use one blind reviewer per answer, a second on
borderline-flagged answers and a random 20%, two per answer whenever the brief changes, and no Opus
arm. The order of work is in the
[run plan](run-plan-wp13-gcp-native-pilot.md#pilot-outcome-and-revised-direction).
