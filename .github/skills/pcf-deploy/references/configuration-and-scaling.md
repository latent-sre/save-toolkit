# Configuration changes and scaling

Apply the [parent approval and recovery rules](../SKILL.md) to environment and scaling plans.

## Planning commands

```bash
cf set-env order-router KEY value && cf restart order-router --strategy rolling
cf set-env order-router JBP_CONFIG_X value && cf restage order-router --strategy rolling
cf scale order-router -i 5
```

Planning examples only: the human release owner runs the exact approved command and supplies
secrets through the approved credential path; agents never execute them.

## Restart versus restage

Choose based on who consumes the variable:

- `cf restart` is sufficient when only the application reads the value at process start, such as a
  runtime feature flag or endpoint. An unstaged most-recent package makes restart stage and run
  that package; otherwise it runs the current droplet.
  Confirm existing-droplet reuse and no artifact build before fast-path classification; unknown
  package/droplet state blocks that classification. A restart that stages needs the full release
  and production gates.
- `cf restage` is required when a buildpack consumes the value during staging because the value
  changes the droplet. Examples include `JBP_CONFIG_*`, `BP_*`, `PIP_INDEX_URL`, and build-time use
  of `NODE_ENV`.

The generic `cf set-env` restage tip cannot identify the variable's consumer; bind that choice to
application/buildpack evidence or leave it `[unverified]`.

`cf env` can display the new value before existing containers receive it; values are injected when
containers start. It is also a human-only credential-bearing read — `pcf-ops` owns that rule.

## Scale effects and rollback

Instance-count scale differs from `cf scale -m/-k/-l`, which stops/starts the whole app. A
no-downtime resize requires a target-supported procedure and confirmed current-droplet reuse;
`pcf-ops` supplies prerequisites, not a generic recipe. `cf push -m/-k` is a new artifact requiring
full release gates. Record old/new values, placement/capacity/quota evidence, restart effects,
health thresholds and the exact scale-back command. Revision rollback does not restore scale:
plan scale recovery separately.
