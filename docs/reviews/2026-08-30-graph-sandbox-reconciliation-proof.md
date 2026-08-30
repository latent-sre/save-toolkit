# Graph-sandbox same-effect reconciliation proof

> **Conclusion:** `[verified]` The supported `graph-sandbox/activate.py` lifecycle at exact source
> revision `45108829642afd87aa67aa39633aa44f90bb6bc2` published two independently validated runtime
> snapshots for one checkout effect. The first snapshot ended `UNKNOWN`; the runner then resumed
> from a recorded LangGraph checkpoint, observed the target-owned checkout receipt, and advanced
> the same effect monotonically to `RECONCILED`. The external checkout effect was dispatched once.

## Boundary

- Contract: `checkout-payments-timeout-drill/v1`; sandbox: `graph-sandbox/v1`; evidence:
  `graph-evidence/v2`; host timeline metadata: `graph-sandbox-host-verification/v2`.
- Case: `checkout-ambiguous-after-commit-001`; run: `reconcile-proof-45108829`.
- Host: Docker context `desktop-linux`; Engine `29.7.2`; Compose `v5.4.0`; Linux/amd64.
- Base image:
  `python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4`.
- Runner image: `sha256:a104b75918dc0bcf1693569e98dd79ba505d0d6c9cc2e00cee5e2e11545cf93b`;
  services image: `sha256:f735e5a35c1c9c7f58534ee71b43ac81f22d00d7b2ab89c7e448f9556070c9cf`.
- Validated Compose SHA-256:
  `bdbb532c8c5e6b692200cd53265705be0879e1ea170c06d6e6d3cd005b43f2ac`.
- Runtime: Python `3.12.10`, `httpx 0.28.1`, `langgraph 1.0.10`, and
  `langgraph-checkpoint-sqlite 3.1.1`.
- No model call, credential, Docker socket mount, host port, external container network,
  production target, notification route, or pager was used.

## Supported lifecycle exercised

The exact build and activation forms were:

```powershell
python graph-sandbox/activate.py build --docker-context desktop-linux --source-revision 45108829642afd87aa67aa39633aa44f90bb6bc2
python graph-sandbox/activate.py fresh --docker-context desktop-linux --source-revision 45108829642afd87aa67aa39633aa44f90bb6bc2 --run-id reconcile-proof-45108829 --evidence-root F:\repos\sre-agents-graph-evidence\reconcile-proof-45108829 --case checkout-ambiguous-after-commit-001 --approval-fixture APPROVED
```

Both commands exited `0`. Activation published one atomic timeline directory with checksum-covered
`unknown/` and `reconciled/` bundles, then removed the run-scoped Compose containers, network, and
five volumes. A post-run label inventory found zero containers, zero networks, and zero volumes.

## Observed transition

| Property | UNKNOWN snapshot | RECONCILED snapshot |
|---|---|---|
| Manifest outcome | `UNKNOWN` | `SUCCEEDED` |
| Snapshot role | `UNKNOWN` | `RECONCILED` |
| Started at | `2026-08-30T17:55:49.930Z` | same |
| Ended at | `2026-08-30T17:55:50.713Z` | `2026-08-30T17:55:50.895Z` |
| Effect transitions | `PREPARED, DISPATCHED, UNKNOWN` | prior prefix plus `RECONCILED` |
| Checkout dispatch events | one | one in the extended history |
| Checkpoint resume | none | one started and one completed |
| Checkout receipt replay flag | unavailable | `false` |
| Alert state | `FIRING` | `RESOLVED` |

`[verified]` Both bundles carry the same run, case, source, start time, effect ID, idempotency key,
payload hash, target, and ledger prefix. The later bundle has one `effect.reconciled` event and one
authoritative receipt. It has no second `effect.dispatched` event. The evaluator produced
`NOT_EVALUATED -> FIRING -> RESOLVED` and ended with zero unresolved effects.

## Verification

- `[verified red-first]` The focused case-catalog regression initially failed because
  `checkout-ambiguous-after-commit-001` did not exist, then passed after the frozen case and all
  producer/consumer allowlists were added.
- `[verified]` `python scripts/test_graph_sandbox_alerts.py`: 8/8 passed, including fail-closed
  rejection when v2 evidence substitutes the semantic snapshot exit for the actual runner exit.
- `[verified]` `python -m unittest discover -s graph-sandbox/tests -p "test_*.py"`: 82/82 passed
  before the exact-revision container build.
- `[verified]` Runner image with `docker run --rm --network none`: contract 22/22, recovery 22/22,
  and integration 10/10 passed.
- `[verified]` Services image with `docker run --rm --network none`: contract 11/11 passed; both
  topology-dependent integration tests were intentionally skipped under `--network none`.
- `[verified]` The published bundles passed the deployment-free graph-sandbox alert evaluator.
- `[verified]` `git diff --check` passed before the implementation commit.

Two failed iterations were not promoted as evidence. The first activation attempt was rejected
before Docker launch because its evidence directory dirtied the exact-revision checkout. A later
runner rejection exposed a missing runner-side fixture allowlist entry; the new container contract
regression caught that producer/consumer drift, and the exact-revision images were rebuilt before
the successful run.

## Microsoft Agent Framework assessment

`[sourced]` Microsoft Agent Framework supports workflow checkpoints at superstep boundaries,
checkpoint-ID restore, executor/shared state, pending request restoration, and streamed workflow
events. Those are useful reference semantics for durable pause/resume
([Microsoft workflow checkpoint documentation](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)).

`[sourced]` Its current approval lifecycle also treats recovery after execution without a result as
indeterminate and blocks another claim; retry after an execution interruption is enabled only when
the caller supplied an explicit idempotency key
([upstream recovery tests](https://github.com/microsoft/agent-framework/blob/main/python/packages/ag-ui/tests/ag_ui/test_approval_lifecycle.py#L795-L851)).
Its own hosting ADR states that exactly-once delivery is not realistic and calls for stable
identities and protocol-level idempotency
([upstream ADR](https://github.com/microsoft/agent-framework/blob/main/docs/decisions/0028-hosting-linking-multicast-enhancements.md#L96-L105)).

`[verified local]` Those principles agree with this sandbox's existing effect ledger, stable
idempotency key, explicit `UNKNOWN`, target receipt lookup, and checkpoint resume. Adopting Agent
Framework would not supply the missing host publication semantics; it would add a second general
workflow/agent runtime and new dependencies. It is therefore not adopted in this slice.

## Limits and residual gaps

- `[verified]` This proves one local, synthetic checkout-level lost-response case and one exact
  Docker host. It does not prove a production target, provider, credential, notification route,
  cross-host recovery, retention, or an SLO.
- `[verified]` The runner resumed from a durable LangGraph checkpoint within the same container
  process. Process-death recovery between the two snapshots remains unexercised.
- `[verified]` The provisional terminal event is a bundle-only projection; it is deliberately not
  inserted into the durable event store. The reconciled bundle extends the durable event prefix and
  contains the one real final terminal event.
- `[unverified]` Agent Framework was assessed from current official documentation and upstream
  source; it was not installed or executed, because doing so would broaden this proof rather than
  validate the repository's supported lifecycle.
