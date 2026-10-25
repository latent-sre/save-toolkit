# WP-08 operator commands

The [approved run plan](run-plan-wp08-swebench-repair.md) owns task selection, model, budget,
execution profile and stop rules. The [implementation plan](implementation-wp08-swebench-repair.md)
maps those requirements to the adapter. The owner starts smoke, the first paid trial, and the
remaining batch separately. Offline tests are not installed-host acceptance.

## Prepare the evaluation host

Use a local Docker engine running Linux containers. The agent network requires Docker's
`--internal` bridge with `com.docker.network.bridge.gateway_mode_ipv4=isolated`: unlike an ordinary
internal bridge, it has no host bridge address. DNS forwarding is disabled in the agent container;
its model endpoint is supplied through an explicit hosts entry. The relay has a fixed destination
and disabled IP forwarding. Host/engine identity and the pinned relay image are part of smoke
evidence. See the [Docker gateway-mode documentation](https://docs.docker.com/engine/network/port-publishing/#gateway-modes).

Install the approved evaluation dependencies in the managed project environment:

```sh
uv pip install --python .venv/bin/python -r requirements-swebench.txt
```

On Windows, use `.venv\Scripts\python.exe`; the target containers and mounted Claude binary are
still Linux. The adapter does not install Docker, change the daemon, provision a machine or pull
images automatically. Keep the native relay image named in `evals/probe/backing.py` locally available.
The optional SWE-bench subset remains separate from CI's normal test dependencies.
The Docker SDK is explicitly pinned as well; offline tests exercise its real API against a local
protocol fixture without requiring a Docker engine.

Download a pinned standalone Linux Claude Code binary on the host. Record its SHA-256 and its full
`--version` output; the smoke also reads that version inside the container. Mounts contain the
binary and frozen plugin only. A CLI wrapper, host subscription directory or credential directory
is not a substitute.

## Freeze the dataset and selection

Choose a full Hugging Face dataset commit. The source is
[SWE-bench/SWE-bench_Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified).
Supply a JSON mapping from repository name to its licence and a source bound to the selected base,
for example `{"owner/repository": "BSD-3-Clause; <licence source at base commit>"}`. Include all
repositories selected by the approved recipe. Missing licence evidence stops selection.

```sh
.venv/bin/python evals/swebench_repair.py select \
  --revision <full-dataset-commit> \
  --licences <licences.json> \
  --dataset .eval-runs/wp08/dataset.json \
  --out docs/fleet-evaluation/wp08-selection.json
```

If the dataset cache is absent, this command fetches that exact revision using the dataset library
installed with SWE-bench. The private cache includes full rows for the independent verifier. An
existing cache must be an object with `dataset`, `revision`, and `rows`; its revision must match.
The public selection contains identifiers, licences, defect labels and hashes, without prompts,
hints, gold patches, test patches or verifier scripts. Review and commit the selection before any
execution. A changed selected row or a population change affecting the seeded draw is refused.

Pull the selected rows' `image` references on the evaluation host, inspect their repository digests
and immutable image IDs, and freeze both. Do not derive image names from instance IDs. Keep each
original row intact in the cache; the verifier receives a separate copy with its image pinned.

## Write the non-secret configuration

The configuration is a JSON object with these fields; every selected instance needs an image entry.
Values in angle brackets are placeholders, not runnable defaults.

```json
{
  "schema_version": 1,
  "plugin_root": "<absolute Git checkout of the candidate>",
  "cli_path": "<absolute path to the pinned Linux Claude binary>",
  "cli_sha256": "<64 lowercase hex characters>",
  "cli_version": "<complete version output>",
  "model": "anthropic/claude-sonnet-5.5",
  "haiku_model": "<explicit approved OpenRouter Haiku model ID>",
  "images": {
    "<selected instance_id>": {
      "reference": "<repository>@sha256:<manifest digest>",
      "image_id": "sha256:<Docker image ID>"
    }
  },
  "proxy_bind": "<host IPv4 reachable by the relay>",
  "proxy_target": "host.docker.internal",
  "storage_quota": false,
  "api_key_helper": false
}
```

On a Linux host, bind the proxy to the local Docker bridge address reachable through
`host.docker.internal`; loopback alone normally is not reachable from that bridge. Docker Desktop
must prove its host route in smoke. No host firewall rules are installed. The proxy requires a random
attempt token and exposes only the Messages route, even on its configured interface.

Set `storage_quota` true only when the engine supports `--storage-opt size=10G`; otherwise the
watchdog measures writable bytes through Docker inspection every minute and stops above 10 GiB
(10,737,418,240 bytes), matching Docker's binary `size=10G` quota.
The exact byte count avoids parsing Docker's rounded human-readable size. The smoke's bounded fill
probe attempts up to 10 GiB plus 100 MiB to demonstrate enforcement; reserve that space on the evaluation host.
CPU is capped at two cores, memory at 2 GiB and processes at 256. The verifier also drops capabilities
and network access; the adapter replaces only SWE-bench's container factory, preserving its grading.

The optional `api_key_helper` setting is the run plan's fallback for a CLI that ignores
`ANTHROPIC_AUTH_TOKEN`; it returns the same placeholder token. Changing it invalidates the smoke
binding. Unknown configuration fields are refused, and no credential belongs in this file.

```sh
.venv/bin/python evals/swebench_repair.py preflight \
  --selection docs/fleet-evaluation/wp08-selection.json \
  --dataset .eval-runs/wp08/dataset.json --config <configuration.json>
```

## Start each approved step

The smoke uses a local model substitute and no real credential. It runs the reference fix and the
unpatched baseline through the independent verifier, then checks guard allow/deny behavior, script
line endings, Git reachability, egress, CPU/storage enforcement and cleanup. Each output directory
must be new; failed evidence is retained.

```sh
.venv/bin/python evals/swebench_repair.py smoke \
  --selection docs/fleet-evaluation/wp08-selection.json \
  --dataset .eval-runs/wp08/dataset.json --config <configuration.json> \
  --out .eval-runs/wp08/smoke-1
```

After reviewing that receipt, the owner creates the campaign-only OpenRouter key with the approved
USD 30 cap and 14-day expiry and selects Anthropic as the first provider in account routing. Store it
as one line in a protected regular file outside the checkout, owner-readable only on POSIX. Never
paste it into a command, trace, configuration, issue or report. The host reads that file only after
checking smoke; the container receives a placeholder.

```sh
.venv/bin/python evals/swebench_repair.py trial \
  --selection docs/fleet-evaluation/wp08-selection.json \
  --dataset .eval-runs/wp08/dataset.json --config <configuration.json> \
  --smoke-receipt .eval-runs/wp08/smoke-1/smoke.json \
  --key-file <protected-host-file> --out .eval-runs/wp08/claude
```

Review the first trace, exact init model, patch, independent verification, cleanup and billed usage.
It counts as the first of the ten trials. A cost above USD 2 stops progression until the owner
re-proposes the run cap; the adapter does not silently waive it. After the owner's separate start:

```sh
.venv/bin/python evals/swebench_repair.py batch \
  --selection docs/fleet-evaluation/wp08-selection.json \
  --dataset .eval-runs/wp08/dataset.json --config <configuration.json> \
  --smoke-receipt .eval-runs/wp08/smoke-1/smoke.json \
  --key-file <protected-host-file> --out .eval-runs/wp08/claude
```

Authentication, identity, budget and unresolved-cleanup failures stop progression; three consecutive
environment failures also stop the batch. An unresolved cleanup marker blocks the next trial until
fresh inspection proves each resource absent. The adapter never removes resources belonging to a
different attempt to make a check pass.

An unknown host-process cleanup also leaves a manual-recovery marker. Use its recorded run ID,
PID, owner PID, command and launch time to investigate the owned process tree; a missing parent PID
alone does not prove its children stopped. Preserve the receipt and record the owner's recovery
evidence before clearing that marker. Windows uses a kill-on-close Job Object established before
the child resumes; its native behavior still needs verification on the selected Windows host.

## Read the evidence

Each attempt lives under `eval-<instance_id>/claude/run-1`. Its v1 record links private trace, patch,
case identity, verifier, billing and cleanup evidence. CLI cost estimates and measured OpenRouter
usage remain separate. Human trace review supplies refusal/policy-deviation and other behavior notes;
the adapter does not infer policy compliance from a successful patch.

The existing comparison reader can retain these trial results, but native scenario threshold pooling
does not support SWE-bench records. Do not invent a native scenario digest to make it pool. Results
from static repair and host-proxy authentication never match subscription or CI-executed profiles.

The owner disables the campaign key and records that disposition after the run. Ten recorded trials,
clean resources, reviewed behavior notes and a disabled key are all required by the run plan; an
offline test pass completes none of those live obligations.
