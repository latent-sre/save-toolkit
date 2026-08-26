# Contributing

This file defines how to change, verify, and promote work in this repository. [`AGENTS.md`](AGENTS.md)
owns fleet operating doctrine, [`docs/rules.md`](docs/rules.md) indexes rule sources, and
[`docs/fleet-roadmap.md`](docs/fleet-roadmap.md) is the only live backlog. Load only the sources
matched by the change.

## Start clean

- Inspect `git status` before implementation.
- For work intended for a pull request, refresh `origin/main` and start a new branch named for the
  work. Never reuse a branch whose pull request already merged.
- Preserve dirty or published branches. Use another worktree instead of switching, stashing, or
  rebasing someone else's checkout.
- Read-only investigation and review use the requested checkout. Fetch only when remote freshness
  affects the answer.
- Prototype personal agents and skills under `~/.claude/{agents,skills}`. Promote shared components
  through a pull request; personal scope reduces shared-fleet exposure but is not a sandbox.

Keep related work on one branch as separate commits. Split only when changes have independent
owners, review timelines, or rollback needs. If separate branches both touch shared catalog files
(`AGENTS.md`, `README.md`, `CHANGELOG.md`, or the roadmap), stack them so the later branch is based on
the earlier one.

## Edit canonical source

Author agents, skills, and commands only under `agents/`, `skills/`, and `commands/`. Ordinary `rg`
searches exclude generated projections through [`.ignore`](.ignore); use `--no-ignore` only when
checking projections intentionally. Never hand-edit `.github/agents/` or
`platforms/copilot/skills/`.

VS Code's tools picker can dirty an open generated `.agent.md` buffer without changing the file on
disk. Before regenerating, check both the editor's dirty state and `git status`; saving that buffer
creates projection drift.

After canonical edits are complete and before push, run the generator and commit its output with
the source:

```powershell
py -3 scripts/generate_platform_adapters.py --write
```

Before changing agent or skill frontmatter, tool authority, delegation, or guard wiring, read
[`claude-code-frontmatter.md`](skills/agent-authoring/references/claude-code-frontmatter.md).

On Windows, use `python` or `py -3`, never the `python3` Store stub. If Python resolution is
uncertain, run `where.exe python` and `python scripts/fleet_doctor.py` from the acting lane. A
SessionStart preflight warning means guarded Bash remains fail-closed; it does not prove the guard
ran successfully.

## Verify the change

Run the smallest tests owned by the changed behavior. A newly asserted contract needs a focused
check that turns red when that exact contract is broken and green when restored. Gate A is
structural and does not replace component tests or evaluations.

### Change-specific evidence

Load only the rows matched by the change:

| Change | Required evidence |
|---|---|
| Executable code | Run the smallest affected test file or files. |
| Eval harness or scenario | Run affected `evals/test_*.py`. If parsing or targeting changes, also run `python evals/run_evals.py --validate`. |
| Routing `description:` content | List cases with `python evals/run_evals.py --list`, then run overlapping scenarios after the edit. Run a prior-revision baseline only for a red case; pure rewording needs no live eval. Direct-agent cases test behavior after selection, not routing. |
| Validator, exit code, schema, or named predicate | Add one focused fixture; prove the named break red, restore it, and prove green. Optional mutation testing is limited to `python scripts/mutation_guard.py --module <one-file.py>` for one named mutant; survivor counts are not findings. |
| `scripts/readonly-guard.py` or `hooks/hooks.json` | Read both docstrings; run `python scripts/test_readonly_guard.py` and `python scripts/test_hook_wiring.py`; inspect the allow/deny corpus diff; preserve 42 allow / 43 deny / 44 indeterminate. |
| `agents/`, `skills/`, or `commands/` | Confirm the regenerated projections are included with their canonical source; use the command under **Edit canonical source**. |
| Bundled reference | Files covered by `CANARY_REQUIRED_GLOBS` need a unique canary token; run `python scripts/test_canary_tokens.py`. Replace an old dated verification stamp; retain an older date only for a different assertion. |
| Runtime probe or schema | Follow [`docs/schema-compatibility.md`](docs/schema-compatibility.md); for a containerized check follow the Docker-backed local verification contract in [`AGENTS.md`](AGENTS.md). |
| Explicit operational closeout after an incident, drill, audit, or approved service/alert change | Apply [`disposition-policy.md`](skills/operational-learning/references/disposition-policy.md). A human-accepted fleet failure instead becomes one focused regression under [`artifact.md`](skills/agent-authoring/references/artifact.md). |

Routing and behavioral evaluations are manual clean-room runs, never CI jobs. Use
`evals/run_evals.py`; keep raw repository-local output under `.eval-runs/`. The runner automatically
extracts its bounded durable summary to `docs/reviews/`; never commit the raw traces wholesale.

Before pushing, ensure the live-tree structural gate passes:

```powershell
py -3 scripts/gate_a.py
```

Report each result as `[verified]`, `[sourced]`, or `[unverified]`. Name what ran, what passed, and
what remains unverified; never upgrade a label during a rewrite or handoff.

## Prepare the pull request

Refresh `origin/main` and inspect divergence in both directions:

```powershell
git rev-list --count origin/main..HEAD
git rev-list --count HEAD..origin/main
git log --oneline origin/main..HEAD
```

Compare with `origin/main`, not a possibly stale local `main`. Integrate current main before the
pull request. Rebase only unpublished history unless the owner explicitly authorizes rewriting a
published branch. Confirm the commit list contains only the intended work.

Independent review is optional unless another gate requires it. Resolve or explicitly reject any
current P0/P1 findings with evidence. A working-tree review is provisional; production deployment
of new bytes requires independent review of the exact candidate SHA through
`production-change-gate`. Add plan-conformance review only when the pull request cites a plan or
roadmap item.

## Repository boundaries

`main` requires pull requests and blocks force-pushes and branch deletion. Maintainer and merge
authority belongs to `latent-sre`; `agentic-sre-dev` is read-only. Merging does not publish an
artifact because this repository has no publication workflow.
