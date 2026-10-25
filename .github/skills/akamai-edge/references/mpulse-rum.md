# mPulse RUM — reading real-user evidence

## What it measures

Boomerang browser beacons feed mPulse aggregates and its REST/JSON Query API. Relevant distinctions:

- Back-End Time: navigation start to first response byte. Front-End Time: that byte through
  onload/page-ready, including asset fetches and browser work.
- Core Web Vitals: LCP, INP, CLS; INP measures responsiveness. Custom timers/metrics require actual
  instrumentation rather than assumed availability.
- Waterfall uses Resource Timing for object-level DNS, TCP, TLS, request and response durations.

## Diagnosing a regression — the slicing method

Compare equal-duration windows and browser/OS/device/network/geography/ISP populations. A bot wave,
campaign or instrumentation change can change the aggregate without a site regression.
These are hypotheses to test, not causal verdicts:

| Change | Discriminating evidence |
|---|---|
| Back-End rises, Front-End flat | Property activations, Traffic by Hostname offload, origin telemetry or the Origin Time timer when available. Local geography/ISP impact suggests a path; uniform impact leaves edge, origin and population changes open. DataStream `turnAroundTimeMSec` does not isolate origin latency. |
| Front-End rises, Back-End flat | Waterfall separates asset network/server waits from JS, tags and rendering. A fast base document does not clear servers handling later requests. |
| Both rise | Shared delivery dependencies, traffic mix, page or instrumentation changes; compare document and later-asset request evidence |

## Boundaries

- Flat sampled RUM cannot clear a failing synthetic journey. Compare URL/journey, window,
  geography/device/network mix and beacon count/freshness; failed sessions may send no beacon.
  Corroborate through request logs or another journey check. `obs-alerting` owns ThousandEyes checks.
- Per-beacon edge cache hit/miss attribution is unconfirmed; use DataStream 2 instead of promising it.
- Redact sensitive URLs/session attributes under the fleet rules before quoting user telemetry.
