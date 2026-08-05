# Fleet naming audit and the graph-engineering framing

- Date: 2026-08-05
- Status: evidence/history (live follow-ups are tracked in `docs/fleet-roadmap.md` only)
- Scope: the component-namespace audit that produced the `observability-engineer`, `save-toolkit`,
  and `language-idiom` renames, and a mapping of this fleet onto the emerging "graph engineering"
  framing.

## 1. The audit: substring collisions are a bug class, not a one-off

Three renames in one arc, all the same defect shape — a component name contained inside another
identifier, meeting tooling that matches by substring:

| Collision | Where it bit | Status |
|---|---|---|
| `sre` ⊂ `sre-steward` | Generator needed a longest-first workaround; two boundary evals false-passed on the wrong lane | Fixed: renamed `observability-engineer` |
| `sre` ⊂ `sre-agents` (the plugin) | Any grader asserting bare `"sre"` was satisfied by any answer naming any component; unfixable by agent renames | Fixed: plugin renamed `save-toolkit`; the two dependent graders tightened to boundary regexes |
| `craft` ⊂ `backend-craft`/`frontend-craft` | Latent (generator rewrites agent names only; no grader asserted it) | Fixed: renamed `language-idiom` |

Lessons the fixes encode:

- **Names are node identifiers, not prose.** Every mechanism that consumes them — eval graders,
  the adapter generator's token rewriting, the stale-name scanner, the readonly guard's
  `agent_type` matching — needs them to be unambiguous tokens. `check_stale_names.py` now records
  the corollary: a common English word (`craft`) cannot be machine-protected after retirement,
  which is an argument against common words as component names in the first place.
- **Renames have second-order failure modes in the enforcement layer.** The readonly guard
  fail-opened under a renamed plugin namespace (`[verified]`: `rm -rf` allowed under the new
  namespace before the fix) — it now fails closed on any unknown namespace whose bare agent name is
  guarded. The Codex installer would have orphaned every previously installed file on a marker-text
  change — it now claims legacy markers while writing only the current one.
- **Short grader tokens are the same defect at the vocabulary level.** `[verified]` against one
  sentence of ordinary incident prose: `sev` matches "Several", `ci` matches "de**ci**sions",
  `sha` matches "shared", `tas` matches "Tasks". Open follow-up; see §3.

## 2. The graph-engineering framing, mapped onto this fleet

"Graph engineering" is the 2026 term (following prompt → context → loop engineering) for treating
a multi-agent system as an explicit graph: agent role definitions as job descriptions — domain
owned, tools accessible, context preserved — plus inter-agent message routing, node failure
isolation, state consistency, dynamic node spawning, and graph observability. *[sourced:
https://www.explainx.ai/blog/graph-engineering-ai-agents-multi-agent-organizations-2026 ;
adjacent: https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph ,
https://github.com/BUPT-GAMMA/Awesome-Graph4LLM — post-cutoff material, labels not upgradeable
beyond the cited pages]*

This fleet already implements most of that vocabulary, under different names:

| Graph-engineering concern | This fleet's mechanism |
|---|---|
| Nodes with job descriptions | The roster: each agent = lane + tool posture + delegation list (`AGENTS.md` table, `agents/*.md`) |
| Edges as data, default-deny | `EXPECTED_DELEGATION` in `validate_fleet.py` — a machine-checked adjacency list; the 2026-07-13 spec's phrasing was already "the graph is data in the validator — default deny" |
| Node identity integrity | This audit: pairwise substring-free component names; guard fails closed when a guarded node appears under an unknown namespace |
| Routing function | Descriptions select lanes; the `discovery-*` evals are edge tests (given this input at this node, does traffic take the right edge?) |
| Edge-selection ambiguity as a bug | The TypeScript double-claim (`frontend-craft` vs the language files) was two nodes claiming the same input with no tie-breaker — fixed by narrowing the descriptions |
| Node failure isolation | Tool absence (platform-enforced) and the readonly-guard allowlist; OS least-privilege beneath both |
| State consistency across hops | The handoff packet convention: evidence labels never upgraded in transit, pinned SHAs, taint marked |

Where this fleet is more honest than the framing usually is: it documents which edges are
**enforced** and which are **convention** — `Agent(target)` lists are enforced for main-thread
agents and silently ignored at subagent depth (probed platform fact, recorded in
`claude-code-frontmatter.md`). A graph description that doesn't distinguish drawn edges from
load-bearing ones overstates its own guarantees.

## 3. Open items surfaced by the audit (not yet roadmap items)

- **Short/echoed eval grader tokens.** ~9 `contains_any` tokens ≤4 chars false-match ordinary
  prose (`sev`, `ci`, `sha`, `tas`, and peers); many longer tokens echo the scenario prompt, which
  is benign for substance checks but worthless for routing assertions. Fix shape exists: the
  boundary-regex treatment already applied to the two bare-`sre` graders.
- **A collision check as structural law.** `gate_a` could assert (a) no component name is a
  substring of another and (b) no grader asserts a bare component name or a sub-5-char token.
  Everything in §1 becomes a build failure instead of an audit finding. The `sde`
  required-skills list is likewise prose today — the one routing table no validator checks; making
  skill-load edges data the way delegation edges already are would extend the §2 table's second
  row to the skill layer.

Neither is scheduled; promoting either to the roadmap is a maintainer decision under the roadmap's
item contract.
