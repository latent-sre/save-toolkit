# Python idiom

Defaults until the owner records a decision in stack-profile.

- **Read `pyproject.toml`, the lockfile, and CI config before choosing syntax or APIs** — the
  interpreter on `PATH` does not define compatibility.
- **`ruff`** for lint and format. Don't hand-format.
- **`mypy`** or **`pyright`** for type checking.
- **`uv`** is the environment manager; `poetry` is acceptable for a published library. Never
  `pip install` into system Python.
- Prefer **`dataclasses`/`pydantic`** to loose dicts and tuples for structured data.
- **`pytest`**: `parametrize` for cases, fixtures for setup, `tmp_path` for files, `monkeypatch` for
  boundaries, an injected clock for time.

## Separate decision from effect

A pure function computes *what* to do (`desired_replicas(...)`); a thin wrapper *does* it. `--dry-run`
then becomes trivial, and provable with a spy:

`spy = mocker.patch("mod.subprocess.run"); run(dry_run=True); spy.assert_not_called()`
