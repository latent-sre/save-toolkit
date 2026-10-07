# Delivery plan and decisions

This is the proposed implementation sequence. Live status belongs to EVAL-012 in the
[fleet roadmap](../fleet-roadmap.md). EVAL-010 owns judge selection; EVAL-011 owns repairs to the
native measurement contract. No dates or spend are promised before task/environment measurements.

## Work packages

| Package | Deliverable | Dependencies | Responsible lane | Completion evidence |
|---|---|---|---|---|
| WP-00 Foundation | Freeze scope, implementation home, result rules, the v1 result record, the native host and account, run limits and the first run plan. Lab, benchmark, external-code and GCP decisions are entry conditions of the packages that need them, not WP-00 | Owner accepts this specification; EVAL-011's threat-model ADR accepted (2026-10-06) | Human owner with agent-engineer | DEC-01/02/04/10/11/17-24 recorded; the [first run plan](run-plan-wp02-native-readiness.md); owner acceptance of this specification revision |
| WP-01 Result comparison | A minimal local comparison over v1 records (DEC-22): per-case incumbent/candidate outcomes, gains, regressions, missing pairs, attempts and known/unknown spend; older runs listed as legacy with their gaps | EVAL-011's runner sequence writing v1 records; a committed synthetic bundle; no model access | software-engineer; reviewer verifies | AC-01/02/19/23 and model-free AC-17 attempt controls on the synthetic bundle, in Linux CI and on Windows; zero candidate/judge calls; source verdicts and costs preserved |
| WP-02 Native readiness | Native compatibility of the frozen runner: identity, plugin/agent/skill/tool canaries, helper return and resume, budget and cancellation, and the result rules | EVAL-011's runner sequence complete and its revision frozen; WP-01's v1 mapping; the [first run plan](run-plan-wp02-native-readiness.md) with its DEC-04 figures approved | software-engineer plus agent-engineer; reviewer verifies | AC-03/04/05/18/22/24; model-free controls first, then the bounded native run; native gaps stated |
| WP-03 Judge comparison | Expanded labels, equivalent-contract test, native-method test and adoption recommendation | EVAL-010 decision; case labels; approved model/configuration/budget for live portion | agent-engineer; independent reviewer | AC-15/16 and AC-17 independent live stability calls; held-out results, error parity, separate cached/live costs and net-code disposition |
| WP-04 Incident evidence pilot | Five frozen ITBench-Lite cases through the selected fleet path | WP-02; validated upstream verifier; incumbent calibrated judge or human review | agent-engineer with adapter support | AC-06; original versus local assessments, coverage and applicability |
| WP-05 Incident conversations | Twelve paired local cases; advisor-only and longer sessions, followed by an authored branching responder | WP-02; authored evidence; calibrated rubric or human review | agent-engineer and software-engineer | AC-07/08/26 plus per-turn AC-03/05/18; fixed and branching profiles both complete, with actual continuity distinguished |
| WP-06 Live incident diagnosis | Three SREGym problems with complete lab lifecycle and fleet adapter | WP-00 and WP-02; separate reviewed lab profile; operator and bounded budget | software-engineer and lab operator; agent-engineer owns cases | AC-09/10; reset controls, exact-agent evidence and diagnosis results |
| WP-07 Guided mitigation and recovery | Advisor and lab actor exercises with actual recovery observations | WP-05/06; action/recovery contract and lab actor selected | agent-engineer and lab operator | AC-11; recommendation/action/outcome separation and unknown-effect handling |
| WP-08 Repository repair | Ten SWE-bench Verified tasks, expandable to twenty | WP-00 and WP-02; DEC-13 admission, coding isolation profile and selected executor | software-engineer; reviewer verifies | AC-12/25; independent patch verification, execution-actor receipts and correctly scoped fleet behavior report |
| WP-09 Tests and terminal work | Five SWT-Bench and five selected Terminal-Bench tasks | WP-08; DEC-13 task-specific admission and Inspect/Harbor choice | software-engineer with agent-engineer | AC-13/14/25; valid reproduction, admitted execution and exact-agent task outcomes |
| WP-10 Wider fleet and adversarial coverage | Focused roster suites plus controlled repo/log/helper/judge instruction-injection pairs | WP-02 and relevant established fixture/report patterns | agent-engineer; subject specialist supplies cases; reviewer checks assertions | AC-20/27; useful positive/negative lane controls and all four adversarial surfaces assessed |
| WP-11 AIOpsLab expansion | One new task/environment integration and rollout plan | Working live-lab profile; named coverage goal; later owner selection | software-engineer and lab operator | AC-21; independent lifecycle controls and common report mapping |
| WP-12 GCP case specification | 32 paired GCP families, beginning with the 24-case pilot, then the full 64-case catalog and assessment controls | WP-00 scope and DEC-14 case/applicability decision; no cloud or model calls needed for authoring | agent-engineer with GCP subject reviewer | AC-28; AC-29/30/31/32/33 authored good/bad/unavailable controls; family partitions and source-bound evidence |
| WP-13 GCP fleet evaluation | Native pilot and full catalog, six branching investigations and two human handover tabletops | WP-02 and WP-12 pilot first; WP-05 continuation/branch capability for the interactive portion; calibrated rubric or human review | agent-engineer with software-engineer adapter support; reviewer verifies | AC-29/30/31/32/33/35 and AC-26 for branching; separate supplied/recorded/live and per-service claims; all 64 cases for full completion |
| WP-14 GCP cloud exercises | Four initial live fault/control exercises, expanding to the eight named GCP exercises | WP-00, WP-02, WP-12 controls, WP-13 pilot and DEC-15; admitted cloud/lab actor and bounded budget | Lab operator with software-engineer integration; reviewer checks outcome evidence | AC-32/33 where applicable and AC-34; observed baseline/fault/outcome/cleanup, separate actors and cloud/model costs for all eight exercises |
| WP-15 Coder Eval assessment (postponed, DEC-24) | The six-task Coder Eval adoption experiment, with the accepted grading fixed | Milestone 3 and the owner's go/no-go; the [prerequisites](coder-eval.md#postponement-and-prerequisites), including a threat-model amendment admitting a third-party runner | software-engineer plus agent-engineer; reviewer verifies | AC-36/37; maintainer usefulness, replacement inventory and DEC-16 disposition |

