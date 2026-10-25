# Manifest and blue-green deployment

Apply the [parent plan, approval and recovery rules](../SKILL.md). Commands below are for the
human release owner, not agent execution.

## Declarative manifest

Keep the application manifest in version control and review its exact diff:

```yaml
applications:
  - name: order-router
    instances: 3
    memory: 1G
    buildpacks: [java_buildpack_offline]
    routes:
      - route: order-router.apps.example.com
    env:
      SPRING_PROFILES_ACTIVE: prod
```

Use approved bindings/credential service for secrets, never manifest values. Target manifest/binding
behavior stays `[unverified]` until observed. Adapt an existing project manifest narrowly; this
example applies only when the repository has neither manifest nor starter.

## Classic blue-green plan

Before each push, resolve both identities and routes. This sequence requires live `order-router`
and a non-production-serving `order-router-green`; never overwrite a serving candidate. Reconcile
UNKNOWN delete/rename outcomes under the approved recovery plan before restarting. Post-soak name
rotation restores this starting state.

```bash
cf push order-router-green -f manifest.yml --no-route
cf map-route order-router-green apps.example.com --hostname order-router-test
# smoke-test green on the test route
cf map-route order-router-green apps.example.com --hostname order-router
# confirm production traffic and telemetry meet approved criteria before unmapping the old app
cf unmap-route order-router apps.example.com --hostname order-router
# soak; rollback here re-maps order-router and unmaps green
cf unmap-route order-router-green apps.example.com --hostname order-router-test
cf delete order-router -f
cf rename order-router-green order-router
```

The human runs only approved commands. Verify green on the test route before production mapping;
confirm shared-route traffic/telemetry before unmapping the old app, retaining it through soak.

Do not use `--no-route` to prove a reused app is isolated: the
[manifest docs](https://docs.cloudfoundry.org/devguide/deploy-apps/manifest-attributes.html) say existing
routes remain, but the [CLI v8.18.4 tests](https://github.com/cloudfoundry/cli/blob/v8.18.4/integration/v7/push/no_route_test.go#L35)
expect them removed. This source conflict leaves target behavior `[unverified]`; require the parent's
bounded non-production evidence for the exact CLI/CAPI versions.

## Manifest-name interaction

The manifest names `order-router`, but push names `order-router-green`. In CLI v7+, when the requested
app name is absent from the manifest, it overrides a single stanza's name; multiple stanzas cause
`AppNotInManifestError`. Confirm one stanza before using this sequence; no separate green manifest
is needed for that case. The human release owner must attach bounded non-production evidence for
the deployed CLI/foundation before treating this behavior as verified.

## Rollback boundaries by phase

- Before the production route is mapped: delete or leave the isolated green candidate; live traffic
  is unchanged.
- While both apps share the route: unmap green and verify traffic remains on the stable app.
- After the stable app is unmapped but before it is deleted: re-map the stable app, verify, then
  unmap green.
- After the stable app is deleted or green is renamed: route remapping is no longer enough. Recovery
  requires a fresh push of the previous artifact and restoration of every non-revision setting.

No phase reverses data/schema changes or external effects; the parent recovery rules apply.
