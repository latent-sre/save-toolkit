# Delivery plan and decisions

This is the proposed implementation sequence. Live status belongs to EVAL-012 in the
[fleet roadmap](../fleet-roadmap.md). EVAL-010 owns judge selection; EVAL-011 owns repairs to the
native measurement contract. No dates or spend are promised before task/environment measurements.

## Work packages

| Package | Deliverable | Dependencies | Responsible lane | Completion evidence |
|---|---|---|---|---|
| WP-00 Foundation | Freeze scope, implementation home, logical mappings, case-selection rules, lab/authentication profiles, external-code execution admission and run limits | Owner reviews this specification; relevant EVAL-011 contract disposition | Human owner with agent-engineer and lab operator | Decisions recorded, including DEC-13 before external coding runs; one reviewable run plan; no invented host capability |
| WP-01 Saved result comparison | Import native records and produce a relocatable local comparison on Windows and Linux; select lasting presentation under DEC-16 | Existing saved or synthetic records; no model access needed; minimal report does not wait for WP-02 | software-engineer; reviewer verifies | AC-01/02/19/23 and model-free AC-17 replay/attempt controls; zero candidate/judge calls; source verdicts and costs preserved |
| WP-02 Actual fleet integration | Plugin/agent staging, native compatibility and the six-task Coder Eval adoption experiment, retaining accepted grading | WP-00; relevant native identity/error repairs from EVAL-011; WP-01's result mapping for comparison | software-engineer plus agent-engineer; reviewer verifies | AC-03/04/05/18/22/24/36/37; controlled failures, explicit native/parity gaps, maintainer usefulness, replacement inventory and DEC-16 disposition |
| WP-03 Judge comparison | Expanded labels, equivalent-contract test, native-method test and adoption recommendation | EVAL-010 decision; case labels; approved model/configuration/budget for live portion | agent-engineer; independent reviewer | AC-15/16 and AC-17 independent live stability calls; held-out results, error parity, separate cached/live costs and net-code disposition |
| WP-04 Incident evidence pilot | Five frozen ITBench-Lite cases through the selected fleet path | WP-02 readiness for the selected path; validated upstream verifier; incumbent calibrated judge or human review | agent-engineer with adapter support | AC-06; original versus local assessments, coverage and applicability |
| WP-05 Incident conversations | Twelve paired local cases; advisor-only and longer sessions, followed by an authored branching responder | WP-02 readiness for the selected path; authored evidence; calibrated rubric or human review | agent-engineer and software-engineer | AC-07/08/26 plus per-turn AC-03/05/18; fixed and branching profiles both complete, with actual continuity distinguished |
| WP-06 Live incident diagnosis | Three SREGym problems with complete lab lifecycle and fleet adapter | WP-00 and WP-02 readiness for the selected path; separate reviewed lab profile; operator and bounded budget | software-engineer and lab operator; agent-engineer owns cases | AC-09/10; reset controls, exact-agent evidence and diagnosis results |
| WP-07 Guided mitigation and recovery | Advisor and lab actor exercises with actual recovery observations | WP-05/06; action/recovery contract and lab actor selected | agent-engineer and lab operator | AC-11; recommendation/action/outcome separation and unknown-effect handling |
| WP-08 Repository repair | Ten SWE-bench Verified tasks, expandable to twenty | WP-00 and WP-02 readiness for the selected path; DEC-13 admission, coding isolation profile and selected executor | software-engineer; reviewer verifies | AC-12/25; independent patch verification, execution-actor receipts and correctly scoped fleet behavior report |
| WP-09 Tests and terminal work | Five SWT-Bench and five selected Terminal-Bench tasks | WP-08; DEC-13 task-specific admission and Inspect/Harbor choice | software-engineer with agent-engineer | AC-13/14/25; valid reproduction, admitted execution and exact-agent task outcomes |
| WP-10 Wider fleet and adversarial coverage | Focused roster suites plus controlled repo/log/helper/judge instruction-injection pairs | WP-02 readiness for the selected path and relevant established fixture/report patterns | agent-engineer; subject specialist supplies cases; reviewer checks assertions | AC-20/27; useful positive/negative lane controls and all four adversarial surfaces assessed |
| WP-11 AIOpsLab expansion | One new task/environment integration and rollout plan | Working live-lab profile; named coverage goal; later owner selection | software-engineer and lab operator | AC-21; independent lifecycle controls and common report mapping |
| WP-12 GCP case specification | 32 paired GCP families, beginning with the 24-case pilot, then the full 64-case catalog and assessment controls | WP-00 scope and DEC-14 case/applicability decision; no cloud or model calls needed for authoring | agent-engineer with GCP subject reviewer | AC-28; AC-29/30/31/32/33 authored good/bad/unavailable controls; family partitions and source-bound evidence |
| WP-13 GCP fleet evaluation | Native pilot and full catalog, six branching investigations and two human handover tabletops | WP-02 readiness for the selected path and WP-12 pilot first; WP-05 continuation/branch capability for the interactive portion; calibrated rubric or human review | agent-engineer with software-engineer adapter support; reviewer verifies | AC-29/30/31/32/33/35 and AC-26 for branching; separate supplied/recorded/live and per-service claims; all 64 cases for full completion |
| WP-14 GCP cloud exercises | Four initial live fault/control exercises, expanding to the eight named GCP exercises | WP-00, WP-02 readiness for the selected path, WP-12 controls, WP-13 pilot and DEC-15; admitted cloud/lab actor and bounded budget | Lab operator with software-engineer integration; reviewer checks outcome evidence | AC-32/33 where applicable and AC-34; observed baseline/fault/outcome/cleanup, separate actors and cloud/model costs for all eight exercises |

