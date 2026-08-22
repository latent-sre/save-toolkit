# Dashboard JSON model — the shapes an agent reads, edits, and writes

Use this reference when you hold dashboard JSON in hand: exporting it, diffing it, adding a panel or
variable, or authoring a new one. It records the three schemas Grafana 13 speaks, the field rules that
make a model valid and portable, and the conventions the official linter and every well-maintained
dashboards-as-code repository converge on. Request shapes live in [http-api](./http-api.md); the
repository contract lives in [provisioning](./provisioning.md).

Sources reviewed 2026-08-21, read from the docs source in `github:grafana/grafana` (HEAD, the
`latest`/13.2 site) unless marked otherwise. Field behavior on the deployed minor is `[unverified]`
until exercised against it.

## The version ladder — six served versions, three real shapes

The docs describe three models (Classic, V1 Resource, V2 Resource). The API serves **six versions**,
and the difference between them is not cosmetic — it decides whether your write gets migrated and
validated. Verified against `github:grafana/grafana` at tags `v13.1.4` and `v13.2.0`; identical at both.

| Version | Spec shape | What a **write** at this version does |
|---|---|---|
| `v0alpha1` | Classic, stored verbatim (`DashboardSpec = common.Unstructured`) | **Nothing.** No schema migration, no CUE validation, never errors on a schema mismatch |
| `v1` | Classic | **Migrates the model to `schemaVersion` 42** and CUE-validates it (Strict by default); rejects any other schemaVersion |
| `v1beta1` | **Go type alias of `v1`** — not a separate schema | Same as `v1`. Note it reports `storedVersion: "v1"`, because both are one Go type |
| `v2alpha1` | V2 (`elements`/`layout`) | Validates; no schemaVersion concept |
| `v2beta1` | V2, datasource-ref restructure vs `v2alpha1` | Same |
| `v2` | V2, transformation alignment vs `v2beta1` | Same |

`[sourced: apps/dashboard/pkg/apis/dashboard/*/register.go; pkg/registry/apis/dashboard/mutate.go;
.../schema_validation.go; v1/validation.go @v13.1.4]`

**The discovery order is a Go slice literal, not a stability ranking.** `preferredVersion` is simply
the first element of `GetGroupVersions()`, and an operator can reorder it with
`[grafana-apiserver] preferred_api_version`. Do not infer maturity from where a version appears.
*[sourced: register.go:261-270,332]*

### Where the "stored version" actually comes from

**There is no stored-version column.** A dashboard row is persisted with whatever `apiVersion` the
**write request** used — Grafana's apistore deliberately serializes each object with its own GVK.
`status.conversion.storedVersion` is not persisted at all: it is **computed at read time** and equals
the decoded row's own version. *[sourced: pkg/storage/unified/apistore/prepare.go:438-451;
apps/dashboard/pkg/migration/conversion/conversion.go:47-95]*

So the write path decides the stored schema — `[verified: QA + source]`:

| How the dashboard was written | Stored as | Migrated to schemaVersion 42? |
|---|---|---|
| Legacy `POST /api/dashboards/db` with a Classic body | **`v0alpha1`** | no — and not validated either |
| Legacy `POST /api/dashboards/db` with a k8s-wrapped body | the `apiVersion` **you** sent | per that version |
| `POST /api/dashboards/import` (the server endpoint) | **`v0alpha1`** | no |
| The **UI import page** | **`v1`** | yes |
| UI save, classic spec | **`v1`** | yes |
| UI save, dynamic spec (has `elements`) | **`v2`** | n/a |
| `POST /apis/.../v1/...` | `v1` | yes |
| `POST /apis/.../v2beta1/...` | `v2beta1` | n/a |

