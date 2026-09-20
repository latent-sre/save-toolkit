# Security and provenance

Read when changing permissions, credentials, event trust, action versions or release evidence.
Use the repository's established policy; identify a policy change explicitly instead of silently
rewriting it while optimizing CI. The parent skill owns execution authority.

## Permissions and untrusted inputs

Start with explicit read permissions and grant writes to the job that needs them. Inspect both
the automatic token and other credentials: a read-only `GITHUB_TOKEN` does not limit a separate
PAT or cloud credential. Keep untrusted validation separate from privileged delivery.
When later steps need no authenticated Git, use checkout's `persist-credentials: false` so its
credential is not retained for scripts. This reduces exposure; it does not remove the job token
from the Actions runtime or sandbox the code being tested.

Pass PR titles, branch names and other event-derived strings through data inputs or environment
variables, then quote them for the actual shell. Do not interpolate them into `run:` source. Treat
downloaded artifacts and workflow output as untrusted too; validate their identity, format and
paths before a privileged consumer processes them.

Avoid `pull_request_target` unless its privileged context is needed. Neither it nor `workflow_run`
may check out and execute untrusted fork code alongside secrets, write permissions or private
runner access. A preceding low-privilege run does not make its downstream workflow low-privilege.
Do not bypass checkout protections to repair a blocked privileged fork checkout.

## Action and tool versions

For new workflows without an established policy, pin external actions and reusable workflows to
reviewed full commit SHAs from the upstream repository, and `docker://` actions to image manifest
digests. Keep a human-readable release comment beside an immutable pin and use the repository's
update automation to make upgrades reviewable. A SHA is an identity, not a security review.

An existing approved tag policy remains a repository choice. Verify the tag and record its
mutability; do not claim reproducibility from a major tag or attach an exact-release comment to
a moving ref. An upgrade must meet action/runtime compatibility and organization allowlist rules.
Never replace an existing reviewed SHA with a tag as incidental cleanup.

Pin installed tools separately from setup actions. Use locked installs and integrity checks where
supported. A deliberate latest-version compatibility canary is a separate concern from reproducible
release validation; label it and record the resolved versions. Consider package lifecycle scripts
as executable dependencies, disabling them only when the project works without them.

## Identity and deployment controls

For a new cloud target supporting federation, prefer short-lived OIDC credentials over adding a
long-lived secret. Verify issuer, audience and subject restrictions against the exact repository,
ref or environment; `id-token: write` permits minting a token but grants no cloud role by itself.
Existing identity policy and target support govern the choice. For this fleet, read `stack-profile`
before proposing an identity change; its current environment-secret policy remains in force.

When secrets are needed, scope them to the relevant environment/job and avoid broad inheritance
through reusable workflows. Do not print values or put them in argv, caches or artifacts. A
credential available in the environment does not authorize its use for a different target.

Check the repository's plan/visibility and actual environment settings before relying on required
reviewers, branch restrictions, self-review prevention or administrator bypass controls. A job's
environment name alone is not an approval gate. If a required control is unavailable, name the
gap and the existing alternative; do not invent protection or weaken it to make YAML run.

## Verification and supply-chain evidence

Use trusted repository-established `actionlint` and security lint such as `zizmor` when configured.
Static checks do not execute the workflow or prove a credential boundary. Exercise changed
permissions/events with scoped evidence; a negative check should test the actual protection.

For release provenance, bind source commit, workflow/run attempt and artifact digest. Add build
attestations or an SBOM when release policy or a consumer needs them, and verify them at consumption;
creating an attestation without checking it downstream does not protect the consumer. An attestation
does not make an unsafe producing workflow safe. For immutable releases, prepare and verify the
draft and assets before publication; recovery after publication may require a new release.
Production readiness and execution remain with the existing release owner/process.

Sources: [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use),
[checkout inputs](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/action.yml),
[OIDC](https://docs.github.com/en/actions/concepts/security/openid-connect),
[environment controls](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
and [artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations).
