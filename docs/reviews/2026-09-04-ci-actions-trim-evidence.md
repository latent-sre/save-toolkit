# ci-actions trim: before/after evidence (2026-09-04)

The `ci-actions` skill was cut from 22,271 B to 19,307 B in the measured candidate (19,424 B
after the review round added one sentence to the contract and one to the PCF skeleton), its
entrypoint from 8,779 B to 7,710 B (7,782 B after the round), under the 7,800 B screen, and
for the first time it was measured by what the workflow it produces is: the pinned actionlint
accepted every produced workflow and a probe-owned oracle read the deploy job's shape against the
skill's own contract. A tools-off probe of Sonnet and Opus set the cut line; a new
software-engineer build probe graded every trial; incumbent and candidate ran two trials per
model. Measured on the maintainer's Windows host. Cited by the pull request and by `CHANGELOG.md`.

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
| `SKILL.md` | 8,779 B | 7,710 B (7,782 B after the round) |
| `references/security-and-provenance.md` | 5,648 B | 4,227 B |
| `references/execution-and-runners.md` | 2,997 B | 2,634 B |
| `references/pcf-deploy-job.md` | 3,295 B | 3,184 B (3,229 B after the round) |
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
| `deploy-job` | a job runs `cf push`; every per-job case below holds for each such job |
| `runner` | it runs on a runner labelled both `self-hosted` and `pcf`, the only place the foundation is reachable from |
| `environment` | it names the `production` environment |
| `concurrency` | its effective group is stable (a literal, or expressions of the workflow, repository, or job name only) and cancel-in-progress is not true; and the workflow-level concurrency, which cancels the whole run and this job with it, does not cancel the push to main that deploys |
| `permissions` | its effective permissions are an explicit mapping with `contents: read` and no `write` scope at all; the job needs none, and a shortcut is not explicit |
| `pins` | every remote `uses:` in every workflow is a full commit SHA with the release named in a trailing comment; every `docker://` uses a manifest digest |
| `reviewed-pins` | every remote `uses:` SHA is on the pin list as the repository seeded it, so adding a SHA to `docs/ci-pins.md` does not review it |
| `no-injection` | no run step interpolates `${{ github.event.* }}` |
| `artifact-promoted` | it downloads the `checkout-build` artifact and does not run the build script |
| `cf-auth-env` | every `cf auth` has no positional argument, no `cf login` appears, and the step running `cf auth` has `CF_USERNAME` and `CF_PASSWORD` in its effective env mapped from `secrets.*` |
| `cf-target` | `cf api` and `cf target -o ... -s ...` both run before the first `cf push`, so a persistent runner cannot deploy to a stale target |
| `secrets-via-env` | no `${{ secrets.` inside its run steps, no shell tracing, no command that reads `CF_PASSWORD` or dumps the environment; a shell comment naming the variable is not a command |
| `rollback` | the workflow names the explicit `cf rollback` command, in a step, an echo, or a comment, or has a job named for rollback with run steps; the word alone is not a path |
| `build-job-unchanged` | the `build-test` job is exactly what the repository had, except that it may gain the cancelling group the deploy forces out of the workflow |

The fixture is a repository with these conventions stated: a reviewed pin list carrying the real
SHAs of `actions/checkout` v7.0.1, `actions/upload-artifact` v7.0.1, and
`actions/download-artifact` v8.0.1; an `actionlint.yaml` declaring the `pcf` runner label; a
build job that must stay as it is; a `cf` shim that records every invocation; and fake production
credentials in the environment. The prompt states the production facts and the actionlint command
and nothing of the contract.

Proven on this host: 15 of 15 on a hand-written deploy job; 4 of 15 on a naive one (floating
tags, `cf login` with the password in argv, a hosted runner, no environment, no permissions, a
rebuild from source, no rollback); red on the targeted case for each of thirty-seven files built
to dodge one finding (a floating tag, an invented SHA, a SHA the agent appended to the pin list,
a missing or major-alias release comment, an event value in `run:`, no permissions, `id-token:
write`, `actions: write`, `write-all`, a `github.ref` or `github.actor` group,
`cancel-in-progress: true`, no deploy group, a workflow-level cancelling group left in place or
made an expression that still cancels a push to main or one the oracle cannot read, no
environment, a hosted or merely self-hosted runner, a rebuild instead of a download, a second
push job without the artifact, credentials in `cf auth` argv, `cf login`, `cf auth` with no env
mapping, no `cf api` or `cf target`, a secret inside `run:`, `set -x`, an echoed password, a
password assignment, `printenv`, no rollback, the word rollback alone, a changed build timeout, a
dropped build step, a misspelt key, and an unknown key), and green on five positive controls that
guard against a stricter oracle (a workflow-level group whose expression exempts the push to main
two ways, a shell comment naming `CF_PASSWORD`, and the rollback command in a comment and in an
echo). Every dodge file is red only on its targeted case, plus `lint` where actionlint sees the
same thing `[verified: this host]`.

