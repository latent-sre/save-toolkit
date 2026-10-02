# Reference necessity and context-cost audit

Date: 2026-10-02. Human owner: the user; review and integration caller: `/root`.
This packet supports `AUDIT-001` in the [live roadmap](../../fleet-roadmap.md).
It records recommendations, not permission to remove guidance or accept model behavior.

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

`KEEP` preserves a distinct useful reference; `TRIM` removes bounded unnecessary material;
`MERGE` consolidates into a named owner while preserving unique content; `MOVE` changes ownership;
`REMOVE` requires evidence that the whole file can disappear; `CONDITIONAL` makes access depend on
an explicit task or owner decision. These are recommendations until the user selects changes.
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
| 03 | frontend-craft, gcp-ops, grafana | 19 | Next group |
| 04 | incident-investigation, obs-alerting, obs-logs | 14 | Pending |
| 05 | obs-metrics, obs-pipeline, obs-traces | 9 | Pending |
| 06 | operational-learning, pcf-deploy, pcf-ops | 8 | Pending |
| 07 | production-change-gate, python-craft, resilience-analysis | 16 | Pending |
| 08 | runbook, service-lifecycle, stack-profile | 8 | Pending |
| 09 | toil-reduction | 1 | Pending |

## Initial verification

[verified] Baseline `scripts/check_links.py` passed using the existing Python 3.14 environment.
All 103 references have at least one basename mention in non-generated local material. A scan
found no identical multi-file paragraphs of at least 160 normalized characters among references.
Those discovery checks do not rule out semantic duplication or establish task value.
The inventory and raw reviewer work are retained in `F:/iso-tmp/reference-audit-20261002`.

## Disposition

The final file-by-file recommendations and synthesis will be recorded after all groups complete.
Retain this packet while `AUDIT-001` depends on the owner's cleanup choices and their validation.
