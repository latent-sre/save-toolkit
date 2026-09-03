# Contributing

The short path for repository changes. [`AGENTS.md`](AGENTS.md) owns fleet-wide authority and the
rule map; [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md) is the only live backlog.

## 1. Protect current work

Check `git status` before editing and leave unrelated work alone. Use a separate worktree rather
than switching, stashing, or rebasing someone else's dirty checkout. Never rewrite published history
without the owner's approval.

## 2. Change the source of truth

Edit agents, skills, and commands only under `agents/`, `skills/`, and `commands/`; `.github/agents/`
and `platforms/copilot/skills/` are generated. After a canonical change, regenerate once and commit
the projections with the source:

```powershell
python scripts/generate_platform_adapters.py --write
```

Before changing frontmatter, tool authority, delegation, or guard wiring, read the
[frontmatter reference](skills/agent-authoring/references/claude-code-frontmatter.md). Pin
third-party dependencies in `requirements-dev.txt`; `scripts/readonly-guard.py` stays
standard-library-only under `python -I -S`. On Windows use `python` or `py -3`, not the Store stub.
`rg` hides generated projections through [`.ignore`](.ignore); pass `--no-ignore` to inspect them.

## 3. Verify in proportion to the change

Run the smallest check that exercises the changed behavior. A new contract needs one focused test
that fails for the named break and passes after the fix. A new mechanism needs the measured failure
it prevents and its weight in Gate A's totals, stated in the PR; the default response to a finding
is a deletion or a one-line rule. An evidence packet under `docs/reviews/` is kept only while a test
or a live document cites it by path; an uncited one fails `scripts/check_links.py` in Gate A, so cite
it from the record that relies on it or delete it in the same change.

| Change | Evidence |
|---|---|
| Code, validator, or exit code | The affected tests |
| Agent, skill, command, or bundled reference | The matching asset or contract test |
| Routing description | The overlapping clean-room scenarios; pure wording changes need no live eval |
| Eval harness or scenario | The affected `evals/test_*.py`; `python evals/build_probe.py --validate` for parsing or targeting changes; `python evals/judge.py --calibrate` after a rubric edit |
| Read-only guard or hook wiring | `python -m pytest scripts/test_readonly_guard.py scripts/test_hook_wiring.py`; exit codes stay 42 allow, 43 deny, 44 indeterminate |
| Canonical task-path file or `description:` field | `python scripts/check_context_cost.py`; it fails when a task or the always-loaded description total exceeds its byte budget |

Live evals run from `evals/build_probe.py` in a manual clean room, not CI. Raw traces and the batch
summary stay private under `.eval-runs/`; quote the numbers you rely on into the PR or review that
uses them.

Before pushing, run the structural gate once:

```powershell
python scripts/gate_a.py
```

Report what ran and what remains unverified.

## 4. Publish the intended change

Compare the branch with current `origin/main` and confirm the diff and commit list hold only the
intended work. `main` takes pull requests only; Save Toolkit maintainers merge. Production deployment
of new bytes is a separate, exact-candidate decision under
[`production-change-gate`](skills/production-change-gate/SKILL.md).
