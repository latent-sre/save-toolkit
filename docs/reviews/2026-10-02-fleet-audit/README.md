# Skill and agent audit findings

This audit reviews all 30 canonical skills followed by all 9 canonical agents for correctness,
suitability, improvement opportunities, LLM readability and verification quality. The human owner
requested six passes per asset, groups of three, and a findings commit before each next group.
Reports record findings and proposed repairs; acceptance and implementation decisions remain with
the owner.

**Review complete:** 30 skills and 9 agents received six documented analytical passes each
(234 passes), in 13 groups. The reports contain 50 distinct confirmed findings, with optional
recommendations, policy choices and unverified runtime behavior kept separate. Each group was
reviewed and its findings committed before work began on the next group.

**Selected repairs:** Thirty-eight findings are implemented and locally verified, with no open
material independent review findings. The [first sixteen repairs](selected-fixes.md) and
[third](selected-fixes-batch-03.md) and [fourth batches of eleven](selected-fixes-batch-04.md)
retain their dispositions and evidence. Latest full-suite verification passed 1,711 tests and
3,192 subtests; 19 environment/opt-in checks were skipped. Live model calibration and
target-platform behavior remain unverified. The other 12 confirmed findings are unchanged,
and the reports below retain their original audit-baseline meaning.

## Exact source and scope

- [verified] Fresh `git fetch origin main` on 2026-10-02, then an isolated worktree and branch
  `work/fleet-audit-20261002` from `origin/main` at
  `a2d2e57d2de70125dbde002072853e73b788bd8d`.
- The original `F:/repos/sre-agents` checkout contains unrelated uncommitted work. The audit uses
  `F:/repos/sre-agents-audit-20261002` and does not depend on those changes.
- Alphabetical order within skills, then alphabetical order within agents. Bundled references,
  assets, scripts and templates are part of each skill's scope. Consumers, generators, guards and
  evaluations are inspected where they determine the asset's behavior.
- Canonical behavior is frozen at the source revision above. Subsequent audit commits contain
  findings and the roadmap reference required to retain them, not repairs to reviewed assets.

## Six review passes

| Pass | Question | Evidence expected |
|---|---|---|
| 1 Suitability | Does this asset solve the intended SRE or engineering task, select the right lane and serve its human and agent readers? | Entrypoint, trigger, exclusions, consumers and neighboring responsibilities |
| 2 Correctness | Are instructions, examples, APIs and factual claims correct for the stated environment? | Full bundle, local implementation and current primary documentation where facts are uncertain or volatile |
| 3 Workflow and authority | Does the procedure preserve trust, ownership, approvals, secrets, failure handling and recovery? | End-to-end workflow, available tools, guard boundaries and counterexamples |
| 4 LLM readability | Can a model retrieve the right rule and follow it without ambiguity, contradictions or unnecessary context? | Instruction order, references, repeated rules, output contracts and context footprint |
| 5 Verification | What do existing tests and evaluations establish, and would their oracles catch the named failure? | Test source, fresh offline results, negative cases and explicit runtime gaps |
| 6 Challenge and improvement | Do findings survive skeptical counterexamples, and what is the smallest useful improvement? | Adversarial cases, claim reconciliation, deletion-first alternatives and prioritized recommendations |

Three bounded reviewers inspect the three assets in a group. Each performs all six passes; the
caller reviews their evidence, resolves disagreements, runs shared verification and commits the
completed group before dispatching the next. These are six analytical passes, not six paid model
campaigns or six claims of independently measured runtime success.

## How to read the findings

`[verified]` means fresh local source or executable evidence establishes the stated, bounded claim.
`[sourced]` means a cited primary external source establishes its contract. `[unverified]` identifies
behavior or applicability that has not been established. Static proof is labeled as static proof;
it is not live platform or model evidence.

Confirmed defects include a concrete trigger, consequence, source location, severity and confidence,
the smallest fix direction and its verification. Recommendations are optional improvements;
policy choices need an owner decision; runtime gaps need the named environment or experiment.
No finding count is required. A clean review still records strengths and what remains untested.

