# Manage dependencies as a uv project with one lockfile

- Date: 2026-11-02
- Status: accepted by the repository owner's instruction in the session that implemented it; the
  implementing candidate still requires the normal human acceptance decision
- Decision owner: repository owner
- Scope: successor to the pin-location clause of
  [allow third-party dependencies](2026-08-23-allow-third-party-dependencies.md) (its condition 1)
  and to the `CONTRIBUTING.md` sentence that kept the requirements/constraints workflow; the
  dependency allowance itself, the Gate A bare-interpreter condition, and the standard-library-only
  guard remain in force

## Context

[verified] The repository carried six requirements files: one canonical pin superset and five
subsets selected through `-c` constraints. Nothing resolved them together. On 2026-11-02 the Harbor
set could not install on any interpreter (its `litellm==1.106.4` requires `filelock<4.0`; the file
pinned `filelock==4.2.1`), the canonical set left transitives such as `litellm` unpinned so a fresh
install reached a published HIGH advisory, two pinned packages had no import site, and no mechanism
proposed updates: every pin was one to two months behind its release.

[sourced] uv resolves every dependency group into one universal `uv.lock` with hashes, supports
groups declared as mutually conflicting so an isolated environment stays isolated by resolver rule
rather than by comment, and `uv sync --locked` fails when the lock and the manifest disagree.
Dependabot updates `uv.lock`.

[sourced] The owner chose: re-resolve the project's dependencies to current releases rather than
reproduce the old pins; one lock with conflicting groups; delete the requirements files and bind
adapter identities to the lock; move the test jobs to `setup-uv` and add Dependabot and an advisory
scan.

## Decision

We will declare every dependency in `pyproject.toml` under `[dependency-groups]` and commit
`uv.lock` as the only exact pin set. `uv sync --locked` installs the default `test` group, which is
what CI and the final local suite use; `grafana` is included in it and `swebench` installs on top of
it. `harbor`, `swt` and `sandbox` are declared conflicting with the project groups and with each
other, and each installs with `--only-group` into its own `UV_PROJECT_ENVIRONMENT`.

Versions that an adapter or sandbox admits by contract stay exact in the manifest and move only with
that contract: Harbor 0.24.0 (`evals/harbor_adapter/contracts.py`), the SWT runtime table
(`evals/swt_adapter/verifier.py`), and the sandboxes' own `requirements.txt` files. Everything else
carries a floor equal to the version the suite was last proven on, and the lock holds the release
that resolved.

Adapter identities that hashed requirements files now hash `pyproject.toml` and `uv.lock`. Older
run identities are not rewritten; a new campaign binds the new inputs.

CI installs with `astral-sh/setup-uv` and `uv sync --locked`, bound to the `setup-python`
interpreter so the tested Python stays the latest 3.14 patch. The Gate A job still runs on a bare
3.12 interpreter and installs nothing; the first gate-path third-party import adds `uv sync
--locked` to that job in the same change, which is the 2026-08-23 condition restated. Dependabot
proposes weekly grouped lock updates, and the weekly scheduled run audits the locked sets against
published advisories without gating merges.

## Consequences

One resolution replaces six files that could disagree, and the Harbor conflict cannot recur
silently. A proposed version change arrives as a pull request with the full suite as its evidence
instead of as drift discovered at install time. The lock records hashes, so an install is bound to
exact artifacts.

The project environment's versions moved on 2026-11-02; the tests, lint and type checks passed on
the new set, and that evidence is in the implementing change. The eval identities for SWE-bench,
SWT and Harbor campaigns change with every lock update, including updates to packages those
adapters never import; that over-invalidation is accepted because the alternative is a per-group
export that a second test must keep in step. The `judge.py` install hint still names the deleted
file; its bytes are calibration-bound, so it changes with the next judge edit that requires
recalibration anyway.

What would show this decision was wrong: Dependabot failing to update conflicting groups, a host
where `uv` cannot be installed, or the lock's universal resolution rejecting a platform the team
uses. The retention of the requirements workflow in Git history is the rollback.

<!-- ADRs are append-only once accepted. Only the decision owner may amend an accepted ADR, adding a
     dated "Amended:" line that names the change. Anyone else writes a new ADR and marks this one
     "superseded by <YYYY-MM-DD>-<slug>". -->