WP-02 has two independently reviewable portions: native readiness (AC-03/04/05/18/22/24) and the
Coder Eval assessment (AC-36/37 and DEC-16). Native-backed work and the first useful comparison may
proceed after native readiness and their own prerequisites pass while the alternative assessment
remains open. A Coder Eval-backed path additionally needs acceptance of its specific scope under
DEC-16. Full WP-02 completion requires both portions to be dispositioned; a pending alternative
assessment is not silently dropped or treated as a native-readiness failure.

WP-01 can start independently of lab provisioning and a judge replacement. WP-04 and WP-08 can use
the incumbent calibrated judge or documented human review; they do not wait for a library to win
WP-03. Coding and SREGym work can proceed as separately owned packages after their shared foundations,
but concurrent execution is not assumed or authorized by this plan.
WP-12 can be authored alongside WP-01. GCP evidence evaluation does not wait for cloud provisioning,
gcpdiag adoption, a new judge or AIOpsLab. WP-13's native pilot precedes its branching/human portion;
work-package numbers identify scope rather than imposing a total execution order.

## Delivery milestones

1. **Reviewable design:** this package, a single roadmap entry, complete requirement/acceptance
   mapping and explicitly owned open decisions. No implementation claim.
2. **Working instrument:** WP-01 and WP-02's native-readiness portion, with model-free controls and
   a bounded native compatibility run. The early Coder Eval assessment can proceed independently.
   Original fleet behavior remains the reference, with no benchmark capability verdict yet.
3. **First useful candidate comparison:** after those native/report readiness checks, one frozen incumbent/candidate change on
   selected representative cases through the accepted path, with decisive evidence and a human
   disposition. This is separate from comparing the same agent on two runners. Broader benchmark
   coverage, completion of the alternative-runner assessment and Workbench implementation are not
   prerequisites when the accepted native path is used.
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

Coder Eval is the first alternative runner assessed, under its [experiment contract](coder-eval.md).
Keep grading fixed and assess its existing Harbor bridge before writing overlapping integration.
If a promptfoo SDK path is later needed, first prove one skill and one helper exchange. The SREGym adapter
should first prove setup/read/submission/reset with controlled outputs before a paid agent trial.
The SWE adapter should first run the official reference and intentionally wrong patches through its
verifier before asking software-engineer to solve a task.

## Decisions

