# Use a consumer-specific Docker Compose sandbox for GRAPH-002

- **Date:** 2026-08-26
- **Status:** Accepted
- **Decision owner:** Save Toolkit maintainers
- **Current state (2026-08-30):** `GRAPH-002` closed into
  [`roadmap-closed.md`](../roadmap-closed.md). This record still governs the
  `graph-sandbox/v1` runtime choice. Remaining graph operations work is `GRAPH-003`
  on the live tracker.

## Context

`GRAPH-002` needs one named consumer before the fleet adopts a graph runtime. The selected consumer
is the existing synthetic checkout payments-timeout incident drill. That drill already models
ordered lane handoffs, staged evidence, human approval gates, bounded retries, cost and time budgets,
and `UNKNOWN` outcomes, but today it scaffolds a source tree and evidence files rather than operating
a running application topology.

The drill's own boundary is explicit: its launcher is not a sandbox. It removes selected environment
variables and narrows lane tools, but a Bash-capable lane still executes as the caller's OS identity
and may see inherited binaries, credential stores, readable files, and permitted network paths. A
direct host process therefore cannot be the accepted execution boundary for a graph that deliberately
tests retries, restarts, fault injection, and untrusted synthetic inputs.

The repository retired the unused general-purpose digest-bound verification sandbox on 2026-08-26.
This decision does not restore that framework. It introduces a consumer-specific disposable lab with
running services because `checkout-payments-timeout-drill/v1` is now a named consumer. The lab follows
the repository's Docker-backed local-verification rules but owns only the graph drill's topology,
state, and failure tests.

The stack profile permits Python services and local Docker-backed verification. PCF/TAS remains the
current application runtime, and the GCP landing runtime remains undecided. This sandbox is a local
test environment: it does not select PCF, Cloud Run, GKE, Kubernetes, or a production deployment
target.

