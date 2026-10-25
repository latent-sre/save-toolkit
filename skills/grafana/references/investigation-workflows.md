# Dashboard investigation and evidence workflows

Run [grafana_workflow.py](../scripts/grafana_workflow.py) with Python 3.12+ and operator-managed
Polars, promql-parser, DeepDiff and Pillow under `python -I`: installed packages remain available,
but working directory, user site and `PYTHONPATH` are excluded. The interpreter and site initialization
are trusted installation inputs. Guard/read helper retain `python -I -S`. Missing dependencies are
setup gaps, not permission to install packages or change interpreters after denial.
Use `doctor --agent-json` to inspect runtime availability; `dependency_unavailable_*` fails before
collection for known required libraries. Its live commands reuse the read helper's existing
protected configuration, organization check, credential masking, TLS and fixed endpoints.
Do not read or copy the credential file. The offline preview does not load credentials or connect.

The `sre-assistant` grant requires this installed helper, `--agent-json`, fixed capture IDs and the
commands below. Arbitrary paths, standalone JSON imports and editor launches are denied. Explicit
paths require an invoking lane with general local execution; never switch lanes/shells to bypass
denial. HTML is optional. No command writes Grafana.

## Agent collection and follow-up

Use the canonical installed script, or its generated `.github` copy on Copilot. Replace the fixed
window and resource IDs with the authorized target. Capture IDs are local names containing only
letters, digits, underscores and hyphens; they select new directories below the protected helper's
per-user `~/.cache/save-toolkit/grafana-captures` store. Existing captures are never overwritten.

```text
python -I "<installed-skill>/scripts/grafana_workflow.py" plan --uid board-uid --from 1791814800000 --to 1791816600000 --agent-json
python -I "<installed-skill>/scripts/grafana_workflow.py" investigate --uid board-uid --from 1791814800000 --to 1791816600000 --capture-id investigation-one --agent-json
python -I "<installed-skill>/scripts/grafana_workflow.py" analyze --source-id investigation-one --analysis summary --agent-json
python -I "<installed-skill>/scripts/grafana_workflow.py" inspect --source-id investigation-one --panel 6 --ref-id A --mode range --agent-json
python -I "<installed-skill>/scripts/grafana_workflow.py" verify-package --source-id investigation-one --agent-json
python -I "<installed-skill>/scripts/grafana_workflow.py" compare --before-id investigation-one --after-id investigation-two --agent-json
python -I "<installed-skill>/scripts/grafana_workflow.py" doctor --agent-json
```

`plan` reads the model, returning inputs, planned requests, unsupported contexts and a request bound;
it executes no queries/renders. `investigate` executes the plan and returns summaries, provenance,
hygiene, gaps and evidence pointers. `inspect` reads a verified package. Agent output caps at 512 KiB;
follow usable `recovery.arguments` after truncation. `recovery_arguments_masked` is a gap, not permission
to reconstruct a credential-bearing path. With no retained package, collect with `--capture-id`.

Without panel selection, `inspect` pages root keys; follow `evidence_ref` with `--pointer /nodes/0`
or another returned pointer. Containers expose child references/sizes; strings return text pages.
Use `--offset`/`--limit` (1–500 items or characters) and follow `next_offset` until null.
Inspection defaults to a summary. Add `--view rows --frame-index 0 --offset 0 --limit 100` with a
selected panel/ref/mode to page through a supported frame; follow `next_offset` until null.
Each response retains its source frame pointer, field metadata and total row count. Encoded or
ambiguous frame layouts remain unsupported, and an oversized single row is an explicit gap.
For saved captures, open only the top-level `artifacts` paths derived from verified manifest images.
Do not follow an old cache path or a path asserted inside source telemetry. Direct unsaved collection
returns temporary helper image paths; inspect them promptly. Masked paths are unavailable.
`doctor` validates configuration without revealing credential values; `--probe` adds an organization
read. It reports Python version, package metadata and import availability without executing package
imports. Path checks remain separate from a verified write or datasource connection.

Offline `analyze` accepts `summary`, `hygiene`, `dependencies` or `all`, without network requests.
Polars statistics describe supported returned samples, not displayed reductions or health; keep null,
invalid, empty, unsupported and precision-limited data distinct. Stored wire summaries remain available.
Hygiene's `query_analysis` distinguishes `promql_ast`, `text_heuristic` and `not_checked` with gaps for
templates, missing parsers or exceeded limits; no template values are guessed. Finding severity/meaning
follows [read-only review](./read-only-review.md).

