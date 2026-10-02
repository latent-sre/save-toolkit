# Reference necessity and context-cost audit

Date: 2026-10-02. Human owner: the user; review and integration caller: `/root`.
This packet supports `AUDIT-001` in the [live roadmap](../../fleet-roadmap.md).
It records recommendations, not permission to remove guidance or accept model behavior.

**Implementation follow-up:** the owner subsequently clarified that edits were expected.
The [implementation receipt](implementation.md) tracks application and verification separately
from this frozen audit snapshot and its original proposal measurements.

**Complete:** all 103 references reviewed. [Consolidated recommendations](recommendations.md)
record **74 KEEP, 26 TRIM, one paired MERGE and two CONDITIONAL inventories**. No unconditional
deletion is supported. The 40 records comprise two documentation correctness defects, seven
navigation-convention records, 30 optional recommendations and one shared ownership decision.
Only audit documents and this item's roadmap entry changed; canonical guidance remains intact.

## Target and method

The frozen target is `c7fdbe314c95f6bbe29b11519214c30655322ba1`, containing the 38 selected
audit repairs. A fresh `git fetch origin` confirmed main remains
`a2d2e57d2de70125dbde002072853e73b788bd8d`; the repaired candidate descends from it.
The audit branch is `work/fleet-reference-audit-20261002`. Original worktrees are preserved.

Scope: all **103 tracked files under `skills/*/references/`**, across **25 skills**, totaling
**553,914 committed UTF-8 bytes**. Assets, executable helpers, generated copies, agents and
entrypoints are consumers or comparison evidence, not additional removal targets.
The seven other supporting Markdown files counted in the earlier size answer are outside
`references/` and are not silently included here. Sizes use committed blobs, avoiding Windows
checkout line-ending differences; bytes are not model tokens or observed prompt usage.

Three skill bundles are reviewed per group (one in the final group). Each group's evidence is
committed before substantive review of the next group starts. Within a group, independent
reviewers own separate bundles. Every reference receives these six lenses:

1. Purpose and a concrete human/agent task served.
2. Routing, local links, code/tests and other actual consumers.
3. Unique information and overlap with the entrypoint or neighboring references.
4. Correctness, freshness, evidence limits and authority/trust boundaries.
5. LLM readability, conditional loading and avoidable context cost.
6. A disposition, smallest safe action, content to preserve and required validation.

`KEEP` preserves a distinct useful reference and may include a small correction or navigation fix;
`TRIM` removes bounded unnecessary material and can participate in a paired relocation;
`MERGE` consolidates into a named owner while preserving unique content; `MOVE` changes ownership;
`REMOVE` requires evidence that the whole file can disappear; `CONDITIONAL` makes access depend on
an explicit owner decision about the two empty inventory files' future home. Ordinary task-based
loading applies to other references too. No MOVE or REMOVE disposition was selected.
These are recommendations until the user selects changes.
Tests asserting a string, a file's age, its length, or a lack of static mentions alone do not
establish necessity or dispensability. Repeated safeguards can be appropriate at independent
dangerous-action boundaries. Mere mention is not proof that a reference was read in a model run.

Local evidence is marked `[verified]`, fetched external contracts `[sourced]`, and unexercised
model/platform utility `[unverified]`. Correctness review is risk-directed; source receipts name
the facts checked and do not certify every vendor claim in every file. No live model campaign,
production action or reference cleanup is part of this audit.

## Coverage

| Group | Skills | References | State |
|---|---|---:|---|
| 01 | agent-authoring, akamai-edge, backend-craft | 16 | [Reviewed](group-01.md) |
| 02 | ci-actions, database-reliability, eng-ladder | 12 | [Reviewed](group-02.md) |
| 03 | frontend-craft, gcp-ops, grafana | 19 | [Reviewed](group-03.md) |
| 04 | incident-investigation, obs-alerting, obs-logs | 14 | [Reviewed](group-04.md) |
| 05 | obs-metrics, obs-pipeline, obs-traces | 9 | [Reviewed](group-05.md) |
| 06 | operational-learning, pcf-deploy, pcf-ops | 8 | [Reviewed](group-06.md) |
| 07 | production-change-gate, python-craft, resilience-analysis | 16 | [Reviewed](group-07.md) |
| 08 | runbook, service-lifecycle, stack-profile | 8 | [Reviewed](group-08.md) |
| 09 | toil-reduction | 1 | [Reviewed](group-09.md) |

## Initial verification

[verified] Baseline `scripts/check_links.py` passed using the existing Python 3.14 environment.
All 103 references have at least one basename mention in non-generated local material. A scan
found no identical multi-file paragraphs of at least 160 normalized characters among references.
Those discovery checks do not rule out semantic duplication or establish task value.
The inventory and raw reviewer work are retained in `F:/iso-tmp/reference-audit-20261002`.

## Disposition

[The inventory](inventory.csv) records each frozen path, committed byte/line count, SHA-256,
group and primary disposition. Each group gives per-file purpose, consumers, unique content,
exact proposals or reasons to retain, and verification limits. The [action register](recommendations.md)
collects every finding ID and explains selection order, retained safeguards and size tradeoffs.

The preferred proposals reduce canonical skill content by an estimated **4,333–5,453 bytes**,
including corrective growth, estimated Contents additions and Copilot consolidation. This is
a proposal-span estimate, excluding generated copies and any historical-link repair. The runbook
merge grows its entrypoint by 311 bytes while removing a 2,946-byte reference; its alternative
placement is not additive. No token/latency or behavioral improvement was measured.

The source audit remains bound to c7fdbe3 even if later reports are committed on this branch.
Retain this packet while `AUDIT-001` depends on the owner's cleanup choices and their validation.

## Verification and limits

[verified] Inventory reconciliation covers exactly 103 distinct paths and 553,914 bytes; every
record's SHA-256 matches its frozen Git blob. Group coverage is complete and all 40 recommendation
IDs are unique. The source diff under `skills/` against c7fdbe3 is empty. Existing link checks
passed after every group, and Gate A passed at the group-08 push boundary. On the completed
publication content, `scripts/check_links.py` passed, `git diff --check` was clean and
`scripts/gate_a.py` passed **2/2 structural steps**. A separate packet check verified all
**449 local Markdown file targets** exist; it did not validate anchors or external URLs.
These checks establish well-formed documents and inventory consistency, not behavioral quality.

An independent reviewer reconciled the inventory against the Git tree and traced actionable
proposals through original source and consumers, with a separate helper for groups 01–04.
The completed synthesis review found no material issues; its independent count, classification
and byte-accounting checks agree with this packet. Final review is bound to the publication
candidate. These are static document/source
checks; no product tests, new tests, live model campaign, platform operation or cleanup ran.
The earlier repair test results in AUDIT-001 belong to that repair candidate and are not new
test results from this audit. Bounded primary-source lookups support named claims only; the
packet does not recertify all vendor documentation or establish model loading/effectiveness.

Group commits, in order: `0cec195d`, `e2adc4d3`, `a121584e`, `178853ca`, `cf021a54`,
`c049cf82`, `277f665a`, `2ff0e3b0`, `8a17035e`. Group 05 also records the helper-exchange
navigation omission discovered during cross-fleet reconciliation, preserving group 04 history.
