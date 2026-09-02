# Dashboard JSON model — storage, conversion, and safe edits

Read this when holding dashboard JSON: exporting, diffing, adding a panel or variable, or authoring a
new model. Request and concurrency shapes live in [http-api](./http-api.md). Generic visualization
advice is intentionally absent; this reference keeps the Grafana behaviors that can silently change
stored data.

Sources were reviewed against `grafana/grafana` 13.1.4 and 13.2.0. Target behavior remains
`[unverified]` until exercised on that instance.

## Six served versions, three shapes

| Version | Spec shape | Write behavior |
|---|---|---|
| `v0alpha1` | Classic, unstructured | Stored verbatim; no migration or CUE validation |
| `v1` | Classic | Migrates to final V1 `schemaVersion` 42 and validates |
| `v1beta1` | Go alias of `v1` | Same as `v1`; reports stored version `v1` |
| `v2alpha1` | V2 `elements`/`layout` | Validates; no `schemaVersion` |
| `v2beta1` | V2 with restructured data-source references | Validates |
| `v2` | V2 with later transformation alignment | Validates |

The group's `preferredVersion` is ordering/configuration, not a stability promise. An unpinned read
may therefore return a different shape from the stored row.

*[sourced: `apps/dashboard/pkg/apis/dashboard/*/register.go`,
`pkg/registry/apis/dashboard/mutate.go`, and dashboard schema validation at 13.1.4/13.2.0]*

## Storage and conversion rules

A dashboard row has no independent stored-version column. Grafana serializes the object with the API
version used by the write; `status.conversion.storedVersion` is computed during a converted read.

| Write path | Stored shape |
|---|---|
| Legacy `POST /api/dashboards/db` with Classic JSON | `v0alpha1` |
| `POST /api/dashboards/import` | `v0alpha1` |
| Browser import or Classic browser save | `v1` |
| Dynamic browser save containing `elements` | `v2` |
| `POST/PUT /apis/.../<version>/...` | The named version |

The UI import page does not call the similarly named legacy import endpoint: it writes through the
app-platform V1 client. The editor selects V1 versus V2 from the spec shape, not merely from the
`dashboardNewLayouts` toggle.

*[sourced: app-platform storage preparation, dashboard conversion, browser import/save, and legacy
import handlers; app-platform rows also verified on QA 13.1.4]*

Rules that follow:

1. **Probe storage, then pin every read and write to that version.** A read converts to the version in
   the URL. A Classic `panels[]` transform against an unpinned V2 response can silently see no panels.
2. **Do not change API versions during a surgical edit.** Writing a converted body at another version
   rewrites the row's stored schema. V2 → V1 → V2 is structurally lossy: rows/tabs/layout kinds flatten
   into Classic panels and cannot be reconstructed.
3. **Strip `status` before every app-platform PUT.** Conversion status is response metadata, not write
   input. On QA 13.1.4, round-tripping a converted response with `status` permanently preserved a stale
   `storedVersion` signal even after the row changed versions. Grafana's legacy handler strips it;
   direct clients must do the same.
4. **A successful conversion is not proof of fidelity.** `conversion.failed: false` means conversion
   code returned, not that panels, queries, annotations, links, or variables survived. A conversion
   error can still answer 200. Compare the source and converted structures; Grafana also emits
   conversion-loss metrics/log fields.
5. **Do not use legacy `meta.apiVersion` as storage evidence.** It reports the client-requested version;
   Grafana's legacy service historically pins that read to `v0alpha1`. Use the app-platform conversion
   signal and the probe in [http-api](./http-api.md).

*[verified: QA 13.1.4 for the status round trip and V1/V2 reads; sourced from
`prepare.go`, conversion handlers, and conversion-loss detection]*

## Classic / V1 fields

| Field | Edit rule |
|---|---|
| `uid` | Stable 8–40 character dashboard identity; never reuse or change after publication |
| `id` | Database id; `null` on create and removed from portable exports |
| `title` | Unique within the target folder |
| `tags` | Search metadata; never copy tags while duplicating |
| `schemaVersion` | Leave the exported value; 42 is the final V1 schema version in Grafana 13 |
| `version` | Grafana save counter and legacy optimistic-concurrency token |
| `editable` | Preserve it; `false` blocks the team's UI workflow |
| `timezone` | Leave unset for this team |
| `time` / `refresh` | Preserve requested window; do not refresh faster than data changes |
| `templating.list[]` | Classic variables |
| `panels[]` | Panels with unique `id`, `gridPos`, data source, targets, field config, and options |
| `links[]` / `annotations.list[]` | Drill-down state and event overlays |

Classic layout has 24 columns. For a new panel, choose `max(existing id)+1` and put it below the last
row (`max(y+h)`); do not renumber or move unrelated panels. Panel ids are link/render targets, so a
duplicate silently retargets consumers.

On app-platform V1 writes, identity is `metadata.name` and concurrency is
`metadata.resourceVersion`. Grafana strips `spec.uid` and `spec.version`, injects defaults, and mints
a distinct `metadata.uid` GUID. Diff the stored readback, not the local pre-write body.

*[sourced: dashboard JSON model, V1 schema, and app-platform handlers; verified on QA 13.1.4]*

