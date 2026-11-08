# Dashboard JSON model — storage, conversion, and safe edits

Use [HTTP API](./http-api.md) for requests, the storage probe and concurrency, and
[dashboard design](./dashboard-design.md#new-dashboard-conventions) for new-dashboard choices.
These shapes describe Grafana 13.3.0 source/docs; target writes, imports, concurrency and rollback
remain unconfirmed until observed.

## Six served versions, three shapes

| Version | Spec shape | Write behavior |
|---|---|---|
| `v0alpha1` | Classic, unstructured | no migration or validation; admission strips `uid`, `version` and `id` from the spec |
| `v1`, `v1beta1` | Classic | migrates to final V1 `schemaVersion` 42 and validates; `v1beta1` reports `v1` |
| `v2alpha1`, `v2beta1`, `v2` | V2 `elements` and `layout` | validates; no `schemaVersion`; later versions restructure data-source references and transformations |

`preferredVersion` is configuration, not stability or stored-shape evidence.

## Storage and conversion rules

A row keeps the version of its write (the `dashboard` table's `api_version` column); through the
API, read it from `status.conversion.storedVersion` on a converted read. Legacy
`POST /api/dashboards/db` (deprecated with `/api` in Grafana 13, still served) and
`POST /api/dashboards/import` store `v0alpha1`. The UI import page stores Classic JSON as `v1` and
a V2 resource as `v2`. In Grafana 13, dynamic dashboards (`dashboardNewLayouts`, GA and on by
default) make a browser save of a Classic dashboard convert it irreversibly to `v2`; a Classic
browser save stores `v1` only where that feature is off. An app-platform write stores the version
named in its path. Never assume v1: probe immediately before every write.

1. **Never change API versions during a surgical edit.** A converted body written at another
   version rewrites the row's stored schema, and V2 → V1 → V2 is lossy: rows, tabs, and layout kinds
   flatten into Classic panels and cannot be reconstructed.
2. **Strip `status` before every app-platform `PUT`.** Conversion status describes a read response,
   not the desired dashboard spec. Do not round-trip it into storage and risk retaining stale
   `storedVersion` evidence. The current read-only check does not exercise that write path.
3. **`conversion.failed: false` is not fidelity.** A conversion error can still answer 200. Compare
   source and converted structures; Grafana also emits conversion-loss metrics.
4. **Legacy `meta.apiVersion` is not storage evidence.** It reports the requested version. On a
   failed conversion the legacy GET reports `storedVersion` and returns the unconverted source body.

## Classic / V1 edits

- Preserve published `uid` values, including existing IDs shorter than eight characters; never
  reuse or rename them during an edit. The legacy validator limits length to 40 and permits letters,
  digits, hyphens and underscores; validate new IDs against the selected API's name rules.
  `id` is `null` on create and dropped from portable exports; `schemaVersion` stays at the exported value (42 is
  final for V1 in Grafana 13); `version` is the legacy concurrency token. Review copied tags for
  the new dashboard's actual purpose and owner.
- An edit preserves `editable`, `timezone` and the requested `time` window.
- A new panel needs an unused ID; `max(existing id) + 1` is one way to allocate it. Place it in
  the requested layout without renumbering or moving unrelated panels. Panel IDs are link and
  render targets; duplicates can retarget consumers.
- On app-platform V1 writes, identity is `metadata.name` and concurrency `metadata.resourceVersion`;
  Grafana strips `spec.uid` and `spec.version`, injects defaults, and mints a distinct
  `metadata.uid`. Diff the stored readback, not the local body.

### Example panel shape

Copy the target's panel structure with discovered metrics/labels. Keep both panel and query-target
`datasource` references typed and bound to the intended source; an example's panel ID, layout or
threshold is not a team default. `obs-analysis` owns the query.

## V2 differences

Panels are `spec.elements.<name>` resources positioned by `spec.layout` (`GridLayout`,
`RowsLayout`, `AutoGridLayout`, `TabsLayout`); variables are typed `spec.variables[]`;
`graphTooltip` becomes `cursorSync`; time, timezone, and refresh live under `timeSettings`;
conditional rendering is V2-only and applies to auto-grid items, rows and tabs. Do not author V2
element or query internals from memory: read a real V2 dashboard at its stored version, or use an
adopted typed SDK, and preserve that shape.

## Variables and portability

- A data-source variable cannot translate query languages: mixed-backend dashboards need separately
  typed variables (for example `${metrics_source}` and `${logs_source}`) in corresponding panels and
  targets. Set each variable's plugin type and resolve it to a discovered source; scope selection
  when several sources share that type. For portable exports, leave `current` unpinned and verify
  selected sources after import; do not assume a saved concrete uid resolves to the intended source
  on another instance.
- Regex matchers use `${var:regex}`; a custom All value such as `.+` is not escaped, works only
  where the query language takes a regex, and the generated expansion can grow large.
- `increase(...[$__range])` can deliberately total the selected dashboard window; preserve
  fixed-horizon intent when justified by scrape cadence. The query API expands Prometheus interval
  macros from the request, not the panel; see [query verification](./http-api.md#verify-then-record).
  LogQL has its own interval semantics; do not apply the Prometheus rule to Loki targets.

A cross-instance export rewrites data sources to `${DS_*}` and adds `__inputs` and `__requires`,
which only the import endpoint or the import UI resolves ([import](./http-api.md#create-import-update)).
Distinguish repository recovery copies from the fresh live export used to prepare a change.

## Check before writing

`dashboard_hygiene.py` is bundled, stdlib-only, and offline; it accepts a bare Classic/V1 or V2
model, an app-platform wrapper, or a legacy GET body. Resolve the installed
[hygiene helper](../scripts/dashboard_hygiene.py) to its absolute path and run
`python "<resolved helper path>" <file>`. It exits 0 with no review-required findings (advisories
may remain), 1 when a query or missing-target finding needs review, and 2 when uncheckable. It
checks a V2 candidate by mapping its elements and grid, row, tab and auto-grid layouts onto the
Classic panel shape, and refuses an unknown layout or element kind rather than reporting zero
panels; it never validates the V2 schema itself. Check the actual V2 candidate, never a converted
V1 substitute, and use `dashboard-linter` v0.5.2+ for V2 schema validation; if the candidate cannot
be checked, report the gap and stop before writing. `dashboard-linter lint --strict`, when installed,
validates more of the real Grafana, PromQL, and LogQL contract; scoped exclusions need a reason.
PromQL heuristics require a datasource reference typed `prometheus`; untyped references remain
unchecked for query semantics. Treat fixed-UID and counter-name findings as review prompts as
explained in [read-only review](./read-only-review.md). On an edit, check the live model first and
block only confirmed defects this diff introduces; report pre-existing findings without expanding
scope. Presentation and portability advice does not block a write. A clean result never proves
target permissions, query data, rendering, concurrency, or the durable save record;
[http-api](./http-api.md) verifies those.
