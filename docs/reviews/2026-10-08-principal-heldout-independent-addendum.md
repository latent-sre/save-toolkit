# PRINCIPAL-001 held-out case: prompted reconciliation addendum to the first pass

**Independent AI review, not human review and not human acceptance.** Authors remain concealed. Inputs for this addendum: the three framing files and H01–H06 only. No mapping, grade, trace, earlier assessment or agent prompt opened. No edits to the packet, the repository or the frozen first-pass report; no evaluation run.

Frozen first pass: `heldout-cutover-first-pass-blind-assessment.md`, 23098 bytes, mtime 2026-10-08 18:11:53, sha256 `02482d73aa5c472ebd9838ada108badb51a0fdea4ccba5a54c32052e553524fa`. Unchanged by this addendum. Every rating change below is recorded here only.

Rule applied throughout: a counterexample is rejected only where the record itself states the mechanism that prevents it. Where a safeguard is missing, it is named as missing, not supplied.

## Correction to the previous reply

The reply that delivered the first pass said "The report also records sha256 for all nine packet files". That was false. The manifest existed only in a tool result that the user cannot see; the first-pass file contains no 64-hex string (checked with `grep -c -E '[0-9a-f]{64}'`, result 0). The manifest is saved for the first time in section 6 below, recomputed from the packet and identical to the values printed during the first-pass turn.

## 1. H03, lines 144–152: can a target write be acknowledged after step 7 and before step 8?

**Verdict: revised.** Criterion affected: C4 (return to old storage, split-brain) with C3 secondary (coherent boundary). First pass: sound on both. Now: **material defect, low**; medium if step 5 is executed as written.

Exact text:
- L144 "5. Enable reverse journal on the replacement (fence off there)."
- L146 "7. Repoint rules-api writes (runtime switch). Release operator-cli and cleanup-task on new credentials afterward."
- L147 "8. Unfence the replacement. **From this point the replacement holds acknowledged writes the legacy store does not …**"
- L150 "Abort rule: if any step before 8 has not finished by an owner-set deadline (for example 45 s), unfence legacy and stop."
- L134 "Abort before step 8 is lossless: unfence legacy; target has had no writes."
- L94 invariant 2: "the non-authoritative database rejects application writes at the database level (not by client convention)".
- L152 "none reaching the target before step 8. The DB-level fences enforce this".

Mechanism the record states against the counterexample: the replacement's database-level fence, on through step 7 (L94, L134, L147, L152). Under that mechanism a write repointed at step 7 is rejected by the replacement and never acknowledged, so the step-8 unfence is the point of no return and the L150 abort is lossless with respect to data.

Where the record contradicts it: L144 says the replacement's fence is off at step 5. Taken literally, the replacement accepts writes from step 5 on; after the step-7 runtime switch, `rules-api` commits and acknowledges on the replacement before step 8. The abort rule then "unfence[s] legacy and stop[s]": the acknowledged target writes are stranded (captured by the reverse journal enabled at step 5, but the abort rule does not drain it), and `rules-api` is still pointed at the replacement, so both stores accept writes. L134's "target has had no writes" is false on this path. The record never states, in stage 1 (L130 "install triggers (fence off). Install matching schema on replacement") or anywhere else, that the replacement's fence is set on before cutover; it is implied only by step 8 and the invariant.

Independent of the step-5 reading, the abort rule does not revert steps 6–7. After an abort at the 7–8 boundary with the fence on, `rules-api` keeps failing against a fenced replacement (write outage past the 60 s budget, no loss) and both readers read a non-authoritative store that goes stale as soon as legacy resumes (a read-after-acknowledged-write breach for `routing-api`).

Reconciliation of sequence and invariant: they cannot both be true as written. The invariant and L152 require the fence on until step 8; L144 says it is off from step 5. The record's intent is clearly the invariant; the runbook text is what a release owner executes.

Additional assumptions needed for the abort to be lossless: (i) "(fence off there)" does not mean the replacement is unfenced; (ii) the abort also reverts the step 6–7 repoints. Neither is stated. Smallest correction (not supplied, named only): delete or correct the step-5 parenthetical and add "revert steps 6–7" to L150. Confidence: high that the contradiction exists; medium on severity.

