# Merge readiness

Record the PR, target branch and reviewed PR head in the [merge verdict](../SKILL.md#verdict).
Determine required checks from active branch protections and repository policy for this change.
An unmet or unverified requirement blocks. P0/P1 findings cannot be waived. Other waivers need
a recorded decision from an authorized human and must be permitted by the applicable policy.

| Item | Passes when |
|---|---|
| Required checks | Each required hosted check has a successful trusted run for the current PR head or the integration revision the provider associates with that head and target base. Record the check, tested revision and result. Where policy assigns checks locally, attach a trusted receipt identifying the tested content, scope and result. A local pass cannot satisfy a required hosted check. |
| Behaviour tested | The checks cover the changed behaviour and its material failure cases. For a bug fix, show the regression distinguishes the broken and fixed behaviour. Recheck affected evidence when the head, base or relevant inputs change. |
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
