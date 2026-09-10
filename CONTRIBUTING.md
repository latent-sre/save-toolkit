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

Repository development and CI track the latest Python 3.14 patch. `.python-version` selects the
minor series; both CI jobs use `check-latest: true`. Use `uv python install 3.14` and
`uv venv --python 3.14`, then install the required dependency set into that environment.
An old uv binary may need updating before it knows about a newly released Python patch.
This development default does not raise the installed hook guard's Python 3.11 floor.

## 3. Verify in proportion to the change

Run the smallest check that exercises the changed behavior. A new contract needs one focused test
that fails for the named break and passes after the fix. A new mechanism needs the measured failure
it prevents and its weight in Gate A's totals, stated in the PR; the default response to a finding
is a deletion or a one-line rule. Keep evidence under `docs/reviews/` while an unresolved roadmap
decision or a current regression depends on its measurements, including failed results. A changelog
entry or a comment recording when a test first ran is not a retention reason. Remove completed
reports, retired eval fixtures, and restoration bundles once their current dependency is gone;
an explicit preservation decision requires a successor or owner disposition, as in the
[retention decision](docs/decisions/2026-09-07-historical-artifact-retention.md). Git retains the
historical bytes; accepted ADRs remain immutable. Update live references in the same change.
Gate A rejects uncited review packets; citation alone does not establish that a packet is still needed.

| Change | Evidence |
|---|---|
| Code, validator, or exit code | The affected tests |
| Agent, skill, command, or bundled reference | The matching asset or contract test |
| Routing description | The overlapping clean-room scenarios; pure wording changes need no live eval |
| Eval harness or scenario | The affected `evals/test_*.py`; `python evals/build_probe.py --validate` for parsing or targeting changes; `python evals/judge.py --calibrate` after a rubric edit |
| Read-only guard or hook wiring | `python -m pytest scripts/test_readonly_guard.py scripts/test_hook_wiring.py`; exit codes stay 42 allow, 43 deny, 44 indeterminate |
| Any byte added under `agents/`, or under `skills/` outside a bundle's `references/` | `python scripts/check_weight.py`; the ceilings in `scripts/weights.json` are ratchets; growth beyond remaining headroom fails Gate A unless the same change raises the ceiling and says why. Bundled `references/` are on-demand depth and sit outside the ceiling — `check_context_cost.py` bounds them when they reach a task path |
| Canonical task-path file or `description:` field | `python scripts/check_context_cost.py`; it fails when a task or the always-loaded description total exceeds its byte budget |

When the acting lane already has Bash, a check may run inside an official pinned Docker image rather
than against a substitute or missing host binary, under
[the Docker-backed verification contract](docs/docker-verification.md).

Live evals run from `evals/build_probe.py` in a manual clean room, not CI. Raw traces and the batch
summary stay private under `.eval-runs/`; quote the numbers you rely on into the PR or review that
uses them.

Before pushing, run the structural gate once:

```powershell
python scripts/gate_a.py
```

Run it once, at the push boundary, and never through a pipe — a pipe masks its exit code.
When the change reaches code, tests, or frontmatter, run the suite at that same boundary.
In the project environment, install its constrained test dependencies first:

```powershell
python -m pip install -r requirements-test.txt
python -m pytest -q
```

[`.github/workflows/validate.yml`](.github/workflows/validate.yml) then runs three jobs on the
pull request: `validate` (this same gate), `component-tests` (`pytest` against
`requirements-test.txt` on Linux), and `claude-plugin-contract`
(npm's latest Claude Code release, with its resolved version recorded in the job log).
That job validates `.claude-plugin/marketplace.json` with `--strict` and
`.claude-plugin/plugin.json` without it: plugin errors fail the job; warnings remain visible.
The root `CLAUDE.md` intentionally provides repository authoring context and produces a warning
because installed plugins do not load it. Report what ran and what remains unverified.

## 4. Publish the intended change

Fetch before comparing — `origin/main` is a local ref, and pull requests land mid-session, so an
unfetched base hides work that is already on `main`:

```powershell
git fetch origin
git diff origin/main...HEAD --stat
git diff origin/main...HEAD
git log origin/main..HEAD --oneline
```

Confirm the diff and commit list hold only the intended work. `main` takes pull requests only;
Save Toolkit maintainers merge. Production deployment of new bytes is a separate, exact-candidate
decision under
[`production-change-gate`](skills/production-change-gate/SKILL.md).
