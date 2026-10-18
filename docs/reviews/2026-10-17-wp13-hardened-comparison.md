# WP-13 hardened GCP cases: Haiku, Sonnet and Opus (2026-10-17)

**Status:** complete; the result is for the owner's decision on the hardening. It runs the comparison
pre-registered in the [hardening design](../fleet-evaluation/gcp-hardening.md) on the nine accepted
hardened cases. It records observations of one candidate on three models. It does not accept or
reject any model.

## Conclusion

- [verified] **The pre-registered criterion is not met.** Two of its three parts hold and one fails:

  | Part | Required | Result | Held |
  |---|---|---|---|
  | Sonnet PASS minus Haiku PASS | at least 10 of 45 | 30 - 14 = 16 | yes |
  | An H5 behavioral check differs between the models | at least 10 of 45 | read check 8 vs 4 failures; omission check 0 vs 0 | **no** |
  | Sonnet PASS | at least 25 of 45 | 30 | yes |

  The design says a failed criterion means the hardening is revised or abandoned before the catalog
  is touched. That decision is the owner's.
- [verified] **The semantic grade separates the models, and the separation survives every open
  judgment call.** Sonnet leads Haiku by 14 to 19 PASS of 45 in each view below. Opus, outside the
  criterion, scores highest in every view.

  | View | Haiku | Sonnet | Opus |
  |---|---|---|---|
  | Primary: mechanical FAIL stays FAIL, else the stricter of two blind reviews | 14 | 30 | 37 |
  | The GCP-17 B sample miscount ruled a slip (decision 2 below) | 14 | 33 | 41 |
  | Either reviewer's PASS counts | 20 | 34 | 42 |
  | Semantic only: mechanical checks ignored, stricter review | 16 | 32 | 38 |

- [verified] **The behavioral checks do not separate Haiku from Sonnet.** Both models choose deciding
  reads far above chance: the read check failed 8 of 45 Haiku trials and 4 of 45 Sonnet trials,
  against about 22 of 45 expected from random choice. Opus failed it in none. The variant C omission
  check never fired on Haiku or Sonnet and fired once on Opus, a false red (below).
- [sourced: 18 blind AI reviews] **Most of the difference is careless facts and missed required
  checks, not wrong mechanisms.** Haiku's 13 FAILs are 8 read-check misses and 5 semantic FAILs;
  Sonnet's 8 are 4 and 4; Opus's 5 are the one false red and 4 semantic FAILs. Few answers in any arm
  asserted the competing lead.

## Method

- **Candidate:** the frozen worktree at `fa8f3409`, plugin `21578f77b2fe`, Claude Code 2.1.301, the
  nine hardened cases at the owner-accepted digests. Every trace confirms the model:
  `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`.
- **Trials:** 45 per model (3 families x 3 variants x 5 passes), serial, no retries. Haiku and Sonnet
  were interleaved per case (USD 5.99); the owner then added Opus, first one measuring pass and then
  the other four (USD 12.81). Total USD 18.79. The owner raised the Haiku/Sonnet cap from USD 8 to
  USD 10 during the run; it was not reached.
- **Integrity:** no trace touched the fixture script or its state (scan of every tool input, all 135
  traces; the scan was proven on planted Read, Grep and Glob accesses). No trial had an identity,
  delivery, authority or grading-machinery fault.
- **Blind review:** the 135 answers got random IDs with model names removed and were grouped by
  case variant. Each variant went to two independent reviewers (18 reviews, Opus 5.5 per the owner's
  choice) under one brief carrying the owner's 2026-10-17 disposition rule. The combination rule was
  fixed before the second set returned. Reviewers agreed on 115 of 135 answers (Cohen's kappa 0.68).
- **Blinding limits:** reviewers ran on the same model as the Opus arm, so the Opus scores may be
  inflated by self-preference; the Haiku/Sonnet comparison has no such overlap. Three reviewers wrote
  scratch files outside their assigned folder and one grepped other answers' traces for a length
  marker; none reports reading another answer's content.

## Findings for the owner

1. **The omission check misfires on careful answers.** Its one firing (Opus, GCP-13 C) matched a fix
   offered only as an option gated on the deciding check; both blind reviewers passed that answer.
   The pattern cannot tell a gated option from a recommendation. Recommendation: drop it, or replace
   it with a reviewed rubric item; do not count it toward H5.
2. **The read check measures something real but not what the criterion asked.** It separates Opus
   (0 misses) from both smaller models, and it concentrates on two variants: GCP-17 C (8 of 10
   Haiku/Sonnet misses; Opus 0 of 5) and GCP-13 C. It does not separate Haiku from Sonnet at n=45.
3. **Reviewer disagreement clusters on how strictly to read the review records.** The 20 split
   answers turn on three questions: whether an off-by-one in a sampled count that changes no
   conclusion is a wrong fact (seven GCP-17 B answers, none Haiku); which listed unknowns and next
   checks are required (GCP-13 B, GCP-25 B); and whether ranking one lead first in variant C counts as
   choosing a boundary (GCP-13 C).
4. **The cases on the branch are no longer the accepted ones.** CI failed on the hardened-case
   commits because the read check did not follow the repository's oracle protocol (a distinct failure
   exit code). Copilot's coding agent fixed that on the branch after the run, which changed every
   hardened case digest: GCP-13 `2080b6920b09` / `43f84b95c1c8` / `9735a2354baa`, GCP-17
   `c8af6b91cef1` / `d9f5d49aa316` / `9bcd4d47823c`, GCP-25 `0db6b335106d` / `0a25c614615e` /
   `103764c793cd` (A / B / C). The run used the accepted digests at `fa8f3409`; all 12 read-check
   failures in it were real misses, none a misconfigured check, so the protocol gap did not change
   any grade. A further run needs acceptance at the new digests.
5. **Case observations.** GCP-13 A and B sit near ceiling for every model. GCP-25 A's cause is one log
   line, as recorded at acceptance. GCP-13 A's omitted-lines summary (HHMM request IDs across an
   hour) led two answers to call the fixture inconsistent.

## Decisions for the owner

| ID | Decision | Recommendation |
|---|---|---|
| R-D1 | The criterion failed on its behavioral part only. Revise or abandon the hardening? | Revise: keep the read catalog, split evidence, competing leads and variant C, which produced a robust semantic separation; drop the omission check and stop requiring a behavioral gap between Haiku and Sonnet |
| R-D2 | Is a sampled-count off-by-one that changes no conclusion a wrong fact (FAIL) or a slip (PASS with a note)? | Slip, when no conclusion, rate band or recommendation depends on it; it moves only Sonnet and Opus and leaves every conclusion above unchanged |
| R-D3 | Which review-record unknowns and next checks are required? | Mark required items explicitly in the family records before any further run, so reviewers stop deciding it per answer |

## Evidence

The private packets are `.eval-runs/wp13-hardened-20261017/` (trials, launchers, results log, the
fixture scan) and `.eval-runs/wp13-hardened-blind-20261017/` (anonymized answers, brief, 18 reviews,
key, aggregation script).

- `unblinded-results.json` SHA-256 `ad59bd812fb739c3418b359979b9d7590955985ffdfffdd6c5fd5e222b506d4e`
- `summary.json` SHA-256 `b4466f5980fcc16ee3d1700db3718e3ccad799970c17d292ffc4d6b849b4cd22`
