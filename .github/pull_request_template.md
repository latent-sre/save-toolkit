<!-- Use an imperative title that explains the change in a log. Delete an inapplicable section only
after stating why; never leave an empty heading. -->

## Summary

<!-- Two or three sentences: consequence, problem, and remedy. -->

## What changed, and why

<!-- One entry per meaningful change: decision, reason, and consequence. -->

## Reviewer briefing

<!-- Point attention without narrowing the independent review or pre-empting its verdict. Standing
review rules live in `.github/copilot-instructions.md`. -->

- **What a serious defect looks like in this change:**
- **Look hardest at:** <!-- files or invariants, not your diagnosis -->
- **Least sure about:**
- **Please still make an independent pass beyond the above and say what it found — including if that
  is nothing.**

## Verification

<!-- Paste commands and results. Label load-bearing claims `[verified]`, `[sourced]`, or
`[unverified]`. -->

- [ ] `python scripts/gate_a.py` — clean <!-- structural only; component tests and evals remain separate -->

**Conditional gates — fill only the rows this PR trips, and delete the rest:**

| If this PR touched… | It must show |
|---|---|
| executable implementation | the smallest focused test file(s) that exercise the changed owner; Gate A does not rerun them |
| a scenario under `evals/scenarios/` (added, edited, or retired) | `python evals/run_evals.py --validate` green — the offline schema/target/grader check; Gate A no longer runs it, so a malformed scenario otherwise reaches review unchecked |
| a routing-content `description:` edit — `Triggers:`, use-when/not-for, or a named alternative | the overlapping scenario(s) run after-change; run the previous-revision baseline only for a red scenario to determine whether the edit caused it. A fleet-failure-driven edit also trips the next row and therefore needs incumbent evidence even when the after-change run is green. Pure rewording needs no live eval. If deferred, say why and what remains unmeasured |
| `scripts/readonly-guard.py` or `hooks/hooks.json` | `python scripts/test_readonly_guard.py` and `python scripts/test_hook_wiring.py` green, plus the guard allow/deny corpus diff — and the 42 allow / 43 deny / 44 indeterminate exit-code contract left intact, since the hook tells this guard's answer from a stand-in interpreter by those codes |
| a newly asserted contract — a validator rule, an exit code, a schema constraint, or any predicate a test names, anywhere in the repo | one focused test that fails when that exact contract is deliberately broken and passes when restored. State the red command and failure reason, then the green command. A survivor inventory or evaluation packet is not a substitute |
| a fleet failure used to justify an agent or skill change | one named regression red on the incumbent, then incumbent/candidate results on identical cases and conditions. Missing or inconclusive candidate evidence and ties retain the incumbent; make one candidate by default and keep the evidence in this PR rather than a second ledger |
| any canonical agent or skill (`agents/`, `skills/`, `commands/`) | `python scripts/generate_platform_adapters.py --write` re-run and the projections committed; no generated root (`.github/agents/`, `platforms/copilot/skills/`) hand-edited |
| an added, renamed, or removed component | host adapters regenerated; the retired name must not linger in `agents/`, `skills/`, or `commands/` (`rg` for it) — plus `python evals/run_evals.py --validate` green, since a rename/remove can orphan a scenario target |
| the runbook frontmatter template, its schema, or its catalog entry (`skills/runbook/assets/runbook-template.md`, `schemas/runbook-frontmatter-v1.schema.json`, `schemas/catalog-v1.json`) | `python scripts/test_runbook_schema.py` green — the template/schema/catalog lockstep; it is not structural, so Gate A does not run it |
| anything users install | whether every host manifest and marketplace needs the same version or cache update |

## Risk

<!-- Failure impact, detection, rollback, irreversible effects, and behavior changes for existing
installations. -->

## Deliberately not done

<!-- Shortcomings, deferrals, and rejected alternatives, each with its reason. -->