Additional audit questions cover stale facts, impossible tool instructions, handoff loss, prompt
injection and misleading evidence labels, test oracles that only check words, excessive mandatory
output, conflicting human/agent guidance, recoverability and duplication across skills.
Context reduction is proposed only where it preserves useful safeguards and demonstrated behavior.

## Progress and reports

| Group | Kind | Assets | State |
|---|---|---|---|
| 01 | Skills | [agent-authoring](group-01-agent-authoring.md), [akamai-edge](group-01-akamai-edge.md), [backend-craft](group-01-backend-craft.md) | Six passes complete |
| 02 | Skills | [ci-actions](group-02-ci-actions.md), [database-reliability](group-02-database-reliability.md), [eng-ladder](group-02-eng-ladder.md) | Six passes complete |
| 03 | Skills | [fleet-atlas](group-03-fleet-atlas.md), [frontend-craft](group-03-frontend-craft.md), [gcp-ops](group-03-gcp-ops.md) | Six passes complete |
| 04 | Skills | [grafana](group-04-grafana.md), [incident-investigation](group-04-incident-investigation.md), [obs-alerting](group-04-obs-alerting.md) | Six passes complete |
| 05 | Skills | [obs-dashboards](group-05-obs-dashboards.md), [obs-logs](group-05-obs-logs.md), [obs-metrics](group-05-obs-metrics.md) | Six passes complete |
| 06 | Skills | [obs-pipeline](group-06-obs-pipeline.md), [obs-traces](group-06-obs-traces.md), [operational-learning](group-06-operational-learning.md) | Six passes complete |
| 07 | Skills | [operator-cli](group-07-operator-cli.md), [pcf-deploy](group-07-pcf-deploy.md), [pcf-ops](group-07-pcf-ops.md) | Six passes complete |
| 08 | Skills | [postmortem](group-08-postmortem.md), [production-change-gate](group-08-production-change-gate.md), [python-craft](group-08-python-craft.md) | Six passes complete |
| 09 | Skills | [resilience-analysis](group-09-resilience-analysis.md), [root-cause](group-09-root-cause.md), [runbook](group-09-runbook.md) | Six passes complete |
| 10 | Skills | [service-lifecycle](group-10-service-lifecycle.md), [stack-profile](group-10-stack-profile.md), [toil-reduction](group-10-toil-reduction.md) | Six passes complete |
| 11 | Agents | [agent-engineer](group-11-agent-engineer.md), [observability-engineer](group-11-observability-engineer.md), [reliability-engineer](group-11-reliability-engineer.md) | Six passes complete |
| 12 | Agents | [repository-investigator](group-12-repository-investigator.md), [researcher](group-12-researcher.md), [reviewer](group-12-reviewer.md) | Six passes complete |
| 13 | Agents | [scribe](group-13-scribe.md), [software-engineer](group-13-software-engineer.md), [sre-assistant](group-13-sre-assistant.md) | Six passes complete |

## Cross-fleet conclusions and proposed repair order

The audit supports retaining the fleet's role separation, conditional skill loading, bounded
handoffs, and distinction between evidence and authority. Several assets have no confirmed defect;
their reports still record useful improvements and the behavior that remains unmeasured. A large
share of the confirmed findings concern evaluators that accept an invalid result or reject a valid
one. Passing those checks cannot establish the stronger behavior their descriptions claim.

The following order helps the owner select repairs under AUDIT-001. It does not change the severity
or evidence limits of any individual finding, and it does not create a second backlog.

