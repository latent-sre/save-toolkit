---
name: akamai-edge
description: >-
  Akamai edge work in three lanes — triage (edge vs origin, Reference # error strings, cache
  status, WAF denials, DataStream 2), delivery config (Property Manager versions, staging-first
  activation, fast fallback), and mPulse RUM (network-side vs app-side slowdowns). Triggers: 'is
  it the CDN or the origin', 'Reference #9.', 'is the WAF blocking real users', 'mPulse shows
  slow pages'. Ownership map only—not a load: obs-logs owns backend log queries; an actively
  firing alert stays with sre.
compatibility: Requires Akamai Control Center access; DataStream 2 queries run in the configured log backend
---

# Akamai edge — triage, delivery config, RUM

We are Akamai customers, not Akamai operators: our lane is our properties' configuration, our
security policies, and the evidence the portal and DataStream 2 expose. The edge network itself is
Akamai's platform — a suspected platform-wide Akamai problem is an escalation to Akamai support
with evidence, not something to debug past the portal.

## The first question: which side of the edge?

Every "site is slow / erroring" report crosses Akamai twice — client→edge and edge→origin — and the
fix differs completely by leg. Establish the leg **before** hypothesizing:

1. **An Akamai error page with `Reference #…`** → decode it in Edge Diagnostics' Translate Error
   String **promptly** — the logs behind a reference number survive roughly 6–24 hours
   [sourced: techdocs.akamai.com/edge-diagnostics/docs/translate-error-string].
2. **No reference number** → Edge Diagnostics' Get Error Statistics splits errors into the
   client→edge and edge→origin legs per URL/CP code; URL Health Check bundles grep + dig + curl +
   MTR for one URL in one job [sourced: techdocs.akamai.com/edge-diagnostics/docs/get-error-statistics,
   …/url-health-check].
3. **Cache behavior in question** → read the cache-status response headers via the debug-header
   mechanism the property actually supports (Enhanced Debug vs legacy Pragma — the reference
   explains which and why it changed).
4. **Sustained or fleet-wide questions** → DataStream 2 fields (`cacheStatus`,
   `turnAroundTimeMSec`, `errorCode`) in the configured log backend, and the Traffic report for
   offload trends.

Edge-side evidence (WAF deny, cache misconfiguration, edge 5xx) stays in this skill's lanes;
origin-side evidence (edge→origin errors, healthy edge with slow turnaround) hands back to the
`sre` agent's app/platform investigation with the leg finding attached.

## Three lanes, three authority postures

- **Triage is read-only, portal-first.** Edge Diagnostics, Web Security Analytics, Reporting, and
  DataStream 2 queries change nothing. Debug-header requests against production URLs are ordinary
  HTTP reads — but from this fleet they are **recommend-for-human** commands, like every network
  probe.
- **Delivery config is change-managed work.** A property version edit is Tier 1 (prepare); any
  activation — staging included — is a live change with an approval gate and a named rollback
  (fast fallback or previous-version activation). Production activation additionally runs through
  `production-change-gate` with a human release owner.
- **WAF policy changes are security changes.** Evidence of a false positive goes to the human
  security policy owner with the sampled requests attached; this fleet never loosens a protection
  itself.

## Read the reference before acting

| Need | Reference |
|---|---|
| Edge vs origin evidence: Edge Diagnostics, reference numbers, cache status, debug headers, DataStream 2, offload reports, WAF events | [Edge triage](./references/edge-triage.md) |
| Property Manager change flow: versions, staging/production activation, fast fallback, PAPI/Terraform/CLI, Sandbox | [Property config](./references/property-config.md) |
| Real-user monitoring: beacons, Core Web Vitals, back-end vs front-end time, slicing a regression | [mPulse RUM](./references/mpulse-rum.md) |

## Handoffs

An actively firing alert or live user impact belongs to the `sre` agent — send the leg finding
(edge vs origin), the exact portal tool and result, and timestamps. A recurring query, missing
alert, or detection gap goes to the `observability-engineer` agent. A property change that is ready
to propose goes to the human release owner as a prepared version with diff, blast radius,
verification, and the fast-fallback/previous-version rollback stated. New durable operational facts
route to `scribe` through the operational-learning disposition path.
