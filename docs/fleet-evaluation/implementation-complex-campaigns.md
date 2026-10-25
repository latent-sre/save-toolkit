# Complex evaluation campaigns implementation plan

**Goal:** Advance WP-08, WP-04, WP-05 and WP-09, plus a campaign report, through all locally
verifiable work. Record each live execution, paid-run or exact-candidate acceptance gate and
continue the other packages when one reaches a gate. Execution status stays in EVAL-012.

**Basis:** The accepted [specification](README.md), [contracts](contracts.md),
[scenario requirements](scenarios.md), [delivery decisions](delivery.md), and the owner's direction
to use complex cases and complete preparation before asking for gated execution.

## Scope and complexity

- Authored incident cases require multi-step reasoning, competing supported explanations,
  time/freshness distinctions, an accessible discriminating observation and meaningful recovery
  evidence. Add realistic noise without changing the one fact that distinguishes paired variants.
- Preserve existing bridge/TLC coordination and actor boundaries. Supplied observations and helper
  returns are labelled as supplied; they do not establish live reads or actual delegation.
- Select public cases for intrinsic difficulty, diversity and source coherence before observing model
  results. Never relabel an easy case as complex or rewrite inconsistent upstream ground truth.
- Preserve original dataset/task IDs, immutable revisions, licences and original scoring. Adaptations
  get their own identity and claim scope. Hidden answers and future observations stay outside the
  candidate's accessible inputs and early-turn assessment context.
- At least two incident families remain outside tuning. Useful alternative checks are accepted;
  unknown or ambiguous branch requests release no invented telemetry.
- Existing approved decisions stand: Windows/Docker Desktop for WP-08, the official SWE-bench
  verifier, Harbor for Terminal-Bench, static authoring with independent external-code verification.
- A harder WP-08 selection is a proposed campaign revision requiring owner acceptance before paid
  execution; the previously approved easy-task selection is not silently substituted.
- No model spend, credential provisioning, lab changes or benchmark acceptance follows from offline
  tests. Original supported assessments survive unrelated later cleanup/billing failures.

## Task 1: campaign report

**Files:** `evals/campaign_report.py`, `evals/test_campaign_report.py`, focused synthetic fixtures
when needed, operator documentation and lint/type scope.

**Interface:** `build_report(bundle: Path, selection: Mapping, label: str) -> dict` and
`render_markdown(report: Mapping) -> str`; a standalone CLI emits JSON or Markdown from existing
artifacts. Reporting stays outside the measured runner packages and performs no model, network or
Docker calls. It does not mutate evidence or select an evaluation host.

- Prove missing selected cases, malformed/unsupported records, identity mismatches, duplicate or
  incomplete attempts, and evidence-path escapes remain visible rather than improving counts.
- Preserve original v1 verdicts and separate independent-verifier, execution, cleanup and human
  policy-review dimensions. Report selected/started/completed/measured counts with explicit denominators.
- Keep provider-measured spend separate from CLI estimates; sum only known amounts and disclose
  missing billing, including kept attempts. Do not infer key disablement or human acceptance.
- Link portable evidence and record actual candidate/model/host/profile identities; never populate
  unknown historical identity from the reporting machine or pool incompatible campaigns.
- Test useful clean, failed, interrupted, partially written and mismatched bundles, plus relocation.

## Task 2: finish WP-08 preparation

**Files:** `evals/swebench_adapter/`, its tests, selection/run-plan/operator artifacts.

- Audit current completion requirements against the merged adapter. Preserve supported verification
  results separately from later cleanup/billing failures, using existing v1 fields.
- Prepare a frozen complex-case selection proposal and provenance/licence evidence. Keep pending
  approval explicit when changing the accepted selection recipe or run conditions.
- Validate available local setup and all model-free controls; prepare exact smoke/first-trial/batch
  commands. Live Docker, model availability, budget and acceptance remain explicit gates.

## Task 3: WP-04 incident evidence pilot

**Files:** a focused ITBench adapter/entrypoint, tests, pinned five-case manifest and review packet.

- Inspect immutable ITBench-Lite snapshots and evaluator source; admit five distinct, complex and
  coherent incident candidates. Record exclusions before model results and retain original identities.
- Fetch/stage only allowlisted observable data. Ground truth, recommended actions and evaluator
  aliases remain hidden; verify separation with inaccessible-answer controls.
- Map structured fleet diagnoses into the upstream assessment input without inventing missing claims.
  Original LLM scoring remains unmeasured without its approved judge; any deterministic entity/edge
  score is a separately labelled adaptation, with correct/wrong/unavailable controls.
- Prepare complex operational review criteria and a bounded run plan for exact-candidate approval.

## Task 4: WP-05 native incident conversations

**Files:** native `evals/probe/` conversation seams and their tests; authored cases and hidden review
material under dedicated evaluation paths. Preserve legacy two-message scenarios.

- Introduce an explicit opt-in incident-conversation profile. Generalize ordered invocation storage,
  trace merging, actual session resume, evidence links and rescoring together; retain legacy paths.
- Author twelve paired cases across INC-01 through INC-06. Deliver two-message segments, the complete
  six-message fixed sequence, and branching variants for at least two families.
- Preserve cumulative CLI-turn limits and record per-invocation wall/spend guards accurately. Declare
  helper expectations per invocation; supplied helper evidence is not actual helper execution.
- Persist exact released inputs and assess each response using only evidence visible through that
  point. Semantic review remains separate from structural checks and unavailable until measured.
- Branch through a frozen exact request/alias map with two useful checks, equivalent wording,
  unavailable and ambiguous requests. Future and unchosen observations must never enter candidate
  inputs or early-turn judge context. Accept alternative useful sequences.
- Test complete and interrupted sessions, identity drift, budget exhaustion, branch corrections,
  no leakage, and saved-run rescore parity. Prepare the human case/run acceptance gate.

## Task 5: WP-09 tests and terminal work

**Files:** focused reproduction and Harbor adapters, offline tests, pinned five-plus-five task
manifests, controls and operator/run-plan material.

- Freeze five intrinsically complex SWT-Bench-compatible cases, explicitly distinguishing submitted
  tests, hidden code fixes and upstream dataset field conventions.
- Verify submitted tests independently on buggy and repaired revisions. Reject always-fail,
  unrelated-import-failure, pass-both and patch-text controls. Semantic relevance remains a separate
  human assessment where a mechanical verifier cannot establish it.
- Freeze five supported complex Terminal-Bench coding/tool tasks and pin Harbor's interface/version.
  Reuse the fleet plugin and static-authoring profile; independent actors execute hidden verifiers.
- Prepare native plugin/tool/trace identity, bounded lifecycle, upstream result preservation and
  exact environment/task receipts. Exclude unsupported interactive/production/JVM-authoring tasks.
- Finish deterministic adapters and controls before the live environment and approved-run gates.

## Verification and integration

Use test-first slices with real local components and strict external-boundary doubles; independently
check upstream APIs to avoid accepting imaginary methods. Run focused tests, lint and typing while
editing. Run the coordinated heavy suite once at each material integration/push boundary. Retain
saved-result comparisons and explain verdict changes. Keep one owner per write surface; root owns
cross-package integration, the live roadmap and final acceptance audit.
