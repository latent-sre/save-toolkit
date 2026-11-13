# WP04/05 six-attempt evidence comparison

[verified] The owner approved the prepared six-test comparison with USD 5.50 reserved inside the
existing USD 100 ceiling. All six serial attempts completed, with no retries, tuning, authentication
failures, runtime failures, unknown-cost attempts or judge API calls. Native cost was USD 0.370427.
[sourced] Both retrieval answers were exact; independent semantic review found all four
interpretation answers satisfied the frozen substantive criteria, with two factual cautions.
Candidate qualification remains HOLD; this small development comparison does not promote it.

## Frozen scope

[verified] The comparison used the [three-arm development pack](../../evals/evidence-isolation/v1/README.md)
at commit `f5ae79c0f16d7342f5847b370d1c5abf4936d056`, two trials per arm, with the same six records.
The direct interpretation arm also received those exact records in its prompt; the file arm had
to retrieve them. Both used the same question, tools, limits and checks. Execution order was
retrieval 1, direct 1, files 1, files 2, direct 2, retrieval 2. No expected answer or review material
was included in candidate inputs. The four reserved qualification cases were not inspected or run.

| Identity | Recorded value |
|---|---|
| Candidate plugin SHA-256 | `8446d62f8b3479ed09898c9bbc084f7b622dd1190d6fe419eeb9b68c669b46f7` |
| Runner SHA-256 | `763b4bc011f23fb4e10ddffc9d8bf2b17f6f46643c39c32eee59f68c212f34d6` |
| Model | `claude-sonnet-5-5` |
| CLI | Claude Code 2.1.323 |
| Host | Linux `adama`, uid 1000, Python 3.14.10 |
| Method | Native clean-room single-message development cases, 16-turn limit |

[verified] Identities and source hashes were checked before each invocation. The CLI version was
frozen after detecting its update from 2.1.322 used in earlier work. These results are not pooled
with the earlier runtime. This synthetic comparison did not use the WP04-specific isolation wrapper.

## Results

[verified] Native grades and saved outputs remain unchanged. Interpretation's native INCONCLUSIVE
is its explicit manual-review gate, not a recorded model failure. All six saved-result replays
matched the original verdicts and expectation states without identity relaxation or artifact writes.
[sourced] The semantic column below is an independent AI review proposal, not human adjudication.

| Arm / trial | Native grade | Semantic review | CLI seconds | Turns | Reported USD |
|---|---|---|---:|---:|---:|
| Retrieval 1 | PASS | Exact values and bare JSON | 4.9 | 3 | 0.083986 |
| Direct 1 | INCONCLUSIVE | Criteria satisfied; coverage caution | 17.8 | 3 | 0.064735 |
| Files 1 | INCONCLUSIVE | Criteria satisfied | 16.7 | 3 | 0.053899 |
| Files 2 | INCONCLUSIVE | Criteria satisfied | 15.5 | 5 | 0.061683 |
| Direct 2 | INCONCLUSIVE | Criteria satisfied; coverage caution | 22.7 | 3 | 0.065956 |
| Retrieval 2 | PASS | Exact values and bare JSON | 5.2 | 3 | 0.040168 |

[verified] Both retrieval outputs were identical and preserved all nine requested values and types.
Both file-interpretation trials read the complete records. Neither direct trial reread the file;
both used the inline evidence. Both direct trials loaded `root-cause`; files 1 did not, while files 2
did. There were no tool errors or denials. Skill loading was an observation, not a frozen pass gate.

[sourced] All four interpretation replies identified the current `broker:9999` versus `9092`
mismatch, correctly excluded first exposure at 14:04 as the initiator of failures beginning at
14:02, kept exit-code causality unproven and user recovery unknown, and made a useful owner request.
They distinguished supported configuration facts from a possible later contribution to failures.

## Retained factual cautions

[verified] Direct 1 says no records cover 14:00–14:04, despite the supplied onset at 14:02 and
first exposure at 14:04. The saved reply states and correctly uses both facts elsewhere.
[sourced] This is a false coverage statement, but it does not reverse the temporal conclusion or
turn the unknown initial mechanism into a claimed cause. The accurate narrower wording would be
that no failure-mechanism evidence is provided for that interval.

[verified] Direct 2 calls the not-ready pod the only later observation, overlooking the supplied
exposure, configuration and listener records. It lists and uses those records earlier in the reply.
[sourced] The recovery conclusion remains correctly unknown because none provides later user
outcomes. The accurate wording would be the only later *workload* observation.

[sourced] These auxiliary overstatements are retained as nonblocking cautions against the frozen
criteria, not erased or treated as supported facts. Neither of the owner's narrow recovery-timing
or approver-attribution exceptions applies here. Downstream operator effects were not measured.
The independent review binds each finding to source and response lines and full-file hashes:
direct 1 lines 32/52 with context 16–18/30–33; direct 2 line 22 with context 12–14/19–20.

## What this establishes

[sourced] The candidate successfully retrieved and interpreted this small evidence set in both
presentations. This weakens an explanation based on a universal inability to read files or reason
about the supplied timeline. It does not identify why the larger WP04 investigations failed.

[unverified] Two trials per arm on six synthetic records do not establish a stable success rate,
reliability on large evidence bundles, superiority of direct versus file input, a causal effect of
skill loading, or the effectiveness of earlier repairs. Long conversations, original upstream
scores, final actual-helper behavior and the reserved cases remain outside this measurement.
Human calibration and exact-candidate acceptance remain separate; Windows stays owner-deferred.

## Cost, evidence and disposition

[verified] The comparison spent USD 0.370427 of its USD 5.50 reservation, leaving USD 5.129573
unused. Adding the prior USD 76.6139074 gives **USD 76.9843344** reported total and **USD 23.0156656**
remaining under the USD 100 ceiling. These are CLI-reported estimates, not reconciled invoices.
The six-attempt authorization is exhausted; no additional calls, repairs or qualification follow
automatically from the unused allowance.

[verified] Private evidence is retained under `.eval-runs/wp0405-isolation-six-20261113/`:
the approved plan, frozen cases/plugin/review, six launch receipts, native inputs/outputs/traces,
`cost-ledger.json`, `evidence-replay.json`, `campaign-report.json` and `manual-review.json`.
The manual review SHA-256 is
`caec55421402189b3a6504c869f1c09004a1c8e04bf54733a5445814ba5602fb`.
Native results and historical assessments are unchanged. `completion.json` binds the final
accounting, source checks and evidence hashes.

[verified] This follow-up changes reports and backlog only. The integrated code's standing heavy
suite remains 5,295 passed, 90 skipped and 5,061 passing subtests, receipt
`.git/local-test-runs/20261113T023550Z-758e322e/run.json`; it is code verification, not model-quality
evidence. Report-link/structure checks and whitespace validation cover this follow-up.

[sourced] The next WP04 investigation should use the retained large-case traces to identify where
relevant records were missed or misinterpreted, before selecting another bounded test. This is an
open follow-up, not authority for more paid attempts. The [prior repair report](2026-11-12-wp0405-eval-validity-repair.md)
and the [live backlog](../fleet-roadmap.md) retain the broader HOLD decision.
