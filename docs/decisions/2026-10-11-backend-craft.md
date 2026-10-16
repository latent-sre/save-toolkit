# ADR: Rebuild backend-craft on the owner's decisions

- **Date:** 2026-10-11
- **Status:** accepted by the owner on 2026-10-11 (the decisions below); the implementing candidate
  awaits exact-candidate acceptance
- **Decision owner:** Save Toolkit owner

## Context

The team builds HTTP services in Python (FastAPI) and Go and publishes them as OpenAPI documents
that its UIs and automation generate clients from [sourced: owner]. Before this change,
`backend-craft` covered FastAPI only: no reference, asset, or rule addressed Go [verified]. The
owner asked for a fresh start: no rule survives on inheritance; each is re-derived from an owner
decision, a current sourced fact, or a measured result.

Development on these services is AI-assisted [sourced: owner]. In this repository's own
measurement of `backend-craft`, a house rule written as prose landed in 2 of 30 builds, while the
same rule shipped as a contract test and handler the agent copied passed in every build that copied
them [verified: 2026-09-02/03 build-probe campaign]. A contract that matters is therefore enforced
by a check the agent runs, not by a sentence it reads.

## Decision

The owner's decisions [sourced: owner]:

1. **Two languages, one contract.** New HTTP services are FastAPI (Python) or Huma (Go), both
   code-first: the framework generates the OpenAPI document from typed handlers. An existing
   service keeps its framework and contract.
2. **The contract is a committed file with gates.** Each service commits its generated OpenAPI
   document. CI regenerates it and fails on any difference, `oasdiff` fails on breaking changes,
   and Schemathesis tests the running service against the document. A new or changed API is
   proposed first as route stubs and the document diff, approved, then implemented.
3. **OpenAPI 3.2-ready.** Documents are valid as both 3.1 and 3.2. A 3.2-only feature (sequential
   media types such as SSE `itemSchema`, the QUERY method) is used only when the tools that write
   and read the document support it.
4. **backend-craft owns the shared API contract.** RFC 9457 problems with `request_id` and
   `errors`, cursor pages, and `Idempotency-Key` writes are defined here; `frontend-craft`
   consumes them.
5. **Versioning.** Every API is served under `/v1` and gated by `oasdiff`. A second version, with
   `Deprecation` and `Sunset` headers, is introduced only when a breaking change reaches a consumer
   that is not deployed with the API.
6. **Apps take actions.** The services perform operational actions, so dry-run, plan-then-apply,
   blast-radius limits, and audit are in scope.
7. **Runtimes.** PCF, Cloud Run, Linux hosts, and Windows desktops (localhost tools).
8. **Data.** Services connect directly to PostgreSQL and SQL Server.
9. **Skill shape.** Go language guidance becomes a separate `go-craft` skill beside `python-craft`;
   `backend-craft` keeps the contract and operating rules with one reference per framework.
10. **Delivery.** A core pull request (the skill entrypoint, the OpenAPI, FastAPI and Go references,
    the starters, and evals) comes first; actions, authentication, data, runtime, and security
    references follow in their own pull requests, as does `go-craft`. Each is measured with the
    skill-creator loop in the clean room.

Rejected [sourced: owner]:

- **Spec-first Go (oapi-codegen) as the default.** Its OpenAPI 3.1 support is partial, so Go
  services would publish a different document flavour from the FastAPI services that share the
  contract. An existing spec-first service keeps its generator.
- **OpenAPI 3.2 as the emitted version now.** FastAPI, Huma, and openapi-typescript did not
  advertise 3.2 support when checked on 2026-10-11.
- **Dropping `/v1` for internal tools.** Scripts and automation call the action-taking tools, and
  open browser tabs and rolling deploys mix old and new versions even for a same-team UI.
- **GraphQL in the core.** The team runs none today; it stays allowed and can return as a
  follow-up reference.
- **Building on PR #362.** The owner is not merging it; actor attribution is re-derived in the
  actions follow-up.

## Consequences

- An agent changing an API produces a document diff a human approves before the implementation,
  and cannot change the contract silently: the drift check fails first.
- Go and Python services present the same problem, page, and header shapes, so one generated
  client pattern serves both.
- The authentication follow-up is written for standard OIDC/JWT validation; the team's identity
  provider is recorded in `stack-profile` once the owner confirms it.
- Until their follow-ups land, the existing API-writes, background-work, and consuming-APIs
  references carry over unchanged and are listed in the roadmap for re-derivation.

## Owner amendment — 2026-10-12

Amended: 2026-10-12 — decision owner narrowed existing-service contract scope.

The owner approved narrowing the first-touch requirements for existing services [sourced: owner].
This amends decisions 2 and 5 and their consequences: new HTTP services retain the full committed
OpenAPI document and gate standard. Existing services preserve their canonical specification
format/location, contract and equivalent checks. Missing service-wide documentation or CI adoption
is a separately scoped task, not automatic work in a bounded API change. The change still updates
existing contract documentation, verifies changed behaviour and discloses missing contract or
compatibility evidence. Existing authentication, contract-change approval and versioning obligations
remain in force.

## Owner amendment — 2026-10-12: internal identity and optional examples

Amended: 2026-10-12 — decision owner confirmed corporate SSO and optional starter examples.

The owner confirmed corporate SSO for internal tools and approved simplifying the starter
packaging [sourced: owner]. Shared web services retain authentication and object authorization;
the SSO vendor and protocol are not selected here. Common HTTP helpers and optional bearer
adapters are separate references. Native framework and existing identity implementations may
satisfy the same contract; copying the example application is optional. Applicable acceptance
checks and new-service CI delivery remain required.

## Review amendment — 2026-10-13

Amended: 2026-10-13 — review reconciled the Consequences section with the streamlined references.

The Consequences statement that the API-writes, background-work and consuming-APIs references
"carry over unchanged" no longer holds: those references were streamlined in the same change
that made the starters optional and the contract tests reusable, and the streamlined text is
now their current form. The 2026-10-12 amendments above are unaffected: existing services keep
their canonical specification and checks, and new HTTP services retain the full committed
document and gate standard. No decision in the Decision section is changed by this amendment.

## Owner amendment — 2026-10-16: established stack and engineering judgment

The owner clarified that FastAPI is the current backend framework and other framework choices
remain open; PostgreSQL and SQL Server remain the datastore choices [sourced: owner].
The requested standard for the remaining guidance is experienced senior engineering judgment.

This supersedes the universal framework/API prescriptions in decisions 1–5 and their delivery
consequences: Huma, fixed URL/error/page/header shapes, a particular OpenAPI artifact layout,
versioning scheme and test packages are options selected for a service's consumers and risks.
Existing consumer contracts, identity integrations (including established corporate SSO), security
controls and applicable checks remain obligations of those services. This does not authorize their
removal, production changes or a framework migration during unrelated work.

Backend guidance now states the engineering bar and conditional implementation reminders.
Frontend guidance consumes the actual service contract. Build fixtures state their own specific
contracts so their existing checks do not manufacture team-wide policy. This amendment also updates
the API-binding clauses of the two frontend decisions from 2026-10-11; their visual and frontend
framework decisions are unchanged. The implementing candidate still requires exact-revision acceptance.