WP-02 covers native readiness only. The Coder Eval assessment moved to WP-15 (DEC-24), which starts
after the first useful comparison and the owner's go/no-go; while it waits, it is neither a
native-readiness failure nor a rejection. The long-term report format is chosen there under DEC-16.

WP-01's importer can be built against the synthetic bundle while EVAL-011's runner sequence lands; it
waits for neither lab provisioning nor a judge replacement. WP-04 and WP-08 can use
the incumbent calibrated judge or documented human review; they do not wait for a library to win
WP-03. Coding and SREGym work can proceed as separately owned packages after their shared foundations,
but concurrent execution is not assumed or authorized by this plan.
WP-12 can be authored alongside WP-01. GCP evidence evaluation does not wait for cloud provisioning,
gcpdiag adoption, a new judge or AIOpsLab. WP-13's native pilot precedes its branching/human portion;
work-package numbers identify scope rather than imposing a total execution order.

## Delivery milestones

1. **Reviewable design:** this package, a single roadmap entry, complete requirement/acceptance
   mapping and explicitly owned open decisions. No implementation claim.
2. **Working instrument:** WP-01 and WP-02, with model-free controls and a bounded native
   compatibility run. Original fleet behavior remains the reference, with no benchmark capability
   verdict yet.
3. **First useful candidate comparison:** after those native/report readiness checks, one frozen incumbent/candidate change on
   selected representative cases through the accepted path, with decisive evidence and a human
   disposition. This is separate from comparing the same agent on two runners. Broader benchmark
   coverage, the WP-15 runner assessment and Workbench implementation are not prerequisites when the
   accepted native path is used. WP-15 starts only after this milestone and its own go/no-go.
4. **Benchmark and GCP pilot coverage:** WP-04, WP-06, WP-08 and the WP-12/13 GCP pilot. This milestone
   includes ITBench-Lite, SREGym, coding repair and 24 authored GCP cases. Each reports selected
   cases, exact candidate and limitations; the pilot alone does not complete WP-12/13.
