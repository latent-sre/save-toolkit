# Fleet evals

Find the relevant checks here, then use the existing runner for that kind of work.

| Layer | What it establishes | Entry point |
|---|---|---|
| Structural checks | Fleet wiring, assets, links, and generated adapters are well formed | `python scripts/gate_a.py` |
| Offline tests | Code, harness, grader, fixture, and oracle behavior under controlled inputs | `python scripts/local_tests.py` |
| Native evals | Agent behavior on explicit scenarios and a particular model/host | `python evals/build_probe.py` |
| Benchmark campaigns | Results under each adapter's admitted case and execution profile | [Campaign guides](docs/running.md#run-it) |

Passing an offline test does not establish live model performance. Human acceptance of the exact
candidate remains separate. [CONTRIBUTING](../CONTRIBUTING.md#3-verify-in-proportion-to-the-change)
owns the required verification policy; named suites are focused checks within it.

## Find and run checks

Use the verified project interpreter (`python` below), from the repository root.

```bash
python evals/catalog.py suites
python evals/catalog.py show --suite python-craft
python evals/catalog.py list --component skill:python-craft
python evals/catalog.py list --profile incident-v1
python evals/catalog.py tests --suite python-craft --json
python evals/catalog.py campaigns
python evals/catalog.py tracks
python evals/catalog.py coverage
python evals/catalog.py check

python scripts/local_tests.py --suite python-craft
python scripts/local_tests.py --suite readonly-guard -n 0
python scripts/local_tests.py                 # default suite
python scripts/local_tests.py --heavy         # default plus heavy; choose one final run
python evals/build_probe.py validate          # offline scenario validation
```

Named suites cover every current native case and root test file, grouped by capability and execution
track. `show` lists exact membership and guides. `tests` lists files without importing them;
it does not claim a collected test count. `coverage` exposes any newly unassigned cases/files and
shows declared kinds and graders. The [capability map](docs/coverage.md) explains coverage limits
and useful additional evaluations. Repeat `--suite` to combine groups without repeating work. `-k` and other pytest
filters remain available and are recorded as filtered runs. Receipts also record effective pytest
collection settings and inherited collection overrides, so a narrowed run is visible.

`tracks` distinguishes existing runners/adapters from inactive proposals, planned integrations, and
independent sandboxes. It does not activate them. `campaigns` links actual selection manifests;
a runner with no selection is still discoverable through `tracks`.

Native discovery supports `--kind`, `--component`, `--profile`, and `--suite`: repeated values within
one filter are OR, different filters are AND. A component is the pinned agent/skill or routing target,
including negative routing targets. It does not imply coverage of every indirectly loaded skill.
Conversation profile is separate from runner kind. Use named suites for cross-cutting workflows.

## Change the evals

CI runs no `evals/` tests, so local runs are the only evidence for an eval change; quote them in
the pull request. Live evals run from `evals/build_probe.py` in a manual clean room. Raw traces and
the batch summary stay private under `.eval-runs/`; quote the numbers you rely on into the PR or
review that uses them.

| Change | Evidence |
|---|---|
| Scenario data, prompt, target, or expected result | `python evals/build_probe.py validate` and the matching scenario/grader contract tests; execute changed fixture code or check commands through their affected behavioral tests |
| Eval harness, grader, or runner | The affected `evals/test_*.py`; `python -m ruff check`, `python -m ruff format --check` and `python -m mypy` for a change to the runner (`evals/build_probe.py`, `evals/probe/`), `evals/compare_runs.py`, `evals/graders.py`, `evals/inspect_pilot.py` or an `evals/test_*.py`; `python evals/judge.py --calibrate` after a rubric edit |
| Judge, clean room or oracle Python | The affected behavioral tests and `python -m ruff check --isolated --select E9,F63,F7,F82 evals/judge.py evals/clean_room.py evals/oracles`; preserve byte-bound formatting and incremental typing unless a broader migration has a measured benefit |

- **Heavy suite:** the default run skips the `HEAVY` files listed in `conftest.py`. Run
  `scripts/local_tests.py --heavy` in place of the default run when changing the evaluator, oracle,
  grader, runner, shared eval fixtures/helpers, or heavy-test selection, and on the exact candidate
  before an eval campaign's first trial. A scenario-only change needs its affected heavy file when
  relevant, not every heavy file.
- **Suites:** add new root tests and native scenarios to capability suites in the same change, and
  run `python evals/catalog.py check` when changing suite membership or the track index.
- **Scenarios and runner:** every active scenario declares `max_turns`, and runner edits retain a
  saved-run `rescore`/`diff` comparison explaining every changed verdict (see
  [running](docs/running.md) and [internals](docs/internals.md)). Oracle changes also exercise the
  supervised completion path, including candidate failure and early exit, unavailable measurement,
  and oracle crash.
- **Accounts:** the suite must also pass under an elevated account. Tests that bind a runtime to
  the host use `probe_testkit.unelevated_host` to retain the real hostname and model an ordinary
  account.
- **Vitest UI calibrations:** pass `--dist loadfile` so each module's matrix runs once.

Behavioral campaign plans include Sonnet, Sol, Luna and Terra coverage. Start with the
[four-model testing block](../docs/fleet-evaluation/multi-model-testing.md) to check the supported
paths, then name the exact models, cases and limits for the campaign. Record unsupported profile
coverage explicitly; a structured Codex artifact result does not establish native routing, hooks or
helper continuation. Keep model and host results separate. This coverage requirement does not
authorize automatic model calls, extra trials or spend beyond the owner's campaign budget.

The eval dependency pins each live in one file: the `swt` group's exact pins, which
`evals/swt_adapter/verifier.py` reads; Harbor's version and wheel hash in `uv.lock`, which
`evals/harbor_adapter/contracts.py` reads; and each sandbox image's `requirements.txt`, which that
sandbox's validators, probe and tests read. A test checks the package set, that each pin is exact,
and that the installed or reported version matches the one source, so a version bump is one edit.
The `swebench` group installs on top of the project environment
(`uv sync --locked --group swebench`); `harbor` and `swt` are declared conflicting with it and
install only into a separate environment, for example
`UV_PROJECT_ENVIRONMENT=.eval-runs/harbor-sdk uv sync --locked --only-group harbor`.

## Freeze a native selection

Organize cases first. After definitions are finalized, export exact case fingerprints and trial slots:

```bash
python evals/catalog.py select --suite python-craft --trials 3 \
  --out .eval-runs/python-craft-next/selection.json
python evals/build_probe.py validate --selection .eval-runs/python-craft-next/selection.json
```

Export never launches a model or grants run approval. External benchmark selections stay with their
own adapters; native export refuses a suite containing linked external campaigns. A selection file
is never overwritten. Existing results retain their original identities.

For an authorized campaign, `build_probe.py run --selection PATH` uses the frozen cases and total
trial count with the usual model, label, plugin, calibration, and budget options. Use `--run-offset O`
and optionally `--trials K` to run slots `O+1..O+K` within the frozen total; omitting K runs the remaining
slots. The runner retains exact selection bytes under `OUT/selections/` before scheduling. Changed
case definitions are refused. [Running guide](docs/running.md) covers execution requirements.

```bash
python evals/campaign_report.py .eval-runs/python-craft-next \
  --selection .eval-runs/python-craft-next/selection.json --label candidate
```

The report keeps missing slots visible. Its logical JSON hash is distinct from the retained file's
`selection_file_sha256`. [Campaign reporting](../docs/fleet-evaluation/campaign-report.md) explains
costs, attempts, and interpretation. [Suite authoring](docs/authoring.md#suite-authoring) explains
membership and the JSON interfaces.

The opt-in [WP04 observable index](docs/itbench-observation-index.md) preserves raw inputs and
introduces a separately identified derived-evidence profile. Preparation is offline.
The [versioned review contract](incident-conversations/review-v2/README.md) separates historical
labels from source-bound reassessment. [Evidence isolation diagnostics](evidence-isolation/v1/README.md)
separate exact retrieval from interpretation; their controls and live run plan remain unaccepted.

## Reference guides

| Guide | Use it for |
|---|---|
| [Running](docs/running.md) | Setup, supported hosts, execution, and model-specific limits |
| [Authoring](docs/authoring.md) | Scenarios, suites, graders, oracles, and calibration |
| [Internals](docs/internals.md) | Runner structure, provenance, clean-room boundaries, regrade/rescore |
| [Case guides](docs/case-guides.md) | Case-family explanations and offline controls |
| [Capability coverage](docs/coverage.md) | Current suite/track map, limitations, and useful missing evaluations |
| [Evaluation specification](../docs/fleet-evaluation/README.md) | Architecture, campaign plans, and accepted constraints |

## Run it

See [Run it](docs/running.md#run-it).

## Muse runner (separate baseline, never comparable)

See [Muse runner (separate baseline, never comparable)](docs/running.md#muse-runner-separate-baseline-never-comparable).

## Runner layout

See [Runner layout](docs/internals.md#runner-layout).

## Inspect AI + Inspect SWE pilot

See [Inspect AI + Inspect SWE pilot](docs/running.md#inspect-ai--inspect-swe-pilot).

## Scenario contract

See [Scenario contract](docs/authoring.md#scenario-contract).

### Native incident conversation

See [Native incident conversation](docs/authoring.md#native-incident-conversation).

## The rubric judge

See [The rubric judge](docs/authoring.md#the-rubric-judge).

## Provenance

See [Provenance](docs/internals.md#provenance).

## Clean-room boundary

See [Clean-room boundary](docs/internals.md#clean-room-boundary).

## Tests

See [Tests](docs/case-guides.md#tests).

## WP-10 offline adversarial preparation

See [WP-10 offline adversarial preparation](docs/case-guides.md#wp-10-offline-adversarial-preparation).

## WP-12 offline GCP pilot

See [WP-12 offline GCP pilot](docs/case-guides.md#wp-12-offline-gcp-pilot).
