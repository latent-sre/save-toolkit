# Grafana 13 unified alerting as code

Alert rules are independent operational resources, not legacy per-panel dashboard alerts. Keep rule
groups, notification routing, and runbook metadata under review with the same rigor as application code.

## Primary sources

Sources reviewed 2026-07-14:

- `[sourced]` [Configure alert rules](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/)
- `[sourced]` [Use configuration files to provision alerting resources](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/)
- `[sourced]` [Labels and annotations](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rules/annotation-label/)

Grafana documents Grafana-managed rules as the recommended option; they can query supported backend
data sources and are evaluated by Grafana, while data source-managed rules are supported for compatible
Prometheus-family backends and are stored/evaluated there. Verify target support and choose one
evaluation owner—never duplicate the same rule in both paths.

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
