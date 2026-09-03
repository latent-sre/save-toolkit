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
| a canonical agent, skill, or command change | adapters regenerated (`python scripts/generate_platform_adapters.py --write`) and the projections committed |
| a newly asserted contract | one focused test red-then-green, plus the weight line from Gate A (`python scripts/check_weight.py`) |
| text added to an always-loaded file (an agent body, a `SKILL.md` core, or `AGENTS.md`) | the tools-off probe, or the failing trial that shows the model needed it |
| a scenario or build probe change under `evals/` | `python evals/build_probe.py --validate` green |

## Risk

<!-- Failure impact, detection, rollback, irreversible effects, and behavior changes for existing
installations. -->

## Deliberately not done

<!-- Shortcomings, deferrals, and rejected alternatives, each with its reason. -->
