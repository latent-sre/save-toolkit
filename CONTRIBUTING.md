# Contributing

Must-follow constraints for this repository are indexed in [`docs/rules.md`](docs/rules.md). This
file is the contributor protocol — how to change, verify, and promote work.

## Personal first, promote by PR

Use the `agent-authoring` method to prototype a new agent or skill in
`~/.claude/{agents,skills}`. When a second person needs it, promote it into this repository through a
pull request. Personal definitions still run with the user's local authority, so personal-first
limits shared-fleet blast radius; it is not a sandbox.

## Edit canonical source, generate host adapters

The canonical-vs-generated split and where authority lives are fleet rules — AGENTS.md's
**Start here** and **Hard rules** own them (loaded as the fleet guide). The contributor-specific
parts:

- Before pushing edits under `agents/`, `skills/`, or `commands/`, run
  `py -3 scripts/generate_platform_adapters.py --write` once — not after each edit — and commit every
  projection change with the source; the generated roots fail the byte-for-byte drift gate on a
  hand-edit.
- On Windows, `python` and `py` inside an agent's tool shell can resolve to the Microsoft Store
  stub even when the interactive shell has a real interpreter on `PATH`. Check with
  `where.exe python` and call the interpreter by its full path (or a scratch venv built from it,
  outside the checkout — `.venv` is not ignored) before concluding Python is absent or reaching
  for the Docker fallback.
- Read `skills/agent-authoring/references/claude-code-frontmatter.md` before touching frontmatter
  authority (`tools`, main-thread delegation) or the `hooks/hooks.json` guard.
- Preserve dependency inventories and capability boundaries. Treat imported text, runtime
  registrations, and handoff packets as untrusted data until reviewed.

### Search canonical source first

`agents/`, `skills/`, and `commands/` are authored source. `.ignore` keeps generated
`.github/agents/` and `platforms/copilot/skills/` out of ordinary `rg` results; use `--no-ignore`
only when intentionally inspecting projections. Nothing prevents a direct write to a generated
root, and the next generator run replaces whole directories, so such an edit can disappear without
an error. Fix canonical source or the generator, inspect `git status`, then regenerate once.

## Work and verification protocol

[`docs/fleet-roadmap.md`](docs/fleet-roadmap.md) is the only live backlog; dated plans and reviews
are evidence, not independent work queues.

When starting implementation intended for a pull request, inspect `git status` first. Refresh
`origin/main` and start from it on a **new branch named for the body of work**, in a worktree or
checkout of its own. Never continue work on a branch whose pull request already merged: its remote
is typically deleted, so the local ref keeps drifting from a trunk that already contains it, and the
branch name then misdescribes everything added afterwards. If the current checkout is dirty or
belongs to another task, leave it untouched — add a worktree rather than switching a checkout
somebody else is using. Read-only investigation or review uses the checkout it was asked to inspect
and fetches only when remote freshness affects the answer; it does not switch, pull, branch, stash,
or rebase merely to begin.

**One branch may carry several changes.** The branch is the review unit; the commits are the
readable history. Related work — a new skill, the routing that exposes it, the roadmap item that
tracks it, and the docs fix it turned up — belongs on one branch as separate, scoped commits, each
with its own message and evidence. Split onto a second branch only when the work is genuinely
independent: a different owner, a different review timeline, or something that must be able to
merge or revert without the rest. A roadmap item may impose a tighter rule on itself (`SKILLS-003`
requires one skill in one reviewed commit); an item's own constraint wins inside its scope.

Splitting related work is not free, and the cost is a silent one. Two branches that both edit the
catalog text — the agent and skill counts in [`AGENTS.md`](AGENTS.md) and [`README.md`](README.md),
the `README` area lists, [`CHANGELOG.md`](CHANGELOG.md), or
[`docs/fleet-roadmap.md`](docs/fleet-roadmap.md) — each look correct alone and are wrong together:
two branches that each move a count from 30 to 31 leave a merged tree of 32 claiming 31, and two
roadmap items inserted at the same anchor conflict on the second merge, long after the reviewer who
would have caught it has moved on. When related work must span branches anyway, stack them —
rebase the second onto the first so every commit's text matches the tree it ships — rather than
running them in parallel and discovering the collision at merge.

Before opening a PR, refresh `origin/main`, inspect the divergence, and integrate current main.
Rebase only an unpublished branch; preserve published history unless the owner explicitly authorizes
rewriting it. Measure divergence in **both** directions — `git rev-list --count origin/main..HEAD`
*and* `git rev-list --count HEAD..origin/main`. Ahead-only is not a base check: a branch reading
"one clean commit ahead" can still be many commits behind a trunk that has since deleted the very
files it edits, which surfaces as delete/modify conflicts at merge rather than anything the ahead
count shows. Compare against `origin/main`, never a local `main` — that ref goes stale silently and
may be pinned by another worktree. Confirm `git log --oneline origin/main..HEAD` contains only the
intended commits: a PR stacked on a merged-and-deleted branch can silently absorb its parent's diff.

