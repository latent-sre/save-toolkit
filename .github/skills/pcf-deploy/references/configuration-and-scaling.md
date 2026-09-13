# Configuration changes and scaling

Read this reference only when the plan changes environment variables, chooses restart versus
restage, or changes instance, memory, or disk scale. The authority, approval, rollback, and evidence
rules in `SKILL.md` still apply.

## Planning commands

```bash
cf set-env checkout KEY value && cf restart checkout
cf set-env checkout JBP_CONFIG_X value && cf restage checkout
cf scale checkout -i 5
cf scale checkout -m 2G -k 2G
```

These are planning examples, never agent execution authority. The human release owner selects only
the exact approved command and supplies any secret through the approved credential path.

## Restart versus restage

Choose based on who consumes the variable:

- `cf restart` is sufficient when only the application reads the value at process start, such as a
  runtime feature flag or endpoint. An unstaged most-recent package makes restart stage and run
  that package; otherwise it runs the current droplet.
  Confirm existing-droplet reuse and no artifact build before fast-path classification; unknown
  package/droplet state blocks that classification. A restart that stages needs the full release
  and production gates. *[sourced: cloudfoundry/cli `command/v7/restart_command.go`]*
- `cf restage` is required when a buildpack consumes the value during staging because the value
  changes the droplet. Examples include `JBP_CONFIG_*`, `BP_*`, `PIP_INDEX_URL`, and build-time use
  of `NODE_ENV`.

The generic `cf set-env` restage tip is conservative because the CLI cannot know which consumer owns
the variable. Identify the exact application/buildpack consumer before choosing. Treat that
classification as `[unverified]` until repository or buildpack evidence supports it.

`cf env` can display the new value before existing containers receive it; values are injected when
containers start. It is also a human-only credential-bearing read — `pcf-ops` owns that rule.

## Scale effects and rollback

Horizontal scaling changes instance count. Memory or disk changes restart instances and can affect
placement or quota. Record current and proposed values, capacity/quota evidence, expected restart
behavior, health thresholds, and the exact command that restores the prior scale. Revision rollback
does not restore scale, so scale recovery must be a separate step.
