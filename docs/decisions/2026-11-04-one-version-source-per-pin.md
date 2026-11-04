# Keep each pinned version in one file, and read it from there

- Date: 2026-11-04
- Status: accepted by the repository owner's instruction in the session that implemented it; the
  implementing candidate still requires the normal human acceptance decision
- Decision owner: repository owner
- Scope: successor to the clause of [manage dependencies as a uv project](2026-11-02-uv-project-lockfile.md)
  that keeps adapter versions exact "in the manifest" and moves them "only with that contract"; the
  lockfile and the conflicting `harbor` and `swt` groups remain in force

## Context

[verified] On 2026-11-04 every version the earlier decision held exact was restated in two to six
places. The sandbox pins lived in `pyproject.toml`'s `sandbox` group and in each sandbox's
`requirements.txt`, and again as literals in the sandboxes' evidence validators, dependency probe,
runtime evidence output and tests; the SWT versions lived in the `swt` group and in
`evals/swt_adapter/verifier.py`; Harbor's version and wheel hash lived in the `harbor` group, in
`uv.lock` and in `evals/harbor_adapter/contracts.py`.

[verified] Dependabot's first run after the uv migration proposed every one of those pins in
separate pull requests per file, and each copy's consistency test would fail a pull request that
changed only one copy. A Dependabot bump of the graph runner image to
`langgraph-checkpoint-sqlite==3.1.2` had already left `activate.py` validating against 3.1.1, and
its contract test failed on main unnoticed: no CI job runs the sandbox suites, and the sandbox's
documented discovery command does not enter `tests/contract/`.

[sourced] Upstream SWT-Bench at the pinned revision declares its runtime packages without versions,
and neither the Harbor nor the SWT WP-09 campaign has executed, so no recorded measurement depends on
the frozen versions.

## Decision

We will keep each pinned version in exactly one file and have code and tests read it from there:

- Each sandbox image's `requirements.txt` is its only pin. Host validators, the dependency probe and
  tests parse it; runtime evidence records installed versions measured with `importlib.metadata`.
  Dependabot's `pip` ecosystem updates the three files directly.
- The `swt` group in `pyproject.toml` is the SWT runtime pin; `verifier.py` reads it.
- `uv.lock` is Harbor's version and wheel-hash source; `contracts.py` reads both. Harbor's upstream
  source commit, which no lock records, stays a constant in `contracts.py`, and the frozen case
  manifest's `harbor` block must agree with the lock.
- A test or validator never restates a dependency version. It checks the package set, that each pin
  is exact, and that what is installed or reported matches the one source.

Pinned versions move like any other dependency until a campaign is accepted; accepting a campaign is
what freezes the versions it ran on.

## Consequences

A version change is one edit, so Dependabot's pull requests can pass on their own merits. The checks
that remain still catch the failures they existed for: evidence from an image that differs from its
pins, an SWT environment with the wrong packages, and a manifest that names another Harbor wheel.

The sandbox images now record measured versions rather than asserted ones. Sandbox transitive
dependencies are not locked, so an image build resolves them fresh. Sandbox suites run only locally.

What would show this was wrong: a pinned-version bump that passes the suites but changes a measured
result, which would argue for freezing earlier than campaign acceptance.

<!-- ADRs are append-only once accepted. Only the decision owner may amend an accepted ADR, adding a
     dated "Amended:" line that names the change. Anyone else writes a new ADR and marks this one
     "superseded by <YYYY-MM-DD>-<slug>". -->
