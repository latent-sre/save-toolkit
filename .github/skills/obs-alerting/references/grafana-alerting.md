# Grafana 13 unified alerting as code

Alert rules are independent operational resources, not legacy per-panel dashboard alerts. Rule
groups, notification routing, and runbook metadata get the same review as application code.

Grafana documentation reviewed 2026-07-14 and extended 2026-08-07 through indirect retrieval;
13.2.0 provisioning parser source rechecked 2026-09-19. The vulnerability sources below were last
reviewed directly 2026-08-22 and require a fresh check for a current security verdict: `[sourced]`
[configure alert rules](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/),
[file provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/),
[labels and annotations](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rules/annotation-label/),
[rule evaluation](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/),
[CVE-2026-17183](https://cveawg.mitre.org/api/cve/CVE-2026-17183),
[GHSA-f74r-h7qj-c63f](https://github.com/advisories/GHSA-f74r-h7qj-c63f).

`stack-profile` owns the current minor. Confirm the exact target patch against the current vendor
advisory before a security verdict; neither a major/minor label nor an old QA result establishes a
security floor. Inspect alert-author and datasource grants separately; version evidence alone does
not establish which data an author can query. Historical advisory details remain in Git history.

Grafana-managed rules are the documented recommendation and are evaluated by Grafana; data
source-managed rules are stored and evaluated in a Prometheus-family backend. Choose one evaluation
owner per rule and never duplicate a rule in both paths.

## The four evaluation knobs, and the spellings that fail to load

- **`for`** filters flapping on entry; **`keep_firing_for`** holds a clearing alert in the Recovering
  state and a re-fire during it returns to Alerting without a new notification. The file-provisioning
  and HTTP-API key is camelCase **`keepFiringFor`** *[sourced: provisioning reference, re-checked
  2026-08-19]*, and an open upstream bug (grafana/grafana #109367) reports the value staying 0 after
  export and reload, so verify the running rule's state, not the YAML, before trusting the filter.
- **Recovery threshold** is hysteresis from the query side: a rule that fires above 1000 ms and
  recovers only below 900 ms cannot oscillate on a value hovering at 1000. Set it on every noisy
  latency or ratio rule; leave it off a step-function signal *[sourced: queries and conditions,
  reviewed 2026-08-21]*.
- **No-data and execution-error states** are a decision per rule: for a paging burn-rate rule,
  silent telemetry mapped to Normal is the false all-clear, and an erroring query mapped to Normal
  disarms the alert invisibly. In file-provisioning YAML "Normal" is spelled `OK`
  (`noDataState: NoData|Alerting|OK|KeepLast`, `execErrState: Error|Alerting|OK|KeepLast`).
  `KeepLast` preserves the previous state; it does not establish current health. Literal UI labels
  `Normal` and `Keep Last State` are invalid provisioning values.
  *[sourced: Grafana 13.2.0 [file loader](https://github.com/grafana/grafana/blob/v13.2.0/pkg/services/provisioning/alerting/rules_types.go#L135)
  and [state parsers](https://github.com/grafana/grafana/blob/v13.2.0/pkg/services/ngalert/models/alert_rule.go#L67),
  checked 2026-09-19; this source check does not prove a target reload]*.

Review all four per rule; the defaults are not a decision.

## Provisioning paths

Three as-code mechanisms: file provisioning under `provisioning/alerting/`, Terraform, and the
provisioning HTTP API. Export endpoints (`…/export?format=yaml|json|hcl`) emit provisioning-ready
formats, but **the export JSON is not accepted by the HTTP API update endpoints** (different
schemas), and the provisioning HTTP API docs sit under an `api-legacy` path with a deprecation
pointer to the App Platform APIs, so pin the mechanism per environment and record it `[sourced]`.
Grafana-managed recording rules exist against any alerting-compatible source (the output name must be
a valid Prometheus metric name) under the same one-owner rule.

## Rule groups as code

File-provisioned resources cannot be durably edited in the UI: change the source and use the
controlled restart or hot-reload path for the target. Group rules that share an evaluation interval,
keep stable rule and folder identifiers, and version-control the exported YAML or JSON. Record the
inventory:

| Rule group | Folder UID | Interval | Rule UID / purpose | Source path | Evaluation owner |
|---|---|---|---|---|---|
| `<service-slo>` | `<uid>` | `<interval>` | `<uid>` / `<burn pair>` | `<repo path>` | `<Grafana or backend>` |

Every rule carries a `runbook_url` annotation plus service, owner, and severity labels sufficient to
route and investigate it. Never place a token or other secret in a rule, label, annotation, or
tracked provider file.

## Contact points and notification policies

**Notification templates are the message; annotations are the facts.** A template assigned to a
contact point shapes what Slack or email shows; the runbook link and the measured value live in the
rule's annotations so every channel gets them. A template that computes facts is a second source of
truth that drifts from the rule *[sourced: template notifications, reviewed 2026-08-21]*.

**Full-tree warning `[sourced]`.** Grafana treats the notification policy tree as one resource:
applying a provisioned tree overwrites every policy in it. Export the full current tree immediately
before review, keep every existing branch in the proposed source, and retain the prior export for
rollback before any controlled apply. Record the routes:

| Match labels | Contact point | Grouping / timing | Correlation destination | Owner / test evidence |
|---|---|---|---|---|
| `<service, severity>` | `<name>` | `<group_by / intervals>` | `<Moogsoft integration>` | `<owner / test record>` |

Test the full path with a controlled non-production rule: evaluation, firing, policy match, contact
point, correlation, acknowledgement, resolution, and runbook link. A green rule preview alone does
not prove notification delivery.

## Review and rollback

For a read-only review, inspect rule definitions and current evaluation state without forcing a
condition or sending a notification. Successful rule reads and healthy evaluations do not prove
firing/resolution or delivery. Record those checks as `[unverified]` until separately exercised.

Submit rule-group and policy changes through a pull request that captures the target Grafana minor,
source revision, before and after export, validation result, and notification-path evidence. Roll
back by reverting the source revision through the same controlled path, then verify the prior rule
UID, policy, and contact route are active.
