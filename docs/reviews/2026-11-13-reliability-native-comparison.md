# RELIABILITY-001: matched native timing comparison

This execution and evidence packet supports [RELIABILITY-001](../fleet-roadmap.md).
The owner approved preparation and the two-arm comparison on 2026-11-13.
Execution does not accept or promote a candidate.

## Frozen execution contract

- Candidate: fresh main `13301b621f06496b4e8dbeed61d5848587ae0a73`, with its
  plugin guidance unchanged. The shared native scenario gains one explicit manual
  criterion for conditional false-return versus uncaught-exception reasoning.
- Control: the same candidate with only the retry-timing wording restored to its
  pre-`2d0292c1` meaning in `skills/resilience-analysis/SKILL.md` and the two
  surviving retry passages in `references/worked-contrasts.md`, plus regenerated
  adapters. Preserve current admission, overload, recovery and other guidance.
- Record both local commits, plugin digests, the common runner/scenario digests,
  CLI version, host/account and command limits before any model call.
- Run exactly one native `native-reliability-helper-return-and-resume` trial per
  arm on `claude-sonnet-5-5`, with the scenario's 18-turn limit and a 300-second
  wall guard per invocation. Each trial has an initial and resumed human turn.
  No retry, substitute model, extra canary or paid judge is authorized.
- Treat the approved approximately USD 1 estimate conservatively as a USD 1 total
  whole-trial scheduling ceiling. Reserve USD 0.50 before each trial and request
  at most USD 0.25 per invocation. Inspect complete actual spend between trials;
  schedule the second only with at least USD 0.50 remaining. The runner resumes
  a conversation automatically under its existing USD 0.75 instrument guard;
  this is not a per-resume aggregate stop. CLI requests may overrun by a response
  and are not a hard provider billing ceiling. Stop further trial scheduling on
  authentication loss, unknown spend, incomplete instrument evidence, input/model
  drift, or insufficient allowance. Preserve missing slots and actual failures.
- Complete the required exact-candidate coordinated heavy run once. Reuse that
  executable evidence for the control's prose-only difference, with focused asset,
  authority and adapter checks on the control. Do not duplicate the full suite.
- Independent static review checks the exact pair and review contract before
  execution. Independent semantic review receives opaque arm labels and actual
  traces, not a suggested verdict or the candidate/control mapping.

## Review checklist

Grade each arm against the complete frozen scenario, separately from structural
results. Record PASS, FAIL or INCONCLUSIVE per criterion with trace locations:

1. Pinned reliability parent, exactly one completed SRE helper, parent continuation
   and an actual same-session follow-up.
2. Bounded helper request, completed evidence read, provenance, and synthesis after
   helper return.
3. Old r7 evidence does not close r8; current r8 evidence closes only the tested
   slow-ledger pool lead, without whole-service or deployment approval.
4. Morgan remains the human owner, the invoking caller the recipient, and untested
   redelivery/deduplication and larger-load behavior remain unknown.
5. Any claimed post-helper reread has a completed parent read after helper return;
   earlier reads and supplied records keep their actual provenance.
6. Retry-count ambiguity, requested versus enforced timeout, backoff, cancellation
   and resource release remain attached to timing claims. No unconditional
   36-second elapsed/occupancy bound or claim that later early-failing attempts
   are unreachable under the overall deadline.
7. Conditional false-return versus uncaught-exception behavior is explained without
   inventing the unseen client's timeout behavior. The fixture supplies no retry
   implementation, so do not grade an invented concrete branch as established fact.

One sample per arm does not establish a reliability rate. A positive result is
bounded evidence for the owner's exact-candidate disposition.

## Frozen identities

| Input | Identity |
|---|---|
| Candidate commit | `1cec1d9b2de63a0d8a194525b3879684859c26c6` |
| Candidate plugin | `8446d62f8b3479ed09898c9bbc084f7b622dd1190d6fe419eeb9b68c669b46f7` |
| Control commit | `dbc5b25dc9ff1942b6a565ac7ca4356b2d99bd4f` |
| Control plugin | `e6c0b09c14ddf1f14c34192f9aa66545517a79ffef07728774641d2e4341935c` |
| Common runner commit | `1cec1d9b2de63a0d8a194525b3879684859c26c6` |
| Common runner source | `763b4bc011f23fb4e10ddffc9d8bf2b17f6f46643c39c32eee59f68c212f34d6` |
| Case | `1334ffba2b84a986facade7a97468a49fc4985a5f9f00d1614fb5a593427f5b6` |
| Runner-bound scenario | `e8688614436ea982971c97b4d6693d48f019f9005481f25c2ccfe27886cb369a` |
| Frozen native selection | `33de9aa2ba986ab93e604b6d4562928cd103186fec5fce3a9407d2c7594989de` |

[verified] CLI `2.1.323`, resolved model `claude-sonnet-5-5`, Windows 11 AMD64,
host `Galactica`, unelevated account; the full account identifier is retained
privately in `freeze.json`. Both runs report the same runtime and clean plugin
inputs. Only the four canonical/generated timing files differ between arms.

## Preparation and qualification

[sourced: independent static pair review] No material finding in the exact pair;
the whole-trial scheduling clarification above resolves the reviewer's budget nit.
The clarification was frozen privately in `launch-contract.json` before execution.

