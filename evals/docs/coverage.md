# Evaluation coverage and useful next experiments

The catalog now groups the current native cases and repository test files by the capability being
checked. It also indexes the other runners, benchmark adapters, independent sandboxes, and inactive
or planned tracks. Use it to choose work and identify gaps; membership is not a score for agent quality.

```bash
python evals/catalog.py coverage
python evals/catalog.py coverage --json
python evals/catalog.py tracks
python evals/catalog.py tracks --suite itbench
python evals/catalog.py show --suite gcp-investigation
python evals/catalog.py campaigns
```

[verified] The inventory contains 409 native scenarios, 149 root-suite Python test
files, 35 suites, and 23 track records. Every current native scenario and root test file belongs to
at least one named suite. Suites overlap intentionally; their counts must not be added to estimate
independent coverage. The live `coverage` output derives counts and lists unassigned IDs/files if
new material has not yet been grouped. Component tests require the committed inventory to remain
assigned, without introducing a catch-all suite that silently absorbs new cases.

## What each layer proves

| Layer | Evidence it can provide | Limit |
|---|---|---|
| Structural and offline tests | Actual execution of validators, guards, adapters, fixture programs, graders and known good/bad controls | A green result does not show how a model answers the scenario |
| Native routing and contract cases | Whether the expected component is invoked or stays out; declared text/structure/rubric judgments | A contract answer alone does not establish an operational effect |
| Native build cases | Declared artifact, trace and fixture-outcome checks | A mechanical pass can still require semantic review; oracle quality matters |
| Incident conversation profiles | Actual session continuity, then-visible evidence and branching contracts | Related profiles are not independent incidents; advice quality needs its own assessment |
| Benchmark adapters | Dataset-specific authoring and independent verification, under admitted profiles | External execution, native host parity and campaign acceptance remain separate |
| Track index | Where the code, guide and associated suites are | `present` means an implementation entrypoint exists, not that a campaign or model is accepted |

The JSON coverage view includes each suite's native kinds, primary components, declared check and
grader types, profiles, test-file count, track associations and guide links. These are source facts.
`declared_manual_review_cases` counts only an explicit conversation field; it cannot infer all cases
that need human review. For example, the [GCP guide](../oracles/gcp/README.md) and
[natural-injection guide](../oracles/natural-injection/README.md) impose additional semantic limits.

## Capability map

[verified] The suite files bind exact IDs and paths. The map below explains their intended use;
`show --suite NAME` is the authoritative membership list, and existing guides own acceptance limits.

| Capability or change | Useful suite | What is represented and what remains separate |
|---|---|---|
| Fleet structure, projections and authoring | `fleet-structure` | Frontmatter, assets, tool/delegation contracts, links and adapters; native behavior needs its own cases |
| Description changes and helper handoffs | `routing-and-handoffs` | All current routing cases plus caller/helper continuation boundaries; does not imply every host executes the same tools |
| Software-engineer work | `software-engineering` | Task scope, authoring, review and artifact controls across its current cases; independent adversarial and platform suites remain useful |
| Python implementation/refactoring | `python-craft` | Routing, closed-JSON judgments, streaming, library choice, resource lifetime, package/refactor and scope cases; the two judgment cases are not open-ended semantic assessments |
| Python engineering skill | `python-engineering` | Four native routing scenarios, offline skill/oracle controls, and [12 paired saved artifact cases](../../eval-runs/python-engineering/README.md); artifact checks, report checks and reference compliance are reported separately |
| Go implementation | `go-craft` | Existing routing and Go API fixture; much narrower than the Python case set |
| HTTP APIs | `api-craft` | Pagination, problem responses, writes, OpenAPI and independent negative controls |
| Application interfaces | `frontend-craft` | UI artifacts and page/console controls; rendering calibrations require their opt-in Node environments |
| Operator tools | `operator-tooling` | Safe requeue and log-tail tasks with CLI oracle controls |
| Durable event handling | `pager-webhook` | Signature, redelivery, durable effects, enrichment, and known failing mutants |
| System design and migration advice | `engineering-design` | Principal/incumbent pairs, held-out cutover and semantic-proposal controls; the proposal remains inactive |
| Reliability and toil decisions | `reliability-and-toil` | Control effectiveness, recovery evidence, duplicate effects, and toil economics; operational benefit requires measurement |
| Incident advice | `incident-investigation` | Board structure, evidence/authority boundaries and helper use; source interpretation and advice quality are distinct dimensions |
| Resumed or branching incidents | `incident-conversations` | Eighteen execution profiles over six incident families; held-out family and semantic-review rules still apply |
| Bounded operational investigation | `sre-investigation` | Lookup, unavailable evidence, read-only boundaries and partial results; installed MCP/browser paths remain host-specific |
| GCP diagnosis | `gcp-investigation` | Authored paired families and hardened variants, plus GCP routing; synthetic evidence does not prove live cloud effects |
| Logs, metrics and traces | `observability-analysis` | Query dialect and supplied-evidence reasoning, including missing or misleading observations |
| Telemetry collection and SDKs | `observability-pipeline` | Collector/configuration/correlation/naming reasoning; deployment and actual signal delivery need other evidence |
| Paging and service objectives | `observability-alerting` | Rule semantics, SLO/error-budget calculations and alert boundaries |
| Grafana workflows | `grafana` | Read/query/write controls, dashboard/version conflicts and visual-evidence boundaries; actual installed-host write proof is separate |
| PCF, database and edge triage | `platform-operations` | Mostly routing, stack facts and supplied-state controls; comparatively sparse task-outcome cases |
| Release, CI and production authority | `release-and-ci` | Approval validity, unknown outcomes, release boundaries and pipeline contracts; no production action is authorized |
| Operational records and service lifecycle | `operational-docs` | Runbooks, postmortems, cards, lifecycle state, imports and disposition controls |
| Evidence collection and independent review | `research-and-review` | Source grounding, missing/private evidence, scratch verification and reviewer boundaries |
| Untrusted instructions | `adversarial` | Benign/malicious repository/log/helper pairs and judge-input controls; free-form semantic interpretation retains review limits |
| Read-only enforcement | `readonly-guard` | Executable command/launcher/hook controls; not proof of containment on every host |
| Evaluator correctness and saved evidence | `eval-harness` | Harness, grades, identities, selections, accounting, rescoring and coordinated test-runner controls |

