# Contributing

The short path for repository changes. [`AGENTS.md`](AGENTS.md) owns fleet-wide authority and the
rule map; [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md) is the only live backlog.

## 1. Protect current work

Check `git status` before editing and leave unrelated work alone. Use a separate worktree rather
than switching, stashing, or rebasing someone else's dirty checkout. Never rewrite published history
without the owner's approval.

## 2. Change the source of truth

Edit agents, skills, commands, and hooks only under `agents/`, `skills/`, `commands/`, and `hooks/`;
`.github/agents/`, `.github/skills/`, and `com.github.copilot/` are generated. After a canonical change, regenerate once and commit
the projections with the source:

```powershell
python scripts/generate_platform_adapters.py --write
```

Before changing frontmatter, tool authority, delegation, or guard wiring, read the
[frontmatter reference](skills/agent-authoring/references/claude-code-frontmatter.md).
Commands using `python` here mean the verified project
interpreter; activate that environment or use its full executable path. A bare `python` or `py -3`
can select a different version on Windows; avoid the Store stub.
`rg` hides generated projections through [`.ignore`](.ignore); pass `--no-ignore` to inspect them.

Host-supplied MCP dependencies: `researcher` uses the host's GitHits and Context7 servers and
`sre-assistant` the Playwright server; this plugin declares none of them. Grants name exact tools,
so a server-side rename silently drops the tool — re-verify those grants after MCP upgrades.

### Changing a delegation edge

A model-call edge `A → B` is the `Agent(save-toolkit:B)` grant in `agents/A.md`. Its one source is
that grant, pinned by `EXPECTED_DELEGATION` in `scripts/validate_fleet.py` and rendered as the
"Delegates to" column of the `README.md` roster; never re-tabulate edges elsewhere. Change all
three in one commit, regenerate, then run Gate A: the source check, the roster render check, and
the byte-for-byte adapter gate must all pass. The [Copilot projection](docs/copilot-projection.md)
grants the `agent` tool without enforcing each parent's list of delegation targets.

Keep handoff instructions short. Add a generic handoff rule to a delegating agent only when a
build probe in `evals/build-scenarios/` shows the agent failing without it.

### Read-only guard scoping

After a host upgrade, re-probe the live `PreToolUse` payload to verify that the guard still
recognizes the agent.

Python 3.14 is the minimum supported version for all repository Python, including installed
hooks and bundled skill scripts; a host whose `python3` is older is unsupported, and the guarded
hook fails closed there. Development and CI track the latest 3.14 patch; `.python-version`
selects it and CI uses `check-latest: true`. Use `uv python install 3.14`, then
`uv sync --locked`, which creates `.venv` on that interpreter and installs the locked `test` group.
Verify it with `.venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version)"`
(POSIX: `.venv/bin/python`). Use this interpreter for the baseline and final checks.
An old uv binary may need updating before it knows about a newly released Python patch.

`pyproject.toml` declares the dependency groups and `uv.lock` holds every exact version with its
hash; `uv sync --locked` fails when the two disagree. Change a dependency with
`uv add --group <group> <requirement>`, or edit the manifest and run `uv lock`, and commit both
files; `uv lock --upgrade-package <name>` moves one package, and Dependabot proposes the weekly
grouped updates. Each pinned version lives in exactly one file: the `swt` group's exact pins, which
`evals/swt_adapter/verifier.py` reads; Harbor's version and wheel hash in `uv.lock`, which
`evals/harbor_adapter/contracts.py` reads; and each sandbox image's `requirements.txt`, which that
sandbox's validators, probe and tests read. A test or validator never restates a dependency
version: it checks the package set, that each pin is exact, and that the installed or reported
version matches the one source, so a version bump is one edit. The `swebench` group installs on top
of the project environment (`uv sync --locked --group swebench`); `harbor` and `swt` are declared
conflicting with it and install only into a separate environment, for example
`UV_PROJECT_ENVIRONMENT=.eval-runs/harbor-sdk uv sync --locked --only-group harbor`.

