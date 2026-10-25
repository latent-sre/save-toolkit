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
filters remain available and are recorded as filtered runs.

`tracks` distinguishes existing runners/adapters from inactive proposals, planned integrations, and
independent sandboxes. It does not activate them. `campaigns` links actual selection manifests;
a runner with no selection is still discoverable through `tracks`.

Native discovery supports `--kind`, `--component`, `--profile`, and `--suite`: repeated values within
one filter are OR, different filters are AND. A component is the pinned agent/skill or routing target,
including negative routing targets. It does not imply coverage of every indirectly loaded skill.
Conversation profile is separate from runner kind. Use named suites for cross-cutting workflows.

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
