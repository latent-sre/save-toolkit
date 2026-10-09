# Grafana 13 unified alerting as code

Alert rules are independent operational resources, not legacy per-panel dashboard alerts. Rule
groups, notification routing, and runbook metadata get the same review as application code.

## Contents

- [Evaluation knobs](#the-four-evaluation-knobs-and-the-spellings-that-fail-to-load)
- [Provisioning](#provisioning-paths)
- [Rule groups](#rule-groups-as-code)
- [Notification policies](#contact-points-and-notification-policies)
- [Review and rollback](#review-and-rollback)

`stack-profile` owns the current minor. Confirm the exact target patch against the current vendor
advisory before a security verdict; neither a major/minor label nor an old QA result establishes a
security floor. Inspect alert-author and datasource grants separately; version evidence alone does
not establish which data an author can query.

Grafana-managed rules are the documented recommendation and are evaluated by Grafana; data
source-managed rules are stored and evaluated in a Prometheus-family backend. Choose one evaluation
owner per rule and never duplicate a rule in both paths.

## The four evaluation knobs, and the spellings that fail to load

- **`for`** filters flapping on entry; keep-firing-for holds a clearing alert in the Recovering
  state and a re-fire during it returns to Alerting without a new notification. The provisioning
  HTTP API body spells it **`keep_firing_for`**; file-provisioning YAML and the YAML/JSON export use
  **`keepFiringFor`**.
  Verify the running rule's state, not the YAML, before trusting the filter.
- **Recovery threshold** is hysteresis from the query side: a rule that fires above 1000 ms and
  recovers only below 900 ms cannot oscillate on a value hovering at 1000. Set it on every noisy
  latency or ratio rule; leave it off a step-function signal.
- **No-data and execution-error states** are a decision per rule: for a paging burn-rate rule,
  silent telemetry mapped to Normal is the false all-clear, and an erroring query mapped to Normal
  disarms the alert invisibly. In file-provisioning YAML "Normal" is spelled `OK`
  (`noDataState: NoData|Alerting|OK|KeepLast`, `execErrState: Error|Alerting|OK|KeepLast`).
  `KeepLast` preserves the previous state; it does not establish current health. Literal UI labels
  `Normal` and `Keep Last State` are invalid provisioning values.

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
truth that drifts from the rule.

**Full-tree warning.** Grafana treats the notification policy tree as one resource:
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

For individual live Grafana-managed rule changes, use [alert operations](./alert-operations.md);
who may write is set in the parent skill's [Access and authority](../SKILL.md#access-and-authority).
Repository/provisioner-owned rules keep their source/apply path; a direct API change must not
bypass that owner. Temporary silences use the [silence procedure](./silences.md).

Submit source-managed rule-group and policy changes through a pull request that captures the target Grafana minor,
source revision, before and after export, validation result, and notification-path evidence. Roll
back by reverting the source revision through the same controlled path, then verify the prior rule
UID, policy, and contact route are active.
