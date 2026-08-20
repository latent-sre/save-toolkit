---
name: pcf-deploy
description: >-
  Prepare a human-executed VMware TAS/Cloud Foundry application deployment, blue-green cutover,
  rolling/canary rollout, scale change, or rollback plan. Triggers: "deploy this app to PCF", "design
  a blue-green deploy", "scale this PCF app". Use only when explicitly requested; do not decide
  release readiness or execute foundation changes.
compatibility: Requires the cf CLI v8 and authorized access to the target PCF foundation/space
# Deploys are human-initiated: invoke explicitly as `/save-toolkit:pcf-deploy`; never auto-load.
disable-model-invocation: true
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# PCF / TAS deployment planning

<!-- deploy-plan canary: pd_4c91 — quoted output proves this manual-only skill loaded -->

Produce an exact plan and evidence checklist. Agents never execute deployment. A named human release
owner acts only after the release- and production-change packets approve the exact artifact, target,
commands, verification, and rollback/recovery. If either packet is absent or stale, stop with the
missing evidence; do not load or run those sibling gates.

## Establish the target

Record before writing commands:

- foundation/API identity, org, space, app/route, and human actor;
- `cf` CLI and CAPI versions plus target feature/configuration evidence;
- reviewed SHA, immutable artifact, manifest and variable-file diff, buildpacks/stacks, services, routes,
  processes, health checks, scale, and current deployment state;
- release and production-change approval references;
- success signals, observation window, abort thresholds, and rollback/recovery owner.

Keep secrets out of manifests, plans, prompts, and command arguments. `cf env`, service-key output, and
credential reads are human-only because they can expose secrets.

**Starter:** adapt [manifest.yml](./assets/manifest.yml) after reconciling its names, routes, buildpack,
services, health checks, scale, and environment with the reviewed target.

## Build the plan

1. Choose the strategy from [deployment strategies](./references/deployment-strategies.md). Treat target
   support as `[unverified]` until version and non-production evidence establish it.
2. Show the exact manifest/variable diff and commands in execution order. Identify which command changes
   traffic or app lifecycle; a route map is not an atomic cutover.
3. State the human actor and approval record beside the effect, not only in a preamble.
4. Define a verification after each meaningful step and a stop condition before the next.
5. Use [rollback boundaries](./references/rollback-boundaries.md) to list what rollback does and does not
   restore. Data/schema, service bindings, routes, scale, and external side effects require separate
   recovery decisions.
6. For environment or scale changes, use [configuration and scaling](./references/configuration-and-scaling.md)
   to choose restart, restage, or scale behavior without inventing a universal rule.

## Rollback truth

A revision or route rollback is not whole-system time travel. It may restore a droplet/process
configuration or traffic target while leaving migrations, data writes, messages/webhooks, bindings,
routes, scale, health-check configuration, or downstream consumer effects unchanged. Rollbackability
also depends on retained artifacts/droplets, not merely a revision number. Keep the claim
`[unverified]` until rehearsed for the exact target.

## Verification

After the human acts, capture the command result and independently observe app/process state, route
mappings, artifact/revision identity, health checks, traffic, errors, latency, saturation, and the
business journey. Missing telemetry is an abort condition, not a green result. Preserve evidence and
taint labels through the handoff.

## Output contract

```text
Deployment: <artifact/reviewed SHA> -> <foundation/org/space/app>
Authority: <release packet — production-change packet — human executor>
Versions/evidence: <cf CLI — CAPI — target feature proof and labels>
Manifest/config diff: <reviewed paths and material values; no secrets>
Strategy and steps: <ordered command — actor — expected effect — verification — stop condition>
Traffic transition: <when both versions receive traffic; exact cutover point>
Rollback/recovery: <exact inverse/recovery — retained prerequisite — exclusions — owner>
Post-change verification: <signals — observation window — recorded result>
Unverified claims/blockers: <each missing target fact or approval>
```

## Conditional references

| Need | Read |
|---|---|
| Blue-green, rolling, canary, manifest-name selection, cancellation, or revisions | [Deployment strategies](./references/deployment-strategies.md) |
| Revision contents, retention, data/schema effects, or rollback exclusions | [Rollback boundaries](./references/rollback-boundaries.md) |
| Environment changes, restart/restage, horizontal/vertical scale, or credential handling | [Configuration and scaling](./references/configuration-and-scaling.md) |
