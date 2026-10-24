# Akamai Property Manager as code — versions, activation, rollback

Apply the [parent activation/authority rules](../SKILL.md), including staging approval and human
execution. Check timings, API shapes and eligibility against the target contract before relying on them.

## The change unit: a property version

Editing a property version prepares it; activation changes staging or production:

- **Staging** activations "usually finish within 3 minutes" — smaller network, no end-user
  traffic. The human resolves the staging edge hostname (the edge hostname with `-staging` before
  the final `.net`, e.g. `<host>.edgekey-staging.net`) to an IP, then requests the **public
  property hostname** with that connection destination, preserving Host, SNI and TLS verification:
  `curl --resolve '<public-host>:443:<staging-ip>' 'https://<public-host>/<safe-path>' -D - -o /dev/null`.
  Verify `X-Akamai-Staging` in the response (`ESSL` for Enhanced TLS, `EdgeSuite` for Standard
  TLS); a request to the edge hostname tests the wrong host.
- **Production** activation first updates live-traffic servers, then the remaining network
  ("Pending - Full Rollout"); users mapped to new edge locations can still receive the previous
  configuration during rollout. Akamai can cancel if it detects a problem. The normal estimate is
  up to 15 minutes; exceptions can take up to 60 minutes: changes to more than 10 hostnames at once,
  custom/advanced configurations requiring Akamai intervention, or legacy Configuration Manager
  hostname migrations.

## Rollback — check eligibility as well as time

- **Fast Fallback, when eligible**: available for 60 minutes after full rollout. Read the current
  activation's `fallbackInfo`: `canFastFallback`, `fallbackVersion`, and `fastFallbackExpirationTime`.
  Use the returned version with `useFastFallback` on `POST /papi/v1/properties/{propertyId}/activations`
  only while eligibility and expiry permit it. First activations, hostname-set changes, and the
  documented activation exceptions cannot use Fast Fallback.
- **Unavailable or expired**: normally activate a known-good previous version and budget the full
  activation time. For a first activation with no previous version, prepare another recovery path.

## Property change packet

Include version diff, staging evidence, hostname/CP-code blast radius, exact verification check,
applicable rollback and expected duration. Prepare recovery before activation; recheck fallback
eligibility/version/expiry afterward. Production activation needs the human release owner and
`production-change-gate` (Tier 2 minimum); WAF/security changes retain their security owner.
Origin/hostname/security activations are Tier 3 access-path changes. Recovery must be eligible
Fast Fallback, tested previous-version activation, or another proven path.

## Cache purge

A purge changes what live users receive: classify it through `production-change-gate` and give
the human release owner the exact URLs, tags or CP code, method, network, expected origin load
and verification.

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
and not yet confirmed: after invalidate, a server that held the object answers `TCP_REFRESH_HIT` or
`TCP_REFRESH_MISS`; after delete, `TCP_MISS`.

## Config-as-code paths

- **PAPI** manages rule trees, versions and activations.
- **Terraform:** property provisioning requires rule format ≥ `v2023-01-05`; `cli-terraform`
  exports an existing property to configuration plus an import script. Select tooling with the
  owning team; this is an option, not a mandated replacement for Property Manager CLI.
- **Akamai CLI `property-manager`** — local snippet-based editing and the multi-environment
  pipeline workflow; current maintenance status unconfirmed.
- **Akamai Sandbox:** tests a development rule tree before activation through a local Sandbox
  Client at `http://localhost:<connector_port>`. It can support iteration; it does not replace
  approved staging validation.

## Review checklist for a property diff

- Cache-key changes (`X-True-Cache-Key` impact) and TTL changes — these move offload and can
  stampede origin on activation; state the expected offload delta.
- Origin settings (hostname, ports, SNI, timeouts) — a typo here is a total outage that staging
  won't catch if staging points elsewhere.
- Rule ordering/criteria — conflicting behaviors use the bottom-most match; complementary behaviors
  can accumulate. A child rule applies only when its parent matches.
- Behaviors that change debugging itself (Enhanced Debug key rotation, `disablePragma`, GRN) —
  check that debug access remains available after the change.
- Hostnames added/removed from the property — that is blast radius, list them in the packet.
