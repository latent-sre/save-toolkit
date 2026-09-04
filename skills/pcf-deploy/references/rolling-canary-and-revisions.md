# Rolling, canary, and application revisions

Read this reference only when the plan uses rolling/canary deployment, instance steps,
`--max-in-flight`, app revisions, `cf rollback`, or `cf cancel-deployment`. The authority, approval,
rollback, and evidence rules in `SKILL.md` still apply.

## Built-in strategies

```bash
cf push checkout -f manifest.yml --strategy rolling
cf push checkout -f manifest.yml --strategy canary
cf continue-deployment checkout
cf cancel-deployment checkout
```

A canary can advance through `--instance-steps 5,10,20`, where values are successive percentages of
the web process instances. Deployment pauses at each step for `cf continue-deployment` or
`cf cancel-deployment`; continuing after the final step completes the rolling deployment. For each
additional canary instance created after the first, one pre-deployment instance is removed; a step
that adds several canary instances can therefore remove several old instances. The deployment holds
one extra instance above target until completion. Confirm quota for that extra capacity.

`--max-in-flight N` limits how many new instances start simultaneously for rolling and canary work,
including each canary step. The default is 1. Raising it shortens a large rollout but widens the
blast radius; retain 1 unless the approved packet explicitly accepts a larger bound.
*[sourced: Cloud Foundry dev guide, rolling and canary deployments; reviewed 2026-08-21]*

## Version and target gates

Canary deployment requires cf CLI v8.8.0 or later and CAPI v3.173.0 or later.
`--instance-steps` additionally requires CAPI v3.189.0 or later and a CLI whose `cf push --help`
exposes the flag. The human owner records the exact CLI and CAPI versions and a bounded
non-production result; CLI version alone is insufficient. *[sourced: Cloud Foundry deployment
documentation and cf CLI source; reviewed 2026-08-24]*

If either version or target behavior is unknown, keep the strategy `[unverified]` and do not include
unsupported flags in an approved production plan.

## Revisions and rollback limits

With application revisions enabled:

```bash
cf rollback checkout --version <n>
```

Revisions and rollback are GA in cf CLI v8.10.0 and later; older v8 releases label them
experimental. A revision captures a droplet, start command, and environment variables.

The useful rollback window is bounded by staged droplets, not the visible revision count. Cloud
Foundry retains five recent staged droplets while CAPI can retain up to 100 revisions by default; a
revision without its droplet cannot restore the prior code. Confirm that the intended previous
artifact is still available before approval.

`cf rollback` creates a new revision; it does not rewind history. `SKILL.md` owns the rollback truth
and the cancel-is-not-rollback rule: the plan must restore every state outside the revision.

These retention and command behaviors remain `[unverified]` for the target until the human release
owner attaches foundation/version evidence. *[sourced: Cloud Foundry application revisions and cf
CLI deployment documentation]*
