# WP-13 catalog regression baseline (2026-10-18)

**Status:** complete; the owner ruled on the one borderline disposition on 2026-10-18. It runs step 3 of the
[WP-13 run plan](../fleet-evaluation/run-plan-wp13-gcp-native-pilot.md#pilot-outcome-and-revised-direction):
the 40 catalog cases once each on one candidate, as a reference point for later regressions. It
records observations of one candidate. It does not accept or reject a model or the candidate.

## Conclusion

- [verified] **The catalog is mechanically clean on the current candidate.** All 40 trials ran on
  `claude-sonnet-5-5`, and none failed an authority, edit, delegation, forbidden-command or read check;
  every case ends at its human-review gate. Turns ranged from 2 to 6 against a limit of 24. No trial
  touched the fixture script or state. `gcp-ops` loaded in 32 trials and one trial loaded no skill.
- [sourced: one blind AI review; one disposition by owner ruling] **The 10% semantic sample is
  4 of 4 PASS: three under the review contract and one by an owner exception to it.** GCP-06 A,
  GCP-14 A, GCP-21 B and GCP-26 B. Notes cover estimates that overstate their data (GCP-06 A) and next
  checks assigned to a different owner than the record names (GCP-26 B).
- [sourced: owner ruling, 2026-10-18] **GCP-21 B is PASS by owner exception, not by the contract.**
  The answer reaches the record's diagnosis but says handoffs succeeded from 08:47; the
  clearing-gateway observation starts at 09:00. The
  [review contract](../../evals/oracles/gcp/README.md)'s numbers rule makes a statement describing an
  event no observation shows a wrong fact, which is FAIL. The reviewer flagged it borderline and kept
  PASS because the answer uses the claim only to rule out the migration, and that conclusion stands
  from 09:00; the owner ruled PASS on that basis. Under the contract alone the sample is 3 PASS and
  1 FAIL. The reviewer policy calls for a second blind review of a borderline answer; it was not run,
  and the owner's ruling took its place.
- [sourced: one blind AI review] **GCP-26 B stays PASS despite its owner routing.** The answer names
  the deciding check with the owner the record gives (Ravi reads the N2_CPUS quota history) and covers
  the recovery condition with a requested post-10:37 capture of the Deployment, scale-up errors and
  quota page. It routes finding the replay-batch owner to Ximena rather than Ravi and names no one to
  watch the next scale-up attempt; neither is the deciding check or the recovery condition the brief
  treated as required, so they are notes.
- [unverified] **Coverage limit.** 36 of the 40 answers have no semantic disposition; mechanical
  cleanliness does not show they are correct.

## Method

- **Candidate:** the frozen worktree at `ee50feca` (main after PR #394), plugin `775cd9a52f40`, which
  includes the `gcp-ops` deciding-read rules and the runner's idle-sleep hold. All 40 cases are at the
  digests accepted on 2026-10-17.
- **Trials:** one Sonnet trial per case, serial, no retries, USD 4.27 under a USD 6 cap.
- **Review:** the owner's reviewer policy for static cases: a seeded 10% sample plus every mechanical
  failure (there were none), one blind reviewer under the owner's disposition and numbers rules. The
  catalog records do not mark required items, so the brief treated the deciding check and the
  recovery or effect condition as required.
- **Sampling recipe:** the population is the 40 case ids `build-gcpNN-<slug>-<arm>` in family order
  03, 04, 06, 07, 10, 11, 14, 16, 19, 20, 21, 22, 23, 24, 26, 27, 28, 30, 31, 32, with arm `a` before `b`
  within each family; Python's `random.Random(20261018).sample(population, 4)`, drawn after the run
  and before any answer was read.

## Evidence

The private packet is `.eval-runs/wp13-catalog-20261018/`.

- Results log SHA-256 `fc3036fc9c02f02916d5e09774779c6fba5223bd4380010231a2a4c6e4f1372e`
- Sample review (`review-sample.json`) SHA-256
  `7728ff3311c4c367d951474db2558ab1ae2fd9f9a8f2395719509cf100993118`
