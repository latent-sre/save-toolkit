# GitHub change-control evidence

Last checked: 2026-08-19. These are current GitHub.com contracts, not proof of a repository's live
configuration. A human or protected evidence job runs authenticated reads and attaches sanitized
results; guarded `sre` and `observability-engineer` agents do not run `gh api`.

## Source-review controls

`[sourced]` Classic branch protection and rulesets can both apply. One classic protection rule can
match a branch, while multiple repository and organization rulesets can apply; the aggregate enforced
result is the most restrictive applicable set.

- Classic protection read:

  ```sh
  gh api repos/{owner}/{repo}/branches/{branch}/protection
  ```

- Active branch rules read:

  ```sh
  gh api repos/{owner}/{repo}/rules/branches/{branch}
  ```

A 404 from the classic endpoint is inconclusive: the resource can be inaccessible to the credential,
and active rules use the separate endpoint. Verify repository/token access, then record both results
and applicable organization policy. Do not convert `evaluate` or disabled rules into enforced facts.

Sources: [GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets),
[protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches),
and [REST rules](https://docs.github.com/en/rest/repos/rules).

## Deployment-effect controls

`[sourced]` A protected environment can name multiple users or teams, but one listed required reviewer
approval is sufficient. Preventing self-review is a separate setting. Administrator bypass is allowed
by default and can be disabled. Record the actual configuration instead of saying that every reviewer
must approve or that administrators can always bypass.

Environment protection is evaluated before the job is sent to a runner, and environment secrets become
available only after approval and job start. This does not isolate a self-hosted runner, and it does not
delay organization or repository secrets that the workflow can already access. Review the workflow's
complete permission and secret surface.

Source: [GitHub deployment environments](https://docs.github.com/en/actions/reference/deployments-and-environments).

## Evidence packet

Record:

- repository, branch/ref, exact SHA, and credential identity/scope used for the reads;
- applicable classic protection and active repository/organization rules;
- required checks/reviews and stale-review behavior;
- environment name, reviewer rule, self-review setting, and administrator/custom-app bypass;
- workflow ref and inputs, concurrency behavior, runner trust boundary, and secret sources;
- every missing or inaccessible fact as `[unverified]`.

Branch policy proves source constraints. The environment or external change-control mechanism must
still bind approval to the production effect.
