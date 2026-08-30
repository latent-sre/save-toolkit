# SKILL-001 Phase 2 — `frontend-craft` disposition evidence

**Status:** Historical evidence captured on 2026-08-27. [The fleet roadmap](../fleet-roadmap.md) is
the only live backlog; this record does not queue work.

## Conclusion

`frontend-craft` is dispositioned as a **confirmed router with a knowledge cut**: the always-loaded
entrypoint falls from 14,150 to 7,481 bytes (−47%) in two steps, and the bundle routes more
reference bytes than it retains (39,798 routed vs 7,481 retained). The description is
byte-identical. The entrypoint stays above the 5,000-byte screen because what remains — the fleet's
decisions, the rules both models drop under pressure, and the routing table — has no conditional
boundary left to split.

Two findings changed the method rather than the skill:

1. **The body's knowledge content is redundant with the models that run it.** With no skill and no
   tools, Opus and Sonnet each answered 18/18 unhinted questions mapped one-to-one onto the body and
   framework references, including the version-gated React 19 / Vue 3.5 facts and the fleet's own
   greenfield stack. The skill's remaining value is posture (a gate instead of advice), decisions a
   model cannot infer, and routing predicates.
2. **Presence is not posture in the fleet's graders.** In the no-skill pressure control, Opus
   satisfied every `contains_any` group on all three `frontend-craft` discovery scenarios while
   explicitly declining to block the merge ("not me blocking the merge"). The graders cannot
   distinguish naming the render/keyboard pass from requiring it. Filed as `GRADER-005`.

## Step 1 — router conversion (14,150 → 10,664 bytes)

`[verified]` On exact base `origin/main` `0eb3daf`, the entrypoint measured 14,150 immutable bytes
with 37,107 reference bytes. The greenfield design language (dark-first surfaces, color courage,
categorical KPI accents, typography, depth cues, self-critique, sidebar-rail default, spacing and
type scale) moved into `references/design-language.md` (1,872 → 4,734 bytes, merged with its
existing paraphrase); the interface-copy rules already in `ux-writing.md` were dropped from the
body; the TanStack Router detail moved into `stack.md`. Reference rot repaired: `stack.md` stated
the Mantine rule twice, `auth.md` carried two overlapping sections, and `data-views`/`forms`/
`data-viz` repeated their H1 as an H2. The body/reference contradiction ("applies to every UI
task" versus "an existing brand or design system always wins") is resolved by the new predicate
"a greenfield or unbranded UI, or a new app shell or view with no existing design system to match".

`[verified]` Iteration-1 evaluation (workspace `.eval-runs/frontend-craft-workspace/iteration-1`,
gitignored): three realistic tasks — a greenfield React status app, a settings form in a branded
Vue 3.5 app, and a framework-free ops console graded by the craft-canary's eight Playwright checks
— each run once with the old skill and once with the candidate on Opus, plus the old skill on
Sonnet as non-comparable extra evidence. Candidate 26/26 assertions; old skill on Opus 25/26 (the
miss: a review packet that named only `forms.md` instead of each reference read); old skill on
Sonnet 26/26. Every candidate run loaded exactly the predicted reference lanes, including *not*
loading `design-language.md` or `stack.md` for the branded app. Candidate runs spent +28% tokens
on average, concentrated in one greenfield run that added an OpenAPI-generated client, axe scans,
and 31 tests; with one run per cell this is executor variance, not attributable to the skill text.

The branded-app task did not separate the versions on behavior: all four old-skill runs kept the
brand and skipped the design language. The contradiction above was therefore real in the text but
not an observed failure on either model.

Grader repairs made during the iteration, applied to every run and reconciled against the final
scripts: the hidden Playwright checks threw on their first failure (one added table column zeroed a
run), counted DOM rows instead of visible rows, and keyed the status cell to the fixture's class
name; the reference-read parser counted files named in a "not read" list, including one whose
heading used markdown emphasis. Reference-read assertions remain executor self-reports and are
labelled `[unverified]` in every grading.

## Step 2 — knowledge cut (10,664 → 7,481 bytes)

`[verified]` Probe transcripts are in `.eval-runs/frontend-craft-workspace/probes/` (gitignored;
verbatim replies with the prompts). Knowledge probe: 18/18 for Opus, 18/18 for Sonnet, both picking
the fleet's greenfield stack unprompted. Pressure control on the three scenario prompts with no
skill:

| Scenario | Opus | Sonnet |
|---|---|---|
| render-is-not-verification | catches the flash; browser/keyboard pass named but "not me blocking the merge" | catches the flash; "otherwise, no objection to merging" |
| blocks-mantine-tailwind | blocks firmly, names the reset conflict and headless alternatives; no `@mantine/hooks` carve-out | blocks softly ("will work, budget time to reskin"); no carve-out |
| framework-evidence | notices `preact/compat` only as a package.json oddity | reviews the Preact file as React |

The body was therefore cut to three kinds of content: the preamble's posture rules (write the
code; one batched question round at a material fork; recommend-better; existing product decisions
win), seven one-line invariants (the rules dropped under pressure, including every phrase the three
discovery graders target), the fleet's decisions (the Mantine rule with the hooks carve-out, the
query layer, the contract-derived client, the testing choices, and the done-bar rewritten as an
explicit gate), and the unchanged routing table. Removed as recitation: Layout, Motion (its timing
line moved to `design-language.md`), the Resilience bullets, Performance, SSE, and the generic
accessibility prose. Every graded phrase is still present in the body `[verified]` by grep.

