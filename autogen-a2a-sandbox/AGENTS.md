# AutoGen GraphFlow + A2A sandbox project context

These instructions apply only under `autogen-a2a-sandbox/`. The root `AGENTS.md`,
`CONTRIBUTING.md`, `docs/rules.md`, and the live roadmap remain authoritative.

## Environment card

- **Toolchain**: Python 3.12.10 at `python`; Docker Engine 29.7.2 Linux/amd64; Docker Compose
  5.4.0; one pinned Linux/amd64 Python 3.12 image shared by both runtime roles unless the clean
  dependency probe proves a conflict.
- **Build**: `python autogen-a2a-sandbox/activate.py build --docker-context desktop-linux --source-revision <40-lowercase-hex>`.
- **Run**: `python autogen-a2a-sandbox/activate.py fresh --docker-context desktop-linux --source-revision <same-40-hex> --run-id mission-healthy-001 --evidence-root <existing-canonical-dir> --case mission-healthy-001 --approval-fixture PENDING`.
- **Resume**: `python autogen-a2a-sandbox/activate.py resume --docker-context desktop-linux --source-revision <same-40-hex> --run-id mission-healthy-001 --evidence-root <same-dir> --decision ACCEPT`.
- **Host test**: `python -m unittest discover -s autogen-a2a-sandbox/tests -p "test_activation.py"`;
  this is the only host-direct test surface and remains standard-library-only. Framework and
  integration discovery runs only inside the hardened, revision-bound sandbox image; the full case
  matrix runs through `activate.py` as documented in the contract.
- **Ports**: none on the host. The internal worker listens on TCP 8081 only on the Compose
  `internal: true` network; the orchestrator is a finite process and binds no port.
- **Module identity**: `git@github.com:latent-sre/save-toolkit.git`; implementation root
  `autogen-a2a-sandbox/`; runtime `autogen-a2a-sandbox/v1`; drill
  `canary-release-evidence-conflict/v1`.
- **Credentials**: none. Runtime rejects model, cloud, GitHub, PCF, SSH, proxy, and provider
  credential variables and has no external network, Docker socket, host-home, or arbitrary bind
  mount.
- **Progress**: `.agents/PROGRESS.md`; orchestration plan `.agents/plan.md`. The builder may append
  progress only; the orchestrator alone edits the plan.

## Mission block

- **Purpose**: Prove a deterministic Microsoft Agent Framework workflow can coordinate an AutoGen
  GraphFlow analysis service through a real A2A v1 task boundary and defer the only human decision
  until the final recommendation artifact.
- **Mission transaction**: From a clean Docker state, start `mission-healthy-001` through the sole
  activation entrypoint. The Microsoft Agent Framework orchestrator must discover the internal A2A
  Agent Card, consume a real streamed A2A task from the AutoGen GraphFlow worker, validate exactly
  one revision-bound `ADVANCE_CANARY` recommendation artifact, and stop at `AWAITING_APPROVAL`
  without executing a release. Resuming the same run with `ACCEPT` must restore the Agent Framework
  checkpoint, bind the decision to the artifact digest and source revision, publish a validated
  evidence bundle, and tear down every run-scoped container, network, and volume.
- **Threat model**: A P0 is host credential/file/network exposure, a privileged or host-reachable
  container, direct execution of framework/application code on the host, a second GraphFlow run
  after stream interruption, approval before a validated final artifact, approval bound to stale
  bytes, an unresolved contradiction represented as a recommendation, a release/rollback effect,
  or false-success evidence.
- **Pipeline visibility**: Verification can parse the rendered Compose model, run disposable local
  Linux containers, observe A2A JSON-RPC/SSE traffic from the orchestrator, stop/restart finite
  containers, inspect run-scoped checkpoint/state volumes, and validate bounded exported evidence.
  It cannot prove production behavior, cloud/model connectivity, external authentication,
  multi-host durability, or framework production readiness.

## Local implementation constraints

- `activate.py` is the only supported build/run entrypoint. Host execution is limited to its
  standard-library validation and tests; Microsoft Agent Framework, AutoGen, and A2A code execute
  only inside the sandbox image.
- Fresh activation creates one retained, run-scoped receipt in the invoking user's private platform
  state directory, outside the caller-selected evidence root. The receipt binds the canonical
  handoff, artifact, checkpoint, daemon, image, and Compose resource identity; resume and exact
  final replay fail closed if it is missing, changed, linked, or substituted. Its private nonce also
  authenticates the closed stage manifest, including the exact decision/runtime bytes and complete
  immutable data-file digest map; public receipt hashes and checksums are not trust anchors. Host
  validation uses one closed byte snapshot, rejects changes observed during validation, and binds a
  successful publication event to the authenticated final-claim identifier.
- Evidence files are flushed before publication. POSIX hosts also fsync the stage and parent
  directories; Windows flushes files and publishes the final directory with
  `MoveFileExW(MOVEFILE_WRITE_THROUGH)`, the strongest local stdlib/Win32 boundary available here.
  This does not claim multi-host durability or recovery from storage-device failure.
- Runtime uses exactly two containers and one internal network. Publish no ports. Add no evidence
  provider service, queue, broker, database server, gateway, model stub, or telemetry backend.
- Containers are numeric non-root, read-only, capability-free, `no-new-privileges`, and bounded by
  CPU, memory, PIDs, wall time, and tmpfs. Mount only named run-scoped state/evidence volumes.
- All agents are deterministic custom AgentChat agents. No model client, API key, or paid call is
  permitted.
- GraphFlow has exactly three analyzers, an all-join, at most one reconciliation pass, and a
  reachable terminal on every route. Merge analyzer findings by stable analyzer ID, never arrival
  order. Callable edge predicates are not serialized; resume relies on persisted manager/agent
  state and re-created named predicates that are covered by route tests.
- A2A diagnostic status/text is never authoritative. Only one closed-schema A2A v1 data-content
  Part (`Part(data=Value(...))`) from a `completed` task may reach final approval.
  `input-required`, `canceled`, `failed`, malformed, or lineage-mismatched tasks produce no
  approval request.
- The final gate accepts or rejects the exact recommendation artifact. It never promotes, deploys,
  rolls back, or contacts a real system.