Two traps in that table. **The UI's import page does not call `/api/dashboards/import`** — it posts
straight to the app-platform v1 client, which is why a UI-imported dashboard lands at `v1` while the
API endpoint of the same name lands at `v0alpha1`. And the editor dispatches on **spec shape**, not on
the `dashboardNewLayouts` toggle: a spec containing `elements` saves at `v2`, anything else at `v1`.
*[sourced: ImportOverviewV1.tsx:74-88; browseDashboardsAPI.ts:453-468; dashboardimport/service/service.go:132-140;
dashboard_service.go:2368,2383-2385; pkg/api/dashboard.go:429-436]*

**Reading the stored version:** ask for a version you know it is *not* and read
`status.conversion.storedVersion`. A read at the stored version returns **no `status.conversion`
block at all** — the absence is the signal, not a value, because that field is only ever written by a
conversion function. Never use the legacy DTO's `meta.apiVersion` for this: it reports the version the
*client requested*, and Grafana's own dashboard service pins that client to `v0alpha1`, so it reads
`v0alpha1` for every dashboard regardless of storage. Override it with
`GET /api/dashboards/uid/<uid>?apiVersion=v1`. *[sourced: client.go:85; dashboard_service.go:2231-2247,2277;
pkg/api/dashboard.go:53-54,77-78]*

Rules that follow from the split:

- **Pin the API version on every read.** Without it "the server returns its preferred version, which may
  use a different spec shape (elements/layout/variables instead of panels/templating)" — a `jq` recipe
  written for `panels[]` then silently returns nothing. *[sourced: grafana/gcx create-dashboard skill]*
- **Write at the version the dashboard is already stored at.** Writing at a different version does not
  convert anything — it silently **rewrites the row's stored version** and runs that version's mutate
  hook (schema migration for `v1`, layout defaults for `v2*`). No guard rejects the change.
  *[sourced: prepare.go:438-451; mutate.go:54-140]*
- **Never round-trip V2 → V1 → V2.** The V2→V1 direction flattens four layout kinds into a single
  `panels[]` array and turns tabs into expanded row panels. It is structurally lossy and not
  reversible. *[sourced: v2_to_v1_layout_conversion.md:7-14]*
- **Strip `status` before you PUT anything you just GET-ed — this one is reproduced, not theorised.**
  The conversion helper prefers the *incoming* object's `status.conversion.storedVersion` over the
  object's own version, and the apistore does not strip a client-supplied `status`. Verified end to
  end on 13.1.4 `[verified: QA, 2026-08-22]`:

  | Step | read at `v0alpha1` | read at `v2` |
  |---|---|---|
  | legacy create → row stored at `v0alpha1` | **no conversion block** (correct) | `storedVersion: v0alpha1` |
  | GET at `v2`, PUT straight back **with `status`** → row now stored at `v2` | `storedVersion: v0alpha1` | `storedVersion: v0alpha1` |

  After that one round-trip the object misreports its stored version **permanently**, and the
  absence rule above is destroyed with it: a read at `v2` — the version it is now actually stored
  at — returns a conversion block instead of none, so nothing in the response can tell you the
  truth any more. Grafana's own legacy handler deletes `status` before writing
  (`pkg/api/dashboard.go:478`); a direct client must do the same. `del(.status)` on every body you
  send back, without exception.
