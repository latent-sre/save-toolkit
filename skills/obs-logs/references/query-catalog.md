# Team query catalog — the searches we already trust

The searches this team runs often enough to get right once. Each entry answers a stated question,
so a responder can pick by *what they need to know* rather than by remembering SPL. Read
[SPL](./spl.md) for the dialect and [local log inventory](./indexes.md) for index, sourcetype, and
field values; this file holds the assembled searches that combine them.

> **Names, locators, and query text only** — no credentials, tokens, session or user identifiers,
> customer data, or raw payloads. A query that only works with a secret pasted into it does not
> belong here; reference the access-controlled saved search instead.

Every row is `[unverified]` until a named human validates it against the live target and records
the date. A catalog entry is a starting point for investigation, never proof about production.

## The `sre` lane runs nothing here

`sre` holds no logging CLI in its allowlist, so it **recommends** a catalog entry — the exact query,
the expected shape, and what a healthy result looks like — for a human to run and paste back. That
boundary is why the "reads as" and "healthy looks like" fields matter: they let the recommending
lane interpret pasted output it could not have produced itself.

## Entry shape

Each entry carries these fields, in this order. The shape deliberately mirrors the
runbook-registry shape in the accepted SRE operational-context contract — identity, applicability,
ownership, lifecycle, and source location — so entries lift into `sre-context` as typed values when
that contract reaches real-team onboarding, instead of being rewritten.

| Field | Meaning |
|---|---|
| **Question** | What a responder wants to know, in plain English. This is the lookup key. |
| **Applies to** | Service, environment, or signal the query is valid for. |
| **Query** | The search itself, with `<placeholders>` for every inventory value. |
| **Reads as** | What the columns mean, so pasted output can be interpreted. |
| **Healthy looks like** | The result shape when nothing is wrong — the comparison that makes an unhealthy result legible. |
| **Owner** | Named human or team role accountable for the entry. |
| **Verified** | `[verified] <date> by <role>`, or `[unverified]` with what is untested. |

## Contribute an entry

Copy this template, fill every field, open a PR. No skill file changes are needed — the catalog is
data, and the query-catalog validator on the Gate A path checks the shape and the safety rules on
every push.

```markdown
### <the question, phrased as a responder would ask it>

- **Applies to:** <service / environment / signal>
- **Reads as:** <what the output columns mean>
- **Healthy looks like:** <the result when nothing is wrong>
- **Owner:** <role>
- **Verified:** [unverified]

```spl
<the query, with <placeholders> for inventory values>
```
```

## Splunk (SPL)

### Which errors started at the same time as the impact?

- **Applies to:** any service emitting structured errors to Splunk
- **Reads as:** one row per error class per minute, most recent first
- **Healthy looks like:** a flat count at the service's normal background rate, with no class appearing for the first time
- **Owner:** `<service on-call>`
- **Verified:** [unverified: target index and `error_type` extraction]

```spl
index=<app_index> earliest=-60m
| bin _time span=1m
| stats count by _time, error_type
| sort - _time
```

### Did error rate change across the deploy?

- **Applies to:** a service with a known deploy timestamp
- **Reads as:** error counts for the window before and after the change
- **Healthy looks like:** both windows within normal variation of each other
- **Owner:** `<service on-call>`
- **Verified:** [unverified: target index and deploy-time substitution]

```spl
index=<app_index> earliest=-2h
| eval phase=if(_time < strptime("<deploy_time_utc>", "%Y-%m-%dT%H:%M:%S"), "before", "after")
| stats count by phase, status
```

### Where did one request fail across services?

- **Applies to:** services that emit the shared correlation-id field
- **Reads as:** the ordered path of one request, one row per service hop
- **Healthy looks like:** every expected hop present, terminating in a success status
- **Owner:** `<service on-call>`
- **Verified:** [unverified: correlation-id field name per `indexes.md`]

```spl
index=<app_index> <correlation_field>="<request_id>" earliest=-24h
| table _time, service, status, latency_ms
| sort _time
```

### Which callers are driving the current load?

- **Applies to:** request-driven services with an access log in Splunk
- **Reads as:** request counts by caller over the window, largest first
- **Healthy looks like:** the usual caller mix; no single new caller dominating
- **Owner:** `<service on-call>`
- **Verified:** [unverified: caller field name per `indexes.md`]

```spl
index=<app_index> earliest=-30m
| stats count by <caller_field>
| sort - count
| head 20
```

## Loki (LogQL)

No entries yet. Add them under this heading using the same shape; `logql.md` owns the dialect and
`indexes.md` owns the stream selectors.

## Metrics (PromQL and WQL)

No entries yet. Metric searches belong to `obs-metrics`; add a pointer here only when a metric query
is the natural companion to a log query above, and keep the query itself in the owning skill.

## Inert canary

This token only proves the catalog loaded; it asserts nothing about a query or an index.

```text
q_ol_qcat_8c2f
```
