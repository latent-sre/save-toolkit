---
name: akamai-edge
description: >-
  Akamai edge work in three lanes — triage (edge vs origin, Reference # error strings, cache
  status, WAF denials, DataStream 2), delivery config (Property Manager versions, staging-first
  activation, fast fallback), and mPulse RUM (network-side vs app-side slowdowns). Triggers: 'is
  it the CDN or the origin', 'an Akamai error page with Reference #[n].[hex].[epoch].[hex]', 'is
  the WAF blocking real users', 'mPulse shows slow pages'. Not for backend log queries (obs-analysis)
  or a firing alert (incident-investigation).
compatibility: Requires Akamai Control Center access; DataStream 2 queries run in the configured log backend
argument-hint: "[the edge, CDN, WAF, or RUM problem]"
---

# Akamai edge — triage, delivery config, RUM

We are Akamai customers, not Akamai operators: our scope is our properties' configuration, our
security policies, and the evidence Control Center and DataStream 2 expose. A suspected
platform-wide Akamai outage is an escalation to Akamai support with evidence, not something to
debug past the portal.

## Which side of the edge?

Establish which hops of the request path were exercised: client/DNS/TLS, edge/cache/WAF, and
origin. Not every request reaches origin; a child or parent cache hit is served at the edge.
Decode any `Reference #…` promptly while its edge logs remain available.

## Three lanes, three authority postures

- **Triage is read-only, portal-first.** Edge Diagnostics, Web Security Analytics, Reporting, and
  DataStream 2 queries change nothing. Production debug-header requests stay **recommend-for-human**
  so the human runs them with their own debug token.
- **Delivery config is change-managed work.** Editing a property version is Tier 1 (prepare); any
  activation (staging or production) or cache purge is a live change requiring an approval gate and
  rollback/recovery path, with production routed through `production-change-gate` and a human
  release owner.
- **WAF policy changes are security changes.** Send false-positive evidence and sampled requests to
  the human security policy owner; never loosen a protection directly.

## Reference router

| Need | Reference |
|---|---|
| Edge vs origin evidence: Edge Diagnostics, reference numbers, cache status by hop, debug headers, DataStream 2 SPL, offload reports, WAF events | [Edge triage](./references/edge-triage.md) |
| Property Manager change flow: versions, staging/production activation, fast fallback, config-as-code, diff checklist | [Property config](./references/property-config.md) |
| Cache purge: invalidate vs delete, scope, network, origin load | [Cache purge](./references/property-config.md#cache-purge) |
| Real-user monitoring: beacons, Core Web Vitals, back-end vs front-end time slicing | [mPulse RUM](./references/mpulse-rum.md) |
