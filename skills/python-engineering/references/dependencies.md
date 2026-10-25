# Dependencies and packaging

Use this before adding, replacing, upgrading, removing, or reorganizing dependencies or packaging.
Do not repeat this research for dependencies an unrelated edit leaves unchanged.

## Contents

- Choose the source of a capability
- Verify a material addition, replacement, or upgrade
- Declare dependencies
- Lockfiles and environments
- Toolchain choices
- Replacing a library or custom implementation
- Re-verify

## Choose the source of a capability

1. Existing project capability: a module or dependency already in the project. Extend it rather
   than adding a parallel one.
2. Standard library: when it covers the requirement fully on the minimum supported Python.
3. Maintained third-party package: when it implements a published standard or specification,
   handles security-sensitive or edge-case-heavy work, or replaces substantial custom code the team
   would otherwise maintain.

There is no standard-library-first rule unless the project states one (for example, a bare
interpreter deployment). MUST NOT hand-roll substantial functionality a suitable maintained library
serves without a concrete reason: a deployment constraint, a license conflict, an unacceptable
transitive footprint, or a verified gap. Weigh the custom code's testing, edge cases, and
maintenance against the dependency's update, audit, and supply-chain cost, and record the decision
row.

## Verify a material addition, replacement, or upgrade

Check each item and record what could not be verified:

| Check | Where to look |
|---|---|
| Package identity: exact distribution name, publisher, and repository | Package index page, project repository; watch for look-alike names |
| It provides the needed functionality | The package's own documentation for that version |
| Supported Python versions and platforms | `Requires-Python` and classifiers in metadata; wheels for the target platforms |
| API of the installed or proposed version | Installed source or `importlib.metadata`; versioned docs; changelog |
| Maintenance status and migration guidance | Release history, changelog, deprecation notices, upgrade guides |
| License compatibility | Distribution metadata and the license file |
| Known security advisories | A vulnerability scanner (for example `pip-audit`) or the OSV and PyPI advisory data |
| Transitive and operational cost | Resolved dependency tree, native extensions, install size, start-up cost |

- Use current primary documentation for uncertain APIs, package selection, and migrations. MUST NOT
  infer capabilities from a package name or from memory.
- Offline: use installed metadata (`importlib.metadata.version()`, `pip show`, `uv pip show`) and the
  installed source. Mark everything else unverified; never invent versions, APIs, or advisories.

## Declare dependencies

| Need | Declare in |
|---|---|
| Runtime requirement of a package | `[project].dependencies` |
| Optional feature | `[project.optional-dependencies]` extra |
| Development, test, lint, type, and docs tools | `[dependency-groups]`, or the project's existing equivalent |
| Single-file script | Inline script metadata (`# /// script` block), only when the runtime honors it |
| Build backend | `[build-system].requires` |

- Reusable library: declare the widest range the code actually supports, usually a lower bound.
  Add an upper bound only for a known incompatibility. Never pin exact versions in library
  metadata.
- Application or service: keep abstract ranges in metadata and get reproducibility from a lockfile
  or a pinned requirements file.
- Every runtime import outside the standard library MUST appear in the runtime declaration; test
  that a clean install imports.

## Lockfiles and environments

- Update lockfiles only with the dependency manager, for example `uv lock`, `uv add`,
  `uv lock --upgrade-package <name>`, `pip-compile`, or `poetry lock`. MUST NOT hand-edit a
  resolved lockfile.
- Upgrade only what the task needs. MUST NOT upgrade unrelated packages as incidental cleanup.
- Check that lock and metadata agree, for example with `uv lock --check`, and commit the lockfile
  with the metadata change.
- When installing or locking is not permitted, prepare the metadata change and report the exact
  command the owner should run.

## Toolchain choices

- For an unconstrained new project, evaluate uv (environment and locking), Ruff (lint and format),
  pytest (tests), and one maintained type checker (mypy or Pyright, or a newer checker whose own
  documentation declares it stable) as candidate defaults. Verify each one's current status and
  fit; they are starting candidates, not a mandated toolchain.
- In an existing project, use its tools. Recommend a replacement only with evidence of a material
  gap: a missing class of check, unsupported Python versions, or an unmaintained tool. Carry out a
  migration only when it is in scope, and never run two tools for the same job.

## Replacing a library or custom implementation

1. Inventory the used surface: every import, call, option, and caught exception of the old
   implementation.
2. Map each usage to the replacement and list semantic differences:
   - Defaults and coercion.
   - Accepted input formats and `None` or empty handling.
   - Exception types, and whether errors raise or return a sentinel.
   - Ordering and equality semantics.
   - Serialization and encoding.
   - Time zones and DST. Compare instants with `astimezone(timezone.utc)` plus `utcoffset()`:
     `==` ignores `fold` within one zone and is false across zones for ambiguous or missing
     times.
   - Timeouts, retries, and redirects.
   - Resource lifetimes and closing.
   - Thread-safety and async behavior.
   - Logging, and performance.
3. While both are installed, write differential tests that run the old and new implementations
   on the same inputs, including the differences listed. Without the old implementation, write
   characterization tests from its documented and observed behavior first.
4. Switch callers, preserving required behavior explicitly where the replacement differs (such as
   catching a new exception type to keep a fallback). Record any behavior that cannot be preserved
   and get it accepted.
5. Remove the old dependency from metadata, lockfiles, requirement files, and documentation.
   Confirm nothing imports it.

## Re-verify

Check these when package metadata, a tool, or a specification behaves differently from this file.

- [pyproject.toml specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [Dependency groups specification](https://packaging.python.org/en/latest/specifications/dependency-groups/)
- [Inline script metadata specification](https://packaging.python.org/en/latest/specifications/inline-script-metadata/)
- [install_requires versus requirements files](https://packaging.python.org/en/latest/discussions/install-requires-vs-requirements/)
- [uv: managing dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/)
- [uv: locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- [uv: running scripts](https://docs.astral.sh/uv/guides/scripts/)
- [pip-audit](https://github.com/pypa/pip-audit)
- [mypy command line](https://mypy.readthedocs.io/en/stable/command_line.html)
- [Pyright configuration](https://github.com/microsoft/pyright/blob/main/docs/configuration.md)
- [PEP 495: local time disambiguation](https://peps.python.org/pep-0495/)
