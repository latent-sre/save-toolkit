# mPulse RUM — reading real-user evidence

## What it measures

Boomerang browser beacons feed mPulse aggregates and its REST/JSON Query API:

- **Back-End Time:** navigation start to first response byte. **Front-End Time:** first response
  byte through onload/page-ready, including asset fetches and browser execution.
- **Core Web Vitals:** LCP, INP (responsiveness), CLS. Custom timers/metrics require confirmed
  instrumentation on the target site.
- **Waterfall:** uses Resource Timing for object-level DNS, TCP, TLS, request, and response durations.

## Diagnosing a regression — the slicing method

Compare equal-duration windows across browser, OS, device, network, geography, and ISP populations:

| Change | Discriminating evidence |
|---|---|
| Back-End rises, Front-End flat | Property activations, Traffic by Hostname offload, origin telemetry, or Origin Time timer when instrumented. Regional/ISP skew points to network/edge path; uniform rise leaves edge, origin, and traffic-mix changes open (`turnAroundTimeMSec` does not isolate origin latency). |
| Front-End rises, Back-End flat | Waterfall separates asset network/server waits from JS, third-party tags, and rendering. A fast base document does not clear servers handling later asset requests. |
| Both rise | Shared delivery dependencies, traffic mix, or page/instrumentation changes; compare base-document and asset timings. |

## Boundaries

- Flat sampled RUM cannot clear a failing synthetic journey: failed sessions may emit no beacon.
  Compare URL/journey, window, geography/device mix, and beacon volume against request logs.
- Per-beacon edge cache hit/miss attribution is unconfirmed; use DataStream 2 for cache rates.
