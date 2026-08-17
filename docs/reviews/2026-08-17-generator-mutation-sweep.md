# Mutation sweep — `generate_platform_adapters.py`

> **Status: historical — closure evidence for a single sweep.** Not a task list. Live work is
> tracked only in [`fleet-roadmap.md`](../fleet-roadmap.md).

**Date:** 2026-08-17 · **Command:**
`python scripts/mutation_guard.py --module scripts/generate_platform_adapters.py --limit 40`

## Why this module, and why now

The generator is the single producer of all four host projections — 278 files, 735 lines of
source — and it had **no mutation coverage at all** behind a 429-line test file. `discover()`
derived subjects from the sibling filename and from `.py` string literals resolved against the
root, and `test_platform_adapters.py` reaches its subject as
`import generate_platform_adapters as adapters`, which is neither. Teaching discovery to follow
imports enrolled it for the first time; this sweep is the first result.

## What was fixed

**The anti-indirection control had no real-symlink test.** The generator refuses to walk links, so
a projection cannot silently absorb content from outside the repository, with
`os.walk(..., followlinks=False)` as the backstop. The sweep flagged *both* `followlinks=False`
constants as unnoticed — correctly, because no fixture anywhere contained a link, so the flag could
not matter in any test. The one existing test patched `_is_link_or_reparse` and covered only the
ancestor path; the in-walk branch that fires on a link *inside* `skills/` or a generated root ran in
no test at all.

Two tests now plant a real directory symlink — one in canonical sources, one in a generated root —
and assert the refusal. Both were confirmed to fail with the two `raise ValueError` branches
removed.

## Survivors triaged and left alone

Survivors are not automatically defects. These were judged equivalent or adequately covered
elsewhere, and are recorded so the next sweep does not re-litigate them:

| Site | Mutation | Why it is left |
|---|---|---|
| `:799` | `__name__ == "__main__"` → `!=` | Tool artifact. The mutant runs `main()` at import time and exits 0, and `run_test` only checks the return code, so a process that died before running a test scores as "survived". Over-reporting, not a false clean. |
| `:318`, `:447` | `ensure_ascii=False` → `True` | Would escape the curly quotes in agent bodies as `\uXXXX`. The unit suite misses it, but the byte gate does not: `validate_fleet` compares freshly generated output against the committed bytes, which still hold real quotes. Defence in depth already covers it. |
| `:411` | drop `disable-model-invocation == "true"` | `check_links` pins `MANUAL_ONLY` to exactly `{pcf-deploy, service-onboarding}` and requires the frontmatter flag on both, so the two operands cannot disagree. Equivalent in this repository. |
| `:490`, `:585` | `followlinks=False` → `True` | Now backed by the explicit link-rejection tests above. The flag itself stays as a backstop; with rejection tested, a mutant here is genuinely equivalent. |
| `:148`, `:212`, `:221`, `:237`, `:256`, `:282`, `:350`, `:357`, `:463`, `:730` | operand drops and constant flips in the YAML scalar reader and token adapter | Narrow parse paths (a value both opening and closing with `'`, empty-tail handling). Real but low-consequence: a malformed value fails the frontmatter contract in `check_links` before it can reach a projection. Recorded, not fixed. |

Everything reported under `test_fleet_doctor.py` rather than `test_platform_adapters.py` is a
pairing artifact of import-following: `fleet_doctor` imports the generator, so the two are paired,
but that suite makes no claim about generation. Judge the generator by its own suite.

## Honest limits

`--limit 40` makes this a **sample**, not a proof. An evenly spaced sample spans the file; it does
not guarantee any particular mutant was tried. A clean bounded report means "no survivor among the
mutants run", never "the suite is complete". Only an unbounded run covers every mutant, and that has
not been done for this module.
