# Skills reduction audit

The best first reduction is to shorten repeated instructions and repair stale guidance while
keeping the current skill boundaries. Twenty skills have specific trimming candidates; ten are
best kept substantially as they are. No shipped skill was established as unnecessary enough to
retire, and no whole-skill merger is supported by the available evidence.

This is an audit and proposed disposition, not acceptance of a changed skill. The live follow-up
is [SKILLS-001](../fleet-roadmap.md#skills-001--reduce-unnecessary-skill-content-without-lowering-standards).
The four source defects have since been repaired; see the
[repair follow-up](#repair-follow-up). The approved first trimming pass is recorded in the
[three-skill consolidation](#three-skill-consolidation). Inventory counts and original findings
describe the audit baseline, not the later candidates.

## PR integration on the merged base

[verified] PR preparation found that `main` had advanced to `71fb230d`, including the separate
agent-authoring and toil-reduction trims in PRs #415 and #416. The measurements below describe
the original audit candidates; the published branches preserve those already-merged changes.
For the initial repairs, the agent-authoring four-theme compression remains, while the removed
platform section stays removed and MCP limits retain their existing frontmatter-reference owner.
No duplicate MCP paragraph is added to the artifact reference. Against this merged base, the
three entrypoints shrink by 1,550 bytes (CI 991, agent-authoring 81, PCF deploy 478); the separate
correctness repairs add 733 bytes, for a net canonical reduction of 817 bytes.

[verified] The integrated initial candidate passed the same five-file focused trim suite:
175 tests and 587 subtests. `incident-investigation` and its generated bundle remain unchanged
against the merged base. Earlier evidence below remains bound to its recorded source candidate.

## Scope and baseline

[verified] Audited revision: `2ed156b12ec48c384b5f7baeb5ad50569ec9bf02`, observed on 2026-10-23.
The checkout was clean before the audit and remained unchanged through its source inspection and
verification. At audit completion, only this report and its roadmap entry changed. The subsequently
authorized source changes are recorded in the repair follow-up.

| Measured surface | Size |
|---|---:|
| Shipped skills under `skills/` | 30 |
| Skill entrypoints | 215,872 bytes; 30,691 whitespace-delimited words |
| Parsed descriptions across those skills | 14,082 UTF-8 bytes; 1,932 words |
| Tracked entrypoints and bundled files | 167 files; 1,100,086 bytes |

[verified] Read every shipped entrypoint and its text references, inspected the frontend assets,
and inventoried every tracked bundle file. Helper scripts were inspected for purpose, interfaces,
consumers, guard integration and tests; this was not a line-by-line security audit of every helper.
Three separate review slices covered operations, observability/platforms, and engineering; the
invoking session reconciled their findings and ran the checks below.

The audit assessed distinct purpose, routing, conditional loading, duplication, task-sized outputs,
asset consumers, safety boundaries and verification. Repository bytes are not simultaneous model
context: references and scripts are loaded or run conditionally. No token, latency or cost saving
has been measured for a proposed cut. No live usage telemetry was available to prove a skill unused.

Generated adapters were checked as consequences of canonical sources. Installed third-party
skills and sandbox experiments are outside the shipped-skill inventory. The sandbox workflow-graph
skill already has an owner-deferred disposition in
[GRAPH-007](../fleet-roadmap.md#graph-007--promote-or-retire-the-sandbox-workflow-graph-skill);
this audit does not reopen it.

## Corrections to make before broader pruning

These findings are source-confirmed. Their effect on an actual model response remains unverified.

| Priority and confidence | Finding and consequence | Smallest repair |
|---|---|---|
| Medium; high confidence | [verified] [SPL](../../skills/obs-logs/references/spl.md), lines 165–188, groups deploy comparisons by `error_type` and sends readers without that field to a catalog fallback. The [catalog](../../skills/obs-logs/references/query-catalog.md), lines 65–75, sends them back to the same query. The promised overall-rate fallback is absent. | Keep one canonical overall-rate recipe with an optional class breakdown. Preserve eligible-request denominators, status validity, equal windows and explicit missing-data behavior. Remove the circular direction. |
| Low; high confidence | [verified] [Grafana read-only review](../../skills/grafana/references/read-only-review.md), lines 20–25, tells `sre-assistant` to record hygiene as not run. Direct standalone execution is indeed denied, but the [entrypoint](../../skills/grafana/SKILL.md), line 33, and [workflow reference](../../skills/grafana/references/investigation-workflows.md), lines 60–68, provide a guarded `analyze --analysis hygiene` route on a named capture. | Point to the supported capture workflow when its prerequisites are met. Preserve the restriction on arbitrary standalone execution and the distinction between static hygiene and live correctness. |
| Low; high confidence | [verified] [Splunk alerting](../../skills/obs-alerting/references/splunk-alerting.md), lines 21–23, assigns indexing-delay, overlap/deduplication and skipped-run completeness rules to the parent's scheduled-work section. The [parent](../../skills/obs-alerting/SKILL.md), lines 47–57, instead covers job freshness and shared detection failures. | Make the existing short completeness rule self-contained in the Splunk reference; remove its inaccurate ownership claim. Keep the distinct job-freshness guidance. |
| Low; high confidence | [verified] [Frontend error-helper comments](../../skills/frontend-craft/assets/problem.ts), lines 2–8, still describe a universal house API contract. The [accepted owner amendment](../decisions/2026-10-11-frontend-craft-generalized.md#owner-amendment--2026-10-16-service-specific-api-contracts) explicitly makes shared error and replay shapes service-specific. | Describe supported input shapes rather than asserting a universal service policy. Keep the adapter behavior and its tests. |

Passing link checks cannot detect a missing promised recipe or a valid link that points to the
wrong responsibility. These four findings survived the structural checks.

## Reduction candidates in order

Start with repeated prose and stale commentary. Preserve the distinct requirements in each passage;
deleting an entire repeated-looking section without checking its exceptions would be unsafe.

1. **Shorten repeated operational instructions.** [verified]
   [Incident guidance](../../skills/incident-investigation/SKILL.md), lines 63–138, already owns
   the investigation loop and board. The phase table at line 170 and advice/trap tables at lines
   216–241 repeat parts of that method. Collapse repetition while keeping examples that teach a
   unique distinction, the compromise exception and acknowledged handover. Similarly consolidate
   runbook authoring/readback reminders and operational-learning's repeated checkout-binding
   explanations. Keep the full binding requirement once and retain safeguards in copied artifacts.
2. **Reduce eager summaries where conditional references own the detail.** [verified]
   [CI guidance](../../skills/ci-actions/SKILL.md), lines 34–56, repeats much of
   [execution and runners](../../skills/ci-actions/references/execution-and-runners.md), lines
   38–99. Keep a compact invariant summary and its conditional load table. In
   [agent authoring](../../skills/agent-authoring/SKILL.md), lines 146–152, retain the warning
   about omitted tool grants, point to the canonical frontmatter contract, and put detailed MCP
   result-size mechanics beside tool-contract guidance. Keep authority rules visible at entry.
3. **Consolidate nearby checklists.** [verified]
   [Principal guidance](../../skills/eng-ladder/references/principal.md) repeats compatibility,
   recovery and complete-record requirements across its method, record, return checks and done
   criteria. Preserve the complete worked example and unique return checks; shorten repetitions
   around them. PCF deployment similarly repeats plan fields across authority, planning and
   handoff sections. Keep one plan checklist plus concise execution conditions.
4. **Remove small fragments when their unique content has a clear existing home.** [verified]
   The 851-byte [Python guard-clause example](../../skills/python-craft/references/guard-clause-example.md)
   repeats semantics in [refactoring](../../skills/python-craft/references/refactoring.md),
   lines 28–41. It can be merged there while preserving the worked comparison, NaN/zero distinction
   and effect order. The short [Grafana tooling reference](../../skills/grafana/references/agent-tooling.md)
   can move into existing API/tooling guidance if its overwrite warning survives. Remove the empty
   worked-evidence canary stub at the end of the [Alloy reference](../../skills/obs-pipeline/references/alloy.md),
   keeping the preceding actual canary contract. These are reference-level candidates, not skill mergers.

[unverified] These changes should reduce maintenance and reading burden. Their byte savings must
be measured on the actual diff; this audit sets no arbitrary percentage or line-count target.

Three further reductions change selection or output behavior and should be separate from wording cleanup:

- **Question-specific gate output.** [verified]
  [Production change gate](../../skills/production-change-gate/SKILL.md), lines 26–32, distinguishes
  merge, release and production decisions, but lines 63–72 provide one production-shaped verdict.
  Make approver expiry, execution binding, monitoring and production-credential fields conditional
  on the relevant decision. Retain each gate's evidence, identity, verdict and blockers; preserve
  existing approval reuse and every production requirement.
- **Proportionate frontend verification for existing apps.** [verified]
  [Frontend craft](../../skills/frontend-craft/SKILL.md), lines 73–78, requests every view/state,
  both themes and desktop/320 px even though its scope includes small edits. Scope existing-app
  work to affected workflows, relevant states and supported presentations, with broader checks
  for shared components or global styling. Keep full application verification for new apps and
  preserve accessibility, integration and serving standards. Actual work saved is unverified.
- **Load optional details only for their task.** [verified]
  [Lifecycle record transitions](../../skills/service-lifecycle/references/record-transitions.md),
  lines 34–69, mixes resolver-version and acceptance details into a reference used for ordinary
  changes. Resolver use is optional in the entrypoint. Make these details conditional while
  retaining ownership and the three distinct freshness/review/execution dates. Similarly, the
  [stack-profile table](../../skills/stack-profile/SKILL.md), line 56, loads Copilot model detail
  for every broad stack inventory even though line 59 has a specific model-selection trigger.

## Disposition of every shipped skill

The source locations below are [verified]. **Trim** means a concrete content reduction is worth
preparing, not that the skill is unnecessary or its revised behavior has passed evaluation.
**Keep** allows minor wording maintenance but identifies no substantial justified reduction.

| Skill | Disposition | Reduction or reason to retain |
|---|---|---|
| [agent-authoring](../../skills/agent-authoring/SKILL.md) | Trim | Consolidate platform facts and generic taxonomy; retain trust, repair-layer ownership, bounded evaluation and human promotion. |
| [akamai-edge](../../skills/akamai-edge/SKILL.md) | Trim | Shorten first-look instructions repeated in `edge-triage.md`; preserve edge/origin discrimination, WAF ownership, staging and fallback rules. |
| [api-craft](../../skills/api-craft/SKILL.md) | Keep | A 38-line entrypoint with conditional references; HTTP contracts, durable acceptance and client failure semantics are distinct. Some references also serve workers through `software-engineer`. |
| [ci-actions](../../skills/ci-actions/SKILL.md) | Trim | Compress duplicated design guidance; retain required-check enforcement, trust separation, artifact identity and bounded remote-run authority. |
| [database-reliability](../../skills/database-reliability/SKILL.md) | Keep | Conditional engine-specific mechanics, query execution classification, write-preserving recovery and isolated restore evidence are substantive. Missing routing cases do not prove it unused. |
| [eng-ladder](../../skills/eng-ladder/SKILL.md) | Trim | Consolidate principal-reference repetition; preserve routing versus assessment, implementation ownership and the tested complete example. |
| [frontend-craft](../../skills/frontend-craft/SKILL.md) | Trim | Correct stale API comments; consider scoped existing-app verification separately. Preserve accepted per-app identity, kit breadth, accessibility and tested assets. |
| [gcp-ops](../../skills/gcp-ops/SKILL.md) | Trim | Keep a bounded first-look logging command; consolidate specialized filters with `obs-logs`. Make non-Cloud-Run branches conditionally discoverable. Preserve target/output protection and human-owned rollback. |
| [go-craft](../../skills/go-craft/SKILL.md) | Keep | Compact language-specific candidate; retain compatibility, goroutine ownership and cancellation rules. Do not expand before its incremental value is measured. |
| [grafana](../../skills/grafana/SKILL.md) | Trim | Repair the hygiene path and consolidate small tooling/review fragments. Keep guarded helpers, ownership, concurrency, readback, query verification and UNKNOWN reconciliation. |
| [incident-investigation](../../skills/incident-investigation/SKILL.md) | Trim | Consolidate repeated phase/advice prose; retain the board, evidence windows, mitigation constraints, helper reconciliation and sustained recovery. |
| [obs-alerting](../../skills/obs-alerting/SKILL.md) | Trim | Consolidate the repeated readiness reminder; fix the Splunk pointer. Keep paired burn windows, freshness, independent detection and fire/resolve/delivery evidence. |
| [obs-dashboards](../../skills/obs-dashboards/SKILL.md) | Keep | Compact dashboard-design guidance; separate from Grafana implementation and authorization. Keep denominator, population and missing-data distinctions. |
| [obs-logs](../../skills/obs-logs/SKILL.md) | Trim | Repair the overall-rate fallback; remove the output requirement to name the reference read while retaining dialect loading and query/source evidence. Keep extraction and coverage rules. |
| [obs-metrics](../../skills/obs-metrics/SKILL.md) | Keep | Specialized quantile, rate-before-sum, population and missing-data semantics across distinct dialects. Naming the reference read is an optional micro-trim. |
| [obs-pipeline](../../skills/obs-pipeline/SKILL.md) | Trim | Move detailed OTel naming grammar to its existing SDK reference; remove the empty canary stub. Preserve signal-path boundaries, cardinality and real canary verification. |
| [obs-traces](../../skills/obs-traces/SKILL.md) | Keep | Distinct critical-path, nesting, asynchronous-link, sampling and protocol semantics; already permits bounded span interpretation. |
| [operational-learning](../../skills/operational-learning/SKILL.md) | Trim | Consolidate repeated binding/prepared explanations; retain authorized roots, dirty-path protection, evidence provenance and review-versus-execution dates. |
| [operator-cli](../../skills/operator-cli/SKILL.md) | Keep | Capability-based requirements already scale to read-only versus effectful commands; retain machine output, real dry runs, interruption and per-item UNKNOWN. |
| [pcf-deploy](../../skills/pcf-deploy/SKILL.md) | Trim | Consolidate plan fields; retain explicit invocation, human execution, artifact/target identity, approval reuse and phase-specific recovery. Keep separate from read-only PCF operations. |
| [pcf-ops](../../skills/pcf-ops/SKILL.md) | Trim | Fold the separate orientation reminder into target/access guidance. Making all first-look observations conditional is a separate workflow change; retain mandatory target confirmation. |
| [postmortem](../../skills/postmortem/SKILL.md) | Keep | Already supports abbreviated reports, unknown causes and omission of optional empty material; preserve nullable metadata and one owned follow-up record. |
| [production-change-gate](../../skills/production-change-gate/SKILL.md) | Trim | Make output fields decision-specific; preserve the three distinct gates, approval validity, exact identities, execution boundary and UNKNOWN outcomes. |
| [python-craft](../../skills/python-craft/SKILL.md) | Trim | Merge the small guard example and compress generic delivery repetition; preserve Python semantics, actual consumers, resource ownership and installed-artifact checks. |
| [resilience-analysis](../../skills/resilience-analysis/SKILL.md) | Keep | Proportionate prospective failure analysis with distinct risk/gap classifications. Retry timing and resource occupancy address measured historical errors. |
| [root-cause](../../skills/root-cause/SKILL.md) | Keep | Compact diagnosis method with bounded-read exceptions and safe reproduction alternatives; causal repair differs from live incident advice. |
| [runbook](../../skills/runbook/SKILL.md) | Trim | Consolidate authoring/readback repetition; keep standalone approval safeguards, branch-entry checks, staffed escalation, exemplar and no-overwrite import. |
| [service-lifecycle](../../skills/service-lifecycle/SKILL.md) | Trim | Make optional resolver detail conditional. Preserve audit/onboard/retire distinctions, retirement order, retained ownership and freshness/authority controls. |
| [stack-profile](../../skills/stack-profile/SKILL.md) | Trim | Consolidate repeated team boundaries and selectively load model-picker detail; retain canonical owner decisions and explicit runtime uncertainty. |
| [toil-reduction](../../skills/toil-reduction/SKILL.md) | Trim | Merge the duplicated positive-economics walkthrough in `worked-examples.md`; retain uncertainty ranges, the fuller return example and the tested interview/return contracts. |

## Standards that reductions must preserve

[verified] Several apparently repetitive instructions protect standalone use or known failure modes:

- The incident board is an explicit every-turn contract, exercised by the
  [helper reconciliation scenario](../../evals/scenarios/incident-companion-assigns-and-reconciles-helper.yaml).
  Making it optional would be redesign, not deduplication.
- Copied runbooks need their own approval boundary. The
  [runbook schema tests](../../scripts/test_runbook_schema.py) protect it; deleting it because a
  parent skill also says it would weaken the standalone artifact.
- The principal worked example demonstrates every required slot, checked by
  [the principal contract test](../../scripts/test_principal_contract.py). Shorten surrounding
  reminders rather than removing the example.
- Grafana's complete operation loop protects more than syntactic validity. Its
  [authority decision](../decisions/2026-08-21-observability-engineer-unguarded-bash.md) records
  why a short prerequisite list was insufficient. Retain scope, provisioning ownership, fresh
  concurrency, readback, query evidence and ambiguous-outcome reconciliation.
- Frontend kit breadth and per-app identity are explicit
  [owner decisions](../decisions/2026-10-11-frontend-craft-generalized.md). They are not generic
  clutter to remove. The converter, deployment example, frontend helpers and Grafana scripts all
  have current consumers or tests; none was established as an orphan.

Do not replace these contracts with a new universal checklist or a new orchestration layer.
Preserve evidence labels, secret protection, uncertainty, human change authority and supported
contracts while reducing how often the same rule is explained.

## Verification and remaining gaps

[verified] Checks ran on the unchanged audited skill revision with the existing project environment:
Python 3.14.8 and Node 22.23.1. No dependencies were installed and no live model, cloud, Grafana or
Splunk operation was invoked.

| Check | Result and limit |
|---|---|
| `.venv/bin/python scripts/gate_a.py` | PASS, 2/2 structural steps; canonical links, bundle reachability, fleet/plugin contracts and generated adapters. This proves structure, not usefulness or current runtime behavior. |
| `.venv/bin/python evals/build_probe.py validate` | PASS, 373 specs: 178 build, 106 contract, 1 native and 88 routing; 2,136 graded expectations. Scenarios validated offline, not executed. |
| Focused skill asset/helper suites below | 1,230 passed, 273 subtests passed, 34 skipped, 11.93 seconds, exit 0. The skips comprise 23 native-Windows cases and 11 external `sre-context` producer cases. |

Exact focused command:

```bash
.venv/bin/python -m pytest -q -n 4 \
  scripts/test_skill_assets.py scripts/test_runbook_schema.py \
  scripts/test_confluence_import.py scripts/test_service_lifecycle_context.py \
  scripts/test_error_budget.py scripts/test_dashboard_hygiene.py \
  scripts/test_pcf_deploy_example.py scripts/test_frontend_craft_assets.py \
  scripts/test_reliability_contract.py scripts/test_principal_contract.py \
  scripts/test_grafana_alert_preview.py scripts/test_grafana_analyze.py \
  scripts/test_grafana_capture.py scripts/test_grafana_dependencies.py \
  scripts/test_grafana_evidence.py scripts/test_grafana_frames.py \
  scripts/test_grafana_helper_guard.py scripts/test_grafana_modules.py \
  scripts/test_grafana_plan.py scripts/test_grafana_query_transport.py \
  scripts/test_grafana_read.py scripts/test_grafana_vscode.py \
  scripts/test_grafana_workflow.py
```

| Audit requirement | Evidence | Assessment |
|---|---|---|
| Cover the shipped skill inventory | All 30 entrypoints and 167 tracked files accounted for; one disposition per skill | Complete for the stated content/structure scope |
| Identify unnecessary material without deleting expertise | Anchored duplicate passages, stale guidance, narrow reference-consolidation candidates | Concrete candidate list; proposed savings unmeasured |
| Preserve high standards | Consumer/test inspection, passed asset/helper checks, protected contracts named above | Source and tested paths covered; behavior after cuts unverified |
| Establish safe skill retirement or merger | No live usage data; distinct domain and authority contracts remain | Not established; keep all 30 skill boundaries for the first pass |

[verified] Routing coverage is uneven. The current catalog has no direct routing cases for
`database-reliability`, `pcf-ops` or `root-cause`; this is not absence of indirect coverage or use.
[ROUTE-007](../fleet-roadmap.md#route-007--re-check-routing-for-the-descriptions-trimmed-on-2026-09-02)
already records missing positive/negative cases for several skills. The
[Go item](../fleet-roadmap.md#backend-002--add-go-craft-beside-python-craft) explicitly distinguishes
authored cases from measured language-skill benefit. Incident, reliability, principal and lifecycle
acceptance gaps remain owned by their existing roadmap items; historical failures are not a verdict
on today's source.

[unverified] The audit does not establish current vendor/version accuracy, installed-host behavior,
actual skill-selection frequency, real-service lifecycle integration, or performance after pruning.
The audit-baseline engineering-quality verdict was **partial**: the inspected structure and tested
paths passed, but four source inconsistencies remained and proposed reductions had no behavioral
acceptance. The follow-up records their repair; it does not supply live behavioral acceptance.

The recommended first candidate repairs the four inconsistencies and consolidates a small set of
repeated passages without changing routing, authority or mandatory output contracts. Measure its
byte delta, regenerate adapters, and run matching checks. Verify the repaired query's denominator
and missing-field behavior before claiming it usable. Keep gate/frontend/loading-policy changes
separate so their effects can be assessed. No new live campaign, skill retirement or promotion is
authorized by this report; human acceptance remains tied to the exact candidate revision.

## Repair follow-up

[verified] The human requested repairs to all four defects. Repair baseline:
`bebbc116cd0814d1f362fcff0c45b4a82149f66c`; candidate: the working-tree diff from that revision.
The six repair source/scenario files have combined SHA-256
`47e5aa51435099d3a01a8c2fad3fe82ac35dbc9159ec040ac071c2d4fd0779f9`
(sorted repository-relative paths, each encoded as path, NUL, file bytes, NUL).
The intervening stack-profile trim and observability-engineer changes were preserved. The
stack-profile repetition identified in the original audit has already been partly reduced by
`bebbc116`; its broad-inventory model-reference loading remains a separate candidate.

| Defect | Implemented repair |
|---|---|
| Missing overall deploy-rate fallback | The SPL reference now owns a complete query grouped only by phase, plus an optional class-breakdown substitution. The catalog links directly to it. Missing/invalid status still keeps the rate unknown, and the class variant retains its phase-wide denominator. |
| Grafana hygiene falsely recorded as unavailable | The review names guarded `analyze --source-id <capture-id> --analysis hygiene --agent-json`; direct standalone execution remains denied for `sre-assistant`. Missing capture/access and unsupported V2 checks remain explicit gaps. |
| Splunk scheduling ownership mismatch | The indexing allowance, late-arrival overlap/deduplication and skipped-run checks are stated locally. The incorrect parent-section attribution is removed. |
| Universal frontend API-contract comments | Comments describe supported response formats and adapting to the actual service contract. Executable TypeScript is unchanged. |

[verified] Extended the existing
[log comparison scenario](../../evals/scenarios/obs-logs-spike-deploy-contract.yaml) with the
missing-error-class decision; no new scenario or evaluator machinery was added. A source-shape
probe failed on the baseline because no complete overall query was independent of `error_type`,
then passed after repair. It also checked preservation of the overall denominator, invalid-status
guard and optional class denominator. This is a structural check, not execution by Splunk.

[sourced] The count/conditional-count construction was checked against Splunk's
[aggregate-function reference](https://help.splunk.com/en/splunk-enterprise/search/spl-search-reference/9.4/statistical-and-charting-functions/aggregate-functions)
and [stats reference](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/9.2/search-commands/stats).
Target Splunk execution remains unverified.

[verified] Fresh repair checks:

- `.venv/bin/python -m pytest -q -ra -n 4 scripts/test_grafana_helper_guard.py scripts/test_grafana_workflow.py scripts/test_skill_assets.py evals/test_probe_catalog.py evals/test_graders.py`:
  408 passed, 1,146 subtests passed, one native-Windows test skipped; exit 0.
- `node --test problem.test.ts` from the frontend assets directory: all nine tests passed.
- `.venv/bin/python evals/build_probe.py validate`: all 373 scenarios validated offline.
- `.venv/bin/python scripts/generate_platform_adapters.py --write`: adapters regenerated;
  only the five changed canonical files produced projection diffs.
- `.venv/bin/python scripts/gate_a.py`: final PASS, both structural steps green.
- `git diff --check`: passed. The five canonical repairs add 733 UTF-8 bytes, principally to
  supply the missing query variant and the supported guarded workflow; this is a correctness
  repair, not a measured reduction.

[verified] Independent source review found no actionable issues in the six repair files. The
first structural run rejected the new SPL section fragment: the existing link checker's fence
parser mistakes embedded triple-backtick SPL comments for closures of four-backtick Markdown
fences. The catalog now uses a file-level link and names the section explicitly; regeneration and
Gate A then passed. This link-only adjustment did not change the query or require repeating the
passed behavioral suites. The checker limitation remains outside these four repairs.

No live model evaluation or production-system check was run. The new scenario is ready for a
separately selected evaluation; passing its schema does not prove a model follows the guidance.

The human subsequently selected the CI, agent-authoring and PCF-deploy consolidation below.
The two small reference mergers remain proposed. Question-specific gate output, frontend
verification scope and optional loading changes remain separate behavioral decisions. The
incident board and existing authorization, recovery and evidence requirements remain protected.

## Three-skill consolidation

[verified] The human approved audit recommendation 1: remove repeated guidance from `ci-actions`,
`agent-authoring` and `pcf-deploy`, preserving workflows and standards. The candidate changes four
canonical files against `bebbc116cd0814d1f362fcff0c45b4a82149f66c`; prior repairs remain byte-identical
to their recorded combined hash. These four files have combined SHA-256
`28d989bf2c275626572df616934eea4867e7aba7c44fe62b6ba2f46132cb8cc7`, using the same path/NUL/bytes/NUL
encoding described above.

| Canonical file | Before bytes | After bytes | Reduction |
|---|---:|---:|---:|
| `ci-actions/SKILL.md` | 7,387 | 6,396 | 991 |
| `agent-authoring/SKILL.md` | 12,730 | 12,066 | 664 |
| `agent-authoring/references/artifact.md` | 5,578 | 6,080 | −502; existing detail relocated here |
| `pcf-deploy/SKILL.md` | 8,609 | 8,131 | 478 |
| **Total** | **34,304** | **32,673** | **1,631** |

The three entrypoints alone shrink by 2,133 bytes (7.4%) and 339 whitespace-delimited words.
The net reduction includes the 502 bytes moved into the existing artifact reference. No skill or
reference was removed, and these byte counts do not establish token or latency savings.

[verified] Retained-rule mapping:

- **CI:** compact entrypoint guidance retains coverage, reproducible installs, first-failure
  visibility, cache-miss correctness and justified abstractions. Existing conditional references
  own detailed matrix, cache, artifact, cancellation and security rules. The verification,
  bounded remote-run authority and output sections are byte-identical to the baseline.
- **Agent authoring:** the four themes are expressed once in prose. Accepted/inert platform keys
  remain in the canonical frontmatter reference; the warning about omitted tool grants and scoped
  hook wiring stays in the entrypoint. Existing MCP result-size detail moves beside tool contracts.
  Evaluation, promotion, source-trust and handoff requirements remain intact.
- **PCF deployment:** one checklist supplies draft, approval and handoff fields. Manual invocation,
  agent non-execution, incident/full-gate distinctions, approval reuse and action-boundary
  revalidation remain explicit. Rollback, conditional references, strategy constraints and
  post-cutover observations/abort conditions are unchanged.

[verified] All three frontmatter blocks are byte-identical. Generated adapters were refreshed from
canonical sources. Fresh focused verification:

```bash
.venv/bin/python -m pytest -q -ra -n 4 \
  scripts/test_validate_fleet.py scripts/test_skill_assets.py \
  scripts/test_pcf_deploy_example.py scripts/test_platform_adapters.py \
  evals/test_probe_assessment.py
```

Result: 175 tests and 587 subtests passed, none skipped; exit 0, 7.57 seconds.
`scripts/gate_a.py` passed both structural steps, and `git diff --check` passed. Independent
working-tree source review of the four canonical files found no actionable issues; generated
projections and documentation were outside that review and covered by the caller's checks.

[unverified] No live model evaluation was run for this prose consolidation; source preservation
and passing contracts do not prove identical model behavior. The reference mergers, task-sized
gate/frontend output changes and broader skill retirement remain outside this approved pass.
