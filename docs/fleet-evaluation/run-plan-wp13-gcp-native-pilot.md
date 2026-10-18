# WP-13 run plan: GCP native pilot

- **Status:** Approved by the owner on 2026-10-17: decisions D1 to D5 as recommended below (smoke
  capped at USD 2; pilot capped at USD 25 after the smoke reads clean; AI-proposed semantic
  dispositions approved by the owner; `sonnet`; steps run serially). A change to the cases,
  trial count, model or cap needs a new approval.
- **Run owner:** the human owner starts each step; `agent-engineer` prepares it; `reviewer` checks
  traces and identity evidence; semantic dispositions are the owner's (decision D3).
- **Purpose:** the first native observations of the fleet on the accepted
  [GCP catalog](gcp.md): the 24-case pilot, on one candidate. It gives the pilot's evidence for
  AC-29 to AC-33 in [measurement](measurement.md#acceptance-catalog), reported separately from the full
  catalog. No result here accepts or rejects a candidate.

WP-13 also needs the 40 catalog cases, six branching investigations (AC-26/AC-35) and two human
tabletops. They follow this pilot under their own approvals; the branching profile needs WP-05's
continuation capability. This plan covers only the native pilot and its smoke step.

## Decisions for the owner

| ID | Decision | Recommendation |
|---|---|---|
| D1 | Approve the smoke step: one trial each of four pilot cases | Yes, cap USD 2 |
| D2 | Approve the pilot: 24 cases, 3 trials each, 72 trials | Yes after the smoke reads clean, cap USD 25 |
| D3 | Semantic review mode for the pilot's trials | AI-proposed dispositions bound to each family's review record, then owner approval in batches |
| D4 | Model | The `sonnet` alias (DEC-17), resolved model recorded |
| D5 | Weekly-limit headroom on the owner's subscription before each step | Owner confirms; steps run serially, never in parallel |

Every trial ends INCONCLUSIVE until a semantic disposition is recorded, because each case's review
step deliberately exits pending. D3 decides who makes that disposition. Human-only review of 72
traces at about ten minutes each is about twelve hours. With AI proposals bound to the hidden
review records, as in the [WP-10 saved-trace review](../reviews/2026-10-15-wp10-saved-trace-review.md),
the owner approves or overrides proposals in about three to four hours. Proposals spend agent
tokens on the owner's subscription but no trials.

## Preconditions

All of these hold before the first paid call:

1. **Accepted cases.** Each pilot case's `fingerprints.case_digest` at the run revision equals its
   digest at the accepted commit `9147ff91` (table below). A mismatch stops the run; a changed case
   needs re-acceptance.
2. **Runner identity.** The run revision, plugin digest and harness digest are recorded at launch,
   and the candidate runs from a frozen copy that is not edited while trials run.
3. **Model-free controls** pass at the run revision on the run host (next section). The fixture
   wrapper tests need a POSIX `sh`; a skip there is not a pass.
4. **Host.** The Windows machine under the owner's everyday account, unelevated (DEC-23). Each
   trial records CLI version, platform and host/account/elevation identity; missing or elevated
   evidence is refused before calls. Account skills are not synced into trials
   (`syncClaudeAiSkills` false). After any Claude Code upgrade, one trial runs and is read before
   the rest.
5. **Headroom.** The owner confirms subscription headroom for the step (D5).

### Accepted case digests (`9147ff91`)

| Case | Digest | Case | Digest |
|---|---|---|---|
| gcp01-startup-a | `e58c11df5a95` | gcp01-startup-b | `68e39bf65c93` |
| gcp02-revision-traffic-a | `4af114159d47` | gcp02-revision-traffic-b | `568d2306ed36` |
| gcp05-timeouts-effects-a | `65b1b8f7979b` | gcp05-timeouts-effects-b | `959bcb10a0a0` |
| gcp08-migration-coexistence-a | `f48b7ac4ec6d` | gcp08-migration-coexistence-b | `002a390ae700` |
| gcp09-log-scope-a | `9f0419a99a41` | gcp09-log-scope-b | `d74a1c6e2c04` |
| gcp12-alert-lifecycle-a | `aa04d7f47133` | gcp12-alert-lifecycle-b | `ecb3043df4b4` |
| gcp13-identity-a | `a6043e0d640c` | gcp13-identity-b | `c1f11adb0535` |
| gcp15-hybrid-network-a | `2cf2144bce78` | gcp15-hybrid-network-b | `ca247af35c4f` |
| gcp17-pubsub-a | `d91adab5ebbb` | gcp17-pubsub-b | `85d3f2088608` |
| gcp18-cloud-sql-a | `ddad15e81bb6` | gcp18-cloud-sql-b | `40a7c07d7e7e` |
| gcp25-container-lifecycle-a | `4f7975a50261` | gcp25-container-lifecycle-b | `41e8bbab877c` |
| gcp29-workload-identity-a | `3895bd9047fe` | gcp29-workload-identity-b | `af529cd98579` |

Each case id is prefixed `build-` in `evals/build-scenarios/`.

GCP-17 was revised on 2026-10-17 after the pilot's semantic review found that its shared
oldest-unacknowledged-age series fit only variant A's mechanism; each variant now carries its own
series. The owner re-accepted it at its new digests, a `126ff9f70fec` and b `e15acfb80da6`, on
2026-10-17 after an independent follow-up check, and its six pilot trials re-run at those digests. The pilot trials above stay bound to the original
digests.

## Model-free controls

These cost nothing and run at the run revision:

- `python evals/build_probe.py validate`.
- `python scripts/generate_gcp_pilot.py`: generated cases match their hidden source data.
- `evals/test_gcp_cases.py` and `evals/test_gcp_pilot.py`: paired isolation, real fixture reads,
  unavailable observations, tool boundaries, forbidden-command grading and useful/wrong/unavailable
  controls. [verified] 684 passed at `dc3206b0`, the last case-changing commit before `9147ff91`.

## Live steps

### Step 1: smoke (D1)

One trial each of `build-gcp01-startup-a` (hand-authored CLI), `build-gcp05-timeouts-effects-a`
(generated CLI), `build-gcp02-revision-traffic-a` (console) and `build-gcp25-container-lifecycle-a`
(GKE CLI). It checks, before the batch: identity evidence, the expected tool inventory (CLI cases
`Read, Grep, Glob, Skill, Bash`; console cases without a shell), that the fixture `gcloud` read
succeeds, turns used against the 24-turn limit, wall time and cost per trial. No case in this
catalog has a saved native Claude run, so the 24-turn limit and the cost estimate are unmeasured
until this step. Smoke trials are not pooled with the pilot.

If any smoke trial ends at its turn limit, the pilot does not start: raising a limit changes the
case digest and needs re-acceptance.

### Step 2: pilot (D2)

- **Cases:** all 24 pilot cases.
- **Trials:** three per case (DEC-10), serial. Cases are interleaved, and the two variants of a
  family run adjacently so both see the same conditions: 72 trials.
- **Limits:** each case's 24-turn limit and the runner's wall-clock guard.
- **Retries:** none. Every attempt is kept.
- **Spend:** the launch script passes the remaining cap to each `build_probe.py run --max-batch-usd`
  call, so scheduling stops at the cap across all cases, not per case.
- **Output:** `.eval-runs/wp13-gcp-pilot-<date>/`, private (DEC-11). Long runs launch detached so a
  closed session does not end them.

## Budget

| Item | Estimate | Basis |
|---|---|---|
| Smoke | USD 0.30 to 1.40 | USD 0.08 to 0.35 a trial |
| Pilot task spend | USD 6 to 25 for 72 trials | Same per-trial range: WP-10's first step cost USD 2.90 for 45 trials (about USD 0.06 each, mostly short cases); WP-02 cost USD 4.60 for 18 trials (about USD 0.26). GCP prompts are long and allow 24 turns, so the upper half is plausible |
| Judge spend | None | No case uses the rubric judge |
| Semantic review | D3 recommended: three to four owner hours plus agent tokens; human-only: about twelve hours | About ten minutes a trace, or a few minutes to approve a bound proposal |
| Caps | Smoke USD 2; pilot USD 25 | Scheduling stops at the cap |

The estimates are [unverified] until the smoke reports measured cost per trial; if it exceeds the
range, the pilot cap is re-proposed before Step 2.

## Reading the results

- **Per family:** report A and B side by side, per trial, with the mechanical result, the semantic
  disposition and its basis in the family's review record.
- **Authority:** any guard-denied or recorded change or credential attempt is a FAIL regardless of
  the diagnosis, and is reported first.
- **Unavailable versus wrong:** a trial whose decisive read failed through the instrument stays
  INCONCLUSIVE (AC-24); a candidate that skipped an available read and guessed fails.
- **Counts, not rates:** three trials support counts. A family whose outcome varies across trials
  is reported as varying, not averaged.
- **Separation:** pilot results are never reported as catalog coverage, and supplied-evidence
  results make no claim about live GCP behavior (WP-14).

## Stop rules

- An identity failure, a wrong plugin or an unexpected tool inventory stops the step.
- A case-digest mismatch stops the step before any call.
- A grading-machinery failure stops that case.
- An authentication failure stops the step.
- Reaching the cap stops scheduling.
- A candidate FAIL does not stop the step: it is the observation being measured.

## Pilot outcome and revised direction

The pilot ran on 2026-10-17: 72 trials for USD 6.26 with no instrument fault. The owner approved
67 PASS, 2 FAIL and 3 INCONCLUSIVE semantic dispositions and a revised order of work: close the
pilot (GCP-17 re-acceptance and re-run), run a Haiku stress test on the same 24 cases under a
USD 6 cap before any catalog run, add mechanical must-mention checks, make fix-and-measure the
main loop, and prioritize branching investigations over the remaining static cases. The
[pilot review](../reviews/2026-10-17-wp13-gcp-pilot-review.md) holds the evidence and decisions.
The [stress test](../reviews/2026-10-17-wp13-stress-test.md) then found that the pilot cases do not
separate Haiku from Sonnet on a blind review, so the cases are hardened before the catalog run.

The hardening ran, failed its behavioral criterion, was revised and was accepted on 2026-10-18
([hardened comparison](../reviews/2026-10-17-wp13-hardened-comparison.md)). The owner then revised
the order on 2026-10-18; this list replaces the one above and the hardening design's validation step 6:

1. **Fix-and-measure the systematic read misses.** GCP-17 C's deciding reads were missed in 8 of 10
   Haiku and Sonnet trials and GCP-25 B's in 4 of 10 across both hardened runs. A targeted skill fix
   gets a measured before/after, as GCP-18 did, under its own small cap. **Done 2026-10-18:**
   `gcp-ops` gained the two deciding-read rules (`fc53d335`). On the same accepted cases, deciding
   reads made, before (revised-case run) to after: GCP-17 C Sonnet 2/5 to 5/5, Haiku 0/5 to 1/5;
   GCP-25 B Sonnet 3/5 to 5/5, Haiku 3/5 to 5/5. Haiku loaded `gcp-ops` in only 2 of its 5 GCP-17 C
   trials and made no tool call in one, so its weak row is a loading gap the rule cannot reach. The
   GCP-17 A and GCP-25 A siblings stayed at 2/2 per model. 28 trials, USD 1.81 under a USD 3 cap, no
   integrity failure or fixture access; read choice only, the answers were not semantically reviewed.
   Private evidence: `.eval-runs/wp13-fix-20261018/`.
2. **Bound the auth hang.** One trial ran 16,047 s against the launcher's 900 s timeout before
   failing on an expired login; the runner or launcher gets a watchdog before the next batch.
   **Done 2026-10-18:** the Windows event log showed the host asleep for the whole trial, and wait
   timeouts do not count sleep, so the runner now holds off idle sleep while a batch runs (`24f30227`).
3. **Catalog regression baseline.** The 40 catalog cases run once, one Sonnet trial each, graded
   mechanically; semantic review covers a 10% sample plus every mechanical failure. Static cases sit
   near the semantic ceiling, so full semantic review is not run. **Done 2026-10-18** on `ee50feca`:
   40 of 40 mechanically clean, the sample 4 of 4 PASS (one borderline, ruled PASS), USD 4.27
   ([record](../reviews/2026-10-18-wp13-catalog-baseline.md)).
4. **Moved out of WP-13 on 2026-10-18.** The six branching investigations are the deferred roadmap
   item BRANCH-001. A human second-turn correction is not available on graded cases (a follow-up
   makes a scenario native, which forbids fixture grading), so the item carries the owner's design
   for when it reopens: the correction arrives as an observation from a read, console families use
   the CLI read catalog, and held-out families stay held-out.
5. **Retired.** Per-family mechanical must-mention checks: the hardened omission check fired once in
   135 trials and that was a false red, and required-item marks with the revised brief took their
   place. Blanket hardening of the remaining pilot families: families are hardened on demand.
6. **Reviewer policy.** One blind reviewer per answer; a second on borderline-flagged answers and a
   random 20%; two per answer again whenever the brief changes. Opus is not run as an arm.
7. **Tabletops.** The two human handover tabletops are their own roadmap item, HANDOVER-001, and no
   longer gate WP-13.

## Done means

Every model-free control passes; every live trial passes its identity checks; every pilot and
hardened trial has a recorded semantic disposition approved by the owner, and every
catalog trial a mechanical disposition with the sampled semantic review above; each failure is
explained as candidate behavior or a named instrument gap; and the reviewer confirms the traces. The
pilot's AC-29 to AC-33 evidence is then observed for one candidate. WP-13 completes after the pilot,
the hardened cases and the catalog baseline; the branching investigations report under BRANCH-001 and
the tabletops under HANDOVER-001. Outcomes are observations, not acceptance evidence.

**Completion, 2026-10-18:** the owner declared WP-13 complete on the pilot, the hardened cases, the
catalog baseline and the fix-and-measure loop. The instrument is used from here as a regression check
when a skill or agent changes.
