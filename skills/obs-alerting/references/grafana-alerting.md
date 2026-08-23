# Grafana 13 unified alerting as code

Alert rules are independent operational resources, not legacy per-panel dashboard alerts. Keep rule
groups, notification routing, and runbook metadata under review with the same rigor as application code.

## Contents

- Primary sources
- The evaluation lifecycle — design every rule around all four knobs
- Provisioning paths and recording rules
- Rule groups as code
- Contact points and notification policies
- Review and rollback

## Primary sources

Grafana documentation was reviewed 2026-07-14 and extended 2026-08-07 through indirect retrieval;
the vulnerability sources were reviewed directly 2026-08-22:

- `[sourced]` [Configure alert rules](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/)
- `[sourced]` [Use configuration files to provision alerting resources](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/)
- `[sourced]` [Labels and annotations](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rules/annotation-label/)
- `[sourced]` [Alert rule evaluation](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/) and its state/no-data subpages
- `[sourced]` [Grafana CNA record for CVE-2026-17183](https://cveawg.mitre.org/api/cve/CVE-2026-17183)
- `[sourced]` [GHSA-f74r-h7qj-c63f](https://github.com/advisories/GHSA-f74r-h7qj-c63f)

**CVE-2026-17183 — `[sourced]` (reviewed 2026-08-22).** Grafana Labs' CNA data lists affected OSS
and Enterprise ranges as `>=8.4.0,<12.3.11`, `>=12.4.0,<12.4.9`, `>=13.0.0,<13.0.7`, and
`>=13.1.0,<13.1.4`. The fixed patch boundaries inferred from those exclusive upper bounds are
12.3.11, 12.4.9, 13.0.7, and 13.1.4. The unreviewed GitHub advisory still lists affected and
patched versions as unknown, so do
not turn 13.2.0 into a universal security floor. QA is verified at 13.1.4 Enterprise and outside
the CNA ranges; production is known only as 13.1.x, so its exact patch remains `[unverified]`.
Until production is confirmed at 13.1.4 or later, treat **alert-rule edit rights as datasource read
rights** — a folder where many people can author rules is a folder where all of them can read every
datasource the rules can reach.

Grafana documents Grafana-managed rules as the recommended option; they can query supported backend
data sources and are evaluated by Grafana, while data source-managed rules are supported for compatible
Prometheus-family backends and are stored/evaluated there. Verify target support and choose one
evaluation owner—never duplicate the same rule in both paths.

## The evaluation lifecycle — design every rule around all four knobs

- **Pending period (`for`)**: the condition must hold the whole period before Pending → Alerting
  and notification routing — the flap filter on entry.
- **`keep_firing_for`**: when the condition clears while Alerting, the instance enters a
  **Recovering** state for that duration before Normal + resolved notification; a re-fire during
  Recovering returns to Alerting **without a new notification** — the flap filter on exit. Zero
  skips Recovering. `[sourced: state-and-health page]` The provisioning/HTTP-API key is camelCase
  **`keepFiringFor`** *[sourced: alerting-provisioning reference example, re-checked 2026-08-19]*,
  and an open upstream bug reports file provisioning failing to apply it (value stays 0 after
  export + reload — grafana/grafana #109367) — verify the running rule's state, not just the
  YAML, before trusting the flap filter.
- **Recovery threshold** — not one of the four evaluation knobs but the same flap problem from the
  query side: "the alert returns to the Normal or Recovering state only after the recovery
  threshold is crossed." A rule that fires above 1000 ms and recovers only below 900 ms cannot
  oscillate on a value hovering at 1000 — hysteresis that `for` and `keep_firing_for` (which are
  time-based) do not give you. Set it on the threshold expression of every latency/ratio rule
  whose input is noisy; leave it off where the signal is a step function. *[sourced: Grafana
  alerting queries-and-conditions; reviewed 2026-08-21]*
- **No-data state**: map to No Data (default — fires a `DatasourceNoData` alert), Alerting,
  Normal, or Keep Last State. Choose deliberately per the parent skill's missing-data rule: for a
  paging burn-rate rule, silent-telemetry-means-Normal is the false all-clear.
- **Execution-error state**: Error/Alerting/Normal/Keep Last State — same deliberateness; an
  erroring query that maps to Normal disarms the alert invisibly.

Review all four per rule; the defaults are not a decision. In file-provisioning YAML the
"Normal" option is spelled `OK` (`noDataState: NoData|Alerting|OK`,
`execErrState: Error|Alerting|OK`) and `KeepLast` is absent from the file-provisioning enum — a
generated YAML carrying `Normal` or `Keep Last State` fails to load *[sourced: file-provisioning
page, re-checked 2026-08-19]*.

## Provisioning paths and recording rules

Three documented as-code mechanisms — file provisioning (`provisioning/alerting/`), Terraform
(built on the HTTP API), and the Alerting Provisioning HTTP API; export endpoints
(`…/export?format=yaml|json|hcl`) emit provisioning-ready formats, but **the export JSON is not
accepted by the HTTP API update endpoints** (different schemas). No official page crowns one
mechanism as recommended, and the current provisioning HTTP API docs sit under an `api-legacy`
path with a deprecation pointer toward the App Platform APIs — pin the mechanism per environment
and record it. `[sourced: set-up/provision-alerting-resources pages]`

Grafana-managed **recording rules** exist against any alerting-compatible data source (output name
must be a valid Prometheus metric name), alongside data-source-managed recording rules in the
Mimir/Loki ruler — same one-evaluation-owner rule as alerts. `[sourced: create-recording-rules pages]`

## Rule groups as code

For self-managed Grafana, file-provisioned alert resources live under `provisioning/alerting`. Group
rules that share an evaluation interval, keep stable rule/folder identifiers, and version-control the
exported YAML or JSON. File-provisioned resources cannot be durably edited in the UI; change their
source and use the controlled restart or hot-reload path documented for the target.

Record the exact inventory:

| Rule group | Folder UID | Interval | Rule UID / purpose | Source path | Evaluation owner |
|---|---|---|---|---|---|
| `<service-slo>` | `<uid>` | `<interval>` | `<uid>` / `<burn pair>` | `<repo path>` | `<Grafana or backend>` |

Review every rule's query, condition, window pair, pending period, no-data state, execution-error state,
labels, summary/description, and annotations. Every rule carries a `runbook_url` annotation plus enough
service/owner/severity labels to route and investigate it. Never place a token or other secret in a
rule, label, annotation, or tracked provider file; tracked alerting configuration contains no credentials.

## Contact points and notification policies

**Notification templates are the message; annotations are the facts.** A notification template
(Go template syntax, `{{ define "name" }} … {{ end }}`) is assigned to a contact point and "changes
the title, message, and format of notifications" — it shapes what Slack or email shows, iterating
`{{ .Alerts }}` with `.Status`, `.Labels`, `.Annotations.summary`, `.CommonLabels`. An annotation
template, by contrast, fills the alert's own `summary`/`runbook_url` from query values. Keep the
division: the runbook link and the measured value live in annotations so every channel gets them;
the template only decides layout. A template that computes facts is a second source of truth that
drifts from the rule. *[sourced: Grafana alerting, template notifications; reviewed 2026-08-21]*

Contact points define where a notification can go; notification policies select contact points using
labels, grouping, and timing. Keep the route inventory explicit:

**Full-tree warning — `[sourced]`.** Grafana treats the entire notification policy tree as one resource:
you cannot provision a subset, and applying a provisioned tree overwrites all policies in that tree
(except internal policies created when a rule directly selects a contact point). Export the full current
tree immediately before review, keep every existing branch in the proposed source, review the whole
tree with its owners, and retain the complete prior export for rollback before any controlled apply.

| Match labels | Contact point | Grouping / timing | Correlation destination | Owner / test evidence |
|---|---|---|---|---|
| `<service, severity>` | `<name>` | `<group_by / intervals>` | `<Moogsoft integration>` | `<owner / test record>` |

Test the full path with a controlled non-production rule: evaluation, firing state, policy match,
contact point, correlation, acknowledgement, resolution, and runbook link. A green rule preview alone
does not prove notification delivery.

## Review and rollback

Submit rule-group and policy changes through a pull request. Capture the target Grafana minor, source
revision, before/after exported resource, validation result, and notification-path evidence. Roll back
by reverting the source revision and reapplying it through the same controlled path, then verify the
prior rule UID, policy, and contact route are active.

<!-- terminal-canary: q_oagraf_4d2b -->
