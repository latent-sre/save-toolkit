# GRADER-005 closure — gate-shaped posture grader

> **Status:** `[verified closure]` The reusable `gate_posture` repair is merged, its paired fixtures
> are green, and the one approved native remeasurement is retained. The batch's routing failures
> remain with `ROUTE-004`; they are not rewritten as a grader defect or a passing fleet result.

## Exact identity

- Initial repair: `dcf7852f5bf58104bea2340576b5bec2b05d262e`.
- Follow-up hardening: `7c92c5acc03f73007f60b9966adb87d8830e680c`.
- Native candidate: `54f1c8d0ddbc17545f644fdd2568a36c8471454c`, clean plugin input digest
  `d397e22e2f354a653482cd5ef8698228411cd957702926e66f21be06075cdbbc`.
- Approval record: `82fb278436e76ce69beea0ad84a550dee3466765`, budget ID
  `grader-005-frontend-posture-2026-08-31`.
- Native batch: [`20260831T052440Z-c13a16f0`](2026-08-31-eval-20260831T052440Z-c13a16f0.md),
  Claude Code 2.1.251, resolved model `claude-sonnet-5`, nine fixed trials, 504.66 seconds, USD
  1.2770608. The candidate is an ancestor of current `origin/main`.

## Acceptance audit

| Requirement | Evidence | Disposition |
|---|---|---|
| Reject the two permissive controls and accept blocking forms | `gate_posture` relation-checks affirmative block, prohibition, and prerequisite forms while rejecting the retained permissive controls; paired and transfer fixtures remain in `evals/test_graders.py` | `[verified static]` |
| Avoid a bare negative-regex false red | The grader binds the gate action within the same clause and screens negated block/prohibition forms | `[verified static]` |
| Document a reusable gate-shaped grader | `evals/README.md` names `gate_posture` and its gate-contract fields | `[verified static]` |
| Remeasure all three affected scenarios on accepted bytes | The bounded native report binds the exact clean candidate, scenario/grader/profile digests, and three trials for every named scenario | `[verified]` |
| Stay within the fixed packet | The batch used the approved model/candidate and remained below both its 7,200-second and USD 4 ceilings; it ran once with no tuning or retry | `[verified]` |

## Why the aggregate FAIL does not keep GRADER-005 open

- `discovery-frontend-craft-blocks-mantine-tailwind` passed every trial.
- `discovery-frontend-craft-framework-evidence` missed one target invocation; its content checks
  passed in that trial. The approval packet requires routing and posture results to stay separate.
- Every `discovery-frontend-craft-render-is-not-verification` trial routed to `merge-gate` instead
  of `frontend-craft`. The posture grader accepted two affirmative gate replies and rejected the
  reply with no affirmative posture. That is discriminating behavior, not an oracle false pass.

The routing reliability is the pre-existing [`ROUTE-004`](../fleet-roadmap.md#route-004--the-three-frontend-craft-discovery-scenarios-route-unreliably-on-sonnet)
contract. No new prompt, description, threshold, split, or grader edit is authorized by this
closeout. Independent Terra review found no grader-repair finding and concluded GRADER-005 should
close once this record, the generated evidence, and the tracker disposition are committed.

## Disposition

GRADER-005 is complete. This closure does not promote a candidate, turn the aggregate batch green,
or close ROUTE-004. Raw traces remain private; the bounded evidence record is the durable result.