The Grafana read helper, dashboard hygiene checker, and read-only hook guard remain
standard-library-only under `python -I -S`. Plugins do not install third-party dependencies.

## 3. Verify in proportion to the change

Run the smallest check that exercises the changed behavior. A new contract needs one focused test
that fails for the named break and passes after the fix. A new mechanism needs the measured failure
it prevents, stated in the PR, plus the byte delta where the growth row below applies; the default
response to a finding is a deletion or a one-line rule. Keep evidence under `docs/reviews/` while an unresolved roadmap
decision or a current regression depends on its measurements, including failed results. A changelog
entry or a comment recording when a test first ran is not a retention reason. Remove completed
reports, retired eval fixtures, and restoration bundles once their current dependency is gone;
an explicit preservation decision requires a successor or owner disposition, as in the
[retention decision](docs/decisions/2026-09-07-historical-artifact-retention.md). Git retains the
historical bytes. Update live references in the same change.
Gate A rejects uncited review packets; citation alone does not establish that a packet is still needed.

| Change | Evidence |
|---|---|
| Code, validator, or exit code | The affected tests; `python -m ruff check` for Python under `scripts/` or `skills/`, and `python -m mypy` when the file is in `pyproject.toml`'s mypy list |
| Agent, skill, command, or bundled reference | The matching asset or contract test |
| Routing description | The overlapping clean-room scenarios; pure wording changes need no live eval |
| Scenario data, prompt, target, or expected result | `python evals/build_probe.py validate` and the matching scenario/grader contract tests; execute changed fixture code or check commands through their affected behavioral tests |
| Eval harness, grader, or runner | The affected `evals/test_*.py`; `python -m ruff check`, `python -m ruff format --check` and `python -m mypy` for a change to the runner (`evals/build_probe.py`, `evals/probe/`), `evals/compare_runs.py`, `evals/graders.py`, `evals/inspect_pilot.py` or an `evals/test_*.py`; `python evals/judge.py --calibrate` after a rubric edit |
| Judge, clean room or oracle Python | The affected behavioral tests and `python -m ruff check --isolated --select E9,F63,F7,F82 evals/judge.py evals/clean_room.py evals/oracles`; preserve byte-bound formatting and incremental typing unless a broader migration has a measured benefit |
| Read-only guard or hook wiring | `python -m pytest scripts/test_readonly_guard.py scripts/test_hook_wiring.py`; exit codes stay 42 allow, 43 deny, 44 indeterminate |
| Large agent, skill, or reference growth | State the byte delta and why the task needs it in the PR; no mechanical ceiling remains, so reviewers own the context-cost judgment |

When the acting lane already has Bash, a check may run inside an official pinned Docker image rather
than against a substitute or missing host binary, under
[the Docker-backed verification contract](docs/docker-verification.md).

Live evals run from `evals/build_probe.py` in a manual clean room, not CI. Raw traces and the batch
summary stay private under `.eval-runs/`; quote the numbers you rely on into the PR or review that
uses them.

The suite must also pass under an elevated account. Tests that bind a runtime to the host use
`probe_testkit.unelevated_host` to retain the real hostname and model an ordinary account.

Behavioral campaign plans include Sonnet, Sol, Luna and Terra coverage. Start with the
[four-model testing block](docs/fleet-evaluation/multi-model-testing.md) to check the supported
paths, then name the exact models, cases and limits for the campaign. Record unsupported profile
coverage explicitly; a structured Codex artifact result does not establish native routing,
hooks or helper continuation. Keep model and host results separate. This coverage requirement
does not authorize automatic model calls, extra trials or spend beyond the owner's campaign budget.
Every active scenario declares `max_turns` and runner edits retain a saved-run `rescore`/`diff`
comparison explaining every changed verdict (see [running](evals/docs/running.md) and
[internals](evals/docs/internals.md)). Oracle changes also exercise the supervised completion path,
including candidate failure and early exit, unavailable measurement, and oracle crash.

