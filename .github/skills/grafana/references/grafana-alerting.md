# Grafana 13 unified alerting as code

`stack-profile` owns the current minor. Confirm the exact target patch against the current vendor
advisory before a security verdict; neither a major/minor label nor an old QA result establishes a
security floor. Inspect alert-author and datasource grants separately; version evidence alone does
not establish which data an author can query.

Keep one evaluation owner per rule, without duplicate rules across paths.

## The four evaluation knobs and their spellings

- **`for`** filters flapping on entry; keep-firing-for holds a clearing alert in the Recovering
  state and a re-fire during it returns to Alerting without a new notification. The provisioning
  HTTP API body spells it **`keep_firing_for`**; file-provisioning YAML and the YAML/JSON export use
  **`keepFiringFor`**.
  A wrong key is ignored, not rejected: verify the running rule's state, not the YAML, before
  trusting the filter.
- **Recovery threshold** supplies query-side hysteresis.
- **No-data and execution-error states** are a decision per rule: for a paging burn-rate rule,
  silent telemetry mapped to Normal is the false all-clear, and an erroring query mapped to Normal
  disarms the alert invisibly. In file-provisioning YAML "Normal" is spelled `OK`
  (`noDataState: NoData|Alerting|OK|KeepLast`, `execErrState: Error|Alerting|OK|KeepLast`).
  `KeepLast` preserves the previous state; it does not establish current health. Literal UI labels
  `Normal` and `Keep Last State` are invalid provisioning values.

Review all four per rule; the defaults are not a decision.

## Provisioning paths

Export endpoints (`…/export?format=yaml|json|hcl`) emit file and Terraform
formats, not HTTP API update bodies; rule API paths are in [alert operations](./alert-operations.md).
The contact point, notification policy, template, and mute-timing provisioning endpoints are
deprecated and will be removed in a future release.
Grafana-managed recording rules write their output to a Prometheus-compatible target datasource
(or the configured `default_datasource_uid`); the output name must be a valid Prometheus metric
name.

## Rule groups as code

File-provisioned resources cannot be durably edited in the UI: change the source and use the
controlled restart or hot-reload path for the target.

Paging rules carry a usable runbook link, normally in `runbook_url`.
Never place a secret in a rule, label, annotation, or tracked provider file.

## Contact points and notification policies

**Full-tree warning.** Since Grafana 13.2 an instance can hold several named notification policy
trees; each tree is its own resource, and a rule can select which tree routes it. Applying a
provisioned tree overwrites every policy in that tree. Export the full current tree immediately
before review, keep every existing branch in the proposed source, and retain the prior export for
rollback before any controlled apply.

## Change and rollback

Live Grafana-managed rule changes use [alert operations](./alert-operations.md), under the parent's
[Access and authority](../SKILL.md#access-and-authority); temporary silences use the
[silence procedure](./silences.md). Repository/provisioner-owned rules keep their source/apply path.

Submit source-managed rule-group and policy changes through a pull request that captures the target Grafana minor,
source revision, before and after export, validation result, and notification-path evidence. Roll
back by reverting the source revision through the same controlled path, then verify the prior rule
UID, policy, and contact route are active.
