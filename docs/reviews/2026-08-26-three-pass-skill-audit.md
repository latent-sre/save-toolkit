# Three-pass audit of all 32 canonical skills

> **Status: review evidence, not a second backlog.** This audits every skill under `skills/` on the
> revision named below. Findings here are measurements and observations; none becomes work until an
> owner decides it does and [`fleet-roadmap.md`](../fleet-roadmap.md) imports it.

**Audit baseline commit ID:** `b61f1eddc1afeac921d3f350dc17ab1b8a3bf11b`
**Scope:** all 32 canonical skills under `skills/`
**Audit date:** 2026-08-26
**Method:** scripted measurement over every `SKILL.md`, its `references/`, and `evals/scenarios/`,
with each aggregate finding hand-verified on a named skill before it was reported. The measurement
script is reproducible from this document's method notes; it was not committed, because a one-shot
audit instrument that nothing calls is the kind of file `docs/README.md` says to remove.

## Conclusion

The fleet's **contract layer is clean** — 32/32 skills pass every structural rule the repository
enforces, with zero unlinked bundle files and zero budget overruns. The **prose quality is unusually
high**: five vague qualifiers across 32 skills, and not a single shouted `MUST`/`NEVER`/`ALWAYS`
anywhere in the fleet.

Two real gaps, both in the layers that structure checks cannot see:

1. **Six skills have no verifier at all** — no eval scenario targets them. `frontend-craft` is the
   sharpest case: the largest skill in the fleet (3,345 tokens, ten references) with zero routing
   coverage.
2. **Three skills pay for the same rules twice**, restating in the always-loaded body what their own
   conditionally-loaded references already say. `agent-authoring` echoes 18 of its 82 body sentences.

Everything else is a judgment call an owner may reasonably decline.

## Pass 1 — Contract integrity

What the repository already enforces, re-measured independently rather than trusted.

| Check | Result |
|---|---|
| Description ≤ 600 UTF-8 bytes (`check_links.py`) | **32/32** — max 589 (`workflow-graph-engineering`), min 321 (`ci-actions`) |
| Description carries `Triggers:` with 2–4 quoted phrasings | **32/32** |
| Body under the 5k-token Level-2 budget | **32/32** — max 3,345 (`frontend-craft`, 67% of budget) |
| Every `references/` and `assets/` file linked from its `SKILL.md` | **32/32**, zero unreachable bundle files |
| Gate A, `check_links`, `check_canary_tokens`, `check_stale_names`, `validate_fleet`, `check_plan_status` | all PASS |

**The one gap: `argument-hint` on 18 of 32.** Missing from `akamai-edge`, `language-idiom`,
`pcf-deploy`, `gcp-ops`, `pcf-ops`, `production-change-gate`, `incident-command`, `stack-profile`,
`release-gate`, `service-readiness-audit`, `postmortem`, `database-reliability`, `merge-gate`, and
`service-onboarding`. It is not enforced and costs nothing when absent; it is a small UX loss in the
picker on both Claude Code and VS Code, which recognizes the field
(`skills/agent-authoring/references/skill-portability.md`). Cheap to close, low stakes.

## Pass 2 — LLM readability

How each body performs *as a prompt*, not as documentation. Four measures, each a proxy — the
numbers locate candidates, and every claim below was confirmed by reading the named skill.

### What the fleet does well

**Vague qualifiers: 5 occurrences across 32 skills.** Searching for the hedges that make an
instruction unfollowable — "appropriate", "as needed", "if necessary", "where relevant", "be
careful", "reasonable" — turns up three in `service-onboarding` and one each in `obs-dashboards` and
`obs-metrics`. For roughly 50,000 tokens of instruction text that is close to zero.

**Shouted imperatives: 0 across all 32.** No `MUST`, `NEVER`, `ALWAYS`, `SHALL`, or `REQUIRED` in
capitals anywhere in the fleet. This is worth naming because it is the opposite of the usual drift:
prompt suites tend to accumulate caps as authors escalate against a model that ignored the lowercase
version. This fleet argues instead, which is both more effective and what its own authoring guidance
asks for.

### The real finding: rules charged twice

A skill body is paid on **every** invocation; a reference is paid only when its predicate fires. When
the body restates what the reference says, and the body also routes to that reference, the same rule
is bought twice on every task that trips the predicate.

| Skill | Body sentences echoed in its own references | Share of body |
|---|---|---|
| `agent-authoring` | 18 of 82 | 22% |
| `operational-learning` | 11 | — |
| `obs-dashboards` | 5 | — |
| `workflow-graph-engineering`, `akamai-edge` | 4 each | — |

Verified on `agent-authoring`: its source-trust gate and evidence-matching rules appear near-verbatim
in both `SKILL.md` and `references/artifact.md`, differing only in a clause or two —

