# Contributing

## 1. Set up

Run `uv sync --locked` from the repository root with Python 3.14 or newer. Use the resulting
virtual environment for the commands below.

## 2. Make the change

- Name new branches `<type>/<short-description>`, for example `chore/clarify-agent-permissions`. [Conventional Branch](https://conventionalbranch.org/)
- Start commit subjects with a type and optional scope, for example `docs(readme): clarify agent permissions`. [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)

Follow the [fleet rules](AGENTS.md). After editing `agents/` or `skills/`, run
`python scripts/generate_platform_adapters.py --write` and commit the generated files alongside the source.

Add a general handoff rule only for an observed failure. Cite an incident record, reviewed
transcript, or existing probe that shows the expected handoff and what happened. Run a focused
probe only if that evidence leaves the failure unclear.

## 3. Verify in proportion to the change

Run `python scripts/gate_a.py` before pushing. Reuse checks while their inputs still apply.

| Change | Additional verification |
|---|---|
| Prose or data | Check the affected asset or contract. Exercise competing routes when selection changes. Wording alone needs no live eval. |
| Code, tests, dependencies, or test configuration | Exercise the changed behavior. One contributor runs `python scripts/local_tests.py` once on the final candidate. For Python in `scripts/` or `skills/`, run Ruff and use mypy for its [configured modules](pyproject.toml). |
| Permissions or hooks, including prompt changes | Get independent review of what becomes allowed or denied. Exercise the affected boundary. After host or MCP upgrades, check the affected hook payload or tool grants on that host. |
| Generator or manifest | Run `python scripts/test_platform_adapters.py` and the Claude manifest validators in [CI](.github/workflows/validate.yml). |
| Evals | Follow the [eval change guide](evals/README.md#change-the-evals). |

## 4. Open a pull request

Target `main`, summarize the user-facing change in [CHANGELOG.md](CHANGELOG.md) under
`[Unreleased]`, and report what you verified. Maintainers merge. Keep review evidence while an
open decision or regression depends on it.

For a Claude marketplace release, bump [the plugin version](.claude-plugin/plugin.json), record
the full source commit, and verify a changed component after upgrading a previous installation
in a disposable profile.
