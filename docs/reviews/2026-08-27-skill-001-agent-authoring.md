# SKILL-001 Phase 2 — `agent-authoring` disposition evidence

**Status:** Historical evidence captured on 2026-08-27. [The fleet roadmap](../fleet-roadmap.md) is
the only live backlog; this record does not queue work.

## Conclusion

`agent-authoring` is dispositioned as a **retained router with a recitation cut**: the always-loaded
entrypoint falls from 10,911 to 8,843 immutable bytes (−19%), the description is byte-identical,
and the bundle routes 36,754 reference bytes (66,628 at the base) against 8,843 retained. The cut is small by design:
the clean-room probes show both models already produce the general method this skill teaches, but
neither knows the fleet's decisions, and both author the Claude Code frontmatter facts wrong — so
the body keeps decisions, traps, the rule statements its references defer to, and the router, and
sheds only restated craft. It stays above the screen — 7,500 bytes since the owner reset it from
5,000 on 2026-08-27 — for that reason.

The slice also corrected the probe-first method itself: a "no skill" probe run as an Agent-tool
subagent inside this repository recites `AGENTS.md` and the memory index verbatim. The usable
baselines below come from the eval harness's clean room.

## Probe method and its correction

`[verified]` The first probes (one per model, in-repository subagents) quoted `AGENTS.md` hard rules
and memory-index hooks verbatim — the model aliases, "`Agent(target)` … documentary at depth",
"authority is host-specific", "a red grader is a finding, not an obstacle" — and are kept only as
evidence of that effect (`.eval-runs/agent-authoring-workspace/probes/contaminated-*.md`, gitignored).
Claude Code loads the project's `CLAUDE.md` → `AGENTS.md` and the session memory index into every
subagent, so those replies measured fleet context, not model knowledge. The `frontend-craft` record
now carries the same caveat; its findings stand because no UI rule lives in either file.

`[verified]` Clean-room reruns (`probes/clean_probe.py`): a bare `claude -p --tools ""` with no
`--plugin-dir`, `CLAUDE_CONFIG_DIR` holding only the credential file, cwd an empty git root outside
the repository, built from `evals/clean_room.py`. A grep for fleet-only phrasings on both replies
returned nothing. The roadmap's Phase 2 prerequisite now names this clean room.

## What the clean probes showed

Eighteen unhinted questions mapped to the body's rules, plus the skill's three `fire` discovery
prompts as a no-skill pressure control scored by the fleet's own graders (content only; routing
is not measured outside the harness).

| Rule in the body | Opus (clean) | Sonnet (clean) |
|---|---|---|
| Baseline before editing; minimal change | produced | produced |
| Description = routing, not procedure; the three symptom→fix pairs | produced | produced |
| Schema for machine output, exemplar/recipe for human output; no "unless it matters" | produced | produced |
| Tool schema before prompt text | produced | produced |
| Bounded-loop field list (entry, verifier, budgets, stops, promotion, evidence) | produced | produced |
| Skill over agent; edge only for isolation/authority | produced | produced |
| Untrusted artifacts as data; sticky evidence labels; human-only promotion | produced | produced |
| Source-trust gate terms (disposable harness, no secrets/egress, denied tools; delegation ≠ isolation) | not produced | not produced |
| Evidence-matching rule for routing edits (after-change only; rewording needs none) | approximate | approximate |
| Cite-only / date-as-fact-vs-provenance rule | approximate | approximate |
| Form table's pressure row (prohibition + rationalization table) | different answer (relocate the rule into the procedure) | different answer (mechanical gate) |
| Four-theme decision rule; `workflow-graph-engineering` boundary; handoff targets | not produced | not produced |
| Claude Code agent/skill frontmatter facts | wrong (`color`, `allowed-tools`, "Task tool", "inherits the parent's tools") | hedged ("not fully certain") |

Control scores: Opus discovery 3/3 and direct 1/3; Sonnet discovery 2/3 and direct 1/3. The
direct misses are mostly phrasing the regexes do not accept ("Safety/authority:" as a label,
"each delegation carries" rather than "handoff"); Sonnet's discovery miss is a missing adoption
condition. Recorded as phrasing sensitivity, not as knowledge gaps.

## The cut (10,911 → 8,843 bytes)

