# Golden saved runs

One stub-driven attempt per result rule and per run ending, and three native conversations (a pass,
a resumed call under the wrong session, a follow-up cut short), kept exactly as the eval runner
published it, with the scenario it graded, the verdict view of its live grade and of a regrade of the
same directory, and the batch view: what the finished trial's result row tells the batch (why the
batch or the scenario stops, and whether the cost is known). `evals/golden_runs.py` writes them from the current runner and
`evals/test_golden_runs.py` proves the current runner still reproduces both views. They are the
behavioral oracle for the runner rewrite in `docs/decisions/2026-11-02-probe-runner-refactor.md`.

Trial-time paths are replaced with `/golden/workspace` and `/golden/checkout`, the judge CLI is
`/golden/claude`, and the trace summary's plugin root is cleared, so a regrade measures against this
checkout wherever it runs; a regrade gives a copy of the run this host's paths back first, since it
restages the served plugin image at the path the run recorded. A judged run is regraded under the judge its binding recorded, because a
live judge's identity is the host's; its `regrade_other_judge` view is what every other judge sees.
Timing, identities and cost are in the artifacts but not in the views.

Regenerate with `python evals/golden_runs.py write` only when a verdict is meant to change, and say
which view changed and why in the pull request.
