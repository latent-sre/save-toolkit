# Sources and current baseline

Initial evidence was gathered on 2026-10-03; Coder Eval research and its approved addition date to
2026-10-04. The planning worktree's runtime-source baseline remains
`207742d26fb78743d8af80c6fedbe3b6f1ddbca3`; another checkout was concurrently changing the clean-room
implementation, so this package uses a fixed baseline. Refresh source claims at implementation time.

## Repository observations

| Source | Bounded observation |
|---|---|
| [Fleet guide](../../AGENTS.md) and [contributing](../../CONTRIBUTING.md) | [verified] Canonical-source, authority, roadmap and manual native-evaluation rules are present |
| [Software-engineer effect authority](../../agents/software-engineer.md#effect-authority) | [verified] External-code execution is refused outside CI; a container is not a policy exception. DEC-13 and AC-25 address this integration constraint without changing the agent |
| [Native runner](../../evals/build_probe.py) | [verified] 3,799 lines at the planning baseline; separate grading/status/provenance and run artifact paths |
| [Eval documentation](../../evals/README.md) | [verified] Routing, contract, build and native paths; native conversation scope is narrower than general interaction |
| [Judge](../../evals/judge.py) | [verified] 901 lines; quote checking, model/execution binding, calibration and spend tracking |
| [Calibration corpus](../../evals/rubrics-calibration.yaml) | [verified] 164 cases across 11 rubrics; mitigation and compromise sets have one pass/two fail each |
| [Scenario directories](../../evals/scenarios) and [build scenarios](../../evals/build-scenarios) | [verified] 193 YAML files; file count is not accepted behavioral coverage |
| [Inspect pilot](../../evals/inspect_pilot.py) | [verified] Artifact-only task, native_fleet_parity false; selected fixture includes seven artifact checks and eight omitted checks at this baseline |
| [Requirements](../../requirements-dev.txt) | [verified] inspect-ai 0.3.263 and inspect-swe 0.2.70 are pinned; this does not prove current environment installation |
| [Incident skill](../../skills/incident-investigation/SKILL.md) | [verified] Human advice, discriminating checks, board continuity, existing TLC/ITO and evidence-bound recovery requirements |
| [Stack guidance](../../skills/stack-profile/SKILL.md) | [verified] PCF/on-prem and GCP context; benchmark Kubernetes labs do not redefine the production stack |
| [Judge ADR](../decisions/2026-09-01-rubric-judge-evaluation-contract.md) | [verified] Accepted contract and historical rationale; do not silently rewrite it |
| [Harness threat model](../decisions/2026-10-03-eval-harness-threat-model.md) | [verified] Proposed local measurement boundary, not proof of hostile-code containment |
| [Modernization record](../python-eval-modernization.md) | [sourced] Historical Inspect pilot rationale and tests; those dated results are not fresh acceptance of this plan |

Counts came from parsing the selected YAML and reading source in the fixed worktree. No paid model,
live benchmark, new dependency installation, Docker lab or external-host compatibility check was run
for this specification. The eval README's old omitted-check count differs from the current pilot's
computed selection; implementation should refresh that wording in its owning change.

## External evidence and provenance

Context7 supplied documentation/API discovery where indexed. GitHits supplied public source,
tests and package metadata. Official project pages were used for direct documentation and benchmark
descriptions, including projects missing from Context7. Package metadata, repository main and a
released runtime are different evidence; none is an installation result.

| Source | Supported fact and limit |
|---|---|
| [ITBench-Lite dataset card](https://huggingface.co/datasets/ibm-research/ITBench-Lite) | [sourced] 35 SRE snapshot scenarios, observable data and fault labels; explicitly limited for dynamic investigation/remediation |
| [ITBench evaluations](https://github.com/itbench-hub/ITBench-Evaluations) | [sourced] Entity, reasoning and propagation-oriented assessments; does not supply this fleet's operational rubric |
| [SREGym README](https://github.com/SREGym/SREGym) | [sourced] Live environments, selected diagnosis/mitigation stages and small-suite guidance; exact selected task support needs verification |
| [SREGym Claude client at 9e3c02f6](https://github.com/SREGym/SREGym/blob/9e3c02f6/clients/claudecode/claudecode_agent.py) | [sourced] Claude process/session integration exists; inspected launcher does not itself prove Save Toolkit loading |
| [AIOpsLab](https://github.com/microsoft/AIOpsLab) | [sourced] Application/task/workload/fault/evaluator extension model; proposed later fleet integration remains untested |
| [SWE-bench](https://www.swebench.com/) and [evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/) | [sourced] Verified has 500 human-filtered tasks; harness accepts generated patches; selected subset scores are not full-suite scores |
| [SWT-Bench adapter](https://github.com/harbor-framework/harbor/blob/a2fafbcfaa457e15043dd83eee356c1b036270ed/adapters/swtbench/README.md) | [sourced] Test-generation/reproduction task direction; adapter documentation is not independent local verification |
| [Harbor agents](https://www.harborframework.com/docs/agents) and [skills](https://www.harborframework.com/docs/run-jobs/skills) | [sourced] Installed/custom agents and injected skills; complete plugin/tool/hook parity needs a separate probe |
| [promptfoo Python provider](https://www.promptfoo.dev/docs/providers/python/) | [sourced] Custom provider integration for an existing runner |
| [promptfoo Claude Agent SDK](https://www.promptfoo.dev/docs/providers/claude-agent-sdk/) | [sourced] Local plugin configuration, tool records and transcript-forwarding behavior; not native parity evidence |
| [promptfoo source](https://github.com/promptfoo/promptfoo/blob/main/src/providers/claude-agent-sdk.ts) | [sourced] Local-plugin options and conditional TaskOutput transcript redaction corroborate documentation in the retrieved snapshot |
| [promptfoo caching](https://www.promptfoo.dev/docs/configuration/caching/) and [data handling](https://www.promptfoo.dev/docs/red-team/troubleshooting/data-handling/) | [sourced] Cache/repeat behavior and distinct remote-generation/telemetry/provider paths; mutable docs must match selected release |
| [promptfoo authoring skills](https://www.promptfoo.dev/docs/integrations/agent-skill/) | [sourced] Optional eval/provider/red-team authoring guidance; not installed by this package |
| [DeepEval G-Eval](https://deepeval.com/docs/metrics-llm-evals) | [sourced] Custom steps, thresholds and model grading; accuracy on local rubrics remains unverified |
| [DeepEval metric source](https://github.com/confident-ai/deepeval/blob/main/deepeval/metrics/g_eval/g_eval.py) and [error handling](https://github.com/confident-ai/deepeval/blob/main/deepeval/evaluate/execute/_common.py) | [sourced] Strict-mode/default threshold behavior and error/skip mapping require adapter attention |
| [DeepEval telemetry test at 23901cf](https://github.com/confident-ai/deepeval/blob/23901cf/tests/test_core/test_telemetry.py#L457) | [sourced] Opt-out tested upstream; GitHits served this indexed snapshot while a newer ref indexed, not a local network test |
| [Pydantic Evals judge](https://github.com/pydantic/pydantic-ai/blob/main/docs/evals/evaluators/llm-judge.md) | [sourced] Rubric judgments and input visibility options; quote/evidence parity must be added or demonstrated |
| [Inspect scorers](https://inspect.aisi.org.uk/scorers.html) and [coding tasks](https://inspect.aisi.org.uk/tutorial.html) | [sourced] Reusable scoring and sandboxed coding-agent execution; fleet-specific parity remains separate |

## Coder Eval evidence

UiPath's `coder_eval` agent/skill/tool evaluation framework is the subject of this addition, not a
similarly named function-generation dataset. Context7 did not return a matching library; official
project documentation and GitHits source supplied the evidence. The inspected source revision is
`0fa062a25e6db7cf76edc487cab6967ebe5c55bf`; it is a research snapshot, not an installed dependency pin.

| Source at the inspected revision | Supported fact and limit |
|---|---|
| [Task guide](https://github.com/UiPath/coder_eval/blob/0fa062a25e6db7cf76edc487cab6967ebe5c55bf/docs/TASK_DEFINITION_GUIDE.md#recording-cli-invocations) | [sourced] CLI shims record invocations and return matched canned outputs; stateless and not real-tool proxies |
| [A/B experiments](https://github.com/UiPath/coder_eval/blob/0fa062a25e6db7cf76edc487cab6967ebe5c55bf/docs/AB_EXPERIMENTS.md) | [sourced] Task/configuration variants; our causal comparison and native parity still need validation |
| [Claude adapter](https://github.com/UiPath/coder_eval/blob/0fa062a25e6db7cf76edc487cab6967ebe5c55bf/src/coder_eval/agents/claude_code_agent.py#L1153) | [sourced] Plugin/SDK/session configuration exists; host tools, hooks and fleet behavior are unproven locally |
| [Skill criterion](https://github.com/UiPath/coder_eval/blob/0fa062a25e6db7cf76edc487cab6967ebe5c55bf/src/coder_eval/criteria/skill_triggered.py#L42) | [sourced] Any-turn Skill/path engagement signals; not proof of successful loading, exact namespace or correct application |
| [Report schema](https://github.com/UiPath/coder_eval/blob/0fa062a25e6db7cf76edc487cab6967ebe5c55bf/docs/REPORT_SCHEMA.md) | [sourced] Per-replicate task.json, configuration lineage, prompt semantics, criterion errors and evaluation/gating fields; mapping needs controls |
| [Extension guide](https://github.com/UiPath/coder_eval/blob/0fa062a25e6db7cf76edc487cab6967ebe5c55bf/docs/EXTENDING.md) and [criterion schema](https://github.com/UiPath/coder_eval/blob/0fa062a25e6db7cf76edc487cab6967ebe5c55bf/src/coder_eval/models/criteria.py#L1578) | [sourced] External agent entry points; documented new typed criteria require central union edits despite the guide's general no-base-edit claim |
| [Harbor adapter](https://github.com/UiPath/coder_eval/blob/0fa062a25e6db7cf76edc487cab6967ebe5c55bf/src/coder_eval/harbor/agent.py) | [sourced] Coder Eval agent runs inside Harbor's environment; selected benchmark and fleet compatibility remain untested |

The owner approved including the adoption experiment, product boundaries and earlier useful
comparison on 2026-10-04. No installation, model trial, Workbench integration or replacement decision
is established. Refresh EVAL-010's accepted judge and EVAL-011's native behavior independently of this
frozen runtime baseline before the pilot; framework selection does not reopen those decisions.

## GCP track evidence

The expanded GCP scope was selected on 2026-10-03: managed services and migration, plus broad GCP
coverage including GKE. Repository observations below use the same fixed runtime-source baseline.
Context7 supplied Cloud Run, Cloud Monitoring and gcpdiag documentation; GitHits confirmed selected
upstream source and examples. Official Google documentation supplied the service behavior and limits.
The 64 cases are proposed local designs, not an imported or executed public GCP benchmark.

| Source | Supported fact and limit |
|---|---|
| [GCP skill](../../skills/gcp-ops/SKILL.md), [inventory](../../skills/gcp-ops/references/projects.md) and [migration map](../../skills/gcp-ops/references/cf-to-cloud-run.md) | [verified] Console/protected-read paths, credential exclusions, provisional platform boundary and placeholder inventory; neither real target access nor production runtime selection is established |
| [Existing GCP discovery case](../../evals/scenarios/discovery-gcp-ops-cloud-run-503.yaml) and [query contract](../../evals/scenarios/obs-logs-query-shape-contract.yaml) | [verified] Reusable routing/query controls exist; they do not provide the planned GCP incident catalog or live-cloud evidence |
| [Cloud Run troubleshooting](https://docs.cloud.google.com/run/docs/troubleshooting) and [request timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout) | [sourced] Startup/serving diagnostic paths; a 504 does not necessarily terminate processing. Exact causes require case evidence |
| [Cloud Monitoring alert troubleshooting](https://docs.cloud.google.com/monitoring/alerts/troubleshooting-alerts) and [missing notifications](https://docs.cloud.google.com/monitoring/alerts/troubleshoot-missing-notifications) | [sourced] Data gaps, condition evaluation and notification delivery are distinct diagnostic concerns |
| [GKE workload troubleshooting](https://docs.cloud.google.com/kubernetes-engine/docs/troubleshooting/deployed-workloads) and [authentication](https://docs.cloud.google.com/kubernetes-engine/docs/troubleshooting/authentication) | [sourced] Workload status/error evidence and Kubernetes/Google identity troubleshooting; source documentation does not grant fleet cluster access |
| [Pub/Sub troubleshooting](https://docs.cloud.google.com/pubsub/docs/troubleshooting) and [Cloud SQL diagnosis](https://docs.cloud.google.com/sql/docs/postgres/diagnose-issues) | [sourced] Source material for selected managed-service cases; target configuration and additional scenario-specific sources must be frozen during WP-12 |
| [gcpdiag at 21d36749](https://github.com/GoogleCloudPlatform/gcpdiag/blob/21d36749/README.md) and [Cloud Run deployment tree](https://github.com/GoogleCloudPlatform/gcpdiag/blob/21d36749/gcpdiag/runbook/cloudrun/service_deployment.py) | [sourced] Diagnostic lint/runbook framework and a target-bound deployment tree with explicit code-error coverage limits; community effort, not an officially supported Google product |
| [Cloud Run samples](https://github.com/GoogleCloudPlatform/cloud-run-samples) | [sourced] GitHits source inspection found application/VPC interaction examples; selected fixture commits and independent verifiers remain implementation work |
| [OpenTelemetry Cloud Run at a5fd79a1](https://github.com/GoogleCloudPlatform/opentelemetry-cloud-run/blob/a5fd79a1/golang/README.md) | [sourced] Go workload/Collector sidecar guide for metrics, logs and traces; no fleet adapter or incident scorer is supplied |
| [Local troubleshooting tutorial](https://docs.cloud.google.com/run/docs/tutorials/local-troubleshooting) | [sourced] Deliberately broken Cloud Run service exercise, but the retrieved tutorial retains legacy Container Registry steps. Refresh build/image/authentication instructions before reuse |
| [Cloud Billing budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets) | [sourced] Alerts-only budgets do not cap spending; separate spend-cap preview support is service-dependent and must not be presumed |

## Refresh before implementation

- Fetch current repository state and reconcile EVAL-010/011 repairs before changing harness code.
- Resolve package versions and actual transitive compatibility in an isolated environment; prior
  direct dependency counts are not a dependency lock or an accurate installed-size comparison.
- Pin benchmark dataset/task revisions, licenses, image versions and evaluator versions.
- Verify current SDK/plugin, CLI, session and tool behavior on the exact intended host.
- Recheck data destinations, telemetry, sharing and cache defaults for installed versions.
- Validate availability of source URLs and upstream APIs; keep original source provenance if a
  project moves rather than silently relabelling an older result as current.

## Remaining uncertainty

Native parity of all new framework paths, lab capacity, benchmark environment reproducibility,
Python 3.14 compatibility of new dependencies, judge superiority, operating cost, PCF/GCP transfer,
and candidate behavior on every proposed case remain [unverified]. The plan supplies experiments
to resolve them; it does not convert them into current stack facts.
