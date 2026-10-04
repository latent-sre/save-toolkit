# Delivery plan and decisions

This is the proposed implementation sequence. Live status belongs to EVAL-012 in the
[fleet roadmap](../fleet-roadmap.md). EVAL-010 owns judge selection; EVAL-011 owns repairs to the
native measurement contract. No dates or spend are promised before task/environment measurements.

## Work packages

| Package | Deliverable | Dependencies | Responsible lane | Completion evidence |
|---|---|---|---|---|
| WP-00 Foundation | Freeze scope, implementation home, logical mappings, case-selection rules, lab/authentication profiles, external-code execution admission and run limits | Owner reviews this specification; relevant EVAL-011 contract disposition | Human owner with agent-engineer and lab operator | Decisions recorded, including DEC-13 before external coding runs; one reviewable run plan; no invented host capability |
| WP-01 Saved result comparison | Import native records and produce a relocatable local promptfoo comparison or export feeding it on Windows and Linux | Existing saved or synthetic records; no model access needed | software-engineer; reviewer verifies | AC-01/02/19/23 and model-free AC-17 replay/attempt controls; zero candidate/judge calls; source verdicts and costs preserved |
| WP-02 Actual fleet integration | Plugin/agent staging, native wrapper and optional SDK/launcher compatibility probes | WP-00; relevant native identity/error repairs from EVAL-011 | software-engineer plus agent-engineer; reviewer verifies | AC-03/04/05/18/22/24; task/instrument failure controls, explicit native/parity gaps and exact-version evidence |
| WP-03 Judge comparison | Expanded labels, equivalent-contract test, native-method test and adoption recommendation | EVAL-010 decision; case labels; approved model/configuration/budget for live portion | agent-engineer; independent reviewer | AC-15/16 and AC-17 independent live stability calls; held-out results, error parity, separate cached/live costs and net-code disposition |
| WP-04 Incident evidence pilot | Five frozen ITBench-Lite cases through the selected fleet path | WP-02; validated upstream verifier; incumbent calibrated judge or human review | agent-engineer with adapter support | AC-06; original versus local assessments, coverage and applicability |
| WP-05 Incident conversations | Twelve paired local cases; advisor-only and longer sessions, followed by an authored branching responder | WP-02; authored evidence; calibrated rubric or human review | agent-engineer and software-engineer | AC-07/08/26 plus per-turn AC-03/05/18; fixed and branching profiles both complete, with actual continuity distinguished |
| WP-06 Live incident diagnosis | Three SREGym problems with complete lab lifecycle and fleet adapter | WP-00/02; separate reviewed lab profile; operator and bounded budget | software-engineer and lab operator; agent-engineer owns cases | AC-09/10; reset controls, exact-agent evidence and diagnosis results |
| WP-07 Guided mitigation and recovery | Advisor and lab actor exercises with actual recovery observations | WP-05/06; action/recovery contract and lab actor selected | agent-engineer and lab operator | AC-11; recommendation/action/outcome separation and unknown-effect handling |
| WP-08 Repository repair | Ten SWE-bench Verified tasks, expandable to twenty | WP-00/02; DEC-13 admission, coding isolation profile and selected executor | software-engineer; reviewer verifies | AC-12/25; independent patch verification, execution-actor receipts and correctly scoped fleet behavior report |
| WP-09 Tests and terminal work | Five SWT-Bench and five selected Terminal-Bench tasks | WP-08; DEC-13 task-specific admission and Inspect/Harbor choice | software-engineer with agent-engineer | AC-13/14/25; valid reproduction, admitted execution and exact-agent task outcomes |
| WP-10 Wider fleet and adversarial coverage | Focused roster suites plus controlled repo/log/helper/judge instruction-injection pairs | WP-02 and relevant established fixture/report patterns | agent-engineer; subject specialist supplies cases; reviewer checks assertions | AC-20/27; useful positive/negative lane controls and all four adversarial surfaces assessed |
| WP-11 AIOpsLab expansion | One new task/environment integration and rollout plan | Working live-lab profile; named coverage goal; later owner selection | software-engineer and lab operator | AC-21; independent lifecycle controls and common report mapping |

WP-01 can start independently of lab provisioning and a judge replacement. WP-04 and WP-08 can use
the incumbent calibrated judge or documented human review; they do not wait for a library to win
WP-03. Coding and SREGym work can proceed as separately owned packages after their shared foundations,
but concurrent execution is not assumed or authorized by this plan.

## Delivery milestones

1. **Reviewable design:** this package, a single roadmap entry, complete requirement/acceptance
   mapping and explicitly owned open decisions. No implementation claim.
2. **Working instrument:** WP-01/02 with model-free controls and a bounded native compatibility run.
   Original fleet behavior remains the reference, with no benchmark capability verdict yet.