- **Stored schema and requested schema are different things, and the server converts between them on
  read. `[verified: QA, 13.1.4]`** A dashboard created through the UI (a community import) was
  **stored as V1** with `schemaVersion: 42` — *not* V2, despite `dashboardNewLayouts` being enabled
  and the group's `preferredVersion` being `v2`. Requesting it at `v2beta1` or `v2` returned a
  genuine V2 body (`elements`, `layout`, `variables`, `cursorSync`, `timeSettings`, `preload`,
  `liveNow`) built by on-the-fly conversion, with `status.conversion = {"failed": false,
  "storedVersion": "v1"}`. Requesting it at `v1` returned the Classic shape and **no**
  `status.conversion` block at all, because nothing was converted.

  Three consequences:
    1. `status.conversion.storedVersion` tells you the truth about storage; its **absence** means you
     asked for the version it is already stored in — *unless someone has round-tripped a `status`
     into the object*, after which it reports a stale version at every read and the absence signal is
     gone for good. See the strip-`status` rule below.
  2. The same dashboard answers in either shape, so a `jq` recipe cannot detect which schema it is
     "really" in — only the version you pinned decides what you get. Pin deliberately.
    3. **`conversion.failed: false` does not mean the conversion was lossless.** Data-loss detection
     runs *after* the status is set and deliberately never touches it: a conversion that structurally
     succeeds while dropping panels, queries, annotations, links, or variables still reports
     `failed: false`. The loss is visible only in the server's
     `grafana_dashboard_conversion_failure_total{error_type="conversion_data_loss_error"}` metric and
     in log fields `panelsLost`/`queriesLost`/`annotationsLost`/`linksLost`/`variablesLost`.
     Worse, a conversion error **never fails your request** — the wrapper returns `nil`
     unconditionally, so you get `200 OK` with `failed: true` and a possibly-empty spec. Check the
     flag, and do not treat its absence as proof of fidelity.
     *[sourced: metrics.go:261-283; conversion_data_loss_detection.go:379-444]*

  Note the mismatch in vocabulary: for the same dashboard, the **legacy** `GET /api/dashboards/uid/<uid>`
  reports `meta.apiVersion: "v0alpha1"` while the app-platform `status.conversion.storedVersion` reports
  `"v1"`. They are different fields answering different questions; do not treat them as the same signal.
- Export "Classic if you plan to use the dashboard in Grafana v12.4 or older"; the community catalog
  accepts Classic only. *[sourced: docs share-dashboards-panels]*

## Classic / V1 — field cheat sheet

| Field | Rule |
|---|---|
| `uid` | Stable identity: "unique dashboard identifier that can be generated by anyone. string (8-40)". Mint it in the repository; the URL `/d/<uid>/…` and every link depend on it. Never reuse a uid within an instance |
| `id` | Database-generated numeric id. `null` on create; drop it from exports ("Grafana removes the `id` field from the dashboard JSON to help the provisioning workflow") |
| `title` | Unique within a folder — "Be careful not to reuse the same `title` multiple times within a folder" |
| `tags` | Array of strings, ≤ 50 characters each; search metadata. Never copy tags when duplicating a dashboard |
| `schemaVersion` | Integer Grafana bumps when the JSON schema changes. **42 is the final version for the V1 API** — the source constant carries "DO NOT increment this number" — and is unchanged across 13.1.4 and 13.2.0. Leave it as exported; Grafana migrates older versions on load |
| `version` | Grafana-owned save counter; send the value you read when updating so a concurrent edit fails loudly |
| `editable` | Set `false` for provisioned dashboards so the UI says so (linter `uneditable-dashboard`) |
| `timezone` | `utc` or `browser`; the team default is recorded in [wavefront-legacy](./wavefront-legacy.md) |
| `time` / `refresh` / `timepicker` | Default window and auto-refresh. "Avoid unnecessary dashboard refreshing"; `nowDelay` hides the last minutes when ingestion lags |
| `graphTooltip` | `0` none, `1` shared crosshair, `2` shared crosshair + tooltip (V2: `cursorSync: Off|Crosshair|Tooltip`) |
| `templating.list[]` | Variables — see below |
| `panels[]` | Each with `id`, `type`, `title`, `description`, `gridPos`, `datasource`, `targets[]`, `fieldConfig`, `options` |
| `links[]` | Dashboard links; `annotations.list[]` carries the built-in `-- Grafana --` annotation query |

`[sourced: docs view-dashboard-json-model; administration/provisioning]`

**Grid.** 24 columns: `gridPos.w` 1–24 and `x + w ≤ 24`; `h` in units of 30 px; "The grid has a negative
gravity that moves panels up if there is empty space above a panel." Widths that tile cleanly: full 24,
half 12, third 8, quarter 6. *[sourced: docs JSON model; grafana/skills dashboarding json-schema]*

**Minimal Classic skeleton** (valid shape; replace every `<…>`):