[verified] Scenario validation passed for the exact frozen selection: one native
specification and three graded expectations. Candidate focused checks passed
15 tests and 26 subtests; control asset, authority and projection checks passed
62 tests and 270 subtests. Adapters were generated from the control's canonical
sources, and both diffs passed `git diff --check`.

**[verified] Full-suite qualification remains FAIL:** one coordinated
`scripts/local_tests.py --heavy` run at clean candidate `1cec1d9b` reported
**10 failed, 5,290 passed, 295 skipped and 5,077 passing subtests** in 538.341
seconds. The before/after receipt is clean at that exact commit:
`F:/repos/sre-agents/.git/local-test-runs/20261113T143021Z-0241eef8/`.
The full suite was not retried.

[verified] Final documentation changes leave both measured plugin digests, the
runner source digest and the frozen case digest unchanged. Gate A passed once:
2/2 structural steps. This does not change the full-suite FAIL or either semantic
FAIL; no full-suite rerun was needed for the report-only continuation.

[verified] A focused run of the two failing files on pristine main `13301b62`
reproduced the identical ten-failure set: 10 failed and 69 passed in 11.12 seconds.
Two failures are in `evals/test_incident_evidence_v2.py`: default Windows cp1252
decoding changes case identities. Explicit UTF-8 reproduces all 14 development
and four reserved frozen identities. Eight failures are in
`evals/test_itbench_native.py`: platform-default fixture writes produce CRLF,
changing frozen receipts; the raw fixture assertion exposes CRLF versus LF.
The exact failed test IDs and both XML receipts are retained privately.

[sourced: independent source and receipt review] These failures do not invalidate
the selected reliability observation. Its actual scenario loader reads UTF-8, its
inline fixture writer uses UTF-8/LF, and it never invokes ITBench preparation.
All 38 NativeConversation cases passed in the heavy run. Proceeding supplies a
bounded observation while retaining full-suite FAIL; it establishes no general
readiness or candidate acceptance. Repairing the separate Windows tests is outside
this timing comparison; specify UTF-8 reads and LF fixture writes when that work
is scoped, preserving historical identities rather than replacing golden hashes.

## Native execution

| Arm | Opaque label | Structural result | Reported USD | Elapsed seconds |
|---|---|---|---|---|
| Control `dbc5b25d` | maple | 3/3 PASS | 0.364608 | 57.3 |
| Candidate `1cec1d9b` | cedar | 3/3 PASS | 0.258161 | 46.4 |

[verified] Both trials completed, with one attempt per arm and four CLI
invocations total. The control ran first. Its complete reported spend left
USD 0.635392, sufficient for the USD 0.50 candidate reserve. Cumulative reported
cost is **USD 0.622769**, leaving **USD 0.377231** of the conservative scheduling
allowance. No retry, additional trial, substitute model or paid rubric judge ran.
These are CLI-reported equivalent costs, not an independently checked bill.

[verified] The operator ran `evals/build_probe.py run` once per arm using the
same frozen `--selection`, `--model claude-sonnet-5-5 --trials 1 --timeout 300
--max-invocation-usd 0.25`, each exact `--plugin-root` and
`--expect-plugin-digest`, and separate opaque labels. Whole-trial
`--max-batch-usd` requests were 1 and 0.635392 respectively. The private dispatch
receipts, summaries, invocation arguments and raw traces retain the full commands.

## Blind semantic review and disposition

[verified] Both initial and follow-up traces and responses were copied byte for
byte into an isolated review packet under opaque labels. All eight copies have
matching source hashes, and each response matches its own parsed invocation trace;
the parent response was not taken from the combined `outputs/response.md` file.
The reviewer receives the frozen scenario and raw conversations, without the
candidate/control mapping or an expected verdict.

[verified] Four actual `invocation.json` receipts were subsequently copied and
hash-bound under the same opaque labels, allowing the reviewer to certify the CLI
parent pin and resume arguments without seeing the arm mapping. The traces and
semantic criteria did not change. Both arms pass the complete native identity,
helper completion, parent continuation and same-session follow-up criterion.

**[sourced: independent blind semantic review] Both arms FAIL.** The coordinator
mapped the sealed proposals back to their revisions; native mechanical grades
remain unchanged and separately report semantic assessment as UNVERIFIED.

| Frozen criterion | Candidate / cedar | Control / maple |
|---|---|---|
| 1. Native parent, helper and resume | PASS | PASS |
| 2. Bounded evidence exchange and provenance | FAIL | PASS |
| 3. Old/current revision and tested scope | PASS | PASS |
| 4. Owner, caller and remaining unknowns | PASS | PASS |
| 5. Actual read history | PASS | PASS |
| 6. Timing assumptions survive reuse | FAIL | FAIL |
| 7. Conditional return/exception paths | FAIL | FAIL |

[sourced: independent blind semantic review] Both whole conversations omit the
required conditional false-return versus uncaught-exception explanation. Both
also reuse illustrative arithmetic as an established timing or capacity limit.
The candidate initially preserves three/four-call ambiguity and says a timeout
sum is not an enforced bound (`cedar/initial-response.md:18`), but its final
recommendation then calls 36 seconds a worst case (`:55`). Its follow-up derives
approximately one post/second from 20 slots and a 20-second maximum (`:15`, `:24`)
without retaining a full-duration slot-occupancy assumption or shared read demand.
A maximum is not measured mean occupancy or a demonstrated saturation threshold.

