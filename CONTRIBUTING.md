# Contributing

The short path for repository changes. [`AGENTS.md`](AGENTS.md) owns the fleet-wide
rules; [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md) is the only live backlog.

## 1. Set up

Check `git status` before editing and leave unrelated work alone. Use a separate worktree rather
than switching, stashing, or rebasing someone else's dirty checkout. Never rewrite published history
without the owner's approval.

Python 3.14 is the minimum for all repository Python, including installed hooks and bundled skill
scripts; on a host whose `python3` is older, the guarded hook fails closed. Install the locked
environment and confirm the interpreter:

```powershell
uv python install 3.14
uv sync --locked
.venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version)"
```

On POSIX the interpreter is `.venv/bin/python`. `python` in this file means that interpreter; a
bare `python` or `py -3` can select a different version on Windows.

`pyproject.toml` declares the dependency groups and `uv.lock` pins every version; change one with
`uv add --group <group> <requirement>` or `uv lock --upgrade-package <name>` and commit both files.
Each pin lives in exactly one file, and a test or validator reads it from there instead of
restating it. The Grafana read helper, dashboard hygiene checker, and read-only hook guard stay
standard-library-only under `python -I -S`; plugins do not install third-party dependencies.

## 2. Change the source of truth

Edit agents, skills, commands, and hooks only under `agents/`, `skills/`, `commands/`, and `hooks/`;
`.github/agents/`, `.github/skills/`, and `com.github.copilot/` are generated. After a canonical
change, regenerate once and commit the projections with the source:

```powershell
python scripts/generate_platform_adapters.py --write
```

`rg` hides the generated projections through [`.ignore`](.ignore); pass `--no-ignore` to inspect
them. Before changing frontmatter, tool authority, delegation, or guard wiring, read the
[frontmatter reference](skills/agent-authoring/references/claude-code-frontmatter.md).

- **After a host upgrade,** re-probe the live `PreToolUse` payload to verify that the guard still
  recognizes the agent.
- **After an MCP upgrade,** re-verify the exact tool grants: `researcher` uses the host's GitHits
  and Context7 servers and `sre-assistant` the Playwright server, and a server-side rename
  silently drops the tool.
- **A delegation edge `A → B`** is the `Agent(save-toolkit:B)` grant in `agents/A.md`.
  Regenerate adapters and run Gate A after changing it; never tabulate edges elsewhere.
- **Handoff instructions stay short.** Add a generic handoff rule to a delegating agent only when
  a build probe in `evals/build-scenarios/` shows the agent failing without it.

## 3. Verify in proportion to the change

Run the smallest check that exercises the changed behavior. A new contract needs one focused test
that fails for the named break and passes after the fix. A new mechanism needs the measured failure
it prevents, stated in the PR; the default response to a finding is a deletion or a one-line rule.

| Change | Evidence |
|---|---|
| Code, validator, or exit code | The affected tests; `python -m ruff check` for Python under `scripts/` or `skills/`, and `python -m mypy` when the file is in `pyproject.toml`'s mypy list |
| Agent, skill, command, or bundled reference | The matching asset or contract test |
| Routing description | The overlapping clean-room scenarios; pure wording changes need no live eval |
| Read-only guard or hook wiring | `python -m pytest scripts/test_readonly_guard.py scripts/test_hook_wiring.py`; exit codes stay 42 allow, 43 deny, 44 indeterminate |
| Adapter generator or plugin manifest | `python scripts/test_platform_adapters.py`, `claude plugin validate .claude-plugin/marketplace.json --strict`, and `claude plugin validate .claude-plugin/plugin.json` |
| Anything under `evals/` | The rows and rules in [Change the evals](evals/README.md#change-the-evals) |
| Large agent, skill, or reference growth | State the byte delta and why the task needs it in the PR; reviewers own the context-cost judgment |

A check may run inside an official pinned Docker image under
[the Docker-backed verification contract](docs/docker-verification.md).

Choose the final run from the changed behavior, not the directory alone:

- **Prose and data** (agent, skill, and command prose, descriptive frontmatter, reference text,
  scenario data) need Gate A and the matching row above, not a full suite. Tool grants, delegation,
  hooks, executable examples, inline fixture code, and check commands still need their behavioral
  tests.
- **Executable code, tests, dependencies, or test configuration** need the default suite once at
  the final boundary, after focused checks.

Use `python -m pytest <affected files>` for focused work, with `-n 0` for a debugger. Never export
worker options through `PYTEST_ADDOPTS`; fixture suites inherit it and spawn extra worker pools.
Run the final suite once per candidate:

```powershell
.venv\Scripts\python.exe scripts/local_tests.py
```

One caller owns that run; helpers return focused evidence instead of starting duplicate suites.
Its receipt lands under the common Git directory's `local-test-runs/`; a dirty receipt does not
prove an exact committed candidate. Report skipped or unavailable checks; a narrower local run does
not establish live behavior or replace required CI.

Before pushing, run the structural gate once, invoked directly so the shell reports its exit code:

```powershell
python scripts/gate_a.py
```

Gate A proves the fleet is well-formed, never that it is correct. The required
[`component-tests (ubuntu-latest)` check](.github/workflows/validate.yml) runs Gate A, the
`scripts/` suite, and Claude Code's marketplace and plugin validators.

### Retaining evidence

Keep evidence under `docs/reviews/` only while an unresolved roadmap decision or a current
regression depends on its measurements, failed results included. Remove completed reports, retired
eval fixtures, and restoration bundles once that dependency is gone, and update live references in
the same change; Git retains the bytes. Keeping one anyway needs a successor or owner disposition,
as in the [retention decision](docs/decisions/2026-09-07-historical-artifact-retention.md). Gate A
rejects uncited review packets, but a citation alone does not show a packet is still needed.

## 4. Publish the intended change

Fetch before comparing; pull requests land mid-session, so an unfetched `origin/main` hides work
that is already merged:

```powershell
git fetch origin
git diff origin/main...HEAD --stat
git log origin/main..HEAD --oneline
```

Add one `CHANGELOG.md` entry per change under `[Unreleased]`, at most two lines saying what changed
for someone using the fleet; measurements belong in the pull request or a `docs/reviews/` record.
Keep the last two releases and drop older ones.

For a Claude marketplace update, increment `version` in
[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json), match it in [`plugin.json`](plugin.json),
and record the full source commit in the release record. Before announcing it, upgrade an installed
previous version in a disposable Claude configuration and read back a changed agent, skill, or hook.

To check an unpublished branch in VS Code, use an isolated profile, set `chat.pluginLocations` to
`{"/absolute/path/to/save-toolkit": true}`, and open a neutral test workspace; opening this
repository itself also discovers `.github/agents/` and `.github/skills/` and can hide
duplicate-install mistakes.

Confirm the diff and commit list hold only the intended work. `main` takes pull requests only;
Save Toolkit maintainers merge. Production deployment of new bytes is a separate, exact-candidate
decision under [`production-change-gate`](skills/production-change-gate/SKILL.md).