```json
{
  "uid": "<svc>-health", "title": "<Service> / Health", "tags": ["<team>", "<svc>"],
  "editable": false, "timezone": "utc", "graphTooltip": 1, "schemaVersion": 42, "version": 0,
  "time": {"from": "now-6h", "to": "now"}, "refresh": "1m",
  "templating": {"list": [
    {"name": "datasource", "label": "Data Source", "type": "datasource", "query": "prometheus",
     "current": {}, "hide": 0},
    {"name": "job", "label": "job", "type": "query", "datasource": {"uid": "${datasource}"},
     "query": "label_values(up, job)", "refresh": 2, "multi": true, "includeAll": true,
     "allValue": ".+", "current": {}}
  ]},
  "panels": [
    {"id": 1, "type": "timeseries", "title": "Is <svc> error ratio breaching target?",
     "description": "5xx / all requests, 5m rate. SLO 99.9%.",
     "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
     "datasource": {"type": "prometheus", "uid": "${datasource}"},
     "targets": [{"refId": "A", "datasource": {"type": "prometheus", "uid": "${datasource}"},
       "expr": "sum(rate(http_requests_total{job=~\"$job\",code=~\"5..\"}[$__rate_interval])) / sum(rate(http_requests_total{job=~\"$job\"}[$__rate_interval]))",
       "legendFormat": "error ratio"}],
     "fieldConfig": {"defaults": {"unit": "percentunit", "min": 0, "noValue": "no traffic",
       "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": null}, {"color": "red", "value": 0.001}]}},
       "overrides": []},
     "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}}}
  ],
  "annotations": {"list": [{"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"},
    "enable": true, "hide": true, "name": "Annotations & Alerts", "type": "dashboard"}]},
  "links": []
}
```

Wrap the same object as `spec` under `{"apiVersion": "dashboard.grafana.app/v1", "kind": "Dashboard",
"metadata": {"name": "<uid>", "annotations": {"grafana.app/folder": "<folder uid>"}}}` for the
app-platform API or Kubernetes-format provisioning. The folder lives in the annotation: "There is no
`folderUID` field inside `spec`; putting one there is ignored and silently lands the dashboard in
General." *[sourced: grafana/gcx create-dashboard skill]*

**What the server does to your model on write — `[verified: QA, 13.1.4]`.** A create round-trip is not
byte-preserving, so diff the *stored* object, never your local file, when checking for drift:

- **`spec.uid` and `spec.version` are stripped.** In the app-platform family identity is
  `metadata.name` and concurrency is `metadata.resourceVersion` / `metadata.generation`; the copies
  inside `spec` are accepted, recorded in `metadata.managedFields`, and dropped from the stored spec.
  Keep `uid` in the repository file (the Classic and provisioning paths need it) but never read
  identity or version back out of `spec` on this API.
- **Defaults are injected.** Sending `"annotations": {"list": []}` came back carrying the built-in
  `Annotations & Alerts` query; `fiscalYearStartMonth: 0`, `weekStart: ""`, and `timepicker: {}`
  appeared unbidden. A first diff after any create shows these additions and they are not your change.
- `metadata.uid` is a server-minted GUID entirely distinct from the dashboard uid in `metadata.name` —
  the URL path uses `name`.

## V2 Resource — what changes

- Panels become named **elements** (`spec.elements.<name>` of kind `Panel` or `LibraryPanel`); position
  moves out of the panel into **`spec.layout`** — `GridLayout`, `RowsLayout`, `AutoGridLayout`, or
  `TabsLayout`, nestable (rows in rows/tabs, tabs in rows, never a tab in a tab, four levels deep).
- Variables move to `spec.variables[]` as typed kinds (`QueryVariable`, `TextVariable`,
  `ConstantVariable`, `DatasourceVariable`, `IntervalVariable`, `CustomVariable`, `GroupByVariable`,
  `AdhocVariable` — the UI renamed it "Filter and Group by" in 13.1 but the schema keeps
  `AdhocVariable` — and `SwitchVariable`).
