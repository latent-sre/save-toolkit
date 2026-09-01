# GRAPH-003 current-runtime observability evidence

> **Conclusion:** `[verified]` The bounded GRAPH-003 acceptance contract is satisfied for the
> offline `checkout-payments-timeout-drill/v1` graph. Current exact-revision sandbox evidence
> supports the indicator and failure-plane references, the synthetic runbook, and one
> deployment-free alert that fires on a readiness failure, resolves after a healthy recovery, and
> refuses to clear an earlier `UNKNOWN` effect. This record does not prove production telemetry,
> notification delivery, or the unexercised runbook branches.

## Binding and boundary

- Runtime source revision: `964e9a4aca83c138dc2b5a483b2192422d5e361e` (`origin/main` at the
  start of the exercise).
- Runtime contract: `graph-sandbox/v1`; graph contract:
  `checkout-payments-timeout-drill/v1`; evidence contract: `graph-evidence/v2`.
- Durable host-exercise envelope:
  [`graph-003-current-runtime`](2026-08-30-exercise-graph-003-current-runtime.md).
- The observability references, evaluator, runbook, and discovery near-miss were developed in the
  candidate tree based on that exact runtime revision. They do not alter the sandbox runtime.
- No model, credential, Docker socket mount, host port, external network, production target,
  Grafana object, notification route, or pager was used.
- **Runbook disposition: create.** The new operating document is
  [`skills/runbook/references/graph-sandbox.md`](../../skills/runbook/references/graph-sandbox.md).

## Exact environment

- Docker context `desktop-linux`; fingerprint
  `6a2bb20636775a19475ec1db0b13aed991808879ea43a62b6545b1fe5ff013c9`.
- Docker Engine `29.7.2`; Compose `v5.4.0`; Linux/amd64.
- Base image
  `python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4`.
- Observed runtime: Python `3.12.10`, `langgraph==1.0.10`,
  `langgraph-checkpoint-sqlite==3.1.1`, and `httpx==0.28.1`.
- The first eight runs used runner image
  `sha256:063e0ca78ab356a5793452226d2d87eeef367be566fa294518b84142fca63e51`
  and services image
  `sha256:130f9a3204da468933e6117b0e860d6a5cf92d6939ca79b50615017731ec1ff3`.
  The later clean-worktree recovery rebuild used runner image
  `sha256:df135794186cf8930d80c866d997887473bee0c8c08fdf82c35cf764bca65fd4`
  and services image
  `sha256:3b01320116608a7fd2350b445ffbb50e7e2fa452314143caa403a4ddb3e53aca`.
  Both builds bind the same source revision and base digest; whole-image IDs are build outputs, not
  a repository reproducibility claim.

## Execution and observed matrix

All builds and runs went through the sole activation path. The repeated fresh-run form was:

```powershell
python graph-sandbox/activate.py build --docker-context desktop-linux --source-revision 964e9a4aca83c138dc2b5a483b2192422d5e361e
python graph-sandbox/activate.py fresh --docker-context desktop-linux --source-revision 964e9a4aca83c138dc2b5a483b2192422d5e361e --run-id <RUN_ID> --evidence-root <EVIDENCE_ROOT> --case <CASE_ID>
```

The approval-timeout row additionally used `--approval-fixture TIMEOUT`. Every run published a
checksum-covered bundle and tore down its run-scoped containers, network, and volumes. The host
verification record uses exit `0` for `SUCCEEDED` and exit `2` for every non-success terminal
outcome. The orchestration PTY collapses native nonzero exits to `1`, so this table uses each
bundle's validated `verification.json`, not the PTY wrapper status.

| Run suffix | Case | Outcome / exit | Duration (s) | Events / completed checkpoints | Approval wait (s) | Failure planes and bounded classes |
|---|---|---:|---:|---:|---:|---|
| `healthy` | `mission-healthy-001` | `SUCCEEDED / 0` | 0.725 | 44 / 10 | 0.080 | none |
| `readiness` | `checkout-readiness-failure-001` | `FAILED / 2` | 0.353 | 24 / 6 | n/a | `checkout`; `health_http_failure`, `readiness_join_incomplete` |
| `latency` | `payments-latency-001` | `UNKNOWN / 2` | 2.644 | 45 / 10 | 0.072 | `checkout`, `graph-control`; `checkout_target_reported_unknown`, `automatic_replay_forbidden` |
| `ambiguous` | `payments-ambiguous-after-commit-001` | `UNKNOWN / 2` | 0.625 | 45 / 10 | 0.110 | `checkout`, `graph-control`; `checkout_target_reported_unknown`, `automatic_replay_forbidden` |
| `payment-http` | `payments-http-error-001` | `FAILED / 2` | 0.653 | 45 / 10 | 0.119 | `checkout`; `payment_unavailable`, `authoritative_not_committed` |
| `inventory-http` | `inventory-http-error-after-payment-001` | `UNKNOWN / 2` | 0.633 | 45 / 10 | 0.123 | `checkout`, `graph-control`; `inventory_unavailable`, `automatic_replay_forbidden` |
| `duplicate` | `duplicate-effect-001` | `SUCCEEDED / 0` | 0.855 | 44 / 10 | 0.082 | none; one idempotent receipt |
| `approval-timeout` | `mission-healthy-001` plus timeout fixture | `REJECTED / 2` | 0.734 | 31 / 7 | 0.010 | approval timeout |
| `recovery` | `mission-healthy-001` | `SUCCEEDED / 0` | 0.713 | 44 / 10 | 0.039 | none |