## Other evaluation tracks

[verified] `tracks` reads an explicit [track index](../tracks.json) without importing the listed
entrypoints, downloading datasets, or starting any runner. `present`, `proposal`, and `planned`
describe repository implementation only. Campaign selection and run authority remain in the linked
source artifacts; the index does not copy their approval state.

| Track | Existing work to use | Boundary |
|---|---|---|
| Native Claude | [Native guide](running.md), suites with native cases | Current host/model, calibration and run admission apply |
| Codex | `codex` suite and [structured adapter](../codex_probe.py) | Scoped artifact/query profiles; no claim of native routing/hooks/helper parity |
| Muse | `muse` suite and [runner guide](running.md#muse-runner-separate-baseline-never-comparable) | Separate baseline; unsupported evidence stays inconclusive |
| Inspect AI/SWE | `inspect` suite and [pilot guide](running.md#inspect-ai--inspect-swe-pilot) | Artifact-only word-frequency pilot, not full fleet acceptance |
| ITBench | `itbench` suite and [operator plan](../../docs/fleet-evaluation/wp04-operator-runplan.md) | Fixed evidence and source-bound cases, not live recovery |
| SWE-bench | `swebench` suite and [operator guide](../../docs/fleet-evaluation/wp08-operator.md) | External repository repair under its execution/admission contract |
| SWT | `swt` suite and [run plan](../../docs/fleet-evaluation/wp09-swt-run-plan.md) | Generated tests must discriminate buggy and repaired revisions |
| Harbor/Terminal-Bench | `harbor` suite and [run plan](../../docs/fleet-evaluation/wp09-terminal-runplan.md) | Selected tasks and independent verifier profiles, not unrestricted terminal authority |
| Four-model preparation | `multi-model` suite and [testing block](../../docs/fleet-evaluation/multi-model-testing.md) | Prepares commands and accounts for results; unsupported profile coverage remains explicit |
| Native judge and reporting | `eval-harness`/`adversarial`; [judge guide](authoring.md#the-rubric-judge) and [reporter](../../docs/fleet-evaluation/campaign-report.md) | Calibration, saved results and fresh model trials are different evidence |
| Graph and interoperability sandboxes | [Graph contract](../../sandbox/graph-sandbox/contract.md), [interop contract](../../sandbox/autogen-a2a-sandbox/contract.md) | Independent test trees/dependencies and controlled activation; excluded from root pytest by design |
| Principal semantic proposal | [Proposal and activation gate](../proposals/principal-judgment/README.md) | Four response-only cases and calibration material remain outside the active native corpus |
| Workflow-graph skill proposal | [Dormant proposal](../../sandbox/workflow-graph-engineering/SKILL.md) | Does not become an installed skill or a runnable eval through indexing |
| SREGym and AIOpsLab | [Existing integration specifications](../../docs/fleet-evaluation/integrations.md) | Planned lab integrations; no repository adapter is claimed |
| Coder Eval and presentation | [Coder experiment](../../docs/fleet-evaluation/coder-eval.md), [integration roles](../../docs/fleet-evaluation/integrations.md) | Deferred infrastructure choices, not additional authored task coverage |
| Judge comparison | [EVAL-015](../../docs/fleet-roadmap.md#eval-015--compare-library-judge-prompts-with-the-incumbent-judge) | Current roadmap narrows the experiment to incumbent/Inspect/Pydantic; older DeepEval references do not authorize a new judge family |
| Live GCP | [GCP evaluation track](../../docs/fleet-evaluation/gcp.md) | Separate planned live-cloud scope; the synthetic catalog is already available |

The `campaigns` view now links six existing selections: SWE-bench, ITBench, SWT, Terminal-Bench,
and the two four-model preparation manifests. Other runners need no invented selection file to be
discoverable through `tracks`. Historical private run bundles and every possible model/case
combination are not separate evaluation tracks.

## Useful additional evaluations

These are recommendations from local coverage evidence, not newly implemented cases or a second
backlog. The existing [fleet roadmap](../../docs/fleet-roadmap.md) owns prioritization and execution.
Several needs are gaps in execution or semantic assessment rather than a lack of authored cases.

| Priority and gap type | Useful next evaluation | Independent evidence of success | Existing evidence and owner path |
|---|---|---|---|
| First: sparse task coverage | Add small PCF/database/edge supplied-evidence investigations with paired counterexamples, unavailable observations, and an exact allowed diagnostic boundary | Correct diagnosis or justified uncertainty; the relevant observed fact distinguishes the pair; no invented access or unauthorized change | Only two primary routing cases each for PCF ops, database reliability and Akamai are currently present. Build on `platform-operations` and the operational host work in the roadmap |
| First: host execution gap | Exercise the installed Grafana/browser/MCP read path and the complete authorized write/unknown-outcome path on the actual supported host | Independently read back the stored version and actual observed/rendered state; denied permissions and unavailable tools produce bounded outcomes | [Case-guide limits](case-guides.md#tests), [EVAL-005](../../docs/fleet-roadmap.md#eval-005--the-observability-engineers-grafana-write-lands-and-only-that-write); source-level controls already exist |
| First: semantic assessment gap | Use the existing full-context design proposal and blind incident/GCP reviews to test plausible but wrong reasoning, valid alternatives and incomplete evidence | Human-labelled or accepted calibrated judgments discriminate good/bad/unavailable answers without grading prose style or merely requiring keywords | [Principal proposal](../proposals/principal-judgment/README.md), [measurement requirements](../../docs/fleet-evaluation/measurement.md), PRINCIPAL-001/EVAL-012; do not add a second keyword oracle |
| Next: adaptive investigation gap | Extend held-out branching work with ambiguous and failed observations, then score which next check reduces uncertainty and when to stop | Decision quality against frozen branches and then-visible evidence; no future-answer leakage; related variants stay in one partition | [BRANCH-001](../../docs/fleet-roadmap.md#branch-001--author-the-six-gcp-branching-investigations) already owns the GCP work; eighteen incident profiles are only six independent families |
| Next: transfer and test-usefulness evidence | Complete the existing admitted SWE/SWT/Terminal comparisons across diverse repositories and failure types before adding another benchmark | Independent repair/regression tests; generated tests fail for the intended bug and pass after repair; cleanup and measurement failures remain visible | Existing selections and verifier controls are registered above; EVAL-012 owns campaign decisions |
| Next: operational benefit gap | Measure recovery/toil recommendations against controlled outcomes and a separately held-out case with more than one defensible solution | Recovery preserves data/effects, and measured time or risk improves under the stated workload; explicit unknowns are retained | [Reliability cases](case-guides.md#tests) already cover judgment and authority. RELIABILITY-001 remains the decision path; a JSON answer alone does not establish benefit |

Keep additional experiments focused on these discriminating behaviors. More paraphrases of the
same case, another framework, or a larger total count would not by themselves close these gaps.

## Maintenance

Add new cases/tests to explicit capability suites in the same change. `catalog.py check` validates
references and track shape; `coverage` exposes missing assignments; the catalog tests check the
current repository's membership. No runtime glob populates a suite. An intentional inactive proposal
belongs in `tracks` with its guide and controls, not in the active native case list.

Do not add sandbox tests to root suites merely to raise the assigned-file count. Their separate
contracts and environments are already visible in `tracks`. Do not infer human acceptance from
`present`, a test count, a rubric declaration, or a model-generated PASS.
