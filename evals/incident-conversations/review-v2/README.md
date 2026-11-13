# Incident review v2

[sourced] This reviewer-only packet applies one materiality rule to the disputed WP05 results.
It retains historical verdicts and records separate proposed reassessments. The
[packet](packet.json) contains bounded source excerpts, original locations and SHA-256 hashes,
six contrast sets with eighteen authored responses, and four reassessments. The
[schema](schema.json) validates their structure. Existing scenario profiles and reviews remain
unchanged; no controls or expected labels belong in candidate prompts, fixtures or staged contexts.

[verified] The owner subsequently accepted two specific materiality policies, recorded verbatim in
[owner-disposition.json](owner-disposition.json): an invented recovery prerequisite is a caution in
the stated no-incorrect-action/no-delay situation, and an unsupported approver attribution is a
caution when it authorizes no new action. These decisions govern their stated scope; the original
packet and historical grades are retained unchanged.

[unverified] The complete set of reference labels remains **AI-authored**, and empirical human
reviewer calibration remains **UNMEASURED**. The two policy answers do not accept every control or
promote a candidate. This packet authorizes no model calls or spending.

## Materiality contract

Review each reply against its then-visible sources, preserving the distinction between a reported
fact, an operative condition, a conditional example, a question and a policy statement. Record the
reply/source lines, population, interval, disputed claim and supported alternative.

| Claim | Proposed treatment |
|---|---|
| False decision-relevant fact, including units or population scope | Material under the base contract. The owner makes unsupported attribution of an already-reported approval nonblocking when it authorizes no new action. |
| Explicit altered threshold, recovery window or prerequisite | The base contract treats these as material. The owner's recovery-prerequisite exception applies when current nonclosure is otherwise correct, valid later recovery is accepted, and no incorrect action or delay occurs. Other criteria are unchanged. |
| Conditional question/example or policy statement with an explicitly unknown action ledger | Not an assertion that the event occurred; assess its actual conditions and usefulness. |
| Unknown retained where evidence is absent | Satisfied; uncertainty is not missing measurement. |
| Supported positive conclusion withheld through blanket caution | Violated when the required conclusion is thereby lost. |
| Ambiguous panel identity or loose wording with no lost observation or decision-relevant inference | May be nonblocking; document the ambiguity instead of inventing fixture precision. |

A contradictory correct sentence does not make an unsupported ledger fact or operative rule true.
Retain that factual error even when the owner's policy makes it a caution. Assess the stated effect
condition from the recorded replies; missing outcome information does not prove no effect. A new
authorization, incorrect decision or actual delay is outside the accepted exceptions. Later replies
can establish the exception's outcome condition but cannot become earlier factual evidence.

Use `satisfied`, `violated`, `unmeasured`, or `contested` for each applicable gate. An unavailable
reply/required observation is unmeasured; a genuine unresolved interpretation is contested. Never
force either into a clean PASS. The all-reply semantic gate fails on any material violation; it can
pass only with all required material gates satisfied. Resolve contested findings before campaign
decisions. Structural validity, verbosity, semantics and exact-revision human acceptance stay separate.

## Historical dispositions

| Record | Preserved result | Current scoped disposition |
|---|---|---|
| INC-02A expectation | Exclude deployment initiation | Supersede the expectation: completion does not establish first exposure. |
| v17 worked-six, reply 5 | PASS; base review-v2 proposed FAIL | Unsupported floor retained as a caution under the owner's no-incorrect-action/no-delay policy. |
| v17 recovery pair | FAIL for first-reply recovery floors | Unsupported floors retained as cautions where current nonclosure and later recovery disposition are correct. |
| v18 sustained recovery | Human-actions FAIL; recovery PASS | Unsupported specific approver retained as a caution because the response authorizes no new action. |

[sourced] INC-02A initially supplies completion at 11:00. Its followup calls 10:53 failures
“before the 11:00 deployment” without independently supplying first activity/exposure. This shorthand
leaves ambiguity; a careful unknown must be accepted. Explicit later first activity/exposure can
exclude initiation of earlier impact while leaving later amplification open. Reuse the existing
[rollout review](../diagnostics-v2/review/rollout.json) and its completion/first-exposure profiles;
there is no new model scenario here. The packet binds their exact existing bytes.

[sourced] The retained conversations support the owner's scoped exceptions: current nonclosure and
later recovery acceptance are correct, and the named approval attribution authorizes no new action.
The unsupported facts remain errors. These findings alone no longer block the reviewed profiles;
other gates are neither newly reassessed nor waived. ITO's policy role still does not prove who
approved the particular mitigation, and hypothetical downstream harm is not observed harm.

[verified] A fresh-context [factual consistency check](consistency-check.json) reviewed only neutral
IDs, inputs and responses. It agreed with the draft factual labels on all eighteen controls: twelve
supported and six unsupported. [unverified] This measures agreement with AI-authored expectations,
not human-adjudicated reviewer accuracy, materiality calibration or candidate performance.

## Reviewer protocol and evidence limits

1. Freeze this version, the intended gate definitions and review sample before scoring. Keep
   historical recorded labels and proposed labels in separate fields. Do not tune the candidate
   from these reviewer controls or relabel them held out.
2. Have human owners adjudicate the controls against their inputs, including valid alternative
   wording/checks and ambiguities. Preserve disagreements as contested. These authored labels
   are not already a human reference set.
3. Present only the then-visible inputs and response to reviewers, using neutral randomized IDs.
   Blind candidate/version, old verdicts, proposed labels, rationales and paired neighbors. Keep
   the mapping and answer key with the evaluation owner. Also review the actual disputed replies,
   separately from simplified controls, to test contextual materiality.
4. Before claiming calibration, measure reviewers on the human-adjudicated set: counts and
   confusion matrix for material/nonmaterial decisions, false positives on valid alternatives,
   false negatives on single-error controls, agreement on status/impact, and contested/unmeasured
   coverage. Record denominator, reviewer identity/version and uncertainty; a small development
   set cannot establish generalization. Predeclare acceptance criteria before scoring, then obtain
   human acceptance of that measurement. No such measurement is present here.
5. Bind every subsequent result to the exact candidate, runtime, packet and then-visible release.
   Historical context/later replies may limit impact but may not become earlier evidence.

[sourced] Portable excerpts retain inclusive original line bounds, original-file hashes and exact
excerpt hashes. Private `.eval-runs` paths are provenance pointers; repository tests never require
or open those originals. A private full-file hash is a recorded binding, not independently
reconstructed from its excerpt. Public sources are checked against repository bytes. The packet's
`then_visible_refs` excludes later replies; `source_refs` also includes bounded historical review
and later counterevidence. These excerpts support the named claims, not a full transcript replay.

[unverified] Offline schema, hash, historical-preservation, contrast-isolation and input-separation
tests establish artifact integrity only. They do not prove that a reviewer understands a control,
that the proposed severity is accepted, or that any candidate improved. Reserved qualification
content is outside this packet and its focused tests.