[sourced: independent blind semantic review] The candidate additionally accepts
its helper's derived 36-second total labelled as sourced
(`cedar/initial-stdout.jsonl:26`, `cedar/initial-response.md:12`). The control
reuses a conditional 0.56/second model as a ceiling (`maple/initial-response.md:44`)
and converts the supplied 20-second deadline to a one/second sustained ceiling
(`maple/followup-response.md:4`, `:11`). It then reopens whether that explicitly
overall deadline is per attempt and claims it would cut a third attempt short
(`:12`, `:19`); early failures can permit later calls before the deadline.

[verified] The coordinator spot-checked those timing passages against the exact
replies. The independent review records a minor control read-line-count error and
an unsupported caller-address embellishment without making either a new mandatory
criterion. Both arms correctly reject deployment approval, keep r7 from closing
r8, preserve untested deduplication and larger load, and truthfully disclaim a
post-helper reread. Those passes do not erase the timing and branch failures.

[verified] The sealed review hashes are
`2db6f31277edbe5510545f6b4d80fe2dba85ad4afacc83394cad8f41ea196029`
(`review.md`) and
`7057ae645a446171d65ed52201a6d7f3d3c85ed892350c70e004e85aea155ba5`
(`review.json`). Private copies retain every criterion's evidence and limitations.

**Disposition:** the bounded comparison is complete and supplies no evidence to
accept this sample against the full frozen criteria. RELIABILITY-001 stays open
and the lane remains unaccepted. The owner decides whether to scope a narrow
repair or retain it shipped and unaccepted. A repair should address branch
analysis in the actual assessment, preserve assumptions at every reused timing or
capacity claim, and reconcile helper-derived claims with their source. No prompt
tuning, extra model call or new trial is scheduled. One sample per arm establishes
neither a rate nor a causal improvement. General qualification also retains the
separate full-suite FAIL.

## Private evidence

Raw evidence is retained at
`F:/repos/sre-agents/.eval-runs/reliability-native-20261113-1cec1d9b/`:
`freeze.json`, `selection.json`, `control.patch`, `launch-contract.json`, both
dispatch receipts, `qualification.json`, base reproduction log/XML, independent
static reviews, `campaign-summary.json`, `blind-bindings.json`, and each native
run's records and actual initial/follow-up invocation artifacts, supplemented by
`blind-invocation-bindings.json`, `blind-review-seal.json` and sealed review copies.
The isolated
semantic packet is `F:/repos/sre-agents/.eval-runs/reliability-blind-20261113-b9e2/`.

## Execution ledger

- [verified] The active Python-skill checkout was left untouched; preparation uses
  an isolated managed worktree from the fresh-main revision above.
- [verified] Local Claude Code is `2.1.323`; its status reports a logged-in
  first-party Claude subscription. Status alone does not prove a live invocation
  will authenticate or resolve the pinned model.
- [verified] Preparation and both native slots are complete. Full-suite FAIL and
  the base reproduction remain visible; no historical result was regraded.
- [sourced: independent blind review] Both native samples fail semantic criteria;
  the approved comparison is concluded with all failures preserved.
- [unverified] Broader reliability and exact-candidate human acceptance remain
  outstanding; no source repair or further trial follows automatically.
- [sourced: independent final documentation review] No material finding in the
  report or backlog delta; immutable commit binding remains a separate check.
- [verified] The primary checkout changed during review: final status is clean on
  `main` at `13301b62`; its reflog records a reset at 08:53:28 and branch switch
  at 08:53:57 on 2026-11-13, UTC-06:00. Actor identity is unknown. This comparison's
  source edits remain in the managed worktree, and its measured inputs are unchanged.

## Owner-requested source repair

The owner subsequently requested a fix for the observed reliability failures.
This section records a source candidate after the sealed comparison above; it does
not rewrite either native result or spend the unused allowance on additional slots.

[verified] Before editing, the incumbent at report commit `ff651f94` still had
plugin digest `8446d62f8b3479ed09898c9bbc084f7b622dd1190d6fe419eeb9b68c669b46f7`,
matching the failed native candidate `1cec1d9b`. Its sealed replies and blind review
therefore supply the applicable failure baseline without repeating model calls.

The repair changes only the canonical `resilience-analysis` skill and its worked
contrast, with regenerated projections:

- Required assessment elements replace analysis-only reminders: conditional return
  and exception paths appear in the answer when the path retries; numeric claims
  include their timing/capacity basis in the caller's permitted sections or fields.
- Conditions remain beside numbers when reused in recommendations, tables or checks.
  A maximum duration does not supply a mean slot residence or throughput ceiling.
- A supplied overall deadline retains its scope. Missing enforcement/release evidence
  does not reopen whether the deadline was per attempt.
- Helper-derived arithmetic is reconciled with the source and kept distinct from
  source-reported inputs. The worked contrast demonstrates the same output elements
  and preserves the nominal 36-second and hypothetical one/second conditions.

