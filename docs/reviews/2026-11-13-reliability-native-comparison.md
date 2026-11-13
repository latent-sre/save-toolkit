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
  scheduling ceiling. Request at most USD 0.25 per invocation; this CLI request
  may overrun by a response and is not a hard provider billing ceiling. Stop
  further scheduling on authentication loss, unknown spend, incomplete instrument
  evidence, input/model drift, or insufficient remaining allowance. Preserve
  missing slots and actual failures.
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

## Execution ledger

- [verified] The active Python-skill checkout was left untouched; preparation uses
  an isolated managed worktree from the fresh-main revision above.
- [verified] Local Claude Code is `2.1.323`; its status reports a logged-in
  first-party Claude subscription. Status alone does not prove a live invocation
  will authenticate or resolve the pinned model.
- [unverified] Pair review, exact-candidate qualification, live results and blind
  semantic review are pending. No run has occurred at this checkpoint.
