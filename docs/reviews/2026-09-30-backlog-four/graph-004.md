# GRAPH-004: selected workflows and recovery evidence

Status: implementation in progress. This packet supports GRAPH-004 and its GRAPH-006
prerequisite in the [live roadmap](../../fleet-roadmap.md); it does not accept a candidate.

## Owner-selected outcome

On 2026-09-30 the human owner selected both uses of the fleet documentation/knowledge atlas:

1. Trace a proposed source change to affected agents, skills, rules, generated projections,
   and verification/evidence references.
2. Find relevant canonical guidance during an investigation, including conditional reference
   loading and evidence labels, without loading the complete repository into model context.

The atlas locates recorded relationships. It cannot establish current service behavior, make an
incident diagnosis, grant execution authority, approve a change, or turn a generated relationship
into canonical knowledge. Ambiguous, missing, inferred, historical, and truncated results remain
explicit. A source change is not proof that every graph neighbor needs an edit.

## Recovered authoritative inputs

- [verified] Fresh GitHub read: PR #205 is closed and unmerged; exact donor head is
  `21dc443b55527d5955713c471fe6168644fac12b`. The object is available locally. A detached,
  clean donor worktree was created at `.worktrees/graph-004-donor-21dc443b` for comparison.
- [verified] The proposed GRAPH-006 revision-2 design is recoverable from commit `67f55b81`,
  path `docs/decisions/2026-09-01-graph-006-fleet-atlas-typed-evidence-pipeline.md`.
  It was merged in PR #207 and is absent from the present tree. Revision 2 already disposes
  the earlier review's selector, evidence-model, rollback, and exit-code objections; the earlier
  revision-1 review is not evidence that those design objections remain unanswered.
- [verified] Donor runtime is five scripts, with sixty named component tests. The donor is
  preserved as comparison material, not installed as a working atlas in the current fleet.

## Compatibility and delivery contract

The implementation follows the revision-2 design's separate-surface migration. Canonical fleet
files remain authoritative; no generated v1 content is edited. New runtime code is
`scripts/fleet_atlas_v2*.py`, with tests `scripts/test_fleet_atlas_v2*.py`. The planned CLI is
`fleet_atlas_v2.py [--root ROOT] {build,check,query}`, with output under `docs/fleet-atlas/v2/`.
The ten donor query verbs remain: `governs`, `owner-of`, `loads-for`, `supersedes`, `depends-on`,
`blocks`, `verified-by`, `evidence-for`, `generated-from`, and `state`. The selected uses add
`impact <path-or-id>` and `guidance <terms...>`; both require verified inputs and bounded output.

| Observable | Required comparison / deliberate v2 change |
|---|---|
| Entity identity and relationships | Compare all donor nodes/edges semantically; explicit selectors preserve distinct entities sharing a path. Wrong or missing donor relationships require named expected deltas and regressions. |
| Evidence | Every determining span and source authority must be verified; exact blobs and excerpt hashes replace placeholder citations. Inferred edges stay inferred. |
| Provenance | Revision, clean-source status, canonical-input digest, manifest membership, and regenerated projections pass one verifier. |
| Labels | Every projected fact carries class, evidence label, and complete citations. |
| Outcomes | Exit 0 means verified results or verified empty; 1 means unavailable, invalid, stale, unverified, or drifted; 2 means usage error. All paths emit an envelope. |
| Limits | Compact query/detail views are capped at 20,000 encoded bytes; index at 4,000. Truncation reserves its own bytes and reports omitted records and actual budget. |
| Generated artifacts | Separate v2 directory and entrypoint; no v1 consumer switches until parity and acceptance. Reverting dependent slices in reverse order is the rollback. |
| Freshness | Content-age findings remain advisory unknowns. A stale atlas cannot produce a verified answer. |
| Investigation guidance | Direct source citations and conditional loading predicates; no inferred operational diagnosis or live-state claim. |
| Change impact | Explain the recorded relation/path connecting each affected artifact; preserve uncertainty and avoid claiming the graph is a complete runtime dependency map. |

## Completion evidence required

The thirteen GRAPH-006 acceptance requirements remain intact:

1. Side-by-side donor/v2 comparator over the full recorded observable contract, with explicit deltas.
2. Byte-identical output with extractor registration shuffled.
3. Selector-safe resolution preserving every entity sharing a path.
4. Every fact and edge cites all determining spans.
5. Authority checks prevent test literals and fixture writes becoming verification evidence.
6. Build/check/query reject tampering through the same verifier.
7. Deterministic clean builds and provenance checks across merge/rebase histories.
8. Every projected fact retains class, label, and citations.
9. Encoded byte budgets for queries and all views, including Mermaid.
10. Named regressions for every material donor finding.
11. Both paths remain available with reversible, explicit consumer cutover.
12. Durable design/compatibility/rollback disposition; no design proposal represented as acceptance.
13. Focused/component/eval/structural/determinism/CI evidence and independent exact-candidate review.

The seventeen named donor regressions from revision 2 are: evidence links selecting decision
entities; component owners emitting ownership edges; all catalog fields cited; batch evidence
citing both sides; guard edges citing roster and hook wiring; generation edges citing mapping
bodies; roadmap state citations; nonancestor revision checks; age checks for all dated live states;
encoded query budgets; CLI labels; absent-needle errors; shuffled registration; correct index
truncation budgets; nonempty real-tree flagship queries; generated-input digest coverage; and
dangling-edge rejection. None may be silently removed because current fixtures pass.

No item is closed by this packet. Implementation progress and fresh test results are recorded below
as each slice becomes verifiable.

## Fresh recovery and foundation checks

- [verified] Python `F:/repos/sre-agents/.venv/Scripts/python.exe` reports 3.14.7.
- [verified] At untouched donor `21dc443b`, `scripts/test_fleet_atlas.py` passed all 60 tests
  in 140.301 seconds. Its negative-case diagnostics are expected test output.
- [verified] A separate in-memory donor extraction produced 815 nodes and 975 edges, while
  `evidence-for EVAL-003` and `owner-of fleet-atlas` both returned zero results. An absent
  needle passed to the donor locator returned line 1. These are fresh reproductions of gaps
  missed by that green donor suite, not acceptance evidence.
- [verified] The first 48 v2 foundation checks passed in 24.16 seconds: explicit entity selectors,
  deterministic bucket merging, typed endpoints and cardinality, source/whole-blob binding,
  dirty-source refusal, nonancestor revision comparison, proof completeness and source authority,
  debt refusal, strict graph shape, complete labeled citations, byte limits, real-Git artifact
  verification and tampering, and enveloped CLI outcomes.
- [unverified] These checks do not prove complete donor extraction, semantic parity, either
  selected end-to-end workflow, real-tree integration, hosted CI, or exact-candidate acceptance.
  The extraction, compatibility and integration work must complete before those claims change.

## First donor comparison and repairs it exposed

[verified] The first complete entity comparison used donor source revision `21dc443b` on both
sides. It measured 815 nodes / 975 edges / 7 unknowns for v1 and 845 nodes / 1,006 edges /
16 unknowns for the initial v2 extractor. The strict comparator reported **DIFFERENT**, with
1,885 exact deltas and no expected-delta exceptions. The common nodes had no attribute-value
deltas; most reported differences were evidence corrections, but that does not dispose them.
Raw snapshots and the full report are retained privately under
`.eval-runs/backlog-four-atlas/` in the main repository checkout.

The comparison exposed actual missing coverage, independently of the new green tests:

- The v2 source boundary omitted `requirements-dev.txt`, dropping a rule's primary source.
  Root dependency-contract inputs have been added to the digest boundary.
- Multiline and nested-label Markdown links dropped the EVAL-005 and SKILLS-003 evidence
  relations. These require source-parser repairs rather than compatibility exceptions.
- Unique schema files were resolved to newly created generic document nodes, changing their
  verification relationships. Schema identity must survive whole-document resolution.
- `CHANGELOG.md` and `evals/README.md` lost their live-contract classification.
- Valid section anchors need their target-heading witness; a missing or ambiguous anchor
  remains unknown, with no arbitrary entity selection.
- The donor's `schema-projection:docs/fleet-atlas/generated/atlas.json` verification edge was
  traced to `scripts/test_fleet_atlas.py:894`, which reads a temporary `self.root` fixture.
  Retaining that edge would preserve false evidence. Its removal needs an explicit, named
  compatibility disposition backed by the fixture-versus-repository regression.

This measurement is an intermediate candidate observation. Rerun it after the repairs;
do not treat the initial counts, green tests, or a corrected subset as semantic-parity acceptance.

## Bounded comparison after coverage repairs