[verified] The repair leaves routing descriptions, agent authority, delegation,
tools, native scenario, graders and frozen semantic criteria unchanged. The branch is
`fix/reliability-001-assessment-reasoning-20261113`; the source remains a reviewable
local candidate. No commit, push, merge, deployment or new model campaign is implied
by the repair request.

[verified] Offline checks passed: `scripts/test_reliability_contract.py`,
`scripts/test_skill_assets.py` and `scripts/test_platform_adapters.py`, run together
with `python -m pytest -n 0 -q -p no:cacheprovider`: **62 tests and 270 subtests**.
Adapters regenerated successfully and `git diff --check` passed.

[verified] The complete canonical skill bundle grows **2,514 LF bytes**: the
entrypoint changes from 7,092 to 8,277 (+1,185), the worked contrast from 3,140 to
4,469 (+1,329), and the 1,908-byte failure-scenarios reference is unchanged. The
growth adds the missing answer elements and conditional counterexamples for the
observed failures; it does not establish token, latency or behavioral benefit.
The final local source plugin digest is
`6db50f2e9ebfb7cc00ca9935f001a5eae893360c5a90ba760106d46d99fce026`
against base commit `ff651f94782aadda930cadf2112e48218a9716dd` with these source
changes uncommitted. Private file hashes and the before/after byte accounting are
retained in `.eval-runs/reliability-001-repair/final-source-binding.json` in the
repair worktree.

[sourced: independent source review] No material finding remains. One review
correction makes three 12-second calls a sufficient example of 36 seconds rather
than a necessary explanation for any observed total; the one-slot-per-post
assumption is explicit. The reviewer verified the corrected paragraph and its
generated mirror. The final focused run passed 62 tests and 270 subtests in
9.49 seconds. Final Gate A passed 2/2 structural steps; `git diff --check` passed.

[unverified] New model behavior remains unmeasured. Static checks establish
asset/authority/projection consistency, not that the repaired model follows the
output contract. Native validation requires a newly
bounded allowance because both earlier approved slots are consumed. The existing
heavy receipt remains FAIL with the identical pristine-main failures above; this
prose-only repair does not repair or suppress those separate Windows tests.

## USD 20 verification

The owner subsequently approved a **new USD 20 spend ceiling** for verification
of the source repair. This allowance is separate from the earlier USD 0.622769
comparison. The previous raw results and sealed semantic FAILs remain unchanged.

### Frozen candidate and conditions

[verified] One repaired source candidate was frozen before any new native call.
The measured changes are only the canonical resilience skill and worked contrast;
generated projections also match. The baseline is the previous failed candidate's
plugin bytes, not the earlier timing-only control `dbc5b25d`.

| Binding | Exact identity |
|---|---|
| Baseline commit | `13301b621f06496b4e8dbeed61d5848587ae0a73` |
| Baseline plugin SHA-256 | `8446d62f8b3479ed09898c9bbc084f7b622dd1190d6fe419eeb9b68c669b46f7` |
| Repair base, with uncommitted source changes | `ff651f94782aadda930cadf2112e48218a9716dd` |
| Repaired plugin SHA-256 | `6db50f2e9ebfb7cc00ca9935f001a5eae893360c5a90ba760106d46d99fce026` |
| Frozen pre-launch patch SHA-256 | `0c44cb908c406e730cbed2fd78a22a0d13fec72546edd143ce892320a48c1b9e` |
| Common runner SHA-256 | `763b4bc011f23fb4e10ddffc9d8bf2b17f6f46643c39c32eee59f68c212f34d6` |
| Case SHA-256 | `1334ffba2b84a986facade7a97468a49fc4985a5f9f00d1614fb5a593427f5b6` |
| Scenario SHA-256 | `e8688614436ea982971c97b4d6693d48f019f9005481f25c2ccfe27886cb369a` |
| Selection-file SHA-256 | `d18d8fbcfe97d75f8a3e48501224137d803232e046a3d847ca0e1123613dfa4e` |

[verified] The plan selected only
`native-reliability-helper-return-and-resume`, with all seven criteria unchanged:
five trials per version, ten total, alternating which version runs first in each
pair. Each complete trial has an initial and resumed follow-up invocation.
Conditions remain Claude Code **2.1.323**, parent model **claude-sonnet-5-5**,
Windows 11 AMD64 on Galactica, the same unelevated account, 18 cumulative turns,
and 300 seconds per invocation. The runner records host execution, not a VM or
OS sandbox. Runtime and source bindings matched before each dispatch and source
bindings still matched at closeout.

[verified] The operator reserves USD 2 before each whole trial under the global
USD 20 ceiling and requests USD 0.50 per CLI invocation. The existing native
USD 0.75 instrument guard also applies. These are scheduling and stop controls;
the CLI request is soft and is not a hard provider billing cap. The frozen plan
permits one candidate, no retries, prompt edits, substitute model, extra case or
paid judge. Any incomplete cost/instrument evidence, structural non-PASS, input
drift or insufficient reserve stops further scheduling.

[sourced: independent prelaunch review] Two private-operator findings were fixed
before launch: bind the exact selection bytes and reject extra summary rows;
stop on a runner `record_problem` after retaining cost. Final static recheck had
no material launch blocker. [verified] Model-free negative controls rejected an
extra valid case and a byte-changed selection; process-ownership smoke passed.

