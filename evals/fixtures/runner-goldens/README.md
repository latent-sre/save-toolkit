# Golden saved runs

One stub-driven attempt per threat-model result rule and per run ending, kept exactly as the eval
runner published it, with the scenario it graded and the verdict view of its live grade and of a
regrade of the same directory. `evals/golden_runs.py` writes them from the current runner and
`evals/test_golden_runs.py` proves the current runner still reproduces both views. They are the
behavioral oracle for the runner rewrite in `docs/decisions/2026-11-02-probe-runner-refactor.md`.

Trial-time paths are replaced with `/golden/workspace` and `/golden/checkout`, and the trace summary's
plugin root is cleared, so a regrade measures against this checkout wherever it runs. Timing,
identities and cost are in the artifacts but not in the views.

Regenerate with `python evals/golden_runs.py write` only when a verdict is meant to change, and say
which view changed and why in the pull request.
