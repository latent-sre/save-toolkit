# `canary-release-evidence-conflict/v1` — interface and state contract

- **Status:** active implementation contract; live work is tracked by
  [`GRAPH-005`](../docs/fleet-roadmap.md#graph-005--autogen-graphflow--a2a-canary-evidence-sandbox).
- **Owner:** The orchestrator owns this file during implementation. Builders route changes through
  the orchestrator.
- **Version:** `autogen-a2a-interface/v1`
- **Runtime:** `autogen-a2a-sandbox/v1`
- **Case:** `canary-evidence-case/v1`
- **Graph state:** `canary-analysis-state/v1`
- **Recommendation:** `release-recommendation/v1`
- **Decision:** `release-decision-state/v1`

This is the living interface between immutable cases, the Agent Framework orchestrator, the A2A
protocol boundary, the AutoGen GraphFlow worker, activation, and evidence validation. A shape change
updates every producer and consumer in one revision and bumps this interface version.

## Boundary and topology

The orchestrator is an A2A client and the worker is an A2A server. Both run from the same immutable
Python 3.12 image so the build proves the pinned dependency families coexist. They communicate only
over the run-scoped internal Compose network. The worker exposes JSON-RPC v1 and Agent Card routes
internally; the orchestrator binds no socket. No runtime service is reachable from the host.

| Method + path | Purpose | Auth |
|---|---|---|
| `GET /.well-known/agent-card.json` | Discover the worker identity, JSON-RPC v1 interface, streaming capability, and one analysis skill | none inside isolated network |
| `POST /a2a/jsonrpc` | A2A v1 message/task/status/artifact/cancel operations | none inside isolated network |
| `GET /healthz` | Worker process liveness | none inside isolated network |
| `GET /readyz` | Worker readiness after graph construction and state-path validation | none inside isolated network |

The A2A protocol owns JSON-RPC error envelopes. The sandbox does not wrap or reinterpret them as a
second HTTP error format. Host activation errors are one-line JSON objects on stderr with a stable
`error_class`; exported evidence carries the structured occurrence.

## Immutable case input

Each checked-in case is closed and digest-bound:

```json
{
  "case_version": "canary-evidence-case/v1",
  "case_id": "mission-healthy-001",
  "candidate": {
    "service": "synthetic-catalog-api",
    "candidate_revision": "1111111111111111111111111111111111111111",
    "rollback_revision": "0000000000000000000000000000000000000000"
  },
  "evidence": {
    "slo": {
      "observed_at": "2026-08-30T12:00:00Z",
      "age_seconds": 15,
      "freshness_limit_seconds": 60,
      "baseline_error_ppm": 1000,
      "canary_error_ppm": 1100,
      "burn_rate_milli": 800
    },
    "deployment": {
      "observed_at": "2026-08-30T12:00:00Z",
      "age_seconds": 10,
      "freshness_limit_seconds": 60,
      "candidate_only_change": true,
      "rollback_ready": true,
      "configuration_drift": false
    },
    "dependency": {
      "observed_at": "2026-08-30T12:00:00Z",
      "age_seconds": 10,
      "freshness_limit_seconds": 60,
      "baseline_impacted": false,
      "canary_impacted": false
    }
  },
  "reconciliation": null,
  "fault": {"slow_analyzer": null, "checkpoint_pause": false},
  "expected": {
    "a2a_state": "completed",
    "recommendation": "ADVANCE_CANARY",
    "reconciliation_attempts": 0
  }
}
```

`fault` and `expected` are harness controls. The worker validates but does not expose them to an
analyzer as evidence. `source_revision`, `run_id`, `case_digest`, A2A task/context IDs, package
versions, and image identity are supplied by activation and are not case-controlled.

`reconciliation` is either `null` or one complete replacement `evidence` snapshot with the same
three domains. It may refresh observed values but cannot change a domain's freshness policy or move
an observation backward in time. V1 deliberately has no partial-merge language.

Exactly these initial cases are required:

1. `mission-healthy-001` → completed `ADVANCE_CANARY`.
2. `confirmed-regression-001` → completed `HALT_CANARY`.
3. `stale-evidence-reconciled-001` → one saved-state resume and one reconciliation, then completed.
4. `unresolved-contradiction-001` → `input-required`, no recommendation and no approval.
5. `slow-analysis-cancel-001` → A2A `canceled`, no recommendation and no approval.
6. `checkpoint-resume-001` → saved GraphFlow state loaded into a fresh team; completed analyzers do
   not execute twice.

## A2A request

The Agent Framework A2A adapter sends one text Part containing canonical JSON with this logical
data. The worker parses and validates the JSON before starting GraphFlow. This deliberately follows
the adapter's public text mapping instead of bypassing it with a raw SDK client or adding a custom
compatibility wrapper:

```json
{
  "request_version": "canary-analysis-request/v1",
  "run_id": "mission-healthy-001",
  "source_revision": "0123456789abcdef0123456789abcdef01234567",
  "case_id": "mission-healthy-001",
  "case_digest": "<64-lowercase-hex>",
  "candidate_revision": "1111111111111111111111111111111111111111",
  "case": "<the validated immutable case object>"
}
```

The worker rejects missing/extra fields, mismatched case/candidate identity, invalid digests, and
unsupported versions before GraphFlow starts.

## GraphFlow contract

The fixed graph is:

```text
ingest -> {slo_analyzer, deployment_analyzer, dependency_analyzer}
       -> join(all three, stable analyzer-id merge)
          -> synthesize when consistent
          -> reconcile -> join when stale/contradictory and attempt=0
          -> input-required when still unresolved after attempt=1
```

At the first quiescent join the worker calls real `GraphFlow.save_state()` and atomically stores a
`canary-analysis-checkpoint/v1`, constructs a fresh team, calls real `load_state()`, and continues.
After the resumed graph reaches its terminal, it saves again and persists a closed
`canary-analysis-state/v1` with the initial-checkpoint digest, final team state, stable-sorted
contradictions, reconciliation count, route and call-count evidence, terminal reason, and
run/source/case/candidate lineage. Before a completed artifact is emitted, the worker atomically
binds the actual A2A task/context IDs and recomputes the terminal-state digest. Canceled analysis
produces neither checkpoint-derived terminal state nor artifact. Evidence rejects missing files,
digest or lineage mismatch, and repeated completed analyzer calls.

## Authoritative recommendation artifact

A completed task emits exactly one A2A artifact named `release-recommendation.json` containing one
A2A v1 Part whose `content` oneof is `data`, constructed as `Part(data=Value(...))`:

```json
{
  "artifact_version": "release-recommendation/v1",
  "artifact_id": "release-recommendation:mission-healthy-001",
  "run_id": "mission-healthy-001",
  "case_id": "mission-healthy-001",
  "case_digest": "<64-lowercase-hex>",
  "source_revision": "0123456789abcdef0123456789abcdef01234567",
  "candidate_revision": "1111111111111111111111111111111111111111",
  "a2a_task_id": "<non-empty>",
  "a2a_context_id": "<non-empty>",
  "recommendation": "ADVANCE_CANARY",
  "basis": ["slo.within_budget", "deployment.rollback_ready", "dependency.healthy"],
  "resolved_contradictions": [],
  "unresolved_contradictions": [],
  "reconciliation_attempts": 0,
  "graph_state_sha256": "<64-lowercase-hex>",
  "packages": {
    "agent-framework-core": "<installed>",
    "agent-framework-a2a": "<installed>",
    "autogen-agentchat": "<installed>",
    "a2a-sdk": "<installed>"
  },
  "artifact_digest": "<sha256 of canonical object with this field omitted>"
}
```

Only `ADVANCE_CANARY` and `HALT_CANARY` are recommendations. No confidence score exists. If
evidence cannot support either one, the task is `input-required` with a structured diagnostic
message and no artifact.

The stable artifact ID is exactly `release-recommendation:<run_id>`.

## Final approval and decision state

The Agent Framework workflow validates raw A2A task/context lineage, the data-content Part schema,
package identities, graph-state digest, and artifact digest before issuing exactly one
`request_info` event. The decision is `ACCEPT` or `REJECT` and binds:

```json
{
  "decision_version": "release-decision-state/v1",
  "run_id": "mission-healthy-001",
  "source_revision": "0123456789abcdef0123456789abcdef01234567",
  "case_id": "mission-healthy-001",
  "case_digest": "<64-lowercase-hex>",
  "candidate_revision": "1111111111111111111111111111111111111111",
  "artifact_digest": "<64-lowercase-hex>",
  "decision": "ACCEPT",
  "approver": "human-release-owner",
  "decided_at": "<UTC RFC3339>",
  "expires_at": "<UTC RFC3339 later than decided_at>"
}
```

The decision record is the only post-gate write. It is idempotent by `run_id + artifact_digest`.
It does not perform or authorize a canary promotion, deployment, rollback, or other system effect.
A mismatched, expired, repeated-with-different-value, or stale-revision decision fails closed.

## Failure mapping

| Condition | A2A / activation result | Approval |
|---|---|---|
| Valid consistent evidence | `completed` with exactly one artifact | required once |
| Contradiction resolved on first reconciliation | `completed` with exactly one artifact | required once |
| Contradiction remains after reconciliation | `input-required`, diagnostic only | forbidden |
| Cancellation acknowledged | `canceled`, no artifact | forbidden |
| Schema, lineage, protocol, or runtime failure | `failed`, no artifact | forbidden |
| A2A stream disconnect | recover the same task or fail inconclusive; never create a second run | forbidden until one completed artifact |
| Approval pending | host exit 20; state and exact resume handoff preserved | awaiting final human decision |
| Approval accepted/rejected | decision evidence published; all resources removed | complete |

## Evidence and acceptance

The final bounded bundle contains the immutable case bytes, manifest, environment/package/image
identities, rendered Compose model, A2A event timeline, GraphFlow route/call-count/state proof,
recommendation artifact when allowed, Agent Framework checkpoint/request proof, decision record when
completed, verification result, and checksums. Prompts, credentials, arbitrary exception bodies,
raw host environment, and unrestricted payloads are forbidden.

The caller-selected evidence root is untrusted for authenticity. A domain-separated HMAC keyed by
the private host receipt nonce covers the closed stage manifest and its complete immutable data-file
digest map, including the standalone and nested final decision bytes. Durable-stage recovery and
exact-final replay verify that tag before trusting public hashes; the only accepted approver identity
is `human-release-owner`. Validation consumes one closed byte snapshot, rejects a snapshot that
changes during semantic checks, performs final-replay cleanup before the last validation, and returns
the authenticated `final_claim_hmac_sha256` identifier with every successful publication event.

The normal Agent Framework adapter's bounded timeline distinguishes its real `workflow_working`
lifecycle observation from the later artifact and terminal A2A events; it does not relabel that
workflow event as protocol `WORKING`. The raw A2A interruption/cancellation path separately records
the actual A2A `working` update with same-task lineage.

Exit 0 means a schema-valid final decision record was published. Exit 2 means a validated terminal
non-success (`input-required`, canceled, failed, or rejected recommendation). Exit 20 means the sole
final approval is pending with a resumable exact-bound state. Other host failures use nonzero
sysexits-style codes and cannot publish success.

## Non-goals

- No production, cloud, PCF, GCP, model/provider, credential, or external network access.
- No real canary promotion, rollback, deployment, notification, pager, or change record.
- No generic orchestration platform, broker, queue, scheduler, database service, or telemetry stack.
- No exactly-once claim, multi-host durability claim, or production-readiness claim for any
  framework.
- No second reconciliation loop and no mid-run human evidence repair.
- No vendored-wheel or air-gapped-build guarantee; only runtime execution is offline.

## Change log

| Version | Change | Propagated to |
|---|---|---|
| `autogen-a2a-interface/v1` | Initial two-container A2A/GraphFlow/final-gate contract | canonical runtime, Compose activation, cases, and tests implemented; acceptance pending |
