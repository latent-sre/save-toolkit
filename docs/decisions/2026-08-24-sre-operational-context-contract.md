# ADR: Establish a source-independent SRE operational-context contract

- Date: 2026-08-24
- Status: Accepted
- Decision owners: `latent-sre`

## Context

The fleet currently mixes reusable operating behavior with team-specific facts. Platform inventories,
the global stack profile, service cards, runbooks, and caller handoffs each carry part of a service's
identity, repositories, deployment target, and operational references. A skill can describe what
evidence it wants, but it cannot deterministically resolve that evidence for one explicit team,
service, and environment without caller-supplied or hard-coded knowledge.

The detailed research and field model are in the
[`CONTEXT-001` architecture proposal](../reviews/2026-08-24-sre-context-framework-architecture.md).
That proposal compares a Git registry, Backstage, federated repositories, a database/API catalog,
Kubernetes-style resources, environment-variable injection, and MCP-only discovery. It recommends a
small Git/file/CLI proof before introducing a catalog platform or transport service.

`[verified]` The continuation check used current `origin/main`
`773b596334c5fa5678fbcabad2de0fe35921bd06`:

- [`service-readiness-audit`](../../skills/service-readiness-audit/SKILL.md) remains a read-only
  consumer with no team-specific lookup contract; its intervening change only prevents padding the
  output to three fixes;
- [`schemas/catalog-v1.json`](../../schemas/catalog-v1.json) still makes published schema versions
  explicit and immutable, while cross-file and authorization semantics remain outside structural
  validation;
- [`generate_platform_adapters.py`](../../scripts/generate_platform_adapters.py) walks every
  canonical skill file and projects `.json`, `.yaml`, and `.yml` sidecars, so a skill-owned
  requirement file does not need a new host-manifest or frontmatter mechanism. The later sidecar
  must still be linked from its canonical `SKILL.md`, and canonical skill changes must regenerate
  and commit the host projections; and
- `requirements-dev.txt` contains only pinned `pyyaml==6.0.3`, while Gate A remains bare-Python.
  Selecting a third-party schema validator for the Gate A path would therefore require the existing
  two-job CI installation change and is not decided by this ADR; and
- [`stack-profile`](../../skills/stack-profile/SKILL.md) identifies PCF/TAS as the current runtime
  and GCP migration as approved, but keeps the landing runtime decision pending. Cloud Run is a
  candidate shape the contract may represent; this ADR does not select it as the landing runtime;
  and
- the canonical PCF [`foundations`](../../skills/pcf-ops/references/foundations.md) and GCP
  [`projects`](../../skills/gcp-ops/references/projects.md) inventories contain placeholders rather
  than approved team/service values, and the repository has no populated `docs/operations` service
  records. The Payments and Identity entities in the architecture proposal are deliberately
  synthetic portability fixtures, not missing pilot inputs. They can prove generic resolution but
  can never become operational targets or ownership facts.

The decision must preserve these boundaries:

- context identifies a target but never authorizes an effect;
- production is never an implicit environment;
- no credential or copied live state enters the context source;
- team values do not move into generalized skills; and
- a schema-valid document is not proof that a referenced live resource is healthy or current.

## Decision

We will establish a versioned, source-independent operational-context contract with the following
decisions.

1. **Model a graph with an explicit selection coordinate.** `Team` owns `Service`; optional `System`
   groups several services into a user-facing application or capability. `Environment` classifies a
   logical operating and safety boundary. A separate `Deployment` binds one service to one
   environment and contains platform, endpoint, delivery, and observability identities for that
   concrete target.
2. **Use `Service` as the canonical operable unit.** Catalog service IDs, display names, scoped
   aliases, platform application identifiers, OpenTelemetry service identity, and runtime instance
   IDs remain separate fields. Full references use `kind:namespace/id`; display names never become
   keys.
3. **Start with one protected private Git authoring repository, without making centralization part
   of the contract.** The initial repository will be `latent-sre/sre-context`. Its `main` branch is
   protected, validation is required in CI, team owners review their team subtrees through
   `CODEOWNERS`, and contract or resolver owners review schemas and tooling. Resolver input is an
   approved source root plus an exact Git revision. Future federation may add approved pinned
   sources without changing consumer requirements. The repository is private because internal
   service topology, FQDNs, repository mappings, and operational locators need not be public even
   though secrets and copied live state are forbidden.
4. **Separate consumer requirements from context values.** A generalized skill owns a versioned
   requirement sidecar in its canonical skill directory. The context source owns team/service values.
   The resolver checks required, optional, and alternative JSON Pointer paths and emits only the
   bounded projection requested by the consumer. No undocumented skill frontmatter key is added.
5. **Use typed references, not general inheritance, in v1.** Shared integrations, repositories,
   runbooks, knowledge, and standards are referenced explicitly. V1 has no deep merge, implicit
   parent walk, template interpolation, environment overlay, or precedence ladder. Any later overlay
   proposal must be justified by measured duplication after the two-fixture portability proof and
   later onboarding evidence.
