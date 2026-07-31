Read this before a behavior-preserving reshape — rename, move, contract change with no observable change.

## Before you touch anything
1. **Pin behavior with tests.** If the area is undertested, add **characterization tests** that capture
   current behavior first using the [tests-first process](./tdd.md). Refactoring without tests is just editing and hoping.
2. **Map the blast radius.** Grep **every** call site / consumer of what you're changing
   (`grep`/`rg` across the repo, plus configs and other languages). List who is affected.

## Work in small reversible steps
- One refactor per commit; **never mix a refactor with a behavior change** — they hide each other in review.
- Keep the suite green after each step. If it goes red, you changed behavior — stop and reassess.
- Prefer the tooling's safe operations (rename symbol, extract function) over manual edits.

## Changing a shared contract → expand → migrate → contract
Don't break callers in one shot:
1. **Expand** — add the new signature/field/endpoint alongside the old; both work (deprecate the old).
2. **Migrate** — move every caller to the new path; dual-write/dual-read data if needed.
3. **Contract** — remove the old path only after you've confirmed nothing uses it.

For risky behavior, gate it behind a **feature flag** so rollout and rollback are independent of deploy.

## Done means
- Behavior is provably unchanged (same tests, still green) — or behavior changes are isolated in their
  own clearly-labeled commits.
- No caller left on a removed path; deprecations are documented.
- Each step is independently revertible.