### Exact-candidate qualification

[verified] The newly required coordinated heavy run completed once on the exact
repaired plugin: **10 failed, 5,290 passed, 295 skipped, 5,077 passing subtests**,
535.197 seconds in the local-runner receipt
`.git/local-test-runs/20261113T170344Z-11597a7b/`. The ten failure IDs exactly match
the saved pristine-main reproduction: two incident-evidence Windows encoding
failures and eight ITBench newline/receipt failures. All **38 native-conversation
tests passed**. Source was unchanged across the run, and the affected executable
paths are identical to the reproduced baseline. The selected-profile disposition
reuses the independent path-impact review; **full-suite qualification stays FAIL**.
The focused 62-test/270-subtest source evidence above remains applicable.

### Execution and stop

[verified] The campaign stopped after **five of ten planned trials**: two complete
pairs and the initial invocation of baseline slot 3. There were **nine CLI
invocations**, one attempt per slot, no paid judge and no retry. Baseline slots
4–5 and repaired slots 3–5 were never dispatched. Complete cost and successful
workspace-removal records exist for all five attempted trials.

| Dispatch | Version and slot | Structural result | CLI invocations | Reported USD |
|---|---|---|---:|---:|
| 1 | Baseline 1 | PASS, 3/3 | 2 | 0.366110 |
| 2 | Repaired 1 | PASS, 3/3 | 2 | 0.284001 |
| 3 | Repaired 2 | PASS, 3/3 | 2 | 0.276981 |
| 4 | Baseline 2 | PASS, 3/3 | 2 | 0.278787 |
| 5 | Baseline 3 | INCONCLUSIVE | 1 | 0.123651 |
| Total | Five attempted slots | Four complete conversations | 9 | **1.329530** |

[verified] USD **18.670470** of the new ceiling remains unspent. The total above
sums the rounded CLI-summary rows; raw record costs sum to approximately
USD 1.3295292. These are complete CLI-reported cost equivalents, not an
independently verified bill. Unspent allowance does not override the stop rule.

[sourced: independent tool-boundary investigation] In baseline slot 3, the SRE
helper attempted `Grep` on the synthetic evidence file. The runtime returned
`No such tool available: Grep` and explicitly said it was disabled in subagents
too (`stdout.jsonl:23–24`). No completed Grep operation is evidenced. The helper
then completed an allowed Read, returned, and the parent continued. The CLI
finished with exit code 0. The native runner counts attempted tool uses, detects
the ungranted name and voids the observation before follow-up; its preserved
reason is `native ungranted tool use: ['Grep']`. The raw structural grade remains
INCONCLUSIVE, with semantic assessment UNVERIFIED. A denied request and a
successful recovery do not supply the missing follow-up or justify regrading it.

[unverified] Why the helper selected the unavailable tool is unresolved. The
trace does not reveal its full tool schema. The helper's normal canonical tools
include Grep, but that alone does not prove a runtime advertising defect. Any
future policy decision about rejected attempts belongs to the native harness
and tool-profile owner, with separate offline regression evidence and a new
measurement identity if the contract changes. Do not widen tool grants to
salvage this trial.

### Independent semantic proposals

[verified] A fresh reviewer received opaque labels, the unchanged scenario and
review contract, and byte-exact copies of each available initial/follow-up reply,
raw trace and invocation record: **27 copied files**. An availability record
identifies the absent follow-up. Version mappings, source checkouts, previous
reviews and suggested verdicts were withheld. The reviewer wrote proposals
before mapping; copies and all original native artifacts still match their seals.
This is label blinding, not a claim that prompt text visible in a trace is hidden.

[sourced: independent blind review] The repaired source has **1 PASS and 1 FAIL
among two complete trials**. The baseline has **0 PASS and 2 FAIL among two
complete trials**, plus one partial trial with observable semantic failures.
The partial trial's raw native result stays INCONCLUSIVE; a semantic proposal
about its recorded initial answer does not replace that grade.

| Version and slot | Opaque label | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Semantic proposal |
|---|---|---|---|---|---|---|---|---|---|
| Baseline 1 | `trial-12b3257131` | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL |
| Repaired 1 | `trial-497a207d18` | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | FAIL |
| Repaired 2 | `trial-fe7653b5e3` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Baseline 2 | `trial-8e9f14faf5` | PASS | PASS | FAIL | PASS | PASS | FAIL | FAIL | FAIL |
| Baseline 3, partial | `trial-e0af1e7a6a` | INCONCLUSIVE | PASS | INCONCLUSIVE | INCONCLUSIVE | PASS | FAIL | FAIL | FAIL |

Criterion numbers refer to the frozen seven-item checklist above. The private
review retains exact file/line evidence for every cell.

[sourced: independent blind review] Both complete repaired replies include
conditional retry eligibility, caught versus uncaught exceptions and unknown
timeout behavior. Both avoid inferring throughput from a maximum. Repaired slot
2 also corrects the helper's retry shorthand, preserves three-versus-four total
calls and nominal 36/48-second sums, accepts the supplied overall-deadline scope,
and passes all seven criteria. These observations do not establish a success rate
or a causal improvement from the repair.