Upstream source and tests pinned during the decision review establish that `langgraph==1.0.8` at
commit [`a7a27dd43a4229c2ca09ac065a6a39e4ce083063`](https://github.com/langchain-ai/langgraph/tree/a7a27dd43a4229c2ca09ac065a6a39e4ce083063)
supplies typed reducer state, dynamic
[`Send`](https://github.com/langchain-ai/langgraph/blob/a7a27dd43a4229c2ca09ac065a6a39e4ce083063/langgraph/types.py#L289-L330)
fan-out, checkpointed
[`interrupt`/resume](https://github.com/langchain-ai/langgraph/blob/a7a27dd43a4229c2ca09ac065a6a39e4ce083063/langgraph/types.py#L420-L440),
and bounded
[`RetryPolicy`](https://github.com/langchain-ai/langgraph/blob/a7a27dd43a4229c2ca09ac065a6a39e4ce083063/langgraph/pregel/_retry.py#L26-L105)
primitives. The SQLite saver is pinned separately as
[`langgraph-checkpoint-sqlite==3.1.1`](https://pypi.org/project/langgraph-checkpoint-sqlite/3.1.1/).
LangGraph retries rerun a complete node task and do not compensate arbitrary external effects. The
consumer must therefore retain its own idempotency, fencing, receipts, reconciliation, and explicit
`UNKNOWN` state.

## Decision

1. **Name one consumer and graph.** The first runtime-specific implementation is
   `checkout-payments-timeout-drill/v1`, derived from the existing `incident-drill` scenario. It is a
   synthetic evaluation graph, not the fleet's universal control plane and not a production workflow.
2. **Run it only in `graph-sandbox/v1`.** The allowed execution environment is a hardened,
   disposable Docker Compose lab. Direct host execution of the graph or its synthetic applications
   is prohibited.
3. **Use a small running topology.** The first topology contains:
   - `graph-runner`: Python 3.12, `langgraph==1.0.8`, and
     `langgraph-checkpoint-sqlite==3.1.1`;
   - `checkout`: the existing synthetic FastAPI checkout service;
   - `payments`: a synthetic dependency with deterministic success, latency, error, duplicate, and
     ambiguous-result modes;
   - `inventory`: a normally healthy synthetic dependency; and
   - an optional bounded `loadgen` profile used only by saturation cases.
4. **Make the default profile offline.** The default Compose network is internal-only, publishes no
   host ports, and permits only inter-service traffic. Graph-node model responses are deterministic
   fixtures in this profile. Offline contract, recovery, temporal, consistency, and budget tests
   require no model credential and make no paid call.
5. **Treat a live Terra run as a separate profile and gate.** A later bounded Terra behavioral run
   may occur only after the offline acceptance suite is green and a human approves the exact run,
   trial count, spend ceiling, ephemeral credential path, and externally enforced endpoint-restricted
   egress. Docker Compose alone is not accepted as domain-level egress enforcement. No standing model
   credential is written to Compose, an image, a volume, a repository file, or a result bundle.
6. **Harden every service.** Containers run as non-root with read-only root filesystems, dropped
   Linux capabilities, `no-new-privileges`, bounded CPU, memory, process count, and execution time,
   and no Docker socket, host home, SSH agent, cloud/PCF/GitHub credential, arbitrary workspace bind,
   or privileged device. Images are version- and digest-pinned before execution. Only sanitized
   scenario input enters the lab and only a bounded evidence directory exits it.
7. **Keep state run-scoped and recoverable.** LangGraph checkpoints live in a dedicated SQLite
   volume keyed by stable run and thread identities. Application receipts and the evidence envelope
   preserve run, node, edge, task, attempt, replay, checkpoint, and effect identifiers. After durable
   evidence is exported, the run-specific containers, networks, and volumes are destroyed.
8. **Fail closed before graph execution.** A preflight validator rejects missing image digests,
   unexpected mounts, published ports, external networks in the offline profile, privileged mode,
   added capabilities, a Docker socket, root users, writable root filesystems, absent resource
   limits, or an unavailable Docker daemon. An attestation flag is not evidence that these controls
   exist.
9. **Keep runtime guidance conditional.** Portable workflow design remains in
   `workflow-graph-engineering`. Runtime-specific implementation guidance is loaded only for the
   accepted LangGraph consumer; it must not make LangGraph the default for every graph-shaped task.
   Implementation and acceptance evidence closed with `GRAPH-002` into
   [`roadmap-closed.md`](../roadmap-closed.md); this ADR still governs the runtime
   choice, not a second backlog.

## Failure and recovery contract

- **Application failure:** health checks and graph state identify the failed service; retries stay
  inside the node's declared attempt and time budgets.
- **Graph-runner crash:** restart against the same run-scoped checkpoint volume and stable thread
  identity; prove that committed nodes are not re-applied.
- **Crash around an effect:** if dispatch may have occurred but no final receipt exists, transition
  to `UNKNOWN` and require reconciliation or target-native idempotency before replay.
- **Checkpoint corruption or incompatibility:** stop the run, preserve the evidence as
  `inconclusive`, and start a new run from clean state. Never silently discard the checkpoint and
  call the resumed result equivalent.
- **Budget, approval, or cancellation boundary:** stop scheduling new work, record the terminal or
  indeterminate state, and require positive cancellation acknowledgement before treating descendant
  work as stopped.
- **Sandbox preflight failure:** run nothing. Missing isolation is an environment failure, not a
  waived test or graph result.

## Consequences

### Positive

- The first graph operates real synthetic HTTP services and can prove restart, timeout, saturation,
  retry, idempotency, and reconciliation behavior at the relevant boundary.
- The lab has a named consumer and teardown path rather than becoming speculative fleet machinery.
- Offline-first implementation provides deterministic evidence without model cost or credentials.
- The same running topology can later supply GRAPH-003 with a concrete graph and failure planes to
  observe, without creating a new agent or production service.

### Negative and neutral

- Docker Desktop or a compatible Linux Docker engine becomes an implementation prerequisite. A
  client binary without a reachable daemon is insufficient.
- Compose provides topology and container controls, not complete destination-aware egress policy.
  The live Terra profile remains blocked until that independent boundary is named and verified.
- SQLite is appropriate for one disposable single-run lab, not a shared or multi-instance production
  deployment. This decision creates no production storage precedent.
- The payments and inventory simulators add code and tests that must remain deterministic and visibly
  synthetic.

## Rollout and rollback

Delivery is offline-first and incremental. `GRAPH-002` sequence, acceptance checks, and closeout are
recorded in [`roadmap-closed.md`](../roadmap-closed.md); this ADR records the stable choice,
not a second backlog.

Before any implementation is merged, rollback is deletion of the feature branch. After the offline
lab lands, rollback disables or removes the `graph-sandbox/v1` entrypoint and returns
`incident-drill` to its existing manual file-and-lane procedure. Because the lab is synthetic,
unpublished, and holds no production state, rollback requires no data migration or production
change. A failed run retains only its sanitized evidence bundle; its run-scoped containers,
networks, and volumes are removed after evidence capture.

## Rejected alternatives

- **Run LangGraph directly on the workstation.** Process locality does not isolate host credentials,
  files, inherited tools, or network access.
- **Containerize only `graph-runner`.** That would leave application behavior mocked or host-bound and
  would not prove the HTTP timeout, saturation, restart, and effect boundaries the consumer exists to
  test.
- **Restore the retired generic verification sandbox.** The new need is a multi-service,
  consumer-specific topology, not arbitrary digest-bound command execution. Restoring the old
  framework would add an unrelated abstraction and still not supply the running applications.
- **Deploy the lab to PCF, Cloud Run, GKE, or Kubernetes.** A local synthetic proof does not justify
  a deployment platform or interact with the pending GCP landing-runtime decision.
- **Enable broad internet access for convenience.** It weakens the isolation boundary and makes
  results depend on uncontrolled services. Live model egress is a separate, explicitly approved
  profile.

## Reopen trigger

Write a superseding decision if the consumer needs multi-host or multi-run shared state, if Docker
cannot supply the required isolation on an approved runner, if a production workflow becomes the
consumer, or if live Terra evaluation requires a different credential or egress architecture.

<!-- ADRs are append-only and immutable once accepted. To change a decision, write a new ADR and mark
     this one "superseded by <YYYY-MM-DD>-<slug>". -->
