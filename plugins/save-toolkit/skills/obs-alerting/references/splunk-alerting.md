# Splunk saved-search alerting

Sources reviewed 2026-08-07: official `help.splunk.com` Alerting Manual and
`savedsearches.conf`/`alert_actions.conf` reference pages, via indirect retrieval — search
extraction and indexed snapshots, not byte-level fetches. Exact behavior on the target Splunk
version and license remains `[unverified]` until validated there. The parent skill's rules apply
unchanged: page on symptoms, every alert links a runbook, and an alert that has never been forced
to fire and resolve is unverified.

## Scheduled beats real-time — Splunk's own words

"Real-time alerts can be costly in terms of computing resources, so consider using a scheduled
alert when possible" *[sourced: Alerting Manual, alert types]*. A real-time alert holds a search
process open indefinitely; a scheduled search costs one dispatch per interval. Reach for real-time
only when seconds of latency genuinely change the response, and say why in the alert's review.

## The scheduled-alert contract (savedsearches.conf)

```ini
# run every 5 minutes over the last 5 minutes — window matches cadence
cron_schedule = */5 * * * *
dispatch.earliest_time = -5m
dispatch.latest_time = now
```

*[sourced: Alerting Manual savedsearches.conf configuration page (shape); the 5-field cron syntax
and examples from the cron-expressions page)]*

- **Window matches cadence, deliberately.** A 5-minute cron over a 1-hour window re-alerts on the
  same events eleven times; a 15-minute cron over a 5-minute window never sees two-thirds of the
  data. Mismatch is the most common silent defect in inherited alerts — check it first.
- **Timezone**: Splunk Cloud evaluates cron in UTC; Splunk Enterprise uses the search head's
  timezone *[sourced: cron-expressions page]*. Record which applies next to every schedule.
- Trigger conditions: `alert_type` (number of events/hosts/sources, or `custom` with
  `alert_condition` — a secondary search over the results), `alert_comparator` +
  `alert_threshold`. `alert.digest_mode` decides whole-result-set vs per-result actions.

## Throttling — suppression is part of the design, not a mute button

```ini
alert.suppress = 1
alert.suppress.period = 30m
alert.suppress.fields = service,alert_type   # required for per-result throttling
```

*[sourced: savedsearches.conf reference]* — `alert.suppress.fields` scopes the suppression key so
one noisy service doesn't mute the alert for every service; `alert.suppress.group_name` extends
suppression across similar alerts. A suppression period longer than the runbook's escalation
time-box hides a still-burning condition — check the pair together.

## Actions

- **Webhook**: generic HTTP POST of the result payload. `alert_actions.conf` ships with
  `enable_allowlist = false` and the official docs caution that without an allowlist the webhook
  "can then query against any endpoint, including external endpoints … that could be malicious"
  *[sourced: use-a-webhook-alert-action; alert_actions.conf]* — turning the allowlist on with the
  Moogsoft/receiver URLs enumerated is part of the alert's review checklist here, not optional
  hardening.
- **Email**: restrict allowed recipient domains (the Email Domains setting exists precisely
  because results-by-email is an exfiltration surface) *[sourced: email-notification-action]*.
- Alert actions carry query results outward — apply the fleet's redaction rules to what the search
  returns, not just to where it posts.

## Data-driving the runbook link

The parent skill requires every alert to link a runbook; in Splunk the mechanism is a lookup at
the end of the alert search:

```spl
... | lookup instructions_lookup alert_type OUTPUT runbook_url
```

The lookup mechanism (CSV/KV-store, `| lookup … OUTPUT …`) is documented *[sourced: Search Manual
lookup pages]*; this specific runbook-column pattern is a **derived pattern, not an official
example** — maintain `instructions_lookup` under version control with the runbook inventory so a
renamed runbook updates every alert at once, and remember the `obs-alerting` rule: a dead
`runbook_url` at 3 a.m. is a design defect.

## Verification, Splunk-shaped

Force the condition with a test search or fixture events and observe trigger + throttle + action
delivery end to end; a green "search ran" is not delivery evidence. For the noise review, the
correlation lane stays with Moogsoft (its reference in this skill) — Splunk-side throttling is per
alert, Moogsoft owns cross-alert dedup/correlation; don't build both for the same storm.

<!-- terminal-canary: q_oasplk_8b2e -->
