# Manifest and blue-green deployment

Read this reference only when the plan creates or changes a manifest, uses parallel blue-green
apps/routes, or needs stable-name rotation and route rollback. The authority, approval, rollback,
and evidence rules in `SKILL.md` still apply.

## Declarative manifest

Keep the application manifest in version control and review its exact diff:

```yaml
applications:
  - name: checkout
    instances: 3
    memory: 1G
    buildpacks: [java_buildpack_offline]
    routes:
      - route: checkout.apps.example.com
    env:
      SPRING_PROFILES_ACTIVE: prod
```

Keep secrets out of the manifest; use approved service bindings or the foundation credential
service. Manifest and binding behavior on the exact foundation remain `[unverified]` until captured
there. If a project-owned manifest exists, adapt it narrowly. The bundled manifest asset is only for
a new manifest when the repository has no owned manifest or starter.

## Classic blue-green plan

The live app keeps the stable name (`checkout`); green is always disposable. Rotate names after the
soak so every run begins with the live app at the stable name.

```bash
cf push checkout-green -f manifest.yml --no-route
cf map-route checkout-green apps.example.com --hostname checkout-test
# smoke-test green on the test route
cf map-route checkout-green apps.example.com --hostname checkout
cf unmap-route checkout apps.example.com --hostname checkout
# soak; rollback here re-maps checkout and unmaps green
cf unmap-route checkout-green apps.example.com --hostname checkout-test
cf delete checkout -f
cf rename checkout-green checkout
```

The human release owner runs only commands named in the approved packet. Before the production map,
verify the candidate on its test route. During the shared-route transition, confirm traffic and
telemetry before unmapping the old app. Keep the old app running through the soak.

Stable-name rotation is load-bearing. Without it, the next run can push onto the app already serving
production. `--no-route` does not unbind routes an app already holds.
*[sourced: docs.cloudfoundry.org/devguide/deploy-apps/manifest-attributes.html]*

## Manifest-name interaction

The example manifest pins `name: checkout`, while the playbook pushes `checkout-green`. The v7+ CLI
applies the app-name argument before the rest of the manifest: if that name is absent and the
manifest contains exactly one application, the CLI renames the stanza to the argument and proceeds;
if it contains multiple applications, it fails with `AppNotInManifestError`. Check that the approved
manifest has one stanza before using this command; no separate `manifest-green.yml` is needed for
that single-app case. *[sourced: `cloudfoundry/cli`
`actor/v7pushaction/handle_app_name_override.go` at `fcb3492`; reviewed 2026-08-21 —
`[unverified]` on the deployed CLI/foundation until the human release owner runs it on a bounded
non-production target and attaches the output]*

## Rollback boundaries by phase

- Before the production route is mapped: delete or leave the isolated green candidate; live traffic
  is unchanged.
- While both apps share the route: unmap green and verify traffic remains on the stable app.
- After the stable app is unmapped but before it is deleted: re-map the stable app, verify, then
  unmap green.
- After the stable app is deleted or green is renamed: route remapping is no longer enough. Recovery
  requires a fresh push of the previous artifact and restoration of every non-revision setting.

None of these phases reverses data/schema changes or external effects. Name those separately in the
handoff.
