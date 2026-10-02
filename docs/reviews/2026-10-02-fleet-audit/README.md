# Skill and agent audit findings

This audit reviews all 30 canonical skills followed by all 9 canonical agents for correctness,
suitability, improvement opportunities, LLM readability and verification quality. The human owner
requested six passes per asset, groups of three, and a findings commit before each next group.
Reports record findings and proposed repairs; acceptance and implementation decisions remain with
the owner.

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
| 10 | Skills | `service-lifecycle`, `stack-profile`, `toil-reduction` | Planned |
| 11 | Agents | `agent-engineer`, `observability-engineer`, `reliability-engineer` | Planned |
| 12 | Agents | `repository-investigator`, `researcher`, `reviewer` | Planned |
| 13 | Agents | `scribe`, `software-engineer`, `sre-assistant` | Planned |

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
