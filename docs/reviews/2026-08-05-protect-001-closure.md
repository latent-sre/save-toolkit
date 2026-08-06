# PROTECT-001 closure evidence

> **Superseded control (2026-08-06):** The owner removed the required `protection-gate` status
> check and its aggregating workflow job. The `Protect main` ruleset still requires pull requests,
> blocks deletion and non-fast-forward updates, has no bypass actors, and has no required status
> checks. The evidence below records the 2026-08-05 configuration and probe; it is historical, not
> the current required-check policy.

- **Roadmap item:** `PROTECT-001` — protect `main` without CODEOWNERS
- **Closure date:** 2026-08-05 (America/Chicago)
- **Owner decision:** No CODEOWNERS file for this user-owned solo-maintainer repository.
  Historical Task-44 CODEOWNERS designs were superseded for this item.
- **Later policy (2026-08-06):** Live contributor policy no longer forbids adding CODEOWNERS;
  protection remains the `Protect main` ruleset. This closure still records what PROTECT-001 decided.

## Identities

| Role | Identity | Access at closure |
|---|---|---|
| Maintainer / merge authority | `latent-sre` | Admin |
| Promotion / exact-SHA publish | `agentic-sre-dev` | Read-only until RELEASE-001 |

No GitHub App was created in this item. RELEASE-001 may replace `agentic-sre-dev` with a
least-privileged App.

## Merged implementation

[PR #93](https://github.com/latent-sre/save-toolkit/pull/93) added the consolidating
`protection-gate` job to `.github/workflows/validate.yml`, rewrote the live PROTECT-001 acceptance
for the no-CODEOWNERS decision, and updated `CONTRIBUTING.md` Promotion. Merge SHA:
`fc30c06b7458ac9f9f4cce24e79d6e028249a3fe`. The PR's own checks included a green `protection-gate`
context before merge (ruleset not yet requiring it at that moment).

## Live ruleset

Repository ruleset [`17841231` — Protect main](https://github.com/latent-sre/save-toolkit/rules/17841231)
on `~DEFAULT_BRANCH`:

- [verified] `enforcement: active`
- [verified] `bypass_actors: []` (`current_user_can_bypass: never`)
- [verified] rules: `deletion`, `non_fast_forward`, `pull_request` (approving review count `0`,
  `require_code_owner_review: false`), `required_status_checks` with context `protection-gate`
  (strict)
- [verified] immutable source-material rulesets `20191052` and `20191066` left unchanged
- [verified] classic `GET branches/main/protection` remains 404 — rulesets are authoritative

## Probe evidence

Direct push of a probe commit to `refs/heads/main` was rejected [verified]:

```text
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - Changes must be made through a pull request.
remote: - Required status check "protection-gate" is expected.
! [remote rejected] HEAD -> main (push declined due to repository rule violations)
```

`main` remained at `fc30c06`; the probe branch was deleted locally and never landed.

Disabling the Validate fleet workflow would omit the `protection-gate` context, so merges cannot
satisfy the required check — the silent-disable hole that motivated this item.

## Residual

Publication and exact-SHA promotion remain under `RELEASE-001`. Host distribution proof remains
under `HOST-001`.