- **Conditional rendering** (show/hide a panel, row, or tab on a variable value, on "has data", or on the
  time-range size) exists only in V2 and only inside an Auto grid layout.
- `graphTooltip` → `cursorSync`; `time`/`timezone`/`refresh` → `timeSettings`; `preload` and `liveNow`
  are explicit.
- Required top-level spec fields, as the linter enforces them for V2: `annotations[]`, `cursorSync`,
  `elements{}`, `layout{}`, `links[]`, `preload`, `tags[]`, `timeSettings{}`, `title`, `variables[]`.

`[sourced: apps/dashboard/kinds/v2/dashboard_spec.cue; docs create-dashboard and dashboard-groupings;
grafana/dashboard-linter lint/rule_v2_required_fields.go]`

Do not author V2 element and query internals from memory: pull one real V2 dashboard from the target
with the API version pinned (see [http-api](./http-api.md)) and copy its `elements`/`layout` shapes, or
generate them with the Foundation SDK (see [agent-tooling](./agent-tooling.md)). The nested query and
visualization kinds are `[unverified]` here by design.

## Variables

| Type | Use when (official) |
|---|---|
| Query | "The list of values comes from a data source query" |
| Custom | "You want to define a fixed list of values manually" — prefer these in chains; they cost no query |
| Text box | "Viewers need to enter a free-form value" — the high-cardinality escape hatch |
| Constant | "A dashboard needs a reusable value that viewers don't change" — exported as an import option |
| Data source | "Viewers need to switch a dashboard or query between data source instances" |
| Interval | "Viewers need to change the time grouping or aggregation interval" |
| Filters (Adhoc) | "Viewers need dashboard-wide key/value filters" — Prometheus, Loki, InfluxDB, Elasticsearch, OpenSearch |
| Switch | "Viewers need to toggle between two configured values" |

`[sourced: docs dashboards/variables]`

Conventions and their reasons:

