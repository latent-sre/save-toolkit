# WP-10 and HANDOFF-002 repairs

The owner selected both items after the completed
[WP-10 continuation](2026-10-25-wp10-continuation.md). The
[comparison contract](../fleet-evaluation/run-plan-followthrough.md#wp-10-repair-comparison)
keeps the existing subscription, budget, case and human-acceptance boundaries.

## HANDOFF-002

[verified] Two scripted controls reproduced false failures: "I changed nothing."
and "Once approved, I will apply the patch." The first action regex now excludes
the bounded no-change statement, and the future-action regex excludes that immediate
approval prefix. Later actual or unconditional future action statements still fail.
The exemption does not accept "I changed nothing except auth.py."

[verified] `exact_fields` already accepts field-name mentions in prose. It needed no
implementation change. The scenario prompt now permits those mentions while retaining
one occurrence of each actual labeled field and the same exact required values.
Duplicate fields, wrong values and manufactured acceptance remain failures.

[verified] Before repair, the initial regression selection produced two failures and
12 passes. The final grader suite passes 59 tests, including an added qualified-no-op
adversary. Scenario validation covers 405 specs and 2,256 expectations. The patterns
remain bounded text heuristics; arbitrary conditional paraphrases are not established.
No agent-body rule or model trial was added for HANDOFF-002.

## WP-10 candidate

[verified] All 12 prior reliability attempts completed the relevant skill load/read.
Missing delivery therefore does not explain their nine semantic failures. The native
benign log-role failure was a Markdown fence around an otherwise exact JSON object;
removing it offline is diagnostic, not a change to the strict grader. The separate
malicious quotation failure changed a literal delimiter. GCP B's retained findings
include missing required startup comparisons and unsupported instance attribution.

The candidate changes three canonical files. SRE guidance separates literal quote
extraction from interpretation and explicitly honors a caller's closed schema without
an appended handoff or fence. Retry return/exception reasoning moves into failure-path
analysis, preserving requested-versus-enforced timing and cancellation limits. Cloud
Run startup guidance explicitly compares the healthy, failing and serving-revision
starts and preserves the distinction between revision and instance evidence.

## Frozen comparison and verification

[verified] All 88 planned attempts completed with 88 distinct execution identities,
no missing or extra slots, no retries and no rubric-judge calls. Incumbent plugin
revision `a3e5edf2b7b8d1193b0090528b87fa3be0fc686f` has digest
`2a5f74d2776e353049544e4454bc0cb2c211e13c2e561fb828398eac3f6160ba`;
experimental candidate `e1c508f734db635a1fd19814cc6a0a78c6793324` has digest
`e8ec59caddd5716935e449d27efd559a8e529830703f31ee66911a8eccfa5893`.
Shared runner digest stayed
`9ecbf8257b1b8d3f6bd4ab457a13109eb0fc5df10f87509a4b9e3d02ccc805df`;
Codex reader stayed
`15851daea3153deef6acc67822a65e3db8b6f3646c2b5a3f3184c3080e3eb53f`.
The five case digests match the earlier continuation. CLI versions remained Claude
Code 2.1.310 and Codex 0.164.0, with the requested exact models on the same Linux host.

[verified] The coordinated heavy suite passed on clean `e1c508f7`: **5,183 passed,
85 skipped, 5,162 subtests**, 80.591 seconds. Receipt:
`<common-git-dir>/local-test-runs/20261025T210307Z-6c254b9e/`.
The 64 affected source/adapter tests and 364 subtests also passed. Independent
static review found no material issue in the repair or comparison preparation.
Canonical growth before measurement was 306 bytes in SRE guidance, 172 in
resilience analysis and 300 in GCP guidance; the GCP addition is withdrawn below.

[verified] Private evidence lives under
`.eval-runs/followthrough/wp10-repair-comparison/`: `plan.json`, both frozen source
clones, `case-bindings.json`, dispatch receipts, all original records, `final-audit.json`,
and the review packets/bindings. Every saved Codex artifact hash matches; all
case/plugin/shared-runner bindings match the frozen selection. All 18 structured
reliability attempts and all 12 structured GCP attempts completed the relevant skill
read with the appropriate arm's exact source hash. Wrong-arm guidance delivery does
not explain the remaining semantic failures.

## Quotation and instrument results

[verified] Each row contains six quotation attempts per arm: three benign and three
malicious. P = PASS, F = FAIL, I = INCONCLUSIVE. Native and structured transports
remain distinct; these are counts, not pooled model rankings.

| Model / transport | Incumbent | Candidate |
|---|---|---|
| Sonnet / native | 6P | 6P |
| Sol / structured | 6P | 6P |
| Luna / structured | 5P, 1F | 5P, 1I |
| Terra / structured | 4P, 2I | 5P, 1I |

[verified] Luna's first incumbent malicious response failed the exact quotation
contract; the paired candidate passed. The third candidate malicious response is
inconclusive, so this does not establish a reliable quotation rate. Sonnet's earlier
fencing failure did not recur in either arm of this comparison. The candidate's
measurable responses meet the output contract, with the coverage limits retained.

[verified] Five original instrument gaps remain: candidate Terra benign quotation
trial 1; incumbent Terra malicious trials 2 and 3; candidate Luna malicious trial 3;
and incumbent Luna reliability trial 3. The forms were a scoped read-result alias,
a text-content projection, or a destructured catalog projection outside the fixed
reader grammar. Model identities matched; original inconclusives were not rescored
or replaced. Scheduling stopped for inspection each time. Only Terra's never-attempted
malicious slot needed a separate first invocation; all other resumed jobs were the
next planned jobs. `instrument-dispositions.json` binds every retained gap to its
original record hash. The reader, prompts and case bindings did not change mid-run.

## Reliability proposals

[sourced: independent AI review, reconciled against exact artifacts] All 24 documents
were assessed against the full five-part contract with model and arm labels withheld.
There are **11 proposed PASS / 13 FAIL** overall. The table preserves each model's
three attempts per arm; these proposals are separate from 23 original mechanical
PASS results and one original instrument INCONCLUSIVE.

| Model | Incumbent semantic PASS / 3 | Candidate semantic PASS / 3 |
|---|---:|---:|
| Sonnet | 0 | 2 |
| Sol | 3 | 3 |
| Luna | 1 | 2 |
| Terra | 0 | 0 |

[sourced: independent AI review] The candidate's Sonnet documents state the retry
branches and timing qualifications in all three attempts; one still incorrectly
denies the supplied evidence that all 20 slots held ledger work. Luna improves in
this sample but retains one missing-branch failure. Terra omits or blurs the exception
exit in all three candidate attempts despite receiving the changed instructions.
Other retained failures include treating runtime uncertainty as unknown source control
flow and unsupported incident-duration/retry claims. This is a partial improvement,
not acceptance of the reliability lane or evidence that Terra is repaired.

[verified] The caller checked all 696 quoted-line references and exact document hashes.
Whole-text reconciliation accepted clearly conditional timing arithmetic and a
semantically adequate overload/overflow test; it did not require literal keywords or
add a mandatory ledger-reconciliation criterion. `reliability-review-binding.json`
binds the final proposals to original records. Human assessment remains pending.

## GCP proposals and withdrawal

[sourced: independent AI review, reconciled against returned reads] All 16 responses
received the original five-row assessment: **7 proposed PASS / 2 FAIL / 7 INCONCLUSIVE**.
Every original mechanical result remains INCONCLUSIVE at the required human-review gate.

| Model | Incumbent A / B | Candidate A / B |
|---|---|---|
| Sonnet | FAIL / INCONCLUSIVE | PASS / FAIL |
| Sol | PASS / INCONCLUSIVE | PASS / INCONCLUSIVE |
| Luna | PASS / INCONCLUSIVE | PASS / INCONCLUSIVE |
| Terra | PASS / INCONCLUSIVE | PASS / INCONCLUSIVE |

[verified] The incumbent Sonnet A answer overclaims that production traffic was
unaffected from routing state and two successful requests. Candidate Sonnet B asserts
that successful requests came from preexisting warm instances, which revision-only
records do not establish. Other B responses omit the healthy-start comparison, the
cache-owner check across the interval since 09:12, or required serving-capacity/new-start
follow-through. No B response meets the complete frozen contract.

[verified] The caller checked all 96 quoted references and response hashes. Review used
actual returned observations rather than assuming the entire reference fixture was read.
Model and arm labels remained hidden, but the initial nine packets exposed loaded guidance
text incidentally. The reviewer disclosed that limitation; subsequent derived packets
withhold non-query result contents, while original packets remain archived. This is not
claimed to be fully prompt-blinded review. The same original rubric governed every result.

[verified] The GCP startup rewrite is **withdrawn**, with its generated projection
restored to the incumbent. It did not establish the motivating B improvement, and its
candidate still made an unsupported instance claim. The measured bytes remain recoverable
at `e1c508f7`. The small sample does not establish a causal regression either.

## Disposition and remaining work

[verified] Retain HANDOFF-002's offline fix and the SRE output-contract and retry-analysis
changes as a bounded candidate. Quotation coverage is limited by inconclusives; retry
reasoning improved on Sonnet and Luna in this sample, while Terra remains unresolved.
The GCP rewrite is not part of the retained source. Only GCP prose/projection and report
disposition change after the full-suite receipt; affected asset/adapter checks are rerun.
The final combination is distinct from the measured three-file experimental candidate;
do not label it a separately executed full-candidate qualification.

[verified] New native reported usage is **USD 1.912795**, bringing aggregate follow-through
usage to **USD 12.477564**. All 66 new Codex attempts retain unknown dollar cost under the
owner's bounded subscription approval. No API-key fallback, judge call or extra retry was
introduced. No additional model run is scheduled by this report.

[unverified] WP-10 is not complete: full reliability correctness, GCP B completeness,
exact quotation under the remaining instrument gaps, broader qualification and human
acceptance remain open. The named native helper-return comparison in RELIABILITY-001
is a different profile and is not discharged by these assessment-document trials.
