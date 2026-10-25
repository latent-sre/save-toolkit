# WP-09 Terminal-Bench operator run plan

[verified] Preparation is implemented by [harbor_pilot.py](../../evals/harbor_pilot.py) and the
[Harbor adapter](../../evals/harbor_adapter/). The [case review](wp09-terminal-cases.md) and
[frozen manifest](../../evals/manifests/wp09-terminal-complex5.json) define the proposed five-case
selection. This plan does not grant live execution, spending or exact-candidate acceptance.

The owner selects the approved unelevated host and local Linux Docker engine. Preserve the accepted
Windows/Docker Desktop direction where this pilot shares WP-08's host; do not silently switch hosts.
All commands below use the isolated interpreter selected for that host. On POSIX its path ends in
`bin/python`; on Windows it ends in `Scripts/python.exe`.

## Preparation without Docker or models

[verified] Harbor is pinned to [0.24.0](https://pypi.org/project/harbor/0.24.0/), source
`b53b8134e1241686dca7759af188f987ecc48e8b`, Apache-2.0, Python 3.12 or later. The exact wheel SHA-256
is `23b7ba616a3aae4eff561ced5e2c51c7186f2981e53a770dea9c689d3969877c`.
[requirements-harbor.txt](../../requirements-harbor.txt) binds that wheel URL and the observed isolated
SDK dependency set. Do not install or synchronize it into the shared project environment.

```powershell
uv venv --python 3.14 .eval-runs/harbor-sdk
$HarborPython = ".eval-runs/harbor-sdk/Scripts/python.exe"
uv pip install --python $HarborPython -r requirements-harbor.txt
& $HarborPython evals/harbor_pilot.py validate
& $HarborPython evals/harbor_pilot.py sdk-check
& $HarborPython -m pytest -o addopts='' evals/test_harbor_adapter.py evals/test_harbor_runner.py evals/test_harbor_sdk.py evals/test_harbor_smoke.py evals/test_harbor_transfer.py
```

Fetch `https://github.com/harbor-framework/terminal-bench-2.git` into ignored private source storage,
checkout `2fd12b88aafdd04a52c298e3940bcb189f9766d6`, then stage to a new directory:

```powershell
& $HarborPython evals/harbor_pilot.py prepare --source .eval-runs/wp09-terminal-source --output .eval-runs/wp09-terminal-staged
```

[verified] Preparation hashes exact source bytes and copies distinct author and host-only verifier
packets. It executes no benchmark code. Staging never mounts the host-only packet in an author.
The generic `harbor run --agent harbor_adapter.sdk:FleetAgent` path is refused unless the environment
is the adapter's already-owned bounded environment. The factory import path is supported, but a
stock Harbor Docker environment is not a substitute for this profile's isolation.

## Image and host gate

The owner prepares two immutable images per task through the admitted independent actor. Author
images contain only the original Dockerfile's `/app` inputs and the dependencies required for the
frozen native CLI and plugin. Do not copy the whole repository or environment directory: the
compressor's `environment/main.rs` is hidden reference material. No tests, solutions, credentials,
Docker socket, host checkout or writable plugin mount belongs in an author image/container.

Verifier images contain the original task environment and cached dependencies so the **unchanged**
upstream `tests/test.sh` completes with networking disabled. Four scripts request curl, uv 0.9.5,
Python 3.13, pytest 8.4.1 and pytest-json-ctrf 0.3.5; the gRPC script requests pytest 8.4.2,
requests 2.32.5, psutil 7.0.0 and pytest-json-ctrf 0.3.5. The gRPC task additionally needs its requested
grpcio/grpcio-tools 1.73.0 and generated modules. The compressor reference control needs the original
compiler toolchain. Preseed caches/system packages in the reviewed image, preserving task inputs.
Package-download commands remaining in the original scripts do not authorize verifier egress.
A verifier that cannot run offline fails smoke; changing its tests requires a separately identified
adaptation, not a hand-edited passing receipt.

Record real `repository@sha256:...` references plus observed `sha256:...` image IDs. The runner does
not build or pull images. Its config uses the existing WP-08 config contract (including the frozen
Sonnet 5.5 model and explicit Haiku model, native CLI binary hash/version, plugin root, proxy bind,
proxy target and literal `storage_quota: true`). Image keys are `<source-name>-author` and
`<source-name>-verifier`, ten entries for all five cases. Quota support is mandatory; there is no
writable-layer polling fallback. Task storage is 10 GiB, memory 2 GiB, CPU two, PID ceiling 256,
capabilities dropped, no-new-privileges. Artifact collection is capped at 64 MiB, 10,000 regular
files and 60 seconds; symlinks, devices, traversal and Windows-ambiguous names are refused.

## Model-free live smoke gate

[verified] The following command creates disposable Docker resources and deliberately probes their
hard quota. It contacts only a local model substitute through the header-injecting proxy, never a
model provider. It executes the benchmark's reference and tests through the independent actor.
Run it after the owner admits those local effects, once per case with a fresh output directory:

```powershell
& $HarborPython evals/harbor_pilot.py smoke --config .eval-runs/wp09/config.json --source .eval-runs/wp09-terminal-source --case wp09-terminal-static-v1-cancel-async-tasks --output .eval-runs/wp09/smoke/cancel-async-tasks
```

Repeat for the other four exact local case IDs. `observations.json` retains measurements and
`smoke.json` derives checks for reference pass, empty fail, missing reward inconclusive, original
verifier dependencies, CPU/memory/storage caps, egress denial and proxy reachability, exact input
hashes/hidden separation, native CLI version/plugin validation, stopped-author artifact transfer
and readback, and confirmed cleanup. Native plugin validation is model-free CLI validation; each
actual trial separately requires its init/trace to prove the loaded plugin and effective tools.
Do not fill in checks by hand. A failed cleanup blocks reuse until the owner reconciles the named
resources; do not rerun into an unresolved environment.

## Human exact-candidate and paid-run gate

The owner reviews the five packets, generated smoke evidence, source/image receipts, exact plugin
revision/content, CLI, model, host, limits and spend cap. `binding` reads host/Docker/image state but
makes no model calls:

```powershell
& $HarborPython evals/harbor_pilot.py binding --config .eval-runs/wp09/config.json
```

Create the owner-approved admission JSON beside the smoke folders with these fields:

- `format: "wp09-terminal-admission"`, `schema_version: 1`, the exact generated `binding`,
  `accepted: true`, and the real `human_owner` only after that owner's acceptance.
- `case_smoke`, keyed by each local case ID, containing `evidence_path` relative to the admission
  file and `sha256` of the complete corresponding `smoke.json` bytes.

[verified] Admission reopens each digest-bound smoke file and checks its current case/binding,
all derived checks, lack of errors, zero model calls and confirmed cleanup. Changed bytes require
new evidence and acceptance. No automated test or smoke result supplies human acceptance.

Provision/reuse the protected host key only through the accepted credential workflow. The container
receives only an ephemeral proxy token; the real credential stays on the host. The runner requires
provider-observed remaining budget with a positive key cap no greater than USD 30 and records
before/after measured usage separately from the CLI estimate. One writer, concurrency one, one
attempt per selected case, no automatic retries. The task budget is 64 native CLI turns; each case
retains its original 900- or 1,800-second author/verifier wall guard.

```powershell
& $HarborPython evals/harbor_pilot.py run --config .eval-runs/wp09/config.json --admission .eval-runs/wp09/admission.json --key-file .eval-runs/wp09/protected-key --source .eval-runs/wp09-terminal-source --case wp09-terminal-static-v1-cancel-async-tasks --label candidate --output .eval-runs/wp09/trials
```

Review the first complete attempt before the remaining four. Do not overwrite a run directory or
retry a failed case under the same attempt identity. A change in source, image, CLI, plugin, adapter,
model or host invalidates the binding. A `harbor-pending.json` marker blocks reuse after unresolved
cleanup; reconcile its prefix and retained cleanup receipt before any manual disposition.

## Evidence and interpretation

[verified] The host stops every author process before copying `/app` through the bounded regular-file
archive reader into a **fresh**, network-disabled verifier. No author process, home directory or
policy file crosses the handoff. The independent actor executes the authored submission script for
four adapted tasks, then Harbor uploads and executes unchanged hidden tests. The canonical fleet
policy is unchanged; static-authoring compliance still requires human trace review. A correct refusal
to execute task code is policy compliance, not a task failure.

Bundles use `eval-<local-id>/<label>/run-1/record.json` with the published v1 schema. Native Harbor
results and raw reward files remain unchanged. A strict additional mapping admits only finite binary
rewards for this selection; unavailable, malformed, boolean, duplicate or nonfinite rewards are
inconclusive. Cleanup and billing failures preserve a supported independent outcome. The same
manifest is consumable by `campaign_report.build_report`; original task IDs, exact input/image
identity, artifact hashes, model/tool trace, native result, independent verifier receipt, policy review,
cleanup and provider/CLI costs remain separate. Review generated-code relevance and static-policy
compliance before claiming AC-14/25 success. Public-benchmark familiarity remains a limitation.

[unverified] No live host smoke, task-control outcomes, native model trial, spending or human
acceptance has occurred in this preparation. Model-free SDK tests and subprocess controls establish
local integration behavior, not benchmark performance or operation on another host.
