# Akamai Property Manager as code — versions, activation, rollback

Sources reviewed 2026-08-07 against official `techdocs.akamai.com` pages via indirect retrieval
(search extraction and indexed snapshots — not byte-level fetches). Re-verify timings and API
shapes against the live pages for the target contract before relying on them.

## The change unit: a property version

Properties are versioned; editing never touches live traffic — **activation** does. Activate a
version to **staging** or **production** *[sourced:
techdocs.akamai.com/property-mgr/docs/how-activation-works]*:

- **Staging** activations "usually finish within 3 minutes" — smaller network, no end-user
  traffic. Verify against staging with the staging hostname; the `X-Akamai-Staging` response
  header proves which network answered.
- **Production** activation is **two-phased**: phase 1 rolls out to live-traffic servers — but
  users mapped to fresh edge locations "may still reach Akamai servers with the previous property
  configuration" for a few minutes after phase 1 completes *[sourced: how-activation-works,
  re-checked 2026-08-19]*; phase 2 ("Pending - Full Rollout") continues to
  the rest of the network and can auto-cancel if the system detects a problem. "The total
  activation process takes up to 15 minutes on the production network." (A "under 4 minutes"
  figure circulates and likely describes phase 1 only — `[unverified]`, don't quote it.)

## Rollback — know which of the two you have

- **Fast Fallback**: for **60 minutes after an activation completes**, revert to the most recent
  previously-active version, faster than a standard activation. In PAPI it is `useFastFallback` on
  `POST /papi/v1/properties/{propertyId}/activations`, gated by `canFastFallback` (with an
  expiration timestamp) *[sourced: techdocs.akamai.com/property-mgr/reference/post-property-activations]*.
- **After the window**: rollback = a normal production activation of the previous version — plan
  for the full activation time in the rollback estimate, not the fast-fallback time.

A production-change packet for a property change therefore states: the version diff, staging
evidence, blast radius (hostnames/CP codes on the property), verification (the exact debug-header
or report check), **which rollback applies right now**, and the fast-fallback expiry once
activated. Production activation is Tier 2 minimum, human release owner, through
`production-change-gate`; a WAF/security-config change is a security change with its own owner.

## Config-as-code paths

- **PAPI** (Property Manager API) — the programmatic interface for rule trees, versions, and
  activations; everything else is built on it *[sourced: techdocs.akamai.com/property-mgr/reference/api]*.
- **Terraform** — the actively versioned path: the Akamai provider's property provisioning
  requires rule format ≥ `v2023-01-05`, and **`cli-terraform` exports an existing property to
  Terraform config plus an import script** — the sane on-ramp for a property that grew up in the
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
- Rule ordering/criteria — Property Manager rules cascade; a new rule above an existing one can
  shadow it silently.
- Behaviors that change debugging itself (Enhanced Debug key rotation, `disablePragma`, GRN) —
  losing debug access mid-incident is a self-inflicted wound.
- Hostnames added/removed from the property — that is blast radius, list them in the packet.
