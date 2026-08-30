# GRAPH-002 exact-revision verification — 2026-08-29

> Historical evidence only. PR #193 review later identified five recovery, lifecycle-identity,
> cross-platform-test, and wall-budget gaps in this candidate. The focused remediation and current
> candidate evidence are recorded in
> [`2026-08-29-graph-002-pr193-remediation-verification.md`](2026-08-29-graph-002-pr193-remediation-verification.md).

## Verdict

`[verified, historical]` The offline `graph-sandbox/v1` candidate at
`02932845fe19150166ece6d01a0959a0effbdbc0` passed its host gates, immutable-image suites,
healthy mission, deterministic fault matrix, crash/restart checkpoint proof, evidence validation,
independent source review, and independent execution verification at the time recorded. This is no
longer current readiness evidence because the later PR #193 findings apply to that revision.

This report is a documentation consequence of that run. Its commit is not represented as the
container-tested revision. Any later change to a runtime input requires a new build and evidence
set; a documentation-only commit does not rewrite the provenance recorded below.

## Boundary and environment

- Consumer: `checkout-payments-timeout-drill/v1`
- Sandbox: `graph-sandbox/v1`, offline Docker Compose, Linux/amd64
- Docker context fingerprint:
  `6a2bb20636775a19475ec1db0b13aed991808879ea43a62b6545b1fe5ff013c9`
- Docker Engine: `29.7.2`; Compose: `v5.4.0`
- Python: `3.12.10`
- Runtime packages: `langgraph==1.0.10`, `langgraph-checkpoint-sqlite==3.1.1`,
  `httpx==0.28.1`
- Base image:
  `python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4`
- Build-context digest:
  `sha256:ddd90d75850fe5589c96174331a83c22e87ef2ca7dabb673387d35b28afdcacf`
- Runner image:
  `sha256:1cb40f336ef2430258eface709c1b3a55af20e329780c0f38bb4cbdb8d0a91c4`
- Services image:
  `sha256:16d20a6b2d18cfeb875d0f63c4650901d8f763a039b59cc8f14611c8efbeacbc`
- Operator-local published evidence root:
  `F:\repos\sre-agents\.worktrees\graph-002-evidence-0e243474`

No credential, host port, Docker socket, external network, live model, cloud endpoint, or production
system was used.

## Gates and immutable-image suites

| Check | Result |
|---|---|
| `python -m unittest graph-sandbox/tests/test_activation.py graph-sandbox/tests/test_preflight.py` | `[verified]` 78 tests passed |
| `python scripts/gate_a.py` | `[verified]` 8/8 structural steps passed |
| Runner image contract/recovery/integration suites | `[verified]` 50 tests passed: 20 contract, 22 recovery, 8 integration |
| Services image contract/integration discovery | `[verified]` 12 discovered: 10 contract passed, 2 topology-dependent tests skipped under `--network none` |

The image suites ran with `--rm`, `--network none`, read-only roots, numeric non-root users, all
capabilities dropped, `no-new-privileges`, bounded PIDs/memory/CPU, and a bounded `/tmp` tmpfs. The
two skipped service tests explicitly require the reviewed internal Compose topology; the real
healthy and fault runs below exercised that topology.

## Exact-revision run matrix

Every row was published by the host evidence oracle at the exact source revision. Independently
recomputed checksums covered 87 listed artifacts. Every checkpoint count equals its saver-ID count.