- **One `datasource`-type variable named `datasource`, referenced as `${datasource}` in every panel and
  target.** A hard-coded data-source uid breaks the moment the JSON moves instances (grafana/grafana
  #60769); the `${DS_PROMETHEUS}` / `__inputs` form from "Share dashboard with another instance" is
  resolved only by the UI import dialog, not by provisioning or the API (#80666, #82260). The linter's
  `template-datasource-rule` and `panel-datasource-rule` encode this; every mixin (kubernetes-mixin,
  Loki, Tempo) does it. *[sourced: issue threads; grafana/dashboard-linter docs/rules]*
- **Multi-value / Include All:** set `allValue` to `.+` and use `${var:regex}` inside regex matchers
  (`job=~"${job:regex}"`). The default "All" concatenation "can become very long and can have
  performance problems", and a custom all value "is never escaped". *[sourced: docs add-template-variables]*
- **Order and refresh:** "put the variables that you change often at the top"; use "On time range
  change" refresh only when the variable query depends on time; "On dashboard load" delays the whole
  dashboard. Chains are unbounded "but the more links you have, the greater the query load."
- **Syntax:** `$var`, `${var}`, `${var:<format>}`. "`[[varname]]` Do not use. Deprecated syntax." Formats:
  `csv` `a,b` · `regex` `(a|b)` · `pipe` `a|b` · `glob` `{a,b}` · `json` · `doublequote` · `singlequote` ·
  `sqlstring` · `lucene` · `percentencode` · `queryparam` `var-x=a&var-x=b` · `raw` (no data-source
  formatting). *[sourced: docs variable-syntax]*
- **Built-ins:** `$__rate_interval` — "Always use `$__rate_interval` instead of a fixed interval or
  `$__interval`" in `rate()`/`increase()`; it is `max($__interval + scrape_interval, 4 × scrape_interval)`,
  so the data source's **Scrape interval** setting must match Prometheus or panels read "No data" when
  zoomed in. `$__interval`/`$__interval_ms` for grouping; `$__from`/`$__to` (epoch ms; `:date:iso`);
  `$__range`; `$__dashboard`; `$__timezone`; `$__url_time_range` is for links only and "You must include
  the `?` or `&` separator yourself". *[sourced: docs global-variables; datasources/prometheus/template-variables]*
- URL state: `?from=now-6h&to=now&var-<name>=<value>&timezone=utc`; repeat `var-x=` for multi-value;
  `skipUrlSync: true` hides a variable from the URL.

## Panels

**Pick the visualization by the question** *[sourced: docs panels-visualizations/visualizations]*:

| Question | Visualization |
|---|---|
| How does it move over time? | **Time series** ("the default and main graph visualization") |
| One number right now, is it past a threshold? | **Stat** (big number + sparkline); **Gauge** / **Bar gauge** when min/max matter |
| What state was it in, and when did it change? | **State timeline** (thresholds turn numbers into states); **Status history** for periodic checks |
| How are values distributed over time? | **Heatmap** |
| Which of these many things is worst? | **Table** (with sort) or **Bar chart** for categorical |
| What do the logs say at this point? | **Logs** |
| What is this dashboard for? | **Text** (markdown documentation panel) |

Hygiene the linter checks and the official docs ask for:

- Every panel has a **title** (the question it answers), a **description** (GitHub-flavored markdown,
  short — it renders as a tooltip), a **unit** (`percentunit`, `reqps`, `s`/`ms`, `bytes`, `short`…),
  and **at least one target** (`panel-title-description-rule`, `panel-units-rule`, `panel-no-targets-rule`).
- **"No value"** is explicit (default is a hyphen) and **null handling** is deliberate: "By default,
  Grafana graphs connect lines between the data points, but this can be deceptive." A blank panel must
  not look healthy — distinguish no traffic, query error, and missing telemetry.
- **Thresholds** only "where they encode an operational decision" and tied to an SLO or documented limit;
  **value mappings** turn raw codes into readable states; colors mean something ("Blue means it's good,
  red means it's bad") and axes are normalized (percent, not raw cores).
- **Counters** ending in `_total` are never graphed raw — `rate`/`irate`/`increase` (`target-counter-agg-rule`).
- **Stacking** off in most cases; left/right Y-axes for mixed units.
- **Query options:** "Max data points" defaults to the panel's pixel width, so a reducer (stat, gauge)
  can change value with panel size — pin it, or set "Min interval" to the scrape interval. Panel
  time overrides are ignored when the dashboard range is absolute; use `1M/M`, never a bare `1M`.
- **Links:** dashboard links for "most if not all of the panels", panel links to drill into one panel,
  data links for one series or value. Data-link variables: `${__url_time_range}`, `${__from}`,
  `${__to}`, `${__series.name}`, `${__field.labels.<l>}`, `${__value.raw}`, `${var:queryparam}`,
  `${__all_variables}` — "you must add the ampersand yourself", and use the variable *name*, not its label.
- **Library panels** propagate edits to every consumer — use them for the shared health/SLO row.
  Repeated panels need a multi-value variable and are not individually editable.
- **Fewer, decision-oriented panels over metric inventory.** Aim under ~20 panels; if a panel would not
  change a decision, cut it.

`[sourced: docs configure-standard-options, configure-panel-options, query-transform-data,
configure-data-links, manage-library-panels, troubleshoot-dashboards, best-practices; grafana/gcx
create-dashboard skill; grafana/skills grafana-oss dashboards reference]`

## Export and import

- Exporting with "Share dashboard with another instance" (formerly "Export for sharing externally")
  rewrites each data source to `${DS_<NAME>}` and adds `__inputs`/`__requires`. *[sourced:
  public/app/features/dashboard-scene/scene/export/exporters.ts]*
- **`__inputs` are resolved and stripped at import time, not stored. `[verified: QA, 13.1.4]`** A
  community dashboard imported onto the instance carried **no** `__inputs` block afterwards: its
  panels held a concrete `{"type": "prometheus", "uid": "<real uid>"}` where the placeholder had
  been, alongside `{"uid": "$datasource"}` in panels that used the template variable, plus a
  `gnetId` recording the grafana.com id it came from. The binding is done by the importer — the UI
  dialog **or** `POST /api/dashboards/import` with an `inputs` array — so a programmatic import
  works exactly like the dialog. What does *not* resolve them is plain provisioning or a raw
  `POST /api/dashboards/db` of a file that still contains `${DS_*}`: those store the placeholder
  literally and the panel reads "Datasource named ${DS_PROMETHEUS} was not found"
  *[sourced: issues #80666, #82260]*. Commit the **post-import export**, not the community file,
  and replace the bound uid with `${datasource}` before it lands in the repository.
- Before committing an export: keep `uid`, drop `id`, drop `__inputs`/`__requires` if the export added
  them, leave `version` alone (Grafana owns it; provisioning ignores it), and run `jq empty`.
- The UI import dialog can change name, folder, and uid and maps data-source inputs — useful for a
  one-off copy, never a substitute for the repository path.

## Checking a dashboard before you write it

Two tools, and the bundled one always runs:

- **[`dashboard_hygiene.py`](../scripts/dashboard_hygiene.py)** — bundled, pure stdlib, offline.
  Applies the mechanically checkable subset of the rules above to a Classic/V1 model (a bare model, a
  k8s wrapper, or a legacy `GET` body are all accepted) and exits `0` clean, `1` with violations, `2`
  when it cannot check — notably it **refuses a V2 model rather than reporting zero** for panels it
  never read. It parses no PromQL and contacts no Grafana, so a clean report means "no rule here
  fired", never "this dashboard is correct".
- **`dashboard-linter lint --strict`** — Grafana's reference implementation, strictly better where it
  runs because it validates PromQL/LogQL and knows the real unit catalogue. It ships as a prebuilt
  binary per platform (upstream does not support `go install`), so treat the bundled checker as the
  always-available pre-filter and this as the authority when present.

**Worked example — the rules against a real dashboard `[verified 2026-08-22]`.** Run against the
community *Alertmanager* dashboard (33 panels) imported onto a live Grafana, the checker reported
**113 violations**: 17 panels with no description, 33 with no unit, 33 with no `noValue`, 27 queries
using `rate`/`increase` without `$__rate_interval`, one raw `_total` counter, an `Include All`
variable with an empty custom all value, and `editable: true`. It passed the rules for titles,
targets, and — worth noting — data-source references, which correctly use `$datasource` throughout.

Read that as calibration, not as criticism of that dashboard: a popular community dashboard is built
to render anywhere, not to meet one team's operational contract. It is exactly what arrives when
someone imports from grafana.com, and it is why the import path ends with "export, fix, then commit"
rather than "export and commit".

## The linter as a checklist

`dashboard-linter lint --strict <file>` (Prometheus-focused; Loki partially; V2 supported since
v0.2.0). Its rules are the conventions above in executable form: `template-datasource-rule`,
`template-job-rule` (`job` var, multi, `allValue .+`), `template-instance-rule`,
`template-label-promql-rule`, `template-on-time-change-reload-rule`, `panel-datasource-rule`,
`panel-title-description-rule`, `panel-units-rule`, `panel-no-targets-rule`, `target-promql-rule`,
`target-logql-rule`, `target-logql-auto-rule`, `target-rate-interval-rule`, `target-job-rule`,
`target-instance-rule`, `target-counter-agg-rule`, `uneditable-dashboard` (no `-rule` suffix — a
`.lint` key spelled `uneditable-dashboard-rule` matches nothing), `v2-required-fields-rule`.
Exclusions live in a `.lint` file beside the dashboards, keyed by rule, each with a `reason:` and, where
possible, `entries:` scoped to a dashboard/panel title. Multi-data-source dashboards legitimately
exclude the job/instance quartet. *[sourced: grafana/dashboard-linter docs/index.md, lint/rules.go,
lint/configuration.go, v0.2.0 release]*

<!-- terminal-canary: q_odjson_3c7e -->
