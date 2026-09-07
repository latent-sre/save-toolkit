# Incident helper exchange

Date: 2026-09-07 UTC.
Status: implemented and independently source-reviewed; final local checks pass; behavior unrun.
Baseline: `a1d2246ca13062a46cebfba7f7b9635257cd06da`, plugin digest
`b81f345d45310584f6be63115de1187a7f5fe7ea758d58c477551424087f4b29`.

## Approved scope and evidence

The human selected item 1: improve incident decisions across advisor dispatch, helper evidence,
and parent reconciliation, not add more handoff headings. One candidate; no role, tool, graph,
description, invocation-policy, runtime or grader change. The other proposed service-context,
runbook/CI/job-example, record-applicability and frontend improvements remain out of scope.

The [second-pass report](2026-09-07-incident-quality-second-pass.md) records actual return and
parent continuation alongside missed advisor/reference selection, lost dispatch identities, and
unsupported causal/current-state claims. Those are historical observations on its named candidate,
not a fresh reproduction at this baseline. A body edit cannot repair a body that was never loaded.

Three source-review cases and acceptance were frozen before edits under the private
`.eval-runs/incident-exchange-20260907/` directory:

| Case | Required decision |
|---|---|
| Ordinary-looking helper overclaims from an untimed export | Retain the count and scoped observations; reject invented current state, chronology/cause, capacity exclusion and historical timestamp recovery; choose a feasible discriminating historical check |
| Matching pool counts, limit, waiters and acquisition waits | Accept scoped pressure without inventing its trigger, fleet-wide impact or approval; request evidence distinguishing what holds/uses connections |
| Direct numbers-only helper request | Return the requested sourced counts to the actual requester, keep absent operational ownership/current state unknown, and avoid a full incident investigation |

Cases SHA-256: `006e866551a308ca933e92e3fc887e3aa20b74c48a50a8c9e9a66543f6770a36`.
Acceptance SHA-256: `8a9ced6bfab260786a650b1f3f7eaea8694bcab5617dae07969de30a181aa1fc`.
Baseline manifest SHA-256: `8fd70041495a605acecd09b646445a87cf7ceea48c733949e0f0831765c8fd26`.

## Candidate

- Replaced redundant one-sided examples in `incident-investigation` with one fictional exchange:
  human question, scoped dispatch with caller and owner, returned observations plus unsupported
  claims, parent rejection of those claims, and a later supported pressure conclusion.
- Kept the example inline: no extra reference fetch or new packet/schema. Condensed nearby
  equivalent wording to stay within the existing corpus ceiling; this is not a measured output
  token saving. Unchanged rules retain time/source scope, false-negative limits, mitigation,
  recovery, blocked-check handling and human ownership.
- Documented the existing explicit advisor invocation as a README fallback. Automatic discovery
  stays enabled; a direct bounded helper ask remains distinct. This does not establish that the
  host selects or loads the advisor correctly.

The helper agent is unchanged. The parent owns reconciliation; a completed slice does not make its
interpretations true or complete the incident. No changes to copied runbook/CI assets or the separate
scheduled-job example are included in this slice.

## Verification and remaining gates

[verified] Before editing: matching local contracts passed, 51 tests and 201 subtests; all seven
context budgets passed. These checks establish structure, not the behavioral failure or its repair.

[sourced] Independent review caught one example gap: the parent rejected bad conclusions but left
the useful observations in the helper packet. The final parent reply now includes the counts, CPU,
update time and missing timestamps before the correction. Reopening found no material source
findings; the positive-pressure and direct-count controls remain covered by the instructions.

[verified] Fresh final-source run: `python -m pytest scripts evals -q` reported **465 passed,
5 skipped, 919 subtests passed**. Adapters regenerated and matched; Gate A passed 4/4 structural
steps; all seven context budgets and all three weight ceilings passed; `git diff --check` passed.
The unchanged scenario validator accepted 65 specs and 324 expectations. No tests, scenarios,
graders or validators were added or changed. Repository-aware checks preserve the supported
Claude frontmatter; the generic Codex validator's known `argument-hint` incompatibility was not
treated as a reason to change valid metadata.

