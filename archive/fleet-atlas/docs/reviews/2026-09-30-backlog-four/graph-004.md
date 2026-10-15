# GRAPH-004: selected workflows and recovery evidence

Status: implementation and expanded comparison completed and independently approved;
exact-candidate human acceptance remains open. Earlier incomplete receipts remain preserved and
are explicitly superseded below. This packet supports GRAPH-004 and its GRAPH-006 prerequisite
in the [live roadmap](../../fleet-roadmap.md); it does not accept a candidate.

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
`scripts/fleet_atlas_v2*.py`, with tests `scripts/test_fleet_atlas_v2*.py`. The implemented CLI is
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
| Generated artifacts | Separate v2 directory and entrypoint; v1 was never installed on main. This is first adoption with canonical-source fallback, subject to the explicit compatibility disposition and exact-candidate acceptance below. |
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
- [unverified at this foundation checkpoint] These checks did not prove complete donor extraction, semantic parity, either
  selected end-to-end workflow, real-tree integration, hosted CI, or exact-candidate acceptance.
  Later comparison and integration results below have their own revision and scope.

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
  relationship (`edge:f4109224559f6913`). The repair preserves different target anchors in the
  relationship identity. Its full suite independently passed 1,363 tests and 2,130 subtests,
  with eight skips and one existing Starlette/AnyIO warning; a green full suite did not hide
  the failing real-tree build.