Before pushing, run the structural gate once and invoke it directly so the shell reports its exit code.

```powershell
python scripts/gate_a.py
```

Choose local verification from the changed behavior, not the directory alone:

- Agent/skill/command prose, descriptive frontmatter, bundled reference text, and scenario data
  changes need Gate A and the matching checks in the table. They do not require an unrelated full
  suite solely because frontmatter or an `evals/` path changed. Tool grants, delegation, hooks,
  executable examples, inline fixture code, and check commands still need their behavioral tests.
- Executable code, tests, dependencies, or test configuration changes require the default suite
  once at the final boundary, after focused checks. Include the heavy suite when changing the
  evaluator, oracle, grader, runner, shared eval fixtures/helpers, or heavy-test selection. A
  scenario-only change needs its affected heavy file when relevant, not every heavy file.
- CI runs no `evals/` tests, so the local runs above are the only evidence for an eval change;
  quote them in the pull request. Before an eval campaign's first trial, run
  `scripts/local_tests.py --heavy` on its exact candidate. Report skipped or unavailable checks; a
  narrower local run does not establish live behavior or replace required CI.

Install the locked test environment, then use the
[coordinated local runner](scripts/local_tests.py) for the final suite. Run the default command
below, or append `--heavy` when the rule above requires it; do not run both for the same candidate:

```powershell
uv sync --locked
.venv\Scripts\python.exe scripts/local_tests.py
```

On POSIX, substitute `.venv/bin/python`. One caller owns that run; helpers return focused evidence instead of starting duplicate full suites.
The runner coordinates linked worktrees via an OS-held lease (`scripts/local_tests.py`) and writes a
receipt directory (`pytest.log`, `junit.xml`, `run.json`) under the common Git directory's
`local-test-runs/`; a dirty receipt does not prove an exact committed candidate.

`pytest.ini` configures the default local worker pool, work stealing, and loopback-only socket and
timeout guards; CI passes its explicit four-worker override. Do not export worker options through
`PYTEST_ADDOPTS` (fixture suites inherit it and spawn extra worker pools). Pass `-n 0` for a
debugger or `--pdb`, and `--dist loadfile` for opt-in Vitest UI calibrations so each module's matrix
runs once. The default skips `HEAVY` files in `conftest.py` (`--heavy` includes them, `-m heavy`
selects only them, naming a file runs it directly). Use `python -m pytest <affected files>` for
focused work and `scripts/local_tests.py` once at the final boundary.

Use the [eval catalog](evals/README.md#find-and-run-checks) for focused checks and follow the final
suite rules above. Add new root tests and native scenarios to capability suites in the same change.
Run `python evals/catalog.py check` when changing suite membership or the track index.

The required [`component-tests (ubuntu-latest)` check](.github/workflows/validate.yml) runs Gate A,
the `scripts/` suite on the supported Python floor, and Claude Code's marketplace and plugin validators.

## 4. Publish the intended change

Fetch before comparing — `origin/main` is a local ref, and pull requests land mid-session, so an
unfetched base hides work that is already on `main`:

```powershell
git fetch origin
git diff origin/main...HEAD --stat
git diff origin/main...HEAD
git log origin/main..HEAD --oneline
```

Add one `CHANGELOG.md` entry per change under `[Unreleased]`, at most two lines saying what changed
for someone using the fleet; measurements, test counts, and byte deltas belong in the pull request
or a `docs/reviews/` record. Keep the last two releases and drop older ones, which Git retains.

For a Claude marketplace update, increment `version` in
[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) and match it in [`plugin.json`](plugin.json).
Use one version per set of shipping plugin files and record the full source commit in the release
record. Before announcing the update, upgrade an installed previous version in a disposable
Claude configuration. Check the installed version and read back a changed agent, skill, or hook.

Confirm the diff and commit list hold only the intended work. `main` takes pull requests only;
Save Toolkit maintainers merge. Production deployment of new bytes is a separate, exact-candidate
decision under
[`production-change-gate`](skills/production-change-gate/SKILL.md).
