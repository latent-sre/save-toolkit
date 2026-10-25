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
[frontmatter reference](skills/agent-authoring/references/claude-code-frontmatter.md). Pin
third-party dependencies in `requirements-dev.txt`; `scripts/readonly-guard.py` stays
standard-library-only under `python -I -S`. Commands using `python` here mean the verified project
interpreter; activate that environment or use its full executable path. A bare `python` or `py -3`
can select a different version on Windows; avoid the Store stub.
`rg` hides generated projections through [`.ignore`](.ignore); pass `--no-ignore` to inspect them.

### Changing a delegation or handoff edge

A model-call edge `A → B` is the `Agent(save-toolkit:B)` grant in `agents/A.md`. Its one source is
that grant, pinned by `EXPECTED_DELEGATION` in `scripts/validate_fleet.py` and rendered as the
"Delegates to" column of the `AGENTS.md` roster; never re-tabulate edges elsewhere. Change all
three in one commit, regenerate, then run Gate A: the source check, the roster render check, and
the byte-for-byte adapter gate (Copilot `agents:`) must all pass.

A VS Code handoff edge is separate and never alters an `Agent(...)` grant. Edit
`COPILOT_HANDOFFS_BY_SOURCE` in `scripts/generate_platform_adapters.py`, update the exact
source-target and authority assertions in `scripts/test_platform_adapters.py`, regenerate, and run
those tests and Gate A. Keep `researcher` call-only and every handoff `send: true`.

### Read-only guard scoping

Hook matchers can express an agent-scoped hook; the read-only guard deliberately does not use one.
A matcher can silently stop matching after an upstream rename. The guard instead runs on every
Bash or PowerShell call and scopes itself in Python. PowerShell uses a separate literal-command
grammar and native launcher; it is not parsed as arbitrary POSIX shell code. Its canaries deny a
guarded name under a changed plugin namespace, or a recognized guarded identity in another
top-level key containing `agent` when `agent_type` is absent. A renamed key such as `role` is not
detected. Re-probe the live PreToolUse payload after host upgrades; offline tests cover known
shapes, not every upstream rename.

Python 3.12 is the minimum supported version for all repository Python, including installed
hooks and bundled skill scripts. The structural CI job runs on the latest 3.12 patch.
Development and component-test CI track the latest Python 3.14 patch; `.python-version` selects
that development minor and CI uses `check-latest: true`. Use `uv python install 3.14`, then create
`uv venv --python 3.14 .venv` if a matching environment does not already exist. Verify it with
`.venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version)"`
(POSIX: `.venv/bin/python`). Use this interpreter for installation, the baseline, and final checks.
This repository uses requirements/constraints files, not a uv project lock; keep that workflow.
An old uv binary may need updating before it knows about a newly released Python patch.
The development default does not change the repository's Python 3.12 compatibility floor.

For the optional Grafana analysis libraries, install only their constrained subset with
`uv pip install --python .venv\Scripts\python.exe -r requirements-grafana.txt`
(POSIX: use `.venv/bin/python`). Exact versions remain in `requirements-dev.txt`.
The Grafana workflow runs with `python -I` in that managed environment for data analysis, query
parsing, capture comparisons and image validation. Its low-level read helper and the hook guard
remain standard-library-only under `python -I -S`. Plugins do not install these dependencies.

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
historical bytes; an accepted ADR changes only through a successor or its decision owner's dated
amendment. Update live references in the same change.
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
Behavioral campaign plans include Sonnet, Sol, Luna and Terra coverage. Start with the
[four-model testing block](docs/fleet-evaluation/multi-model-testing.md) to check the supported
paths, then name the exact models, cases and limits for the campaign. Record unsupported profile
coverage explicitly; a structured Codex artifact result does not establish native routing,
hooks or helper continuation. Keep model and host results separate. This coverage requirement
does not authorize automatic model calls, extra trials or spend beyond the owner's campaign budget.
Every active scenario declares `max_turns`; missing or invalid limits are refused before calls.
Use saved counts and timing evidence to size a change, retain its rationale, and distinguish an
offline budget choice from measured live completion. Runner edits retain the saved-run rescore/diff
comparison and an explanation of every changed verdict. Oracle changes also exercise the supervised
completion path, including candidate failure and early exit, unavailable measurement and oracle crash.

Before pushing, run the structural gate once:

```powershell
python scripts/gate_a.py
```

Run it once, at the push boundary, and never through a pipe — a pipe masks its exit code.
Choose local verification from the changed behavior, not the directory alone:

- Agent/skill/command prose, descriptive frontmatter, bundled reference text, and scenario data
  changes need Gate A and the matching checks in the table. They do not require an unrelated full
  suite solely because frontmatter or an `evals/` path changed. Tool grants, delegation, hooks,
  executable examples, inline fixture code, and check commands still need their behavioral tests.
- Executable code, tests, dependencies, or test configuration changes require the default suite
  once at the final boundary, after focused checks. Include the heavy suite when changing the
  evaluator, oracle, grader, runner, shared eval fixtures/helpers, or heavy-test selection. A
  scenario-only change needs its affected heavy file when relevant, not every heavy file.
- CI continues to run both full shards for every pull request. Report skipped or unavailable
  checks; a narrower local run does not establish live behavior or replace required CI.

Install the constrained test dependencies in the project environment. Use the
[coordinated local runner](scripts/local_tests.py) for the final suite. Run the default command
below, or append `--heavy` when the rule above requires it; do not run both for the same candidate:

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-test.txt
.venv\Scripts\python.exe scripts/local_tests.py
```

One caller owns that run; helpers return their focused evidence instead of starting duplicate full suites. The runner
refuses a second coordinated run across linked worktrees while the first owns its OS-held lease.
The lease releases on process exit; do not delete its file or terminate another owner's job.
Direct `pytest` commands and separate clones do not participate, so coordinate those explicitly.

The runner prints a directory under the common Git directory's `local-test-runs/` containing
`pytest.log`, `junit.xml`, and `run.json`: start/end time, elapsed seconds, command, effective worker
and selection settings, interpreter/dependency versions, and Git revision/dirty state before and
after. A dirty receipt is not proof of an exact committed candidate; untracked contents are not
hashed. An interrupted run may have incomplete artifacts. Keep comparable receipts when assessing
speed: same candidate and selection, known competing workloads, and the same interpreter.

`pytest.ini` defaults to **10 local workers** with `--dist worksteal`; CI passes its explicit
four-worker override on the command line. Do not export worker options through `PYTEST_ADDOPTS`:
fixture suites inherit that variable and start additional worker pools. CI disables automatic
plugin loading and explicitly loads xdist and Hypothesis; the FastAPI fixture opts into Schemathesis.
Work stealing balances individual cases across workers; module and class
fixtures can run once on each worker that receives their tests. Pass `-n 0` for a debugger or
`--pdb`, or a smaller count on a constrained host. More workers are not a speed guarantee.
For the opt-in incidents-page and incidents-console UI calibrations, pass `--dist loadfile`
to run each module's full Vitest matrix once instead of repeating it on several workers.
The default skips heavy files listed in `conftest.py`
(`HEAVY`): `--heavy` includes them, `-m heavy` selects only them, and naming a file runs it directly.
The default run and exact `-m heavy`/`-m "not heavy"` selections exclude the other files before
importing them. Mixed marker expressions keep pytest's normal marker evaluation.
Use `python -m pytest <affected files>` for focused work; use the coordinated runner once for the
final suite and retain its timing evidence.

For recurring focused checks, `python scripts/local_tests.py --list-suites` lists named groups and
`python scripts/local_tests.py --suite python-craft` resolves their explicit test paths. Repeat
`--suite` to combine groups. Pytest filters remain available and are recorded as filtered runs;
extra positional test paths cannot be combined with a suite. Named suites do not replace the final
suite requirements above. The [eval catalog](evals/README.md#find-and-run-checks) also lists native
cases and links existing benchmark campaigns without executing them. Run `python evals/catalog.py
check` when editing suite membership or the track index; `coverage` exposes unassigned cases and
test files. Add new root tests and native scenarios to explicit capability suites in the same change.
Finalize definitions before exporting fingerprints for a new
campaign; keep historical result identities intact.

On POSIX, substitute `.venv/bin/python`. Installing `requirements-test.txt` honors its
`requirements-dev.txt` constraints; it is a selected test set, not a complete environment export
for `uv pip sync`. CI retains its setup-python/pip workflow in a job-owned environment.
Both test jobs cache pip downloads, keyed on the test requirements and development constraints.

[`.github/workflows/validate.yml`](.github/workflows/validate.yml) then runs these jobs on the
pull request: `validate` (this same gate); the two `fast-tests` matrix entries (the default `pytest`
run against `requirements-test.txt` on Linux) and the three `eval-tests` matrix entries in
parallel. Each matrix selects its shards through pytest's `-k`, and its last entry is the complement
of the others, so every case runs in exactly one shard; the real collection contract checks the eval
entries' union and overlap. `component-tests`,
the required check, passes only when fast tests and every eval matrix entry passed; and
`claude-plugin-contract`
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