[verified] `comparison-03` ran the same donor-source extraction under `python -I -S` with an
isolated copy of the v2 implementation and a SHA-256 manifest of those exact implementation files.
The private directory is `.eval-runs/backlog-four-atlas/comparison-03/`; earlier failed reports
remain retained. It contains the full candidate entity snapshot, strict comparator report, engine
copy, and implementation manifest. Result: **DIFFERENT**, 840 nodes / 1,016 edges / 11 unknowns,
and **1,877 exact deltas**, still with zero accepted exceptions.

[verified] The previously missing dependency-file, multiline/nested-label evidence, live-guide
authority, and function-local repository-schema-read relationships are restored. All attributes
on common nodes match the donor. No common edge has a changed source, target, kind, class, or
attribute; its evidence records do change.

The remaining entity-level differences require these explicit dispositions:

| Difference | Current evidence and required disposition |
|---|---|
| Four duplicate `document:docs/decisions/...` nodes removed; five governing edges now use their existing typed decision node | Corrects path-as-entity duplication. Verify the exact old/new node and edge identities in the report, then name these as intentional selector repairs. |
| One review citation now targets `roadmap-item:ROUTE-004` instead of the entire roadmap document | The source carries that explicit anchor. Keep the narrower target and exact heading witness as an intentional selector correction. |
| One generated-atlas `verified_by` edge removed | The donor test reads its temporary `self.root` fixture, not the repository artifact. Preserve the removal and its regression as a false-evidence correction. |
| External owner `owner:save-toolkit-maintainers` path changes from null to `docs/fleet-roadmap.md` | v2 records the declaration's source path. Accept this representation change explicitly or add a separate entity-path field; it is not an unnoticed exact match. |
| 29 newly represented nodes (21 document, 5 review, 3 validator) and additional relationships | Inspect each exact addition for actual source support. Additions include resolvable source targets, corrected evidence/ownership and conditional method loading; a higher count alone proves no completeness. |
| Node/edge evidence and added v2 proof/selector/guidance records | Complete blob-bound proofs, correct classes/kinds, heading witnesses and bounded guidance are deliberate changes. Their exact before/after records still need named comparison dispositions. |
| Four additional advisory unknowns and source-digest/count changes | Broader dated-status freshness checks and newly represented source material explain candidates for review; do not downgrade advisory unknowns to verified absence. |

This is the **entity/provenance comparison surface**, not a completed comparison of every CLI
envelope and generated projection. No expected-delta file has been approved or applied. The full
GRAPH-006 comparison, final combined candidate checks, independent review disposition, and exact
candidate human acceptance remain open. The root's separate clean-snapshot build/check/query
checks establish their own narrower runtime scope.

[verified] Additional implementation regressions reproduced and corrected: `supersedes` must
match both the superseding and superseded entity; malformed tracked Python input must produce
an exit-1 unverified envelope in build/check/query; body-guidance snippets must survive oversized
matching metadata under the byte cap; and identifier/path control characters or Unicode line
separators must not introduce unlabeled output lines. Ordinary spaces and non-ASCII paths remain
supported. These are concrete contract repairs, not completion of the open comparison gate.

## Integration rehearsal history

- [sourced: root verification] Isolated candidate snapshot
  `19f779079dc7cbf1acc1bca1f8d985db88025a2c` passed all seven real-tree build/check/query CI
  commands, including the two selected navigation tasks, and an isolated `python -I -S` check.
  Its full suite reported 1,351 passing tests, 2,113 passing subtests, eight skips, and one
  collection error: an imported helper named `test_file_reads` was mistakenly collected as a
  pytest test. The helper import was subsequently aliased. These results establish that earlier
  snapshot's scope; they do not verify the later repairs.
- [sourced: root verification] Later isolated candidate
  `3e34095e85482732ef5acb3a684589440caeefed` failed its real-tree build on a conflicting extracted
  relationship (`edge:f4109224559f6913`). The extractor owner is repairing the duplicate-source
  relationship handling; final candidate integration results remain pending.
- [verified] Projection comparison found readable Mermaid entity names had become opaque hashed
  boxes. A focused test reproduced the loss; display labels are now retained separately from safe
  internal IDs, with complete evidence comments and the same encoded-byte limit. Label escaping
  uses the official Mermaid flowchart decimal entity contract, fetched through Context7 from
  [Mermaid's flowchart documentation](https://github.com/mermaid-js/mermaid/blob/develop/docs/syntax/flowchart.md).
  The targeted rendering test passed; browser-rendered visual acceptance remains unverified.
