# WP-13 stress test: Haiku against Sonnet on the GCP pilot (2026-10-17)

**Status:** complete; the result is for the owner's decision on the catalog run. It covers the
stress step the [pilot review](2026-10-17-wp13-gcp-pilot-review.md) added to the
[WP-13 run plan](../fleet-evaluation/run-plan-wp13-gcp-native-pilot.md). It records observations of
one candidate on two models. It does not accept or reject either model.

## Conclusion

- [verified] **The pilot cases do not separate a weaker model from a stronger one.** On a blind
  semantic review of one trial per case and model, Haiku scored 23 PASS and 1 INCONCLUSIVE.
  Sonnet scored 20 PASS, 2 INCONCLUSIVE and 2 FAIL. Pairwise, each model wrote the better answer in
  6 of 24 variants and the rest were equivalent. Sonnet had 1 material win and Haiku 2.
- [verified] **Mechanical checks cannot separate them either.** Across all 72 trials per model,
  both had zero mechanical failures, the same turn profile (1, 4 and 7 turns at minimum, median and
  maximum) and similar answer length (median 1,001 against 1,025 words).
- [sourced: two blind AI reviews] **These cases mainly test careful reading of a supplied packet.**
  The decisive evidence names or nearly names the mechanism, so a smaller model reaches the
  supported conclusion as reliably as a larger one. The one miss both models share, GCP-18 A's
  effect state, is a guidance gap that the saturation-triage rule fixed for Sonnet.
- [unverified] **Review noise is comparable to the model difference.** Two Sonnet answers that the
  pilot review graded PASS were graded differently here: GCP-15 B run 1 became INCONCLUSIVE, and
  GCP-02 A run 1 became a borderline FAIL. With one trial per case and model and one reviewer per
  answer, a difference of a few dispositions is within grading variance.

## Method

- **Candidate:** two source revisions with the same plugin `8668ab377128` and harness
  `4f8c69f8d1be`. Haiku and the GCP-17 Sonnet re-run ran on the frozen worktree at `4e9c0342`; the
  other 22 Sonnet answers are the pilot's run 1 on `9147ff91`. All 24 case digests are the accepted
  ones; GCP-17 is at its re-accepted digests.
- **Endpoint:** the owner-approved stress protocol was mechanical, with semantic spot-reads only
  where a Haiku outcome differed from Sonnet's. Mechanical outcomes did not differ, so the owner
  separately approved the blind semantic comparison below on 2026-10-17; its result is that
  approved extension, not the original mechanical endpoint.
- **Haiku:** 72 trials (24 cases, 3 each) on `claude-haiku-5-5`, USD 0.43. The owner's login
  expired mid-batch, and 53 slots ended in about 4 seconds with "Failed to authenticate". The
  runner's detector missed that wording, so those slots were graded INCONCLUSIVE rather than
  stopping the batch. They were re-run in place with `--overwrite` after the owner logged in again;
  the superseded attempts stay under each run's `attempts/`. #391 adds the detector fix.
- **Sonnet:** the pilot's run 1 of each case. For GCP-17 it is the re-run on the re-accepted case
  (6 trials, USD 0.60, every mechanical check passed), so both models faced identical cases.
- **Blinding:** the 48 answers got random IDs. Model names were stripped from answers and traces,
  and each variant's two answers went side by side to one of two reviewers, six families each.
  Reviewers applied the owner-approved pilot rule. The caller applied the rule to one borderline
  call: a reversal command that would route traffic to the failing revision is a wrong fact told
  to others, so FAIL.
- **Blinding limits:** some tells were visible to reviewers.
  - Three Haiku answers loaded skills without the plugin prefix.
  - Six Sonnet answers opened with a method preamble.
  - Three Haiku answers and one Sonnet answer made no tool calls.

  The results do not favor either model in a way those tells would predict.

## Evidence

The private packet is `.eval-runs/wp13-blind-20261017/`.

- **Packet:** `answers/` holds the anonymized answers. `reviewer-1.md` and `reviewer-2.md` hold the
  blind reviews. `KEY-do-not-read.json` maps each ID to its case, model and source run.
- **Results:** `unblinded-results.json` holds the per-answer dispositions, SHA-256
  `fcafa3eac2560348c43de1825ca9e68bc7dcf71d5dc81ba6848149bd6c813f84`.
- **Raw trials:** under `.eval-runs/wp13-gcp-pilot-20261017/`, labels `stress-haiku` and
  `g17-rerun-sonnet`.

## What follows under the approved direction

The approved revised direction says: if outcomes stay near the ceiling, harden the cases before more
runs. They did, so the 40-case catalog run should wait. Hardening means four changes:

1. Take the mechanism out of owner notes.
2. Add plausible distractors.
3. Make the decisive read a choice, as in the recorded-observations branching profile.
4. Add the must-mention mechanical checks.

The fix-and-measure loop stays useful regardless: GCP-18 showed a real guidance gap and a measured
repair.