## 2. H05, lines 152–159: does the abort rule cover a partial or unknown outcome of step 6?

**Verdict: revised.** Criterion affected: C4 with C3 secondary. First pass: sound on both. Now: **material defect, low**.

Exact text:
- L152 "Sequence, with the pause covering only steps 2–6"
- L157 "5. Enable the reverse journal on the target."
- L158 "6. Flip `routing-api`, `rule-audit` and `rules-api` to the target. Re-point the CLI and cleanup. Unfence on the target."
- L159 "**Abort rule.** If any step fails or the pause exceeds the owner-set threshold (D6, suggested well under 60 s), unfence legacy. Nothing has moved, so this is lossless."

Mechanism the record states against a target acknowledgement before the end of step 6: a fence on the target, implied solely by the final sub-action "Unfence on the target". The record never states that the target is fenced against writes during stages 3–5, what the fence is, or who holds it (L154 describes grant revocation for legacy only; L162 fences legacy during the window). If the sub-actions run in the listed order, no target write can be acknowledged before the last one, so "Nothing has moved" is true up to that point.

Where it fails: the abort rule is unscoped ("any step fails") and asserts "Nothing has moved" for all of step 6. It is false once the final sub-action has run: if the CLI or cleanup repoint fails after the unfence, or the unfence command's outcome is unknown, the record directs the operator to unfence legacy with target-acknowledged writes possibly present and `rules-api` already flipped. That is both stores accepting writes. The reverse journal (step 5) captures the stranded writes, but the abort rule does not drain it. The pause "covering only steps 2–6" ends with step 6, so the threshold branch of the abort rule can also fire after the unfence.

Boundary between safe abort and reverse-sync rollback: not defined. Stage 6 (L161–165) describes rollback for the 24 h window as "the same fence/drain/verify/flip run in the opposite direction", but nothing says when the L159 abort stops applying and that procedure takes over. H01 (L194 "Before the unfence … After: use stage 5 rollback"), H04 (L117, bounded to "if step 4 has not begun"), and H06 (L119 "Before (e) … After (f)") each state a boundary; H05 does not.

Partial completion: step 6 bundles four reversible flips with the point of no return. The abort does not revert the flips, so an abort before the unfence leaves readers and writers pointed at a fenced, non-authoritative target.

Additional assumptions needed: sub-actions execute strictly in the listed order; the abort is never invoked once the unfence has run or has an unknown result; the operator knows to switch to the stage-6 procedure. None is stated. Smallest correction (named only): split "Unfence on the target" into its own step, bound the abort to steps before it, and name the stage-6 procedure as the path after it. Confidence: high on the textual gap; medium on severity.

### Same standard applied to H01, H02, H04, H06 (abort boundary)

Applying the Q1/Q2 reading to the other four so the comparison is not skewed:

- **H01 L194.** Boundary defined: "Before the unfence: unfence legacy, nothing was acknowledged on the target. After: use stage 5 rollback." Writers are repointed before readers and hit the still-fenced target. Abort does not revert repoints (same low gap as above, not scored separately). Rating retained; the C3 material defect (abort threshold at 60 s) stands.
- **H02 L91.** Boundary defined at "(6) lift pause"; abort "nothing has been acknowledged by the target yet". Between (5) and (6) `rules-api` is held by an application gate (L68) and the two direct-SQL writers, rebound at (5), are protected only by convention (L69 operators told of the window; L70 cleanup schedule paused). No target-side fence is stated before (6); a "fence target" step appears only in the stage-6 rollback (L93). By H02's own L61 argument, convention is not a fence. **Low note, rating retained**: the abort claim is bounded to a defined step and the record names a control for each direct-SQL writer, so this sits below the H03/H05 defects, where the losslessness claim is contradicted or unbounded.
- **H04 L113–117.** Abort bounded to "if step 4 has not begun", which excludes partial step 4. Within step 4 the CLI and cleanup are flipped to the target before "lift gate" and no target fence is stated (the gate is `rules-api` only), and no procedure is given for a failure mid-step-4 (neither abort nor rollback). **Low note, rating retained**: no false losslessness claim is made for that window.
- **H06 L119.** Boundary explicit: "Before (e): lossless abort … After (f): roll back". Between (e) and (g) the target has not been released, so an abort is still lossless; H06's statement routes it to rollback, which is safe but imprecise (already noted in the first pass). What holds the target closed before (g) is implied by "release the target to writes" and the L116 authority flag, not a stated grant. **Low note, rating retained.**

