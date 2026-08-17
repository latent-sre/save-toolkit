# Eval clean room — make the harness measure the fleet, not the laptop

**Date:** 2026-07-13
**Status:** implemented (PR #52, merged 2026-07-13) — first clean baselines recorded in `evals/`.
Historical record; do not execute. Live work is tracked only in
[`docs/fleet-roadmap.md`](../../fleet-roadmap.md).

## Problem

The behavioral harnesses (`evals/discovery_probe.py`, `evals/run_evals.py --run`) shell out to
`claude -p …` from `subprocess.run(...)` **without setting `env=`**. Every trial therefore inherits
the operator's whole Claude Code environment:

- `~/.claude/skills/` — 9 personal skills (`eng-ladder`, `root-cause`, `backend-craft`, `runbook`, …)
- `~/.claude/agents/` — 7 personal agents
- `~/.claude/plugins/` — installed marketplace plugins, which ship *those same 9 skills again*
- `~/.claude/CLAUDE.md` — the operator's global instructions

None of these belong to the fleet. They do not shadow it by name, but they **compete with it for
discovery**: a realistic prompt like *"how much design work does this change need?"* can land on the
operator's `eng-ladder` instead of the fleet's `sde-ladder`. Discovery rate is precisely what
`discovery_probe.py` exists to measure, so the number it produces is a property of **the machine it
ran on**, not of the fleet.

The harness already knows. Every recorded baseline carries this note:

> *"measured on a machine carrying 9 personal GLOBAL skills (`~/.claude/skills`: root-cause,
> eng-ladder, prompt-craft, runbook, backend-craft, sre-tool...) that shadow fleet skills — treat as
> a LOWER BOUND for a clean checkout."*

A measurement that has to be caveated is a measurement nobody can act on. The fleet cannot tune a
description against a number it does not trust, which means the harness — the most valuable thing in
this repo — is currently unusable for the one decision it was built to inform.

### Why this matters now

There is a live decision blocked on it. The ladder skills (`sde-ladder`, `sre-ladder`) **set altitude
on every task** — `CLAUDE.md` states this — yet neither `sde-engineer` nor `sre-engineer` preloads
one. They are told to *"load the skill"*, which is an instruction, and instructions bend. If
discovery is unreliable, those agents silently work at no altitude and nothing ever reports it.

The dirty data hints at exactly that:

| scenario | recorded baseline (n=2, contaminated) |
|---|---|
| `obs-sre-ladder` | 2 hit / 0 misroute / 0 no-route |
| `craft-sde-ladder` | **0 hit / 0 misroute / 2 no-route** |

But acting on a number the harness itself disclaims would be building on sand. Fix the instrument
first.

## Goals

- Every trial sees **only** the fleet under test: `.claude/skills/` and `.claude/agents/` of the
  project, plus nothing else.
- The harness fails **loudly** when it cannot produce a valid measurement, instead of scoring a
  broken run as a finding.
- Recorded baselines state honestly which namespace they were taken in.

## Non-goals

- **Changing the operator's `~/.claude`.** Those skills are the operator's and they are fine. The
  harness must be robust to its environment, not the other way around. Sanitising the machine would
  "fix" one laptop; fixing the instrument fixes every future run on every machine.
- **Preloading skills into agents.** That is the decision this unblocks, not this change. It is
  deliberately gated behind a clean baseline (see Follow-on).
- **Re-baselining all 44 discovery scenarios.** Live-model time; out of scope. See Baselines below.

## Verified facts

Everything load-bearing here was probed, not assumed.

| Fact | Evidence |
|---|---|
| `CLAUDE_CONFIG_DIR` relocates the entire user config — skills, agents, plugins, and the user `CLAUDE.md` | Probe: `CLAUDE_CONFIG_DIR=<tmp with only .credentials.json> claude -p "is each of these skills available? sde-ladder / eng-ladder / backend-craft"` → **`YES, NO, NO`**. The project's `sde-ladder` remained visible; the personal `eng-ladder` and the personal-*and*-plugin `backend-craft` both disappeared. |
| An **empty** `CLAUDE_CONFIG_DIR` breaks auth | Same probe with a truly empty dir → `Not logged in · Please run /login`. Credentials live at `~/.claude/.credentials.json` and must be seeded into the clean dir. |
| This is the ONLY viable isolation mechanism | `--plugin-dir` **adds** to the installed plugin set rather than replacing it ("the local copy takes precedence" — plugins docs); there is no documented `--no-plugins`, and `skillOverrides` explicitly does not affect plugin skills ("Plugin skills are not affected by `skillOverrides`" — skills docs). |
| Skill precedence is **personal over project** | skills docs: *"When skills share the same name across levels, enterprise overrides personal, and personal overrides project."* (Agents are the reverse — project wins.) There are no exact name collisions today, but a personal skill named `craft` or `sde-ladder` would silently override the fleet's. |

## Change 1 — The clean room

A single shared helper, used by both harnesses:

```
clean_env() -> (env: dict, cleanup: callable)
```

It creates a temp directory, copies **only** `~/.claude/.credentials.json` into it, and returns an
environment with `CLAUDE_CONFIG_DIR` pointed at it. Both `discovery_probe.run_trial()` and
`run_evals`'s trial runner pass that env to `subprocess.run(...)`.

Effect: the model sees the project's `.claude/skills/` and `.claude/agents/` and nothing else.

