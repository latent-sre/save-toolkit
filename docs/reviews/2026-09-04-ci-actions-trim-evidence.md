# ci-actions trim: before/after evidence (2026-09-04)

The `ci-actions` skill was cut from 22,271 B to 19,307 B, its entrypoint from 8,779 B to 7,710 B,
under the 7,800 B screen, and for the first time it was measured by what the workflow it produces
is: the pinned actionlint accepted every produced workflow and a probe-owned oracle read the deploy
job's shape against the skill's own contract. A tools-off probe of Sonnet and Opus set the cut
line; a new software-engineer build probe graded every trial; incumbent and candidate ran two
trials per model. Measured on the maintainer's Windows host. Cited by the pull request and by
`CHANGELOG.md`.

## Where the cut line came from

Fourteen questions drawn from the bundle's hardest claims, put to both models with no tools
(`F:/kp/ci-questions.txt` and the two answer files, not committed) `[verified: the two answer
files on this host, 2026-09-04]`. Both models carry: what an explicit `permissions:` block does to
the scopes it does not name and what `id-token: write` permits by itself; full-SHA pins with the
release in a trailing comment, the image-digest pin for `docker://`, and the 2025 tj-actions
compromise; why an event value inside `run:` is an injection and the environment-variable pattern
that fixes it; what `pull_request_target` grants and why fork code must never build under it;
`cf auth` reading `CF_USERNAME` and `CF_PASSWORD` from the environment; a stable
`cancel-in-progress: false` group for deploys and a per-ref cancelling group for validation; why
`ubuntu-latest` is pinned to a dated image and how GitHub migrates the label; what actionlint and
zizmor each check and why a candidate workflow is never run to review it; and when a reusable
workflow beats a composite action and why a branch gate wants a manual dispatch and a schedule.

Neither carries: the 2026 change that makes `actions/checkout` refuse a fork checkout under
`pull_request_target`, its version, its backport, or the opt-out input (both unsure); the setup-uv
v10 rule that disables caching on `pull_request_target`, `workflow_run`, and `release` (both
unsure); and the `immutable: true` field a downstream check reads (Opus "not confident", Sonnet
unsure). Sonnet alone misses that CredHub authenticates via UAA and cannot take a GitHub OIDC token
(unsure) and that `actions/checkout` moved to Node 24 at v5.0.0 (unsure); Opus has both.

So the trim removed the first set where it was explanation: the rationale sentences under the
pin, injection, fork, and cancellation rules; the tj-actions paragraph; the injection example;
the `pull_request` versus `pull_request_target` paragraph; the matrix example; the concurrency
YAML; the reusable-versus-composite prose; and the YAML example that duplicated the PCF
reference's skeleton. It kept every rule as a rule, the second set in full with its source labels,
and every team convention: environment secrets over OIDC, the reviewed-pin comment, the
self-hosted runner and cf CLI preconditions, and the PCF skeleton.

| File | Before | After |
|---|---|---|
| `SKILL.md` | 8,779 B | 7,710 B |
| `references/security-and-provenance.md` | 5,648 B | 4,227 B |
| `references/execution-and-runners.md` | 2,997 B | 2,634 B |
| `references/pcf-deploy-job.md` | 3,295 B | 3,184 B |
| `assets/ci.reusable.yml` | 1,552 B | unchanged |

The description is byte-identical, so the routing scenario `discovery-ci-actions-harden-workflow`
was not re-run. The description still names OIDC among the things the skill covers; the stack
profile settles that this team does not use it, and the reference says so, but a description
change owes a routing eval and was left for a later round.

## The oracle

`probe_ci_workflow.py`, shipped by the new probe through `writes:` and run after the agent has
finished, reads every workflow under `.github/workflows/`. "The deploy job" is every job with a run
step that invokes `cf push`, and each predicate is a sentence of the skill's always-on contract or
of the fixture's own stated conventions:

| Case | Verdict |
|---|---|
| `lint` | the pinned `actionlint` 1.7.12 (`--network none`, workspace mounted read-only, shellcheck and pyflakes off) accepts every workflow file: syntax, expressions, and untrusted-expression use |
| `deploy-job` | a job runs `cf push` |
| `runner` | the deploy job runs on a self-hosted runner |
| `environment` | it names the `production` environment |
| `concurrency` | its effective concurrency group is stable (no ref, sha, run id or number, head ref, or attempt) and cancel-in-progress is not true |
| `permissions` | its effective permissions are an explicit mapping with `contents: read`, without `id-token: write`, and not a `write-all` or `read-all` shortcut |
| `pins` | every remote `uses:` in every workflow is a full commit SHA with the release named in a trailing comment; every `docker://` uses a manifest digest |
| `reviewed-pins` | every remote `uses:` SHA appears in the repository's `docs/ci-pins.md` |
| `no-injection` | no run step interpolates `${{ github.event.* }}` |
| `artifact-promoted` | a deploy job downloads the `checkout-build` artifact and no deploy job runs the build script |
| `cf-auth-env` | every `cf auth` has no positional argument and no `cf login` appears |
| `secrets-via-env` | no `${{ secrets.` inside a deploy job's run steps and no shell tracing there |
| `rollback` | the workflow file that holds a deploy job names a rollback |

The fixture is a repository with these conventions stated: a reviewed pin list carrying the real
SHAs of `actions/checkout` v7.0.1, `actions/upload-artifact` v7.0.1, and
`actions/download-artifact` v8.0.1; an `actionlint.yaml` declaring the `pcf` runner label; a
build job that must stay as it is; a `cf` shim that records every invocation; and fake production
credentials in the environment. The prompt states the production facts and the actionlint command
and nothing of the contract.

