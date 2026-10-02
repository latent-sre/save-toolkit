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
| 03 | Skills | `fleet-atlas`, `frontend-craft`, `gcp-ops` | Planned |
| 04 | Skills | `grafana`, `incident-investigation`, `obs-alerting` | Planned |
| 05 | Skills | `obs-dashboards`, `obs-logs`, `obs-metrics` | Planned |
| 06 | Skills | `obs-pipeline`, `obs-traces`, `operational-learning` | Planned |
| 07 | Skills | `operator-cli`, `pcf-deploy`, `pcf-ops` | Planned |
| 08 | Skills | `postmortem`, `production-change-gate`, `python-craft` | Planned |
| 09 | Skills | `resilience-analysis`, `root-cause`, `runbook` | Planned |
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