| Run | Frozen case | Outcome | Checkout | Exit | Checkpoints |
|---|---|---:|---:|---:|---:|
| `mission-healthy-final-001` | `mission-healthy-001` | `SUCCEEDED` | `COMPLETE` | 0 | 10/10 |
| `checkout-readiness-final-001` | `checkout-readiness-failure-001` | `FAILED` | `NOT_STARTED` | 2 | 6/6 |
| `payments-latency-retry-001` | `payments-latency-001` | `UNKNOWN` | `UNKNOWN` | 2 | 10/10 |
| `payments-http-error-retry-001` | `payments-http-error-001` | `FAILED` | `FAILED` | 2 | 10/10 |
| `payments-ambiguous-after-commit-001` | same | `UNKNOWN` | `UNKNOWN` | 2 | 10/10 |
| `inventory-http-error-after-payment-001` | same | `UNKNOWN` | `UNKNOWN` | 2 | 10/10 |
| `duplicate-effect-001` | same | `SUCCEEDED` | `COMPLETE` | 0 | 10/10 |
| `restart-resume-002` | `payments-latency-001` | `UNKNOWN` | `UNKNOWN` | 2 | 10/10 |

The healthy result contains committed payment and inventory receipts. The duplicate-effect fixture
returned target receipts with `replayed:true` while the graph retained one
`PREPARED -> DISPATCHED -> RECEIPT_RECORDED` ledger chain. Ambiguous and partial-effect cases never
became success.

## Crash and resume proof

The runner container for `restart-resume-002` was deliberately killed with exit 137 during the
2.25-second payment-latency window. Activation returned its fail-safe `resume_required` record and
preserved the four containers, internal network, and five durable volumes. The recorded, unchanged
resume command completed from checkpoint
`1f1a40da-ec66-66e3-8005-28b37306b19b`.

`[verified]` Published recovery evidence contains ordered `checkpoint.resume_started` and
`checkpoint.resume_completed` events, a non-null resume source, ten lineage IDs matching ten saver
IDs, exactly one `effect.dispatched` event, and one `PREPARED -> DISPATCHED -> UNKNOWN` effect chain.
The earlier `restart-resume-001` kill occurred before the first checkpoint and is not counted as
checkpoint-resume acceptance evidence.

## Verification-discovered fixes

Docker execution found and the branch committed five narrow fixes before the accepted revision:

1. Explicit UTF-8 command-output decoding with malformed-byte replacement, preserving binary Git
   archives as bytes (`5e7afdd9`).
2. The frozen event-data rejection diagnostic (`84bcdb45`).
3. LF policy for Dockerfiles, `.dockerignore`, and text requirements so Git archives and Windows
   checkouts hash identically (`82fcddec`, `c50a7819`).
4. Durable checkout failure lookup preserving the original 502/504 status/body instead of returning
   a misleading HTTP 200 (`02932845`).

Two first-attempt `c50a7819` fault runs exposed the failure-lookup defect and were never counted as
acceptance results. Their checkpoint/effect/event and service SQLite databases were exported to
`F:\repos\sre-agents\.worktrees\graph-002-failure-evidence-c50a7819` before the eight exactly named
stopped containers, two networks, and ten volumes were removed. Those Docker resources are not recoverable;
the exported diagnostic state remains.

## Independent checks

`[verified]` Independent exact-commit source inspection returned GO with no P0/P1 blocker.
`[verified]` A separate execution-only pass reran the host gates and both immutable-image suites,
rehashed every published evidence inventory, reconfirmed revision and checkpoint/saver equality,
confirmed the restart source checkpoint, and found zero `graph-sandbox-v1-*` containers, networks,
or volumes.

## Remaining limits

- `[unverified]` Production connectivity, credentials, provider behavior, telemetry delivery,
  persistence beyond this local Docker daemon, recovery across hosts, and live Terra behavior were
  outside the accepted offline boundary.
- `[unverified]` No candidate promotion or production authority follows from this evidence; exact
  candidate acceptance and repository integration remain human decisions.
- `[verified]` Nonblocking review gaps remain: the checked-in LF test asserts effective Git
  attributes rather than archive/worktree digest equality, and failure lookup does not separately
  cover restart plus all 502/504 variants. The exact revision received live archive/worktree digest
  comparison and real 502/504 fault coverage, so these are future test-depth improvements rather
  than acceptance blockers.