6. **Make repositories first-class entities.** A service-to-repository relation carries one or more
   provisional roles—`source`, `infrastructure`, `configuration`, `deployment`, `database`,
   `automation`, `testing`, `documentation`, or `shared-library`—plus a required purpose statement.
   Multiple roles are allowed. An `other` role is not a permanent untyped escape hatch; a repeated
   missing role requires a contract revision.
7. **Index runbooks without forcing one storage location.** A runbook may be owned in `sre-context`
   or in the service repository. The registry stores identity, applicability, ownership, lifecycle,
   source location, and the minimum useful discovery metadata; it does not copy executable job
   definitions or live output.
8. **Store curated facts and locators, not live state.** Git may contain stable ownership,
   repositories, deployment coordinates, FQDNs, platform identifiers, dashboard locators, Jira and
   Confluence locations, runbooks, and architecture references. Alerts, incidents, deployments,
   tickets, health, metrics, logs, and traces remain in their live authoritative systems. Context
   tells the consumer where and how to retrieve them.
9. **Qualify provenance only where it changes operational trust.** Every resolved bundle identifies
   the source repository and revision. Platform-generated IDs and freshness-sensitive resource
   mappings also identify their authoritative system, management mode, and last validation evidence.
   Field-by-field provenance is not required for ordinary manually curated catalog facts.
10. **Use a deterministic file/CLI resolver for the alpha.** `sde` owns the initial implementation
    under `latent-sre/sre-context/tooling/`, co-located with the source schemas and semantic fixtures.
    It validates structural and semantic contracts, rejects duplicate IDs or aliases and
    broken/kind-wrong/cyclic references, resolves an explicit `team + service + environment`
    selector, requires a deployment selector when that coordinate is ambiguous, enforces depth and
    byte budgets, and emits canonical JSON plus provenance. It performs no network discovery by
    default. Language and validator-library selection remain an implementation experiment subject
    to the pinned-dependency and bare-Gate-A rules. Backstage, commercial catalogs, MCP, generated
    discovery, and a long-running database/API are later adapters or decisions.
11. **Keep context separate from authority and secrets.** The resolver rejects secret-bearing fields
    and values matching the bounded secret policy. It never retrieves credentials, approves an
    action, chooses production by default, or bypasses the existing effect and production gates. An
    effect-capable consumer must separately bind the resolved target to its existing approval,
    rollback, credential, and execution controls.
12. **Version by immutable schema URI.** Source entities begin at `sre-context/v1alpha1`; consumer
    requirement and resolved-bundle contracts have their own versions. Alpha makes no general
    compatibility promise, but every breaking change still receives a new URI and migration rather
    than editing a cataloged shape in place. Writers emit one current version. During a declared
    alpha migration, readers accept the current and immediately previous version; support for the
    previous version ends only after both fixture sources and consumers migrate. Generic alpha
    portability is proven with synthetic tenants. Promotion to operational `v1` additionally needs
    at least one separately approved real-team onboarding to validate maintainability; that later
    adoption cannot introduce a team-specific schema or skill branch.

The alpha is deliberately bounded to stages 1–3 from the architecture proposal:

1. publish the contract skeleton and validator fixtures;
2. resolve a synthetic team's read-only `service-readiness-audit` context across multiple services
   and environments; and
3. prove the unchanged consumer contract against a second synthetic team with a materially different
   repository, integration, and platform representation. A Cloud Run-shaped fixture tests the
   contract only; it does not select or approve Cloud Run as the landing runtime.

Fleet-wide skill adoption, effect-capable consumers, federation, automatic discovery, an MCP facade,
or a general overlay language requires a later owner decision based on the alpha evidence.

## Generic fixture policy

The generic contract is developed without organization-specific values:

1. fixture sources live under a dedicated `fixtures/` root and declare `mode: fixture` and
   `nonOperational: true` in their source manifest;
2. entity IDs use visibly synthetic namespaces, locators use RFC-reserved example domains, and
   identifiers contain no copied application GUID, project ID, repository, dashboard, Jira,
   Confluence, on-call, or owner value;
3. the resolver refuses a fixture source unless the caller explicitly supplies `--allow-fixtures`;
4. every resolved fixture bundle preserves `source.mode: fixture` and sets
   `target.actionSelection: prohibited` so it cannot be handed off as an effect target;
5. semantic tests reject a fixture containing a non-example hostname, an unmarked operational
   locator, a secret-bearing field, or a value copied from the repository's live stack references;
   and
6. both synthetic tenants use the same source schemas, resolver, and consumer requirement sidecar.
   Differences are expressed only through typed values and references.

The Tenant Alpha/Checkout and Tenant Beta/Authentication examples are contract fixtures only. They
do not assert that any corresponding team or service exists.

## Implementation defaults

Repository evidence and the accepted architecture settle four implementation defaults:

