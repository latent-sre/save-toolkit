# GRAPH-004 decision packet — a fleet knowledge atlas

**Status:** Historical evidence captured on 2026-08-30. [The fleet roadmap](../fleet-roadmap.md) is
the only live backlog; this record does not queue work. Owner acceptance of the scope below was
given on 2026-08-30.

**Inspected:** `latent-sre/save-toolkit` at `4a745fb3` (main after PR #193); `sre-design` at
`318d011` on `feat/codebase-understanding`, for provenance and drift patterns only.

Labels: `[verified]` read from the named bytes or computed on the checkout; `[sourced]` cited from a
document or record; `[proposed]` a design choice the owner accepted; `[unverified]` stated, not
proven.

## Recommended scope

`[proposed]` GRAPH-004 is a **fleet knowledge atlas**: a deterministic, revision-bound graph over
the fleet's own canonical artifacts — 8 agents, 33 skills, 114 bundled references, 1 command,
23 decisions, 19 live roadmap items, 122 reviews, 136 eval scenarios, 38 test files, and 2
generated roots — that answers ownership, loading, governance, verification, evidence,
supersession, dependency, and contradiction questions with citations. It is the union of the graph
slices the fleet's checkers already compute implicitly plus the relations nothing computes today,
consumed through small generated views and a stdlib query CLI so that no consumer loads the whole
graph. Stage 1 is the static graph, views, and drift check; stage 2 is the query layer; GraphRAG is
not proposed and is gated behind five named prerequisites.

`[verified]` The need was demonstrated in one session rather than argued: the live roadmap said
GRAPH-002's "CI, review-thread acceptance, repository integration, and exact-candidate human
acceptance remain open" after PR #193 had merged (2026-08-30T04:04Z); it said `backend-craft` was
"in progress on its own branch" when `git branch -a` shows none; the item ID `EVAL-005` was claimed
by three branches in one day and caught only by CI on the merge result, as `ROUTE-004` had been
earlier in the week; 67 of 122 files under `docs/reviews/` are cited by filename nowhere else in the
repository (61 generated eval-evidence docs, which may be cited by batch ID instead, and 6
hand-written reviews) against a `docs/README.md` rule that an uncited review is removed, which no
checker enforces; and the fleet's knowledge is about 3.1 MB (agents 130 KB, skills 984 KB,
decisions 154 KB, reviews 1.5 MB, roadmap 72 KB, scenarios 255 KB) against the 5,000-token-per-skill
and 25,000-total post-compaction budget recorded in the
[2026-08-24 host context-budget audit](2026-08-24-host-context-budget-audit.md).

### How the scope differs from its neighbours

| Neighbour | What it is | Taken from it | Must not do |
|---|---|---|---|
| sre-design's code atlas (`sre-kb atlas`) | Tree-sitter parsing of application code: modules, imports, calls, package manifests, coupling metrics | `[verified]` Patterns only: an evidence-class enum with `UNKNOWN`; `path:line` + SHA-256 excerpt hash + named detector on every claim; `unknowns[]` with `neededEvidence` instead of empty confident edges; a sha256 file manifest with regenerate-and-compare drift; an explicit boundary config; no timestamps in generated output; "the committed JSON is primary, pages are projections" | Parse any application source, this repository's included |
| agent-authoring's delegation graph | `[verified]` One enforced source — each agent's `Agent(...)` grant checked against `EXPECTED_DELEGATION` in `scripts/validate_fleet.py` — and one render, the roster's "Delegates to" column, bound by `validate_roster_graph` | `delegates_to` edges cited from that source with provenance; a mismatch is a `contradicts` finding routed to agent-authoring's lane | Define, redesign, or arbitrate delegation; become a second authority for any enforced edge |
| workflow-graph-engineering | Executable workflow/state graphs | Nothing structural; it is a node like any skill | Execute anything |
| GRAPH-003 runtime observability | Indicators and alerts for a running graph, fed by telemetry | Nothing; GRAPH-003 is a roadmap-item node with a `depends_on GRAPH-002` edge | Ingest telemetry, hold credentials, describe live state |

## 1. Operator need and primary consumer