- [verified] Projection comparison found readable Mermaid entity names had become opaque hashed
  boxes. A focused test reproduced the loss; display labels are now retained separately from safe
  internal IDs, with complete evidence comments and the same encoded-byte limit. Label escaping
  uses the official Mermaid flowchart decimal entity contract, fetched through Context7 from
  [Mermaid's flowchart documentation](https://github.com/mermaid-js/mermaid/blob/develop/docs/syntax/flowchart.md).
  The targeted rendering test passed; browser-rendered visual acceptance remains unverified.

- [sourced: root verification] Exact candidate `2ffc6151` passed all seven real-tree CI
  build/check/query commands, isolated `python -B -I -S` verification, Gate A 2/2, and scenario
  validation (181 specifications / 630 expectations). Its full suite passed 1,365 tests and
  2,137 subtests, with eight skips and one existing Starlette/AnyIO warning, in 349.28 seconds.
  The real `service-lifecycle` impact query returned 19 relationships / 17,313 bytes without
  truncation, including the affected reliability agent, verification references, and generated
  projections. The independent approval at that revision covered four repaired findings only:
  writer lineage, anchor identity, readable Mermaid labels, and reliability integration.
- [verified] The full donor CLI/view rehearsal `full-comparison-03` used clean synthetic
  shared-source revision `7507c58ecc257eba1f41ea8b03e316c88e1ef9b7`. Both real CLIs built and
  checked successfully under isolated stdlib Python. All ten legacy verbs, both supersession
  directions, empty/invalid/drift outcomes, and both selected additions were captured alongside
  every generated file. This exposed missing projection families and lookup semantics; repairs
  retained delegation/constraints, near-miss coverage, decision and roadmap metadata, and
  readable diagrams. Further red regressions restored exact-name precedence, rule section and
  source-text lookup with rule facts, and joined multiword state/loading arguments. The final
  focused CLI run passed 13 tests and nine subtests in 26.97 seconds.
- [sourced: root verification] The intermediate affected suite passed 100 tests and 62 subtests
  before those last lookup repairs. The later producer-order/budget/history/lookup checkpoint is
  `46abca05dd012cc6d0ab07371e438094224aa41e`; final comparison and exact-revision checks below
  supersede narrower intermediate measurements, without retroactively changing their results.

## First-adoption consumer rollback

The preserved donor is a comparison and recovery source. Installing its known evidence defects
on main would not demonstrate a useful production migration. The concrete disposition is to
keep both runtimes independently executable in the shared-source comparison fixture and keep
the exact donor checkout recoverable; current adoption enables the v2 skill and CI consumer only.
Canonical guidance remains the operational fallback. This adapts the historical migration plan
to the verified fact that PR #205 was closed unmerged; human acceptance of this disposition is
still required, and no v1-to-v2 production cutover is claimed.

[sourced: root verification] A 19-command rollback/resume rehearsal at `37bf6a6d` in
`F:/iso-tmp/atlas-consumer-rollback-37bf6a6d` removed exactly six consumer paths: the new atlas
skill and generated mirror, three discovery scenarios, and the CI invocation. It retained the
offline runtime and canonical incident/service guidance. Adapter regeneration, Gate A, and
scenario validation passed. After the rollback commit, the old atlas query returned exit 1 with
an unverified envelope and no results. Restoring the six paths and regenerating produced a tree
identical to the base; Gate A and atlas `check` passed without rebuilding. Private command and
result artifacts are `.eval-runs/backlog-four-atlas/consumer_rollback.py` and
`consumer-rollback.json`. This proves repository consumer stop/resume at those bytes, not a
live-host rollback or complete runtime uninstall.

## Requirement-to-evidence map

This map names actual test bodies and retained artifacts. Passing component tests establish the
stated local contracts; they do not supply human acceptance, hosted CI, or operational truth.
`scripts/test_fleet_atlas_v2_` is the common prefix for the test modules abbreviated below.

| GRAPH-006 requirement | Concrete evidence and remaining boundary |
|---|---|
| 1. Full observable parity and explicit corrections | `compat.py` preserves supplemental facts; `compare.py` tests exact path/before/after exceptions, missing-vs-null and duplicate identities. Private `full-comparison-07` combines 25 fresh ordinary/usage cases with nine required refusal cases and exact restoration, for 35 actual CLI cases per version. Final counts and hashes are below; proposal matching is not owner acceptance. |
| 2. Shuffled producer registration gives identical bytes | `extract.py::test_shuffled_extractor_registration_is_byte_identical` reverses and applies 12 seeded permutations before ten real registered producers execute. It verifies prerequisite outputs/frozen results, graph serialization and all 12 rendered files including manifests. `test_extraction_stage_dependencies_reject_missing_cycles_and_duplicates` checks invalid schedules. The earlier bucket-only test was insufficient and was replaced by this producer-level test. |
| 3. Selector-safe resolution | `model.py::test_evidence_link_resolves_by_selector_not_path` and `test_ambiguous_selector_names_candidates_without_picking_first`; extractor tests cover decision links, valid section witnesses and multiple selectors in one evidence file. |
| 4. Complete determining spans | Extractor catalog, joined-batch, guard, mapping-body, function-local-root and standalone-writer tests inspect required inputs; proof tests reject wrong values, irrelevant spans and missing/extra joined inputs. Full comparison verifies every exported evidence span against the frozen source bytes. |
| 5. Source authority and actual test reads | `extract.py::test_ast_verification_rejects_literals_and_fixture_reads`, rooted-fixture-write and helper-write tests; `proofs.py::test_test_fixture_literal_does_not_establish_agent_fact`. Direct/keyword/transitive helper writes are negative controls. These establish static attribution, not executed test coverage. |
| 6. One artifact verifier | Artifact tests alter facts, views, membership and manifests; `cli.py::test_query_rejects_drift_using_same_verifier_as_check` exercises query refusal. Full comparison tampers with each runtime's INDEX and records actual exit 1. |
| 7. Determinism and Git provenance | Artifact deterministic-build and generated-only-commit tests; `sources.py::test_same_corpus_accepts_divergent_rebased_and_merged_history` creates real divergent, rebased and merged histories. The differing nonancestor-corpus negative test remains. |
| 8. Labels and citations on every projection | `format.py::test_every_projected_fact_carries_class_label_and_all_citations`, CLI label tests, readable-Mermaid evidence test and model control-character rejection. Inferred claims remain unverified; unknown advisory text does not become verified absence. |
| 9. Encoded byte limits | Format query/index/oversized-record tests; CLI crowded-guidance regression; `budgets.py::test_large_multibyte_details_and_mermaid_account_for_omitted_facts` runs actual rendering with hundreds of multibyte relationships and verifies all view limits, reported bytes and omissions. Final actual CLI/view measurements are retained separately. |
| 10. Named donor regressions | The 17-row mapping below names the corresponding bodies/artifacts. New findings from comparison and independent review added further regressions; names alone are not treated as proof. |
| 11. Recoverability and consumer rollback | Exact v1 donor remains recoverable; both runtimes execute in the shared-source fixture. The 19-command first-adoption consumer rollback/resume rehearsal passed. Acceptance of this disposition remains a human decision; v1 was never a main consumer. |
| 12. Durable design and compatibility decision | Historical revision-2 design is preserved by exact commit/path; this packet records source authority, selected tasks, exact differences, rollback and verification boundaries. It is a proposed current adoption decision, not a claim that historical design acceptance approves today's candidate. |
| 13. Tests, structural checks, CI and independent review | Exact-revision root results and scoped independent review are recorded above and in the final checkpoint section. Hosted CI and exact-candidate human acceptance remain separate gates. |

| Named revision-2 regression | Test or actual-run artifact |
|---|---|
| Evidence link selects the decision entity | `extract.py::test_evidence_link_resolves_by_selector_not_path`; actual `evidence-selector-repair` query |
| Component owner emits ownership edge | `extract.py::test_owner_field_naming_a_component_emits_owner_to_component_edge`; workflow owner query and actual `owner-missing-component-repair` |
| Catalog proof covers every determining field | `extract.py::test_catalog_node_proof_is_extracted_over_every_contributing_field` |
| Batch edge cites both joined sides | `extract.py::test_batch_edge_proof_is_joined_and_cites_both_sides` |
| Guard relation cites roster and hook wiring | `extract.py::test_guard_edge_proof_is_joined_over_roster_and_hook_wiring` |
| Generation proof cites mapping body | `extract.py::test_generated_from_proof_cites_mapping_span_not_signature`; standalone writer/dataflow negative controls |
| Roadmap state facts project class, label and all citations | `format.py::test_every_projected_fact_carries_class_label_and_all_citations` covers the design's named projection regression. Additional `extract.py::test_roadmap_state_cites_status_or_closure_and_rejects_missing_support` checks exact live Status/historical closure spans and rejects omitted or irrelevant support. |
| Nonancestor revision checked for identical inputs | `sources.py::test_reachable_non_ancestor_revision_with_differing_inputs_is_rejected` and actual merge/rebase-history test |
| Every dated live state gets advisory age check | `extract.py::test_staleness_applies_to_every_dated_live_status_as_unknown`; exact added GRADER-009/GRAPH-004/GRAPH-006 donor advisories |
| Query cap uses encoded bytes | `format.py::test_query_bounded_by_encoded_bytes_with_truncation_record`; real state/guidance query byte counts |
| CLI preserves evidence labels | `cli.py::test_cli_results_carry_evidence_labels`; captured inferred dependency results remain `[unverified]` |
| Missing locator needle fails | `sources.py::test_locator_raises_when_needle_absent`; donor line-1 fallback reproduced before implementation |
| Registration shuffle is deterministic | Actual ten-producer permutation test described in requirement 2, including graph and rendered bytes |
| Index truncation reports index budget | `format.py::test_index_truncation_reports_its_own_budget`; actual rendered index budget checks |
| Empty flagship queries fail CI | `scripts/test_check_fleet_atlas_v2.py::test_ci_contract_run_fails_on_empty_flagship_queries`; actual donor/v2 owner, evidence and loading queries plus real-tree impact/guidance CI and body-only workflow tests establish positive behavior separately. |
| Generated-input paths enter source digest | `sources.py::test_canonical_digest_covers_github_and_platforms`; root dependency-contract corpus test |
| Dangling relationships fail | `model.py::test_no_dangling_edges`; predicate endpoint-type/cardinality tests |

## Checkpoint verification

[sourced: root verification] At exact implementation checkpoint
`46abca05dd012cc6d0ab07371e438094224aa41e`, the affected atlas suite passed **105 tests and
92 subtests in 58.11 seconds**, including the real producer-permutation, oversized-rendering,
Git-history, query, extractor and artifact regressions. All seven real-tree atlas CI commands
passed. The independent cumulative static review against base `65daa521` returned **APPROVE**
for atlas runtime, schema, skill, CI and tests at tree
`005936634265b62918d7ebe158ed371346a1a7fb`. That review explicitly excluded the full compatibility
disposition/report, eval behavior, generated parity, runtime execution and hosted CI; these are
not inferred from its verdict. The full repository suite above was at `2ffc6151`; the later
atlas changes receive their own affected-suite and real-tree checks rather than a retroactive
full-suite claim.

[sourced: extractor-owner verification] The producer-stage refactor independently compared the
old and new implementations over the same `37bf6a6d` source corpus: 665 nodes / 7,240 facts,
byte-identical serialized graph and all 12 rendered files. The new scheduler uses explicit
prerequisites and immutable stage outputs; registration-order tests execute the producers after
permutation. This result establishes that bounded scheduling refactor's behavior on that corpus;
the donor comparison still uses its separately frozen shared-source fixture.

## Exact comparison disposition method

The comparison does not normalize away evidence, returned facts, text, exit codes, or file
membership. It compares complete v1-shaped semantic exports plus raw actual command envelopes,
stdout/stderr/encoded lengths, every generated file's text/hash/length, and all additional v2
selectors, facts and proofs. Only entity array ordering is normalized. A proposed exception names
one exact JSON pointer and its complete before/after values; unused or changed exceptions fail.
Each exception has a separate reason and source evidence. No wildcard or broad ignore rule is
used, and a comparator match does not approve those proposals.

The private `dispose_comparison.py` verifies the frozen implementation manifest and invokes the
complete artifact verifier before classification. It separately checks every exported citation
against its exact source excerpt, requires common entity values/attributes to remain identical,
and restricts additions/removals to the individually reviewed inventory. Five rule-source edges
move from duplicate generic document nodes to their existing typed decisions; two review
citations preserve their explicit target anchors. One donor verification edge is removed because
its cited read is of temporary fixture output. These are explicit corrections, not parity by
count. Complete proof/selector records, body guidance and the two new selected queries are
versioned additions.

For each legacy query, the checker compares the donor's returned relationships with the complete
v2 selection before applying its byte budget. On untruncated relation queries it also rejects
extra retained donor relationships. That additional precision control rejected the intermediate
`full-comparison-03` implementation: `verified-by software-engineer` had 33 unrelated matches
from broad description search. Its earlier coverage-only exception match is marked rejected in
the private disposition summary. Focused red tests and checkpoint `46abca05` fixed the lookup;
the final actual query returns the same 12 relationships, with v2 output 10,765 bytes versus
40,554 donor bytes, without truncation. This failed intermediate evidence remains retained.

All v2 command envelopes are checked for actual exit code, UTF-8 bytes, outcome, complete result
count plus omitted count, and source-bound selected fact IDs. Every generated file is compared
with fresh rendering from verified facts; compact Markdown and Mermaid outputs additionally
check their exact reported byte budgets and omissions. Full graph/manifest artifacts are explicit
offline data and are not described as compact model views.

[sourced: extractor-owner verification] A final coverage audit found the named roadmap-state
regression was only indirectly covered at `46abca05`. The added test-only regression now checks
the exact live-status and historical-closure source lines and rejects omitted or irrelevant
support. The full extractor module passed 27 tests and 47 subtests in 0.19 seconds. No runtime
bytes changed; this later test evidence is recorded separately from the checkpoint suite.

## Earlier comparison result: required failure paths were incomplete

[verified] `full-comparison-04` used donor `21dc443b55527d5955713c471fe6168644fac12b` plus
the exact `46abca05` v2 implementation in one clean synthetic source fixture,
`e3250f25d086f6a0a00af456a51780177e9dc7e5`, at
`F:/iso-tmp/atlas-donor-v2-bv3b_x2n`. Its 11-file implementation manifest has SHA-256
`151efa0b14fa475edf06475876c86c2ca8b19fa09657963a811e403055f34756`.
Both real CLIs ran under `python -I -S`: 22 command cases per version, including build/check,
all ten legacy verbs, positive name/section and multiword loading lookups, empty/invalid/drift
cases, both supersession directions, and the two selected new tasks. Every generated artifact
was captured: 11 v1 files and 12 v2 files. This fixture is comparison evidence, not a main or
release revision.

The undisposed strict result was **DIFFERENT: 2,110 exact deltas**. After the independently checked,
individually named proposed corrections/additions, the strict comparator returned **MATCH**:
**2,110 matched expected deltas, zero unexpected deltas, zero unused exceptions**. No source
entity's common value or attribute changed silently. V1 has 815 nodes / 975 edges / seven
unknowns; v2 has 844 nodes / 1,018 edges / eleven unknowns on this shared corpus. The four v2
implementation/schema entities in this fixture explain why these counts differ from the earlier
donor-only extraction comparison.

| Exact delta family | Count and disposition |
|---|---|
| Complete source proofs on common entities | 1,778; common claims remain equal, source spans and per-fact derivations are explicit and replay-verified. |
| Source-supported additions | 84 complete added entities/relationships, each bound to its individual source evidence and reviewed identity. |
| Selector and false-evidence repairs | 11 duplicate/less-specific identity removals plus one temporary-fixture false-coverage removal; corresponding replacements are explicit additions. |
| Owner location, metadata and advisory changes | One declared owner source path; four digest/count fields; one complete unknown array preserving all seven donor messages and adding four advisory cases. |
| Typed pipeline additions | Three complete supplemental fact/selector/proof collections, retained rather than hidden from comparison. |
| Actual CLI and projection representations | 193 command-field deltas and 34 generated-file deltas; complete before/after records plus result precision/coverage, byte, label and truncation checks. |

The selected change-impact query returned 12 relations / 10,271 bytes without truncation in
this donor fixture. Guidance returned ten source-bound facts / 19,002 bytes and explicitly
reported 211 omitted facts. Broad rule-section lookup returned 39 facts / 19,621 bytes with
85 omissions; the donor emitted 46,853 bytes. These results prove bounded navigation of this
recorded corpus. They do not establish that a symptom has a particular operational cause or
that all affected artifacts are known.

Full private artifacts are retained under
`F:/repos/sre-agents/.eval-runs/backlog-four-atlas/full-comparison-04/`: raw v1/v2 observables,
unclassified report, `proposed-exact-deltas.json`, `delta-rationales.json`, command precision and
coverage checks, projection budget checks, disposed report, implementation manifest, and packet
hash manifest. Replay drivers and exact engine files are bundled in
`F:/repos/sre-agents/.eval-runs/backlog-four-atlas/graph-004-comparison-46abca05.zip`
(23,911,187 bytes); ZIP CRCs and every recorded artifact hash were verified after packaging.

| Retained artifact | SHA-256 |
|---|---|
| Full archive | `6178ef3499f6b1ec65214c265a61153778c5af179517853ccd21578584763f71` |
| Packet hash manifest | `2cca6c6c306899950567688cb3a3ef4ba8ca8864c55980d26d8e1da856503042` |
| Exact proposed exceptions | `63c0f9955788b0deb7af4e3fea217ec24373b04ab37ec6608b151fa1a026cecc` |
| Disposed strict report | `dd8531144d18973550dfd8c452200c714e4baa01a850735b28eba64faa7c6c3b` |

At this checkpoint, the independent static code approval excluded this detailed
compatibility disposition; the owner still needs to accept the exact candidate and its deliberate
API/evidence/first-adoption rollback changes. Hosted CI and browser-rendered Mermaid visual
acceptance are not claimed. No atlas query grants execution authority, and no generated output
promotes repository evidence into current operational truth.

Independent disposition review subsequently identified missing enumerated observable categories:
missing atlas, malformed atlas JSON, wrong API version, stale canonical provenance, query refusal
on projection drift, and invalid/missing/blank query terms. `full-comparison-04` remains valid for
the cases it measured, but its earlier full-completion claim is withdrawn. The review also
reproduced a real arity regression: actual donor `loads-for agent-authoring` returned exit 2,
while v2 returned exit 0 with seven facts. The exact receipt is
`.eval-runs/backlog-four-atlas/loads-for-arity-red.json`. A named regression reproduced wrong
outcomes with an absent atlas, a built atlas and direct query selection; the three-line repair
requires both skill and predicate before verification and inside selection. Joined multiword
predicates remain supported. The focused CLI suite passed 14 tests and eleven subtests in
28.39 seconds after repair. The following expanded measurement supersedes the earlier completion
claim rather than treating this unrequested behavior as an accepted extension.

[sourced: root verification] The repaired runtime checkpoint
`c9fb5bf7a1b244e6b36e6bfee002025626306aab` passed the full repository suite: **1,374 tests and
2,188 subtests**, eight skips and one existing Starlette/AnyIO warning, in 355.31 seconds.
`SRE_CONTEXT_ROOT` was bound to the clean producer revision `3433f98e`. All seven real-tree atlas
CI commands, Gate A 2/2, and 181 scenario / 630 expectation validation also passed. These results
are for that exact repaired checkpoint; earlier counts are left unchanged. Root also verified
two byte-identical 12-file builds and strict plugin/marketplace validation at the earlier
`46abca05` checkpoint, including an isolated stdlib build; those checks have that earlier scope.

## Expanded final comparison after disposition review

[verified] The expanded measurement uses the repaired `c9fb5bf7` engine in clean synthetic
shared-source fixture `6bfd625495a729278de6e4fbe40a5187186fbf3e`, located at
`F:/iso-tmp/atlas-donor-v2-xsjiiwdf`. The base remains exact donor `21dc443b`.
`full-comparison-06` freshly captured 25 cases per version, including missing search term, blank
quoted term and missing loading predicate: all three returned **exit 2 on both actual CLIs**.
The arity repair therefore restores the donor contract rather than accepting an unrequested
expansion. `full-comparison-07` preserves all 25 receipts and every generated artifact exactly,
and adds nine required failure cases plus a restoration check per version: **35 cases each,
70 actual CLI observations total**, all executed under `python -I -S`.

| Required failure state | Actual commands and observed outcomes |
|---|---|
| Missing `atlas.json` | `check` and a previously positive `query verified-by software-engineer`: exit 1 on both runtimes. |
| Unparsable atlas JSON | Same two commands: exit 1 on both runtimes. |
| Wrong atlas `apiVersion` | Same two commands: exit 1 on both runtimes. |
| Projection drift | Append the recorded comment to `INDEX.md`; the previously positive query refuses with exit 1 on both runtimes. The earlier check-drift case remains captured separately. |
| Committed canonical-source staleness | Append the recorded comment to `README.md` and commit it without rebuilding either atlas; `check` and the positive query both return exit 1 on both runtimes. This distinguishes stale committed provenance from dirty-source refusal. |
| Exact restoration | Restore original source revision and every changed artifact byte; both actual `check` commands return exit 0 without rebuilding. |

Every v2 refusal emitted a bounded `unverified` or `drift` envelope with zero results; there were
no tracebacks or unbounded error messages. The donor's stderr/text behavior is retained verbatim
in the comparison. Each mutation records its exact path, operation, before/after SHA-256, commands,
exit codes and restored SHA-256 in `failure-mutations.json`. The committed stale-source probe is
retained as `d93f7a2d5aa45e4a62e7b9edeab9201aae2d5812` on the private fixture's
`atlas-stale-provenance-probe` branch. The source was restored to `6bfd625495a729278de6e4fbe40a5187186fbf3e`;
all original source/artifact hashes matched, and the canonical input tree was clean. The preserved
donor and production checkout were not mutated by these probes.

[verified] The expanded undisposed result is **DIFFERENT: 2,161 exact deltas**. The strict result
with individually justified exact proposals is **MATCH: 2,161 matched, zero unexpected, zero
unused**. Owner acceptance remains false. The entity counts remain 815/975/seven for donor
nodes/edges/unknowns and 844/1,018/eleven for v2. The earlier 1,778 evidence corrections, 84
source-supported additions, 12 selector/false-evidence removals, owner/metadata/advisory and
typed-proof changes, and 34 file-representation deltas remain explicit. The complete CLI surface
now accounts for **244 command-field deltas**, including the additional usage/refusal/restoration
records. The checker requires the exact enumerated failure and invalid-term cases, validates
their refusal outcomes and restoration receipts, and retains the earlier positive-query precision,
coverage, labels, encoded-byte and projection checks. The runtime needed no further correction
after the arity repair.

The final private packet is
`F:/repos/sre-agents/.eval-runs/backlog-four-atlas/full-comparison-07/`.
`extension-source.json` binds the inherited 25-case receipts by hash; the original 04 packet and
archive remain untouched. The archive below contains final raw observables, all exact proposed
exceptions and per-delta rationales, mutation/restoration receipts, engine files, capture/disposition
drivers, the explicit reviewed-addition identity inventory, the actual arity red receipt and inherited
06 receipts. ZIP CRCs and all **41 recorded artifact-member hashes** passed after packaging.

| Final retained artifact | SHA-256 |
|---|---|
| `graph-004-comparison-c9fb5bf7.zip` (28,906,654 bytes) | `0f434ba8e4514766ce0adc15b0755a5593a3cfb75d6523ef3738dac418a1563c` |
| Packet hash manifest | `c3a27be3df317023bb8b0cc27da70f72e75c973aa46145cccb49242a0efbc388` |
| Exact proposed exceptions | `283f7df5790fe9b28e468eca8a99d64a1194953611ed5bdedc04478894ab6eb5` |
| Disposed strict report | `b45d72d8a8b6f0b9c02484e46069f61a28d6cd77cbdae4ab95f5add7da86e479` |
| Failure mutation/restoration receipt | `ab501176ebd2d43c82804db0aa6967765f5cc4c8a62bf962132bf06a39d9805b` |
| Eleven-file implementation manifest | `173d8ffa1991936fc5d285ba15dc28d1183b0646780407369be63121056b81d4` |

The archive is under `F:/repos/sre-agents/.eval-runs/backlog-four-atlas/`.

## Final independent disposition

[sourced: independent reviewer] The bounded follow-up approved the `10d4c61d..c9fb5bf7`
predicate-validation correction and regression, plus the hash-bound `full-comparison-07` packet.
It verified all 41 packet hashes, eleven fixture implementation hashes, the 25 inherited cases,
nine added failure cases and restoration per runtime, and all 2,161 exact proposed dispositions.
No remaining concrete defect was found. This closes the earlier comparison-coverage finding;
the reviewer inspected source and recorded evidence without executing candidate code or tests.
The previously approved implementation audit retains its original scope.

The reviewed report before this disposition paragraph had SHA-256
`ac4860b5e2a531e43e0696ed5fe1831d67ef323af8417d77d871956ff4bc9cf6`;
the archive retains the final hash recorded above. Human acceptance of the exact candidate and
its explicit compatibility corrections remains required. Neither the measured match nor the
independent review approves adoption or establishes current operational truth.