| Repair theme | Why it matters | Smallest useful next step |
|---|---|---|
| Read-only command enforcement | The SRE command guard allows Git stash/reflog output-file options that create or overwrite local files, despite blocking the equivalent ordinary diff option. | Apply the same effect-option rejection to every permitted Git form and retain both Bash/PowerShell decisions plus disposable-file controls. See [SRE-01](group-13-sre-assistant.md). Recheck the installed hook separately. |
| Executable helpers and boundary arithmetic | The runbook converter can overwrite a concurrently created file or join separate commands; the burn calculator mishandles an inclusive threshold; a PowerShell recipe can alter Unicode input. | Repair the specific operations and retain the reproduced positive, negative, and boundary controls. See [RUN-01/02](group-09-runbook.md), [OA-01](group-04-obs-alerting.md), and [PIPE-02](group-06-obs-pipeline.md). |
| Operational conclusions and current facts | Incorrect timing localization, log-freshness inference, trace provenance, rollout scope, and heap advice can steer an investigation or change proposal incorrectly. | Correct the stated decision rule and add one discriminating counterexample for each, using the primary sources already cited. See [incident investigation](group-04-incident-investigation.md), [logs](group-05-obs-logs.md), [traces](group-06-obs-traces.md), [deployment](group-07-pcf-deploy.md), and [PCF operations](group-07-pcf-ops.md). |
| Evidence and outcome binding in evaluators | Several checks accept the right words, a successful exit, an unrelated artifact, final-state equality, or a mismatched query as proof of the intended result. | Calibrate each reported counterexample against the actual predicate before relying on a fresh native run. Preserve controls that already reject invalid behavior. Examples include [CI-01](group-02-ci-actions.md), [PY-02/03](group-08-python-craft.md), [GRA-02/03](group-04-grafana.md), [OE-01](group-11-observability-engineer.md), and [REV-01](group-12-reviewer.md). |
| Conflicting authority and tool contracts | Some fixtures contradict required security review or approval evidence; some guidance overstates guard scope or assumes an older workflow/tool name. | Reconcile the owning contract, dependent fixtures and validator registry together. Preserve the existing human acceptance and ownership boundaries. See [BC-01](group-01-backend-craft.md), [GATE-01](group-08-production-change-gate.md), [GP-01](group-03-gcp-ops.md), [LEARN-02](group-06-operational-learning.md), and [researcher](group-12-researcher.md). |
| Readability and context cost | Much of the useful complexity expresses real authority, recovery, or evidence distinctions. Generic repetition adds cost without strengthening those controls. | Make targeted deletions in the owning layer, report byte/line deltas, and compare relevant outputs. Preserve unique safeguards; avoid a fleet-wide wording rewrite without measured benefit. |
| Host and model acceptance | Canonical files, generated parity and offline tests cannot prove installed tool resolution, nested delegation limits, safe execution, correct reasoning, or target behavior. | Select a small exact-candidate acceptance slice with explicit host, budget, stop conditions and manual trace review after relevant oracle repairs. Existing acceptance gates remain open. |

## Recommended next-audit improvements

1. Keep a compact contract-to-evidence map: each material instruction names its positive case,
   invalid counterexample, owning predicate, and remaining manual or native check. Use the current
   reports as evidence rather than duplicating their findings into a second task queue.
2. Add counterexamples before expanding prompt rules. Test wrong identity, stale evidence,
   missing fields, quoted refusals, returned-versus-raised errors, wrapper commands, and transient
   writes where the contract depends on those distinctions. A check should prove its named claim.
3. Record successful retrieval and exact source identity separately from tool-call attempts.
   Keep documented vendor behavior, upstream implementation, inspected checkout bytes and observed
   runtime behavior distinct through every handoff.
4. Refresh tool inventories and volatile external facts when a server, host, dependency or owning
   platform changes. An exact reviewed pin or checked date makes a future comparison possible;
   a floating source or a remembered capability does not.
5. Evaluate compression as a candidate change: remove duplicated generic material first, preserve
   evidence-backed safeguards, and compare matching tasks under the same conditions. Fewer words
   alone are not proof of better adherence.
6. Budget native work by the decision it needs to settle. Start with corrected high-impact checks
   and representative task/return behavior; retain inconclusive results, manual trace failures,
   missing target evidence and independent human acceptance requirements.

## Group 01 adjudicated findings

