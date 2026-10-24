# Splunk saved-search alerting

Apply the [parent verification and paging rules](../SKILL.md). Target version/licence behavior
remains unconfirmed until validated.

## The scheduled-alert contract

Prefer scheduled alerts: real-time holds a search process open indefinitely. Justify real-time
when seconds materially change the response.

```ini
# Five-minute windows with an illustrative two-minute indexing allowance.
# Choose the allowance from measured _indextime - _time for this source.
cron_schedule = */5 * * * *
dispatch.earliest_time = -7m@m
dispatch.latest_time = -2m@m
```

- Measure source indexing delay (`_indextime - _time`); handle late arrivals with bounded overlap
  and deduplication. Check skipped runs and event-time gaps before claiming complete coverage.
- **Timezone:** Splunk Cloud evaluates cron in UTC; Splunk Enterprise uses the search head's
  timezone. Record which applies next to every schedule.
- Trigger conditions are `counttype` with `relation` and `quantity`, or `alert_condition`, a
  secondary search that replaces the trio when set; `alert_type`, `alert_comparator`, and
  `alert_threshold` are the REST API's names and configure nothing in the file.
  `alert.digest_mode` decides whole-result-set versus per-result actions.

## Throttling is part of the design

```ini
alert.suppress = 1
alert.suppress.period = 30m
# Required for per-result throttling:
alert.suppress.fields = service,alert_type
```

`alert.suppress.fields` prevents one service muting all others. In Enterprise 10.4,
`alert.suppress.group_name` shares suppression only among alerts with the same user owner; a matching
group name alone is insufficient. Compare suppression duration with the runbook escalation time-box
so continuing burn is not hidden.

## Actions carry results outward

- **Webhook:** `alert_actions.conf` defaults `enable_allowlist = false`, permitting arbitrary
  endpoints. Include enabling it with only actual approved receiver URLs in the alert review.
- **Email:** restrict allowed recipient domains; results by email is an exfiltration surface.
- Apply the fleet's redaction rules to what the search returns, not only to where it posts.

## The runbook link

Discover the existing paging-runbook link mechanism. This lookup is an optional pattern, neither
an assumed deployed resource nor an official example:

```spl
... | lookup instructions_lookup alert_type OUTPUT runbook_url
```

If selected, use the actual lookup name and version its mapping with the runbook inventory.

## Verification, Splunk-shaped

Using test searches/fixtures under the parent safeguards, observe trigger, throttle and actual
notification delivery; search success alone is insufficient. Check per-alert and same-owner group
suppression, including other members. Discover correlation layers/owners (possibly Moogsoft) and
coordinate suppression to avoid hiding the storm twice.
