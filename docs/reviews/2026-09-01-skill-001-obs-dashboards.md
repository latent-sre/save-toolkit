# SKILL-001 — obs-dashboards disposition

> **Conclusion:** `[verified]` `obs-dashboards` remains the dashboard-only live-write router, with
> its routing description byte-identical and its high-risk authority, schema, concurrency,
> reconciliation, verification, and evidence contracts retained. Generic model recitation and
> volatile product catalogues were removed from both the entrypoint and conditional references.

## Decision and exact inputs

- Branch: `work/skill-001-backend-craft`.
- Exact base: `026335aa84d79eec7966dee4066c6b55aeb1c0fc`.
- Candidate revision: the commit containing this review. The canonical candidate blobs are:
  - `skills/obs-dashboards/SKILL.md` — `91ecad42b88bab4a45ebab73c25b83ed37f047a8`
  - `references/http-api.md` — `aedd858cc62ca61e934a79508d4e0e91ff435e2a`
  - `references/json-model.md` — `0e94bc1cc00c3f3f1252352ebdb4d021141beb2c`
  - `references/agent-tooling.md` — `f5f33c222cbd9b8809253f1f0551b834532d2cca`
  - `references/viewer-editor-workflows.md` — `3c77860e8b774f6e5e61a57269718c899a551178`
  - `references/wavefront-legacy.md` — `11a7146ecb4d0ccf96ab905abaee790a4a2d0ec9`
- The user approved this one-skill change after the read-only evidence/recommendation checkpoint.
- No live Grafana target, credential, dashboard, permission, plugin, or external system was touched.

## Measurement

Sizes are canonical UTF-8 working-tree bytes against the immutable base blobs:

| Surface | Base | Candidate | Change |
|---|---:|---:|---:|
| Entrypoint | 11,419 | 7,160 | -4,259 (-37.3%) |
| HTTP API reference | 33,781 | 15,122 | -18,659 (-55.2%) |
| JSON model reference | 30,022 | 10,773 | -19,249 (-64.1%) |
| Agent tooling reference | 8,628 | 3,174 | -5,454 (-63.2%) |
| Viewer/Editor reference | 5,777 | 2,543 | -3,234 (-56.0%) |
| Legacy conventions reference | 5,090 | 2,868 | -2,222 (-43.7%) |
| All references | 83,298 | 34,480 | -48,818 (-58.6%) |
| Common live-edit path: entrypoint + HTTP + JSON | 75,222 | 33,055 | -42,167 (-56.1%) |

The entrypoint is below the 7,800-byte advisory screen. Size is the result, not the acceptance
condition; retained contracts and focused verification decide the disposition.

## What a modern model supplied without the skill

Five independent `gpt-5.6-terra` cooperative probes ran without repository, memory, web, or tool
access. Their private prompts, raw responses, and scorecard are under
`.eval-runs/obs-dashboards-workspace/probes/`.

Three exact `discovery-obs-dashboards-edit-live` controls scored 0/3 against the committed graders.
All produced plausible Classic read-modify-write mechanics, version pinning, `overwrite: false`, a
save message, and history. All omitted the fleet-required `${datasource}` form and evidence labels;
two asserted the older documented 412 conflict response instead of the QA-observed Grafana 13.1
409. Their semantically correct “verify with a fresh read” wording also exposed an over-narrow
readback regex.

Two unhinted knowledge probes independently supplied the Classic/resource API split, optimistic
concurrency, rollback rebasing, and post-write verification. Neither supplied the `v0alpha1`
stored-version probe, `status` stripping, create-only permission asymmetry, QA-observed legacy 409,
or UNKNOWN reconciliation after a dispatched write loses its response.

These are content-recall probes, not native-plugin discovery or promotion evidence. Provider cost
and independently verified resolved-model identity are unavailable from the collaboration
interface.

## Disposition by layer

### Entrypoint retained

- Dashboard/folder-only live authority under `observability-engineer`.
- Preflight, effective permissions, target discovery, stored-version read, rollback export,
  diff-before-write, API-family concurrency token, and save message.
- `idempotent-by-target`, UNKNOWN after an ambiguous dispatch, and readback-plus-history
  reconciliation before redispatch.
- Query-data proof, conditional visual inspection, durable history, and evidence labels.
- Dashboard JSON as `[UNTRUSTED]` input.
- No invented metric/label/folder/data-source identifiers; p99, `$__rate_interval`, and
  `${datasource}` remain explicit because the pressure control dropped them.
- Ownership edges to signal skills, `obs-alerting`, and `sre`.

### Conditional references retained

- The HTTP reference keeps QA-only permission asymmetry, stored-version probing, fail-closed curl
  and body builders, create/import/update examples, actual conflict behavior, UNKNOWN
  reconciliation, query verification, history, and token-rebased rollback.
- The JSON reference keeps the six-version/three-shape ladder, write-path storage semantics,
  lossy conversion, mandatory `status` stripping, V1/V2 differences, portability decisions,
  compact p99 exemplar, import behavior, and linter boundary.
- Tooling keeps only adoption/current-doc rules and the dangerous MCP patch-mode
  `overwrite: true` behavior.
- Viewer/Editor material keeps permission scope, evidence sharing, snapshot egress, managed-owner
  restore, and save-record boundaries.
- Legacy material keeps entitlement uncertainty and owner-decided folder/naming/time/variable rules.

### Removed as recitation or maintenance burden

- Generic RED/USE, visualization-selection, panel-count, color, and layout advice already supplied by
  modern models or enforced by the bundled checker.
- The full dashboard skeleton, variable-format catalogue, broad panel taxonomy, and duplicated linter
  rule inventory.
- Version/install histories and command catalogues for optional tools not installed by this
  repository; live `--help` and current upstream documentation now own them.
- Kiosk/star/UI tips and empty placeholder inventory tables.

## Eval and test decision

No scenario or test was removed. The discovery scenario's readback regex now accepts verification
phrased as “verify/confirm ... fresh read or re-read” while an adversarial fixture proves a
conflict-only re-read still fails. `discovery-obs-dashboards-edit-live` left the fixture-gap
allowlist and now has explicit green and incomplete sides.

Fresh focused evidence on the candidate:

- `scripts/test_observability_skill_contracts.py` — 7/7.
- `scripts/test_dashboard_hygiene.py` — 33/33.
- `evals/test_graders.py` — 1,474/1,474 checks.
- `evals/run_evals.py --validate` — 145 scenarios: 61 direct, 84 discovery, 65 regression.
- `scripts/test_canary_tokens.py` — 7/7.
- `scripts/test_skill_asset_contracts.py` — 9/9.
- `scripts/check_links.py` — PASS.
- `scripts/generate_platform_adapters.py --write` — 198 projections generated; adapter check PASS.
- `scripts/validate_fleet.py` — PASS; canonical plugin and generated adapters consistent.
- `scripts/run_component_tests.py` — 39/39 active component entrypoints in 100 seconds.
- `scripts/gate_a.py` — PASS, 8/8 structural steps.

The exact-commit live build/discovery evals remain `[unverified]` until the separately approved
post-commit profile runs.

## Non-actions and next gate

No native Claude/Codex eval, push, or PR was performed in this disposition. Post-commit live
evaluation must use an approved v2 execution profile binding the exact commit, resolved model,
reasoning setting, both dashboard scenarios, trials, per-trial/total timeouts, unavailable-cost
record, and bounded stop condition. Human acceptance of the exact PR revision remains the only
promotion decision.