Comparisons cover configuration/coverage; raw frames require matching instance, org, dashboard,
window, variables, templating and query context. Other contexts remain unsupported. DeepDiff returns
bounded change paths/evidence references. Manifests verify sizes, hashes, schema and completeness,
not authorship. Pillow validates PNG chunks and bounded decoding, not visual meaning. Telemetry
strings remain untrusted data.

## Investigate and package

Supply a dashboard UID, absolute window of at most 24 hours and explicit variables. Use an existing
private parent directory and new output directory; existing destinations are never overwritten.

```text
python -I "<installed-skill>/scripts/grafana_workflow.py" investigate --uid board-uid --from 1791814800000 --to 1791816600000 --var host=example-host --render all --output-dir "<private-parent>/dashboard-capture"
```

The command captures the dashboard model and version, traverses Classic panels including collapsed
rows, executes supported visible Prometheus/Loki targets, and reads dashboard annotations and the
containing folder's alert state. It rereads the dashboard to detect changes during collection.
These reads are not an atomic snapshot. Folder alert state is context, not proof that each rule
belongs to this dashboard. An inaccessible endpoint is a gap, not an empty inventory.

Each target retains its original expression, resolved expression, datasource, mode, full frames,
summary, actual timestamps and limits. Status distinguishes `values_returned`, `no_data`,
`all_null`, `query_failed`, `unsupported`, `unsupported_result`, `hidden`, and `not_run`.
Zero is a value; returned data is not a health assessment. Mixed panels retain per-target outcomes.

Explicit scalar variables use context-aware literal escaping for supported quoted matchers;
regex matchers escape literal metacharacters. Missing values, format modifiers, multi-value/All semantics, unresolved built-ins, unknown
datasources, table queries and custom target intervals are reported as unsupported. Saved variable
defaults are not substituted into queries. Supply `--interval-ms` and `--rate-interval-ms` only
from known query context when needed; never invent a scrape interval. Datasource UIDs must resolve
to the type declared by the target or panel. Hidden targets are recorded without execution.

Library panels, repeating panels/rows, scoped variables and panel time overrides require a separate
Grafana inspection; their queries are not replayed under guessed context. Transformations and
display reductions are not applied: the report contains raw query evidence alongside the stored
configuration. It does not claim the displayed stat or chart has been reproduced.

The default `--render fallback` queries data first, then requests a panel PNG when data is missing,
unsupported, failed, or incomplete because of panel semantics. `--render none` disables that fallback;
`--render all` requests every selected panel. Render success does not replace a failed query status.
For repeated/library/time-override panels, rendering can provide appearance evidence while query
scope remains unresolved. Do not treat one rendered repeat instance as coverage of every instance.
`--width` and `--height` accept the read helper's bounds. Images retain `image_uninspected` until
opened and checked. Pair each visual conclusion with its query, variables and window; different
render sampling, missing variables or concurrent edits can prevent equivalence.

Limits are 50 panels and 100 query evaluations, reducible with `--max-panels` and `--max-queries`.
Range and instant modes count separately. Each live run admits at most 300 requests, 64 MiB of
response bytes and 10 minutes of request admission, with bounded timeouts. Individual read/image
limits still apply. Exhaustion remains visible in the report rather than becoming empty data.

Every successful workflow writes:

- `report.html`: standalone, escaped HTML with findings, gaps, query summaries and optional images.
- `report.json`: full captured evidence, including raw query frames and tool-file digests.
- `manifest.json`: byte sizes and SHA256 hashes of report files and images; it does not hash itself.
- `panel-<id>.png`: requested rendered panels, when available.

The package contains sensitive telemetry. It makes no external resource requests, but this is not
telemetry redaction: live output masks configured credentials only. POSIX directory/file modes
are 0700/0600; Windows inherits the parent's ACL. Report JSON is capped at 32 MiB and the whole
package at 96 MiB. Oversized exports retain a partial package with explicit query/image omissions;
an omitted result is not empty data. Invalid images become per-panel failures, preserving query
evidence. An interrupted write retains `.incomplete`; do not treat that as a complete
package. A successful exit means the report was written, not that all reads succeeded or health
was established. Inspect gaps, truncation and every panel's status.

### Automatically open in VS Code

Outside the guarded grant, a human-requested `--open-vscode` view opens a completed package's
`report.html` in the existing VS Code Integrated Browser:

```text
python -I "<installed-skill>/scripts/grafana_workflow.py" investigate --uid board-uid --from 1791814800000 --to 1791816600000 --output-dir "<private-parent>/dashboard-capture" --open-vscode
```