## 3. H02, lines 54, 59 and 87–91: which final check catches a lower-sequence commit after the last clean full pass?

**Verdict: revised.** Criterion: C2. First pass: sound with a low note. Now: **material defect, low**; medium if the overlap variant is what gets built.

Exact text:
- L54 "The applier therefore must not advance its checkpoint past a possibly in-flight lower `seq` (use the transaction-visibility horizon of the journal reader, or re-read with an overlap window; both are safe because apply is idempotent)."
- L59 "record the journal `seq` position in the same transaction; … then replay the journal from that recorded position (overlap harmless)."
- L87 stage 3: row-level comparison, tombstone check, "N consecutive clean full passes".
- L89 stage 4: "the pause only checks 'journal position applied = last fenced position' plus a delta/sample check."
- L91 stage 5: "(2) wait for in-flight transactions to finish; (3) drain journal and confirm applied position = final legacy position and delta check clean".

Duplicate-safe versus omission-free: idempotent conditional apply makes re-applying an entry the cursor has already read harmless. It does nothing for an entry the cursor never reads. L54 attributes safety of both variants to idempotence; that is true of the horizon only by coincidence (the horizon is safe for a different reason) and false of the overlap window.

**Horizon alternative, assessed alone: sound.** The checkpoint cannot pass a row whose transaction may still be open, so the long-open transaction holds the horizon back and omission is impossible by construction. The cost is liveness: the applier stalls behind the oldest open transaction. At cutover, step (2) forces in-flight transactions to finish and the horizon reaches the journal head, so step (3)'s "applied position = final legacy position" is then a valid completeness check. The same reasoning repairs the L59 start position if that position is taken from the horizon rather than from the snapshot's visible `max(seq)`; the record does not say which.

**Overlap alternative, assessed alone: not omission-free, and no stated final check detects the omission before the flip.** Scenario: transaction T writes rule `r_x` (journal `seq` 100) and stays open; the cursor passes 100 plus the window; the last clean stage-3 full pass runs while T is still open, so legacy and target agree on `r_x` and the pass is clean; T commits after that pass; the cursor never revisits 100. At cutover: step (2) has nothing to wait for because T already committed; step (3) compares the cursor to the journal head, both far above 100, so "applied position = final legacy position" passes; the "delta/sample check" is unspecified at L89, and if the delta is identified by `seq` above the cursor at the last pass, 100 is excluded, while a sample is probabilistic. Nothing else is named before the flip. After the flip, stage 6's "periodic row-level comparison" (L93) can detect the difference, but only once the target is authoritative, with no repair rule stated, and possibly after a post-cutover target write has built on the stale value (the version guard will not distinguish two different values at the same version).

Consequence if the skipped entry is an update: a lost acknowledged update. If it is a delete: no tombstone on the target, the rule stays live, and it is served after cutover. That is resurrection, the requirement the whole design exists to prevent.

The record offers both variants as equivalent and bounds neither the window nor the maximum transaction age; `operator-cli` is a direct-SQL path that can hold a transaction open for as long as an operator leaves a session open. Additional assumption needed to make the overlap variant safe: window length exceeds the longest possible transaction. Not stated, and not enforceable for interactive sessions. Smallest correction (named only): strike the overlap alternative, or bound the window by the age of the oldest open transaction, which is the horizon by another name. Severity low because the sound variant is in the same sentence; confidence medium-high.

### Same standard applied to H01, H03, H04, H05, H06 (capture gap)

