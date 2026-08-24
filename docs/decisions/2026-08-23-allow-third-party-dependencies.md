# Allow third-party dependencies everywhere, pinned in requirements-dev.txt

- **Date:** 2026-08-23
- **Status:** Accepted
- **Decision owner:** `latent-sre`
- **Supersedes:** the "Standard library only" Hard rules bullet (AGENTS.md) and its
  `docs/rules.md` index row, in full — including the PyYAML and blanket new-dependency bans.

## Decision

Third-party Python dependencies are permitted in every part of this repository — `scripts/`, the
Gate A path, the guard, the generator, skill bundles, and evals — under two conditions:

1. **Declared and pinned in `requirements-dev.txt`.** Exact versions, one file; never a bare
   `pip install <name>`.
2. **The first Gate A-path adoption pays its freight in the same PR.** Today no gate-path script
   imports a third-party package, so `python scripts/gate_a.py` still runs on a bare Python. The
   change that first introduces such an import must, in the same PR, add
   `pip install -r requirements-dev.txt` to both CI validate jobs and update `gate_a.py`'s
   docstring. Without that, the gate becomes an `ImportError` on every machine that has not
   installed the deps — the exact silent-ish failure this condition exists to prevent.

pytest may be installed and used as a runner. Test files keep the executable unittest entrypoint
that `check_test_layout.py` mechanically requires, so every suite remains runnable with bare
`python`; pytest collects `unittest.TestCase` natively, so the two coexist.

## Why

The old rule bought one property — "every host package must validate anywhere Python does", i.e.
an adopter can clone and run Gate A with zero pip installs — and the owner judged its cost too
high on 2026-08-23:

- Python's stdlib cannot parse YAML, so the rule forced a hand-rolled strict-subset parser
  (`scripts/fleet_frontmatter.py`) with its own bug surface, and forced every tooling design to
  contort around the absence of a real parser.
- The restriction repeatedly shaped decisions it had no business shaping (facts-file formats,
  validator designs) — the tail wagging the dog.
- The zero-install property survives *in practice* until a gate-path script actually imports
  something, and condition 2 makes that moment loud and paid-for rather than forbidden.

## What did not change

- `evals/` already required PyYAML (`requirements-dev.txt`); that is now the general pattern, not
  an exception.
- `scripts/test_gate_a.py` still pins that Gate A never runs the eval harness — that boundary is
  about push-boundary scope, not dependencies; its justification message no longer cites PyYAML.
- `scripts/test_validate_workflow.py` no longer forbids the CI validate job from installing
  `requirements-dev.txt`; the assertion embodying the old ban is removed.
- `check_test_layout.py`'s executable-entrypoint requirement stands unchanged.

## Reopen trigger

Distribution to an environment where pip installs are prohibited or impractical (air-gapped
adopters, locked-down runners) — at that point, either the gate path stays dependency-free by
construction or a vendoring strategy gets its own decision.
