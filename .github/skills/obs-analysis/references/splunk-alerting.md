# Splunk saved-search alerting

Apply the [parent alerting and paging rules](../SKILL.md#2-alerting-slisslos-and-scheduled-work-freshness).

## Scheduled-alert contract

```ini
# Five-minute window with a 2m indexing-lag offset (size from _indextime - _time).
cron_schedule = */5 * * * *
dispatch.earliest_time = -7m@m
dispatch.latest_time = -2m@m
```

- Handle late arrivals with bounded overlap/deduplication; check skipped runs and event-time gaps
  before claiming complete coverage. **Timezone:** Splunk Cloud evaluates cron in UTC; Splunk
  Enterprise uses the search head's timezone.
- Trigger conditions use `counttype` (`always` or `custom` with `relation` and `quantity`) **or**
  `alert_condition` (secondary search firing on non-empty results); set only one. `alert_type`,
  `alert_comparator`, and `alert_threshold` do not configure anything in `savedsearches.conf`.
  `alert.digest_mode` selects whole-result-set vs. per-result actions.

## Throttling

```ini
alert.digest_mode = 0
alert.suppress = 1
alert.suppress.period = 30m
alert.suppress.fields = service,alert_type
```

Field-based suppression works only on per-result alerts (`alert.digest_mode = 0`); digest alerts
throttle by time alone, muting other services. `alert.suppress.group_name` shares suppression only
across alerts with the same user owner. Compare suppression duration against runbook escalation
timelines so continuing burn is not hidden.

## Actions and verification

- **Webhook / Email:** On Splunk Enterprise, `alert_actions.conf` defaults `enable_allowlist = false`
  — require enabling it with only approved receiver URLs, and restrict email recipient domains.
  Apply redaction rules to search results as well as notifications.
- Verify trigger, per-alert/group throttling, and actual notification delivery (and coordinate with
  Moogsoft/correlation layers so suppression does not hide a storm twice).