### Compact p99 panel exemplar

Copy structure from the target and replace the metric/labels only with discovered values:

```json
{
  "id": 42,
  "type": "timeseries",
  "title": "Is checkout p99 latency breaching target?",
  "description": "99th percentile request latency; target 300 ms.",
  "gridPos": {"x": 0, "y": 24, "w": 12, "h": 8},
  "datasource": {"type": "prometheus", "uid": "${datasource}"},
  "targets": [{
    "refId": "A",
    "datasource": {"type": "prometheus", "uid": "${datasource}"},
    "expr": "histogram_quantile(0.99, sum by (le) (rate(<discovered_metric>_bucket{<verified_labels>}[$__rate_interval])))",
    "legendFormat": "p99"
  }],
  "fieldConfig": {
    "defaults": {"unit": "s", "min": 0, "noValue": "no traffic"},
    "overrides": []
  }
}
```

The histogram unit comes from instrumentation; use `s` only for seconds and `ms` only for
milliseconds. `obs-metrics` owns query construction beyond this shape.

## V2 differences

- Panels are named `spec.elements.<name>` resources; positions live in `spec.layout`
  (`GridLayout`, `RowsLayout`, `AutoGridLayout`, or `TabsLayout`).
- Variables move to typed `spec.variables[]` entries. `graphTooltip` becomes `cursorSync`, and
  time/timezone/refresh move under `timeSettings`.
- Conditional rendering is V2-only and currently tied to auto-grid layouts.
- Required top-level fields include `annotations`, `cursorSync`, `elements`, `layout`, `links`,
  `preload`, `tags`, `timeSettings`, `title`, and `variables`.

Do not author nested V2 element/query internals from memory. Read a real V2 dashboard at its stored
version or use an already-adopted typed SDK, then preserve that shape. The bundled checker refuses V2;
use `dashboard-linter` where available.

*[sourced: V2 CUE schema, dashboard grouping documentation, and dashboard-linter V2 rules]*

## Variables and portability

- Every interchangeable-source dashboard has one data-source variable named `datasource`, referenced
  as `${datasource}` in every panel and target. A rebuilt source can receive a new uid.
- Leave the data-source variable's `current` unpinned. QA showed Grafana stores a concrete uid exactly
  as sent; `{}` resolves from the target default. Add a regex when several sources share a type.
- For multi-value/All selectors, set `allValue: ".+"` and use `${var:regex}` in regex matchers. The
  generated All expansion can become large; a custom value is not escaped.
- Use `$__rate_interval` for Prometheus `rate()`/`increase()`. The query API does not expand it, so
  verification substitutes a concrete interval and records that difference.
- Preserve time and variables in links. Deprecated `[[var]]` syntax is not used.
- A data-source variable switches instances of the same type; it cannot translate WQL, SPL, PromQL,
  LogQL, or TraceQL.

*[sourced: Grafana variable, Prometheus template-variable, and dashboard-linter documentation;
`current` behavior verified on QA 13.1.4]*

## Panel hygiene

The bundled checker and upstream linter own mechanics; retain these behavioral decisions:

- Title states the question, description supplies context, unit matches instrumentation, and
  `noValue` distinguishes no traffic from health.
- Counters use `rate`/`increase`; latency uses percentiles; ratios use compatible numerator and
  denominator populations.
- Thresholds encode an operational decision rather than decoration.
- Query cardinality is checked after variables expand. A returned HTTP success with zero frames is
  not a useful panel.
- Links preserve time/variables. Library-panel changes inventory every consumer first.
- Existing findings do not expand a surgical edit: establish the live baseline and block only new
  violations.

## Export and import

A cross-instance export rewrites data sources to `${DS_*}` and adds `__inputs`/`__requires`.
The import UI or `POST /api/dashboards/import` resolves and strips those placeholders. Raw
provisioning or `POST /api/dashboards/db` does not; it stores the literal placeholder and produces a
missing-data-source panel.

After import, replace a concrete bound uid with `${datasource}` where the dashboard is intended to be
portable. Before an authorized export leaves the instance, remove instance URLs and folder/data-source
uids. Keep stable dashboard uid, drop numeric id, and validate JSON. This team does not commit
dashboard exports; Grafana history remains the record.

*[verified: QA 13.1.4 import round trip; sourced from export/import handlers and issues 80666/82260]*

## Check before writing

- `dashboard_hygiene.py` is bundled, stdlib-only, and offline. It accepts a bare Classic/V1 model, an
  app-platform wrapper, or a legacy GET body. Exit 0 means no implemented rule fired, 1 means
  violations, and 2 means uncheckable. It refuses V2 rather than falsely reporting zero panels.
- `dashboard-linter lint --strict` validates more of the actual Grafana/PromQL/LogQL contract when the
  binary is installed, including data-source templates, panel metadata/units/targets, rate intervals,
  raw counters, job/instance conventions, editability, and V2 required fields. Scoped exclusions need
  a reason.

A clean linter result never proves target permissions, query data, rendering, concurrency, or the
durable save record; [http-api](./http-api.md) verifies those.

<!-- terminal-canary: q_odjson_3c7e -->
