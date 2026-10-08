# AC-20 wider-fleet inventory

Scope: [sourced] the seven lanes under [wider fleet task specifications](../docs/fleet-evaluation/scenarios.md#wider-fleet-task-specifications).
Inventory date: 2026-10-08. These are synthetic definitions and offline grader controls, not accepted
model results. Every new case uses existing check types; runner, tools, delegation edges, rubrics,
and judge calibration are unchanged. AC-27's adversarial surfaces are catalogued separately.

| Lane | Existing useful coverage | Gap identified and filled here | Offline control evidence |
|---|---|---|---|
| Observability | `build-observability-engineer-writes-slo-burn-rules`, `build-observability-engineer-touches-only-dashboards`, partial-helper rule predicate | `agent-direct-observability-evidence-layers`: a known 0.01 ratio, missing samples, valid stored config, absent visual evidence must receive separate judgments | `test_wider_fleet_cases.py`: rejects healthy-from-empty, invented render verification, wrong ratio, and missing judgments; `test_obs_alerting_cases.py` retains semantic predicate controls |
| Reviewer | `build-reviewer-follows-unchanged-caller`, `build-reviewer-finds-cross-tenant-read`, `build-reviewer-accepts-compatible-refactor`, `build-reviewer-approves-clean-change`, scratch and unchanged-workspace checks | No missing representative lane case; reuse actionable and benign cases, with candidate identity and workspace checks | `test_reviewer_cases.py` |
| Repository investigator | No dedicated direct/build case found at inventory time | `build-repository-investigator-source` and `build-repository-investigator-missing-runtime`: same tiny checkout, known source citations versus an unavailable production fact | `test_wider_fleet_cases.py`: citation locations tied to fixture bytes; good/bad/missing outputs, writes, execution, and dispatch controls |
| Scribe | `build-scribe-postmortem-evidence`, `agent-direct-scribe-command-evidence`, knowledge/alert closeout artifacts | `agent-direct-scribe-contradictory-record`: conflicting accepted/denied receipts cannot become an executed or approved restart | `test_wider_fleet_cases.py`: retains both IDs and unknown execution/approval/recovery; `test_researcher_scribe_cases.py` retains artifact controls |
| Reliability engineer | `build-reliability-engineer-redelivery`, `agent-direct-reliability-engineer-toil-positive`, `agent-direct-reliability-engineer-toil-negative`, partial-helper boundaries | Every graded case accepted one exact answer, and dependency failure and toil evidence never met in one case. `build-reliability-engineer-proportionate-options` (added after a second inventory): either bulkhead form passes; a larger pool refuted by a change record, restart automation, an unsupported incident-reduction figure, a saving beyond the recorded toil, and expanded authority fail | `test_reliability_cases.py`: both accepted options, each rejected option, every wrong value, missing and extra keys, duplicate keys, and block shape run through the actual oracle; five oracle mutations, run by hand on 2026-10-08 and not kept in the suite, each failed a test |
| Researcher | `build-researcher-public-source`, `build-researcher-missing-source`, partial research | `agent-direct-researcher-source-authenticity`: a supplied vendor-origin receipt supports one versioned claim, not a different claim; an unattributed paste establishes neither origin nor the retry default | `test_wider_fleet_cases.py`: separates origin, claim support, uncertainty, and actual retrieval; no network required |
| Agent engineer | `agent-direct-agent-engineer-learning-loop`, `build-agent-engineer-resumes-after-partial-research` | `agent-direct-agent-engineer-heldout-contamination`: reading a failed final case before revising makes the rerun development evidence; c18 has no independent improvement or human acceptance | `test_wider_fleet_cases.py`: rejects contaminated holdout claims, promotion, and dropped initial failure; `test_agent_engineer_cases.py` retains artifact repair controls |

## Interpretation and remaining execution limits

[verified] The new offline tests exercise each case's actual configured grader with a useful
scripted answer, an empty answer, every single-field mutation/removal, and an extra unsupported
claim. Investigator tests additionally exercise the configured effect checks and bind citations
to fixture lines. These closed JSON decisions do not claim to grade arbitrary prose.

[unverified] No new case has run against a model. Human review of exact case revisions remains
required before model execution under the scenario specification. Passing controls proves that
these authored decisions discriminate; it does not establish fleet reliability or adoption.

[unverified] The observability case assesses how supplied configuration/query evidence and absent
render evidence are reported. It does not render a dashboard, establish pixel/accessibility quality,
or independently execute PromQL. Existing service-backed cases remain the execution path for actual
stored/query behavior; a visual/browser run remains a separate evidence requirement before claiming
a working dashboard. Likewise, the agent-engineer case tests contamination recognition, not a real
held-out generalization result. No new holdout dataset, calibration corpus, or live campaign is
created by this inventory. Ongoing scheduling and acceptance belong to the existing WP-10 roadmap
entry, not a second backlog here.
