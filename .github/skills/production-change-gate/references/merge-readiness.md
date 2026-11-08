# Merge readiness

Use the [parent verdict](../SKILL.md#verdict); later gates consume it without re-running it.
`HEAD` is the PR head commit, never the local checkout. Any NO blocks. P0/P1 cannot be waived;
other waivers require a recorded human decision.

| Item | Passes when |
|---|---|
| CI | Build, lint and full suite are green in trusted CI at the exact PR head, read from the CI record. Assertions alone are `[unverified]` and a NO. |
| Behaviour tested | Changed behaviour has a regression failing without the change, run at `HEAD`; stale evidence re-runs. |
| Findings disposed | Every current P0/P1 finding, security included, is fixed or rejected with evidence; no credentials, tokens or keys in code, fixtures, artifacts or logs; ordinary merges need no independent re-review per push. |
| Compatible | Migration, API and UI-state contract changes use expand-then-contract. Web GUI changes check keyboard/WCAG behaviour or record a waiver. |
| Scoped | Split only when size or mixed concerns prevent reliable review. |
| Docs and ops | Changed behaviour updates docs: `scribe` for runbooks/postmortems, `observability-engineer` for dashboards/alerts/SLOs, or a recorded reason neither is needed. |

P2 blocks only if introduced or worsened; P3 never blocks. Read active repository rules
(`gh api repos/{owner}/{repo}/rules/branches/{branch}`) and classic protection
(`gh api repos/{owner}/{repo}/branches/{branch}/protection`). A 404 without admin rights means unknown,
not unprotected. The rules endpoint omits `evaluate` and `disabled` rules and bypass actors; classic
`enforce_admins` decides whether admins bypass classic protection. Record enforced approvals; do
not claim independent review is enforced without that evidence. Exact-commit independent review belongs to production deployment, not every merge.
