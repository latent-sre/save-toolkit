# Incident review v2

[sourced] This reviewer-only packet applies one materiality rule to the disputed WP05 results.
It retains historical verdicts and records separate proposed reassessments. The
[packet](packet.json) contains bounded source excerpts, original locations and SHA-256 hashes,
six contrast sets with eighteen authored responses, and four reassessments. The
[schema](schema.json) validates their structure. Existing scenario profiles and reviews remain
unchanged; no controls or expected labels belong in candidate prompts, fixtures or staged contexts.

[unverified] All new judgments are **AI proposals**. Human acceptance of these exact labels and
empirical reviewer calibration are **UNMEASURED**. Authorization to prepare this repair did not
accept the labels. This packet authorizes no model calls, spending, candidate change or promotion.

## Materiality contract

Review each reply against its then-visible sources, preserving the distinction between a reported
fact, an operative condition, a conditional example, a question and a policy statement. Record the
reply/source lines, population, interval, disputed claim and supported alternative.

| Claim | Proposed treatment |
|---|---|
| False decision-relevant fact, including approval provenance, units or population scope | Material, even if the immediate recommendation is otherwise justified. |
| Explicit altered threshold, recovery window or prerequisite | Material, even with independent grounds for present nonclosure or a correct later reply. |
| Conditional question/example or policy statement with an explicitly unknown action ledger | Not an assertion that the event occurred; assess its actual conditions and usefulness. |
| Unknown retained where evidence is absent | Satisfied; uncertainty is not missing measurement. |
| Supported positive conclusion withheld through blanket caution | Violated when the required conclusion is thereby lost. |
| Ambiguous panel identity or loose wording with no lost observation or decision-relevant inference | May be nonblocking; document the ambiguity instead of inventing fixture precision. |

A contradictory correct sentence does not cancel an affirmative false ledger fact or an operative
rule elsewhere in that reply. A later correction is positive evidence and may limit consequences;
it does not erase an earlier material failure. Assess factual materiality separately from practical
impact. A hypothetical risk is not evidence that an operation or harm occurred.

Use `satisfied`, `violated`, `unmeasured`, or `contested` for each applicable gate. An unavailable
reply/required observation is unmeasured; a genuine unresolved interpretation is contested. Never
force either into a clean PASS. The all-reply semantic gate fails on any material violation; it can
pass only with all required material gates satisfied. Resolve contested findings before campaign
decisions. Structural validity, verbosity, semantics and exact-revision human acceptance stay separate.

## Historical dispositions

| Record | Preserved result | Proposed review-v2 disposition |
|---|---|---|
| INC-02A expectation | Exclude deployment initiation | Supersede the expectation: completion does not establish first exposure. |
| v17 worked-six, reply 5 | PASS; clock-floor caution nonblocking | FAIL for an unsupported operative recovery floor. |
| v17 recovery pair | FAIL for first-reply recovery floors | FAIL under the same rule. |
| v18 sustained recovery | Human-actions FAIL; recovery PASS | Keep factual approval-attribution FAIL, with medium scoped impact and no implied live action. |

[sourced] INC-02A initially supplies completion at 11:00. Its followup calls 10:53 failures
“before the 11:00 deployment” without independently supplying first activity/exposure. This shorthand
leaves ambiguity; a careful unknown must be accepted. Explicit later first activity/exposure can
exclude initiation of earlier impact while leaving later amplification open. Reuse the existing
[rollout review](../diagnostics-v2/review/rollout.json) and its completion/first-exposure profiles;
there is no new model scenario here. The packet binds their exact existing bytes.

[sourced] v17 worked-six already had queue impairment that justified nonclosure and later accepted
the valid receipt. Those facts limit consequence; they do not validate its added clock floor. For
v18, ITO's policy role is supplied, but “approved by ITO per report” falsely adds a particular
approver to the action history. A question about ITO with an unknown approver ledger is distinct.

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
