# PCF deploy-job planning skeleton

Use this only after the main skill's trust and authority checks. Pin every `uses:` entry to a full
commit SHA, verify the runner image/toolchain, and replace placeholders with reviewed values. Define
required `artifact_name` and `artifact_sha256` workflow inputs and bind both values to the reviewed
release and production-change packets.

```yaml
deploy-prod:
  runs-on:
    group: pcf-production      # organization/enterprise runner group restricted outside this file
    labels: pcf-linux          # reviewed Linux + cf CLI capability label inside that group
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
        name: ${{ inputs.artifact_name }}
        path: reviewed-artifact
    - name: Verify expected cf CLI
      shell: bash
      run: |
        set -euo pipefail
        cf version
        sha256sum --version
    - name: Verify reviewed artifact identity
      shell: bash
      env:
        REVIEWED_ARTIFACT_SHA256: ${{ inputs.artifact_sha256 }}
        REVIEWED_ARTIFACT_PATH: reviewed-artifact/app-build.zip
      run: |
        set -euo pipefail
        test -n "$REVIEWED_ARTIFACT_SHA256"
        test -f "$REVIEWED_ARTIFACT_PATH"
        [[ "$REVIEWED_ARTIFACT_SHA256" =~ ^[0-9A-Fa-f]{64}$ ]]
        printf '%s  %s\n' "$REVIEWED_ARTIFACT_SHA256" "$REVIEWED_ARTIFACT_PATH" \
          | sha256sum --check --strict -
    - name: Deploy the reviewed artifact and manifest
      shell: bash
      env:
        CF_API: ${{ secrets.CF_API }}
        CF_USERNAME: ${{ secrets.CF_USERNAME }}
        CF_PASSWORD: ${{ secrets.CF_PASSWORD }}
        CF_ORG: ${{ vars.CF_ORG }}
        CF_SPACE: ${{ vars.CF_SPACE }}
        REVIEWED_ARTIFACT_PATH: reviewed-artifact/app-build.zip
      run: |
        set -euo pipefail
        cf api "$CF_API"
        cf auth
        cf target -o "$CF_ORG" -s "$CF_SPACE"
        cf push -f manifest.yml -p "$REVIEWED_ARTIFACT_PATH" --strategy rolling
```

`[sourced]` CLI v8.18.4 reads `CF_USERNAME` and `CF_PASSWORD` for `cf auth`; this does not prove
support for SSO origin/assertion environment variables. Target CLI/CAPI behavior and rolling support
remain `[unverified]` until the platform owner attaches version and non-production evidence.

`actions/download-artifact` materializes artifact contents under `path`; it does not make those bytes
the `cf push` input automatically. The digest check and explicit `-p` are load-bearing. The approved
artifact must contain exactly one `app-build.zip` in the downloaded root, and the build job—not this
production job—creates that archive and digest.

The environment gate controls this job and its environment secrets. It does not sanitize the
self-hosted runner or protect unrelated repository/organization secrets. The runner must be scoped,
least privileged, and disposable or independently cleaned. A label selects matching runners; it is
not a runner-group boundary. Configure the named group at the organization or enterprise layer to
admit only the intended repository/workflow, then verify that control separately. A human release
owner dispatches only the exact reviewed ref/inputs after release and production-change approval; the
agent never runs it.