3. **First substantive evaluation:** WP-04, WP-06 and WP-08. This milestone includes ITBench-Lite,
   SREGym and coding repair. Each reports selected cases, exact candidate and limitations.
4. **Broader fleet evaluation:** WP-03/05/07/09/10, including a judge disposition, longer and branching
   incident conversations, recovery advice, test generation, terminal work, wider roster coverage
   and controlled adversarial cases. Fixed conversations alone do not complete WP-05.
5. **Environment expansion:** WP-11 adds Microsoft AIOpsLab for the selected later capability.

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

The promptfoo SDK path should first prove one skill and one helper exchange. The SREGym adapter
should first prove setup/read/submission/reset with controlled outputs before a paid agent trial.
The SWE adapter should first run the official reference and intentionally wrong patches through its
verifier before asking software-engineer to solve a task.

## Decisions

| ID | Decision and recommendation | Owner | Needed before | If unresolved |
|---|---|---|---|---|
| DEC-01 | Implementation home: start with thin repo-local adapters; choose a separate repo only for a concrete independent consumer/release need | Human owner | WP-01 code placement | Plans remain here; no assumed relationship to the Workbench implementation repo |
| DEC-02 | Primary runtime: native Claude plugin first; SDK/SREGym/Inspect/Harbor parity measured separately | Maintainers | WP-02 live run | Native reference remains authoritative |
| DEC-03 | Lab host and capacity: dedicated Linux environment, serial pilot first; Windows/Linux report tooling | Lab operator and owner | WP-06/08 setup | No lab readiness claim; offline planning/import continues |
| DEC-04 | Credentials, provider destinations and budget: explicitly selected per campaign, separate task and judge spend | Human owner | Any paid call or remote execution | Model-free controls only |
| DEC-05 | Judge adoption: incumbent, Inspect, Pydantic Evals or DeepEval by calibrated comparison | EVAL-010 owner | Replacing the current judge | Incumbent or human review retained |
| DEC-06 | Coding executor: extend Inspect unless Harbor demonstrates needed coverage/parity/maintenance advantage | Maintainers | WP-08/09 integration selection | No duplicate general-purpose runners installed by default |
| DEC-07 | Benchmark revisions and task lists: fixed selection and licenses reviewed before scores | Case owner | Each benchmark pilot | Proposed counts remain estimates, not a frozen manifest |
| DEC-08 | Lab action profile: diagnosis first; separate operator executes guided recovery | Human owner and lab operator | WP-07 | No change authority inferred from a benchmark |
| DEC-09 | Multi-turn implementation: advisor-only two turns first, then authored longer conversations | Maintainers | WP-05 code change | Existing snapshots remain useful but do not prove runtime continuity |
| DEC-10 | Acceptance thresholds and critical checks: freeze per experiment; preserve existing calibration contract | Human owner and reviewer | Candidate comparison | Results are exploratory, not acceptance evidence |
| DEC-11 | Evidence retention/sharing: local private artifacts and redacted review summaries | Human owner | External model/data path or publication | No implicit hosted sync or shared report |
| DEC-12 | AIOpsLab's first coverage goal and repository connection | Human owner | WP-11 | Remains later scope, not a dependency of initial milestones |
| DEC-13 | External-code admission: recommend unchanged agent policy, manual model session and separately authorized CI execution with receipts; direct agent execution in a lab needs a separate canonical policy decision | Human owner and maintainers, with CI execution owner | WP-08/09, before any external repository command | Static authoring can proceed; execution and self-verification claims remain blocked until the profile is admitted |

Each decision records the chosen alternative, reason, exact scope and evidence. Do not reopen a
settled choice without new information. No decision grants the evaluated agent additional authority.

## Material risks and responses

| Risk | Practical consequence | Planned response |
|---|---|---|
| Runtime changes the evaluated behavior | Improvements belong to the wrapper rather than the fleet | Native compatibility set and recorded instruction/tool/transcript differences |
| Benchmark answer leakage or familiarity | Inflated scores | Hidden verifier/reference partition, source provenance and separate held-out local cases |
| Judge rewards polished wording over evidence | Unsafe or unsupported advice passes | Human labels, quote checks, counterexamples and per-rubric false-pass reporting |
| Replay, retries or mismatched arms inflate success | Unreliable comparison | Explicit attempt identity, cache policy and expected-count reconciliation |
| Kubernetes tasks do not match PCF work | Poor operational transfer | Applicability labels and separate PCF/GCP fixtures |
| Dirty lab state contaminates the next trial | Wrong diagnosis or false recovery | Observed baseline/fault/reset and block on failed cleanup |
| Dependencies and adapters exceed code removed | Higher maintenance | Isolated pilots, explicit removal inventory and rejection of redundant frameworks |
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