Retained verbatim or compressed: the source-trust gate; the evidence-matching and retest rules;
the cite-only rule; the description rule and the failure→form table (both are statements
`artifact.md` explicitly defers to); the four-theme rule; the graph boundary; the Loop Engineering
contract fields; the router; the platform traps as one paragraph; promotion and composition;
handoffs. Removed or folded: the "prompt text is not always the owner" paragraph (the control table
in `artifact.md` owns it — now a one-sentence pointer), the "narrow diagnosis examples belong in the
body" meta-paragraph, the method's restated steps 1 and 3 (one line each), the preamble's restated
untrusted-data rule (one line), and the runtime quick reference's prose around the facts the models
get wrong. Every statement a reference points at was grepped present after the edit `[verified]`.

Duplication was not the lever: the 2026-08-26 audit's "18 of 82 sentences echoed" finding was
already resolved by the dedupe commit that followed it; on `origin/main` `4f01f22` only two body
sentences echo a reference at Jaccard ≥ 0.5.

## Owner-preference trim of the references (66,628 → 59,529 bytes)

Not probe-driven: the owner asked for tables over paragraphs and for no pattern catalogs or vendor
commentary. The platform-traps section became a table. `roster.md` (19,474 → 15,289) lost its
multi-agent pattern catalog, the vendor-multiplier and BrowseComp asides, the Managed Agents/Dreams
comparison, the "evidence was refreshed" preamble, and the provenance footers — every rule in those
sections is retained; only the narrative around it went. `claude-code-frontmatter.md` (20,297 →
17,383) lost its dated changelog digest, whose bullets mostly said "nothing to change here";
the one decision in it — hook matchers fail open, so the guard scopes itself in Python — stays as
its own section. This is consistent with the fleet's own rule that a skill cites only where the
source changes what the reader does.

## Probe-backed recitation cut in the references (59,529 → 51,188 bytes)

A second pass answered the owner's question "is there anything in those files an LLM already
knows" against the clean-probe answers. `artifact.md` (7,884 → 6,813) lost the
"strongest control" table (Q4/Q6), the symptom→fix table (Q3, except the fleet's own fourth symptom,
which stays as a sentence), and the long form of "structural beats behavioral" (Q4); the body's
pointer to that table became a plain rule. `roster.md` (15,289 → 12,722) lost the
orchestration-pattern descriptions, the generic design principles, the failure-modes list, and the
generic half of the wrapper taxonomy (Q8), keeping the fleet default, the context-boundary rule, the
tools-are-authority and final-message rules, the fan-out budget, the tiering rule, and the two
wrapper failures this fleet's rules exist for. `context.md` (4,981 → 1,904) and
`tools.md` (4,020 → 2,394) were reduced to their fleet rules: the cold-start packet, the
replay/side-effect rule, the domain-namespacing examples, the output cap, the promote-from-bash gate,
the sprawl stance, in-this-fleet, and handoffs. `delegation-graph.md`, `skill-portability.md`, and
`claude-code-frontmatter.md` are untouched: their content is fleet and platform fact the probes
showed both models get wrong or hedge.

Evidence gap, stated: the probe questions covered `artifact.md`'s and `roster.md`'s cut sections
directly (Q3, Q4, Q6, Q8, Q13, Q14) but not `context.md`'s techniques or `tools.md`'s principles
question by question; those two are public guidance the models paraphrased in Q6 and Q8, and both
files are conditional loads, so the cut was made on that reading rather than on a fourth call per
tier. Every `../SKILL.md` statement a reference defers to was grepped present after the edit, and
no reference names a removed section `[verified]`.

## Form pass: rules as tables, no prose (references 36,754 bytes after; body 8,843)

Owner standard applied: a rule is its trigger, its imperative, and the failure it prevents. Every
paragraph that stated rules became a table or bullet list; explanatory and provenance narrative was
removed; every rule, every platform fact with its `doc-checked`/`probed` stamp, and every statement a
reference defers to was kept and re-grepped `[verified]`. Per file: body 8,843 (source-trust gate,
evidence-per-change, symptom→cause, four themes, which-graph, and the router are tables);
`roster.md` 8,789 (agent-vs-skill, verifiers per lane, orchestration shapes, packet rules, tiering,
wrapper failures as tables; the four-theme table dropped because the body owns it);
`artifact.md` 5,694 (case-set sizing and the wrong-form list as tables; learn-from-failure as
bullets); `claude-code-frontmatter.md` 10,859 (agent and skill fields, checkable rules, budgets,
and unused-field decisions as tables; the runtime-environment section removed as not an authoring
concern; the `disable-model-invocation` and plain-scalar histories reduced to the fact and its stamp);
`delegation-graph.md` 2,495 and `skill-portability.md` 4,619 (copies, roles, and host limits as
tables). Not a knowledge cut: no rule was removed for being known; this pass changes form only, so
by the fleet's own rule it owes no live eval, and an after-change discovery run was made anyway.