| Observed gap | Label | Question it maps to |
|---|---|---|
| GRAPH-002 status says four things "remain open"; PR #193 merged and heads main | `[verified]` | Which claims are stale? |
| SKILL-001 says `backend-craft` is in progress on its own branch; no such branch exists | `[verified]` | Which claims are unverified? |
| `EVAL-005` introduced by PR #189 and independently by two other branches the same day; `ROUTE-004` collided earlier | `[verified]` | Which roadmap item depends on or conflicts with another? |
| 67 of 122 reviews uncited by filename; the docs-map rule is unenforced; `check_evidence_refs.py` checks only roadmap→batch | `[verified]` by filename search; batch-ID citations would not count | Which evidence report supports a roadmap status? |
| Five operator-facing contradictions between skills (e.g. `obs-dashboards/references/http-api.md` "the main session can run them too" vs the sole invoked-agent exception in `AGENTS.md`) | `[sourced]` [2026-08-26 three-pass review](2026-08-26-repo-skills-non-eval-review.md) | Where do documentation and rules disagree? |
| `evals/README.md:194` says a negative scenario's response graders must pass; five scenarios record in their own comments that they follow the opposite routing-only precedent | `[verified]` | Where do rules and implementation claims disagree? |
| ~3.1 MB of knowledge against a 25,000-token budget | `[verified]` sizes; `[sourced]` budget | What to load without loading the repository? |
| The only fleet-level routing index is the hand-kept "Start here" table; 20 skills carry hand-kept "read first" tables | `[verified]` | Which references load for a task or predicate? |

