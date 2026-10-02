# Reference audit implementation

The owner clarified on 2026-10-02 that the reviewed edits were expected as part of this work.
Implementation starts from published audit commit `8c63128e540758876a3ba314db6a600848fca0bf`.
Fresh fetch confirmed main remains `a2d2e57d2de70125dbde002072853e73b788bd8d` and is an ancestor.
The [audit register](recommendations.md) retains the original findings and proposal measurements;
this receipt records actual changes and fresh verification. Source cleanup does not imply
model-behavior acceptance or promotion.

## Scope and invariants

Apply the 39 implementable records in the original groups of three skill bundles, using the
preferred paired runbook merge and trace-to-pipeline relocation. REF-GCP-02 remains an owner
decision about the real inventory source: retain both placeholder files and their missing-context
read/ask behavior until that location is supplied. Do not invent team records.

Preserve source/version qualifications, task-specific mechanics, independent entry-path safety,
human ownership, scoped Grafana authority, ITO/TLC continuity, UNKNOWN outcomes and no-blind-retry
rules. No frontmatter, runtime tool grants, code, tests, dependencies or live platform state are
part of the selected edits. Regenerate host projections from canonical sources in each group.

## Completed groups

Group results, exact change counts and focused checks are appended before each group commit.
The final receipt reconciles all selected IDs and committed UTF-8 byte deltas.

### Group 01 — agent-authoring, akamai-edge, backend-craft

Implemented REF-AA-01/02/03 and REF-AK-01/02/03 in five canonical references, then regenerated
their host copies. Backend-craft's KEEP decision needs no edit. Actual canonical delta: **−1,573 B**
(artifact −351, Copilot −999, security Contents +213, edge triage −268, mPulse −168).
Copilot's unique pin/adoption/host-verification reasons now live in primary rows; the duplicate
table is gone. The corrected SIEM paragraph preserves replay urgency and retention uncertainty.

[verified] Root inspected the complete source diff. Fenced examples are unchanged and all five
new security Contents anchors resolve. The existing routine-review/promotion contract and
generated-output parity tests passed: **2 tests, 8 subtests**. Adapter generation and diff
whitespace checks passed. These are source/structural checks, not model or Akamai runtime proof.

### Group 02 — ci-actions, database-reliability, eng-ladder

Implemented REF-CI-01, REF-DB-01/02 and REF-EL-01 in four references; regenerated host copies.
Actual delta: **−70 B** (PCF Contents +167, explicit DBA deadline +9, restore footer −119,
principal consumer guidance −127). The deadline clarifies the existing wait limit; all restore
verdicts and accepted-write recovery remain. PCF YAML is byte-for-byte unchanged.

[verified] Root inspected the source diff; new Contents anchors resolve and fenced examples
are unchanged. The PCF asset assertion plus the executable documentation fixture suite passed
**33 tests** against local CF/HTTP fixtures. Adapter generation and diff whitespace checks passed.
These fixture results do not establish actual foundation deployment or database behavior.

### Group 03 — frontend-craft, gcp-ops, grafana

Implemented REF-FE-01/02, REF-GCP-01 and REF-GRAF-01 through 05; REF-GCP-02 remains pending.
Ten references changed, with generated copies refreshed. Actual delta: **+305 B** (frontend/GCP
−182; Grafana −772 in bounded cuts plus +1,259 for four clickable Contents lists). Navigation
exceeded the original estimate; all 24 existing H2 destinations remain reachable. Frontend source
URLs/immutable pins and the two inventory placeholders are unchanged. Grafana retains authorized
organization preflight, selective reads, ownership, optimistic concurrency and UNKNOWN handling.

[verified] Root inspected all source diffs. Fenced examples are unchanged; new anchors resolve.
Generated parity and the existing organization-mismatch helper cases passed **9 tests**; the
latter verifies the existing helper defense, not model compliance with the edited prose.
Link, generation and whitespace checks passed. No actual Grafana/MCP/cloud/browser operation ran.

### Group 04 — incident-investigation, obs-alerting, obs-logs

Implemented REF-II-01 through 04, REF-ALERT-01 and REF-LOG-01 in five references and regenerated
host copies. Actual delta: **+509 B** (incident wording −230 plus helper Contents +180;
Splunk stale aside −37; query-catalog Contents +596). Timing differences now require matching
request identity and timer boundaries before localizing delay. Readback points to the intact
interrupted-attempt rule; UNKNOWN, executor reconciliation and ITO authority remain.

[verified] Root inspected all source diffs. All new Contents anchors resolve; every fenced
example/query, including the single helper reply, is byte-for-byte unchanged. The shipped helper
reply oracle and generated parity passed **2 tests**. Generation, link and whitespace checks
passed. No live query, incident action or model adherence check ran.

### Group 05 — obs-metrics, obs-pipeline, obs-traces

Implemented REF-MET-01/02, REF-PIPE-01/02/03 and REF-TRACE-01 in five references; regenerated
host copies. Actual delta: **−402 B** (WQL −264; PromQL Contents +264; Alloy +207; SDK +16;
Cloud Trace −625). The paired exporter move retains one blank separator, saving 241 B rather
than the proposed 242 B. Transport endpoints, ADC, writer/Service Usage roles, quota project,
source URLs and preview/canary limits now remain with pipeline ownership. PromQL navigation
costs 24 B more than the audit's upper estimate because the links target the existing headings.

[verified] Root inspected all diffs and the paired source/destination. All fenced queries/configs,
including the repaired PowerShell recipe, are unchanged; new Contents anchors resolve. Generated
parity passed **1 test**; generation, links and whitespace checks passed. No telemetry export,
collector validation against a deployed build or model behavior was exercised.
