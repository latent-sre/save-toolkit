# PCF deploy-job planning skeleton

Use this only after the main skill's trust and authority checks. Pin every `uses:` entry to a full
commit SHA, verify the runner image/toolchain, and replace placeholders with reviewed values.

```yaml
deploy-prod:
  runs-on: [self-hosted, pcf]  # scoped runner group with required foundation network access
  environment: production     # configured protection rule passes before this job starts
  concurrency:
    group: deploy-prod
    cancel-in-progress: false
  permissions:
    contents: read
  steps:
    - uses: actions/checkout@<full-commit-sha>
    - uses: actions/download-artifact@<full-commit-sha>
      with:
        name: app-build
    - name: Verify expected cf CLI
      run: cf version
    - name: Deploy the reviewed artifact and manifest
      env:
        CF_API: ${{ secrets.CF_API }}
        CF_USERNAME: ${{ secrets.CF_USERNAME }}
        CF_PASSWORD: ${{ secrets.CF_PASSWORD }}
        CF_ORG: ${{ vars.CF_ORG }}
        CF_SPACE: ${{ vars.CF_SPACE }}
      run: |
        set +x
        cf api "$CF_API"
        cf auth
        cf target -o "$CF_ORG" -s "$CF_SPACE"
        cf push -f manifest.yml --strategy rolling
```

`[sourced]` CLI v8.18.4 reads `CF_USERNAME` and `CF_PASSWORD` for `cf auth`; this does not prove
support for SSO origin/assertion environment variables. Target CLI/CAPI behavior and rolling support
remain `[unverified]` until the platform owner attaches version and non-production evidence.

The environment gate controls this job and its environment secrets. It does not sanitize the
self-hosted runner or protect unrelated repository/organization secrets. The runner must be scoped,
least privileged, and disposable or independently cleaned. A human release owner dispatches only the
exact reviewed ref/inputs after release and production-change approval; the agent never runs it.
