# CI security and provenance

Read this reference only when the task designs or changes credential/OIDC handling, action/image
provenance and re-pinning, event trust, workflow linting, attestations, or immutable releases. The
authority and safety contract in `SKILL.md` still applies.

## Credentials and identity

This team authenticates CI jobs from GitHub environment secrets, not OIDC
*[sourced: operator statement 2026-08-21]*. Scope each secret to a protected environment so the
approval gate and credential release are the same control. Rotate long-lived credentials on a
schedule and after a runner rebuild; their blast radius lasts until rotation.

`permissions: { id-token: write }` only permits GitHub to mint a short-lived OIDC token; the target
still needs a broker that accepts and exchanges it. CredHub authenticates via UAA and does not
accept GitHub OIDC JWTs, so GitHub OIDC is not a PCF credential path on this stack. Do not add
`id-token: write` as decorative hardening. For a GCP target, load `stack-profile` and confirm the
selected runtime and identity broker before proposing an exchange.

## Re-pinning

Some projects do not publish floating major tags; the trailing comment names the exact reviewed
release, not an invented major alias. Let dependency automation propose SHA changes, inspect the
upstream diff, and normally allow a short adoption cooldown; skip the cooldown when the current
SHA has a disclosed vulnerability, since waiting would retain the known-bad revision.
`owner/repository@<commit-sha>` resolves a Git commit and `docker://image@sha256:<manifest-digest>`
an image manifest in a registry; a Git commit after `docker://` does not identify an image and the
job will not start.

## Fork checkout under privileged events

`actions/checkout` refuses fork checkout under `pull_request_target`, and under `workflow_run` when
the triggering `workflow_run.event` is a `pull_request*` event. It fails when `repository` resolves
to the fork, when `ref` matches `refs/pull/<n>/head` or `/merge`, or when `ref` resolves to the fork
PR's head or merge SHA.

This shipped in v7.0.0 on 2026-06-18 and was backported to every supported major on 2026-07-16, so
a workflow resolving to v5 or v6 enforces it too. On a floating major tag such as `@v5` the tag is
mutable, so unchanged YAML can resolve to newly backported code: read a new failure there as the
protection engaging rather than hunting for a regression in your own YAML. A full commit SHA pin
cannot change behavior until someone moves it, so there the backport arrives with the re-pin. The
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

For releasable artifacts, use pinned `actions/attest-build-provenance` and `actions/attest-sbom`
steps, then verify the result downstream with `gh attestation verify`. The attestation connects an
artifact to its source and workflow; it does not replace review of the workflow that produced it.

When immutable GitHub Releases are enabled, published assets cannot be modified or deleted and the
tag is locked to its commit while the release exists. Build the release as a draft, attach and check
every asset, then publish. A bad release requires a new release; deleting it does not make the same
tag reusable. Downstream checks should inspect the API's `immutable: true` value, not merely the
existence of a tag. *[sourced: GitHub Docs, immutable releases; reviewed 2026-08-21]*
