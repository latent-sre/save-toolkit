# PCF deployment job

Read this reference only when the task requires a PCF deployment job, cf authentication,
deployment verification, or rollback. Load `stack-profile` first for runner placement,
infrastructure, runtime, or identity recommendations. The authority and safety contract in
`SKILL.md` still applies.

## Preconditions and design

- A self-hosted runner in an approved runner group with network access to the foundation, and a
  pinned cf CLI v8 installation from an approved, checksum-verified source.
- A protected GitHub environment with required reviewers and environment-scoped credentials for a
  least-privilege PCF service account. There is no GitHub-OIDC-to-CredHub exchange.
- The exact artifact produced by the trusted build job, downloaded, never rebuilt.
- Shell tracing off. `cf auth` with no arguments reads `CF_USERNAME` and `CF_PASSWORD` from the
  environment; never put them in argv. *[sourced: cf CLI `command/v7/auth_command.go` help text]*
- A reviewed manifest, health check, rollback job or commands, release-readiness evidence, and
  current human approval naming the exact artifact, target, action, verification, and rollback.
  This skill does not load, run, or approve either gate.
- Stable deployment concurrency with `cancel-in-progress: false`; a newer commit never interrupts a
  production deployment.

## Planning skeleton

Pin every `uses:` to a reviewed full commit SHA before committing this example.

```yaml
deploy-prod:
  runs-on: [self-hosted, pcf]          # runner group with foundation network access
  environment: production               # required reviewers approve before this runs
  concurrency: { group: deploy-prod, cancel-in-progress: false }   # never cancel a deploy
  steps:
    - uses: actions/checkout@<pin-to-sha>
    - uses: actions/download-artifact@<pin-to-sha>   # promote the SAME artifact built earlier
      with: { name: app-build }
    - name: Verify cf CLI v8
      run: |
        cf version
    - name: Deploy
      env:                              # from environment secrets — not echoed, not in ps
        CF_API: ${{ secrets.CF_API }}
        CF_USERNAME: ${{ secrets.CF_USERNAME }}
        CF_PASSWORD: ${{ secrets.CF_PASSWORD }}   # fed to cf auth via env, never argv
        CF_ORG: ${{ vars.CF_ORG }}
        CF_SPACE: ${{ vars.CF_SPACE }}
      run: |
        cf api "$CF_API"
        cf auth
        cf target -o "$CF_ORG" -s "$CF_SPACE"
        cf push -f manifest.yml --strategy rolling
```

Deployment execution belongs to the human release owner. This file is a planning artifact; running
it against a foundation requires the approved-change packet named in `SKILL.md`.

## Verification and rollback handoff

The authored job must name the post-deploy health checks and the rollback action. Static validation
cannot prove foundation reachability, credential validity, application health, or rollback success;
keep those `[unverified]` until the human-approved run produces evidence. Report the workflow and
artifact SHA, PCF API/org/space identifiers without credentials, environment, runner group,
manifest, verification commands, rollback commands, and the approval still required.