- **H01 L138–140, L175, L194.** Overlap margin only, with "[unverified] that the margin suffices, so it needs a concurrency test". Stated detection: "final reconciliation under the fence" (L175), which at L194 is "the bounded check of journal high-water plus every ID touched since the last full reconciliation". How touched IDs are identified is not stated; identified by `seq` above the last-reconciliation position, the check is blind to the skipped lower `seq`. A concurrency test can show a finite margin failing but cannot make it sufficient for unbounded sessions. **Revised: C2 sound → material defect, low.** The mechanism is the same as H02's overlap variant; H01 does not call it safe, which is credited under C5 and is why severity stays low, but candor about an unproven mechanism does not make the mechanism gap-free.
- **H03 L107, L178, L148.** Governing sentence: "must only advance past rows guaranteed committed (for example by a transaction-snapshot watermark)", which is the horizon. Then "or re-scan a trailing window; idempotent version-conditional apply makes re-scan safe", where idempotence is correctly scoped to re-scan (duplicate safety), not to omission. The window alternative is offered without a bound. Detection named: watermark, periodic reconcile, final drain under fence (L178), full post-cutover reconcile (L148). **Low note, rating retained**: the stated guarantee is the horizon and the unsafe claim H02 makes is not made. The distinction from H02 is the sentence "both are safe"; a second-pass reader who finds that distinction too fine should move H03 to the same mark as H02.
- **H04 L61** ("only read rows below the snapshot horizon … so it never skips a late-committing lower `seq`"), **H05 L84–85** ("safe horizon … never records a bare 'applied up to N' watermark"), **H06 L96** ("reads only rows whose `xid` is below the oldest in-flight transaction; apply is idempotent so overlapping re-reads are safe"). Horizon only; H06 scopes idempotence correctly to re-reads. **Upheld sound.**

## 4. H04 line 36 and H05 line 38: does v7 then v9 imply v8 existed on the target?

**No.** `contracts/store.json` `version_scope` is "strictly increasing for each existing rule; not a global commit position". Strictly increasing permits gaps. A target holding r17 at v7 that then accepts a write producing v9 is contract-compliant without v8 ever existing on the target. Additional assumption needed for any "inconsistency" claim: versions increment by exactly one. It appears in neither `contracts/store.json` nor `requirements.md`.

What the fixture demonstrates: the target's r17 was stale (v7) while the source held v8; the target then accepted a write on stale content (v9 north) while the source holds v8 west. That is the missed-source-update-then-divergence hazard and the rollback hazard; all six records draw it correctly.

What the fixture does not demonstrate: that it is internally inconsistent; that v8 "should" have been present on the target; that v9 was produced by an unrecorded catch-up or was fabricated.

Record by record, same standard:

- **H05 L38** "It implies the target held v8, but `target_after_copy` shows v7. The rehearsal is internally inconsistent. Either a catch-up step happened that is not recorded, or v9 was fabricated. It cannot be used as evidence of correct catch-up." The first sentence is false under the contract; the second is unsupported; the third accuses owner-supplied evidence of fabrication with no basis. The final sentence is correct. **Revised: C5 sound → material defect, low.** C5 is evidence honesty; a false factual claim about the supplied evidence, including a provenance accusation, is a defect in kind. Severity low because the design is unaffected; the realistic harm is Morgan discounting a legitimate negative result as bad data. Confidence high.
- **H04 L36** "The target value v9 on top of a copied v7 is also internally inconsistent (the version jumps 7 -> 9 with 8 never present), so the rehearsal doesn't model version continuity either." The inconsistency claim is unsupported for the same reason; the rehearsal neither models nor contradicts version continuity. No provenance claim. **Revised: C5 sound → sound with a low accuracy note.** The difference from H05 is the fabrication sentence; a reader who weighs the shared false inference alone should mark both the same.
- **H06 L48** "The target has no record of v8" (true); "a post-cutover write at v9 shows the version sequence was not continued from the true latest state" (unsupported, and if anything backwards: v9 is consistent with continuation from the true latest v8 as well as from v7); hedged by "Whatever produced v9" and "[verified fact; cause unverified]". **Low note, rating retained.**
- **H01 L164** "a post-cutover update continues from the copied version. This matches the rehearsal's r17 v9 write." Consistent with the contract (v9 > v7). **Upheld.**
- **H02 L31** uses v9 only as the rollback hazard. **Upheld.**
- **H03 L80** "Post-cutover write `r17 north v9` … on top of a stale base | The new store accepts writes on diverged data." Correct and no overreach. **Upheld.**

