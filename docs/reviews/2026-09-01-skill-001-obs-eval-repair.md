# SKILL-001 observability eval repair

> **Conclusion:** `[verified]` The exact `dcf3bed4` native result remains a no-go: one of three
> scenarios passed, and the service-backed build result was inconclusive. The follow-up changes
> repair two invalid discovery contracts and make backing-service failure stop before model launch.
> They do not reclassify the saved result or authorize another live run.

## Exact failed measurement

- Candidate: `dcf3bed4c9a6b2c19875cfe5f4c7ad546936ea4a`.
- Plugin-input SHA-256: `91db2987b5d35825a21b0eab129db309dd941aa70c2e1d8b967950da7ee54b42`.
- Native batch: `20260901T204208Z-720985a6`; requested `sonnet`, resolved
  `claude-sonnet-5`, high effort, Claude Code 2.1.252.
- Evaluator suite: `36d4f16f31cea1731642a64e0a17d09245ada1ca6d1aa82af87ff0f60c9f1233`.
- Native verdict: FAIL; `discovery-obs-alerting-splunk-saved-search` 0/3,
  `discovery-obs-dashboards-edit-live` 0/3, and `obs-dashboards-records-unknown-write` 3/3.
- Native recorded cost: USD 3.0887254. Two separately approved build trials recorded USD
  0.63351 and were both INCONCLUSIVE.
- Durable claim-scoped evidence: [native batch record](2026-09-01-eval-20260901T204208Z-720985a6.md).

## Root causes

### Service-backed probe

`[verified]` Docker Desktop 4.88.1 / Engine 29.7.2 did not expose a published port for a service
started directly on an `--internal` network. Both build trials therefore left `GRAFANA_URL` as the
literal `${SERVICE_URL:grafana}`. The runner caught that fixture error but still launched Claude.
One response then found and queried an unrelated local E2E Grafana read-only. No write occurred,
the `admin/admin` values in the private trace belonged to the disposable fixture, and all probe
containers and networks were removed.

The repaired design retains the internal service network. Each service is reachable only through a
fixed-target TCP relay using the already-pinned
`python:3.12.10-slim-bookworm@sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4`
image. Only the relay receives a loopback-published port; its target is the validated service name
and port, not request or model input. The host audit proxy remains in front of it. A startup, relay,
seed, snapshot, or cleanup failure is INCONCLUSIVE and returns before `build_command` or Claude.

Docker documents omitted host-port syntax for ephemeral publication and the outbound-isolation
semantics of internal networks in its
[port-publishing](https://github.com/docker/docs/blob/main/content/manuals/engine/network/port-publishing.md)
and [networking](https://github.com/docker/docs/blob/main/content/manuals/compose/how-tos/networking.md)
documentation. Docker CLI source confirms the observed `docker port` error means the container has
no published frontend in
[`cli/command/container/port.go`](https://github.com/docker/cli/blob/master/cli/command/container/port.go#L62-L72).

### Discovery contracts

`[verified]` The dashboard discovery runner exposes only `Skill,Task`, while its old prompt demanded
a live HTTP write. One trial safely stopped; two returned unexecuted procedures. The graders also
rejected semantically equivalent `re-GET` and post-write `GET ... again` language. The repaired
prompt explicitly requests an `[unverified]`, tool-less procedure; the service-backed probe owns the
actual write. Positive fixtures accept `re-read`, `re-fetch`, `re-GET`, `GET ... again`, and an
explicit verify section followed by a dashboard GET. Negative fixtures still reject conflict-only
reads, query-only GETs, forced overwrite, missing readback, missing durable history, and missing
evidence labels.

`[verified]` The alerting prompt required a named route without supplying one, rewarding invention,
and its regex rejected two Markdown-formatted named routes. It now supplies fictional fixed values
`checkout-primary pager` and `runbooks/checkout-5xx.md`; exact-value graders accept layout variance
and reject placeholders.

## Red-first and offline evidence

- Before the implementation, `evals/test_build_probe.py` failed exactly the new port-boundary and
  no-model-after-service-failure checks (52/54 green).
- Before the scenario repair, `evals/test_graders.py` failed exactly the new `re-GET` and Markdown
  route variants; the later query-only negative fixture also failed until dashboard readback was
  distinguished from `/api/ds/query`.
- After the implementation, `evals/test_build_probe.py` passes 54/54 and
  `evals/test_graders.py` passes 1,479/1,479.
- `evals/build_probe.py --scenario build-obs-dashboard-write-honours-the-carve-out --validate`
  passes one scenario / 15 checks; `evals/run_evals.py --validate` passes 145 scenarios.
- A no-model Docker boundary probe started both pinned services, waited for real Prometheus
  histogram data, seeded Grafana, snapshotted the protected datasource, reached both through their
  relays, and cleaned every probe container and network.
- Regrading the old responses with the repaired graders is diagnostic only because the prompts
  changed: alerting remains 0/3 (the old prompt did not supply the new fixture values); dashboards
  becomes 1/3. No saved verdict or promotion record was rewritten.

## Remaining gate and non-actions

The original FAIL/INCONCLUSIVE evidence remains authoritative. A fresh exact-revision native run
and build probe require a new separately approved model, trial, timeout, and budget profile. No
additional model call, skill-body change, production Grafana change, push, or PR occurred in this
repair.
