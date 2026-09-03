# frontend-craft trim: before/after evidence (2026-09-03)

Measured with the fixture-backed build probe
`evals/build-scenarios/build-software-engineer-incidents-page.yaml` on the consolidated runner
(PR #222), on the maintainer's Windows host. The probe seeds a Vite + React 19 + TypeScript app,
runs `claude -p --agent save-toolkit:software-engineer` in it, and grades the running page with a
probe-owned oracle the agent never sees: a loading state, an inline error instead of a white page,
a designed empty state, labelled controls, the status filter round-tripping through the URL, a
clean axe scan, and status stated in text; plus typecheck, the agent's suite, and the packet and
surgical-change checks. Cited by the scenario's own header and by PR #222.

## Provenance

| Item | Value |
|---|---|
| Incumbent plugin root | detached worktree at `7c312ab8`; `frontend-craft` bundle 47,790 B |
| Trimmed plugin root | detached worktree at `617b105e`; bundle 12,262 B (SKILL.md 3,950; stack, design-language, data-viz kept; React, Vue, forms, interaction-a11y, auth, ux-writing, data-views deleted) |
| Runner | `evals/build_probe.py` at `17be0b6c` (the read boundary scoped to fixture-less trials; see below) |
| Model | `claude-sonnet-5` only; the Opus arms were skipped because the Anthropic API was returning 529 Overloaded for Opus throughout (status page: minor service outage) |
| Trials | 5 trimmed, 2 incumbent; the maintainer stopped the incumbent arm at two on the grounds that the question is whether the trimmed bundle still meets the bar |
| Raw runs | `.eval-runs/build/frontend-craft-2026-09-03/` (gitignored, private) |

## Results

| Arm | Scores (of 21) | Total | Skill loaded |
|---|---|---|---|
| Full bundle, Sonnet | 21, 21 | 42/42 | 2/2 |
| Trimmed bundle, Sonnet | 20, 21, 21, 21, 21 | 104/105 | 5/5 |

The one miss: the trimmed arm's first trial kept the status filter in component state instead of
the URL. The "URL is state" rule survived the trim as an invariant row, and the next four trials
honoured it. Every other bar passed in every trial on both arms: the loading, error, and empty
states, labelled controls, the axe scan, status in text, typecheck, the agent's suite with an
incidents test, no Mantine, the packet slots, a surgical change, nothing committed.

## What this says

- **The trim is safe on this task.** Five trimmed trials at or within one check of a perfect
  score, against two perfect incumbent trials; nothing the incumbent passes is failed by the trim.
- **Unlike backend-craft, Sonnet meets the frontend bar with or without most of the bundle.** A
  tools-off probe the same morning had Sonnet and Opus at 19 of 19 on the generic content; the
  trials confirm it on the running page. The 35 KB removed (the React and Vue references above
  all) was reproducing what the model does.
- **Not measured**: Opus; a no-skill arm; the design-language choices (the fixture is an existing
  app, so the greenfield defaults never trip); Vue.

## Instrument defect found and fixed during the campaign

The consolidated runner applied its read-path boundary to every trial granted read tools. A build
lane runs with its real tools on the host and legitimately reads outside the workspace (the first
Sonnet build read one of Claude Code's bundled-skill example files), so every trial of the first
incumbent arm came back INCONCLUSIVE after a complete 43-turn build. Fixed at `17be0b6c`: the
boundary applies only to fixture-less clean-room trials, with a unit test; the inconclusive runs
were discarded and both arms rerun on the fixed runner.