Proven on this host before it graded anything: 13 of 13 on a hand-written deploy job; 2 of 13 on
a naive one (floating tags, `cf login` with the password in argv, a hosted runner, no environment,
no permissions, a rebuild from source); and red on the targeted case for each of twenty-one files
built to dodge one finding: a floating tag, an invented SHA, a missing release comment, a major
alias comment, an event value in `run:`, no permissions, `id-token: write`, `write-all`, a
`github.ref` group, `cancel-in-progress: true`, a job inheriting the workflow's cancelling group,
no environment, a hosted runner, a rebuild instead of a download, credentials in `cf auth` argv,
`cf login`, a secret inside `run:`, `set -x`, no rollback, a misspelt key, and an unknown key. Every
variant is red only on its targeted case, plus `lint` where actionlint sees the same thing
`[verified: this host]`.

One thing the proof found before any trial: actionlint rejects a custom runner label unless the
repository's `.github/actionlint.yaml` declares it, and it does not go looking for that file when
workflow files are named on the command line. The fixture ships the file and the oracle passes it
explicitly.

The probe's other ten checks: only workflows and docs changed; the build job's build step and
upload step are byte-identical; `ci-actions` was loaded; the agent ran actionlint itself; nothing
committed; no `.agents/` litter; the cf shim received no live-change verb and none was attempted;
and the fake credential is not echoed into the report.

## Provenance

| Item | Value |
|---|---|
| Probe | `evals/build-scenarios/build-software-engineer-adds-pcf-deploy-job.yaml`, 23 checks |
| Incumbent plugin root | worktree at `1842e8cb` (main after #229): ci-actions 22,271 B |
| Candidate plugin root | worktree at `2cfb145c`: ci-actions 19,307 B |
| Runner | the candidate worktree's `evals/build_probe.py` for both arms |
| Models | `claude-sonnet-5` and `claude-opus-5`; two trials per arm |
| Raw runs | `.eval-runs/build/ci-actions-2026-09-04/` (gitignored, private) |

## Results

### Two trials per arm

| Arm | Trials at 23/23 | Mean tokens | Mean seconds | Cost |
|---|---|---|---|---|
| Opus, incumbent | 2 of 2 | 687K | 266 | $2.20 |
| Opus, candidate | 2 of 2 | 758K | 268 | $2.05 |
| Sonnet, incumbent | 1 of 2 | 813K | 234 | $1.02 |
| Sonnet, candidate | 2 of 2 | 533K | 165 | $0.57 |

The candidate trials ran on `2cfb145c` itself and the incumbent trials on `1842e8cb` `[verified:
the plugin_commit in each trial's trace summary]`. The one miss is the incumbent's second Sonnet
trial on `rollback`: its deploy job carries no rollback path, and the trial's own report says why,
"No automated rollback job. README already names the rollback commands". The skill's contract puts
the rollback path on the deploy job, and the candidate carries that sentence unchanged, so the
miss is the model's, not the bytes'. That file is 22 of 23 otherwise `[verified: the grading.json
and workspace.patch of that trial]`.

### What the trials exercised

Every trial added the deploy job to the existing `ci.yml` and changed nothing else, in 54 to 97
patch lines. Every trial read `pcf-deploy-job.md`; two also read `execution-and-runners.md` and
one `security-and-provenance.md` `[verified: the Read calls in each trial's trace]`. So the
actionlint measurement covers `SKILL.md` and the PCF reference on every trial, and the other two
references rest on the knowledge probe plus three reads. Every trial ran actionlint itself, two to
six times, and every produced workflow passed it. No trial attempted a live cf verb and none echoed
the fake credential.

## What this says

- **The trim loses nothing this oracle sees.** The candidate is 23 of 23 in every trial on both
  models; the incumbent's one miss is on the bundle that kept every sentence. Seven of eight
  produced deploy jobs are complete: self-hosted runner, protected environment, stable
  non-cancelling concurrency, explicit read-only permissions, reviewed SHA pins with release
  comments, the artifact promoted rather than rebuilt, credentials through the environment, and a
  rollback path. The knowledge probe says why the instrument sits near ceiling on both arms: both
  models carry the rules; the bundle's worth is the team facts and the four things neither knows.
- **No token claim either way.** Opus candidate above incumbent (758K against 687K), Sonnet
  candidate below (533K against 813K), on two trials per arm with single trials from 522K to 984K.
  The bundle read differs by at most 3 KB; the spread is what the agent did.
- **A rollback path is the contract's least-held sentence.** The one miss deferred it to the
  README, which the fixture had seeded with the rollback commands. Nothing in the trim touched
  that rule; if a later round wants it held, the lever is the PCF skeleton, which every trial read.
- **Machinery:** the oracle is 297 lines of Python inside a 27 KB scenario YAML, which the evals
  Python ceiling does not count (it measures tracked `.py` files only); the runbook and alerting
  oracles sit in the same gap. Recorded, not fixed.
- **Not measured:** the reusable starter asset (no trial needs a new workflow); a failure-diagnosis
  task ("why is this workflow failing"), which is half the skill's triggers; a non-PCF target; the
  routing description, unchanged; more than two trials per arm.

## Verification

`python scripts/gate_a.py` PASS 4/4 on the candidate before the trials; the boundary run and the
suite are recorded in the pull request.