[verified] All three complete reports were read and reconciled by the caller. The group contains
six confirmed findings: AA-01 and AA-02 concern reference provenance and calibration evidence;
AA-03 and AA-04 are smaller authoring/delegation contradictions; BC-01 is the security-review
policy conflict; BC-02 covers the reproduced HTTP-shape false positives. The owner-lookup
substring weakness is a verified verification improvement under BC-R01. No material Akamai
correctness defect was confirmed. Separate recommendations cover context reduction and decision
coverage; live-platform gaps remain explicitly unverified.

The caller directly inspected the contested validators, calibration rubric, reference-read path,
webhook fixture, reviewer rule and HTTP assets. It reproduced the path-identity and HTTP predicate
counterexamples. The reports qualify what each result establishes and retain useful controls.

## Group 02 adjudicated findings

[verified] Two additional confirmed evaluator defects survived source review and executable
counterexamples: CI-01 credits an artifact download without binding the deployment path to it;
EL-01 accepts contradictory extra prose around a correct recovery decision packet. Both reports
state their individual-predicate scope and retain rejecting controls. Missing CI authentication is
recorded as a narrower coverage recommendation because a different validated authentication path
can be legitimate. No material database-guidance correctness defect was confirmed.

Recommendations favor small clarifications: synchronize accepted writes throughout backfill,
make concurrent-index completion/cancellation criteria explicit, distinguish illustrative horizons
from routing predicates, and measure a bounded consultation/return sequence when needed. Existing
engine-version qualifications, preserved-write recovery and human execution boundaries remain
strengths. Database upstream source indexing was incomplete; the report relies on identified
primary documentation and labels actual engine behavior unverified.

## Group 03 adjudicated findings

Five confirmed findings have bounded evidence: FA-01 is the advertised atlas path-query mismatch;
FA-02 is ignored canonical input bypassing snapshot rejection; FE-01 and FE-02 concern UI-state
visibility and missing filter-result assertions; GP-01 overstates the scope of two guard flags.
The caller reproduced both atlas cases and the two-lane/two-shell guard matrix. The UI cases rest
on inspected predicates plus current primary query documentation, with full mutant execution
explicitly unverified because fixture dependencies are unavailable.

The seven-command atlas contract passed in a detached checkout of the original source revision,
separating baseline behavior from this audit's changing roadmap/evidence inputs. Correcting FA-02
must preserve intended cache/generated exclusions; simply removing Git's ignore handling would
create another problem. Recommendations cover verification-link meaning, source-corpus scope,
oversized results, conditional readiness probes and present-state rollback compatibility.

## Group 04 adjudicated findings

Eight confirmed findings survived reconciliation. GRA-01 is the malformed-input diagnostic/exit
contract; GRA-02 and GRA-03 are false acceptance of different queries and failed/null-only data.
II-01 incorrectly localizes a timing gap outside the container without establishing timer boundaries.
OA-01 is the exact-threshold floating-point inconsistency; OA-02 erases PromQL `bool` semantics;
OA-03 conflates Prometheus rules with Grafana file-provisioning input; OA-04 contradicts Splunk
suppression-group scope. The caller independently executed the applicable helper and predicate
counterexamples. II-01 is a constructed timing counterexample, while schema/semantic claims are
supported by identified primary documentation and upstream source, not live-platform execution.

Recommendations preserve the useful safeguards while tightening rollback interleavings, clarifying
unsaved time-picker actions, labeling diagnostic excerpts and removing obsolete fixture wording.
The existing incident-quality runtime gate remains open. No Grafana query/write, alert delivery,
Prometheus engine run or native model campaign was performed.

## Group 05 adjudicated findings

Three confirmed findings remain after reconciliation. DASH-01 is the missing requested-quantile
check: the actual panel/query predicates accept a median calculation labeled p95. LOG-01 omits
case-sensitive Cloud Logging payload keys; LOG-02 overstates what an event-time-bounded freshness
query establishes about current ingestion. The dashboard issue has an executed positive/mutant/
negative-control comparison. The log defects have inspected source plus current primary contracts
and explicit constructed counterexamples; no backend search was executed.

No new confirmed metrics defect was established. Recommendations cover bounded gap filling,
backend-specific query behavior, precise datasource/authentication applicability, actual per-signal
routing, scrape-evidence scope and decision-level coverage. Existing Grafana/alerting oracle defects
are cross-referenced rather than counted again. Inventory, live data and native model behavior
remain unverified.

