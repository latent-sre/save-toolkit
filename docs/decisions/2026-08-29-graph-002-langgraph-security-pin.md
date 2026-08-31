# Supersede the GRAPH-002 LangGraph dependency pin

- **Date:** 2026-08-29
- **Status:** Accepted
- **Decision owner:** Save Toolkit maintainers
- **Supersedes:** only the `langgraph==1.0.8` version choice in
  [`2026-08-26-graph-002-docker-sandbox-runtime.md`](2026-08-26-graph-002-docker-sandbox-runtime.md)

## Context

The accepted GRAPH-002 sandbox decision selected `langgraph==1.0.8` for the synthetic
`checkout-payments-timeout-drill/v1` consumer. Before implementation began, dependency review found
that version in the affected range for
[`GHSA-g48c-2wqr-h844`](https://github.com/advisories/GHSA-g48c-2wqr-h844), an unsafe checkpoint
deserialization advisory fixed in LangGraph `1.0.10`.

The reviewed `1.0.8` to `1.0.10` change is a patch upgrade. Its direct dependency shape and the
GRAPH-002 primitives remain compatible with the accepted design: typed reducer state, dynamic
fan-out, checkpointed interrupt and resume, and bounded retry policy. The SQLite checkpoint package
`langgraph-checkpoint-sqlite==3.1.1` is not in the advisory's affected component and remains the
accepted disposable single-run saver.

Exact pins remain required by repository policy. This decision does not authorize unbounded
dependency upgrades, host execution, live model access, or production use.

## Decision

1. GRAPH-002 uses `langgraph==1.0.10` and `langgraph-checkpoint-sqlite==3.1.1`.
2. The dependency declarations remain exact pins in `requirements-dev.txt` and in the sandbox image
   build input.
3. The original Docker sandbox, consumer, isolation, retry, idempotency, reconciliation, `UNKNOWN`,
   and verification decisions remain unchanged.
4. Checkpoint data remains synthetic and run-scoped. A checkpoint created with a different package
   set is not silently resumed or published as a terminal result; activation preserves the run for
   diagnosis, and any clean replacement uses a new run identity.

## Consequences

- The initial implementation avoids a known checkpoint-deserialization vulnerability before any
  checkpoint artifact exists.
- Exact pins preserve a reproducible image and evidence envelope, at the cost of requiring an
  explicit reviewed upgrade for later releases.
- The final Docker evidence must record the installed LangGraph and SQLite saver versions alongside
  the resolved image identities.

## Rollback

Before merge, rollback removes this implementation branch. After merge, rollback disables the
GRAPH-002 entrypoint; it must not restore vulnerable `langgraph==1.0.8`.