**Consumers.** Primary: `agent-engineer` (edits prompts, skills, evals, graphs) and the human owner.
Read-only: `repository-investigator` (answers "which document is canonical for X" and "what verifies
Y" from views with `Read`/`Grep`/`Glob`), and `scribe` before proposing a new artifact. Automated:
the drift check, run with the component suites; not a Gate A step unless the owner decides so.

## 2. The questions the atlas must answer

| Question | Answered by | Computed today by | Missing |
|---|---|---|---|
| Which document is canonical for a fleet rule? | `rule` —`governed_by`→ source doc | `[verified]` `docs/rules.md` pairs 90 rule rows with a primary-source column; `check_links` resolves the links | Machine-readable rule IDs; a check that the source still contains the rule's substance |
| Which agent or skill owns a capability? | `capability` ←`owns`— `agent`/`skill` | Roster "Lane" column; skill descriptions; roster validated by `validate_roster_graph` | A capability vocabulary; ownership is prose |
| Which references load for a task or predicate? | `skill` —`loads_when(predicate)`→ `reference` | `[verified]` 20 routing tables; 135 skill→reference links; `check_links` proves reachability | Extracted predicates; cross-skill view; budget per path |
| Which decision introduced or superseded a rule? | `decision` —`supersedes`→ rule/decision; —`disposes`→ item | `[verified]` ADRs declare state (`DECISION_MARKERS`); 11 carry supersession or disposition lines | Resolved targets; a check that superseded text is gone |
| Which roadmap item depends on another? | item —`depends_on`/`blocks`→ item | `[verified]` `check_plan_status` parses IDs in **Prerequisites**, rejects self- and unknown references | Dependencies stated elsewhere in an item; cross-branch ID view |
| Which eval or test verifies a claim? | claim ←`verified_by`— scenario/test | `[verified]` scenarios declare `target` (36 distinct); 5 IDs cited in scenario comments; contract tests pin prose | Claims as nodes; test→skill pins discoverable only by reading test source |
| Which evidence supports a roadmap status? | item —`evidenced_by`→ review | `[verified]` 31 roadmap→review/decision links; `check_evidence_refs` resolves batch IDs | The reverse direction; status-vs-evidence staleness |
| Which generated adapters derive from a canonical source? | projection —`generated_from`→ canonical | `[verified]` `generate_platform_adapters.expected_outputs()`; byte-for-byte gate; `.ignore`; `schemas/catalog-v1.json` models `canonical_path`/`validator`/`generated_projections` | Nothing to compute; the 70 eval-evidence docs are unmodelled |
| Where do docs, rules, roadmap, and implementation disagree? | `contradicts` edges + report | Only roster/frontmatter parity and stale-name rejection | Everything else |
| What to load for a question without loading the repository? | views + query CLI | "Start here" table; skill routing tables | A fleet-level index; size discipline |
| Which claims are stale, unverified, superseded, blocked, or missing evidence? | node state + report | `HISTORICAL_MARKERS`; status banners on 98/122 reviews; retired names | A consolidated view; external-state staleness |

## 3. Static graph, query layer, optional GraphRAG

| Layer | What | Stage | Boundary |
|---|---|---|---|
| Static knowledge graph | Deterministic extractor over canonical files → `docs/fleet-atlas/generated/atlas.json` (schema-validated) + views + sha256 manifest + drift check | 1 | Reads bytes and declared structure only: frontmatter, roster, rules table, routing tables, ADR status lines, roadmap fields, scenario `target`/`routing`, generator mapping, catalog. Judgement is `STATIC_INFERRED` or `UNKNOWN`. No model builds it |
| Query / retrieval layer | Stdlib CLI `python scripts/fleet_atlas.py query <question> <arg>` for parameterised questions; pre-rendered views for the rest; agents without Bash use the views | 2 | Answers are projections carrying the atlas revision; no write-back; output capped |
| GraphRAG | Not proposed | — | Only after the static contract is accepted and the query layer measured. Any proposal must first define citation (node ID, `path:line`, excerpt hash, revision on every chunk), freshness (index revision equals atlas revision or the answer says so), access control (private text never leaves the host without a decision record; no external embedding service by default), contradiction handling (`contradicts` edges surfaced, never averaged), and retrieval evaluation (graded cited-answer scenarios measured before adoption). Product selection comes after all five |

## 4. Node and relationship vocabulary

`[proposed]` Two adjustments to the candidate lists: *canonical source* and *generated projection*
are an `authority` attribute on every node rather than node types; `owner` is a node type with
subtypes agent and human.

| Node type | Instances | Extracted from | Attributes beyond provenance |
|---|---:|---|---|
| `agent` | 8 | `agents/*.md` frontmatter | name, description, tools, guard-roster membership |
| `skill` | 33 | `skills/*/SKILL.md` frontmatter | name, description, argument-hint, manual-only (3), entrypoint bytes |
| `reference` | 114 (+52 bundle files) | `skills/*/references/*.md` | owning skill, bytes |
| `command` | 1 | `commands/*.md` | selected-agent precondition |
| `rule` | 90 | `docs/rules.md` rows | section, statement; stable row hash as ID until rules gain IDs |
| `decision` | 23 | `docs/decisions/*.md` | date, declared state |
| `roadmap-item` | 19 live + 11 closed | roadmap headings and bold fields; closed register rows | status, dates, six required fields |
| `review` | 122 | `docs/reviews/*.md` | banner (98), date, generated-from-run (70) |
| `scenario` | 136 + 6 build | `evals/scenarios`, `evals/build-scenarios` | mode, split, target, expect, expected_alternative, threshold |
| `test` | 38 files | `scripts/test_*.py`, `evals/test_*.py` | paths each test reads, from string literals |
| `schema` | 5 | `schemas/` + `catalog-v1.json` | validator, projections |
| `generated-projection` | 8 + 33 + 70 | `.github/agents/`, `platforms/copilot/skills/`, eval-evidence docs | authority = generated |
| `capability` | derived | roster Lane; skill descriptions | `STATIC_INFERRED` unless declared; no new authority |
| `owner` | 8 agents + named humans | roster; roadmap Owner; ADR owners | kind = agent \| human |
| `probe` | 2 | `docs/probes/` | live only while a roadmap item links it |

| Edge | From → to | Source of truth | Default class |
|---|---|---|---|
| `owns` | owner → capability/skill/item | roster Lane; roadmap Owner; ADR owners | `STATIC_EXTRACTED`; capability side `STATIC_INFERRED` |
| `routes_to` | task phrase → skill/doc; scenario → target | "Start here"; `Triggers:`; scenario `expect: fire` | `STATIC_EXTRACTED`, with `via` |
| `delegates_to` | agent → agent | cited, never derived: `Agent(...)` grants and `EXPECTED_DELEGATION` | `CONTRACT_RESOLVED` |
| `loads_when` | skill → reference, with `predicate` | routing-table rows; plain links get `UNKNOWN` predicate | `STATIC_EXTRACTED` |
| `governed_by` | rule → doc; skill/agent → rule | `rules.md` primary-source cells; AGENTS.md hard rules | `STATIC_EXTRACTED` |
| `constrained_by` | agent → guard/hook; skill → validator | `hooks/hooks.json`; guard roster; catalog validators; test literals | `CONTRACT_RESOLVED` for hook/validator; `STATIC_EXTRACTED` for tests |
| `verified_by` | skill/agent/claim → scenario/test | scenario `target`; test literals | `STATIC_EXTRACTED` |
| `evidenced_by` | item/decision → review or batch ID | links; `BATCH_ID_RE` | `STATIC_EXTRACTED` |
| `depends_on` / `blocks` | item → item | **Prerequisites** IDs as `check_plan_status` parses them; IDs elsewhere are `STATIC_INFERRED` | as stated |
| `supersedes` | decision → decision/rule/doc; name → name | ADR "Supersedes:" lines; `check_stale_names` retirements | `STATIC_EXTRACTED` when resolved, else `UNKNOWN` with prose kept |
| `generated_from` | projection → canonical; eval-evidence review → batch | `expected_outputs()`; batch IDs | `CONTRACT_RESOLVED` |
| `near_miss_for` | scenario → skill/agent, with `expected_alternative` | scenario `expect: not_fire` | `STATIC_EXTRACTED` |
| `contradicts` | any → any, with detector | the detectors in §7 | `STATIC_INFERRED` — a finding, never a fact |
| `cites` | doc → doc | Markdown links | `STATIC_EXTRACTED`; untyped fallback |

## 5. Canonical versus generated handling

- `[verified]` The rule and mechanism exist: canonical is `agents/`, `skills/`, `commands/`;
  generated roots are regenerated and checked byte-for-byte; `.ignore` hides them from `rg`.
- `[proposed]` Every node carries `authority ∈ {canonical, live-contract, generated,
  historical-evidence, external}` — the classes `docs/README.md` names. Rules, the roadmap, accepted
  decisions, and schemas are `live-contract`; reviews and closed items are `historical-evidence`;
  projections and eval-evidence docs are `generated`.
- `[proposed]` Generated nodes originate no edges; their relations are lifted from the canonical
  source with one `generated_from` edge back. Queries default to canonical; `--include-generated`
  inspects projections.
- `[proposed]` The atlas is itself generated: its views carry the generator banner, live under
  `docs/fleet-atlas/generated/`, are listed in the manifest, and get a `catalog-v1.json` entry with
  `canonical_path`, `validator`, and `generated_projections`. It has no authority over anything it
  describes.
- `[proposed]` A generated answer never becomes repository truth: a `contradicts` or stale finding
  is a report line; only a human edit or roadmap import changes what governs. The atlas has no
  write path outside its own generated directory.

## 6. Provenance requirements

| Field | Content | Reused from |
|---|---|---|
| Source path and section | repository-relative path; heading path or 1-based line range; SHA-256 of cited lines; named detector | sre-design `AtlasEvidence` |
| Source revision | full commit SHA; `dirty: bool`; `treeDigest` over canonical inputs | `scripts/evidence_envelope.py` `tree_digest` and `target_revision` |
| Canonical / generated classification | `authority` attribute | `docs/README.md` authority table |
| Evidence label | `[proposed]` `CONTRACT_RESOLVED` (a validator or generator enforces it), `STATIC_EXTRACTED` (bytes state it), `STATIC_INFERRED` (an extraction rule combined facts), `OPERATOR_CONFIRMED` (a named human, dated, in the source), `UNKNOWN`. Rendered answers map `CONTRACT_RESOLVED`/`STATIC_EXTRACTED` → `[verified]`, `OPERATOR_CONFIRMED` → `[sourced]`, `STATIC_INFERRED`/`UNKNOWN` → `[unverified]` | sre-design class enum; the fleet's `EVIDENCE_TRIAD` |
| Freshness or verification date | only a date the source states; the atlas adds no clock | determinism |
| Supersession state | `live` · `superseded-by <id>` · `historical` · `retired` · `proposed` · `rejected` · `deprecated` | `DECISION_MARKERS`, `HISTORICAL_MARKERS`, `ROADMAP_ITEM_STATUSES`, `check_stale_names` |
| UNKNOWN when evidence is absent | `unknowns[]` record with stable code and `neededEvidence`; never an empty edge | sre-design `AtlasUnknown` |

## 7. Freshness and drift detection

**Drift of the atlas.** `[proposed]` Regenerate on the same revision and compare byte-for-byte
against the sha256 manifest. Determinism rules: sorted output, no timestamps, no host paths,
`.eval-runs/` and the generated roots excluded from inputs. Run with the component suites;
promotion to Gate A is a separate owner decision.

**Staleness of what the atlas describes.** `[proposed]` Two kinds, kept apart. *Revision
staleness*: a consumer compares `metadata.revision` to `HEAD`; if different, answers are prefixed
"as of `<sha>`, N commits behind" and any node whose path changed since is answered `UNKNOWN`.
*Content staleness*: deterministic detectors that emit `contradicts` or `stale` findings from
repository bytes — a review cited by nothing (resolving batch IDs, not just filenames); a roadmap
item whose Source or Acceptance cites a review older than its status date; a decision whose
"Supersedes" target text still appears verbatim in the superseded document; a retired name in
canonical text; a scenario whose target no longer exists; a rule row whose linked section no
longer contains the rule's key phrase; a roster or frontmatter fact that disagrees with the
validator's literal.

**External state is a boundary, not a feature.** "Remain open" versus a merged PR cannot be
decided from the checkout. An optional `--probe-github` mode may read PR and branch state through
`gh` read-only calls, labelling every such finding `[sourced: GitHub API]`; its output is never part
of the deterministic baseline or the drift manifest. The same mode is the only way to detect an
item ID claimed on another open branch.

## 8. Just-in-time retrieval

`[proposed]` `atlas.json` never enters model context. Three surfaces, each bounded: an index view
under 1,000 tokens (the eleven questions, each pointing at one view or query form — the only
content the `fleet-atlas` skill body carries); generated views, one per unparameterised question,
each capped at 5,000 tokens by the generator with an explicit `UNKNOWN: view truncated` line rather
than an overrun; and the query CLI for parameterised questions (`owner-of`, `loads-for`,
`verified-by`, `supersedes`, `depends-on`, `evidence-for`, `generated-from`), one fact per line with
node ID, class, and `path:line`, line-capped with the same marker. Views are one fact per line with
stable IDs so a `Read`/`Grep`/`Glob`-only agent answers by grepping one small file. The budget is
enforced by the drift check.

## 9. Ownership

| Role | Owner | Why |
|---|---|---|
| Implementation | `software-engineer` for `scripts/fleet_atlas.py`, tests, schema and catalog entry, drift check; `agent-engineer` for the `fleet-atlas` skill text and scenarios | Tooling is the engineer's lane; skill text and evals are agent-engineer's |
| Read-only consumer | `repository-investigator`, `agent-engineer`, `scribe`; the human owner | All read views; none writes canonical files through the atlas |
| Knowledge acceptance | `latent-sre` | The atlas proposes findings; turning one into a canonical edit or roadmap item is a human act. `scribe`'s knowledge-closeout mode governs operational knowledge, not fleet meta-knowledge |
| Authorities deferred to | `agent-authoring`, `validate_fleet.py`, `generate_platform_adapters.py`, `check_plan_status.py` | Where a contract enforces an edge, the atlas cites it; parity is an acceptance test; disagreement means the atlas is wrong until a human says otherwise |

## 10. Acceptance tests and routing scenarios

1. **Schema and provenance.** `atlas.json` validates against `schemas/fleet-atlas-v1.schema.json`;
   every node has the seven provenance fields; every edge has one of the five classes and a
   `path:line` plus excerpt hash; every extraction failure is an `unknowns[]` record.
2. **Determinism and drift, by mutation.** Same revision → byte-identical. A renamed bundled
   reference → its `loads_when` edge becomes `UNKNOWN` and the drift check reds. A timestamp in a
   view → red.
3. **Parity with cited authorities, by mutating the atlas output.** `delegates_to` equals
   `EXPECTED_DELEGATION` and the roster render; `generated_from` keys equal `expected_outputs()`;
   `depends_on` equals the checker's Prerequisites parse; guard membership equals
   `GUARDED_AGENT_NAMES`.
4. **Golden answers.** Each of the eleven questions has a fixture answer on a pinned revision,
   asserted by a component test.
5. **Budget.** No view exceeds 5,000 tokens (bytes/4, fixed divisor stated in the test); the index
   view is under 1,000.
6. **Boundary.** `rg` proves the generator imports no application-code parser and no network
   module; Gate A green; PyYAML is confined to the component-test path.
7. **Prose contract.** The skill's exclusions list and "cited, never defined" sentence are pinned by
   a component contract test with a one-line mutation oracle.

| Scenario | Mode | Grades |
|---|---|---|
| `discovery-fleet-atlas-owner-of-capability` | discovery, fire | routes to `fleet-atlas`; names `observability-engineer`; cites the agent file and the AGENTS.md exception with `path:line`; states the atlas revision |
| `discovery-fleet-atlas-which-reference-loads` | discovery, fire | the `loads_when` edge with its predicate, the scenario targeting it, the class of each |
| `discovery-fleet-atlas-defers-delegation-design` | discovery, not_fire → `agent-authoring` | the atlas does not own delegation |
| `discovery-fleet-atlas-defers-code-graph` | discovery, not_fire → inline | consistent with the two existing near misses, which stay unchanged |
| `agent-direct-repository-investigator-atlas-citation` | direct | "as of `<sha>`" prefix; the unknown reported with `neededEvidence`; no upgrade of a `STATIC_INFERRED` edge |
| `agent-direct-agent-engineer-contradiction-is-a-finding` | direct | proposes a canonical edit for the human; does not edit; does not "fix" the atlas to match |

## 11. Risks, rollback, exclusions

| # | Risk | Mitigation |
|---|---|---|
| R1 | Competing authority: the atlas's delegation, generation, or dependency view drifts from the validators and is trusted | Parity tests red the build; the skill states "cited, never defined"; findings route to the owning lane |
| R2 | False contradictions from heuristic detectors | Detector output is `STATIC_INFERRED` and a report line, never a build failure or an edit; precision measured on the golden fixture before a detector ships |
| R3 | Drift noise | No timestamps, sorted output, canonical-root inputs only; eval-evidence docs enter by batch ID, not content hash |
| R4 | Context bloat | Caps are tests; truncation is explicit |
| R5 | External state leaking into the baseline | Probe mode writes an uncommitted report labelled `[sourced: GitHub API]` with no revision binding |
| R6 | Scope creep toward a code atlas or GraphRAG | The exclusions are acceptance criteria; the §3 prerequisites gate any proposal |
| R7 | A third generated root to maintain | Same discipline as the adapters; one stdlib script; views replace nothing hand-written |
| R8 | Over-reporting uncited reviews | The detector resolves `BATCH_ID_RE` as `check_evidence_refs` does before calling a review uncited |
| R9 | Secret hygiene | Views quote only committed canonical bytes; the query-catalog rule applies; nothing from `.eval-runs/` |

**Rollback.** Delete `scripts/fleet_atlas.py` and its tests, the `fleet-atlas` skill and scenarios,
the schema and catalog entry, and `docs/fleet-atlas/generated/`; close the item. No credential or
service exists, and no canonical document was written by the atlas.

**Exclusions.** No application-code AST, imports, calls, or package analysis; no runtime service
topology; no production telemetry ingestion; no executable workflow engine; no new
agent-delegation authority; no production access or credentials; no target-code execution; no
automatic rewriting of canonical human documentation; no GraphRAG before the static contract is
accepted; no generated answer silently becoming repository truth; no graph database or product
selection at this stage.

## 12. Roadmap text

Applied to `docs/fleet-roadmap.md` in the same change as this record.

## Evidence ledger

| Claim | Label | Where |
|---|---|---|
| Inventory counts; frontmatter key set; 90 rule rows; 23 ADRs with declared states, 11 with supersession or disposition lines; 19 live items and 11 closed rows; 136 scenarios (57 direct / 79 discovery; 57 regression / 79 calibration; 36 distinct targets); 20 routing tables; 135 skill→reference links; 31 roadmap evidence links; 98/122 review banners; 70 generated eval-evidence docs; byte sizes | `[verified]` | sre-agents @ `4a745fb3`, scripted inventories |
| What each checker enforces | `[verified]` | `scripts/check_plan_status.py`, `check_evidence_refs.py`, `validate_fleet.py`, `generate_platform_adapters.py`, `check_links.py`, `check_stale_names.py`; `schemas/catalog-v1.json`; `hooks/hooks.json`; `.ignore` |
| Stale claims | `[verified]` | roadmap lines 182 and 597 at `4a745fb3`; `gh pr view 193`; `git branch -a`; the PR #191 and #182 history |
| 67/122 uncited reviews (61 generated) | `[verified]`, method caveat stated | filename-mention search across `docs/`, root docs, `skills/`, `agents/`, `evals/`, `scripts/`, `commands/` |
| Five operator-facing contradictions | `[sourced]` | [2026-08-26 three-pass review](2026-08-26-repo-skills-non-eval-review.md) |
| 5,000 / 25,000 token budget | `[sourced]` | [host context-budget audit](2026-08-24-host-context-budget-audit.md) |
| sre-design patterns reused | `[verified]` | sre-design @ `318d011`: `src/sre_kb/atlas/model.py`, `evidence.py`, `runner.py`, `.sre/atlas.yaml`, `docs/CODEBASE-ATLAS.md`; none of its parsers or scope is adopted |

Repository evidence and external research are kept separate; this record contains no external
research beyond the sre-design files cited as pattern sources.