5. **Broader fleet evaluation:** WP-03/05/07/09/10, full WP-12/13 and WP-14, including a judge disposition, longer and branching
   incident conversations, recovery advice, test generation, terminal work, wider roster coverage
   and controlled adversarial cases, the complete GCP catalog, GCP handover tabletops and eight live
   cloud exercises. Fixed conversations alone do not complete WP-05 or the interactive part of WP-13.
6. **Environment expansion:** WP-11 adds Microsoft AIOpsLab for the selected later capability.

Only mark a work package complete when its named acceptance evidence exists. Framework installation
and a successful import are not substitutes. If a proposed tool is rejected, retain the capability
requirement and record the replacement/disposition in the roadmap.

## Implementation boundaries

Prefer small reviewable changes: logical result mapping, then report integration, then host adapter,
then a benchmark-specific adapter. Each new mechanism names the failure or gap it addresses. Use
existing fixtures before adding new ones; retain one canonical scenario source. No generated fleet
adapter edits are needed until canonical agents/skills change.

Separate source correctness, runtime compatibility and model behavior evidence. Use offline
regressions for code changes, selected native canaries for host changes, and paired behavior trials
for prompt changes. Record every unresolved difference before replacing the native path.

Coder Eval is the first alternative runner to assess, in WP-15 under its [experiment contract](coder-eval.md).
Keep grading fixed and assess its existing Harbor bridge before writing overlapping integration.
If a promptfoo SDK path is later needed, first prove one skill and one helper exchange. The SREGym adapter
should first prove setup/read/submission/reset with controlled outputs before a paid agent trial.
The SWE adapter should first run the official reference and intentionally wrong patches through its
verifier before asking software-engineer to solve a task.

## Decisions

Until a role named in this table is assigned to someone else, the human owner holds it. WP-00 records
the decided rows; each open row is an entry condition of the package in its "Needed before" column,
not of WP-00.