## Group 06 adjudicated findings

Six confirmed findings survived review. PIPE-01 corrects an obsolete service-maturity claim while
preserving the independently preview Alloy component; PIPE-02 records UTF-8 corruption in the
PowerShell 5.1 native-stdin validation path. TRACE-01 separates Cloud Run platform traces from
application-exported spans; TRACE-02 distinguishes recording from the sampled flag. LEARN-01 is
the reproduced detached-provenance oracle gap; LEARN-02 reconciles API-owned alert definitions
with documentation that currently assumes repository ownership.

The caller executed the shell-encoding and closeout-oracle controls and inspected the internal
ownership conflict. Product/SDK claims are bounded to current primary sources; no Alloy, trace
backend or native model was executed. The Tempo size-limit documentation disagreement remains a
version-qualification recommendation pending implementation/target evidence. Proposed repairs
preserve no-data uncertainty, exact KB checkout binding, human review and production boundaries.

## Group 07 adjudicated findings

Four bounded findings survived adjudication. CLI-01 is the reproduced EOF traceback/refusal-exit
problem. CLI-02 is a missing definitive-rejection precondition at the copyable client seam; the
provided stub is valid, so this remains a Low documentation finding rather than a demonstrated
production-client failure. DEPLOY-01 qualifies rolling/canary bounds by process type and app state.
PCF-01 corrects the absolute prohibition on adjusting a fixed heap when that heap causes the
calculator's total-memory overflow.

The caller ran the real CLI prompt/test path with yes/no/EOF controls and the conditional
applied-then-error seam comparison. PCF conclusions use inspected guidance and identified primary
contracts, without CF, JVM or foundation execution. Recommendations address adapter applicability,
cooperative-lock wording, receipt responsibility, process-level plan tests and target evidence.
Backfill synchronization and previously recorded oracle weaknesses retain their existing IDs.

## Group 08 adjudicated findings

Four confirmed evaluator/fixture findings survived adjudication. GATE-01 is an expected approval
without the explicit expiry required by the skill; the scheduled action time does not supply that
missing deadline. PY-01 falsely rejects permitted fixed-buffer streaming on a tiny input; PY-02
credits process success after an early candidate SystemExit; PY-03 erases the distinction between
returning an error string and raising the required exception. The caller executed all three Python
counterexamples with valid and rejecting controls against the actual oracle entrypoints.

No new postmortem defect was confirmed. Its accepted completed-follow-up mutation establishes a
disclosed coverage limit and remains a recommendation. The gate's incident-deferral wording also
remains a clarification recommendation, without claiming a proved authority bypass. Small repairs
should strengthen oracle calibration and fixture completeness before interpreting native outcomes;
the existing evidence, recovery and human-ownership controls remain useful.

## Group 09 adjudicated findings

Three confirmed findings survived review. RCA-01 is a missed compatibility regression: exact-class
TimeoutError handling passes the current behavior checks while breaking the existing subclass
policy. RUN-01 is the converter's non-atomic default no-overwrite check; RUN-02 silently joins
HTML code lines separated by br elements. The caller reproduced each against actual fixture/oracle
or converter code with positive and rejecting controls, using only owned temporary inputs.

No new resilience-analysis defect was confirmed. Its recommendations concern required method-load
coverage and failure-capacity/recovery examples. Explicit converter force replacement is intentional
and stays a documentation/policy recommendation, separate from the unforced race. Root-cause manual
reasoning acceptance, operational drills and native host/model behavior remain open evidence layers.
Preserve the existing uncertainty, bounded investigation and human execution boundaries.

## Group 10 adjudicated findings

One confirmed finding remains: STACK-01 is the support-only-stack evaluator accepting ordinary
wrapped Java/Maven execution attempts that it claims to exclude. The caller ran the actual
predicate over nine synthetic Bash/PowerShell cases; direct forbidden commands failed, common
wrappers passed, and permitted discovery/version controls remained accepted. No command under
review was executed.