Applied to **both** harnesses. `run_evals.py` forces the target by prepending
*"(Use the &lt;target&gt; skill.)"*, so namespace competition bites it less — but its 39 scenarios still
grade model output produced under the influence of nine foreign skills and a foreign global
`CLAUDE.md`, and a suite graded in a polluted namespace has the same credibility problem. One helper,
two callers.

## Change 2 — Fail loudly, never fail open

This is the part that matters most, and it is where a careless version of this change would be
**worse than no change at all**.

If the credentials cannot be located, `claude -p` returns `Not logged in · Please run /login`. The
harness would parse that trace, find no `Skill()` call in it, and score the trial as a **no-route** —
a clean, plausible-looking miss. Every scenario would "fail", and the report would read as a
devastating finding about the fleet rather than a broken instrument.

So:

- If `~/.claude/.credentials.json` (or the resolved equivalent) does not exist, **abort the run with a
  clear error**. Do not run a single trial.
- If a trial's trace contains a not-logged-in / auth-failure marker, that trial is an **ERROR**, not a
  miss. It must never be counted as a routing outcome.

An eval harness that silently converts its own breakage into findings about the thing it measures is
the single most dangerous failure mode available to it.

## Change 3 — Honest baselines

Every existing `note:` in `evals/discovery/*.yaml` records a number taken in the contaminated
namespace. They are not comparable to clean ones and must not be silently read as history.

- Annotate each existing note as **`namespace: contaminated`** — taken before the clean room, not
  comparable.
- Take a fresh **clean** baseline for the two ladder scenarios (`craft-sde-ladder`, `obs-sre-ladder`)
  and the capability probe (`agent-reaches-skill`), which are the ones the follow-on decision rests
  on.
- Adopt a convention going forward: a baseline note states the namespace it was taken in. A number
  without that is not a baseline.

The other 41 scenarios keep their annotated-as-dirty notes until someone re-runs them. That is
honest, and it costs no live-model time.

## Change 4 — Measure the actual question

The follow-on decision is *"does `sde-engineer` load its ladder on a real task?"* No existing scenario
asks that. `craft-sde-ladder` measures **main-session routing to the skill** (`expected: sde-ladder`,
`also_acceptable: [sde-engineer]`) — a different question, and one that passes if the main session
merely delegates to the agent.

Add one scenario using the harness's existing `agent_must_reach_skill` mechanism, which proves via
`parent_tool_use_id` that the **delegated subagent itself** — not the main session — invoked the
skill. That distinction is the whole point of that flag, and it is exactly the false pass we would
otherwise take:

```yaml
id: capability-sde-engineer-reaches-ladder
expected_agent: sde-engineer
agent_must_reach_skill: true
# The prompt must be a REAL build request (so sde-engineer is the right target), non-trivial enough
# that altitude genuinely matters (so loading the ladder is correct behaviour, not ceremony), and it
# must NOT name a skill, a ladder, a tier, or the word "design" -- naming any of them would hand the
# agent the answer and turn a discovery probe into a compliance probe.
prompt: |
  The checkout service and the payments service both read the order table directly. I want to put
  an API in front of it so only payments owns the writes. Get started on it.
```

That prompt trips altitude (two services, a contract change, a data-ownership migration — squarely
principal-tier by `sde-ladder`'s own rubric) without ever saying so. An `sde-engineer` that starts
writing code without consulting its ladder is the exact failure this measures.

## Verification

- The clean room is proven by the probe already run: `YES, NO, NO` (project visible, personal and
  plugin skills gone). Re-run it as a test.
- **The fail-loud path must be seen failing.** Point the harness at a config dir with no credentials
  and assert it *aborts* rather than reporting a suite of no-routes. A guard never seen firing is not
  a guard — and this one exists to stop the harness lying about the fleet.
- Existing suites stay green: `evals/test_graders.py`, `evals/test_discovery_probe.py`,
  `scripts/test_validate_fleet.py`, `scripts/test_readonly_guard.py`, `scripts/validate_fleet.py`,
  and `run_evals.py --validate` (all now gated in CI).

## Follow-on (explicitly NOT this change)

Once a clean baseline exists: if `sde-ladder` / `sre-ladder` discovery is unreliable, preload the
ladder into its engineer via `skills:` frontmatter — a runtime guarantee rather than an instruction.
**Only the ladder.** `sde-engineer` references 15 skills and `sre-engineer` 12; preloading those would
destroy the fleet's architecture, which is deliberately *"agents are WHO, skills are HOW, loaded on
demand"* and is correct.

`test-engineer` is already the model to copy: it preloads `tdd-workflow` (needed on every task) and
invokes `craft` on demand (needed only sometimes). That is the pattern, not a bug.

## Risks

1. **A clean baseline may be WORSE than the dirty one, not better.** The contaminated numbers were
   called a "lower bound" on the assumption that foreign skills only ever steal discoveries. They may
   also have been *helping* — the operator's `eng-ladder` or `root-cause` could be absorbing prompts
   the fleet handles badly, flattering it. If clean numbers drop across the board, that is a real
   finding about the fleet, not a bug in this change. Do not "fix" it by reverting the clean room.
2. **Nothing catches a harness that stops isolating.** If a future edit drops the `env=` argument, the
   harness silently returns to measuring the laptop. Mitigate with a test that asserts `run_trial`
   passes `CLAUDE_CONFIG_DIR`.
3. **`.credentials.json` is an auth secret being copied to a temp dir.** It must be created with
   restrictive permissions and removed on exit, including on failure.