The remaining repaired failure is precise: slot 1's initial answer says
`up to 3 calls in total` and calls `3 calls and 12 s per attempt` sourced inputs
(`initial-response.md:23,29`). The follow-up again lists `3 attempts`
(`followup-response.md:14`). The source's “retries ... up to three times” leaves
three total calls versus an initial call plus three retries unresolved. The
reply drops that ambiguity rather than attaching it to the derived sum. Its
otherwise correct return/exception and capacity analysis cannot make criterion
6 pass. Baseline replies also retain the older timing/capacity and omitted-branch
failures; baseline slot 2 reopens the supplied overall-deadline scope.

[verified] The sealed blind review SHA-256 values are
`05b447a343bb45fd80285a94f1366477aa769123a39a7979c99317417b4777e9`
for Markdown and
`17a71bfbdffa7e7aa104ddaeb4e2c9d1f637c807020bc829f1f85665f8051698`
for JSON. The mapping and aggregation do not edit those proposals or any raw
mechanical grade.

### Disposition and retained evidence

**The bounded campaign is concluded after its stop; the repair is not accepted.**
It supplies one complete semantic PASS and one complete semantic FAIL for the
repaired bytes, rather than the five planned trials per version. RELIABILITY-001
stays open. No reliability rate, whole-service readiness, deployment approval or
lane promotion follows from this public regression case. The source candidate
remains uncommitted on the repair branch; no publication or further native call
is scheduled. The separate general qualification result remains FAIL.

The next decision is whether to scope a further repair of retry-count ambiguity
in the returned assessment. Before another paid campaign changes the native
measurement contract, the harness/tool-profile owner must explicitly settle the
policy for denied unavailable-tool attempts and cover it with a model-free
regression. The current attempt-sensitive policy and historical results remain
intact. Unused dollars and missing slots are not authorization to tune or retry
this concluded candidate loop.

