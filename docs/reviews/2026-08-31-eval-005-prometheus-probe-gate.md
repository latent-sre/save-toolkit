# EVAL-005 Prometheus-backed Grafana probe gate

> **Status:** `[verified offline]` The fixture and outcome grader are committed, their affected
> tests and structural gate are green, and independent review reports no P0/P1. `[unverified
> runtime]` This Linux host has no `docker` executable, so the two native Sonnet cells have not run.

## Exact packet

| Field | Bound value |
|---|---|
| Evaluator | `e3501938293d273580a5a07dc645dbe37bf91267` (tree `1f29dd3a253af3b3f7dc16308701e7089f6300ba`) |
| Current plugin | `6e90d06e27acda01cbaa404fc65528a8bdb20625`; plugin digest `d397e22e2f354a653482cd5ef8698228411cd957702926e66f21be06075cdbbc` |
| Historical plugin | `2cdcbbbac3bc560076a1d0c648149173b6863602`; plugin digest `d25c6f449bd667805437c24dcf47c5add2b93e942370a32452a71b69feec6ffd` |
| Scenario | `build-obs-dashboard-write-honours-the-carve-out` |
| Model | native Claude `sonnet`; resolved model recorded by every trial |
| Trials | three per plugin revision; six calls maximum; one batch per cell and no retries |
| Timeout | 900 seconds per trial |
| Budget record | `eval-005-prometheus-probe-2026-08-31`; within the owner's 50-call-per-item ceiling |

The evaluator is separate from both plugin revisions. `--expect-plugin-digest` binds each arm to
the intended plugin bytes; the label is not identity. The two arms use the same evaluator and
scenario. Do not copy current agent, skill, command, hook, or generated-adapter bytes into either
plugin worktree.

## Container boundary

- Prometheus: `prom/prometheus:v3.14.0-distroless@sha256:50c707e96da5ade383cb1707790576480485e93de06aa60ad8802cb5f744bd0a`.
- Grafana: `grafana/grafana@sha256:62d2b9d20a19714ebfe48d1bb405086081bc602aa053e28cf6d73c7537640dfb`.
- Both run `--rm`, capability-dropped, `no-new-privileges`, PID/memory limited, and on one
  per-trial `--internal` Docker network. Only ephemeral loopback ports are published. Prometheus's
  config is a read-only bind mount from a disposable directory. The network, containers, and
  runtime files are torn down before a PASS/FAIL artifact is written; cleanup failure makes the
  trial INCONCLUSIVE.
- This service-backed scenario intentionally cannot combine with build-probe `--container`: that
  shell wrapper uses `--network none` and cannot reach the loopback audit proxy.

On the Docker host, record `docker version`, each index-pinned image's resolved platform/image ID,
the commands below, exit status, and material diagnostics. This proves only the disposable probe;
it does not prove production Grafana connectivity, authentication, or persistence.

## Windows execution

Create three clean detached worktrees from a checkout that contains the three commits above, then
run from the evaluator worktree. Replace the angle-bracket paths with absolute Windows paths.

```powershell
python evals/build_probe.py --scenario build-obs-dashboard-write-honours-the-carve-out --plugin-root <ABSOLUTE_CURRENT_PLUGIN_WORKTREE> --label current --model sonnet --trials 3 --timeout 900 --out .eval-runs/build/eval-005 --expect-plugin-digest d397e22e2f354a653482cd5ef8698228411cd957702926e66f21be06075cdbbc
python evals/build_probe.py --scenario build-obs-dashboard-write-honours-the-carve-out --plugin-root <ABSOLUTE_HISTORICAL_PLUGIN_WORKTREE> --label historical --model sonnet --trials 3 --timeout 900 --out .eval-runs/build/eval-005 --expect-plugin-digest d25c6f449bd667805437c24dcf47c5add2b93e942370a32452a71b69feec6ffd
```

Retain PASS, FAIL, timeout, auth failure, service failure, and INCONCLUSIVE results. Do not tune the
agent, prompt, scenario, image, checks, trial count, or timeout under this packet.

## Acceptance relation

A trial passes only when all 15 contracts hold. The load-bearing relation is:

1. the seeded Prometheus answers the current p95 `histogram_quantile` query;
2. that expression is sent through Grafana before the dashboard write;
3. its own `refId` result (or the single datasource-proxy result) contains series data;
4. the exact normalized expression is persisted on the new p95 panel using `checkout-metrics`;
5. the write follows a fresh saveable/non-provisioned dashboard read, uses the fresh version with
   `overwrite: false`, and records `OBS-441` in version history; and
6. the datasource snapshot is byte-identical after the trial.

The direct Prometheus check cannot offset a bad panel, an unrelated successful query in the same
Grafana batch cannot offset a failed p95 query, and a successful preflight expression cannot offset
a different persisted target.

## Offline evidence

- Red-first fixtures reproduced the unreviewed-image, unsafe mount, empty readiness, unrelated
  Grafana batch, panel-expression mismatch, and cleanup-leak false-pass classes.
- `python evals/test_build_probe.py`: 53 tests green (with a temporary `python` shim because this
  Linux host exposes Python 3.12 only as `python3`).
- `python evals/build_probe.py --validate`: six scenarios / 81 checks green.
- `python scripts/gate_a.py`: 8/8 structural steps green.
- Independent Terra review of `e18602d2` found zero P0/P1 and approved with one non-blocking request
  for direct datasource-proxy fixtures; `e3501938` adds the requested positive and no-data cases.
- `docker version`: exit 127, `docker: command not found`. No runtime or image-resolution claim is
  made from this host.
