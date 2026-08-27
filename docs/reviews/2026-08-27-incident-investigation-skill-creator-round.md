# incident-investigation — skill-creator round, 2026-08-27

> **Status: review evidence for commits ebad080 and 90dd83d, plus one follow-up wording change.**
> Measurements were taken outside the repository's own harness, with subagents reading the skill
> from disk and blind LLM graders; they are evidence about the skill's content, not about the `sre`
> lane under the plugin. Raw runs, grades, and benchmarks are under
> `.eval-runs/incident-investigation-workspace/` (untracked).

## Method

Three prompts a responder would actually type — an untriaged Cloud Run page, a three-candidate
differential with no agent, and a systemic failure whose trigger is gone — each run as a fresh
subagent on `claude-opus-5` and `claude-sonnet-5`. Iteration 1 compared with-skill against no
skill (n=1); iterations 2 and 3 compared the revised skill against the pre-edit snapshot (n=1, then
n=2 per cell on a rewritten ruler); two targeted re-measures covered single-sentence fixes. Every
set of four answers was anonymized A–D and graded by one Opus grader that fixed its bar per
assertion before reading, with the answers' configurations withheld. Fourteen grader runs in all,
roughly 100k tokens each.

## Results

| iteration | comparison | Opus | Sonnet |
|---|---|---|---|
| 1 (n=1) | with skill vs no skill | 1.00 vs 0.82 | 0.93 vs 0.67 |
| 2 (n=1) | revised vs snapshot | 0.94 vs 0.91 | 0.83 vs 0.85 |
| 3 (n=2, rewritten ruler) | revised vs snapshot | 0.84 vs 0.74 | 0.71 vs 0.54 |

Iteration 1 established that diagnosis quality is model-native — 19 of 28 assertions passed in
every configuration — and that the skill's value is process content: the incident spine, the
stuck predicate, the handover packet, recovery criteria. Iteration 2 showed the first revision
fixed its targets (tooling vocabulary in the reply 6/6 clean vs 3/6, companion reference loads
3/6 vs 5/6, canary tokens in an answer 0/6 vs 1/6, Cloud Run examples native) without moving the
overall rate, and introduced one regression: a recipe line asking for "verification and rollback"
per action displaced the systemic reference's recovery criterion (0/2 vs 2/2). Replacing that line
with an explicit sustained-window sentence restored it 4/4. Iteration 3, on assertions rewritten
to the graders' own critiques, shows the revised skill ahead on both models in every prompt.

Landed in iteration 3 (revised vs snapshot): caller-reported facts labelled `[sourced]` 8/8 vs
3/8; recovery window 4/4 vs 1/4; finding stated first 11/12 vs 8/12; canary tokens 0/24;
companion loads 7/12 vs 10/12; Opus answers shorter (2,297 vs 2,625 words). Not landed: the
first-screen budget (the first lever arrives after the mechanism in every model and version);
naming what a mitigation can destroy (3/4 vs 3/4); "acknowledge the page" (0/4 vs 1/4). The
onset-as-a-bound rule reached only the first-response path because it sat in
`signal-characterization.md`, which the hypothesis path correctly skips; moved into the spine, all
four re-measured answers state the bound, and one of four stops ranking candidates on the exact gap.
A second rewrite added the behaviour to the rule ("no candidate is ranked on a gap measured from
either") and bounded the finding to two or three sentences with the mechanism pushed after the
escalation trigger; re-measured on the same prompt (Opus x2, Sonnet x2, 13-assertion ruler with
first-screen split into ordering and budget): onset behaviour 3/4, first-screen ordering 3/4,
first-screen budget 2/4, against 1/4, 2/4, 1/4 before the rewrite.

## What the grader pilot established for EVAL-005

Blind Opus graders with a fixed per-assertion bar produced consistent verdicts across reps, no
adjacency false-reds of the kind recorded in `4738372a`, literal-token checks where a literal
check was the right instrument, and — most useful — a critique of each weak assertion that became
the next ruler. Cost was about 100k tokens per set of four answers. Not settled: the policy for a
non-deterministic grader inside an otherwise reproducible suite, and how to carry the "fix the bar
before reading" discipline into a scenario file.

## Clean-room runs on the committed candidate (062f1cf)

Three batches under Claude Code 2.1.247, `claude-sonnet-5`, three trials each, retained as
`docs/reviews/2026-08-27-eval-*.md`:

- `97efbc22`, profile-less, all nine `incident-investigation` scenarios. Without a profile the runner
  enables no reference reads, so every trial answered from `SKILL.md` alone: valid for the four
  SKILL.md-only scenarios (no-incident 3/3, self-recovery 3/3, mode-selection 2/3,
  correlated-incidents 0/3 on three adjacency regexes with no prior baseline), not for the two
  reference-bearing ones.
- `873221fe`, the `eval-004-reference-reachability` profile. All six canaries PASS under the
  inert-canary framing; stuck-differential 3/3 (2/3 in `4738372a`); flat-signals 1/3 (2/3 in
  `4738372a`), where both reds are the `not_regex` matching "not a silent close" and "stops being
  a same-night close-out" while all three trials open "Not yet supported". The three
  `incident-command` scenarios sit at their accepted 2/3, 2/3, 3/3.
- `61040f56`, a control on the pre-change bytes (`35fb312`) under the same CLI, discovery scenarios
  only: defers-engineering-altitude 1/3 against 0/3 on the candidate (the literal `eng-ladder`
  grader; routing PASS in all six trials), systemic-failure 2/3 against 0/3 (the literal
  `human execution` phrase list; routing PASS in all six), first-response 3/3 on both. The
  systemic-failure phrase shift is plausibly the recipe's phrasing at n=3; both scenarios were
  already below their 1.0 threshold on the old bytes under this CLI.

Per EVAL-005's accepted stance a red on an adjacency grader is not by itself a finding, and no
tuning run was spent on pattern repair.

## Limitations

Subagents read the skill from disk without the plugin namespace, so routing under the real host and
the `sre` lane's output contract were not exercised; the repository's `incident-investigation-*`
scenarios remain the instrument for that. Cells differ by one or two assertions at n=2, so no
Opus-versus-Sonnet claim finer than the 0.10–0.17 gaps is supported. The eval prompt's "you cannot
access their systems" constraint produced disclaimer-first openings in iteration 2 on both versions
and was reworded before iteration 3.