The synthetic sample therefore spans 0.353–2.644 seconds, approval waits of 0.010–0.123 seconds,
and six or ten completed checkpoints for the fault cases that reached checkpointing. These are
observations, not alert thresholds, SLOs, or retention settings.

## Alert evaluation

The candidate pure-standard-library evaluator recomputes the published checksum inventory and
validates manifest, verification, event, effect, version, identity, timestamp, and
contiguous-sequence invariants before deriving alert state:

```powershell
python skills/obs-alerting/scripts/graph_sandbox_alerts.py <FAULT_EVIDENCE_DIR> <RECOVERY_EVIDENCE_DIR>
python scripts/test_graph_sandbox_alerts.py
```

`[verified]` Results:

- readiness failure followed by the recovery run produced
  `NOT_EVALUATED->FIRING`, then `FIRING->RESOLVED`, with zero unresolved effects;
- ambiguous-after-commit followed by that same unrelated recovery remained `FIRING` with effect
  `graph003-ambiguous-964e9a4:checkout_effect:0:effect-checkout` unresolved; and
- checksum-tampered evidence and malformed non-contiguous event evidence failed closed in focused
  regressions.

The synthetic rule is named `GraphSandboxRunNeedsAction`, assigns active response to `sre`, names
the evidence bundle plus matching runbook branch as the first action, and has `notification_route:
null`. Cause, failure-plane, timeout, approval, checkpoint, and saturation data remain diagnostics;
they do not create more pages.

## Acceptance mapping

1. `[verified]` Existing `obs-metrics`, `obs-logs`, `obs-alerting`, and `runbook` skills own the new
   references. `discovery-obs-alerting-defers-live-graph-outage` keeps active impact and effect
   uncertainty with `sre`.
2. `[verified]` The indicator set comes from observed boundary events and covers outcome,
   divergence/join state, attempts/retries, stuck work, cancellation, approval wait, checkpoints,
   budgets, and `UNKNOWN` effects with a bounded-label policy. Unsupported queue/worker signals are
   explicitly `n/a` for this topology.
3. `[verified]` The event view keeps graph control, runner/worker, model fixture/provider,
   checkpoint store, downstream synthetic services, and reconciliation distinct.
4. `[verified]` The runbook has the seven required branches and marks current model,
   checkpoint/resume, reconciliation-resolution, and budget exercises unverified.
5. `[verified]` The deployment-free alert fires, resolves after the current recovery case, remains
   sticky for effect uncertainty, names its owner and first action, and has no route.
6. `[verified]` No agent, tool grant, credential, production dashboard, live alert route, or pager
   was introduced.

Structural verification after the candidate edits: `test_graph_sandbox_alerts.py` 4/4,
`test_observability_skill_contracts.py` 7/7, `check_canary_tokens.py` PASS, `check_links.py` PASS,
`test_graders.py` 1426/1426, and `run_evals.py --validate` PASS with 140 scenarios. Gate A was 8/8.
The complete scripts suite ran 476 tests: 467 passed, eight skipped, and one unrelated
order-dependent `test_fleet_doctor` error remained. A clean detached worktree at the unchanged
runtime/base revision reproduced that same full-suite error (472 tests: 463 passed, eight skipped,
one error); the named test passes alone on that base. This item neither changes nor closes that gap.

## Remaining limits

- `[unverified]` Current evidence does not inject a model/fixture failure, checkpoint write or
  resume failure, cancellation, or budget exhaustion.
- `[verified static at this record's runtime revision]` Focused evaluator regressions prove that a
  monotonic same-run snapshot can advance the same uncertain effect from `UNKNOWN` to `RECONCILED`,
  while unrelated success and unsupported duplicate-run snapshots cannot clear it. Post-closure PR
  [#197](https://github.com/latent-sre/save-toolkit/pull/197) later supplied the separately bounded
  host exercise; see the
  [same-effect reconciliation proof](2026-08-30-graph-sandbox-reconciliation-proof.md). That
  merged follow-up strengthens the evidence but neither reopens GRAPH-003 nor retroactively changes
  this record's runtime matrix.
- `[unverified]` Notification delivery, production ingestion, retention, SLOs, provider behavior,
  credentials, cross-host persistence/recovery, and any production graph remain outside scope.
- The raw bundles remain operator-local. This committed record and the bounded host-exercise
  envelope retain the conclusions without committing unique local paths or runtime payloads.
