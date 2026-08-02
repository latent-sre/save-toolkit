# Local Sol conformance for externally reviewed source

- **Date:** 2026-08-01
- **Status:** accepted; runners parked 2026-08-02 at tag `pre-trim-2026-08-02` (beta trim — this
  contract governs any recovered use)
- **Scope:** Codex/Sol skill and custom-agent behavioral evaluation

## Decision

Retain the fixed `gpt-5.6-sol` manifests, deterministic trace/oracle graders, usage limits, sanitized
reports, and typed evidence envelopes. Run them manually against this repository's local checkout
using the operator's existing Codex login in a disposable `CODEX_HOME`. Commit and independently
review the exact revision before a live run; the runner records behavior but cannot verify that
external review.

Retire the GitHub Actions Responses API broker, repository API secret, immutable evaluation-canary
workflow, raw Git object materializer, cross-job report reducer, and their broker-specific tests and
release dependencies.

## Why

The broker attempted to make untrusted candidate evaluation safe while model credentials existed in
the same job. That required a second transport, Linux identity and sudo assumptions, object-only Git
acquisition, a credential-free extraction phase, report reduction on another runner, and repository
promotion controls. The fleet needs behavioral feedback on already reviewed agent and skill source;
it does not currently need to execute hostile pull-request content with model credentials. The
narrower contract removes that control plane while preserving the measurements that inform fleet
quality.

## Enforced contract

- Live runs accept only this repository checkout and the fixed manifests; there is no external
  `--target-root` path.
- Clean plugin, generated-agent, and harness inputs are required by default. Dirty development runs
  set `exact_revision` false and reduce to `inconclusive` evidence. Scoped ignored untracked files
  are treated as dirty because the evaluated snapshot includes them even though ordinary Git status
  hides them. Scoped tracked files carrying `assume-unchanged` or `skip-worktree` index flags are also
  treated as dirty.
- Every report sets `source_review` to `not-verified-by-runner`, `independent_evaluator` to false,
  `baseline_eligible` to false, and `release_granted` to false. Those reserved authority fields
  cannot be overridden by caller-supplied evidence.
- The operator's regular, unlinked, single-link `auth.json` must remain outside the repository. The
  runner copies it into a disposable home only after credential-free plugin bootstrap, requests owner
  read/write mode where supported, and deletes it before returning the report.
- Bootstrap and model output are scanned for credential-shaped material before any output is retained
  or echoed. A match aborts report generation without echoing the value.
- Skill runs disable collaboration. Agent runs retain their one-child depth/concurrency limits.
- Raw JSONL, parsed responses, rollout contents, auth paths, and auth digests never enter reports.
- Reports retain commit/tree identities, input hashes, deterministic verdict facts, bounded usage,
  timeouts, and explicit `local-same-user`, `not-proven`, and `not-verified-by-runner` labels.
- Report files are create-only. Existing files and linked/reparse paths are refused; outputs inside
  the repository must resolve beneath `.eval-runs/`.

## Limitations

Read-only model tools can still read the copied same-user login. This design does not contain hostile
candidate code and does not establish source review, credential isolation, independent evaluation,
baseline acceptance, or release authorization. A clean report proves only that the scoped inputs
matched the recorded revision and that the measured behavior produced the reported verdict. Pair it
with independent review evidence for the exact same commit before accepting a baseline.

Historical 2026-07-31 reports remain revoked because they also persisted parsed model responses;
their files remain unchanged for diagnosis.

## Reopen trigger

Reconsider a broker only when a named workflow must evaluate genuinely untrusted content with model
credentials and has an owner, threat model, independent identity, operational budget, and evidence
that local evaluation plus external exact-revision review cannot satisfy the use case.
