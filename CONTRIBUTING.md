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
  `plugins/sre-agents/skills/` are generated. Direct edits fail the byte-for-byte drift gate.
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
explicitly provisional. Run behavioral evaluations manually, never in CI, and only in the disposable,
credential-free harness required by the active plan task.

Every result distinguishes `[verified]`, `[sourced]`, and `[unverified]` claims. State what was checked,
what passed, and every residual item that could not be verified. Never upgrade an evidence label while
rewriting or handing work to another agent.

## Promotion

Promotion to `release` is **blocked** until the promotion controls land: a default-rule CODEOWNERS, the
protected exact-SHA promotion workflow with a named maintainer plus a distinct release operator, and
the live GitHub rules/environment/App configuration. Until then: never merge a PR into, push directly
to, reset, force-push, or directly revert `release`, and never promote a feature or canary ref. The full
control design (promotion steps, ownership boundary, rename/skew rules) is preserved in git history at
tag `pre-cleanup-2026-07-15`.

The repository-side canary harness is [`.github/workflows/validate-canary.yml`](.github/workflows/validate-canary.yml).
After that workflow reaches protected `main`, dispatch it from `main` with a full candidate SHA and the
matching immutable `canary/<phase>/<full-sha>` ref. Its three-OS Gate A result is structural canary
evidence, not behavioral runtime evidence and not release authorization. It runs candidate-controlled
code only on ephemeral hosted runners with read-only repository authority, no persisted checkout
credential, and no protected environment or secrets; a fresh trusted job rechecks the canary ref and
writes the evidence artifact.
