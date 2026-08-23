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
  runtime feature flag or endpoint. Restart reuses the staged droplet.
- `cf restage` is required when a buildpack consumes the value during staging because the value
  changes the droplet. Examples include `JBP_CONFIG_*`, `BP_*`, `PIP_INDEX_URL`, and build-time use
  of `NODE_ENV`.

The generic `cf set-env` restage tip is conservative because the CLI cannot know which consumer owns
the variable. Identify the exact application/buildpack consumer before choosing. Treat that
classification as `[unverified]` until repository or buildpack evidence supports it.

`cf env` can display the new value before existing containers receive it; values are injected when
containers start. It is also credential-bearing and remains a human-only read. A pasted, sanitized
excerpt may be used as evidence, but the agent never requests or handles raw secret output.

## Scale effects and rollback

Horizontal scaling changes instance count. Memory or disk changes restart instances and can affect
placement or quota. Record current and proposed values, capacity/quota evidence, expected restart
behavior, health thresholds, and the exact command that restores the prior scale. Revision rollback
does not restore scale, so scale recovery must be a separate step.
