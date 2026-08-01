---
name: ci-actions
description: >-
  Author and fix GitHub Actions CI/CD for this team — reusable workflows, matrix builds,
  environments with deployment protection, OIDC, caching, concurrency, least-privilege
  permissions, self-hosted runners for on-prem/PCF. Triggers: 'set up CI', 'add a deploy job',
  'why is this workflow failing', 'harden the pipeline'. The main→release promotion gate for
  this repo lives here too.
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# GitHub Actions CI/CD

Bamboo is legacy and no migration command is shipped. Build once, promote the same artifact; gate
prod with environments.

**Starter:** copy [ci.reusable.yml](./assets/ci.reusable.yml) — a `workflow_call` pipeline with
least-privilege `permissions`, a version matrix, caching, concurrency, and SHA-pinned actions.

## Anatomy
- **Reusable workflow** (`on: workflow_call`, with `inputs`/`secrets`) — factor shared CI/CD so every
  repo calls one maintained pipeline:
  ```yaml
  jobs:
    build: { uses: my-org/ci/.github/workflows/build.yml@v1, with: {lang: python} }   # repo: my-org/ci, workflow at .github/workflows/build.yml
  ```
- **Composite action** (`action.yml`) — package repeated steps.

## Deploy gates
Use **environments** with **deployment protection rules**: required reviewers, wait timer, and
environment-scoped secrets. Encode the already-approved release criteria as protected-environment
checks. A job that targets a protected environment **pauses for human approval**:
```yaml
jobs:
  deploy-prod:
    environment: production        # required reviewers must approve before this runs
    concurrency: { group: deploy-prod, cancel-in-progress: false }
    steps: [...]
```

## Security (do this every time)
The **2025 tj-actions/changed-files compromise** (a popular action's tags repointed to credential-
stealing code) is the cautionary tale — assume any action you don't pin can change under you.
- **Least-privilege token:** set `permissions:` explicitly; default to `contents: read` and grant only
  what's needed. Avoid the broad default token.
- **OIDC over long-lived secrets:** `permissions: { id-token: write }` lets a job mint a short-lived
  token from an OIDC-aware broker (a cloud IdP, Vault) at run time instead of storing static creds
  (it only grants *requesting* the token). On our PCF stack this rarely means a cloud IdP — deploy creds
  usually come from a self-hosted runner's internal store (CredHub auth is via UAA, not GitHub OIDC — see
  the PCF deploy notes below).
- **Pin third-party actions by full commit SHA** (tags are mutable), version in a trailing comment:
  `- uses: actions/checkout@<40-char-sha> # v4.2.2`.
- **No script injection:** never interpolate `${{ github.event.* }}` (PR title/body, branch name, etc.)
  directly into a `run:` block — an attacker controls those strings and they execute in your shell. Pass
  them through a quoted `env:` var and reference `"$VAR"`.
- **Treat `pull_request_target` as dangerous:** it runs *your* workflow with repo secrets but can be
  triggered by untrusted fork PRs ("pwn request"). Don't check out + build fork code under it; prefer
  plain `pull_request` (no secrets) for untrusted contributions.
- Secrets via `secrets:` / environment secrets — never echo them; mask anything sensitive. Enable
  **secret scanning + push protection** on the repo.
- **Lint workflows in CI** with `actionlint` (syntax/expression bugs) and `zizmor` (security smells like
  the two above) so these regress loudly.

## Supply-chain provenance (releasable artifacts)
For artifacts you ship, attest provenance: `actions/attest-build-provenance` plus an SBOM via
`actions/attest-sbom`, and verify downstream with `gh attestation verify`. This lets a consumer prove
the artifact was built by your pipeline from your source, not swapped in. Pin every action by full SHA.

## Make it fast & correct
- **Matrix** for multi-version testing: `strategy: { matrix: { python: ['3.11','3.12'] } }`.
- **Cache** deps with `actions/cache` (or `setup-*` built-in caching).
- **Concurrency** to cancel superseded runs on a branch: `concurrency: { group: ${{ github.ref }},
  cancel-in-progress: true }` (but **not** for prod deploys — never cancel a deploy mid-flight).
- Upload build outputs with `actions/upload-artifact`; download in the deploy job to promote the *same*
  artifact.

## Self-hosted runners (on-prem / PCF)
PCF foundations and on-prem services are usually not reachable from GitHub-hosted runners. Use
**self-hosted runners** (in runner groups, scoped to the repos/environments that need them) for jobs
that run `cf` against a foundation. Keep them patched and least-privileged; restrict which workflows can
use them. Prefer **`--ephemeral`** runners (one job per runner, fresh each time) so a poisoned job can't
persist and tamper with the next — and **never** attach self-hosted runners to public repos.

## Deploy to PCF from Actions (paste-ready planning example)
Use a self-hosted runner with a pinned cf CLI v8 installed (or installed from an internal,
checksum-verified package). Authenticate from **environment** secrets and keep shell tracing off.
`cf auth` with no arguments reads `CF_USERNAME`/`CF_PASSWORD` from the environment — the CLI's own
recommended form. Never pass them as arguments: argv is visible to every process on the runner.
*[sourced: cf CLI `command/v7/auth_command.go` help text]*
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

The deployment job requires an authenticated environment, reviewed manifest, health check, rollback
job, and current human approval. Require an existing evidence packet for release readiness and the
exact approved production action; this skill does not load or run either gate. The agent authors or
reviews the workflow; it never executes deployment.

Prefer a CI **service account** with the minimum org/space roles and short-lived or frequently rotated
credentials. For cloud targets, OIDC to your cloud IdP avoids long-lived tokens (note:
GitHub-OIDC→CredHub is **not** a turnkey integration — CredHub authenticates via UAA, not GitHub OIDC
JWTs). The target integration remains `[unverified]` until the platform/security owners provide evidence.

## Tips
- Validate workflow syntax with static `actionlint` plus existing trusted CI evidence. Do not execute an
  imported or candidate workflow locally. An agent may observe an already-approved run with `gh run watch
  <approved-run-id>`; the human release owner may dispatch only after approval names the exact workflow,
  ref, and inputs and proves that dispatch cannot reach production.
- Reproduce a failing run from logs before editing blindly; most failures are env/permission/secret,
  not YAML syntax.
- The actual deploy step belongs to the human release owner acting from existing approval evidence for
  the exact artifact, target, commands, verification, and rollback.