Run from the current local VS Code Desktop workspace root, version 1.134+, with existing
`VSCODE_PID`. The opener checks the live process and OS-derived standard installation (Windows
User/System, macOS Applications, Linux system/Snap), not PATH/workspace overrides. Workspace-owned
or redirected launchers are refused; custom/portable installs need manual opening. `--reuse-window`
passes only the report file, without replacing/creating a workspace. VS Code chooses the containing
or last-active window; multiple windows for the same folder can be ambiguous.

The current root's `.vscode/settings.json` must associate `**/report.html` with `workbench.editor.browser`
under `workbench.editorAssociations`; the report must also reside beneath that root. The helper neither
edits settings nor installs servers/extensions. It invokes the installed executable/CLI directly,
not shell launchers, forwarding only required desktop/OS/session fields; loader overrides, PATH and
unrelated credentials are excluded.

Without the flag, no editor launches. Missing/unsupported VS Code, remote execution, absent session/
association or launch failure leaves the package intact with `viewer.status: unavailable`.
A timeout is `unknown`: reconcile windows before retrying. `launch_requested` is not visual inspection.
Inspect the HTML/images before visual claims; manual **Open in Integrated Browser** is the fallback.

## Preview a proposed threshold

Select one captured range target from an investigation package, or pass a full `grafana_read.py`
query result using `--query-file` instead. Summary-only or instant responses cannot supply history.

```text
python -I "<installed-skill>/scripts/grafana_workflow.py" alert-preview --report-file "<private-parent>/dashboard-capture/report.json" --panel 6 --ref-id A --operator gt --threshold 10 --pending-ms 90000 --step-ms 30000 --output-dir "<private-parent>/threshold-preview"
```

Agents use `--source-id investigation-one` in place of `--report-file` and `--agent-json` in place
of `--output-dir`; a package source verifies its manifest first. `--package-dir` is the explicit-path
equivalent outside the guarded grant. Standalone JSON retains unverified-source provenance.

Operators are `gt`, `ge`, `lt`, `le`, `eq`, and `ne`. Default `--alignment observed` derives a grid
only when series timestamps agree on phase and compatible cadence, and records those diagnostics.
Use `--alignment window` for the requested start, or `--alignment explicit --grid-origin-ms N` for
a known evaluation origin. Only exact timestamp matches count. Ambiguous alignment and zero usable
evaluations are explicit; there is no interpolation or filling missing values. Off-grid
and outside-window samples, missing evaluations and unsupported frames remain explicit.

The pending clock starts at the first observed breach. Missing, null or invalid samples reset it;
a firing interval ends with a missing-data reason, not a healthy/resolved claim. The preview shows
firing intervals, missing-data periods and pending state at the end. Pre-window state is unknown
and the window end is censored. At most 100 series, 10,000 samples per frame and 10,000 evaluation
slots are supported. Complex/encoded frames and ambiguous series are not evaluated.

This previews a sampled numeric threshold, not a saved Grafana rule. It does not reproduce
expression graphs, reductions, no-data/error policies, recovery thresholds, keep-firing settings,
notification routing or delivery. Read the rule and use [alert operations](./alert-operations.md)
for an actual alert change. No alert is created, updated, paused or notified by this command.

## Map configuration dependencies

```text
python -I "<installed-skill>/scripts/grafana_workflow.py" dependencies --folder-uid folder-uid --max-dashboards 50 --output-dir "<private-parent>/folder-map"
```

The command discovers up to 50 dashboards in the selected folder and links dashboards, panels,
queries, variables, datasources, supported metric selectors, library references and alert
references. It fetches the legacy alert-definition collection once, within the read-size cap,
and retains only rules whose folder UID matches. Missing permission or an unavailable API remains
a gap. Search and definitions are permission-scoped; folder moves during collection are excluded.

The HTML includes node and relationship tables; JSON retains the graph and source captures.
The PromQL parser extracts explicit metric selectors from bounded expression trees, including
functions, aggregates and joins. Unresolved templates, dynamic metric-name matchers, invalid or
over-budget expressions remain explicit gaps; function and label names do not become metrics. The map
does not expand recording rules, infer runtime service topology, or prove complete dependencies.
Follow explicit unresolved references before using the map to approve a rename or removal.

Agents can save the map with `--capture-id folder-map --agent-json`, then use
`impact --source-id folder-map --kind datasource --key metrics --agent-json` or select an exact
`--node-id`. Reverse traversal returns referring queries/panels/dashboards/alerts with evidence
pointers; ambiguous matches, unresolved edges and truncated discovery remain visible.