| ID | Decision and recommendation | Owner | Needed before | If unresolved |
|---|---|---|---|---|
| DEC-01 | **Decided 2026-10-05:** implementation starts in this repository as thin repo-local adapters; a separate repository follows only if the work expands and shows independent value | Human owner | WP-01 code placement | Plans remain here; no assumed relationship to the Workbench implementation repo |
| DEC-02 | **Decided 2026-10-05:** the native Claude Code plugin is the automated reference, because the team does this work in Claude Code and it has carried over to VS Code Copilot. Copilot, which the team also uses, is verified by humans with the [VS Code plugin acceptance](../vscode-plugin-acceptance.md) cases under DEC-19, because the owner judges it cannot be scripted; this names the method, not a current result, and RELEASE-001 records which cases have run on a candidate. Coder Eval/SDK/SREGym/Inspect/Harbor parity is measured separately, and host results are never pooled | Human owner; maintainers implement | WP-02 live run | Native reference remains authoritative |
| DEC-03 | Lab host and capacity: dedicated Linux environment, serial pilot first; Windows/Linux report tooling | Lab operator and owner | WP-06/08 setup | No lab readiness claim; offline planning/import continues |
| DEC-04 | **Decided 2026-10-05:** campaigns use the owner's existing access — the Claude subscription through Claude Code, the Codex subscription through `codex exec`, and an OpenRouter API key for other providers. Each campaign states its trial count, estimated cost, estimated human review hours and cost cap before running, with task and judge spend reported separately. Keys stay in the owner's environment, never in the repository or run records | Human owner | Any paid call or remote execution | Model-free controls only |
| DEC-05 | Judge adoption: incumbent, Inspect, Pydantic Evals or DeepEval by calibrated comparison | EVAL-010 owner | Replacing the current judge | Incumbent or human review retained |
| DEC-06 | Coding executor/environment: compare the smallest Inspect extension with Harbor; assess Coder Eval's existing Harbor bridge if relevant to DEC-16, with one owner for each execution responsibility | Maintainers | WP-08/09 integration selection | Native parity and independent verifiers still required; no duplicate general-purpose runners installed by default |
| DEC-07 | Benchmark revisions and task lists: fixed selection and licenses reviewed before scores | Case owner | Each benchmark pilot | Proposed counts remain estimates, not a frozen manifest |
| DEC-08 | Lab action profile: diagnosis first; separate operator executes guided recovery | Human owner and lab operator | WP-07 | No change authority inferred from a benchmark |
| DEC-09 | Multi-turn implementation: advisor-only two turns first, then authored longer conversations | Maintainers | WP-05 code change | Existing snapshots remain useful but do not prove runtime continuity |
| DEC-10 | **Decided 2026-10-05:** freeze per experiment before running, starting from this default: three interleaved trials per arm; each scenario's native threshold, never a framework average; any safety or authority check (deployment, credential output, unapproved write) fails the candidate on a single failure; no pooling across models, hosts or CLI versions; human acceptance of the exact revision. The existing calibration contract is preserved | Human owner and reviewer | Candidate comparison | Results are exploratory, not acceptance evidence |
| DEC-11 | **Decided 2026-10-05:** raw run artifacts stay local and private, and shared reports are redacted summaries. OpenRouter calls go only to providers that do not retain prompts or train on them, enforced by the owner's OpenRouter API key settings | Human owner | External model/data path or publication | No implicit hosted sync or shared report |
| DEC-12 | AIOpsLab's first coverage goal and repository connection | Human owner | WP-11 | Remains later scope, not a dependency of initial milestones |
| DEC-13 | External-code admission: recommend unchanged agent policy, manual model session and separately authorized CI execution with receipts; direct agent execution in a lab needs a separate canonical policy decision | Human owner and maintainers, with CI execution owner | WP-08/09, before any external repository command | Static authoring can proceed; execution and self-verification claims remain blocked until the profile is admitted |
| DEC-14 | GCP catalog: freeze the named pilot/full cases, source revisions, applicability, interface profiles and family partitions; evaluate managed services/migration first and GKE separately | Human owner and case owner | WP-12 case acceptance and WP-13 run selection | Synthetic case drafting proceeds; no actual environment or settled production runtime is inferred |
| DEC-15 | GCP lab: select disposable project(s), regions, services, GKE mode/version, observation permissions and tested pre-model output protection, operator identities, resource/run limits, budget, test notification sink and cleanup owner | Human owner and lab operator | WP-14 cloud execution | Evidence/recorded-observation work continues; no cloud provisioning, credential access or paid run is implied |
| DEC-16 | Coder Eval adoption and comparison presentation: assess first through AC-36/37 in WP-15; record full, limited or rejected adoption, practical benefit, exact responsibilities removed/retained/added, and one primary report path. Adoption or a limited role also needs a successor to the [one-runner ADR](../decisions/2026-09-03-one-eval-runner.md) | Human owner with maintainers and reviewer | WP-15 trials (benefit thresholds); replacing a runner or selecting lasting presentation | Native execution and WP-01's minimal local comparison continue; no permanent extra orchestrator, grader or result ledger assumed |
| DEC-17 | **Decided 2026-10-05:** Claude Code runs use the `sonnet` alias by default, and each run records the concrete model that answered; Codex runs use the latest Sol model. Any other model is a named per-campaign choice, never pooled with these (DEC-10) | Human owner | Any campaign | — |
| DEC-18 | **Decided 2026-10-05:** the frozen incumbent/candidate comparison runs before each major release and gates the release-tag bump (RELEASE-001) | Human owner | The first major release tag | — |
| DEC-19 | **Decided 2026-10-05:** before each major release, a human runs the [VS Code plugin acceptance](../vscode-plugin-acceptance.md) cases on the shipping bytes, including its deployment and review behavior cases, and records PASS/FAIL/UNVERIFIED per case | Human owner | Each major release | — |
| DEC-20 | **Decided 2026-10-05:** the human owner makes a go/no-go call before each delivery milestone, judged by whether the previous milestone's results changed a real decision, and reviews evaluation-code growth before work expands | Human owner | Each milestone after the first | — |
| DEC-21 | **Decided 2026-10-06:** verdicts in every profile follow the result rules of the accepted [threat-model ADR](../decisions/2026-10-03-eval-harness-threat-model.md); adapters map to those rules rather than restating them | Human owner (maintainers) | Any assessment | — |
| DEC-22 | **Decided 2026-10-06:** the runner writes one versioned [v1 record](contracts.md#result-record-v1) per trial as part of EVAL-011's runner sequence. WP-01 reads v1 only and lists older runs as legacy with their gaps; a legacy importer needs a named consumer | Human owner | WP-01 importer | — |
| DEC-23 | **Decided 2026-10-06:** native runs use this Windows host under the owner's everyday account, unelevated. The runner creates run folders that inherit the parent's permissions instead of owner-only temporary folders, and older owner-only folders get a one-time read grant from an elevated prompt. Linux report checks run in CI on synthetic bundles | Human owner | WP-02 live run | — |
| DEC-24 | **Decided 2026-10-06:** the Coder Eval assessment moves to WP-15, after milestone 3 and the owner's go/no-go. It needs a threat-model amendment for a third-party runner, one Linux or WSL host for both arms, two maintainers besides the case author and a GCP case, none of which the native path needs; WP-02 is native readiness only | Human owner | WP-15 | — |

Each decision records the chosen alternative, reason, exact scope and evidence. Do not reopen a
settled choice without new information. No decision grants the evaluated agent additional authority.

## Material risks and responses

| Risk | Practical consequence | Planned response |
|---|---|---|
| Runtime changes the evaluated behavior | Improvements belong to the wrapper rather than the fleet | Native compatibility set and recorded instruction/tool/transcript differences |
| Benchmark answer leakage or familiarity | Inflated scores | Hidden verifier/reference partition, source provenance and separate held-out local cases |
| Judge rewards polished wording over evidence | Unsafe or unsupported advice passes | Human labels, quote checks, counterexamples and per-rubric false-pass reporting |
| Replay, retries or mismatched arms inflate success | Unreliable comparison | Explicit attempt identity, cache policy and expected-count reconciliation |
| Kubernetes tasks do not match PCF/GCP work | Poor operational transfer | Applicability labels, WP-05's Apps Manager cases and WP-12/13's explicit migration/managed-service/GKE catalog; local Kubernetes is not GKE evidence |
| GCP permissions or telemetry hide decisive evidence | False health claim or wrong target | AC-29/31 resource/interface controls and explicit unknown observations |
| Cloud resources outlive a cancelled trial | Continuing spend or contaminated state | DEC-15 resource inventory, bounded scheduling and AC-34 verified cleanup with residual cost recorded |
| Dirty lab state contaminates the next trial | Wrong diagnosis or false recovery | Observed baseline/fault/reset and block on failed cleanup |
| Dependencies and adapters exceed code removed | Higher maintenance | Isolated pilots, explicit removal inventory and rejection of redundant frameworks |
| Framework signals are mistaken for useful work | Skill activation or a recorded command passes despite a wrong investigation | Independent outcome controls and maintainer disposition under AC-36/37; CLI stubs do not establish Workbench implementation or live GCP behavior |
| Reference tests miss a regression | Patch looks correct but is incomplete | Preserve benchmark scope, add targeted independent controls, retain human review |
| Costs are unavailable or exceed estimates | Unbounded campaign | Small measured preflight, scheduling limits and explicit unknown spend |
| Existing harness work changes during implementation | Conflicts or stale assumptions | Refresh EVAL-010/011 and source identities at each package boundary |

## Rollback and handoff

Keep new execution profiles opt-in until accepted. Rollback selects the native executor/incumbent
judge and preserves both old and new artifacts. Do not delete failed evidence to restore a clean
report. A lab rollback restores/destroys only the named exercise resources and verifies the result.
Dataset/package rollback requires a new run identity, not overwriting earlier evidence.

Each implementation handoff includes the invoking caller, human owner, package scope, exact source
revision, tests run, raw evidence location, limitations and next caller action. Human acceptance is
recorded against the actual candidate after review; no framework score promotes it automatically.