The skill corpus is 575,993/576,000 bytes, up 105 bytes; agents stay at 113,990/115,000 bytes.
Initial drafts exceeded the ceiling and were compacted within the named skill before final review.
No ceiling was raised. The first full test run overlapped the parent-summary correction, so the
full suite was rerun on final bytes rather than attributing the earlier pass to them.

Final plugin SHA-256: `d713afa16e5816c1e56a9cab0eae6bf25e32dd92bbf3add10776c971b65fcb26`.
Reviewed skill SHA-256: `5326c99172a2168cb2d4bc6346152b0e769db1e4adcdcaaf78f84738404b7097`.
README SHA-256: `be29271c6fa9b1a8a73d3aea5c7cb4fe2b2ac17cf28185d718d256eff26def27`.
The unchanged helper hash, private source review and frozen candidate copies are retained alongside
the cases. This identifies uncommitted source changes over the baseline, not an accepted revision.

[unverified] No fresh model reproduction or before/after run. A separate question asks approval
for three matched Sonnet source-only pairs (six calls, at most $2 in summed CLI estimates, 180 seconds
per call, no tools/live access, retries or paid judges). No such call is authorized until the human
answers. This is a different decision from the earlier task-sized-output comparison; Terra stays
paused. No new runner was built.

Native selection, successful symptom-reference read, real dispatch identities, real helper return,
and parent continuation are separate acceptance checks, all unrun here. Written examples and
source-only comparisons cannot prove them. Existing behavioral adoption holds remain open; no
commit, push, merge, installation, production change or candidate promotion is included in this task.

## PR #236 review follow-up

The preceding sections bind the initial helper-exchange candidate. The human subsequently asked
to address Codex's five comments on `8b80eacc3296f7619a4a896c9e0dd91134f80f02`.

- Restart headroom: the exemplar has no serving-headroom check, so its restart branch now goes
  directly to the named engineering lead, with missing proof and a no-restart outcome. The short
  example, escalation and cleanup references agree; no fictional safety threshold was invented.
- Recovery versus confirmation: closeout, postmortem and scribe preserve the evidenced impact-end
  time separately from the human's resolution call. `resolved_at` remains the impact endpoint;
  `resolution_confirmed_at` is additive. Missing times remain unknown, not invented from the call.
- Unknown severity: the postmortem template supports YAML `null` for unknown/unassigned severity
  and unknown times. Known P1-P4 values remain supported. No local timestamp arithmetic or
  postmortem-schema consumer was found; external consumers were not inspected.
- Bounded mitigation stance: Result distinguishes `not assessed` with its reason, assessed with
  none supported, and a supported recommendation. A numbers-only ask still needs no full diagnosis
  or mitigation plan; it does not imply that mitigation was assessed.

The new parsed-template test failed against the incumbent for unknown severity/start/end values
and the absent confirmation field (four subtest failures), then passed after the fix. It proves
the shipped field/default shape, not model interpretation. Static acceptance examples keep 10:15
recovery separate from 10:30 confirmation, and leave recovery/duration unknown when only the call
is supplied. No new model campaign, paid judge or runtime mechanism is part of this review repair.

**Adoption remains on hold.** The P1 identifies a valid merge/adoption decision, not proof that
canonical paths on an unmerged candidate branch have already been promoted. CONTRIBUTING requires
canonical edits and generated projections, while normal installations track `main`; deliberate
checkout loading remains possible, so the branch is not an enforced quarantine. Do not infer
acceptance from review-ready status, green checks, commit/push permission or these four fixes.
The final exact-revision acceptance decision remains with the human; the P1 thread stays open.

Final review-repair verification: [verified] `python -m pytest scripts evals -q` reported
**466 passed, 5 skipped, 923 subtests passed**. Adapters match, Gate A passes 4/4, all context and
weight limits pass, and `git diff --check` is clean. Skill bytes are 575,921/576,000; agent bytes
114,243/115,000; no limits changed. [sourced] Independent static review found no material issue
in the four targeted fixes. Model/native behavior remains [unverified]. Final plugin digest:
`ed5f99592fac39992f57c3b69a6c0142669dbdb9aac859ecf6a3e1f7809bfcc0`.
