# ADAPT-001 closure evidence

- **Roadmap item:** `ADAPT-001` — finish the bounded sibling-repo adaptations
- **Closure date:** 2026-08-06 (America/Chicago)
- **Merge:** [PR #99](https://github.com/latent-sre/save-toolkit/pull/99), merge commit
  `b75f29d6951b96a7ca50bd9ad0a0183d37c652f2`, five commits from
  `d94300a92aa2a1b3f0152476d0bcc7280db2b0de` to `69831babd667ab5ac72fa2bb198de50922140958`

## What was delivered

All five sub-items landed with tests. This closure covers the two learning-system sub-items that
remained after the rest of ADAPT-001 merged in the same pull request.

| Sub-item | Delivered as |
|---|---|
| (1) Drift watch over pending packets | [`packet_drift.py`](https://github.com/latent-sre/save-toolkit/blob/2c71fe94e2281be69dfd65756a6108181afb60a0/skills/operational-learning/scripts/packet_drift.py) + [`test_packet_drift.py`](https://github.com/latent-sre/save-toolkit/blob/2c71fe94e2281be69dfd65756a6108181afb60a0/scripts/test_packet_drift.py) (24 tests) |
| (2) Forward freshness deadlines | [`knowledge-update-v3.schema.json`](https://github.com/latent-sre/save-toolkit/blob/2c71fe94e2281be69dfd65756a6108181afb60a0/skills/operational-learning/assets/knowledge-update-v3.schema.json), validator support, [`migrate_v2_to_v3.py`](https://github.com/latent-sre/save-toolkit/blob/2c71fe94e2281be69dfd65756a6108181afb60a0/skills/operational-learning/scripts/migrate_v2_to_v3.py), catalog entry `current` |

**Adaptation note.** An external `ledger_drift.py` scans a committed candidate store and derives a
baseline with `git log --first-parent`. This fleet deliberately never ported that store, and its
`proposed`/`blocked` dispositions are validated as *pathless* handoffs, so there was no `destination`
field to watch. The port therefore takes packets as arguments and watches their `repository` evidence
locators against the exact `target.revision` the packet already pins — a stricter baseline than a
store-wide first-parent scan.

## Acceptance evidence

- `python scripts/gate_a.py` — **24/24** structural steps green at `69831ba`
- 69 tests green across `test_packet_drift.py` and `test_operational_learning.py`
- `validate_improvements.py` — PASS (2 records)
- `claude plugin validate . --strict` — passed
- Host adapters regenerated; byte gate green
- Live end-to-end run against this repository, plus all three exit-code contracts (0 advisory,
  1 under `--fail-on-drift`, 2 unreadable)

## Review history — the part worth keeping

Two adversarial review rounds ran against this change. **Both found real defects that Gate A was
green over**, which is the point of keeping the two mechanisms separate.

Round one returned `do-not-merge` with seven findings. The most serious was not in the product code
but in a test: `test_fail_on_drift_turns_a_finding_into_a_nonzero_exit` asserted the opposite of the
contract named in its own comment. Mutating the exit expression so the gate failed *every* clean
sweep left all sixteen tests green. Round two returned `merge-with-nits` with six more, including a
fourth false-clean path (no ancestry check on `target.revision`) and a log-injection surface
(CWE-117/150) where a packet passing this repo's own validator could forge the watch's clean-sweep
sentence into a CI log.

Recurring theme across both rounds and the author's own fixes: **false-clean paths** — the tool
reporting "no drift" for evidence it never inspected. Four distinct instances were found and closed
(glob pathspec expansion, never-tracked locators, untracked-on-disk locators, non-ancestor HEAD).

## Limitations carried forward

- Both review lanes ran read-only and executed nothing, so every "tests green" claim above is
  author-reported from a local terminal. CI runs Gate A on the pull request; no independent
  verification-engineer run was performed.
- Nothing invokes `packet_drift.py` on a cadence — CI runs only Gate A. This ships the instrument;
  the loop closes in a consuming repository.
- No `transition` verb exists for dispositions, so the action the watch recommends has no mechanism
  in this repository.
- The verification-integrity gap the first round exposed is tracked separately as
  [`fi_mutation_untested_assertions`](https://github.com/latent-sre/save-toolkit/blob/2c71fe94e2281be69dfd65756a6108181afb60a0/evals/improvements/fi_mutation_untested_assertions/record.json),
  at `observed`, with its narrative in [the mutation-testing gap report](2026-08-06-mutation-testing-gap.md).
