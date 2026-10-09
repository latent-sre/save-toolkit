# PRINCIPAL-001: design judgment acceptance candidate

Status: 2026-10-08 familiar and held-out cases independently AI-reviewed; targeted tracker
advantage, two design ties, and stronger method/boundary consistency. Human acceptance open.
Owner: Save Toolkit maintainers. Starting revision: `37bb5600`; candidate branch:
`work/principal-001-judgment`. This packet does not accept the lane or authorize another campaign.

## Owner decision and scope

On 2026-10-07 the owner selected **demonstrably better design judgment, plus consistent usable
records** as the acceptance bar, then approved the alerting prerequisite repair and semantic
rubric preparation. Keep one combined design/architecture lane provisional. The
[lane ADR](../decisions/2026-10-05-principal-engineer.md) stays proposed.

The owner subsequently approved a USD 10 ceiling for twelve native attempts using the existing
written-record pairs, with document review and no model judge. All twelve attempts are retained:
eleven completed and one was interrupted by authentication after writing its document. Recorded
task cost is **USD 2.351204**; judge cost and calls are zero. See the native evidence below.

On 2026-10-08 the owner approved repairing the demonstrated failures before another campaign.
The source repair at the end of this packet is a new candidate. The earlier native results remain
bound to their original digest and do not verify the repaired candidate's behavior.

The owner then approved another twelve attempts under the same USD 10 ceiling. All twelve
completed for **USD 2.306003**, with no interruptions or retries. The final section records the
repaired candidate's targeted improvement, residual errors and remaining acceptance limits.

The [earlier campaigns](2026-10-05-principal-engineer-evals.md) establish record consistency,
not superior judgment: paired decision fields matched, and structural passes missed endpoint
retirement, shared-fate monitoring and infeasible migration gates. The new-system follow-up's
three principal records each passed 14/15 checks and failed the `obs-alerting` load check.
Preserve those failures and their exact revisions.

## Implemented candidate

- `principal-engineer` now requires loading the relevant alert/dashboard guidance from the service's
  requirements, with the same "not ready to return" consequence as the data-plan prerequisite.
  The existing written-record alert-load checks remain unchanged. Offline wording verification
  cannot prove the model will load the skill.
- The inactive [`principal_design_judgment` proposal](../../evals/proposals/principal-judgment/rubrics.yaml)
  specifies substantive design reasoning for two bounded cases. It does not grade headings, label counts, skill loading or agent identity.
  Its supplied facts distinguish each case; missing approval, integration and target evidence
  stays unknown. Alternative mechanisms and proposed thresholds are allowed when justified.
- Four [proposed build scenarios](../../evals/proposals/principal-judgment/README.md) form principal/software-engineer pairs for contract migration and
  certificate-tracker design. Both arms receive identical prompts, original fixtures and checks.
  They return the complete record as their final response, which the existing rubric grader
  actually reads. Existing written-document/JSON cases remain separate format/method evidence.
  They are excluded from the default catalog until activation and accepted calibration are
  approved. No runner or judge implementation is changed.
- Eighteen inactive proposed calibration examples comprise eight positives and ten single-fault negatives.
  Positive controls include additive/versioned API migration and active-inventory/latest-run
  paging. Negatives cover request-log and producer-only migration proof, an incompatible first
  release, retired-endpoint pages, database-only heartbeat, no-data-only error handling,
  rescanning lost history and invented accepted targets. The 2026-10-08 additions contrast a
  supplied CSV with a false absence claim, and a preservation prerequisite with destructive
  rollout relying on an unconfirmed restore. These are proposed human labels;
  offline parsing and tests do not calibrate a live judge. The two PR-review additions cite exact
  fixture facts omitted from the former summary. The proposal now embeds each full scenario
  prompt and every fixture file, with a round-trip binding test; summaries do not restrict which
  supplied facts a record may correctly cite.

## Acceptance observations

| Case | Material judgment to assess |
|---|---|
| Contract migration | All known consumers and unknown external readers; compatible first release; feasible consumer-side retirement evidence; local-time ambiguity; staged recovery preserving accepted data |
| Certificate tracker | Inventory-scoped expiry paging while retaining history; distinct missing-data/query-error notification paths and tests; shared-fate gaps; honest history recovery; unconfirmed integrations and unset targets |