Correction to the first pass: section 3 listed "flags the rehearsal's r17 v7 to v9 jump" as a strength of H04, and section 4 listed "rehearsal version discontinuity (H04, H05, H06)" under edge cases caught. That credit is withdrawn for the inconsistency inference. What remains creditable is the design requirement that the target hold each rule's latest version before accepting writes (H06 L48, H04 L67, H03 L80).

## 5. Net effect on the frozen table and comparison

Changes recorded here, none applied to the frozen file:

| Record | First pass | After addendum |
|---|---|---|
| H01 | C3 MD-low; others sound | C2 **MD-low** (overlap margin, bounded final check blind to a skipped lower `seq`); C3 MD-low retained |
| H02 | all sound, C2 low note | C2 **MD-low** ("both are safe" conflates duplicate safety with omission-free capture; no pre-flip check detects the skip); C4 low note (direct-SQL writers protected by convention between (5) and (6)) |
| H03 | all sound | C4 **MD-low** (step 5 "fence off there" contradicts the no-target-writes-before-8 invariant; abort does not revert repoints); C2 low note (unbounded trailing-window alternative) |
| H04 | all sound | all sound; low notes on C5 (unsupported "internally inconsistent"), C3 (undefined mid-step-4 failure, "never reads first" wording) |
| H05 | all sound | C4 **MD-low** (abort rule unscoped over a step that includes the point of no return; no abort/rollback boundary); C5 **MD-low** ("fabricated") |
| H06 | all sound | all sound; low notes retained ((e)-(f) imprecision, L48 inference, no ID allocator) |

Comparison revised. First pass: H03 ≈ H06 ≈ H05 > H04 ≈ H02 > H01. Now: **H06 ≈ H04 > H02 ≈ H03 > H01 ≈ H05.** All defects remain low; the architecture is still equivalent across the six. The prompted questions exposed two areas the first pass under-scrutinized (the abort boundary at the flip, and the inference from a version gap) and one bias (crediting H03 and H05 for sophistication at the fence and in the rehearsal reading without pressing the runbook text). The second pass should treat the ordering as low-confidence between neighbours, as before.

## 6. Nine-file SHA-256 manifest (first time saved)

Recomputed 2026-10-08 from the packet; byte-identical to the values printed in the first-pass turn's tool output. Packet mtimes remain 2026-10-08 10:31:17.

```
0b5bf8feb334bb92c655d91e50024032669ce179e9cb1fd411e1f2440c03744f  case-facts.md
c315d98331a7b41546c3ee728d18a4951347b156185fbd048457d22abccf3145  preregistered-review.md
c2cd6cb14130ccdf3386a76336736a69aa97aae39824ed94835c0edc8929d002  review-sheet.md
c14c3a0169fb9c3015b7ece830b4db8997bbd16f92cebb6125f5d4c50a80a122  H01.md
ef22dbb0265ffef2d5e688a93486c20e39cc6e3832d5018483ce96095fd2fd1f  H02.md
011e7922d5d7f9f306cbfcc045bea03b2b3a327f3088088106fddc1e21df1168  H03.md
7c6b69bcaf3f4ecf7ebec8aa94789a2b80f9070aa0138ce4bd196b6e4736eda2  H04.md
159db341c80e98ad151a2906f6329eef3240129fe3e5bb48a7aeeae961f1c861  H05.md
9a33bf32d645af9897341ce59429ba79d2bec917c55d920c3e7a523fd1dba3e9  H06.md
```

End of addendum. Authors still concealed; no key, grade, trace or earlier assessment opened.