[verified] New private evidence is retained at
`F:/repos/sre-agents/.eval-runs/reliability-20usd-20261113/`: `freeze.json`,
`selection.json`, `candidate.patch`, `qualification-disposition.json`,
`campaign-started.json`, `campaign-state.json`, all five operator logs and native
trial folders, `execution-closeout.json`, `blind-bindings.json`,
`sealed-blind-review.md`, `sealed-blind-review.json`, and `blind-review-seal.json`.
The isolated packet is
`F:/repos/sre-agents/.eval-runs/reliability-20usd-blind-20261113/`.
The repair worktree's ignored `.eval-runs/reliability-20usd/` retains the reviewed
one-off operator, negative-control/ownership preparation, independent prelaunch
review and denied-tool investigation. The
[live backlog](../fleet-roadmap.md#reliability-001--preserve-retry-count-uncertainty-and-qualify-the-native-assessment)
owns remaining work.

[verified] Final Gate A passed **2/2** structural steps after updating the case
guide's incoming backlog anchor; `git diff --check` passed. A final identity-only
dry run confirmed the frozen plugin, runner, case, selection and runtime bindings
without a model call. No repeated full suite was needed for these documentation
updates. [sourced: independent final documentation review] No material finding
remains in the new report/backlog delta; the ignored
`.eval-runs/reliability-20usd/final-doc-review.md` retains that review. These checks
do not change the native, semantic or general-qualification outcomes above.

## Retry-count repair verification

The owner approved a further narrow repair and matched comparison within the
**remaining USD 18.670470** of the existing USD 20 ceiling. This is a new frozen
loop, not replacement trials for either earlier comparison. Historical raw grades,
semantic proposals and missing slots remain unchanged.

### Source repair and shared test context

[verified] The main skill now requires a **retry-count basis** before calculation:
retain the source wording, distinguish maximum total calls from retries after the
initial call, and preserve compatible interpretations until evidence resolves
them. A selected interpretation cannot be called sourced. This belongs in the
entrypoint because the prior failing reply loaded the skill but never read the
worked reference. The contrast now starts with ambiguous retry wording and carries
three/four total calls through conditional 36/48-second sums; it no longer starts
from an explicitly established three-call total. Return/exception paths, known
overall-deadline scope, unknown enforcement/backoff/release, capacity basis and
source provenance retain their previous protections.

[verified] The complete canonical bundle grows **737 LF bytes** relative to the
preceding repair: entrypoint 8,277 to 8,685 (+408), contrast 4,469 to 4,798 (+329),
and failure-scenarios 1,908 unchanged; total 14,654 to 15,391. The increment targets
the observed count-interpretation failure and its returned assessment. It does not
establish a token, latency or population benefit. Generated mirrors match.

[verified] The shared scenario prompt now explicitly requires the parent to tell
the helper that only Read of `evidence.md` is permitted for that task. Both arms
receive this same sentence. Fixture evidence, follow-up, all seven success
criteria, tool grants, runtime denials, staging, executable runner and graders are
unchanged. The case identity changes because its prompt changes. Comparisons
against older runs cannot attribute this shared context effect to the skill.
No measured plugin is silently rewritten during staging.

### Frozen identities and bounds

| Binding | Exact identity |
|---|---|
| Common source base; both plugin inputs dirty | `ff651f94782aadda930cadf2112e48218a9716dd` |
| Preserved preceding-repair baseline plugin | `6db50f2e9ebfb7cc00ca9935f001a5eae893360c5a90ba760106d46d99fce026` |
| Revised candidate plugin | `3c29631501a51347d78e5bf927df2e82c352f719a7da7cc9d7f6432b48b87243` |
| Frozen pre-launch patch SHA-256 | `f75e5141443d385604b01480c0a329dcf0ccfdf2f3a1a3a9826877534a0bc21a` |
| Common runner SHA-256 | `763b4bc011f23fb4e10ddffc9d8bf2b17f6f46643c39c32eee59f68c212f34d6` |
| New common case SHA-256 | `151f747a27888a5f6b6366add6c2dd4ce19cec9507c43ddd8786c7b1d4cdd8b0` |
| New scenario SHA-256 | `c6215c712caa7e554632764a2be1b5ecc4dd9cf0c550fb2b29377591d4882c7e` |
| Selection-file SHA-256 | `6c486627e1b427967a960140aa7cfe141b880cc254d419fd4fbcd51c8c1171e0` |

[verified] The baseline was preserved before editing in managed checkout `0180`,
with its measured plugin hash checked against the preceding tested repair.
Candidate edits remain in `f086`. The native profile remains Claude Code 2.1.323,
`claude-sonnet-5-5`, the same Windows 11 AMD64 host and unelevated account, 18
cumulative turns and 300 seconds per invocation. The plan allows one candidate,
five trials per arm in alternating pair order, no retries or paid judges. It
retains the USD 0.50 soft CLI request, USD 2 whole-trial reserve and existing
instrument stops. Scheduling is not a hard provider billing cap.

[verified] The operator SHA-binds the preceding campaign's complete USD 1.329530
cost receipt and verifies that the additional USD 18.670470 ceiling sums to the
same USD 20 approval. Source, runtime, case and selection bindings are checked
before each dispatch. [sourced: independent source/operator review] No material
source finding or operator launch blocker remained in these reviewed increments.
The four-model testing block was consulted; this approved native case is measured
only on Sonnet. Structured Sol/Luna/Terra paths do not admit this helper/resume case
and remain unmeasured. No pooled model result is inferred.

### Qualification and additional failure

[verified] The single required exact-candidate heavy run finished in **558.438
runner seconds: 11 failed, 5,289 passed, 295 skipped, 5,077 passing subtests**.
Receipt: `.git/local-test-runs/20261113T213400Z-2111d3b2/`. The ten known pristine-main
failures remain, plus
`test_routes_cannot_choose_upstream_or_expose_usage[http://evil.test/v1/messages]`
in `evals/test_swebench_proxy.py`. That test aborted in a local HTTP response read
with WinError 10053; it did not report an incorrect route status. The failed run
did not reach its no-upstream-call assertion. All 38 NativeConversation checks
passed. Source was unchanged across the run and matched the frozen patch.

[verified] The exact additional proxy parameter passed **once**, in a focused
0.50-second check, including HTTP 404 and no upstream call. There was no full-suite
rerun or test retry loop. [unverified] The socket abort's root cause remains
unresolved; the focused pass does not repair or erase the full-run failure.

[sourced: independent path-impact review] The selected native path does not
construct or start that `ModelProxy`; its shared Windows job module owns
processes. The case has no backing service or fixture environment overrides, and
the reviewed launch environment has no proxy/base-URL overrides. Unchanged
executable paths and the saved focused result justify only the selected native
observation, not immunity to host-level aborts or general readiness. **Full-suite
qualification remains FAIL with eleven failures.**

[verified] A review-found P2 preflight gap was corrected: the focused prerequisite
must contain the exact testcase and cannot be skipped. Model-free negative
receipts for a different case and a skipped exact case were refused; the original
passing XML was restored byte-for-byte. Selection controls also refused an extra
valid case and changed selection bytes. The selected-profile disposition binds
the independent impact review and preserves the unresolved cause and full-suite
FAIL. Focused source/asset/adapter/native-contract checks passed **92 tests and
328 subtests** in 72.72 seconds; scenario validation passed one native spec with
three structural expectations.

### Completed native execution

[verified] All **ten planned trials**, five per arm, completed on attempt 1: twenty
CLI invocations, **3/3 structural checks in every trial**, complete reported costs
and successful removal of every trial workspace. No native tool-boundary stop,
missing slot, retry, paid judge or substitute model occurred. Source bindings still
match at closeout. Structural results alone do not assess the seven semantic
criteria or establish automatic agent discovery.

| Pair | Baseline reported USD | Revised reported USD |
|---|---:|---:|
| 1 | 0.379314 | 0.287244 |
| 2 | 0.313711 | 0.331560 |
| 3 | 0.284221 | 0.354854 |
| 4 | 0.294426 | 0.303586 |
| 5 | 0.293723 | 0.288512 |
| Total | 1.565395 | 1.565756 |

[verified] This loop reports **USD 3.131151**. Combined with the preceding
USD 1.329530, the current USD 20 approval reports **USD 4.460681**, leaving
**USD 15.539319** unspent. The older USD 0.622769 comparison is outside this newer
approval. Rounded summary rows supply these totals; raw new record costs sum to
approximately USD 3.1311508. They are CLI-reported cost equivalents, not an
independently verified bill. No cost or latency benefit is claimed. No further
metered call is scheduled.

### Independent semantic review and disposition

[verified] Two fresh label-blind reviewers each assessed five opaque trials using
the same scenario, seven criteria and review contract. They received **60
byte-exact files** in total: both replies, raw traces and actual invocation records
for every trial. Version mappings, source checkouts, earlier reviews and suggested
outcomes were withheld. Their four original review files were retained verbatim
before mapping; aggregation adds no new judgment. This is label blinding, not
concealment of skill text visible in a trace. Original native artifacts and copied
inputs still match their seals; raw structural grades remain unchanged.

[sourced: independent blind reviews] The revised candidate has **2 PASS and 3 FAIL
among five complete trials**. The preceding-repair baseline has **1 PASS and 4 FAIL
among five complete trials**. Every trial passes C1, C2, C4, C5 and C7: pinned
helper/resume structure, bounded Read-only evidence work, owner/caller and residual
uncertainty, honest read provenance, and conditional return/exception reasoning.
The following table lists all failing criteria; all other criteria pass.

| Pair | Baseline proposal | Revised proposal |
|---|---|---|
| 1 | PASS | PASS |
| 2 | FAIL C6 | FAIL C3, C6 |
| 3 | FAIL C6 | FAIL C6 |
| 4 | FAIL C6 | PASS |
| 5 | FAIL C6 | FAIL C6 |
| Total | **1/5 PASS** | **2/5 PASS** |

[sourced: independent blind reviews] The revised failures are:

- **Revised slot 2**, `trial-d56051c72d`: its initial answer preserves both count
  readings but calls the 36/48-second sums a duration bound without establishing
  backoff, timeout enforcement or release (`initial-response.md:36,41–43`). The
  reviewer also finds that the follow-up reopens supplied control coverage and
  denies concurrent-read coverage after recognizing the records
  (`followup-response.md:4–8,12,14`), failing C3 as well as C6.
- **Revised slot 3**, `trial-56ceecbd34`: the follow-up says at most two attempts
  fit before cancellation (`followup-response.md:10`). A 12-second maximum is not
  a minimum duration; early failures can permit more attempts within 20 seconds.
  The current overall deadline bounds the request, not its attempt count.
- **Revised slot 5**, `trial-a9b17ad5c6`: conditional 36/48-second sums become a
  claim that actual per-post time exceeds 20 seconds and that the old override
  does not fit (`initial-response.md:23–28`). An overall deadline could truncate
  either retry budget. The reason r7 cannot establish r8 safety is missing target
  binding/release evidence, not numerical incompatibility.

[sourced: independent blind reviews] Three baseline failures select three total
calls from ambiguous wording; the fourth categorically truncates a second attempt
without retaining the full-duration condition. Revised initial count handling is
stronger in these inspected examples, but required conditions still fail during
numeric reasoning and reuse. The single extra complete PASS does not establish a
reliability rate, a causal improvement or a successful repair of the full contract.
All ten Read-only helper assignments are evidenced; no general host or model
behavior guarantee follows.

[verified] The combined verbatim review hashes are
`a921c58e4cca8d85195b99187c1b58ac8c0dce6283b656a970e8f2c9f664ed2d`
for Markdown and
`aa545de26ef77ebe5e89a06c65727c4825f602fbc2a068874973c6f9dffc180d`
for JSON. The four individual group review files have separate seals. No proposal
or historical mechanical result was regraded.

**Disposition: this approved one-candidate loop is complete, and the revised
candidate does not satisfy the full frozen criteria.** RELIABILITY-001 stays open;
the source remains an unaccepted, uncommitted local candidate. The previous plugin
is preserved separately. No automatic tuning, extra trial, publication or lane
promotion follows from the unused USD 15.539319. Human acceptance of exact source
remains separate from evaluation. The full suite remains FAIL with eleven failures.

Further repair must address the numerical reasoning itself: keep elapsed/occupancy
bounds unknown without established enforcement, backoff and release inputs; do not
derive an attempt-count ceiling from a maximum duration; and retain supplied
overall scope and tested coverage. Merely retaining three/four-call wording did
not make those later inferences reliable. Any further candidate and measurement
loop need an explicit scope; no next metered loop is scheduled here.

[verified] New raw evidence is retained at
`F:/repos/sre-agents/.eval-runs/reliability-count-20261113/`: frozen source patch,
case/selection/runtime and budget bindings, qualification disposition, all ten
operator logs and native trial folders, `execution-closeout.json`,
`blind-bindings.json`, four `sealed-review-*` originals, combined
`sealed-blind-review.md/json`, `blind-group-review-seals.json`, and
`blind-review-seal.json`. The blind packet is
`F:/repos/sre-agents/.eval-runs/reliability-count-blind-20261113/`. The repair
worktree's ignored `.eval-runs/reliability-count-20261113/` retains the plan,
prior-plugin snapshot/binding, reviewed operator/source, focused proxy log/XML,
additional-failure impact review and preflight controls. The
[live backlog](../fleet-roadmap.md#reliability-001--preserve-retry-count-uncertainty-and-qualify-the-native-assessment)
owns remaining work.
