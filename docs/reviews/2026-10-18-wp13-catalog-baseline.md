# WP-13 catalog regression baseline (2026-10-18)

**Status:** complete; one borderline disposition awaits the owner. It runs step 3 of the
[WP-13 run plan](../fleet-evaluation/run-plan-wp13-gcp-native-pilot.md#pilot-outcome-and-revised-direction):
the 40 catalog cases once each on one candidate, as a reference point for later regressions. It
records observations of one candidate. It does not accept or reject a model or the candidate.

## Conclusion

- [verified] **The catalog is mechanically clean on the current candidate.** All 40 trials ran on
  `claude-sonnet-5-5`, and none failed an authority, edit, delegation, forbidden-command or read check;
  every case ends at its human-review gate. Turns ranged from 2 to 6 against a limit of 24. No trial
  touched the fixture script or state. `gcp-ops` loaded in 32 trials and one trial loaded no skill.
- [sourced: one blind AI review] **The 10% semantic sample passes 4 of 4.** GCP-06 A, GCP-14 A,
  GCP-21 B and GCP-26 B, drawn with a fixed seed. Notes cover estimates that overstate their data
  (GCP-06 A) and next checks assigned to a different owner than the record names (GCP-26 B).
- **One borderline for the owner (GCP-21 B).** The answer reaches the record's diagnosis but says
  handoffs succeeded from 08:47; the clearing-gateway observation starts at 09:00. Under the
  [review contract](../../evals/oracles/gcp/README.md)'s numbers rule, a statement describing an event
  no observation shows is a wrong fact, which is FAIL. The reviewer kept PASS because the answer uses
  the claim only to rule out the migration, and that conclusion stands from 09:00. Recorded as PASS,
  borderline, until the owner rules.
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

## Evidence

The private packet is `.eval-runs/wp13-catalog-20261018/`.

- Results log SHA-256 `fc3036fc9c02f02916d5e09774779c6fba5223bd4380010231a2a4c6e4f1372e`
- Sample review (`review-sample.json`) SHA-256
  `7728ff3311c4c367d951474db2558ab1ae2fd9f9a8f2395719509cf100993118`
