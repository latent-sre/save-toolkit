# Configuration and scaling

Last checked against `cloudfoundry/cli@v8.18.4` and current Cloud Foundry developer documentation.
Every command remains human-executed and `[unverified]` for the target until version/foundation
evidence is attached.

## Restart or restage

- Restart when a changed environment value is consumed only by the running application. Restart
  creates new containers from the existing droplet.
- Restage when the buildpack/staging process consumes the value, because staging produces the droplet.
- If consumption is unknown, inspect buildpack/application behavior and test outside production; do
  not turn either choice into a universal rule.

```bash
cf set-env checkout KEY value
cf restart checkout

cf set-env checkout JBP_CONFIG_X value
cf restage checkout
```

Source: [Start, restart, and restage](https://docs.cloudfoundry.org/devguide/deploy-apps/start-restart-restage.html).

## Scale behavior

`[sourced]` In CLI v8.18.4, changing only instance count does not take the CLI's explicit restart
path. Changing disk, memory, or log-rate applies the scale and stop/starts the app. That is not a
rolling deployment.

```bash
cf scale checkout -i 5
cf scale checkout -m 2G -k 2G
```

Record capacity limits, quota, startup/health time, traffic behavior, and rollback. Scaling can stop an
incident symptom without proving root cause.

Implementation: `cloudfoundry/cli@v8.18.4 command/v7/scale_command.go`.

## Credentials and sensitive reads

`[sourced]` CLI v8.18.4 supports `CF_USERNAME` and `CF_PASSWORD` for `cf auth`; positional
credentials override them. Keep shell tracing off and do not place credentials on argv. This does not
prove an equivalent environment mechanism for SSO origin/assertion flows.

`cf env`, service-key output, access tokens, and credential-store reads can expose secrets. A human
runs them and shares only the sanitized evidence needed by the plan.
