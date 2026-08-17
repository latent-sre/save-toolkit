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

## Second pass (same day): the two deferred classes closed

The `ensure_ascii` and YAML-scalar rows below were initially recorded as "left alone" and were then
closed. Six mutants are now caught, each by a real assertion rather than an incidental crash:
description/short-description escaping on both hosts, both halves of the quoted-scalar guard, the
`or ""` in `_split_tool_specs`, and both arms of the skill-reference tail test.

Re-sweep, same command: survivors under the generator's own suite fell **16 → 13**.

Total survivor *lines* rose 23 → 53, which is a reporting artifact and not a regression. 40 of the 53
are the single `test_fleet_doctor.py` pairing: that file names `scripts/generate_platform_adapters.py`
as a string inside a mocked command tuple (`:31`), so literal-resolution enrols it as a subject the
test never executes, and every sampled mutant survives. The tool already knows this shape — see
`Subject.origin` — and collapses it to one "probably never exercises it" line, but that verdict is
deliberately withheld under `--limit`, because a bounded run cannot support a claim about total
survival. So a sampled run prints one line per mutant instead. Judge the generator by
`test_platform_adapters.py`; the other pairing says nothing about it.

*Worth noting:* this re-sweep ran while the working tree was being edited, which the previous
in-place design forbade. Worktree isolation landed in the same session.

## Survivors triaged and left alone

Survivors are not automatically defects. These were judged equivalent or adequately covered
elsewhere, and are recorded so the next sweep does not re-litigate them:

| Site | Mutation | Why it is left |
|---|---|---|
| `:799` | `__name__ == "__main__"` → `!=` | Tool artifact. The mutant runs `main()` at import time and exits 0, and `run_test` only checks the return code, so a process that died before running a test scores as "survived". Over-reporting, not a false clean. |
| `:318` | `ensure_ascii=False` → `True` on the **name** field | **Now provably equivalent, and this is the sharper answer than the original triage.** The escaping mutants on *description* fields are caught by the new tests, but this one is on `name`, and `NAME_RE` enforces kebab-case `^[a-z0-9]+(?:-[a-z0-9]+)*$` — an agent name can never contain a non-ASCII character, so the flag cannot change the output. Closed by proof rather than by test. |
| `:490`, `:585`, `:730`, `:758` | `followlinks=False` → `True`, and the link guards around it | Backed by the real-symlink tests above. With rejection itself tested, the `followlinks` flag is a backstop whose flip cannot change behaviour on any tree that reaches the walk. |
| `:411` | drop `disable-model-invocation == "true"` | `check_links` pins `MANUAL_ONLY` to exactly `{pcf-deploy, service-onboarding}` and requires the frontmatter flag on both, so the two operands cannot disagree. Equivalent in this repository. |
| ~~`:148`, `:212`, `:237`~~ | quoted-scalar guard, `or ""`, skill-reference tail | **Closed in the second pass.** Pinned not for their blast radius — a malformed value fails the `check_links` contract before reaching a projection — but because this is one of three readers in the repository that disagree about the same grammar, and consolidating them later is only safe with today's behaviour written down. |
| `:221`, `:256`, `:282`, `:350`, `:357`, `:463` | remaining operand drops and constant flips in the token adapter | Narrow paths in tool-spec splitting and description handling, each guarded downstream by the frontmatter contract. Recorded, not fixed. |

**Correcting this document's own first draft:** the `test_fleet_doctor.py` pairing was originally
written up here as an artifact of import-following. It is not. That file does not import the
generator — it names `scripts/generate_platform_adapters.py` as a **string inside a mocked command
tuple** (`:31`), and `literal` resolution has enrolled it that way since long before import-following
existed. The conclusion is unchanged (judge the generator by its own suite), but the stated cause was
wrong, and a review that misattributes a cause is how the next person draws the wrong lesson from it.

## Honest limits

`--limit 40` makes this a **sample**, not a proof. An evenly spaced sample spans the file; it does
not guarantee any particular mutant was tried. A clean bounded report means "no survivor among the
mutants run", never "the suite is complete". Only an unbounded run covers every mutant, and that has
not been done for this module.
