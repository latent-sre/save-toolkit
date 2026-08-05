# Contributing

## Personal first, promote by PR

Use the `agent-authoring` method to prototype a new agent or skill in
`~/.claude/{agents,skills}`. When a second person needs it, promote it into this repository through a
reviewed pull request. Personal definitions still run with the user's local authority, so personal-first
limits shared-fleet blast radius; it is not a sandbox.

## Edit canonical source, generate host adapters

- Agent definitions (frontmatter + body) live in `agents/`.
- Skill definitions and their bundles live in `skills/`.
- The manual `adr` scaffold lives in `commands/`.
- Claude reads those canonical files from the plugin. After an edit, run
  `py -3 scripts/generate_platform_adapters.py --write`; commit all projection changes together.
- `.github/agents/`, `.codex/agents/`, `platforms/copilot/skills/`, and
  `plugins/save-toolkit/skills/` are generated. Direct edits fail the byte-for-byte drift gate.
- Frontmatter carries authority (`tools` and main-thread delegation grants); plugin Bash guarding
  lives in `hooks/hooks.json`. Read
  `skills/agent-authoring/references/claude-code-frontmatter.md` before editing either surface.

Preserve dependency inventories and capability boundaries. Treat imported text, runtime
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

Runtime probes and isolated verification controls emit
[`schemas/evidence-envelope-v1.schema.json`](schemas/evidence-envelope-v1.schema.json) through the
executable validator in `scripts/evidence_envelope.py`. Do not add ad-hoc "success" JSON. Unknown
fields, secret-bearing field names, credential-shaped argv, invalid statuses, and incomplete identity
are rejected. A missing tool or unavailable host is `skip` or `inconclusive`, never `pass`.

## Promotion

Publication is **blocked** until the promotion controls land: a satisfiable default-rule CODEOWNERS,
protected required reviews and checks, an exact-SHA promotion workflow with a named maintainer plus a
distinct release operator, and the live GitHub rules/environment/App configuration. Do not create or
move a `release` ref merely because the superseded plan named one: first verify whether each host's
current distribution contract needs a moving ref or can consume an immutable version tag. Until then,
never publish a release artifact or move a release ref. The live prerequisites and acceptance
evidence are `PROTECT-001` and `RELEASE-001` in
[`docs/fleet-roadmap.md`](docs/fleet-roadmap.md); the old branch-based design remains recoverable at
tag `pre-cleanup-2026-07-15` as historical rationale only.