1. create a private `latent-sre/sre-context` repository with protected `main`, required validation,
   team-subtree `CODEOWNERS`, and schema/tooling ownership by `latent-sre`;
2. place the phase-one resolver and semantic validator under `sre-context/tooling/`, owned by `sde`,
   while consumer-requirement sidecars remain with their canonical skills in this repository;
3. use the alpha compatibility window in decision 12: current plus immediately previous only during
   a declared migration, and no operational `v1` promotion before generic portability plus one
   separately approved real-team onboarding; and
4. model PCF now and keep the deployment-kind extension point capable of representing GCP mappings,
   without treating Cloud Run or GKE as selected by this context decision.

## Acceptance and authority boundary

`latent-sre` accepted this generic contract and authorized creation of the separate private context
repository on 2026-08-24. That approval authorizes stages 1–3 only: the contract skeleton and two
synthetic-tenant portability proofs. It does not authorize real-team onboarding, effect-capable
consumer adoption, live discovery, or a platform selection. No team name, service name, owner, FQDN,
application ID, repository, runbook, or platform adoption decision is required to implement the
generic alpha.

The ownership split is: `latent-sre` for schema/contract acceptance, `prompt-engineer` for
consumer-requirement semantics, and `sde` for resolver and validator implementation. A real team's
owner becomes relevant only when that team separately authorizes onboarding.

## Consequences

### Positive

- A skill can state what it needs once and operate for any onboarded team without a team-specific
  branch.
- Explicit selection, qualified identity, closed schemas, and fail-closed semantic validation reduce
  the chance that an agent guesses the wrong service or production target.
- Progressive projection limits context size and makes provenance inspectable without loading the
  full registry.
- A Git authoring source is easy to review, diff, recover, and prototype while keeping the contract
  portable to future catalog or MCP adapters.
- Existing service cards, runbooks, platform skills, and production gates remain useful rather than
  being replaced by a new universal control plane.

### Negative and neutral

- The registry introduces a new reviewed data product with ownership, validation, migration, stale
  reference, and recovery obligations.
- References are more verbose than implicit inheritance, and some duplication will remain during the
  alpha.
- JSON Schema cannot prove cross-file uniqueness, alias resolution, FQDN semantics, link reachability,
  or authority. A semantic validator and explicit diagnostics are required.
- A Git checkout is not a low-latency live-state store. Consumers must still query authoritative
  systems when freshness matters.
- The synthetic alpha cannot prove organization-wide scale, write-capable consumer safety,
  federation, or MCP transport behavior.

## Failure modes and rollback

- **Ambiguous or missing selection:** fail before a consumer runs and report the exact unresolved
  selector or requirement path; never fall back to production or the first matching deployment.
- **Bad source revision:** reject the source before indexing. Operators pin the last known-valid
  revision while the owning team repairs the new revision through review.
- **Stale external reference:** preserve the declared locator and provenance, report validation age
  or lookup failure, and query the authoritative system only through an existing read-only tool path.
- **Resolver regression:** consumers retain their existing explicit caller-handoff path during the
  alpha. Disable the context adapter and return to the last supported resolver/source pair.
- **Schema migration failure:** readers continue accepting the prior supported URI until every
  synthetic fixture source and consumer has migrated; no accepted schema is edited in place.
- **Repository outage:** use a previously verified local checkout at its recorded revision for
  read-only work. Effect-capable work remains blocked unless its independent production gate can
  establish the target and authority.

Before the first consumer adoption, rollback is simply removal of the unaccepted or failed
synthetic-alpha branch/repository: no generalized skill behavior has changed. After adoption, each
stage must be independently revertible: source contracts, resolver release, consumer sidecar, and
onboarding data are separate revisions.

## Alternatives rejected

- **Hard-coded skill values or environment-variable matrices:** cannot represent relationships,
  provenance, shared resources, or deterministic multi-team discovery.
- **One nested team/application/environment YAML document:** couples unrelated change ownership,
  makes partial reads expensive, and cannot naturally model shared repositories or resources.
- **Backstage or a commercial catalog first:** adds a platform and ingestion model before the minimum
  SRE consumer contract has been proven.
- **A database/API as the authoring source:** adds availability, backup, migration, and administrative
  obligations without improving the first read-only proof.
- **Kubernetes CRDs as the canonical model:** imports cluster scope and control-plane semantics and
  implies a deployment platform the fleet has not selected.
- **MCP as the data model:** MCP is a useful later resource transport but does not define operational
  entities, truth ownership, inheritance, validation, or authorization.
- **General defaults and deep-merge inheritance:** concise authoring at the cost of hidden effective
  values that are difficult for humans and models to explain safely.

<!-- ADRs are append-only and immutable once accepted. To change a decision, write a new ADR and mark
     this one "superseded by <YYYY-MM-DD>-<slug>".
     The repository's structural plan-status check reads the Status field above from the first 14
     lines and wants it as "Status: value"; keep that form or the gate reports no status. -->
