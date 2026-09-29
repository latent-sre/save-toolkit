# Akamai Property Manager as code — versions, activation, rollback

Sources reviewed 2026-08-07 against official `techdocs.akamai.com` pages via indirect retrieval
(search extraction and indexed snapshots — not byte-level fetches). Re-verify timings and API
shapes against the live pages for the target contract before relying on them.

## Contents

- The change unit: a property version
- Rollback — check eligibility as well as time
- Property change packet
- Cache purge
- Config-as-code paths
- Review checklist for a property diff

## The change unit: a property version

Properties are versioned; editing never touches live traffic — **activation** does. Activate a
version to **staging** or **production** *[sourced:
techdocs.akamai.com/property-mgr/docs/how-activation-works]*:

- **Staging** activations "usually finish within 3 minutes" — smaller network, no end-user
  traffic. The human resolves the staging edge hostname (the edge hostname with `-staging` before
  the final `.net`, e.g. `<host>.edgekey-staging.net`) to an IP, then requests the **public
  property hostname** with that connection destination, preserving Host, SNI and TLS verification:
  `curl --resolve '<public-host>:443:<staging-ip>' 'https://<public-host>/<safe-path>' -D - -o /dev/null`.
  Verify `X-Akamai-Staging` in the response (`ESSL` for Enhanced TLS, `EdgeSuite` for Standard
  TLS); a request to the edge hostname tests the wrong host
  *[sourced: techdocs.akamai.com/property-mgr/docs/test-https; reviewed 2026-09-09]*.
- **Production** activation first updates live-traffic servers, then the remaining network
  ("Pending - Full Rollout"); users mapped to new edge locations can still receive the previous
  configuration during rollout. Akamai can cancel if it detects a problem. The normal estimate is
  up to 15 minutes; exceptions can take up to 60 minutes: changes to more than 10 hostnames at once,
  custom/advanced configurations requiring Akamai intervention, or legacy Configuration Manager
  hostname migrations. *[sourced: [activation phases and exceptions](https://techdocs.akamai.com/property-mgr/docs/how-activation-works)]*

## Rollback — check eligibility as well as time

- **Fast Fallback, when eligible**: available for 60 minutes after full rollout. Read the current
  activation's `fallbackInfo`: `canFastFallback`, `fallbackVersion`, and `fastFallbackExpirationTime`.
  Use the returned version with `useFastFallback` on `POST /papi/v1/properties/{propertyId}/activations`
  only while eligibility and expiry permit it. First activations, hostname-set changes, and the
  documented activation exceptions cannot use Fast Fallback. *[sourced: [PAPI recovery](https://techdocs.akamai.com/property-mgr/reference/property-activation-error-handling)
  and [Fast Fallback limitations](https://techdocs.akamai.com/property-mgr/docs/how-activation-works#fast-fallback-considerations)]*
- **Unavailable or expired**: normally activate a known-good previous version and budget the full
  activation time. For a first activation with no previous version, prepare another recovery path.

## Property change packet

The packet states: the version diff, staging evidence, blast radius (hostnames/CP codes on the
property), verification (the exact debug-header or report check), **which rollback applies right
now**, and its expected duration. Prepare recovery before activation; afterward confirm current
fallback eligibility, version, and expiry. Production activation is Tier 2 minimum, with a human
release owner through `production-change-gate`; a WAF/security-config change has its own owner.
Origin, hostname, or security-config activations are Tier 3 access-path changes (proxy and
firewall in the gate's Tier 3 row); the recovery path must fit the change: eligible Fast Fallback
inside its window, a tested previous-version activation, or another proven path when neither exists.

## Cache purge

A purge changes what live users receive: classify it through `production-change-gate` and give
the human release owner the exact URLs, tags or CP code, method, network, expected origin load
and verification *[sourced: techdocs.akamai.com/purge-cache/docs/purge-methods;
…/purge-cache/reference/post-invalidate-url]*.

| Choice | Default | Why |
|---|---|---|
| Method | **Invalidate**, "the default and most popular behavior": the next request revalidates with origin (`If-Modified-Since`), and stale content can still be served if the origin is unreachable | **Delete** removes the object and "can increase the load and bandwidth on your origin more than invalidate"; keep it for content that must not be served (compliance, copyright) |
| Scope | Narrowest that covers the change: URL, then cache tag, then CP code (ARL also exists) | A wide scope revalidates everything under it at once — state the expected origin load |
| Network | `staging` to rehearse; `production` (the API default) for users | A production purge has no undo; origin refetches the content |

During an origin brownout, avoid deletion while serving stale content remains acceptable: it
removes the available copies (`TCP_REFRESH_FAIL_HIT`). If content must no longer be served, give
the responsible human/security owner a narrowly scoped deletion for approval through the change
gate, with the availability consequence explicit; invalidation can keep serving that content.
Verify with a debug request; inferred from the X-Cache definitions
`[unverified]`: after invalidate, a server that held the object answers `TCP_REFRESH_HIT` or
`TCP_REFRESH_MISS`; after delete, `TCP_MISS`.

## Config-as-code paths

- **PAPI** (Property Manager API) — the programmatic interface for rule trees, versions, and
  activations; everything else is built on it *[sourced: techdocs.akamai.com/property-mgr/reference/api]*.
- **Terraform** — the actively versioned path: the Akamai provider's property provisioning
  requires rule format ≥ `v2023-01-05`, and **`cli-terraform` exports an existing property to
  Terraform config plus an import script** — an import path for a property maintained in the
  UI *[sourced: techdocs.akamai.com/terraform/docs/set-up-property-provisioning,
  …/docs/import-and-export-assets]*. No official page crowns Terraform as "the" recommended path
  over the Property Manager CLI — `[unverified]`; choose per team and record the choice.
- **Akamai CLI `property-manager`** — local snippet-based editing and the multi-environment
  pipeline workflow; current maintenance status `[unverified]`.
- **Akamai Sandbox** — an isolated environment to test a development version of a property before
  any activation: the Sandbox CLI builds it from the property's rule tree and the local Sandbox
  Client serves it at `http://localhost:<connector_port>` *[sourced:
  techdocs.akamai.com/sandbox/docs]*. Sandbox-first beats staging-first for iteration; staging
  remains the pre-production gate.

## Review checklist for a property diff

- Cache-key changes (`X-True-Cache-Key` impact) and TTL changes — these move offload and can
  stampede origin on activation; state the expected offload delta.
- Origin settings (hostname, ports, SNI, timeouts) — a typo here is a total outage that staging
  won't catch if staging points elsewhere.
- Rule ordering/criteria — conflicting behaviors use the bottom-most match; complementary behaviors
  can accumulate. A child rule applies only when its parent matches. *[sourced: [behavior resolution](https://techdocs.akamai.com/property-mgr/docs/config-best-practices)]*
- Behaviors that change debugging itself (Enhanced Debug key rotation, `disablePragma`, GRN) —
  check that debug access remains available after the change.
- Hostnames added/removed from the property — that is blast radius, list them in the packet.
