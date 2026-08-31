# Contributing

This is the short path for repository changes. [`AGENTS.md`](AGENTS.md) owns fleet-wide authority
and safety rules, [`docs/rules.md`](docs/rules.md) indexes the uncommon contracts, and
[`docs/fleet-roadmap.md`](docs/fleet-roadmap.md) is the only live backlog. Load a linked rule only
when the change matches it.

## 1. Protect current work

Inspect `git status` before editing and preserve unrelated or published work. Use a separate branch
or worktree when the current checkout is unsafe to modify; it is an isolation tool, not a gate for
every change. Refresh `origin/main` when remote freshness affects the work or before publishing.
Do not switch, stash, or rebase another owner's dirty checkout; use a separate worktree. Never
rewrite published history without explicit owner approval.

## 2. Change the source of truth

Edit agents, skills, and commands only under `agents/`, `skills/`, and `commands/`. Generated
`.github/agents/` and `platforms/copilot/skills/` files are consequences, not sources. After changing
canonical fleet content, regenerate once and include the projections with the source:

```powershell
python scripts/generate_platform_adapters.py --write
```

Before changing frontmatter, tool authority, delegation, or guard wiring, read the
[`agent-authoring` frontmatter reference](skills/agent-authoring/references/claude-code-frontmatter.md).
On Windows use `python` or `py -3`, not the `python3` Store stub.

Prefer `rg`. [`.ignore`](.ignore) hides generated projections, so use `--no-ignore` to inspect them;
use `--hidden` for dot-directories such as `.github/` workflows.

## 3. Verify in proportion to the change

Run the smallest check that exercises the changed behavior. A new contract needs one focused test
that fails for the named break and passes after the fix. Gate A is structural; it does not replace
that test.

| Change | Evidence |
|---|---|
| Code, validator, exit code, or schema | Run the affected tests. Follow [`schema-compatibility.md`](docs/schema-compatibility.md) for schema changes. |
| Agent, skill, command, or bundled reference | Run the matching asset/contract test; canary-protected references also run `python scripts/test_canary_tokens.py`. |
| Routing description | Run the overlapping clean-room scenarios after a routing-content change. A prior-revision baseline is needed only to diagnose a red case; pure wording changes need no live eval. |
| Eval harness or scenario | Run the affected `evals/test_*.py`; run `python evals/run_evals.py --validate` when parsing or targeting changes. |
| Read-only guard or hook wiring | Run `python scripts/test_readonly_guard.py` and `python scripts/test_hook_wiring.py`; preserve exit codes 42 allow, 43 deny, and 44 indeterminate. |

Live routing and behavioral evals use `evals/run_evals.py` in a manual clean room, not CI. Keep raw
traces under `.eval-runs/`; only the runner's bounded durable summary belongs under `docs/reviews/`.

Before pushing, run the structural repository gate:

```powershell
python scripts/gate_a.py
```

Report what ran and what remains unverified.

## 4. Publish the intended change

Before a pull request, compare the branch with current `origin/main` and confirm the diff and commit
list contain only the intended work. Integrate current main when needed to resolve overlap or meet
repository policy.

Independent review is required only when another repository gate calls for it. Resolve or explicitly
disposition known P0/P1 findings. Production deployment of new bytes remains a separate,
exact-candidate decision under [`production-change-gate`](skills/production-change-gate/SKILL.md).

`main` requires pull requests and blocks force-pushes and branch deletion. Save Toolkit maintainers
own merge authority; `agentic-sre-dev` is read-only. A merge does not publish an artifact because
this repository has no publication workflow.
