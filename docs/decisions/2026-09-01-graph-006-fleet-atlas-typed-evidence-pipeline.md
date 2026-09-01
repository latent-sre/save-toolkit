# Refactor `fleet-atlas` around a typed, evidence-bound pipeline

- **Date:** 2026-09-01
- **Status:** Proposed (revision 2, after principal consult)
- **Decision owner:** Save Toolkit maintainers
- **Backlog item:** [`GRAPH-006`](../fleet-roadmap.md)
- **Donor revision under measurement:** `21dc443b55527d5955713c471fe6168644fac12b`
  (branch `work/graph-004-fleet-atlas`, [PR #205](https://github.com/latent-sre/save-toolkit/pull/205))

## Context

PR #205 went through four review-and-repair rounds. Each round closed its findings; the next round
opened comparable ones at the same four boundaries. The tenth finding re-opened a defect that had
already been repaired twice. That pattern is evidence about the design, not about the repairs.

All measurements below were taken at donor revision `21dc443b`. `scripts/`, `evals/`, `schemas/`,
and `skills/` are byte-identical between the reviewed revision `d0e83c2f` and `21dc443b`
(`git diff --stat d0e83c2f 21dc443b -- scripts/ evals/ schemas/ skills/` is empty), so every open
finding is live at donor HEAD.

### Six structural causes

| # | Cause | Measured evidence | Label |
|---|---|---|---|
| 1 | A repository path is treated as entity identity | `_path_index()` (`fleet_atlas_extract.py:544`) collapses by type priority and drops a path when no node there has a priority type and more than one node exists; `node_for_path()` (`:246`) is first-insertion-wins; `fleet_atlas_detect.py:50` is a last-wins comprehension. On `docs/roadmap-closed.md` the three disagree in one tree: `SAFE-001`, `GRADER-005`, and nothing. 17 paths carry more than one node, **and 4 of those still collide after adding node type** (`roadmap-closed.md` 34 roadmap-items, `fleet-roadmap.md` 20 roadmap-items, `rules.md` 16 rules, `AGENTS.md` 8 capabilities). 57 nodes are unreachable by path | `[verified]` |
| 2 | Node creation is order-dependent and unmodelled | `ensure_document()` (`:253`) is lookup-then-create against shared graph state at 5 call sites, forced by `Graph.add_node` raising on duplicate ids (`fleet_atlas.py:135`). Moving `extract_documents` to last changes the output: `document:docs/rules.md` disappears and 4 edges differ. No shuffle test exists | `[verified]` |
| 3 | Evidence attached by convention, and sometimes fabricated | `find_line()` (`:34`) returns line 1 when its needle is absent, at 12 call sites. 464 of 815 nodes (57%) carry exactly one span pinned at `lines: [1, 1]`; 1,470 attributes sit on those nodes, and 37 edges also carry a `[1,1]` span | `[verified]` |
| 4 | Four independent validation surfaces, no single trust boundary | `provenance_failures` (`fleet_atlas.py:332`), `manifest_failures` (`:369`), `projection_failures` (`:378`), `fleet_atlas_cite.parity_failures` (`:126`). `cmd_query` re-implements `apiVersion` and digest checks inline, then rebuilds the whole graph through `projection_failures`, which runs `provenance_failures` a second time | `[verified]` |
| 5 | Renderers receive loose dictionaries and synthesise facts themselves | Markdown views emit 365 evidence labels; CLI query output emits 0, because `_class_field` (`fleet_atlas_views.py:57`) is never reached from the CLI path. `_where()` (`:52`) renders only `evidence[0]` and only its start line. Views cap at 20,000 bytes and **two already truncate today** (`claim-to-eval-map.md` 19,863; `skill-reference-loading-map.md` 19,894); `query` bounds by `QUERY_LIMIT = 20` results, so `query state docs/fleet-roadmap.md` emits 66,125 bytes and `query verified-by software-engineer` 39,566 bytes, LF-normalized | `[verified]` |
| 6 | No enforcement point on the real tree | `.github/workflows/` contains only `validate.yml`; `grep -rn fleet_atlas .github/workflows/` returns nothing. No CI step runs `fleet_atlas.py build`, `check`, or `query` against the real repository | `[verified]` |

Cause 6 is why causes 1 through 5 became chronic, and it is the one this design fixes first.

Cause 5 has a narrower companion worth stating precisely, because revision 1 of this record
overstated it. Exit code 1 is overloaded (`fleet_atlas.py:605` for zero results; `:566-587` for a
missing atlas, unparseable JSON, wrong `apiVersion`, stale provenance, and projection drift). An
*invalid* atlas is nonetheless distinguishable today: it returns before printing an envelope. What is
**not** distinguishable is the pair that mattered — a broken resolution and a correct negative both
emit exit 1 with a well-formed envelope carrying `count: 0`:

| Case | Exit | Envelope |
|---|---|---|
| `query evidence-for EVAL-003` — resolution broken | 1 | `count: 0` |
| `query owner-of fleet-atlas` — edge never emitted | 1 | `count: 0` |
| `query governs adapters` — correct negative | 1 | `count: 0` |

Those three are indistinguishable to any consumer, which is how the path-index defect survived three
repair rounds. Acceptance criterion (10) — every material finding has a named regression — requires
this pair to be separable.

`skills/fleet-atlas/SKILL.md:68` instructs the consumer to "lead with the answer and its evidence
label", and the CLI it directs them to produces no label. A compliant consumer must invent one.

## Decision

Four boundaries, not seven stages. "Discover" is part of source loading, index freezing is an
internal transition, and detection is an extractor that emits inferred facts:

`extract typed facts` → `resolve typed references` → `verify immutable graph` → `project / query`

### 0. The enforcement point comes first

Slice **S0** wires a real-tree contract run into CI before any pipeline work lands: `build` on a clean
checkout, `check` against the committed artifacts, and a fixed set of `query` invocations whose
`outcome` and non-empty results are asserted — including `evidence-for EVAL-003` and
`owner-of fleet-atlas`, which must fail today. S0 makes every later slice observable and is the only
slice worth landing even if the rest of this record is rejected.

### 1. Reference resolution with a selector

Adding a node type is not sufficient: four of the seventeen colliding paths hold many nodes of one
type. Resolution therefore takes an explicit selector and never hands an ambiguous set to a caller.

```python
@dataclass(frozen=True)
class NodeRef:
    path: str
    node_type: str
    selector: NodeId | ItemId | Anchor | LineRange | WHOLE_DOCUMENT

def resolve(self, ref: NodeRef) -> Node     # raises AmbiguousReference / UnresolvedReference
```

A markdown link carrying no anchor resolves to `WHOLE_DOCUMENT` — the honest reading of a link whose
target is `docs/roadmap-closed.md` with no `#fragment` — and a link to a specific item must carry an
anchor or item id. `_path_index()`, `node_for_path()`, and the `detect.py:50` comprehension are deleted, not
repaired. Ambiguity becomes a build-time error naming the candidates, never a silent pick.

### 2. Deterministic node creation

No extractor reads the graph. Each emits candidate facts into its own bucket, declaring its inputs and
required predecessors as data; a merge stage keys by node id, merges attributes, and orders by
`(node id, extractor name)`. `ensure_document()` disappears, and with it the lookup-then-create race
that makes registration order load-bearing. The shuffle test asserts byte-identical output across
permuted registration — criterion (2)'s entire content, and absent from the donor suite today.

### 3. Facts and proofs

`Claim(value, spans)` is not enough: requiring *a* span does not establish that the span has standing
to determine the value, nor that every determining span was supplied.

```python
Fact(subject: NodeId, predicate: Predicate, object: Scalar | NodeId, proof: Proof)

Proof(
    kind: EXTRACTED | NORMALIZED | COMPUTED | JOINED | INFERRED | ABSENCE | DEBT,
    inputs: tuple[Span | FactRef, ...],   # non-empty
    evaluator: str,                        # named, versioned transformation
    scope_digest: str | None,              # required for ABSENCE
)

Span(path, blob_hash, start_line, end_line, excerpt_hash)
```

Each proof kind carries its own validity rule, replacing the single under-specified `supports()`:

| Kind | Rule | Answers |
|---|---|---|
| `EXTRACTED` | re-parse the span with the named parser; the parsed field equals the value | catalog-field and decision-status findings |
| `NORMALIZED` | re-run the named normalizer over the raw span | `manual_only`, roadmap status, decision state |
| `COMPUTED` | re-run the named deterministic transformation over declared inputs | `bytes`, hashes, stable ids |
| `JOINED` | evaluator returns the **complete** input set; every returned span is cited | batch-to-review, guard roster, generated-from mapping |
| `INFERRED` | rule id plus all premises; class stays `STATIC_INFERRED`, never promoted | capability ownership, prose dependencies |
| `ABSENCE` | closed-world `scope_digest` plus the predicate searched | uncited-review and probe-linkage unknowns |
| `DEBT` | carries no support; forces `outcome: unverified` on anything it reaches | the placeholder census |

Two properties this buys that revision 1 did not have:

**Authority is separate from containment.** A span proves containment; whether that file may
*establish* the claim is a second, declared question. Each predicate names the source kinds allowed to
establish it — delegation facts from `agents/*.md` frontmatter and `validate_fleet.EXPECTED_DELEGATION`
only, never from a test or scenario file. Without this, criterion (5) is unmet: `scripts/test_*.py` and
`evals/scenarios/**` are canonical inputs, so a span pointing at a fixture literal would satisfy any
containment-only check.

**Completeness is asserted, not hoped for.** `JOINED` evaluators return their full input set and the
build cites all of it, which is what the batch, catalog, guard-roster, and mapping findings require.
A roadmap line proves "batch X was named"; it cannot prove "batch X resolves to review Y".

`find_line()` is removed; a locator that cannot find its needle raises.

**Debt.** `Proof(kind=DEBT)` replaces the allowlist and is keyed by **fact id**, covering the 37 edge
placeholders a `(node_id, attribute)` key could not express. Under the fact model the census is
roughly 1,934 keys, not 464. A frozen baseline is committed once; CI asserts the live debt set is a
**subset** of it — a count-only assertion would permit remove-one-add-one indefinitely. A rename that
orphans a key is repaired through a documented rekey procedure that rewrites the baseline in the same
commit, so ordinary content work is never blocked. Debt must be empty before the v2 cutover.

### 4. Typed graph semantics

`Graph.add_edge` today validates provenance class and id uniqueness but not endpoint existence, so
dangling edges are representable (none are live). Each predicate declares allowed endpoint types and
cardinality — `owns` is `owner|agent → skill|command|capability|roadmap-item`; `evidenced_by` is
`roadmap-item|decision → review|decision` — and the constructor rejects unresolved or ill-typed
endpoints. Resolution alone cannot prevent a semantically wrong edge.

### 5. One trust boundary

No document reaches query or render except as a `VerifiedDocument`, which only the verifier can
construct. That is the difference between one trust boundary and four methods on one class.

The verifier covers `apiVersion`, canonical-input digest, manifest membership, projection parity,
freshness, and revision provenance. Revision provenance compares canonical paths whenever the recorded
object exists and accepts a reachable non-ancestor revision only when that diff is empty. Framed
accurately: `treeDigest` already binds canonical *content* (`fleet_atlas.py:340`), so what the `:356`
early return leaks is a false *revision label* that propagates into every view header and query
envelope. Real, worth fixing, not a content-integrity hole.

**Query rebuilds.** Projection parity is regenerate-and-compare by definition, so a query that does not
rebuild cannot detect projection drift, and criterion (6) requires it to. No latency requirement is
recorded anywhere, so v2's query re-verifies and rebuilds exactly as v1 does. If a measured bottleneck
appears, cache by canonical-input digest; do not add an unverifiable fast path first.

**Canonical inputs.** `.github/` and `platforms/` determine `generated-projection` nodes and
`generated_from` edges through `tracked_expected_outputs()` (`cite.py:83`) but are absent from the
570-file digest set, so two checkouts with equal `treeDigest` can produce different graphs. Both trees
join the canonical set.

**Freshness is advisory.** Broadening staleness beyond `active` would otherwise turn 7 live `unknowns`
into `check` failures on the real tree at S3. Freshness findings remain `unknowns` and are reported;
they do not fail `check`.

### 6. Projection

Renderers receive only verified `Fact` objects and may choose layout, but cannot synthesise class,
evidence, or state from dictionaries. Text, JSON, and Mermaid share one fact iterator with per-
projection adapters — Mermaid cannot consume a text line, so a shared string formatter alone is
insufficient. The text adapter emits:

```
subject | predicate | object | CLASS [label] | path:line[, path:line ...]
```

so node state lines and edge lines carry citations by construction, all spans render, and CLI results
carry the `[verified]` / `[sourced]` / `[unverified]` label the SKILL.md contract requires.

**Budgets.** Criteria (8) and (9) are in real tension: two views already truncate at 20,000 bytes, and
S4 adds labels and additional spans to lines already at the cap. Capping `query` at 20,000 bytes while
returning full node objects with embedded evidence would discard roughly 70% of
`query state docs/fleet-roadmap.md`. The resolution is representational, not lossy: **`query` returns
compact fact lines by default** — which is what the originating finding proposed — and full objects
only under an explicit flag carrying no budget. Every projection is bounded by encoded UTF-8 bytes
against its own budget (20,000 detail view, 4,000 index, 20,000 compact query) with one record that
names the budget that actually applied, reserves its own bytes, and defines behaviour when a single
result exceeds the budget:

```json
{"truncated": true, "omittedResults": 41, "budgetBytes": 4000, "encodedBytes": 3987}
```

This replaces v1's prose marker, which hardcodes `20000 bytes` (`fleet_atlas_views.py:11`) yet is also
emitted for the 4,000-byte index cap (`:97`), so a truncated `INDEX.md` misreports its budget by five
times and states no omitted count. `.mmd` output is capped on the same mechanism; today it is uncapped.

### 7. Compatibility boundary and exit codes

v1's CLI, schema, and generated filenames are untouched for as long as any consumer uses them. v2 ships
as a **separate entrypoint writing a separate output directory**, which is what makes per-consumer
cutover and rehearsed rollback possible.

Because v2 is a new surface, giving it a correct exit contract breaks no v1 consumer, so it is defined
correctly from day one rather than deferred:

| Code | Meaning |
|---|---|
| 0 | query ran against a verified atlas — **including a legitimate empty result** |
| 1 | atlas missing, invalid, stale, unverified, or drifted |
| 2 | invalid command, verb, or arguments |

Every outcome, success and failure alike, emits a machine-readable envelope carrying `outcome`
(`results`, `empty`, `unverified`, `drift`). v1's failure paths print no envelope at all, so adding
`outcome` to success envelopes only would not have removed the opacity.

> **Owner decision required.** This reverses the earlier instruction to keep exit 1 overloaded and split
> it at cutover. That instruction was given to avoid a v1 compatibility break; a separate v2 surface has
> no v1 consumer to break, so the original goal is preserved while the defect that hid four rounds of
> regressions is not carried forward. If the owner prefers the deferral anyway, only this subsection
> changes.

### 8. Migration slices and rollback

| Slice | Adds | Consumer switched | Reversal | Requires |
|---|---|---|---|---|
| S0 | CI real-tree `build`/`check`/`query` contract run | none | revert commit | — |
| S1 | `NodeRef` resolution, deterministic merge, typed edges | none (v2 dir only) | revert commit | S0 |
| S2 | `Fact` / `Proof`, authority table, DEBT baseline | none (v2 dir only) | revert commit | S1 |
| S3 | Verifier and `VerifiedDocument` | v2 `check` | revert commit | S2 |
| S4 | Fact projection and all adapters | v2 views | revert commit | S2 |
| S5 | Budgets, truncation record, `outcome`, v2 exit codes | v2 `query` | revert commit | S3, S4 |
| S6a | Point consumers at the v2 surface, one at a time | per consumer | repoint that consumer | S5 green in CI |
| S6b | Delete v1 after measured consumer retirement | none | revert commit | no consumer on v1 |

**Rollback is reverting the commit, not flipping a flag.** A flag cannot roll back S1, S2, or S4: each
changes generated bytes, those bytes are committed, and `check` byte-compares committed artifacts
against a fresh render (`fleet_atlas.py:400-404`). Flag-off would leave new bytes on disk and an old
renderer producing old ones, so `check` would report `drift:` and a rollback would be indistinguishable
from corruption. Writing v2 to its own output directory removes the collision: v1's artifacts are never
rewritten, so reverting a v2 commit restores a consistent tree.

`metadata` gains a `pipeline` field recording which implementation and slice set produced the
artifacts, so `check` can always separate a rollback from real drift.

Slices are individually reversible but form a dependency chain: a slice carrying dependents is reverted
after them, last-in first-out along `Requires`. S0 has no prerequisites. S6a is per-consumer and
independently reversible by repointing that consumer.

**The comparator.** Criterion (1) requires comparing every recorded observable before switching, and
v1/v2 differ deliberately in evidence, labels, bytes, truncation, and `outcome`. The comparator is
therefore field-by-field with an explicit expected-delta list per slice, not a byte diff — a byte
comparison would fail by design at S4.

## The v1 observable contract

Frozen from donor revision `21dc443b`. This is the record criterion (1) compares against.

**CLI.** `fleet_atlas.py [--root ROOT] {build,check,query}`. `query <verb> <terms...>` with verbs
`governs`, `owner-of`, `loads-for`, `supersedes`, `depends-on`, `blocks`, `verified-by`,
`evidence-for`, `generated-from`, `state`.

**Exit codes.** `build` 0. `check` 0 pass / 1 fail. `query` 0 with results, 1 with zero results, 1 on
missing atlas, unparseable JSON, wrong `apiVersion`, stale provenance, or projection drift, 2 on an
invalid verb or terms. Failure paths emit no envelope.

**Envelopes.** Atlas `save-toolkit/fleet-atlas/v1`, kind `FleetAtlas`, top-level `apiVersion`, `kind`,
`metadata`, `nodes`, `edges`, `unknowns`. Query result `save-toolkit/fleet-atlas-query-result/v1`,
top-level `apiVersion`, `atlas`, `count`, `query`, `results`, `truncated`; `atlas` holds `dirty`,
`revision`, `treeDigest`. Edge results hold `attrs`, `class`, `evidence`, `id`, `kind`, `resultType`,
`source`, `sourceNode`, `target`, `targetNode`; node results hold a different key set — `attrs`,
`authority`, `evidence`, `id`, `name`, `path`, `resultType`, `state`, `type`. Both shapes are frozen.

**Labels.** `_class_field` (`fleet_atlas_views.py:57`) maps `CONTRACT_RESOLVED` and `STATIC_EXTRACTED`
to `verified`; `OPERATOR_CONFIRMED` to `sourced`; `STATIC_INFERRED` and `UNKNOWN` to `unverified`; any
unrecognised class falls back to `unverified`. Rendered `CLASS [label]`. Markdown views emit this; CLI
results do not.

**Citations and truncation markers.** A citation renders as `path:line` from `evidence[0]` only
(`_where()`, `:52`). View truncation appends a literal prose line naming 20,000 bytes (`:11`) for both
the 20,000 and 4,000 caps. Query truncation is the boolean `truncated` with `QUERY_LIMIT` 20. Unknown
groups larger than `COLLAPSE_THRESHOLD` 5 are summarised with an elided count.

**Vocabularies.** 20 node types, 15 edge kinds, 5 provenance classes, 5 authority values, 7 states.
`blocks` is in the edge enum but no extractor emits it; the `blocks` verb is a reverse traversal of
`depends_on`. v2 preserves the behaviour and records the gap as an `ABSENCE` proof over the extractor
corpus rather than as prose.

**Determinism.** JSON at `indent=2`, `sort_keys=True`, LF newlines, trailing newline; nodes and edges
sorted by id; unknowns by `(code, path, message)`; manifest entries sorted. `VIEW_CAP` 20,000,
`INDEX_CAP` 4,000, `COLLAPSE_THRESHOLD` 5, `QUERY_LIMIT` 20. Generated filenames: `INDEX.md`,
`atlas.json`, `manifest.json`, `capability-owner-map.md`, `claim-to-eval-map.md`,
`contradictions-and-stale-evidence.md`, `decision-supersession-map.md`, `roadmap-dependency-map.md`,
`skill-reference-loading-map.md`, `delegation.mmd`, `roadmap-dependency-map.mmd`.

**Deliberately changed in v2, and carved out of the frozen set.** `QUERY_LIMIT` and the meaning of
`truncated`, replaced by byte budgets and the truncation record at S5. `attrs["bytes"]` for the 154
skill and reference nodes taken from filesystem `st_size`, which is not reproducible across checkouts;
the 199 generated-projection nodes already use in-memory `len(content)` (`cite.py:104`) and are
unchanged. `render_all()`'s in-place overwrite of `metadata.revision` and `dirty` before the drift
compare, which excludes both fields from drift detection; v2 compares them through the verifier.

## Findings traceability

| Finding | Cause | Named regression |
|---|---|---|
| Preserve decision nodes when linking roadmap evidence (`extract.py:914`) | 1 | `test_evidence_link_resolves_by_selector_not_path`; `evidence-for EVAL-003` returns the decision edge. The `evidenced_by` target union is declared in the predicate table |
| Link declared component owners to the owned skill (component skip at `extract.py:841-842`) | **missing emission, not resolution** | `test_owner_field_naming_a_component_emits_owner_to_component_edge`. A typed index cannot cause an edge that is never emitted; the extractor must stop skipping components |
| Cite all catalog fields used by schema nodes (`extract.py:752`) | 3 | `test_catalog_node_proof_is_extracted_over_every_contributing_field` |
| Cite the target review line for batch-resolved evidence (`extract.py:940`) | 3 | `test_batch_edge_proof_is_joined_and_cites_both_sides` |
| Cite the guarded-agent roster on guard edges (`cite.py:55`) | 3 | `test_guard_edge_proof_is_joined_over_roster_and_hook_wiring` |
| Cite the mapping body for generated-from edges (signature cited at `cite.py:99`) | 3 | `test_generated_from_proof_cites_mapping_span_not_signature` |
| Emit citations for roadmap state facts (roadmap lines render at `views.py:160`) | 5 | `test_every_projected_fact_carries_class_label_and_citation` |
| Compare every reachable recorded revision (`fleet_atlas.py:356`) | 4 | `test_reachable_non_ancestor_revision_with_differing_inputs_is_rejected` |
| Check evidence age for every dated live status (predicate at `detect.py:122`) | 4 | `test_staleness_applies_to_every_dated_live_status_as_unknown` |
| Bound query output by bytes instead of result count (`fleet_atlas.py:561`) | 5 | `test_query_bounded_by_encoded_bytes_with_truncation_record` |

Regressions for defects found during this consult and absent from the review:
`test_cli_results_carry_evidence_labels` (cause 5, `SKILL.md:68`);
`test_locator_raises_when_needle_absent` (cause 3);
`test_shuffled_extractor_registration_is_byte_identical` (cause 2);
`test_index_truncation_reports_its_own_budget` (cause 5);
`test_ci_contract_run_fails_on_empty_flagship_queries` (cause 6);
`test_canonical_digest_covers_github_and_platforms` (cause 4);
`test_no_dangling_edges` (cause 4, latent).

## Acceptance criteria traceability

| Criterion | Mechanism |
|---|---|
| (1) new pipeline beside v1, compare every recorded observable | separate v2 entrypoint and output directory; "The v1 observable contract" is the record; field-by-field comparator with per-slice expected deltas |
| (2) shuffled registration is byte-identical | §2 deterministic merge; extractors never read the graph |
| (3) typed resolution preserves every node sharing a path | §1 `NodeRef` with selector; ambiguity raises and names candidates |
| (4) every attribute and edge cites every determining span | §3 `Proof`; `JOINED` returns the complete input set |
| (5) literals and fixture writes never become verification evidence | §3 authority table, distinct from containment |
| (6) build/check/query reject tampering through one verifier | §5 `VerifiedDocument`; query rebuilds |
| (7) two clean builds identical; merge/rebase checkouts | §5 revision provenance; canonical set extended to `.github/` and `platforms/` |
| (8) every rendered fact keeps class, label, citation | §6 fact projection |
| (9) CLI query *and* every index/detail view capped by encoded bytes | §6 compact fact lines by default; three budgets, one truncation record |
| (10) every material finding has a named regression | findings table above |
| (11) both paths available, each step reversible | §8 separate output directory, revert-based rollback, `pipeline` stamp, LIFO along `Requires` |
| (12) principal consult returns one durable record disposing evidence model, complete v1 boundary, phased cutover, rollback per slice | this record; the consult and its dispositions are below |
| (13) focused, component, eval, Gate A, determinism, CI, review | S0 wires the real-tree run; full set at the S6a boundary on one candidate |

## Principal consult disposition

Two independent adversarial reviews at donor head `21dc443b`, plus a factual audit of every
load-bearing claim. Both reviews returned "not approvable as written" against revision 1.

**Accepted and fixed in revision 2.** `(path, node_type)` leaves 4 of 17 collisions unresolved (§1
selector). Criterion (2) empirically false; order-dependence is in node creation, not iteration (§2).
Flag-off breaks `check` for every slice that changes committed bytes (§8 revert-based rollback plus a
separate output directory). One flag over six slices gives no per-slice rollback, and artifacts did not
record which pipeline built them (§8 `pipeline` stamp). `supports()` was circular for search-located
spans and could not deliver criterion (5) (§3 authority table). `supports()` had no derivation relation
and eight claim classes have no literal span (§3 proof kinds). `EVIDENCE_DEBT` could not key edge debt
and the census is ~1,934, not 464 (§3 fact-id keying). The debt allowlist self-blocked on renames and
its named regression enforced a weaker rule than the prose stated (§3 subset assertion plus rekey
procedure). Criteria (8)/(9) conflict at current data volume (§6 compact fact lines). No slice fixed
cause 6 (§0, S0). `query` "does not rebuild" contradicted criterion (6) (§5 query rebuilds). S5 broke
`QUERY_LIMIT` and `truncated`, which revision 1 had frozen through S5 (now carved out explicitly). The
canonical digest excluded `.github/` and `platforms/` (§5). Freshness as a verifier failure would break
`check` on the live tree (§5 advisory). No endpoint-type or cardinality validation existed (§4).
Renderers synthesised facts from dictionaries, and Mermaid cannot consume a text line (§6 adapters).
The owner-to-skill finding is a missing-emission bug, not a resolution bug — the traceability row was
wrong and is corrected. Exit codes: v2 takes the correct contract immediately (§7, owner decision
flagged). Seven factual and citation errors, three of them wrong `path:line`, corrected in Context.

**Accepted, narrowed.** The claim that empty and broken were wholly indistinguishable was too strong: an
invalid atlas is distinguishable by envelope absence. Narrowed, with measurements, to the pair that is
genuinely identical. The `:356` "tamper path" framing was overstated: `treeDigest` already binds
content, so the leak is a false revision label (§5).

**Accepted, deferred with reason.** The 107 `git ls-files` subprocess calls per build, the circular
imports worked around by six `sys.path.insert` calls and four function-local imports, and the
hand-rolled markdown and YAML parsing are real and unaddressed here. They are implementation hygiene
for the slice that touches each module, not architecture, and naming them as blockers would widen this
record past the four items criterion (12) asks it to dispose.

**Rejected.** The two definitions of "canonical input" (`_matches_canonical()` versus the git pathspec
list) were reported as a maintenance hazard rather than a defect: the reviewer attempted to construct a
divergence and could not — both yield the same 570 files at this tree. Recorded as a hazard, not fixed,
because an unproven divergence does not justify changing the digest boundary in the same record that
already widens it for `.github/` and `platforms/`.

## Rejected alternatives

**Keep the v1 structure and add a build-time invariant gate.** Cheapest, one new module. Rejected: it
detects rather than prevents, leaves the resolvers and renderers in place, and to catch the wrong-span
findings it needs the proof machinery anyway.

**Declarative extraction spec.** Extractors declare field-to-span mappings as data and the framework
attaches evidence. Strongest elimination of the citation class, but it rewrites all 15 extractors at
once and cannot be delivered in reversible slices, contradicting criterion (11). Reconsider if the
citation class recurs after S2.

**Continue repairing PR #205 finding by finding.** Rejected on the evidence in Context: recurrence of an
already-twice-repaired defect shows the boundary, not the patch, is wrong.

**A single `FLEET_ATLAS_V2` flag with both pipelines writing one output directory.** Proposed in
revision 1 and rejected during this consult: it cannot give per-slice rollback, and rollback becomes
indistinguishable from drift.

## Reopen trigger

Reopen if a finding class in the traceability table recurs after its slice lands; if the DEBT baseline
gains an entry outside a documented rekey; if the compact-fact-line representation still cannot meet
20,000 bytes on the flagship queries; if the two "canonical input" definitions are ever shown to
diverge; or if the owner keeps the v1 path after S5, which makes S6a, S6b, and the v2 exit contract
moot.

PR #205 stays open as implementation donor and review record. Closing or superseding it is a separate
owner decision that this record does not make.
