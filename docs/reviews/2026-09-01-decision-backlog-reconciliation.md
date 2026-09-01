# Decision-backlog reconciliation — routing and evaluator items

> **Status:** `[verified structural]` Read-only reconciliation on 2026-09-01. This packet updates
> planning evidence; it does not approve a model run, promote a candidate, consume a budget, or
> accept an owner disposition.

## Exact subject

- Repository revision: `5abe50193386b8d008c534a05835443a418cc197` (`main` and `origin/main`).
- Live items inspected: `ROUTE-003`, `ROUTE-004`, `GRADER-009`, `EVAL-004`, `EVAL-006`,
  `EVAL-007`, and `ROUTE-005`.
- Canonical backlog: `docs/fleet-roadmap.md` at the revision above.
- Local evidence branch: `work/incident-investigation-eval-evidence` at
  `c3fb733fb9c06b3163738275b238f4bee7126970`, clean, three commits ahead and 49 behind `main` at
  inspection time. Its measurements are branch evidence, not current-main promotion evidence.
- The separate `work/incident-investigation-review-fixes` worktree was dirty and was not changed.

## Findings

| Item | Verified finding | Planning consequence |
|---|---|---|
| `ROUTE-003` | Both approved v1 packets are consumed `INCONCLUSIVE`; no later gradeable run exists | Any new campaign is a new v2 design and approval, not reuse or migration of a consumed packet |
| `ROUTE-004` | Native Sonnet evidence on current-main-ancestor bytes measured target invocation at 3/3, 2/3, and 0/3; the 0/3 prompt is explicitly merge-readiness work owned by `merge-gate` | Disposition the three scenarios separately; do not widen `frontend-craft` to compete with `merge-gate` |
| `GRADER-009` | Both quoted false positives fail on the pre-repair evaluator and pass on current bytes; current negative/transfer fixtures remain green | The deterministic repair is proven offline; the owner decides offline closure versus a new four-cell v2 campaign |
| `EVAL-004` | Eight scenario files exist, but the retained profiles select five and two; both profiles are v1 | No fixed executable eight-scenario campaign exists; design the closure and v2 profiles before requesting approval |
| `EVAL-006` | The discovery fixture denies the inspection tools its prompt asks to use, so it measures the degraded advisory path | Align prompt, success criteria, and graders to that path or design a different instrument; do not tune the skill against an impossible task |
| `EVAL-007` | Current `main` rejects a nonempty `Next:` board field while the local branch's widened pattern accepts it; the branch's post-change model result remained 1/3 | This is another phrase-oracle example, not acceptance evidence; coordinate its structured contract and removal control with `EVAL-004` |
| `ROUTE-005` | The measured pair belongs to the router now named `investigation-depth`; the later human-facing `incident-investigation` skill is a different subject | Close or reject the original experiment on its own evidence; any accepted residual for the new skill receives a new ID |

## Profile-v2 boundary

Current `evals/execution_profiles.py` refuses every v1 profile when `require_approval=True`.
`GRADER-009`, `EVAL-004`, `ROUTE-003`, and the historical `ROUTE-005` packets are all v1. The
retained approval objects remain evidence of historical authorization; they cannot authorize a new
live call after the v2 contract landed. A new campaign must bind resolved-model identity, reasoning
effort, stop condition, and the frozen evaluator-suite digest in v2, then receive a fresh approval.

## Focused reproductions

Commands ran from the exact subject revision unless a named historical worktree is stated.

| Check | Result | What it establishes |
|---|---|---|
| `python evals/test_execution_profiles.py` | 17/17 pass | v1 remains readable and is rejected as live authority; v2 approval fields validate |
| `python evals/test_graders.py` | 1,470/1,470 pass | Current deterministic grader fixtures and transfer/negative controls pass |
| `python evals/run_evals.py --validate` | 145 scenarios; 65 regression; pass | Current scenario schema, targets, and grader configuration validate |
| `python scripts/check_plan_status.py` | pass | Existing mechanical roadmap status rules pass; semantic freshness is outside this check |
| `python scripts/check_evidence_refs.py` | pass | Existing durable evidence references resolve |
| Replay both `GRADER-009` accepted sentences on `2cdcbbbac3bc560076a1d0c648149173b6863602` and current `main` | both fail before; both pass now | Direct red-to-green proof for the two deterministic repairs |
| Grade one response containing mechanism, `Ruled out:`, and a nonempty `Next:` board field on current `main` and `work/incident-investigation-eval-evidence` | current `False`; branch `True` | The stranded branch changes a phrase oracle; it does not prove semantic next-check quality |

## Evidence limits and non-actions

- No Claude, Codex, provider, or other model call ran.
- No profile approval, cost budget, or consumed packet was reused.
- The local incident-evidence branch used legacy profile-less discovery runs; its durable summaries do
  not bind a current v2 approval or current evaluator bytes.
- The human-facing incident skill changed after the branch measurement, and later evaluator changes
  landed on `main`. Its full-contract results are therefore not current-candidate evidence.
- No branch was merged, rebased, pushed, or deleted. No historical evidence was rewritten.
