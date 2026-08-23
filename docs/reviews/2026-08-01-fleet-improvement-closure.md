# IMPROVE-001 closure evidence

- **Roadmap item:** `IMPROVE-001` — enforce a bounded fleet-improvement lifecycle
- **Closure date:** 2026-08-01 (America/Chicago)
- **Authority boundary:** encounter-driven, repository-backed, and human/protected-workflow promoted;
  no background self-modification or self-approval

## Merged implementation

- [PR #76](https://github.com/latent-sre/sre-agents/pull/76) merged the bounded lifecycle at merge
  commit `606d788157eccd717251ceb94dbe8530b3c1c73e` from reviewed candidate
  `cf6afe36b37be21c5d92c3b9f9b3d186e15cf44f`.
- PR #76's Copilot review found that first-record corpus replay bypassed the initial authority-shape
  validator. [PR #77](https://github.com/latent-sre/sre-agents/pull/77) added the focused regression
  and fix, then merged at `f1b084b05b9845d04ea4016489f9d250630f9e1b` from candidate
  `cda947b4355a08faa6b8f230f8a63a61585ef28e`.
- Copilot reviewed all five PR #77 files without a further finding. Codex reviewed the exact PR #77
  candidate and reported no major issue.

## Acceptance disposition

The merged tree contains the typed record schema, executable lifecycle and corpus validators,
evidence-envelope bindings, bounded attempt and caller budgets, caller-supplied transition authority,
real Git ancestry and object checks, rollback verification, cross-record deduplication, the rejected
historical pilot, routing and handoff contracts, focused mutation coverage, and synchronized generated
adapters. Fresh structural verification for this closure is recorded with the change that removes the
item from the live roadmap.

> **Post-closure update (2026-08-02):** PR #79 parked the executable lifecycle and corpus validators
> at tag `pre-trim-2026-08-02` for the beta. This section records the acceptance state at closure; it
> does not claim those executables remain in the current tree. The schema and lifecycle contract
> remain active, and no record may advance beyond `observed` or `rejected` until the validators are
> recovered and independently reviewed.

Codex/Sol behavioral evaluation was not an `IMPROVE-001` acceptance condition. At closure it was
tracked under `EVAL-001` as an operator-run local measurement whose exact-revision report had to be
paired with separate independent review; the runner was not a baseline or release-authorization
mechanism. `EVAL-001` was retired by owner disposition on 2026-08-23, with its historical bytes
preserved at tag `pre-trim-2026-08-02`.