`[verified]` Iteration-2 check (one Opus greenfield build against the cut body — the only task
where visual character could regress): 8/9 assertions. The design language survived the move —
dark and light token sets, one accent, categorical KPI tiles, a signature deploy-tape element
encoding outcome by shape as well as color — with 16 component tests, 7 Playwright paths, axe
clean in both themes, and twelve saved screenshots; the executor's own render pass caught three
defects the tests had not. The one miss is packet completeness: the review packet referred to
"the stack reference" and "the a11y reference" instead of naming the files, the same miss the
old skill's Opus console run made in iteration 1. The run loaded exactly the predicted lanes.
343k tokens, 49 minutes (iteration-1 candidate: 387k, 57 minutes; old skill: 249k, 38 minutes;
one run each).

## Fleet routing evidence

`[verified]` After-change run on exact candidate `1b2d485` (clean tree, `--require-clean-plugin`),
batch [`20260827T193543Z-4d6f596b`](2026-08-30-folded-eval-index.md), Claude Code
2.1.247, `claude-sonnet-5`, two trials, 600-second timeout: **1/3 scenarios** —
`blocks-mantine-tailwind` 2/2, `framework-evidence` 0/2, `render-is-not-verification` 1/2 (3 of 6
trials). Every failing trial is a routing miss: the runner saw no `frontend-craft` invocation, and
the second render trial routed to `merge-gate` and `root-cause` instead and spent 359 seconds
trying to verify with tools the clean room denies.

`[verified]` Previous-revision baseline on exact `0eb3daf` (the untouched skill, same conditions),
batch [`20260827T194430Z-3ec34e1f`](2026-08-30-folded-eval-index.md): **0/3
scenarios** — 1/2, 0/2, 0/2 (1 of 6 trials). The red is therefore pre-existing, not a regression:
the candidate is at or above the baseline on every scenario. PR #174, which added these three
scenarios on 2026-08-26, recorded that they had never executed; these two batches are their first
measurements. On the baseline's one `framework-evidence` trial where the old skill did fire, the
model still reviewed the Preact file as React, so the predicate paragraph is not reliably applied
even when loaded. The description is byte-identical across the two revisions, so selection cannot
differ by design; with two trials per scenario the trial-level difference (3/6 versus 1/6) is not
claimed as an improvement. Neither batch authorizes prompt or description edits; the routing
instability is filed as `ROUTE-004`.

## What this record does not prove

- Reference selection by the executors is self-reported; no trace of file reads exists outside the
  discovery harness.
- The interview-style knowledge probe measures recall, not task behavior; the pressure control is
  the closer measurement and covers only the three scenario prompts.
- Both probes ran as Agent-tool subagents inside this repository, so Claude Code loaded `AGENTS.md`
  and the session's memory index into their context. Neither carries UI rules, and the fleet's
  greenfield stack is named there only by the skill name `stack-profile`, so the frontend findings
  stand; but the method is not a clean room. The `agent-authoring` slice found the same setup
  reciting `AGENTS.md` verbatim and moved probes to the harness's clean room (credentials-only
  config dir, empty workspace, no plugin).
- All results are Claude-host results. The Copilot projection of this skill may run on a model
  with different knowledge; the fleet's host-specific-authority rule applies to the knowledge cut.
- One run per cell throughout. No token or duration claim rises above variance.

## Remeasurement

`[verified]` On `origin/main` `0eb3daf`, 33 entrypoints total 231,513 immutable bytes. Seventeen
non-Phase-1 entrypoints other than `frontend-craft` sit at or above 5,000 bytes: `obs-dashboards`
11,419; `backend-craft` 11,123; `agent-authoring` 10,911; `runbook` 9,561;
`workflow-graph-engineering` 8,622; `incident-drill` 8,154; `gcp-ops` 8,102; `obs-alerting` 7,755;
`service-readiness-audit` 6,871; `service-lifecycle` 6,244; `operational-learning` 6,090;
`obs-pipeline` 5,941; `eng-ladder` 5,351; `incident-investigation` 5,339; `postmortem` 5,138;
`root-cause` 5,062; `obs-traces` 5,024. The roadmap's earlier twelve-candidate screen predates six
of these.
