# GitHub Actions security boundaries

Last checked: 2026-08-19. These sources establish GitHub.com's current documented behavior. Verify
GitHub Enterprise Server versions, plan/visibility limits, and repository policy separately.

## Immutable dependencies

`[sourced]` A full commit SHA is the immutable reference for a GitHub Action. Tags and branches can
move. Review automated SHA updates; do not add an arbitrary waiting period that leaves a known
vulnerable pin in service. A `docker://` reference is resolved by a registry and therefore uses an
image manifest digest.

Source: [GitHub secure use reference](https://docs.github.com/en/actions/reference/security/secure-use).

## Untrusted events and expressions

`[sourced]` `pull_request_target` runs base/default-branch workflow code. The dangerous pattern is
explicitly fetching or executing PR-head code, or trusting its artifacts, in that privileged context.
Prefer ordinary `pull_request` for untrusted build/test work. If a privileged metadata workflow is
necessary, do not check out or execute the contribution.

`[sourced]` GitHub substitutes expressions embedded in `run:` before the temporary shell script is
parsed; shell quotes around `${{ github.event.* }}` do not make attacker-controlled text safe. Use a
purpose-built action or an intermediate environment variable quoted by the shell.

Sources: [secure `pull_request_target`](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target)
and [script injection](https://docs.github.com/en/actions/concepts/security/script-injections).

## Tokens, secrets, and OIDC

- Set `permissions:` explicitly. Start with `contents: read` or no permissions and add only the
  capability a job requires.
- `[sourced]` `id-token: write` allows a job to request a GitHub OIDC JWT; it does not grant cloud
  access. The external provider's trust policy performs that exchange. Constrain `aud` and `sub`,
  and verify the actual subject format because current GitHub.com can use immutable repository IDs
  while older/GHES configurations use different claims.
- Environment secrets become available after the protected job passes its environment rules and
  starts. Repository/organization secrets available to another job are outside that environment gate.
- Never put secrets in a prompt, log, artifact, cache key, command argument, or untrusted action.

Source: [GitHub OIDC reference](https://docs.github.com/en/actions/reference/security/oidc).

## Environments and concurrency

`[sourced]` A protected environment can list several users/teams, but one listed required reviewer
approval is sufficient. Prevent-self-review and administrator bypass are separate configurable
settings. Record the actual policy.

Default concurrency allows at most one running and one pending member of a group; ordering is not
guaranteed. `cancel-in-progress: true` cancels a running member—it is not application rollback or
cleanup. Keep it false for production deployment groups unless the release design explicitly proves a
safe cancellation protocol.

Source: [Deployments and environments](https://docs.github.com/en/actions/reference/deployments-and-environments).

## Caches and artifacts

Treat cache and artifact content from untrusted code as untrusted input. Do not restore an untrusted
cache into a privileged job or publish it under a key later consumed by trusted branches. Prefer
immutable artifacts with explicit producer/consumer identities and verify digest, source SHA, and
expected file shape before privileged use.

## Self-hosted runners

`[sourced]` Self-hosted runners are not clean or isolated by default. Ephemeral registration limits
the runner to one job and removes its registration afterward; it does not sanitize the machine.
Public-fork code must not run on a credentialed/internal-network runner. Use a disposable VM/container
boundary or verified reimage/cleanup, scoped runner groups, least-privilege credentials, and outbound
controls.

Source and implementation evidence: [secure use of self-hosted runners](https://docs.github.com/en/actions/reference/security/secure-use)
and `actions/runner@258d6c857db3519913f7deb6004b60172f8043ae`
(`src/Runner.Listener/Runner.cs`, one-job removal path).

## Attestations

`[sourced]` Artifact attestations provide signed provenance/integrity claims about the artifact,
workflow, repository, and commit. They do not prove that the artifact is safe or correct, and they
protect a decision only when a downstream verifier/policy checks them.

Source: [Artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations).
