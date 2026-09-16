# Python craft on a medium-sized refactor — measured evidence

Date: 2026-09-16 · Branch `work/python-craft-medium-jobs` off main `8f4c11cf` · Claude Code
2.1.271 on the Windows host, `--model sonnet`, clean-room workspaces under `F:\iso-tmp` (outside
the home directory) · Incumbent plugin root: a detached worktree at `8f4c11cf`, source digest
`dc037244…e273`, `plugin_inputs_dirty: false`.

This record measures whether the fleet completes a medium-sized, multi-module Python refactor and
whether `python-craft` is reached while doing it. It does not accept a release or judge design
quality beyond the oracle's contract.

## The question

Every `python-craft` PR (#263, #266, #270, #272) recorded live effectiveness on substantial rewrites
as `[unverified]`. PR #270 made "medium-sized stages" verification checkpoints rather than limits,
but the six existing build probes are one-function, one-file fixtures, and the judgment scenario
asks the model to pick the label `coherent_stages`, not to do the work. Nothing measured a medium
job.

## The instrument

[`build-python-unify-policy`](../../evals/build-scenarios/build-python-unify-policy.yaml): seven
modules. Three intake entrypoints (`api.submit`, `cli.run`, `batch.load`) each embed the same order
policy and have drifted (the CLI still caps quantity at 99; batch does not strip the SKU), a
registry maps channel names to those callables, `client.py` resolves a configured dotted name from
`settings.json`, `legacy.py` re-exports names for independently released plugins, and a ten-test
unittest suite encodes the drift (`tests/test_cli.py` asserts that 100 is rejected). The task asks
for one owner in a new `policy.py`, every entrypoint routed through it and honoring a patch of
`policy.normalize_order`, consumers unchanged, both import orders working, staged work with the
suite green at each stage, and drifted tests updated rather than deleted.

The oracle mode `policy` in [`check_contracts.py`](../../evals/oracles/python-craft/check_contracts.py)
checks: specification parity for every entrypoint over a bounded domain (7 SKUs × 9 quantities ×
5 prices, plus the CLI's integer subset); single ownership through the patch seam, where a record
the old rules reject must pass once the shared policy accepts it; exception identity through every
entrypoint; input immutability and fresh result dicts; legacy, registry, and configured-lookup
identity; six fresh-process import orders; and the fixture suite green with at least its ten
original tests. Calibration in [`test_python_craft_oracle.py`](../../evals/test_python_craft_oracle.py):
the hand solution passes, the seed fails, the seed suite is green before the refactor, and eleven
named artifacts fail (drifted owner limit, owner without strip, rules kept before delegation,
copied rules, bound-name import defeating the seam, wrapped legacy name, replaced exception,
mutated input, circular import, stale drift test kept, drift test deleted). The oracle does not
grade how the work was staged.

Eval Python ceiling: 12,458 → 12,681 lines (+223) for the oracle mode and its calibration.

## Method

One arm per plugin root, three trials each, same scenario file, same runner process identity,
sequential trials, the `software-engineer` agent with `Read, Glob, Grep, Edit, Write, Bash, Skill`.
Trials whose resolved model identities or plugin digest do not match are INCONCLUSIVE, never a
verdict. Per the evals README, the model, trial count, and cost cap were agreed before the run.

## Batch 1: incumbent under the pre-fix evaluator (observations, not an aggregate)

Three Sonnet trials of main `8f4c11cf`, CLI 2.1.271. The runner closed the batch INCONCLUSIVE for
"mixed resolved model identities" because every trial's `modelUsage` listed
`claude-haiku-4-5-20251001` beside `claude-sonnet-5`. In each trace the session model and all
top-level assistant turns are Sonnet; the Haiku entry is one CLI helper call of 1,344 input and 14
output tokens ($0.0014). The per-trial gradings stand as observations under that evaluator:

| Trial | Oracle (work) | `python-craft` loaded | Suite runs | Turns | Seconds | Cost |
|---|---|---|---|---|---|---|
| 1 | pass | no | 7 | 31 | 176 | $0.52 |
| 2 | pass | no | 6 | 35 | 241 | $0.63 |
| 3 | pass | no | 7 | 37 | 207 | $0.50 |

Every trial completed the refactor correctly and unaided: read every module and test, ran the
suite for a green baseline, wrote `policy.py` with its own tests, then routed `api`, `batch`, and
`cli` one at a time with the suite after each, updated the drifted CLI test to the specification,
and added wiring tests for the legacy, registry, and configured consumers. The only failed check
was skill reach: `python-craft` appeared only in the engineer agent's on-demand catalogue, not in
its Process step 1 beside the other crafts.

## The evaluator fix (`6aa2c329`)

`build_probe.py` read every key of the CLI's usage table as an agent identity. It now resolves a
trial's identity from the main thread (the init model plus every top-level assistant turn, which
it already tracked as `main_models`) and records the usage table as `usage_models`. A parent that
changes model mid-trial still resolves to two identities; a dispatched subagent's model stays the
dispatch's; a trace with no main-thread turn falls back to the usage table. The judge's
`_resolved_model` already treated the same side call this way. Two parse tests pin the cases, the
three saved batch-1 traces re-parse to Sonnet alone, and the eval ceiling rose by the 36 lines
this earns. The Claude Code documentation names no way to suppress the helper call, only
`ANTHROPIC_DEFAULT_HAIKU_MODEL` to rename its model.

## The candidate (`0060f85c`)

Process step 1 of `software-engineer` names `python-craft` "for any Python you write, refactor, or
modernize, composed with the layer craft" beside the backend, frontend, and CLI crafts. Nothing in
the skill body changed: the batch-1 transcripts show Sonnet already staging and verifying well
without it, so guidance on staging would have been weight without a measured gap.

## Batch 2: both arms under the fixed evaluator

Launched in parallel at 07:28 under runner `6aa2c329`, CLI 2.1.271, Sonnet; every trial resolved
to `claude-sonnet-5` alone, zero INCONCLUSIVE. Incumbent: main `8f4c11cf` (digest `dc037244…`).
Candidate: `0060f85c` (digest `0f0ee6dd…`, unchanged by the later runner commit).

| Arm | Trial | Verdict | `python-craft` loaded | Oracle (work) | Suite runs | Turns | Seconds | Cost |
|---|---|---|---|---|---|---|---|---|
| incumbent | 1 | PASS | yes | pass | 7 | 39 | 176 | $0.57 |
| incumbent | 2 | FAIL | no | pass | 7 | 35 | 226 | $0.60 |
| incumbent | 3 | FAIL | no | pass | 5 | 29 | 174 | $0.47 |
| candidate | 1 | PASS | yes | pass | 6 | 38 | 188 | $0.60 |
| candidate | 2 | PASS | yes | pass | 7 | 36 | 177 | $0.53 |
| candidate | 3 | FAIL | no | pass | 7 | 33 | 203 | $0.50 |

Batch verdicts at the scenario's 1.0 threshold: incumbent FAIL (1/3), candidate FAIL (2/3). Every
failure is the skill-reach check; the work passed the oracle in all six trials.

## Batch 3: the description candidate (`3becb641`, digest `90464da6…`)

The batch-2 transcripts left the description as the one unmeasured reach lever: it opened with
"Improve difficult Python code", a gate a model can read as a reason to skip the skill on a clean,
well-specified task. The use-when now covers writing, refactoring, or modernizing any Python,
"routine or difficult", and says to load before editing; the quoted triggers and the not-for line
are unchanged (+19 bytes; always-loaded descriptions 16,660 of 17,000). Run after the change only,
per the description-eval rule; same runner `6aa2c329`, CLI 2.1.271, Sonnet, workspaces on `F:`.

| Trial | Verdict | `python-craft` loaded | Oracle (work) | Suite runs | Turns | Seconds | Cost |
|---|---|---|---|---|---|---|---|
| 1 | PASS | yes | pass | 9 | 43 | 195 | $0.58 |
| 2 | PASS | yes | pass | 8 | 43 | 248 | $0.64 |
| 3 | PASS | yes | pass | 7 | 38 | 224 | $0.61 |

Batch verdict PASS (3/3, 0 inconclusive). Reach across the round: 1/6 on main, 2/3 with the
step-1 edit alone, 3/3 with the description as well. The loaded trials ran 38–43 turns against
29–39 unaided, and $0.58–0.64 against $0.47–0.63; a small tax, inside the spread of nine trials.

Routing scenarios on the same candidate, three Sonnet trials each, after-only per the
description-eval rule (`iter-3/eval-discovery-python-*/desc-sonnet/`):

| Scenario | Expect | Verdict | Note |
|---|---|---|---|
| `discovery-python-refactoring` | fire | PASS 3/3 | |
| `discovery-python-improvement` | fire | PASS 3/3 | |
| `discovery-python-modernization` | fire | PASS 3/3 | runs 2–3 re-run after the copied OAuth token expired mid-batch (see below) |
| `discovery-python-explanation` | fire | FAIL 0/3 | attribution run on main `8f4c11cf`: FAIL 0/3, so pre-existing, not a regression |
| `discovery-python-defers-live-incident` | not fire | PASS 3/3 | the not-for line still holds |

The explanation prompt ("I'm learning Python. Explain what this function does…") is answered
directly in one turn on both descriptions; Sonnet does not reach for a skill to explain a
six-line generator. That scenario has been red on main since it was added schema-validated
in PR #270 and had no live result until now.

Seven trials of the first routing pass returned INCONCLUSIVE in about 1.3 s with zero tokens:
the clean room copies the host credential file per trial and a copy cannot refresh an expired
OAuth token (`Failed to authenticate: OAuth session expired and could not be refreshed`, model
`<synthetic>`). The affected slots were re-run under the same label, output directory, and
digest with `--overwrite`, with a one-word host call before each scenario to keep the copied
credential fresh.

## What the trials establish

- **Capability:** a medium-sized, multi-module Python refactor of this shape is completed correctly
  by Sonnet under `software-engineer` in 9/9 trials, with or without `python-craft`: one owner
  reached through every entrypoint, drift removed to the specification, consumers untouched, both
  import orders working, the drifted test updated rather than deleted. The claim that stages are
  checkpoints rather than limits is now measured on this fixture; it is not attributable to the
  skill body.
- **Skill reach moved with wording, not with the body:** `python-craft` self-loaded 1/6 on main,
  2/3 with the step-1 edit alone (Fisher exact p ≈ 0.23 against main, direction only), and 3/3
  once the description stopped gating on "difficult". Three trials per cell are small; 3/3 against
  1/6 is p ≈ 0.048 by the same test. Both levers are text the host shows the model before it
  decides, which matches the backend-craft and advisor-trigger findings on Sonnet reach.
- **No measurable effect of loading the skill on this job:** turns (33–39 loaded, 29–37 not), cost
  ($0.53–0.60 loaded, $0.47–0.63 not), and suite discipline (5–7 runs, one module per stage in
  seven of nine trials) do not move. Candidate trial 1, which read the refactoring reference, wrote
  all four modules before its first test run, the coarsest staging of the nine.

## Not established

- Behaviour on Opus, on the VS Code or Copilot hosts, or on a fixture larger than seven modules.
- Whether the staging table and the parity-test asset drafted for this round would change anything;
  they were not shipped because no trial showed the gap they address.
- Reach beyond three trials, on Opus, or on the six single-file Python probes. The scenario keeps
  its `skill_loaded` check and 1.0 threshold like its six siblings; 3/3 on one candidate is a
  first green, not a contract, and self-load remains a model propensity the fleet should keep
  treating as calibration.
- Cost or quality on the six existing single-file Python probes under the step-1 edit; they were
  not run.