No new service-lifecycle or toil-reduction defect was confirmed. Lifecycle's focused verification
passed its two local checks and explicitly skipped all eleven external-producer cases; compatibility
with a selected producer remains unverified. Recommendations cover retirement quiescence, mode
clarity, cost/demand uncertainty and useful lifetime, alongside narrow stack-policy clarifications.
Team choices remain policy and provisional inventory; external documentation does not prove private
live configuration. All thirty skills have now completed their six review passes.

## Group 11 adjudicated findings

[verified] All three agent reports were read and adjudicated by the caller. Three bounded evaluator defects survived controlled counterexamples: AE-01 (Low) accepts a leading blank line that the strict frontmatter parser rejects; OE-01 (Medium) credits no forbidden edits after a successful write and restoration; RELI-01 (Low) rejects an explicit refusal because it quotes an authorization phrase. The valid and invalid controls and execution limits are recorded in the shared verification record. None is evidence that a native agent performed the constructed behavior.

The current agent bodies and generated projections preserve their intended ownership boundaries. Broad shell/write tools and nested delegation still have the documented cooperative or host-dependent limits; file presence is not proof of current Codex registration. AE-R01 reconciles the stale non-author approval field as a recommendation, since the actual body and validator require exact-revision human acceptance. Other recommendations prioritize graph-design and operation-specific verification and deletion of generic design duplication. Existing shared skill findings remain cross-referenced rather than recounted as new defects.

## Group 12 adjudicated findings

[verified] All three complete reports were read and adjudicated by the caller. Three findings remain: RS-01 (Low) records the stale GitHits code_grep operation grant and validator entry against the observed current grep contract; REV-01 (Medium) shows that path-qualified and env-wrapped Python runs evade the outside-checkout predicate; REV-02 (Low) shows that LF-to-CRLF changes evade the promised byte-preservation check. The latter two were reproduced against actual predicates with controls. RS-01 is qualified to the observed provider tool set; native Claude resolution was not tested.

No new defect was confirmed in repository-investigator. Its direct behavior coverage, caller-supplied dirty-state evidence, and fallback-host local-effect controls remain recommendations. Researcher recommendations cover privacy across MCP calls and binding successful retrieval to supported claims. Reviewer recommendations and shared findings retain their exact scope. The candidate source remains unchanged, and none of these checks supplies native model, sandbox, or production acceptance.

## Group 13 adjudicated findings

[verified] All three final agent reports were read and adjudicated by the caller. SRE-01 (Medium) is a command-guard enforcement defect: stash/reflog output-file options pass both Bash and PowerShell checks and were shown to create and overwrite owned files in a disposable Git repository. SE-01 (Medium) is a bounded evaluator defect: fabricated artifact creation in passive or bare-voice wording passes all five no-tools scenario graders, while the equivalent first-person claim fails. The reports and shared verification record preserve their positive/negative controls and native-host limits.

No distinct defect was confirmed in scribe. Its recommendations concern closeout-binding and evidence negatives, method-loading coverage, and targeted prose consolidation. Software-engineer retains the full diagnosis loop, stack boundaries and independent-review conditions; current source policy governs deployment preparation. SRE browser and credential-output controls retain their stated cooperative limits, and successful protected observations still need target-bound receipts. Previously recorded skill/agent findings are cross-referenced, not counted again. All 39 assets now have six documented analytical passes.

## Verification record

Shared baseline checks and group-specific reproductions are recorded in [verification](verification.md).
Green structural or offline checks do not establish live cloud, browser, installed-host enforcement,
model instruction-following or human acceptance. Existing roadmap items retain those distinctions.

## Disposition and retention

The live `AUDIT-001` item in `docs/fleet-roadmap.md` owns completion and disposition. This packet is
review evidence, not a second backlog. Keep it while the owner is selecting or resolving these
findings; retire it when accepted repairs and explicit deferrals/dispositions no longer depend on
its measurements, preserving history in Git. Findings already covered by a live item should link
that item rather than create a duplicate queue.