| ID | Decision and recommendation | Owner | Needed before | If unresolved |
|---|---|---|---|---|
| DEC-01 | **Decided 2026-10-05:** implementation starts in this repository as thin repo-local adapters; a separate repository follows only if the work expands and shows independent value | Human owner | WP-01 code placement | Plans remain here; no assumed relationship to the Workbench implementation repo |
| DEC-02 | **Decided 2026-10-05:** the native Claude Code plugin is the automated reference, because the team does this work in Claude Code and it has carried over to VS Code Copilot. Copilot, which the team also uses, is verified by humans through the [VS Code plugin acceptance](../vscode-plugin-acceptance.md) cases; the owner judges it cannot be scripted. Coder Eval/SDK/SREGym/Inspect/Harbor parity is measured separately, and host results are never pooled | Maintainers | WP-02 live run | Native reference remains authoritative |
| DEC-03 | Lab host and capacity: dedicated Linux environment, serial pilot first; Windows/Linux report tooling | Lab operator and owner | WP-06/08 setup | No lab readiness claim; offline planning/import continues |
| DEC-04 | **Decided 2026-10-05:** campaigns use the owner's existing access — the Claude subscription through Claude Code, the Codex subscription through `codex exec`, and an OpenRouter API key for other providers. Each campaign states its trial count, estimated cost and cost cap before running, with task and judge spend reported separately. Keys stay in the owner's environment, never in the repository or run records | Human owner | Any paid call or remote execution | Model-free controls only |
| DEC-05 | Judge adoption: incumbent, Inspect, Pydantic Evals or DeepEval by calibrated comparison | EVAL-010 owner | Replacing the current judge | Incumbent or human review retained |
| DEC-06 | Coding executor/environment: compare the smallest Inspect extension with Harbor; assess Coder Eval's existing Harbor bridge if relevant to DEC-16, with one owner for each execution responsibility | Maintainers | WP-08/09 integration selection | Native parity and independent verifiers still required; no duplicate general-purpose runners installed by default |
| DEC-07 | Benchmark revisions and task lists: fixed selection and licenses reviewed before scores | Case owner | Each benchmark pilot | Proposed counts remain estimates, not a frozen manifest |
| DEC-08 | Lab action profile: diagnosis first; separate operator executes guided recovery | Human owner and lab operator | WP-07 | No change authority inferred from a benchmark |
| DEC-09 | Multi-turn implementation: advisor-only two turns first, then authored longer conversations | Maintainers | WP-05 code change | Existing snapshots remain useful but do not prove runtime continuity |
| DEC-10 | **Decided 2026-10-05:** freeze per experiment before running, starting from this default: three interleaved trials per arm; each scenario's native threshold, never a framework average; any safety or authority check (deployment, credential output, unapproved write) fails the candidate on a single failure; no pooling across models, hosts or CLI versions; human acceptance of the exact revision. The existing calibration contract is preserved | Human owner and reviewer | Candidate comparison | Results are exploratory, not acceptance evidence |
| DEC-11 | Evidence retention/sharing: local private artifacts and redacted review summaries | Human owner | External model/data path or publication | No implicit hosted sync or shared report |
| DEC-12 | AIOpsLab's first coverage goal and repository connection | Human owner | WP-11 | Remains later scope, not a dependency of initial milestones |
| DEC-13 | External-code admission: recommend unchanged agent policy, manual model session and separately authorized CI execution with receipts; direct agent execution in a lab needs a separate canonical policy decision | Human owner and maintainers, with CI execution owner | WP-08/09, before any external repository command | Static authoring can proceed; execution and self-verification claims remain blocked until the profile is admitted |
| DEC-14 | GCP catalog: freeze the named pilot/full cases, source revisions, applicability, interface profiles and family partitions; evaluate managed services/migration first and GKE separately | Human owner and case owner | WP-12 case acceptance and WP-13 run selection | Synthetic case drafting proceeds; no actual environment or settled production runtime is inferred |
| DEC-15 | GCP lab: select disposable project(s), regions, services, GKE mode/version, observation permissions and tested pre-model output protection, operator identities, resource/run limits, budget, test notification sink and cleanup owner | Human owner and lab operator | WP-14 cloud execution | Evidence/recorded-observation work continues; no cloud provisioning, credential access or paid run is implied |
| DEC-16 | Coder Eval adoption and comparison presentation: assess first through AC-36/37; record full, limited or rejected adoption, practical benefit, exact responsibilities removed/retained/added, and one primary report path | Human owner with maintainers and reviewer | Replacing a runner or selecting lasting presentation; benefit thresholds before pilot | Native execution and minimal portable comparison continue; no permanent extra orchestrator, grader or result ledger assumed |

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
