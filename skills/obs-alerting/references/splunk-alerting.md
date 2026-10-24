# Splunk saved-search alerting

Exact behaviour on the target Splunk version and licence is unconfirmed until validated there. The
parent skill's rules apply unchanged: page on symptoms, every paging alert links a runbook, and an alert
never forced to fire and resolve is unverified.

## The scheduled-alert contract

Prefer scheduled over real-time: a real-time alert holds a search process open indefinitely, and
Splunk's own manual says to use a scheduled alert when possible. Reach for real-time only when
seconds change the response, and say why in the review.

```ini
# Five-minute windows with an illustrative two-minute indexing allowance.
# Choose the allowance from measured _indextime - _time for this source.
cron_schedule = */5 * * * *
dispatch.earliest_time = -7m@m
dispatch.latest_time = -2m@m
```

- **Cover event time and indexing delay.** Choose the indexing allowance from measured
  `_indextime - _time` for this source. Cover late arrivals with bounded overlap and deduplication;
  check for skipped runs and uncovered event-time intervals before claiming complete coverage.
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

`alert.suppress.fields` scopes the suppression key so one noisy service does not mute the alert
for every service. In Splunk Enterprise 10.4, `alert.suppress.group_name` can suppress other
alerts in the same group only when they have the same user owner. For example, alerts A and B owned
by the same user can share suppression; alert C owned by a different user cannot join it just by
using the same group name. A suppression period longer than the runbook's escalation time-box
hides a still-burning condition; check the pair together.

## Actions carry results outward

- **Webhook:** `alert_actions.conf` ships with `enable_allowlist = false`, so without an allowlist the
  action can post the result payload to any endpoint. Turning the
  allowlist on with only the actual approved receiver URLs enumerated is part of the alert's review here.
- **Email:** restrict allowed recipient domains; results by email is an exfiltration surface.
- Apply the fleet's redaction rules to what the search returns, not only to where it posts.

## The runbook link

Every paging alert needs a runbook link. Discover how the existing alert and notification route
carry it before changing that mechanism. A lookup is one possible pattern, not an assumed deployed
team resource or an official example:

```spl
... | lookup instructions_lookup alert_type OUTPUT runbook_url
```

If this pattern is selected, use the actual lookup name and keep its mapping with the versioned
runbook inventory so renamed links can be updated together.

## Verification, Splunk-shaped

Force the condition with a test search or fixture events and observe trigger, throttle, and action
delivery end to end; a green "search ran" is not delivery evidence. Check both per-alert throttling
and any same-owner suppression group, including its effect on other member alerts. Discover the
existing correlation layers and owners; Moogsoft may be one of them. Coordinate Splunk suppression
with those layers so the same storm is not hidden twice.