**The review round.** The trials ran on the oracle's first version, thirteen cases. Codex's one
round found eleven ways a wrong workflow could still pass it: `cf auth` with no `env` mapping the
secrets, a write scope other than `id-token`, the word rollback in a comment, `self-hosted` without
the `pcf` label, a rewritten build job that kept two anchor lines, a SHA the agent appends to the
pin list, a second push job without the artifact, an echoed or dumped password, a group varying by
actor or event, no `cf api` or `cf target` on a persistent runner, and a path-qualified `cf` the
attempt regex missed. All eleven are closed above, each proven red on a file built to take it.
Re-scoring the eight produced workflows on the closed oracle then found a hole the round had not
named: two candidate files kept the fixture's workflow-level `cancel-in-progress: true` group and
gave the deploy job a non-cancelling group of its own, which does not protect it, since a
workflow-level cancel cancels the whole run. Three other trials had moved that group onto the
build job, which is the correct change, so `build-job-unchanged` allows that one key. The skill's
PCF skeleton showed a job-level group only; the round added one sentence there and one to the
contract, unmeasured.

One thing the proof found before any trial: actionlint rejects a custom runner label unless the
repository's `.github/actionlint.yaml` declares it, and it does not go looking for that file when
workflow files are named on the command line. The fixture ships the file and the oracle passes it
explicitly.

The probe's other eight checks: only workflows and docs changed; `ci-actions` was loaded; the
agent ran actionlint itself; nothing committed; no `.agents/` litter; the cf shim received no
live-change verb and none was attempted, bare or path-qualified; and the fake credential is not
echoed into the report.

## Provenance

| Item | Value |
|---|---|
| Probe | `evals/build-scenarios/build-software-engineer-adds-pcf-deploy-job.yaml`, 23 checks (10 structural + 13 oracle when the trials ran; 8 + 15 after the round) |
| Incumbent plugin root | worktree at `1842e8cb` (main after #229): ci-actions 22,271 B |
| Candidate plugin root | worktree at `2cfb145c`: ci-actions 19,307 B |
| Committed skill | `2cfb145c` plus the round's two sentences: 19,424 B, not re-measured |
| Committed probe | the trials ran on the thirteen-case oracle at `2cfb145c`; the committed oracle has the fifteen cases above, no live trial ran on those bytes, and every produced workflow is re-scored on them below |
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

### Re-scored on the review-round oracle

Each trial's `workspace.patch` applied to a fresh copy of the fixture and the committed
fifteen-case oracle run on it `[verified: this host]`:

| Arm | Files at 15/15 | The miss |
|---|---|---|
| Opus, incumbent | 2 of 2 | |
| Opus, candidate | 1 of 2 | run 2: the workflow-level cancelling group left in place |
| Sonnet, incumbent | 1 of 2 | run 2: no rollback command, as before |
| Sonnet, candidate | 1 of 2 | run 2: the workflow-level cancelling group left in place |

Five of eight. Every other case the round added, the credentials bound from secrets, no write
scope, both runner labels, the seeded pin list, per-job artifact download, no password reference
or environment dump, a stable group, `cf api` and `cf target` before the push, and the build job
whole, is green on all eight files. Seven of the eight name the exact `cf rollback` command, in
an echo or a comment; none executes one.

## What this says

- **No separation the trim can claim either way.** On the oracle the trials ran, the candidate is
  4 of 4 and the incumbent 3 of 4; on the round's oracle, 2 of 4 against 3 of 4. The two candidate
  misses are the same defect, a workflow-level cancelling group left in place, and nothing in the
  trim bears on it: the cancellation sentence is the same in both bundles, and both trials read
  only the PCF reference, whose skeleton in both bundles showed a job-level group and nothing
  about the workflow's. With two trials per arm the arms differ by one file. What the oracle does
  say is that five of eight produced jobs are complete on fifteen predicates, and that the two
  rules the models hold least are the rollback path and the workflow-level cancel, so those two
  now sit in the skeleton every trial read.
- **No token claim either way.** Opus candidate above incumbent (758K against 687K), Sonnet
  candidate below (533K against 813K), on two trials per arm with single trials from 522K to 984K.
  The bundle read differs by at most 3 KB; the spread is what the agent did.
- **The skeleton is the lever.** Every trial read `pcf-deploy-job.md` and copied its skeleton's
  shape: job-level group, environment, `cf auth` from env, download then push. The two rules the
  models missed are the two the skeleton did not show, the workflow-level group and a rollback
  command. One sentence each is now in the skeleton, unmeasured; the runbook campaign found the
  same thing, that a contract carried as a shape lands where a sentence does not.
- **Machinery:** the oracle is 414 lines of Python inside a 35 KB scenario YAML, which the
  evals Python ceiling does not count (it measures tracked `.py` files only); the runbook and
  alerting oracles sit in the same gap. The review round added two cases, six predicates, and 117
  lines. Recorded, not fixed.
- **Not measured:** the reusable starter asset (no trial needs a new workflow); a failure-diagnosis
  task ("why is this workflow failing"), which is half the skill's triggers; a non-PCF target; the
  routing description, unchanged; more than two trials per arm; the two sentences the round added
  to the skill.

## Verification

`python scripts/gate_a.py` PASS 4/4 on the candidate before the trials; the boundary run and the
suite are recorded in the pull request.