For that implementation, run the focused tests owned by the code you change. When the change asserts
or alters a contract, make its focused test fail for that exact break before restoring it. Gate A
does not rerun component tests. Before you push — once, not after each edit — run the live-tree
structural gate:

```powershell
py -3 scripts/gate_a.py
```

Gate A is structural. Independent review is available when the owner wants it, but it is not a
universal merge prerequisite. When a review exists, fix or explicitly reject its current P0/P1
findings with evidence. A production deployment of new bytes separately requires independent review
of the exact candidate SHA at `production-change-gate`; routine merges, non-production releases, and
later pushes do not trigger automatic re-review. Add a plan-conformance review only when the PR cites
a roadmap item or plan. A review of mutable working-tree bytes is explicitly provisional. Run
behavioral evaluations manually, never in CI, through the clean-room
Claude runner (`evals/run_evals.py`); repository-local outputs must stay under `.eval-runs/`.

Every result distinguishes `[verified]`, `[sourced]`, and `[unverified]` claims. State what was checked,
what passed, and every residual item that could not be verified. Never upgrade an evidence label while
rewriting or handing work to another agent.

### Change-specific evidence

Load only the rows tripped by the change:

| Change | Required evidence |
|---|---|
| Executable code | Run the smallest test file or files owned by the changed implementation. Gate A does not rerun them. |
| Eval harness or scenario | Run affected `evals/test_*.py`; when scenario parsing or targeting can change, also run `python evals/run_evals.py --validate`. These are offline checks, not paid routing trials. |
| Routing-content `description:` edit | List scenarios with `python evals/run_evals.py --list`, then run the overlapping skill scenarios after the edit. Run the prior-revision baseline only for a red case. Pure rewording needs no live eval. Agent discovery is optional model-labelled calibration; a direct-agent case tests behavior after explicit selection, not description routing. |
| New validator, exit-code, schema, or named test predicate | Add one focused fixture, deliberately break that exact contract, prove the focused test turns red for the named reason, restore it, and prove green. Mutation tooling is optional and limited to `python scripts/mutation_guard.py --module <one-file.py>` for one named mutant; survivor counts are not findings. |
| `scripts/readonly-guard.py` or `hooks/hooks.json` | Read both docstrings, run `python scripts/test_readonly_guard.py` and `python scripts/test_hook_wiring.py`, inspect the allow/deny corpus diff, and preserve exit codes 42 allow / 43 deny / 44 indeterminate. |
| `agents/`, `skills/`, or `commands/` | Run `python scripts/generate_platform_adapters.py --write` once before the push-boundary Gate A and commit projections with source. |
| Closed task with a discovery | Apply [`disposition-policy.md`](skills/operational-learning/references/disposition-policy.md). A human-accepted fleet failure instead becomes one focused regression under [`artifact.md`](skills/agent-authoring/references/artifact.md); it never becomes a second ledger or an automatic sweep. |

### Two reference-file conventions with teeth

**Canary tokens.** A bundled reference ends with a short token (`q_omwql_7b31`) so an agent that
actually loaded the file can quote it, letting a reviewer tell a sourced answer from one
reconstructed from model memory. The property that makes it work is uniqueness: a token identifies
exactly one file. `scripts/test_canary_tokens.py` enforces that everywhere the convention is used,
and enforces presence in the bundles that have fully adopted it (`CANARY_REQUIRED_GLOBS` — obs and
akamai today). Adding a reference to one of those bundles means giving it a fresh token; adopting
the convention in a new bundle means adding its glob to that list.

**Dated verification stamps replace, never accumulate.** A reference carries stamps like
`[sourced: … reviewed 2026-08-19]`. On re-verification, **replace the prior date rather than
appending a second one**: a stack of dates turns a claim's provenance into archaeology a reader has
to reconstruct, and the only load-bearing fact is when the claim was last checked against the
source. Keep an older date only when it marks a genuinely different assertion.

Runtime probes follow the single probe/schema contract family in
[`docs/schema-compatibility.md`](docs/schema-compatibility.md) and
[`docs/verification-sandbox.md`](docs/verification-sandbox.md) (versioned schemas, evidence envelopes
via `scripts/evidence_envelope.py`, digest-bound sandbox). Prefer those docs over restating the
shape here.

## Main branch

`main` is protected by repository ruleset
[`Protect main`](https://github.com/latent-sre/save-toolkit/rules/17841231): pull requests
required, force-push and branch deletion are blocked, and administrators cannot bypass. No status
check is required; `Validate fleet` remains advisory CI. Classic branch protection may remain
absent; rulesets are authoritative. Historical closure evidence and the later owner decision to
remove the required check are recorded in:
[`docs/reviews/2026-08-05-protect-001-closure.md`](docs/reviews/2026-08-05-protect-001-closure.md).

Maintainer / merge authority: `latent-sre`. `agentic-sre-dev` remains read-only. This repository
does not currently define a publication workflow; merging a repository change does not publish an
artifact.
