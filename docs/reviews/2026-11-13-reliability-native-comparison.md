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
