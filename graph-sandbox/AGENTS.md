# GRAPH-002 project context

These instructions apply only under `graph-sandbox/`. The root `AGENTS.md`, the accepted GRAPH-002
runtime decision, and the live roadmap remain authoritative.

## Environment card

- **Toolchain**: Python 3.12.10 at `python`; Docker Engine 29.7.2 Linux/amd64; Docker Compose 5.4.0;
  container base `python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4`
  for Linux/amd64.
- **Build**: `python graph-sandbox/activate.py build --docker-context <named-local-context> --source-revision <40-lowercase-hex>`.
- **Run**: `python graph-sandbox/activate.py fresh --docker-context <same-named-local-context> --source-revision <same-40-hex> --run-id mission-healthy-001 --evidence-root <existing-canonical-dir> --case mission-healthy-001 --approval-fixture APPROVED`.
- **Resume**: replace `fresh` with `resume` and reuse the exact context, revision, run ID, and
  evidence root. `activate.py` is the only supported activation path; never invoke the runtime
  Compose file directly.
- **Test**: `python -m unittest discover -s graph-sandbox/tests -p "test_*.py"` for host-side contract/preflight tests; the Compose integration command is the Run command above.
- **Ports**: none — the offline profile publishes no host ports; service ports exist only on the internal Compose network.
- **Module identity**: `git@github.com:latent-sre/save-toolkit.git`; implementation root `graph-sandbox/`; contract `checkout-payments-timeout-drill/v1`.
- **Credentials**: none — the offline profile accepts no model, cloud, GitHub, PCF, SSH, or host credential mount or environment variable.
- **Progress**: GRAPH-002 is closed. Remaining operator work is `GRAPH-003` on
  [`docs/fleet-roadmap.md`](../docs/fleet-roadmap.md). Do not restore multi-worker plan files
  under `.agents/`.

## Mission block

- **Purpose**: Prove the accepted checkout/payments timeout graph contract inside a hardened, disposable, offline Docker Compose lab without creating production authority.
- **Mission transaction**: From a clean Docker state, execute the reviewed Compose entrypoint for run `mission-healthy-001`; one checkout request crosses the real synthetic checkout, payments, and inventory HTTP boundaries and ends in one authoritative successful result with payment and inventory receipts, checkpoint lineage, bounded budget evidence, and a sanitized evidence bundle outside the run-scoped containers.
- **Threat model**: A P0 is any path that exposes host credentials/files/network authority, admits a privileged or externally reachable container, runs graph/application code directly on the host, silently replays an ambiguous effect, reports `UNKNOWN` as success, loses the only evidence copy during teardown, or touches a production system.
- **Pipeline visibility**: Verification can parse the rendered Compose model, execute disposable local Linux containers, drive internal HTTP requests, stop/restart the graph runner, inspect the run-scoped SQLite checkpoint and sanitized evidence bundle, and confirm teardown. It cannot prove production behavior, provider credentials, destination-restricted live-model egress, production telemetry delivery, or multi-host durability.

## Local implementation constraints

- Direct host execution is allowed only for the standard-library preflight validator and tests.
  LangGraph and all synthetic application code execute only inside `graph-sandbox/v1` containers.
- The default Compose network is `internal: true`; publish no host ports and mount no Docker socket,
  host home, credential store, SSH agent, or arbitrary workspace path.
- Every Docker operation names one validated local context explicitly. TCP/SSH endpoints and
  ambient Docker selector/TLS variables are rejected; build and activation run with a scrubbed
  environment.
- `fresh` exclusively creates run-scoped evidence and rejects existing project/network/volume
  resources. `resume` requires matching ownership labels and the same revision/context/run identity.
  Project, network, checkpoint-volume, and evidence-volume names derive from the run ID. Containers
  receive no host bind mount; activation exports and validates the bounded evidence tree before
  teardown.
- `fresh` also acquires an exclusive, no-follow, identity-bound claim under the evidence root.
  Nonterminal exits retain it; `resume` must present the same run, revision, and context fingerprint.
  Both `fresh` and `resume` additionally hold an exclusive per-activation lease. Pre-effect failure
  releases a newly created claim and the lease; safely preserved nonterminal state retains only the
  identity claim. Terminal completion releases both after publication or bounded rejection cleanup.
- Every service runs as a numeric non-root user with a read-only root filesystem, dropped
  capabilities, `no-new-privileges`, bounded CPU, memory, PIDs, and execution time.
- Treat retries as re-execution, never exactly-once delivery. Consumer idempotency, receipts,
  reconciliation, and explicit `UNKNOWN` own effect safety.
- `checkout-ambiguous-after-commit-001` publishes the sole supported reconciliation timeline at
  `<evidence-root>/<run-id>/{unknown,reconciled}`. Both snapshots come from one activation and one
  checkout dispatch; do not synthesize either directory or run Compose directly.
- Evidence events follow the GRAPH-003 boundary vocabulary; unique identities stay out of metric
  labels. Prompts, credentials, authorization headers, raw payloads, and raw exception bodies do
  not enter normal telemetry.
