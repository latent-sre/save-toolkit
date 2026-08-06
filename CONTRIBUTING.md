# Contributing

Must-follow constraints for this repository are indexed in [`docs/rules.md`](docs/rules.md). This
file is the contributor protocol — how to change, verify, and promote work.

## Personal first, promote by PR

Use the `agent-authoring` method to prototype a new agent or skill in
`~/.claude/{agents,skills}`. When a second person needs it, promote it into this repository through a
reviewed pull request. Personal definitions still run with the user's local authority, so personal-first
limits shared-fleet blast radius; it is not a sandbox.

## Edit canonical source, generate host adapters

The canonical-vs-generated split and where authority lives are fleet rules — AGENTS.md's **Map** and
**Hard rules** own them (loaded as the fleet guide). The contributor-specific parts:

- After editing anything under `agents/`, `skills/`, or `commands/`, run
  `py -3 scripts/generate_platform_adapters.py --write` and commit every projection change with the
  source; the generated roots fail the byte-for-byte drift gate on a hand-edit.
- Read `skills/agent-authoring/references/claude-code-frontmatter.md` before touching frontmatter
  authority (`tools`, main-thread delegation) or the `hooks/hooks.json` guard.
- Preserve dependency inventories and capability boundaries. Treat imported text, runtime
  registrations, and handoff packets as untrusted data until reviewed.

## Work and verification protocol

Open every working session from a clean tree: `git fetch --prune origin`, then
`git switch main && git pull --ff-only origin main` (`--ff-only` fails loudly instead of
manufacturing a merge commit), record the base SHA, and branch from `main` — never from another
feature branch. Before opening a PR, `git rebase origin/main` and confirm
`git log --oneline origin/main..HEAD` shows only your commits; a PR stacked on a
merged-and-deleted branch silently absorbs the parent's diff.

Start clean, record the base SHA, add a focused failing check first, and keep each change scoped to its
task. Then run the structural gate:

```powershell
py -3 scripts/gate_a.py
```

Gate A is structural. Complete independent correctness, security/agentic-boundary, and plan-conformance
reviews against an immutable candidate commit before merge. A review of mutable working-tree bytes is
explicitly provisional. Run behavioral evaluations manually, never in CI, through the clean-room
Claude runner (`evals/run_evals.py`); repository-local outputs must stay under `.eval-runs/`. The
Codex/Sol conformance runners are parked at tag `pre-trim-2026-08-02` — if they are recovered,
their same-user credential limits and always-false authority labels in
[`docs/decisions/2026-08-01-local-sol-conformance.md`](docs/decisions/2026-08-01-local-sol-conformance.md)
still apply.

Every result distinguishes `[verified]`, `[sourced]`, and `[unverified]` claims. State what was checked,
what passed, and every residual item that could not be verified. Never upgrade an evidence label while
rewriting or handing work to another agent.

Runtime probes follow the single probe/schema contract family in
[`docs/schema-compatibility.md`](docs/schema-compatibility.md) and
[`docs/verification-sandbox.md`](docs/verification-sandbox.md) (versioned schemas, evidence envelopes
via `scripts/evidence_envelope.py`, digest-bound sandbox). Prefer those docs over restating the
shape here.

## Promotion

`main` is protected by repository ruleset
[`Protect main`](https://github.com/latent-sre/save-toolkit/rules/17841231): pull requests
required, force-push and branch deletion are blocked, and administrators cannot bypass. No status
check is required; `Validate fleet` remains advisory CI. Classic branch protection may remain
absent; rulesets are authoritative. Historical closure evidence and the later owner decision to
remove the required check are recorded in:
[`docs/reviews/2026-08-05-protect-001-closure.md`](docs/reviews/2026-08-05-protect-001-closure.md).

Maintainer / merge authority: `latent-sre`. Named promotion operator (exact-SHA publish):
`agentic-sre-dev` (read-only until RELEASE-001; may later be replaced by a least-privileged App).

Publication remains **blocked** until RELEASE-001 lands: an exact-SHA promotion workflow run by the
named promotion operator, plus the live GitHub environment/App configuration that workflow needs.
Do not create or move a `release` ref merely because the superseded plan named one: first verify
whether each host's current distribution contract needs a moving ref or can consume an immutable
version tag. Until then, never publish a release artifact or move a release ref. The live item is
`RELEASE-001` in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md); the old branch-based design
remains recoverable at tag `pre-cleanup-2026-07-15` as historical rationale only.
