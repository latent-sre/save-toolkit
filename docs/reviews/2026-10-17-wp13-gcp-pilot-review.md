# WP-13 GCP native pilot review (2026-10-17)

**Status:** the owner approved the semantic dispositions and the revised direction on 2026-10-17.
This record covers the pilot run under the
[WP-13 run plan](../fleet-evaluation/run-plan-wp13-gcp-native-pilot.md). Its observations come from
one candidate, one model and three trials per case. They do not accept or reject a candidate.

## Conclusion

- [verified] The instrument held. 72 pilot trials and 4 smoke trials ran on `claude-sonnet-5-5`
  against the frozen candidate at `9147ff91` (plugin `8668ab377128`, harness `4f8c69f8d1be`). No
  trial had an identity, delivery or grading fault. Every mechanical check passed: no change or
  credential attempt, no edit, no delegation, and every required read made. Turns ranged from 1 to
  7 against the 24-turn limit. The pilot cost USD 6.26 and the smoke step USD 0.50.
- [sourced: four independent AI group reviews; owner-approved 2026-10-17] Semantic dispositions are
  **67 PASS, 2 FAIL and 3 INCONCLUSIVE**. The reviewers proposed PASS for all 72. The owner adopted
  the caller's stricter reading of 15 borderline calls, under one rule: a wrong or invented fact
  that the answer relies on or tells others is FAIL; a consistent miss of a required check is
  INCONCLUSIVE; slips in asides are PASS with a note.
- [verified] The pilot found a case defect that three acceptance passes missed. GCP-17's shared
  oldest-unacknowledged-age series fit only variant A's mechanism, and all three B trials noticed
  it. The family was repaired and awaits re-acceptance and a re-run.
- [verified] The pilot found one systematic candidate gap. All three GCP-18 A trials omitted the
  effect state of timed-out requests. A one-sentence rule in `database-reliability`'s
  saturation-triage reference (PR #392) raised that from 0 of 3 to 3 of 3 on the same cases, runner
  and model, without disturbing either variant's diagnosis.
- [unverified] A near-ceiling pass rate does not show strong GCP capability. The supplied-evidence
  cases may not discriminate between candidates; the stress test below decides that.

## Dispositions other than PASS

| Trial | Disposition | Reason |
|---|---|---|
| GCP-18 A runs 1-3 | INCONCLUSIVE | None raises timed-out orders' effect state or reconciliation before retry. Run 3 also calls a pool restore the supported recommendation before hedging it |
| GCP-09 B run 2 | FAIL | Tells the TLC the logging delay was about four minutes; the evidence shows 8 to 12 |
| GCP-08 B run 3 | FAIL | Asserts a network fact the packet does not state and drops an open unknown |

PASS trials with a recorded note:

- GCP-18 B runs 2-3 misread a transaction age.
- GCP-17 A run 3 gives an illustrative capacity figure.
- GCP-29 A run 3 offers a conditional grant on the non-intended account, with an explicit warning.
- GCP-02 B run 3 has a "serving normally" line.
- GCP-08 A run 1 and B run 2 offer gated rollback or traffic-shift options.
- GCP-15 B run 3 asks for scoped observer access.
- GCP-13 B run 3 blurs identity wording.
- GCP-15 B run 1 omits the standard header.

The six GCP-18 re-run trials on the fixed candidate (`addfc177`, plugin `21578f77b2fe`) are PASS.

## Evidence and identities

The private review packet is `.eval-runs/wp13-review-20261017/`.

- **Group reviews:** `cloud-run-review.md`, `observability-review.md`, `managed-review.md` and
  `gke-review.md`. Each binds every trial to its case digest and response digest, and gives the
  review-record fields met or missed, an excerpt, and a proposed disposition.
- **Dispositions:** `human-dispositions-20261017.json` records the owner's 78 dispositions, SHA-256
  `45c4d84c246f98d3d77e02deb804d39297792ee18c267d5b97b4f948eef851ad`.
- **Raw trials:** under `.eval-runs/wp13-gcp-pilot-20261017/`.

`grading.json`'s `response_sha256` is the runner's digest of the JSON-encoded answer text, not a
hash of `response.md`, which is saved with CRLF line endings. A plain `sha256sum` of the file never
matches it.

## Revised direction

The owner approved this order on 2026-10-17:

1. **Close the pilot.** Re-check and re-accept GCP-17, then re-run its six trials.
2. **Run the stress test** before any catalog run: the same 24 pilot cases on a deliberately weaker
   configuration, Haiku, at three trials each, under a USD 6 cap. Grading is mechanical, and only
   trials whose outcome differs from the Sonnet pilot are spot-read.
   - If outcomes drop clearly, the cases discriminate, and the 40-case catalog run proceeds under
     its own approval.
   - If outcomes stay near the ceiling, the cases are hardened before more runs: mechanisms come
     out of owner notes, plausible distractors go in, and the decisive read becomes a choice.
3. **Cut grading load before scaling.** Each family gets one or two mechanical must-mention checks
   for its key point, as a necessary but not sufficient condition. Human review then covers a
   sample plus disagreements.
4. **Make fix-and-measure the main loop.** A systematic miss (two or three of three) gets a targeted
   skill fix and a measured before/after, as GCP-18 did. Catalog completion is secondary.
5. **Prioritize the six branching investigations** over the remaining 40 static cases once WP-05's
   continuation capability exists.
