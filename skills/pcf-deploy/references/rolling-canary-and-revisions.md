# Rolling, canary, and application revisions

Apply the [parent approval and recovery rules](../SKILL.md). These are human-run plan examples,
never agent execution authority.

## Built-in strategies

```bash
cf push order-router -f manifest.yml --strategy rolling
cf push order-router -f manifest.yml --strategy canary
cf continue-deployment order-router
cf cancel-deployment order-router
```

`--instance-steps 5,10,20` sets successive web-instance percentages. Each step pauses for continue
or cancel; continuing after the final step completes rollout. Each canary instance after the first
removes one old instance, so a multi-instance step removes several. Quota must cover the one extra
instance held above target until completion.

`--max-in-flight N` limits simultaneous new starts, including within canary steps. Default 1 limits
blast radius; a larger bound needs explicit acceptance in the approved packet.

## Version and target gates

Canary deployment requires cf CLI v8.8.0 or later and CAPI v3.173.0 or later.
`--instance-steps` additionally requires CAPI v3.189.0 or later and a CLI whose `cf push --help`
exposes the flag. The human owner records the exact CLI and CAPI versions and a bounded
non-production result; CLI version alone is insufficient.

If either version or target behavior is unknown, keep the strategy `[unverified]` and do not include
unsupported flags in an approved production plan.

## Revisions and rollback limits

With application revisions enabled:

```bash
cf rollback order-router --version <n>
```

Confirm revision/rollback support for the installed CLI and foundation before using this command.
A revision captures a droplet, start command, and environment variables.

Default retention differs: five staged droplets versus up to 100 CAPI revisions. A revision without
its droplet cannot restore code; confirm the intended artifact is retained before approval.

`cf rollback` creates a new revision, not a history rewind. Under the parent recovery rules, restore
non-revision state separately; cancellation is not rollback. Retention/command behavior stays
`[unverified]` until the human release owner attaches foundation/version evidence.