## Exercise check

`[verified]` One Opus run of the candidate on a fixture task (a release-notes skill that fires for
unrelated documentation requests and returns prose instead of the required JSON — the shape of the
fleet's own `trigger-and-shape` scenario): 8/8 scripted assertions. The run applied the body's
decisions rather than generic craft: it declined to execute the fixture under the source-trust
gate and said so first; rewrote the description to capability, three quoted triggers, and named
exclusions (427 bytes, no procedure); fixed the JSON failure with an exact output contract plus a
strict-parser validation gate instead of louder prose; measured activation and shape separately on
the six fixture cases with paired incumbent/candidate runs, one candidate, hard budgets, the
no-progress and safety stops, and human acceptance of the exact revision; and read exactly
`artifact.md` and `claude-code-frontmatter.md`. 77k tokens, 4.7 minutes.

## Six-run Sonnet comparison (owner-requested, after the PR opened)

`[verified]` Three runs of the incumbent (`origin/main` 4f01f22 snapshot) and three of the candidate
(`f492153`) on the same fixture task, Sonnet, in-repository subagents (identical context for both
arms, so the comparison is fair even though it is not a clean room). Scripted assertions: incumbent
24/24, candidate 23/24, with the one miss — "activation and shape measured separately with a
baseline" on candidate run 2 — passing on reading: that plan's `### Measurement` section carries an
**Activation (A1–A3)** track and an **Output shape (S1–S3)** track, each paired against the
incumbent. The detector keys on wording ("separate", "two tracks") and was widened once during
grading; the Opus run re-graded 8/8 under the same version. Every run in both arms read exactly
`artifact.md` and `claude-code-frontmatter.md`, declined to execute the fixture under the
source-trust gate, rewrote the description to capability + quoted triggers + exclusions, moved the
JSON contract to a strict output rule, removed the "offer to post" step, and named human acceptance
as promotion. Candidate runs averaged 78.4k tokens / 205 s against the incumbent's 78.7k / 217 s —
no behavioral difference, and no context penalty, on the fleet's measurement tier. Budget for this
check: six Sonnet calls beyond the slice's three-per-tier, at the owner's request.

## Fleet routing evidence

`[verified]` After-change run on exact candidate `fc5748a` (clean tree, `--require-clean-plugin`),
batch [`20260827T220227Z-744f0426`](2026-08-27-eval-20260827T220227Z-744f0426.md), Claude Code
2.1.247, `claude-sonnet-5`, regression split, two trials, 600-second timeout: **3/3 scenarios, 6/6
trials** — `defers-code-dependency-graph` (not_fire) 2/2, `loop-engineering` 2/2,
`trigger-and-shape` 2/2. Green, so no previous-revision baseline is owed. The only prior evidence for
these scenarios is the 2026-08-24 batch-1 audit's narrative (code-graph exclusion 2/2, Loop
Engineering activation 2/2); the calibration-split `workflow-graph` scenario was not run.

`[verified]` After the form pass and the owner decisions, exact candidate `e53eaa4` (clean tree,
`--require-clean-plugin`), batch [`20260827T234106Z-dca82a64`](2026-08-27-eval-20260827T234106Z-dca82a64.md), same conditions:
**3/3 scenarios, 6/6 trials** — the rewritten body routes as the pre-rewrite body did.

## Budget

At most three model calls per tier, as directed: Opus — contaminated probe, clean probe, exercise
run; Sonnet — contaminated probe, clean probe, repo discovery run. No build benchmark.

## What this record does not prove

- Probes measure recall; the pressure control covers only three prompts and is scored on content,
  not routing.
- The Opus exercise run has no incumbent comparison; the Sonnet six-run comparison does, at n=3 per arm.
- Claude-host results only; the Copilot projection may run on a model with different knowledge.