Keep three separate results per record: deterministic authority/method/format checks, the semantic
rubric verdict, and a blind human review of each material judgment above. A wrapper or instrument
failure is not evidence the other agent makes better decisions. A complete record is not semantic
acceptance. A model verdict is evidence, not the owner's decision.

## Next decision

The two completed diagnostics supersede the earlier proposal for three separate canaries plus
twelve semantic trials. Do not rerun these familiar cases simply to obtain another green result.

An independent AI reviewer completed the author-hidden first pass and trace-reconciled second
pass, preserved below. It found repeated material improvement on the tracker case and a tie
without a principal regression on contract migration. Residual reasoning errors remain. The
owner approved preserving the reports, reconciling the evidence and preparing one
[fresh held-out task](2026-10-08-principal-heldout-cutover.md), without changing the measured lane
sources. Its separately approved six-trial campaign completed for USD 1.905009 and now has a
frozen first pass, prompted addendum and trace/unmasking review. The final held-out result is a
design tie with material findings in both arms, not a new superiority claim. Preserve all three
reports and prepare the [bounded follow-up](2026-10-08-principal-heldout-cutover.md#disposition-and-bounded-follow-up)
before requesting further changes or paid trials. Human review/acceptance of the exact candidate
remains separate. The first campaign's interrupted slot remains unchanged; later campaigns are
new measurements, not replacement trials or pooled results.

If reusable automated semantic scoring is wanted, first review the proposed gold labels and settle
other EVAL-010 corpus/judge changes. Freeze the candidate and scoring inputs, then obtain a new
receipt under the everyday account. The original publication temporarily expanded the active
corpus to 197 cases. PR review exposed that this would invalidate unrelated calibration receipts:
the active corpus is now restored to main's 181 cases, with eighteen principal controls retained
outside it. Any future activation must calibrate the exact combined contract under a separate
scope/budget; no calibration is part of this approval.

EVAL-014 still gates affected routing comparisons. Picker usability, final-byte coverage of the
other cases, helper return/resume, other hosts/models and installed Copilot behavior remain outside
this preparation. None is supplied by offline tests or this packet.

## Offline verification of the first candidate (2026-10-07)

`evals/test_principal_judgment.py` pins the requirement-based alert prerequisite, paired fixture and
check equality, complete-record judge input, retained old load checks, case rendering, corpus
coverage and refusal before a model call without calibration. Its baseline run failed on the
absent prerequisite, scenarios, rubric and corpus. The existing principal and judge tests also
exercise deterministic decision checks, record-oracle counterexamples and calibration bindings.

[verified 2026-10-07] Tested the uncommitted candidate working tree based on `37bb5600`, in its
isolated Python 3.14.7 environment with the repository's pinned test requirements:

| Check | Result |
|---|---|
| Principal judgment, existing principal, judge, skill assets and fleet-validator suites | 160 tests and 509 subtests passed |
| Full suite, four workers with `PYTHONDONTWRITEBYTECODE=1` | 1,889 tests and 4,050 subtests passed; 41 skipped; 306.39 seconds |
| Ruff lint and format; strict mypy | PASS; 19 formatted/type-checked source files |
| Offline scenario validation | 211 specifications and 883 expectations |
| Adapter regeneration | PASS; 174 outputs checked/generated; only the principal mirrors changed |
| Gate A, links and whitespace | PASS; Gate A 2/2 |
| Parsed calibration corpus | 177 cases; 12 new principal examples |

The runner, judge implementation and existing written-record cases are unchanged. These offline
checks preceded the native diagnostic below; they did not calibrate a judge. The candidate remains
uncommitted and unpushed. Native evidence binds the dirty candidate by its complete source digest
and retained patch, not by the base commit alone.

## Native diagnostic: identity, budget and execution

[verified 2026-10-07 America/Chicago; 2026-10-08 UTC] The owner-approved campaign used the ordinary,
unelevated Windows account, Python 3.14.7 and Claude Code 2.1.292. It requested `sonnet`; every
actual model response was `claude-sonnet-5-5`.

- Base: `37bb56009e873621bfd014bf093f5153cd69fab4`, with the uncommitted candidate changes.
- Plugin source SHA256: `fb1331df411f74340b577fd4ac17f7803fb6f28b63d58a38a2da43e5294885f2`.
- Unchanged runner SHA256: `633770b9656dbd8980df842af9d0e41e7e233ab293f69338de05f280c9d249d3`.
- The four existing contract-change/new-system scenarios retained identical prompt, fixture,
  success criteria and checks within each principal/builder pair. No runtime rubric was used.
- Twelve serial, interleaved attempts, three per arm and case; USD 0.75 native limit per trial,
  900-second timeout, campaign accounting across both arms, and a USD 8.50 stop-scheduling
  threshold to preserve headroom below the approved USD 10 ceiling. No budget stop occurred.
- Estimated review allowance: 1-2 hours. Historical cost reference stated before launch:
  USD 4.18 for the earlier fifteen-trial campaign. Actual task cost: **USD 2.351204**,
  all known; **zero judge/calibration calls and USD 0 judge cost**. No retries or replacements.
- Private evidence root: `.eval-runs/principal-001-judgment-20261007/`. It retains the registration,
  launch scripts/logs, candidate patch, each original trace/grade/result record, full workspace
  patches, and normalized design exports. Source digests stayed constant across all attempts.

Attempt seven (builder contract run 2) wrote its design, then its isolated OAuth session expired
and could not refresh. Its USD 0.141661 cost and INCONCLUSIVE result remain unchanged. The CLI's
error response used model `<synthetic>`; the frozen runner consequently reports mixed model
identities for that scenario. This placeholder is an authentication-error artifact, not evidence
of a second actual model. Do not publish a pooled builder-contract verdict from this campaign.

The original run stopped. Read-only account checks found credentials already refreshed after
that attempt began and valid for the following eight hours. The five unrun slots then continued
with the same candidate, controls and budget. The interrupted slot was not retried. The private
`auth-interruption.md` records the timestamps and preserves this distinction.

## Deterministic results and their scope

| Existing written-record case | Principal | Software engineer |
|---|---|---|
| Contract migration | 3 PASS, each 19/19 | 2 FAIL, each 17/19; 1 authentication INCONCLUSIVE |
| Certificate tracker | 3 PASS, each 15/15 | 3 FAIL: 13/15, 12/15, 12/15 |
| Alert guidance loaded before tracker design | 3/3 | 0/3 |
| Required record-oracle contract on completed runs | 6/6 | 0/5 |

The builder's completed failures are guidance loading and the required record contract. Its
documents still contain useful design reasoning; missing recognized slots/labels is not itself
proof of worse engineering judgment. All completed runs respected the design-only file boundary,
made no commits, executed no shell commands and delegated no tasks. The failed authentication
attempt is not counted as a successful boundary test.

The revised principal candidate loaded `obs-alerting` in all three tracker runs, unlike the prior
candidate's 0/3. This establishes behavior on the measured candidate/model/host. It is not an
isolated causal A/B test of the sentence, nor proof the guidance was correctly applied.

## Provisional document assessment

The coordinating assistant read all twelve written documents, including the artifact from the
interrupted run. It knows the authors and authored the candidate; this is **author-aware assistant
review**, not independent human review, calibrated gold labels or automated semantic PASS rates.

Material evidence against accepting the stronger bar now:

1. **Retired endpoints can keep paging (principal tracker run 1).** The page uses "any endpoint's
   latest known cert" and the schema/queries contain no current-inventory or latest-run membership
   filter. Removed endpoints retain old results for 90 days. The first builder tracker document
   explicitly excludes endpoints absent from the latest run. This is a substantive comparison
   where the principal record's extra structure does not supply the better decision.
2. **Database-outage alerting is not established (principal tracker runs 1 and 3).** Both route
   database failure to a freshness alert whose state is queried from that database. Run 1 says
   "Run fails, staleness alert"; run 3 says "Task run fails; freshness alert fires". Neither
   specifies and tests the query-error notification path. No-data tests alone do not establish it.
   Run 2 does explicitly configure query-error notifications and test their route; none of the
   three builder tracker records specifies that complete path. The improvement is inconsistent.
3. **A false verified input claim (principal tracker run 2).** It says
   `inventory/endpoints.csv` is "not present in this checkout" and proposes deciding whether it
   gains an owner column. The unchanged fixture supplies that CSV with `host,port,app,owner`.
   The trace shows `Glob("**/*.md")`, three Markdown results, and no read of the CSV: a
   Markdown-only search was incorrectly treated as proof of file absence. This is a model
   evidence error, not a missing fixture or grader inference.
4. **Recovery depends on missing preservation evidence (principal tracker run 3).** A wrong
   retention purge is to be recovered from broker backups whose existence and restore time are
   marked unverified. Shipping the purge last and testing its predicate do not establish that
   recovery path. The design needs verified preservation or an explicit owner trade-off before
   enabling destructive deletion. Runs 1 and 2 also propose dropping newly populated tables
   without clearly separating disposable trial data from required history.

The contract designs generally identify the three local readers, preserve the external unknown,
propose compatible staging, and use consumer-side retirement evidence. Principal runs 1 and 2
explicitly discuss strict readers rejecting additive fields. Overbroad safety claims still occur
in both arms: principal run 3's consumer table calls unknown readers unaffected before later
qualifying the risk, and the completed builder documents also make categorical safety claims.
The interrupted builder document usefully proposes a legacy-free route for observable request
evidence, but its artifact cannot repair the incomplete trial.

**Recommendation: keep PRINCIPAL-001 active and do not accept superior design judgment yet.**
The readiness sentence has native support, and required-record consistency is stronger. The
candidate still makes material lifecycle, failure-path, recovery and source-grounding errors.
These two familiar cases and one interrupted pair do not support a general superiority claim.

## Owner review packet

The private `blind-review/` directory contains twelve complete documents labeled D01-D12, supplied
case facts, the preregistered criteria and a blank review sheet. Extraction verified each complete
new-file hunk's line count; explicit author/role fields were hidden while substantive content was
retained. `review-key.json` is outside that directory and binds each export to its source, hash,
trial status and any identity redaction. The interrupted trial's document is present for artifact
review; its runtime outcome remains INCONCLUSIVE.

Reviewers should record judgments before opening that key. Conversation participants have already
seen some author-attributed findings, so a teammate who has not read those findings is needed for
an independent masked review. No such human review or exact-candidate acceptance is claimed here.

## Approved source repair (2026-10-08)

The owner approved the recommendation to fix the demonstrated failures before another campaign.
The changes are confined to the owning guidance and the comparison material:

| Demonstrated failure | Changed source | Repair direction |
|---|---|---|
| Markdown-only search reported the supplied CSV absent | [`principal-engineer` method](../../agents/principal-engineer.md) | Open named inputs before absence claims or contract changes; distinguish not read/inaccessible from absent |
| Retained results kept removed endpoints eligible for paging | [`principal` new-system data step](../../skills/eng-ladder/references/principal.md) | Name the membership filter for actions limited to current members; preserve history separately |
| Database-backed age query was said to detect that database's outage | [`obs-alerting` scheduled-work guidance](../../skills/obs-alerting/SKILL.md) | Trace shared dependencies; specify query-error notification or independent detection and test it separately from missing data through the receiver |
| Destructive recovery relied on an unconfirmed backup | [`principal` first-release recovery guidance](../../skills/eng-ladder/references/principal.md) | Gate the stage on preservation evidence or an explicit owner decision accepting loss; distinguish disposable tests from required history |

The data-guidance prerequisite also covers new stored data and retention, closing the observed
first-release exemption. Existing database-reliability recovery rules are retained. No tool grants,
delegation, runner, judge implementation, original scenario prompts or written-record graders change.

The semantic rubric now supplies the CSV's exact path and rejects false absence/column claims.
It explicitly distinguishes an unverified restore label from a real stage prerequisite. Four new
proposed calibration cases bring the corpus to **181 total**, of which **16** are principal cases
(six positive, ten negative). Positive controls allow source-grounded input claims and a proposed
destructive stage that remains blocked on preservation evidence; negatives reproduce the two
newly exposed errors. No live calibration or automatic semantic grading was performed.

Normalized UTF-8 runtime-source growth relative to the measured candidate:

| Canonical source | Bytes | Lines |
|---|---:|---:|
| `agents/principal-engineer.md` | +187 | +2 |
| `skills/eng-ladder/references/principal.md` | +584 | +5 |
| `skills/obs-alerting/SKILL.md` | +360 | +5 |
| Total | +1,131 | +12 |

The new plugin source SHA256 is
`fb2fba9ac7800518dad140ebb601dd6ddda97c9d88a489771236a21f4b6b4050`.
The runner remains
`633770b9656dbd8980df842af9d0e41e7e233ab293f69338de05f280c9d249d3`.
The candidate is local, uncommitted and unpushed. Before-source copies are retained privately
under `.eval-runs/principal-001-repair-20261008/`; the earlier native evidence is unchanged.

[verified] The affected baseline passed 30 tests/243 subtests. The extended corpus/rendering check
then failed on the four absent cases and missing CSV path in the judge context. After the repair:

- Principal, alerting, judge, authority, asset and fleet-validator suites: **166 tests and 535
  subtests passed** on the final source, 12.67 seconds.
- Scenario validation: **211 specifications, 883 expectations**; adapters: **174 outputs**, PASS.
- Ruff lint/format, strict mypy (19 sources), links and whitespace: PASS.
- Runner, judge and grader source diff: unchanged. No new model calls or spend.

These checks establish coherent source, examples, projection and evaluation wiring. They do not
prove the model follows the new instructions or that the proposed labels agree with a live judge.
No larger keyword checker or additional prompt-text assertion suite was introduced. The full-suite
result recorded above belongs to the earlier candidate; it is not restamped as a new run.

## Repaired-candidate native comparison (2026-10-08)

[verified] The owner approved twelve new attempts under the same USD 10 campaign ceiling.
The preregistered comparison froze the repaired plugin digest `fb2fba9ac780` (full value above),
the unchanged runner digest, the four original written-record scenarios, and the previous limits:
USD 0.75 native limit per trial, 900-second timeout, serial interleaving, no retries, and a
USD 8.50 stop-scheduling threshold. Prompt, fixture, success criteria and checks remained identical
within each pair. Both arms could load the repaired shared guidance. No semantic judge was used.

All twelve trials completed under the ordinary unelevated Windows account, Python 3.14.7 and
Claude Code 2.1.292. Every actual model response reported `claude-sonnet-5-5`. All costs are known:
**USD 2.306003 total**, comprising **USD 1.337870 principal** and **USD 0.968133 builder**. There
were no interruptions, retries, replacements, identity changes or judge/calibration calls.
The earlier USD 2.351204 campaign remains a separate historical receipt, not pooled evidence.

| Existing written-record case | Principal | Software engineer |
|---|---|---|
| Contract migration | 3 PASS, each 19/19 | 3 FAIL, each 17/19 |
| Certificate tracker | 3 PASS, each 15/15 | 3 FAIL: 12/15, 12/15, 11/15 |
| Required record-oracle contract | 6/6 | 0/6 |
| Tracker CSV successfully read | 3/3 | 1/3 |
| Tracker database and alert guidance loaded | 3/3 for each | 0/3 for each |

The builder omitted `eng-ladder` in all six runs and `obs-alerting` in all three tracker runs.
Its exact record-slot/label failures do not establish worse substantive reasoning. Tracker run 3
also executed read-only `git status --short; git log --oneline -5` despite the assignment's
no-shell constraint. **Correction after trace reconciliation:** neither its document nor its
final JSON claims that nothing was executed; the earlier attribution of that false claim is
withdrawn. No principal run executed a shell command. All twelve changed only the requested design document, made no commits and
delegated no tasks. These are observed boundaries, not hard host-enforcement claims.

### Substantive result, separate from structural passes

The coordinating assistant read all twelve complete designs. It knows the authors and prepared
the candidate, so the following is **author-aware assessment**, not blind human review or semantic
PASS rates. The target repair criteria were registered before generation.

| Previously demonstrated defect | Repaired principal tracker evidence | Builder comparison |
|---|---|---|
| Supplied CSV/owner column declared absent | 3/3 correctly ground the input; raw tool-result pairs show successful reads of the actual `host,port,app,owner` header and all three fixture rows | Run 3 reads it; runs 1/2 do not. Run 2's proposed input omits `app` and adds an optional name without reading the file |
| Retained history makes retired endpoints page | 3/3 explicitly constrain alerting to active inventory or latest-successful-run membership, while preserving history | Run 1 is unclear: dashboard membership is mentioned but the page predicate is not constrained; runs 2/3 use latest-per-endpoint without a current-membership condition |
| Database failure sent to a database-backed age query | 3/3 specify query-error notification and a distinct test through a non-production contact; shared evaluator/notification gaps remain explicit decisions | No tracker run establishes that complete failure-notification path |
| Destructive retention depends on unconfirmed restore | 3/3 gate retention on preservation evidence or an owner decision accepting history loss; rescanning is not historical recovery | No tracker run gates destructive retention on preservation of required history; an open backup question alone does not establish recovery |

Principal tracker run 2 has the clearest preservation gate: the purge is enabled only after a
restore has shown it preserves `cert_check`, or the owner accepts loss. Run 3 is less direct but
explicitly gates the stage on the owner's tested-restore-versus-loss decision. Its dry-run count
and row guard are prevention, not proof that an unverified backup can restore history. These
records propose tests; none of the designed alerts, databases or restores was implemented or tested.

**The material advantage is repeated on the tracker case; contract migration is broadly
comparable.** Both lanes usually find the local readers, retain the external unknown, preserve
storage, and use consumer-side migration evidence. Useful builder reasoning remains visible
despite formal record failures. The builder did not actually load the requested shared design
method, so this measures the whole lane's behavior, including guidance selection and application,
not superior reasoning with identical consumed context or an isolated effect of one prompt rule.

Residual findings are retained rather than repaired during measurement:

- Principal tracker run 3 explains a proposed 36-hour threshold as "one missed daily run plus
  grace". A success at hour 0, miss at hour 24 and next success at hour 48 would already alert at
  hour 36. The owner still has a decision, not an invented accepted target, but the explanation
  is wrong. Builder tracker run 2 has the same error.
- Principal contract run 3 says all three local readers parse the exact old format, despite its
  own SPA row correctly describing raw display. Distinguish CLI/Grafana parsing failure from
  changed display semantics. The compatible migration recommendation remains useful.
- Categorical first-release safety headlines need the strict-reader/unknown-consumer qualification
  already discussed later. Current-inventory propagation, complete-run freshness semantics and
  independent alert-evaluator detection also retain implementation/owner decisions.

**Recommendation: retain the repaired candidate for independent review and a fresh held-out
case; keep PRINCIPAL-001 active and the ADR proposed.** This is encouraging evidence of targeted
improvement and usable records, not broad superiority or exact-candidate human acceptance.
The two cases are familiar and influenced the repair. No extra trials or source fixes are implied.

### Evidence packet and verification boundary

Private root: `.eval-runs/principal-001-judgment-20261008/`. It retains registration, launch
script/log, candidate patch and guidance snapshots, the twelve original traces/grades/records,
full workspace patches, `assistant-review.md`, and the author-hidden `blind-review/` packet.
All twelve exported new-file line counts match their patch headers; `review-key.json` binds
original and masked SHA256 values and stays outside the review folder. Four explicit author
fields were masked, eight records were unchanged. Substantive content remains intact. This is
author hiding, not a guarantee that style or handoff language cannot suggest the lane.

The blank `blind-review/review-sheet.md` is for owner/teammate scoring before opening the key or
assistant assessment. No completed independent human scoring is claimed. Judge calibration,
other models/hosts, picker usability and the other existing acceptance gaps remain unmeasured.

Only evidence documents changed after the campaign. Final source/runner fingerprints remained
identical to the measured values; adapters, documentation links and whitespace were rechecked.
The earlier 166-test/535-subtest receipt was not rerun or presented as a new suite result.

## Independent AI review and reconciliation (2026-10-08)

The owner supplied a separate Claude session's two-pass assessment, then approved preserving it
outside the temporary folder. These reports are copied verbatim, not rewritten to match the
coordinating assistant's findings:

- [First pass, authors hidden](2026-10-08-principal-independent-first-pass.md), SHA256
  `52de5f701a5616f45f96d0e7067dea32a31cf9212af8a43a25b5c314c6d470ea`.
- [Second pass, identity and trace reconciliation](2026-10-08-principal-independent-second-pass.md),
  SHA256 `b47a515f85b59971ff96a6c632ce3006125b4453e9873fd179c140db2e694618`.

[verified] Both preserved copies match the supplied source files byte for byte. The first-pass
hash is unchanged after the second pass. All twelve original/masked document hashes still match
the review key, and the plugin/runner fingerprints remain the measured values. The reviewer
reports having kept the key and earlier assessments out of the first pass, and the coordinating
assessment out of both passes; that access history is reviewer-reported, not independently audited.
This is independent AI review, not independent human review or calibrated judge labels.

The first-pass tracker split aligns exactly with the arms: principal D04/D05/D12 were rated sound
on all five criteria; builder D02/D06/D07 had material design gaps. Contract migration was broadly
tied. The second pass changed D06's evidence rating from unclear to a low-severity material defect
after confirming its unlabeled column list described a CSV it never read. It separately confirmed
D02's prohibited read-only shell call without attributing a false non-execution claim. Other
first-pass semantic ratings and comparison order were preserved.

The independent review supports the selected stronger bar **on these two familiar tasks**. It
does not establish broad superiority, successful operation of the proposed systems, or weak
software implementation capability. Principal's absent shell tool is part of its boundary design;
the method-load pattern is consistent with a combined-role benefit, not isolated causal proof.

The blinding limitation is now specific: all four explicit author-field redactions were principal
records. A future packet must normalize the author field in every record, including documents
that lacked it. Original exports and independent reports remain unchanged.

Reconciliation notes preserve disagreement and uncertainty rather than silently editing the review:

- The independent reviewer marks builder tracker run 2's preservation plan unclear; the earlier
  coordinating review calls its absent stage prerequisite a material defect. Both agree that
  backup coverage is unresolved and does not gate the purge. Keep both assessments visible.
- The review's "all eleven" non-execution-statement count enumerates nine records. Do not reuse
  that count. The independently checked runtime fact is eleven runs with no shell call and one
  with a shell call; these are different claims.
- Latest-run versus last-known-good expiry behavior remains a design choice requiring treatment
  of failed probes. Membership wording alone does not prove all error-state behavior. Existing
  freshness-arithmetic and compatibility-wording concerns remain in the coordinating assessment.
- Skill-load checks measure actual required-method use, not semantic quality or an inherent arm
  identity. The builder's current instructions require `eng-ladder` for these design forks; its
  six omissions are an observed adherence gap. Neither this nor formal headings alone establishes
  lack of implementation ability.

The [held-out preparation](2026-10-08-principal-heldout-cutover.md) fixes the next case and review
protocol before outputs exist. It keeps lane/tool sources and the runner unchanged. No new live
calls, judge calibration, human acceptance, commit or push is implied by this reconciliation.

[verified after preparation] The held-out pair's four initial tests failed on missing scenario
files; the completed pair and affected principal suites then passed **23 tests and 160 subtests**
in 5.77 seconds. The new test file's initial formatting and strict-type failures were corrected;
Ruff lint/format and mypy now pass. Offline scenario validation reports **213 specifications and
899 expectations**. Links, adapters and tracked whitespace checks pass. The two preserved review
hashes and the measured plugin/runner digests remain unchanged. These are offline preparation
receipts, not new model evidence; the prior full-suite and 166-test receipts remain historical.

## Held-out follow-through (2026-10-08)

The [live-store cutover receipt](2026-10-08-principal-heldout-cutover.md#native-receipt-and-provisional-assessment-2026-10-08)
records the owner's separately approved six attempts, all completed for USD 1.905009, with the
same candidate/model and the earlier installed CLI pinned explicitly. Principal was 3/3 on
structural checks, builder 0/3; two builder runs nevertheless loaded design/database guidance
after a forbidden shell call, so the method-check failures must not be reported as absent loads.
All builder runs retrieved the supplied inputs, including one through Bash.

The coordinating assistant found useful design reasoning in both arms, replay-cursor uncertainty,
a material principal fence/abort contradiction and builder boundary/reporting failures. The
[completed independent reconciliation](2026-10-08-principal-heldout-cutover.md#independent-ai-review-and-final-reconciliation-2026-10-08)
preserves the first pass, prompted addendum and trace/unmasking report verbatim, with hashes and
the final six-record table. It confirms comparable substantive quality, not held-out superiority.
The first two cases' independent ratings remain separate: one tracker advantage and two ties
across the three cases do not establish general superiority. Principal's observed advantage is
method and authority consistency, partly supported by absent shell authority.

H05's initially material abort finding becomes a low note under its listed sub-action order;
unknown outcomes and incomplete abort reversal remain open. H03's explicit fence contradiction
remains material. The three builder non-execution claims conflict literally with successful
read-only shell calls; the reviewer records low contextual notes, not clean authority compliance.
No consistent design disadvantage was observed in these small trials; that is not a general
non-regression or equivalence proof.

The owner authorized this evidence update and PR, not acceptance or another campaign. Keep
PRINCIPAL-001 active and the ADR proposed. No prompt repair or new model run follows from this
publication step. Follow-up scope covers the measured adherence/reporting gaps, shared cutover
reasoning, misleading method-check labels, and a more discriminating future judgment case.

## Publication verification (2026-10-08)

Main `cfeec10c` was integrated normally. Its newer builder guidance and judge code do not inherit
the historical native receipts above. The measured canonical principal/method/alerting sources
and both held-out scenarios remain byte-identical to their pre-publication copies; all five
preserved independent reports match their supplied SHA256 values.

Two integration checks first failed and were corrected before the final offline run:
the rubric-rendering test bypassed main's new response-frame tag, and the retention gate required
live roadmap citations for the five raw reports. The test now captures the actual judge prompt
with the process mocked out and stopped before execution or spend; the roadmap directly records
why each report remains retained. No judge implementation or measured scenario was changed.

Fresh checks with the verified Python 3.14.7 environment:

| Check | Result |
|---|---|
| Principal and link/retention tests | 62 passed, 1 skipped, 174 subtests passed |
| Full offline suite, `pytest -q -n 4 --dist loadfile`, bytecode disabled | 2,002 passed, 49 skipped, 4 warnings, 4,370 subtests passed in 303.72 seconds |
| Ruff lint and format check | PASS; 21 source files already formatted |
| Strict mypy | PASS; 21 source files |
| Build-scenario validation | PASS; 243 specifications, 1,050 graded expectations |
| Adapter regeneration | PASS; 174 outputs, no additional changes |
| PR whitespace check against refreshed main | PASS |

The suite's four warnings are the dependency's deprecated AnyIO BlockingPortal alias, repeated
across workers. Skipped checks are not passes. The push-boundary Gate A result is recorded in the
PR. At that publication head the 197-case live judge calibration was deliberately not run without its own approval;
there are no new native/model receipts. These checks verify publication integrity and offline
contracts, not design superiority, successful operation of a proposed system or human acceptance.

## PR review remediation (2026-10-08)

The owner requested fixes for PR #338's three review findings after the normal merge of main
`2b3b28b8`. The original model archives, five verbatim AI reports, measured principal guidance,
and held-out structural scenarios remain unchanged.

- [Global calibration activation](https://github.com/latent-sre/save-toolkit/pull/338#discussion_r4226044923):
  `load_binding()` binds the entire canonical rubric/corpus maps, not only the requested rubric.
  The proposed rubric, controls and four unmeasured semantic scenarios now live under
  [the inactive proposal](../../evals/proposals/principal-judgment/README.md). Both active YAML
  contracts match main byte for byte; keeping this proposal no longer changes their digests.
  Existing receipts still need to satisfy all other runner/judge identity requirements.
- [Complete fixture context](https://github.com/latent-sre/save-toolkit/pull/338#discussion_r4226044932):
  the proposed rubric now contains each complete prompt and all fixture file contents, keyed by
  case and including untrusted notes as evidence only. A rendered JSON round-trip check binds
  them to the paired scenarios. Two proposed positive controls cite the exact endpoint/port/owner
  and API/Grafana configuration facts that the former summaries omitted. This verifies context
  delivery, not a model's semantic verdict; live calibration remains unperformed.
- [Evidence provenance](https://github.com/latent-sre/save-toolkit/pull/338#discussion_r4226044941):
  the live PRINCIPAL-001 status now explicitly marks retained receipt observations and independent
  review conclusions `[sourced]`, links their reports, and labels general superiority and
  acceptance `[unverified]`. Historical results are not described as fresh PR-head verification.

[verified] Before the changes, the new exclusion test failed because the proposal was active,
and both full-context subtests failed because the judge had only the hand-written summaries.
Afterward the focused proposal suite passed; it also checks inactive-rubric refusal, refusal
without calibration under explicit offline proposal loading, and mocked prompt construction.
Fresh final verification is recorded with the remediation commit in the PR. No model call,
receipt bypass, acceptance decision or historical rescore is part of these repairs.
