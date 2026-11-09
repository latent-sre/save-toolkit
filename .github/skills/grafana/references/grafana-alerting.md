# Grafana 13 unified alerting as code

Alert rules are independent resources, not legacy per-panel dashboard alerts.

`stack-profile` owns the current minor. Confirm the exact target patch against the current vendor
advisory before a security verdict; neither a major/minor label nor an old QA result establishes a
security floor. Inspect alert-author and datasource grants separately; version evidence alone does
not establish which data an author can query.

Grafana evaluates Grafana-managed rules; Prometheus-family backends store/evaluate datasource-managed
rules. Keep one evaluation owner per rule, without duplicate rules across paths.

## The four evaluation knobs, and the spellings that fail to load

- **`for`** filters flapping on entry; keep-firing-for holds a clearing alert in the Recovering
  state and a re-fire during it returns to Alerting without a new notification. The provisioning
  HTTP API body spells it **`keep_firing_for`**; file-provisioning YAML and the YAML/JSON export use
  **`keepFiringFor`**.
  Verify the running rule's state, not the YAML, before trusting the filter.
- **Recovery threshold** supplies query-side hysteresis. Choose it from the signal/response intent
  when threshold oscillation causes noise.
- **No-data and execution-error states** are a decision per rule: for a paging burn-rate rule,
  silent telemetry mapped to Normal is the false all-clear, and an erroring query mapped to Normal
  disarms the alert invisibly. In file-provisioning YAML "Normal" is spelled `OK`
  (`noDataState: NoData|Alerting|OK|KeepLast`, `execErrState: Error|Alerting|OK|KeepLast`).
  `KeepLast` preserves the previous state; it does not establish current health. Literal UI labels
  `Normal` and `Keep Last State` are invalid provisioning values.

Review all four per rule; the defaults are not a decision.

## Provisioning paths

Three as-code mechanisms: file provisioning under `provisioning/alerting/`, Terraform, and the
provisioning HTTP API. Export endpoints (`…/export?format=yaml|json|hcl`) emit file and Terraform
formats, not HTTP API update bodies; rule API paths are in [alert operations](./alert-operations.md).
The contact point, notification policy, template, and mute-timing provisioning endpoints are
deprecated and will be removed in a future release. Pin the mechanism per environment.
Grafana-managed recording rules can query any alerting-compatible source, but write their output
to a Prometheus-compatible target datasource (or the configured `default_datasource_uid`); the
output name must be a valid Prometheus metric name. The one-owner rule applies.

## Rule groups as code

File-provisioned resources cannot be durably edited in the UI: change the source and use the
controlled restart or hot-reload path for the target. Group rules that share an evaluation interval,
keep stable rule and folder identifiers, and version-control the exported YAML or JSON. Record each
group's folder UID, interval, rule UIDs, source path, and evaluation owner in the team's own inventory.

Paging rules carry a usable runbook link, normally in `runbook_url`. Use the labels and annotations
required by the actual notification route; this reference does not establish a team-wide label schema.
Never place a secret in a rule, label, annotation, or tracked provider file.

## Contact points and notification policies

Keep runbook links/measured values in rule annotations; contact-point templates format those facts
rather than recomputing them independently.

**Full-tree warning.** Since Grafana 13.2 an instance can hold several named notification policy
trees; each tree is its own resource, and a rule can select which tree routes it. Applying a
provisioned tree overwrites every policy in that tree. Export the full current tree immediately
before review, keep every existing branch in the proposed source, and retain the prior export for
rollback before any controlled apply. Record each route's matchers, contact point, timing, and owner
in the team's own inventory.

Test the full path with a controlled non-production rule: evaluation, firing, policy match, contact
point, correlation, acknowledgement, resolution, and runbook link.

## Change and rollback

Live Grafana-managed rule changes use [alert operations](./alert-operations.md), under the parent's
[Access and authority](../SKILL.md#access-and-authority); temporary silences use the
[silence procedure](./silences.md). Repository/provisioner-owned rules keep their source/apply path.

Submit source-managed rule-group and policy changes through a pull request that captures the target Grafana minor,
source revision, before and after export, validation result, and notification-path evidence. Roll
back by reverting the source revision through the same controlled path, then verify the prior rule
UID, policy, and contact route are active.
