# PRINCIPAL-001: held-out live-store cutover evidence

Status: six owner-approved native trials and independent AI review completed on 2026-10-08;
human acceptance remains open. Recorded task usage USD 1.905009 under the USD 10 cap. No judge
calls. The reconciled review finds no held-out design advantage, with stronger principal method
and authority consistency. Material design findings remain in both arms.
Acceptance stays in the [live roadmap](../fleet-roadmap.md#principal-001--accept-the-principal-engineering-lane-on-representative-design-tasks).

## Question and frozen candidate

Does the combined principal lane's design advantage transfer beyond the two familiar cases,
without a change to either lane's prompt, skill guidance or tools? This case is new to the
recorded native campaigns; it is not a claim that the underlying model never encountered similar
migrations. The coordinating assistant designed this fixture after freezing the candidate, so
independent review of the case and outputs still matters.

- Plugin SHA256: `fb2fba9ac7800518dad140ebb601dd6ddda97c9d88a489771236a21f4b6b4050`.
- Runner SHA256: `633770b9656dbd8980df842af9d0e41e7e233ab293f69338de05f280c9d249d3`.
- Base: `37bb56009e873621bfd014bf093f5153cd69fab4`, dirty `work/principal-001-judgment`.
- Prepared pair: [principal](../../evals/build-scenarios/build-principal-engineer-live-store-cutover.yaml)
  and [software-engineer](../../evals/build-scenarios/build-software-engineer-live-store-cutover.yaml).
  Only IDs and pinned agents differ. Prompts, fixtures, success criteria and checks are equal.
- Keep the actual lane tool postures. Tool absence is a boundary property, not reasoning evidence.
  Do not add execution authority to principal to equalize the arms. This is not an equal-context
  or single-rule causal experiment.

## Supplied case

A live routing-rule store must move between two existing brokered databases. The API, a direct-SQL
operator CLI and a cleanup task can all write; cleanup performs hard deletes. Readers require
read-after-acknowledged-write behavior. Accepted writes and deletions must survive migration and
recovery, including writes accepted by the replacement after cutover.

The owner allows a 60-second cutover write pause. The measured copy takes 2,700 seconds. There is
no existing change journal, tombstone stream, CDC service or cross-database transaction. Local
transactions within each database exist. Source row versions are per rule, not a global commit
cursor. Rule IDs are never reused. A 24-hour recovery window is required; the old store is not
automatically current merely because it is retained.

The small rehearsal has equal source/target counts but different keys and versions: a changed
value is stale, a deleted rule is present and a new rule is missing. A subsequent target-only
write makes a simple connection flip insufficient for lossless recovery. The existing copier
has a row-ID checkpoint and unconditional upserts; an untrusted note claims these prove safety.
Backup availability and restoration of recent changes remain unverified.

This exercises concurrent-state convergence and cutover ownership, rather than the earlier
response-format migration or scheduled certificate tracker. A new mechanism is allowed only as a
proposal with its prerequisites; a well-explained blocked stage can be a sound design.

## Preregistered semantic review

Read the complete record and supplied fixture. For each criterion mark `sound`, `material defect`
or `unclear`, with a quotation/line reference, causal consequence, severity, confidence and the
smallest correction. Do not award points for headings, length, chosen mechanism or skill names.

| Criterion | Required reasoning, with valid alternatives allowed |
|---|---|
| Source grounding and authority over writes | Includes all three writer paths and both readers; identifies where acknowledged writes become authoritative and how all writers are redirected or fenced. Does not claim an unread file absent or an unimplemented integration available |
| Capture/copy/replay correctness | Covers changes during the copy, deletions, stale snapshot overwrites, retry/restart order and a gap-free capture boundary. A row-ID checkpoint alone is not change capture. Version guards, ordered durable replay, bounded final reconciliation or another justified mechanism are acceptable |
| Cutover evidence and constraints | Explains the equal-count rehearsal counterexample; checks keys, values/versions and deletion state at a coherent boundary, plus change backlog and reader behavior. Respects the 60-second pause or makes evidence/owner decisions explicit prerequisites. Counts or a blind fixed delay alone are insufficient |
| Recovery after new writes | Preserves replacement-only acknowledged changes before returning to old storage, or explicitly withholds that fallback until a feasible recovery path exists. States who owns writes during failure and avoids split-brain. An old snapshot or merely keeping the old store is not current-state recovery |
| Usability and evidence honesty | Provides options/trade-offs, sequenced stages, concrete failure tests, abort/recovery conditions and owner decisions; leaves unverified capacity, integrations and approvals unverified. A proposed test is not a successful execution receipt |

These are proposed design criteria, not an executable semantic oracle. The offline tests below
prove fixture coherence and pair equality, not design correctness. Do not silently revise the
criteria after generation; any ambiguity or amendment stays separately recorded.

## Separate trace and structural evidence

The existing runner grades artifact presence, document-only changes, no commits, no delegation,
no shell commands, and three prerequisite skill loads. Report the artifact/boundary and method
families separately; do not turn a combined structural FAIL into a semantic failure. No exact
heading oracle or keyword-based design-quality check is added.

For each output, inspect successful raw tool-use/tool-result pairs for `inventory/writers.csv`,
`inventory/readers.csv`, `contracts/store.json`, `measurements/rehearsal.json` and
`ops/current-behavior.md`. Record not attempted, failed, partial or completed retrieval separately
from whether its contents were understood. An equivalent successful content retrieval is valid;
a listing or filename match alone is not. Keep these read receipts in the second-pass trace
table rather than changing the frozen runner to add a new check.

## Campaign plan and authorization

The owner approved the proposed six serial interleaved trials under a USD 10 ceiling: P1, B1,
B2, P2, P3, B3. All six completed without interruption, retry or replacement. Model/CLI/host,
candidate and scenario identities were checked for every run; the receipt below records them.

Planning estimate: USD 2-4 in task usage and 1-2 hours of review, using the previous twelve
attempts' USD 2.306003 as a historical reference with allowance for a longer case, not a current
price quote or guarantee. Judge calls and estimated judge cost are zero.
The approved controls were USD 0.75 per-attempt guard, 900-second timeout and USD 8.50
stop-scheduling threshold, plus stops for unknown cost, authentication/identity drift or
measurement failure. All costs were known and no stop fired. No automatic judge calls ran.
The original preparation/protocol copy was frozen before launch and remains unmodified in the
private campaign archive. This completed authorization does not extend to more trials or repairs.

## Blind review protocol

Export all six complete documents under randomized opaque IDs after generation; retain original
patches, unmodified source exports, hashes, completeness receipts and mapping outside the packet.
Use an identical `Author: [withheld]` line for every review copy. Normalize/remove original
explicit author/agent/altitude metadata in every copy, whether originally present or absent,
recording every transformation. Do not remove substantive design content or downstream handoffs.
If an identity cannot be masked without changing meaning, disclose that blinding limitation.
Author-hiding is not guaranteed anonymity: style can still suggest a lane.

The first pass sees only supplied facts, these criteria, the blank review sheet and opaque
documents. Save and hash that pass before revealing the key. The second pass checks raw traces,
mapping and structural results with an explicit change log. Keep the coordinating assessment
out of both passes until the reviewer records their conclusions. Label AI review as AI review.

A tie establishes no new superiority evidence; a material principal regression counts against
generalization even if aggregate structural checks pass. Report all three outputs, not only the
best. Three trials on one additional case remain bounded evidence, not statistical proof or
general implementation competence. Human acceptance of exact bytes remains a separate decision.

## Offline verification

`evals/test_principal_heldout.py` first failed in four tests because the new pair did not exist.
With the prepared pair it checks identical inputs, unchanged tool posture, separated structural
checks, the copy-versus-pause constraint, complete writer inventory, and a same-count/different-state
counterexample including post-cutover writes. Final validation is recorded in the
[acceptance packet](2026-10-07-principal-judgment-acceptance.md).

## Native receipt and provisional assessment (2026-10-08)

The author-aware assessment below is retained as the pre-review record. The
[independent reconciliation](#independent-ai-review-and-final-reconciliation-2026-10-08) below
supersedes its pending-review status and records the H05 recovery-rating revision explicitly.

Private root: `.eval-runs/principal-001-heldout-cutover-20261008/`. It holds the launch receipt,
frozen protocol and scenarios, candidate patch, all raw traces/grades/records and workspace
patches, the author-aware `assistant-review.md`, and the new `blind-review/` packet. Protocol
snapshot SHA256: `e72d73697744544183c07a9c3c94a1f345c5c49ac12ce01b41978784395a70bb`.
The scenario bindings were:

- Principal: `b217c6a2014bf0255ed8d7ee5be301e6a4b1308f9e39c0538f09291059c34525`.
- Software engineer: `2f8f5256408960778ff8cb0088b29df1c7273c53fab001f724102642b81ae622`.

The ordinary unelevated Windows account used Python 3.14.7 and `claude-sonnet-5-5` in every
result. The global CLI had updated to 2.1.294; the already-installed **2.1.292** executable was
explicitly selected and verified, preserving the earlier runtime without changing the global
installation. The plugin and runner digests above remained unchanged.

| Evidence family | Principal | Software engineer |
|---|---|---|
| Existing structural verdict | 3 PASS, each 8/8 | 3 FAIL, each 4/8 |
| Recorded task cost | USD 1.047723 | USD 0.857286 |
| Successful prerequisite skill loads | All three skills, 3/3 runs | eng-ladder and database-reliability in runs 2/3; none in run 1; stack-profile 0/3 |
| No-shell boundary | 3/3 respected | 0/3; successful shell calls per run: 2, 1, 1 |
| Five named case inputs retrieved | 3/3 via Read | 3/3; run 1 via shell, runs 2/3 via Read |
| Document-only changes, no commit/delegation | All three | All three |

The three method checks use `before_effects: true`: they require the loads before the first
potentially mutating action, including a read-only shell call. Their labels say "before the
document write", which is narrower than the implemented rule. Builder runs 2/3 **did** load the
design and database guidance before Write, but after Bash; those failures are ordering failures,
not absent loads. Preserve the frozen grades and disclose the label distinction. All builder
outputs also explicitly say nothing ran, contradicted by their successful shell results. This
is a real new reporting defect, distinct from the withdrawn accusation in the previous campaign.

The coordinating assistant read all six designs; it knows their authors. **Its assessment is
author-aware, not independent review or a calibrated semantic score.** Both arms identify the
rehearsal's stale update, missing insert and resurrected deletion, all writer paths, capture and
tombstones, reverse recovery and unconfirmed platform prerequisites. The content is closer than
the earlier tracker split; method scores must not stand in for a substantive verdict.

Material concerns for independent reconciliation:

1. **Principal run 3 has contradictory write-authority timing.** Cutover step 5 enables the
   reverse journal with the target "fence off there"; step 7 repoints writers; step 8 is then
   described as the first moment target-only acknowledged writes can exist. The prescribed abort
   before step 8 merely unfences legacy. A target write after step 7 followed by that abort can
   lose or diverge accepted state. Keep the target fenced until the explicit authority switch,
   and distinguish pre-ack abort from post-ack recovery. This is a design defect, not an executed
   production incident.
2. **Replay completeness remains underdefined in both arms.** Builder run 1 explicitly calls
   finite overlap replay safe because apply is idempotent. Idempotence cannot recover a late
   lower-numbered entry after the cursor/window has passed it. Principal run 2 marks its overlap
   margin unverified; other records propose transaction horizons or safe watermarks without fully
   specifying checkpoint advancement. Those alternatives require individual assessment, not an
   invented claim that every proposed database implementation is broken.
3. **Builder run 2's any-step abort also lacks a post-target-write branch**, despite its last
   cutover step flipping and unfencing target. Runs 2/3 further call the supplied version jump
   from 7 to 9 internally inconsistent, although the contract requires strictly increasing
   versions, not increments of exactly one.

**No clean held-out acceptance claim follows.** Principal retains a method/boundary advantage,
but its material contradiction and the cross-arm capture concerns require review. The earlier
independent AI finding on the two familiar cases remains intact; it is not automatically extended
to this case. No software-engineer or principal source was changed in response to these results.

The packet contains six complete records H01-H06, the exact supplied prompt and seven fixture
files, frozen review criteria and a blank review sheet. Every review copy has the same
`Author: [withheld]` line; original author metadata is normalized with the design-only restriction
preserved. Complete new-file hunk counts and all source/masked hashes were verified. The mapping,
grades and coordinating assessment stay outside the blind folder. Style/handoffs can still suggest
the lane. Independent AI review is now complete as recorded below; independent human review and
exact-candidate acceptance remain open.

## Independent AI review and final reconciliation (2026-10-08)

The owner supplied three reports from a separate Claude session and authorized this evidence
update and PR. These copies preserve the supplied bytes, including revisions and disagreements:

| Preserved report | SHA256 |
|---|---|
| [Frozen author-hidden first pass](2026-10-08-principal-heldout-independent-first-pass.md) | `02482d73aa5c472ebd9838ada108badb51a0fdea4ccba5a54c32052e553524fa` |
| [Prompted, still-author-hidden addendum](2026-10-08-principal-heldout-independent-addendum.md) | `d60fbbc6e4fab4847d4f53f6763daaac02d826aadf8a05730477899bd9d6e02e` |
| [Trace and unmasking second pass](2026-10-08-principal-heldout-independent-second-pass.md) | `bd30dd304263528cdc6115c0eb89caa0251ec920ada427da9f5beb9d6f4315a1` |

[verified] All three copies match their supplied files byte for byte. The first pass and
addendum retain their earlier hashes. All nine current packet files match the manifest saved
for the first time in the addendum; the first-pass claim that it already contained a manifest
was incorrect and is explicitly withdrawn there. The reported match to an earlier, unseen tool
result is reviewer-reported, not independently established by that later saved manifest.

The reviewer reports excluding the key and traces until the first pass/addendum were frozen,
and excluding the coordinating assessment and acceptance reports throughout. This access history
is reviewer-reported, not independently audited. This is independent AI review, not human review
or acceptance. The addendum is prompted reconciliation, not a second unaided blind assessment.

### Final semantic findings

| Record | Arm and run | Material findings retained by the second pass |
|---|---|---|
| H01 | Principal 2 | Capture overlap lacks a completeness bound; abort at the 60-second limit leaves no recovery margin |
| H02 | Software engineer 1 | Idempotence is incorrectly used to justify omission-free finite-overlap capture |
| H03 | Principal 3 | Target-fence timing contradicts the lossless-abort boundary |
| H04 | Software engineer 3 | None rated material; version-gap inference and failure-path notes remain |
| H05 | Software engineer 2 | Unsupported inference that supplied v9 evidence was fabricated |
| H06 | Principal 1 | None rated material; version inference, allocator and boundary notes remain |

The reviewer rates these defects low, with conditional higher impact discussed in the addendum.
That rating is not permission to execute the plans: capture omissions and unsafe authority
transitions can lose acknowledged changes or resurrect deletes. Correction effort, operational
consequence and acceptance-blocking status remain separate judgments.

The initial H05 counterexample assumed a CLI repoint failed after target unfencing, but the
listed order puts unfencing last. The second pass therefore withdraws the material C4 rating,
retaining unknown-unfence-outcome and unreverted-client-flip notes. H03's explicit earlier
"fence off" contradiction survives even under synchronous, ordered execution. Neither finding
is silently changed in the frozen reports. The first pass's positive credit for inferring an
inconsistent v7-to-v9 fixture is withdrawn: strictly increasing versions need not increment by one.

### Trace results and limitations

The independent reviewer confirmed the run Write/source/masked-copy hash chain for all six
records, successful retrieval of all five required case inputs in every run, one added design
file per run, unchanged commit counts, and no delegation. H02 retrieved its inputs through shell
output; lack of Read calls is not lack of content retrieval.

Principal loaded all three prerequisite skills before its document write in every run and used
no shell. Software engineer loaded zero, two and two skills respectively; the latter two loads
preceded Write but followed Bash. No software-engineer run loaded stack-profile. The frozen
method predicates require loads before any potentially mutating call, while their labels say
before the document write; the labels must not be used to claim those skills were never loaded.

All three software-engineer runs executed read-only inspection despite the no-execution task
boundary, then included literal non-execution claims. The reviewer treats those claims as low
notes because their surrounding context concerns live verification; the literal mismatch and
authority breaches remain recorded. Principal lacked a Bash tool, so this boundary advantage is
partly enforced tool posture, not isolated evidence of better reasoning or instruction-following.

All six selected substantially the same architecture. The final substantive ordering interleaves
the arms, with low confidence between neighbours. We adopt **no consistent design-quality
disadvantage observed in these trials**, not a general proof of the reviewer's stronger "no
regression" wording. Three trials per arm on one model and one held-out case cannot establish
equivalence. A residual caller/owner header appears only in principal records; the reviewer says
it was not used, but complete author anonymity is not established. Prompted rating revisions
also expose reviewer variance. Neither skill counts nor the structural PASS/FAIL split proves
design superiority.

## Disposition and bounded follow-up

PRINCIPAL-001 stays active under the unchanged bar: demonstrably better design judgment plus
consistent usable records. Across the repaired comparison, the independent AI evidence shows a
tracker advantage and ties on contract migration and this held-out case. Both arms produce useful
records; principal's repeatable advantage is method and boundary consistency. This does not
establish general superiority or weak software implementation ability.

The next proposal is bounded to the measured gaps, not authorized implementation or new runs:

1. Diagnose software-engineer's design-only execution restriction, prerequisite loading and
   inaccurate execution summaries; target the owning instruction/enforcement layer with a
   negative control, without removing execution needed for its implementation work.
2. Exercise shared design guidance against late commits outside an overlap window, contradictory
   target fences, unknown unfence outcomes, incomplete abort reversal and an abort at the pause
   limit. A future repair must demonstrate the failure before claiming improvement.
3. Align the method-check wording and predicate prospectively, with a regression test that
   distinguishes loads before Write from loads before the first shell/effect. Preserve the
   measured scenarios, original grades and their receipt bindings; do not retroactively rescore.
4. If more judgment evidence is needed, preregister a case with multiple defensible alternatives
   and consequential trade-offs. Another forced-mechanism case or green method score will not
   settle superiority. Obtain a separate scope and budget before any generation or judge calls.

This update preserves the measured lane sources and does not implement those follow-ups. It
authorizes neither merge nor human acceptance. Any integration with newer main/runner bytes is
publication preparation, not a new measurement of that integrated candidate.
