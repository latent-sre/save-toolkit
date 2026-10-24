# Merge readiness

Use the [parent verdict](../SKILL.md#verdict); later gates consume it without re-running it.
`HEAD` is the PR head commit, never the local checkout. Any NO blocks. P0/P1 cannot be waived;
other waivers require a recorded human decision.

| Item | Passes when |
|---|---|
| CI | Build, lint and full suite are green in trusted CI at the exact PR head, read from the CI record. Assertions alone are `[unverified]` and a NO. |
| Behaviour tested | Changed behaviour has a regression failing without the change, run at `HEAD`; stale evidence re-runs. |
| Findings disposed | Every current P0/P1 finding is fixed or rejected with evidence; ordinary merges need no independent re-review per push. |
| Security | Changed auth, input handling, secrets, crypto, file/network access or dependencies have their risks assessed with no P0/P1 open. No credentials, tokens or keys in code, fixtures, artifacts or logs. |
| Compatible | Contract changes use expand-then-contract; check affected migrations, APIs and UI state. Web GUI changes check keyboard/WCAG behaviour or record a waiver. |
| Scoped | Smallest correct change, no dead code/unrelated churn; split only when size or mixed concerns prevent reliable review. |
| Docs and ops | Changed behaviour updates docs: `scribe` for runbooks/postmortems, `observability-engineer` for dashboards/alerts/SLOs, or a recorded reason neither is needed. |

P2 blocks only if introduced or worsened; P3 never blocks. Read active repository rules
(`gh api repos/{owner}/{repo}/rules/branches/{branch}`) and classic protection
(`gh api repos/{owner}/{repo}/branches/{branch}/protection`). A 404 without admin rights means unknown,
not unprotected. Record enforced approvals; do not claim independent review is enforced without
that evidence. Exact-commit independent review belongs to production deployment, not every merge.
