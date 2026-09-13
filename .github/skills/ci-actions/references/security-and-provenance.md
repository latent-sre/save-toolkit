# CI security and provenance

Read this reference only when the task designs or changes credential/OIDC handling, action/image
provenance and version updates, event trust, workflow linting, attestations, or immutable releases. The
authority and safety contract in `SKILL.md` still applies.

## Credentials and identity

`SKILL.md` owns the environment-secrets-not-OIDC default *[sourced: operator statement
2026-08-21]*. Scope each secret to a protected environment so the approval gate and credential
release are the same control. Rotate long-lived credentials on a schedule and after a runner
rebuild; their blast radius lasts until rotation.

`permissions: { id-token: write }` only permits GitHub to mint a short-lived OIDC token; the target
still needs a broker that accepts and exchanges it. CredHub authenticates via UAA and does not
accept GitHub OIDC JWTs, so do not add `id-token: write` as decorative hardening. For a GCP target,
load `stack-profile` and confirm the selected runtime and identity broker before proposing an
exchange.

## Action versions

Use published major tags for GitHub Actions. Verify the tag exists before changing a reference;
if upstream publishes only release tags, use a published release tag and document the exception.
For example, setup-uv publishes `v10.0.1` but no `v10` tag (verified 2026-09-10).
Major tags receive upstream updates without a repository edit; review changes to the selected
major and investigate new failures against the version resolved in the run. Do not label a moving
tag with a fixed release comment. Keep `docker://image@sha256:<manifest-digest>` for image actions;
a Git commit does not identify a registry image.

## Fork checkout under privileged events

`actions/checkout` refuses fork checkout under `pull_request_target`, and under `workflow_run` when
the triggering `workflow_run.event` is a `pull_request*` event. It fails when `repository` resolves
to the fork, when `ref` matches `refs/pull/<n>/head` or `/merge`, or when `ref` resolves to the fork
PR's head or merge SHA.

This shipped in v7.0.0 on 2026-06-18 and was backported to every supported major on 2026-07-16, so
a workflow resolving to v5 or v6 enforces it too. On a floating major tag such as `@v5` the tag is
mutable, so unchanged YAML can resolve to newly backported code: read a new failure there as the
protection engaging rather than hunting for a regression in your own YAML. The
opt-out input `allow-unsafe-pr-checkout: true` exists; treat finding one in a diff, or an upgrade
failure that tempts you to add one, as an unsafe design to review, not a fix to reach for.
*[sourced: GitHub Changelog, ["Safer pull_request_target defaults for GitHub Actions
checkout"](https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout/),
and actions/checkout CHANGELOG v7.0.0; reviewed 2026-08-25]*

## Static security checks

Use the repository's trusted, pinned installation of `actionlint` for workflow syntax and
expression errors and `zizmor` for risky permissions, injection, and event patterns. Do not
download or execute a candidate-provided linter or workflow merely to review it. A clean static
result does not establish runtime or deployment behavior.

## Artifact attestations and immutable releases

For releasable artifacts, use major-tagged `actions/attest-build-provenance` and `actions/attest-sbom`
steps, then verify the result downstream with `gh attestation verify`. The attestation connects an
artifact to its source and workflow; it does not replace review of the workflow that produced it.

Build a release as a draft, attach and check every asset, then publish: with immutable releases on,
a bad release requires a new one. The `production-change-gate` skill owns the immutable-release
evidence contract and the API reads that prove it.
