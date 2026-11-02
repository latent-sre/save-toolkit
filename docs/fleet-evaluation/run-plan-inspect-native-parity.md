# Run plan: Inspect orchestration against the native batch

Roadmap item: [EVAL-016](../fleet-roadmap.md#eval-016--prove-the-inspect-orchestration-matches-the-native-batch-then-decide-what-it-replaces).
Decision: [Inspect AI orchestrates the native runner](../decisions/2026-11-02-inspect-orchestrates-native-runner.md).

This plan compares `evals/inspect_fleet.py` with `build_probe.py run` on one frozen selection. The
two paths share the trial code, so the comparison is about what the orchestration changes: timing,
cost accounting, limits, and whether anything in Inspect's process model disturbs the clean room.
A matching result does not accept any candidate; it accepts the orchestration as equivalent.

## Prerequisites

- A host where `build_probe.py run` already works: Claude Code authenticated, the plugin root
  clean, an unelevated account, and the project environment from `uv sync --locked`.
- A current judge calibration (`python evals/judge.py --calibrate`) if the selection includes
  rubric-graded contracts; both arms must bind the same `identity.json`.
- A maintainer's budget approval. The native batch cap `--max-batch-usd` holds only the native arm;
  size the selection so the Inspect arm cannot exceed the budget without it.

## Steps

1. Freeze one selection of routing and contract scenarios from a named suite, one trial each:

   ```powershell
   python evals/catalog.py select --suite routing-and-handoffs --trials 1 --out .eval-runs/selections/inspect-parity.json
   ```

   `catalog.py select` refuses a suite that includes build probes or conversations only through the
   Inspect task's own admission; check the selected ids with `python evals/catalog.py show --suite <name>`.

2. Native arm, serially, as every accepted batch has run:

   ```powershell
   python evals/build_probe.py run --selection .eval-runs/selections/inspect-parity.json `
     --label native --model sonnet --timeout 900 --out .eval-runs/parity/native `
     --judge-calibration .eval-runs/judge-calibration/<timestamp>/identity.json
   ```

3. Inspect arm, one sample at a time, same model, timeout, CLI and judge binding, in a fresh
   iteration directory:

   ```powershell
   inspect eval evals/inspect_fleet.py@native_scenarios --model none --max-samples 1 `
     --log-dir .eval-runs/parity/inspect/logs `
     -T selection_file=.eval-runs/selections/inspect-parity.json -T label=inspect `
     -T claude_model=sonnet -T timeout=900 -T out=.eval-runs/parity/inspect `
     -T judge_calibration=.eval-runs/judge-calibration/<timestamp>/identity.json
   ```

4. Verdicts over the published runs, the same reader for both arms:

   ```powershell
   python evals/build_probe.py regrade .eval-runs/parity/native
   python evals/build_probe.py regrade .eval-runs/parity/inspect
   ```

5. Record, per scenario: both verdicts, both resolved models, per-trial seconds and known cost
   from each `summary-*.json`, and every INCONCLUSIVE reason. Record the Inspect log's sample
   errors, if any, and the native batch's stop reason, if any.

6. Optional second Inspect arm with `--max-samples 4` on the same selection, labelled
   `inspect-parallel`, to measure what concurrency changes on this host and account. Keep it
   separate; it is not part of the equivalence claim.

## Acceptance

The orchestration is equivalent when every scenario's `regrade` verdict is the same in both arms,
both arms resolved the same model, neither arm stopped early for a reason the other did not hit, and
no Inspect sample ended in error. Report differences in seconds and cost as observations; they do
not fail the comparison unless a trial timed out in one arm only.

File the comparison under `docs/reviews/` with the two iteration directories' summary files quoted,
then update EVAL-016. If equivalent, the follow-up decision names the replacement inventory. If not,
the `inspect-native` track is relabelled as scheduling only, or the task is withdrawn; the native
CLI is untouched either way.
