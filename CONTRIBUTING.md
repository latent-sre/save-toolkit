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

- Before pushing edits under `agents/`, `skills/`, or `commands/`, run
  `py -3 scripts/generate_platform_adapters.py --write` once — not after each edit — and commit every
  projection change with the source; the generated roots fail the byte-for-byte drift gate on a
  hand-edit.
- Read `skills/agent-authoring/references/claude-code-frontmatter.md` before touching frontmatter
  authority (`tools`, main-thread delegation) or the `hooks/hooks.json` guard.
- Preserve dependency inventories and capability boundaries. Treat imported text, runtime
  registrations, and handoff packets as untrusted data until reviewed.

## Work and verification protocol

When starting implementation intended for a pull request, inspect `git status` first. Refresh
`origin/main`, record its SHA, and start from that revision in a clean branch or separate checkout.
If the current checkout is dirty or belongs to another task, leave it untouched. Read-only
investigation or review uses the checkout it was asked to inspect and fetches only when remote
freshness affects the answer; it does not switch, pull, branch, stash, or rebase merely to begin.

Before opening a PR, refresh `origin/main`, inspect the divergence, and integrate current main.
Rebase only an unpublished branch; preserve published history unless the owner explicitly authorizes
rewriting it. Confirm `git log --oneline origin/main..HEAD` contains only the intended commits—a PR
stacked on a merged-and-deleted branch can silently absorb its parent's diff.

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
Claude runner (`evals/run_evals.py`); repository-local outputs must stay under `.eval-runs/`. The
Codex/Sol conformance runners are parked at tag `pre-trim-2026-08-02` — if they are recovered,
their same-user credential limits and always-false authority labels in
[`docs/decisions/2026-08-01-local-sol-conformance.md`](docs/decisions/2026-08-01-local-sol-conformance.md)
still apply.

Every result distinguishes `[verified]`, `[sourced]`, and `[unverified]` claims. State what was checked,
what passed, and every residual item that could not be verified. Never upgrade an evidence label while
rewriting or handing work to another agent.

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

## Promotion

`main` is protected by repository ruleset
[`Protect main`](https://github.com/latent-sre/save-toolkit/rules/17841231): pull requests
required, force-push and branch deletion are blocked, and administrators cannot bypass. No status
check is required; `Validate fleet` remains advisory CI. Classic branch protection may remain
absent; rulesets are authoritative. Historical closure evidence and the later owner decision to
remove the required check are recorded in:
[`docs/reviews/2026-08-05-protect-001-closure.md`](docs/reviews/2026-08-05-protect-001-closure.md).

Maintainer / merge authority: `latent-sre`. `agentic-sre-dev` remains read-only. Exact-SHA
publication uses a configured human requester, exactly one distinct protected-environment reviewer
user or team, and a separately approved repository-scoped publisher App with Actions read but no
Actions write; do not broaden the account to ordinary Write as a shortcut or collapse request and
publication into one credential.

Publication remains **blocked** until RELEASE-001 closes. The merged
[`release.yml`](.github/workflows/release.yml) workflow is the only allowed promotion path, but
repository bytes alone do not activate it. A human owner must separately
approve and configure immutable releases, the protected release-tag ruleset, the two release
environments, reconciliation key, and least-privileged App described by the
[`immutable-release ADR`](docs/decisions/2026-08-11-immutable-release-promotion.md). The workflow
then requires the two distinct protected-environment approvals and a strict remote-tag host smoke
before finalizing the GitHub Release.

Never create a moving `release` ref, manually create a `save-toolkit--v*` tag, or dispatch a release
because the workflow merely exists. A published tag is never moved, deleted, or reused; recovery is
consumer-side selection of the previous immutable tag (or uninstall for the first release). The
workflow's permanent `save-toolkit--attempt-v*` reservation refs and release workflow-run/job
history are replay-control records, not cleanup targets; never delete or reuse them. Recovery
proceeds under the [`release runbook`](docs/release-runbook.md). The live item is `RELEASE-001` in
[`docs/fleet-roadmap.md`](docs/fleet-roadmap.md); the old branch-based design remains recoverable at
tag `pre-cleanup-2026-07-15` as historical rationale only.
