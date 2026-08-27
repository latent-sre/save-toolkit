# SKILL-001 Phase 2 — `agent-authoring` disposition evidence

**Status:** Historical evidence captured on 2026-08-27. [The fleet roadmap](../fleet-roadmap.md) is
the only live backlog; this record does not queue work.

## Conclusion

`agent-authoring` is dispositioned as a **retained router with a recitation cut**: the always-loaded
entrypoint falls from 10,911 to 9,653 immutable bytes (−12%), the description is byte-identical,
and the bundle routes 59,529 reference bytes (66,628 before the owner's trim below) against 9,653 retained. The cut is small by design:
the clean-room probes show both models already produce the general method this skill teaches, but
neither knows the fleet's decisions, and both author the Claude Code frontmatter facts wrong — so
the body keeps decisions, traps, the rule statements its references defer to, and the router, and
sheds only restated craft. It stays above the 5,000-byte screen for that reason.

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

## The cut (10,911 → 9,653 bytes)

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

## Fleet routing evidence

`[verified]` After-change run on exact candidate `fc5748a` (clean tree, `--require-clean-plugin`),
batch [`20260827T220227Z-744f0426`](2026-08-27-eval-20260827T220227Z-744f0426.md), Claude Code
2.1.247, `claude-sonnet-5`, regression split, two trials, 600-second timeout: **3/3 scenarios, 6/6
trials** — `defers-code-dependency-graph` (not_fire) 2/2, `loop-engineering` 2/2,
`trigger-and-shape` 2/2. Green, so no previous-revision baseline is owed. The only prior evidence for
these scenarios is the 2026-08-24 batch-1 audit's narrative (code-graph exclusion 2/2, Loop
Engineering activation 2/2); the calibration-split `workflow-graph` scenario was not run.

## Budget

At most three model calls per tier, as directed: Opus — contaminated probe, clean probe, exercise
run; Sonnet — contaminated probe, clean probe, repo discovery run. No build benchmark.

## What this record does not prove

- Probes measure recall; the pressure control covers only three prompts and is scored on content,
  not routing.
- One exercise run; no incumbent comparison.
- Claude-host results only; the Copilot projection may run on a model with different knowledge.