> BODY: *Imported or unreviewed artifacts receive static inspection only.*
> REF : *Imported or unreviewed artifacts receive static inspection only.*

This is the same defect repaired in `backend-craft` on 2026-08-25, where `api-design.md` restated the
parent's method semantics and status codes nearly verbatim. Worth distinguishing from the
**deliberate** case: an agent body may reasonably duplicate a skill's highest-stakes rules, because
skill loading is model-elective and the body is the more reliable layer. That argument does not apply
here — a skill body and its own bundled reference load through the same mechanism.

### Explanation density — a signal, not a verdict

Causal connectives per 1,000 body tokens ("because", "so that", "otherwise", "rather than",
"means that"). The fleet's own authoring guidance asks authors to explain *why* rather than command,
so a body with none is worth a look:

| Density | Skills |
|---|---|
| 0.0 | `akamai-edge`, `language-idiom`, `obs-traces`, `pcf-deploy` |
| 0.5–1.0 | `gcp-ops`, `ci-actions`, `pcf-ops`, `operational-learning`, `eng-ladder`, `obs-pipeline`, `incident-command` |
| 2.5+ | `runbook`, `database-reliability`, `merge-gate`, `service-onboarding`, `ops-tooling`, `obs-logs`, `root-cause` |

**Treat this as the weakest measure in the audit.** Spot-checking found `ci-actions` genuinely
carries no explanatory clause, while `eng-ladder`'s scored low only because its reasoning is phrased
in ways the pattern misses. A terse reference-style skill may be right to be terse. The honest
reading: these are candidates for a human to look at, not a defect list.

## Pass 3 — Verification coverage

Whether anything would notice if a skill's behavior regressed. The fleet's own rule — *name the
verifier before the work* — applied to the skills themselves.

**Six skills have no eval scenario targeting them:**

| Skill | Body tokens | References | Why it matters |
|---|---|---|---|
| `frontend-craft` | 3,345 | 10 | **The largest skill in the fleet**, with a two-branch framework predicate (React vs Vue) that is exactly the kind of routing that silently rots |
| `incident-drill` | 1,697 | 2 | Explicit-invocation only, so routing matters less — but it spends real money when it runs |
| `ops-tooling` | 1,608 | 6 | Six references, no coverage |
| `eng-ladder` | 1,367 | 7 | Seven references, no coverage |
| `obs-pipeline` | 1,351 | 2 | The only obs-* skill with no scenario; its five siblings have 1–2 each |
| `pcf-ops` | 1,655 | 3 | Sibling `pcf-deploy` has 2 |

At the other end, `production-change-gate`, `gcp-ops`, and `akamai-edge` carry seven scenarios each —
so the suite's coverage tracks perceived blast radius rather than skill size, which is defensible but
leaves the largest authoring skill uncovered.

**Canary-token coverage is 9 of 32 bundles**, all at 100% where adopted (`obs-*`, `akamai-edge`,
`incident-drill`, `workflow-graph-engineering`). Thirteen bundles carry three or more references and
no token, so for those there is no way to distinguish a reference that was genuinely read from one
reconstructed from model memory: `language-idiom` (8 references), `frontend-craft` (10),
`backend-craft` (9), `agent-authoring` (7), `eng-ladder` (7), `ops-tooling` (6),
`database-reliability` (5), and six others. `check_canary_tokens.py` calls fleet-wide adoption "a
churn decision for a human", so this is recorded as a measurement, not a recommendation.

## What an owner might do with this

Ranked by value against cost, for a decision rather than as queued work:

1. **Cover `frontend-craft` with routing scenarios.** Largest skill, zero verifier, and its
   React/Vue predicate is the most rot-prone routing in the fleet.
2. **Cut the duplication in `agent-authoring` and `operational-learning`**, in the reference
   direction — the pattern already applied to `backend-craft`.
3. **Add `argument-hint` to the 14 skills missing it.** Mechanical, low stakes.
4. **Read the four zero-explanation skills** and decide per skill whether terse is correct there.
5. **Decide on canary adoption** for the thirteen uncovered multi-reference bundles — one decision,
   not thirteen.

## Method notes

Measurements were taken by parsing each `SKILL.md`'s frontmatter and body, its `references/` and
`assets/` trees, and every `evals/scenarios/*.yaml` target. Duplication used Jaccard similarity ≥ 0.5
over 4+ character word sets between body sentences and reference sentences of eight words or more,
with code fences stripped. Token counts are `len(body) // 4`, the same approximation used elsewhere
in this repository; they are estimates, and the budget conclusions hold with wide margin regardless.
Every aggregate was confirmed against at least one named skill before being reported here.
