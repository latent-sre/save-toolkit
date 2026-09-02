# Generalized SRE team and application context framework

> **Status: architecture and research proposal for `CONTEXT-001`, not implementation authority and
> not a second backlog.** Current status and sequencing live only in
> [`fleet-roadmap.md`](../fleet-roadmap.md). This record proposes a contract and staged experiment;
> it does not create the context repository, add a runtime dependency, rewrite fleet skills, or
> authorize a production-facing action.
>
> **Superseded detail:** recommendations below that place an exact source revision or digest in the
> resolved fixture bundle were not adopted. The accepted
> [`operational-context ADR`](../decisions/2026-08-24-sre-operational-context-contract.md) leaves
> exact source identity to a separately trusted execution boundary.

**Research baseline:** `50eff87e982455ce23d4dcb683d675159e0af706`

**Research date:** 2026-08-24

**Scope:** reusable SRE agents and skills, team/application operational context, a possible central
context repository, schemas, validation, deterministic resolution, progressive disclosure, and a
staged adoption path.

## Conclusion

Create a separate, Git-backed **SRE operational context registry** as the first authoring source,
but do not make “one central repository” part of the logical contract. The contract should describe
versioned entities and references; a deterministic resolver should be able to read one checked-out
source root today and additional approved sources later. This preserves a simple first deployment
without making future federation a migration of every skill.

The smallest useful model is not a rigid
`organization -> team -> application -> environment` tree. Operational facts form a graph:

- a team owns services and integrations;
- an optional system groups services into a user-facing application or business capability;
- an environment profile classifies `production`, `staging`, or another operating boundary;
- a **deployment binding** connects one service to one environment and carries the PCF, Cloud Run,
  Kubernetes, endpoint, deployment, and observability identifiers for that concrete target;
- repositories, runbooks, dependencies, dashboards, and external systems are referenced entities
  or typed references that may be shared across services.

Use `Service` as the canonical deployable/operable unit because this repository already keys
runbooks and knowledge on `service_id`. Use optional `System` for a composite “application” made of
several services. Do not overload either with a platform application GUID or a running instance ID.

The operating formula becomes:

```text
consumer-owned context requirement
        + explicit team/service/environment selection
        + schema-valid versioned context entities
        -> deterministic resolved context bundle
        -> reusable skill or agent
```

The recommended boundaries are:

1. **`sre-agents` owns consumer requirements and generic behavior.** A skill declares the context it
   needs in a versioned sidecar contract owned with that skill. Do not add an undocumented skill
   frontmatter key.
2. **`sre-context` owns curated values and operational documents.** Team data, service definitions,
   deployment bindings, repository records, integration endpoints, runbooks, and knowledge links
   are reviewed as Git changes.
3. **A resolver owns interpretation.** It validates, canonicalizes aliases, follows references,
   enforces selection and environment rules, checks the consumer contract, and emits only the
   requested projection plus provenance.
4. **Live systems own live state.** The resolved bundle says where and how to retrieve current
   metrics, deployments, alerts, incidents, tickets, and health; it does not copy that state into
   Git.
5. **The effect boundary owns authorization.** Context can identify a production target but cannot
   approve, credential, or execute an action. Production is never an implicit default.

Do not begin with Backstage, a database, a Kubernetes CRD, a general inheritance engine, or an MCP
server. A file/CLI contract with two explicitly synthetic tenant fixtures is the smallest reversible
generic proof. Backstage export, federated sources, and an MCP resource facade remain compatible
later adapters. Real team values are onboarding inputs after the contract proves portable, not
architecture prerequisites.

## Evidence method

The research kept four evidence lanes separate:

- **Local workspace:** canonical agents, skills, schemas, contributor rules, and the live roadmap at
  the baseline above. Generated projections were not treated as independent sources.
- **Context7:** current documented contracts for Backstage, OpenTelemetry, and MCP. Resolved library
  IDs were `/backstage/backstage`, `/open-telemetry/opentelemetry-specification`, and
  `/modelcontextprotocol/modelcontextprotocol`.
- **GitHits:** pinned upstream source, schemas, tests, and OSS adoption evidence for catalog and
  workload models. Those findings are implementation evidence, not local-workspace evidence.
- **Official specifications:** JSON Schema 2020-12, OpenGitOps 1.0.0, Kubernetes object conventions,
  OpenTelemetry semantic conventions, MCP, and RFC 6570.

Context7 exposed draft MCP 2026-07-28 material while the official site still identifies 2025-11-25
as the stable protocol revision. This proposal uses the stable resource contract; draft-only caching
and subscription changes do not enter the required design.

## 1. Current repository assessment

The repository already has useful pieces, but they are templates and team-global references rather
than a resolvable context model.

| Existing surface | What is already correct | Missing boundary | Consequence for `CONTEXT-001` |
|---|---|---|---|
| [`stack-profile`](../../skills/stack-profile/SKILL.md) | One canonical source for the current stack, documentation home, change systems, and app/platform boundary | It describes one team's facts and is loaded globally; it cannot select among teams, services, or deployments | Split reusable platform interpretation from team values; use synthetic platform representations for contract proof and consider a profile adapter only during a separately approved real-team migration |
| [`pcf-ops` foundation inventory](../../skills/pcf-ops/references/foundations.md) and [`gcp-ops` project inventory](../../skills/gcp-ops/references/projects.md) | They tell agents not to guess platform targets and exclude secrets | Values live in Markdown tables with different shapes and no shared identity, cross-reference, or validator | Replace value lookup with typed deployment bindings; retain platform-specific skills and procedures |
| `service-onboarding` (renamed to `service-lifecycle` after this review) | Requires a named service/environment, owner, revision, and authoritative definitions | The caller must assemble every value manually; onboarding does not register a schema-valid context entity | Make validated context creation an early onboarding output, without letting the context contract authorize onboarding effects |
| [`service-readiness-audit`](../../skills/service-readiness-audit/SKILL.md) | Defines a strong read-only evidence inventory | It has no deterministic way to discover the selected service's repository, deployment, dashboards, SLOs, dependencies, or runbooks | Use its unchanged requirement contract for the first synthetic read-only portability proof |
| [`operational-learning`](../../skills/operational-learning/SKILL.md) and [service-card template](../../skills/operational-learning/assets/service-card-template.md) | Stable `service_id`, ownership, criticality, dependencies, recovery, observability, and provenance already exist | The cards are Markdown templates, not registered service entities; repository/runtime values are copied into prose | Preserve the human card, but generate or validate its links from the same service identity rather than creating a second configuration truth |
| [Runbook schema](../../schemas/runbook-frontmatter-v1.schema.json) and [template](../../skills/runbook/assets/runbook-template.md) | Stable runbook/service IDs, lifecycle, review/verification separation, and immutable schema policy are established | Environment applicability and reusable-runbook context requirements are not modeled; only runbook frontmatter has a schema | Reference the existing contract and version it deliberately if a real consumer requires new fields; never mutate v1 in place |
| [Context-engineering reference](../../skills/agent-authoring/references/context.md) | Progressive disclosure, provenance, freshness, trust, and small context are explicit | It governs token selection, not operational entity identity or resolution | The resolver implements these principles; it does not replace the reference |
| [Schema compatibility policy](../schema-compatibility.md) and [catalog](../../schemas/catalog-v1.json) | Published schema versions are immutable and structural validation is not authorization | There is no team, service, environment, deployment, repository, or consumer-requirement schema | Reuse the immutable-version/catalog pattern and add semantic validation because cross-file relationships exceed JSON Schema |

The primary duplication problem is not merely repeated strings. Team-specific facts currently appear
as a global stack profile, platform-specific inventories, service-card prose, and caller-supplied
handoffs. A new registry must consolidate their identity and references without turning human
operational documents into generated configuration dumps.

## 2. Research findings and alternatives

### Useful patterns to adopt

Backstage demonstrates a versioned entity envelope, stable entity references, explicit ownership,
and graph relations among Component, System, Domain, Resource, API, and Group. Its own guidance says
the catalog should model useful human concepts rather than every possible object, and that the
catalog service is a materialized view rather than the ultimate truth; Git-backed descriptors or
existing authoritative systems should remain the sources. See the official
[descriptor format](https://backstage.io/docs/features/software-catalog/descriptor-format/),
[system model](https://backstage.io/docs/features/software-catalog/system-model/),
[entity references](https://backstage.io/docs/features/software-catalog/references/), and
[catalog graph guidance](https://backstage.io/docs/features/software-catalog/creating-the-catalog-graph/).

Score separates an environment-agnostic workload request from environment-specific platform
resolution. Its resource references fail when a requested output is unknown, and its schema is
validated before platform-specific generation. That separation is useful; its container/runtime
specification and placeholder interpolation are not this registry's job. See the official
[Score overview](https://docs.score.dev/docs/) and
[specification reference](https://docs.score.dev/docs/score-specification/score-spec-reference/).

Kubernetes shows why a strict tree is insufficient: labels support cross-cutting grouping because
real deployments are multi-dimensional. It also distinguishes a human-selected object name from a
runtime UID and separates desired `spec` from observed `status`. This proposal borrows those
distinctions but rejects Kubernetes owner-reference semantics, which imply garbage-collection
ownership and scope rules that do not describe service dependencies or documentation. See
[labels and selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/),
[names and UIDs](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/), and
[owners and dependents](https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/).

OpenTelemetry Semantic Conventions 1.44.0 provide a useful mapping vocabulary, not the catalog's
canonical identity. The service identity conventions are stable, while several platform-specific
cloud/Cloud Foundry attributes remain Development; keep those spellings behind a mapping boundary
rather than freezing them into the catalog's core identity.
`service.name` is the logical telemetry service, `service.namespace` groups related services, and
`service.instance.id` identifies one concurrent runtime instance. Environment does not participate
in that identity. Keep the catalog's service/environment coordinate separate and map it explicitly
to OTel fields. See the
[service semantic conventions](https://opentelemetry.io/docs/specs/semconv/resource/service/) and
[deployment-environment conventions](https://opentelemetry.io/docs/specs/semconv/resource/deployment-environment/).

JSON Schema 2020-12 is the right structural schema dialect. Pin `$schema` and absolute `$id`, use
`$defs`/`$ref`, close known objects, and test the selected validator. `format` is annotation-only by
default and `default` does not materialize values, so FQDN/URL/date validation and all resolution
semantics require an explicit semantic validator. See
[Draft 2020-12](https://json-schema.org/draft/2020-12) and its
[core specification](https://json-schema.org/draft/2020-12/json-schema-core).

MCP's stable resources contract fits later progressive delivery: list small named resources, read
one selected URI, and offer parameterized resource templates. MCP does not define SRE entities,
truth ownership, inheritance, authorization, or skill requirements. Treat it as an optional adapter
over the resolver. See the stable
[MCP resources specification](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)
and [RFC 6570 URI Templates](https://www.rfc-editor.org/rfc/rfc6570.html).

OpenGitOps supports declarative, versioned/immutable desired state that agents pull and continuously
reconcile. A reviewed context repository satisfies the first two properties, but it is not GitOps
unless a controller applies and reconciles it. Call this configuration-as-code and avoid implying a
live reconciliation authority. See [OpenGitOps principles 1.0.0](https://opengitops.dev/).

### GitHits implementation evidence

GitHits checked the documented patterns against exact upstream source rather than using OSS names as
architecture by analogy.

| Upstream evidence | Finding | Use here |
|---|---|---|
| Backstage `de92fae`: [`system-model.md`](https://github.com/backstage/backstage/blob/de92faeb4a375af5bd4f7a84311e702736e98964/docs/features/software-catalog/system-model.md#L15-L141) | Components/resources and organizational groups are separate graphs; Systems and Domains are optional groupings | Ownership is a relation, not physical containment; keep optional System separate from Service |
| Backstage `de92fae`: [`descriptor-format.md`](https://github.com/backstage/backstage/blob/de92faeb4a375af5bd4f7a84311e702736e98964/docs/features/software-catalog/descriptor-format.md#L159-L236) and [`references.md`](https://github.com/backstage/backstage/blob/de92faeb4a375af5bd4f7a84311e702736e98964/docs/features/software-catalog/references.md#L11-L21) | `apiVersion + kind` selects a schema; kind/namespace/name forms canonical identity | Version every kind and use full references rather than unqualified IDs |
| Backstage `de92fae`: [`descriptor-format.md`](https://github.com/backstage/backstage/blob/de92faeb4a375af5bd4f7a84311e702736e98964/docs/features/software-catalog/descriptor-format.md#L365-L453) and [`well-known-relations.md`](https://github.com/backstage/backstage/blob/de92faeb4a375af5bd4f7a84311e702736e98964/docs/features/software-catalog/well-known-relations.md#L16-L26) | Processors derive directional relations and resolved relations become the consumption view | Preserve authored declarations and emit a separate deterministic resolved view with provenance |
| Backstage `de92fae`: [`api.md`](https://github.com/backstage/backstage/blob/de92faeb4a375af5bd4f7a84311e702736e98964/docs/features/software-catalog/api.md#L204-L224) | The API supports JSON-path field projection to reduce response size | Make a consumer context contract executable as a bounded field projection |
| Score `1c2427d`: [`README.md`](https://github.com/score-spec/spec/blob/1c2427db4e1c96e05956e0546e767fc994a5421d/README.md#L53-L63) | Workload requirements are environment-agnostic and target platforms resolve environment values | Keep Service separate from Deployment and Environment |
| Score `1c2427d`: [`score-v1b1.json`](https://github.com/score-spec/spec/blob/1c2427db4e1c96e05956e0546e767fc994a5421d/score-v1b1.json#L1-L92) | Its root is version-discriminated and closed while bounded metadata/annotations remain extensible | Use a closed typed core; any extension namespace cannot satisfy a core consumer requirement |
| Runme `dea8211`: [`README.md`](https://github.com/runmedev/runme/blob/dea82115348945835f326f75db0a35c37c5a4100/README.md#L7-L30) and [`frontmatter.go`](https://github.com/runmedev/runme/blob/dea82115348945835f326f75db0a35c37c5a4100/document/frontmatter.go#L125-L152) | Human procedures remain Markdown while small namespaced frontmatter serves tooling | Keep runbook bodies human-readable and separate executor-specific metadata from SRE discovery metadata |
| Rundeck `a462982`: [`JobDefinition.ts`](https://github.com/rundeck/rundeck/blob/a462982aa22bf350c9e121d213283ffaa7994b4e/rundeckapp/grails-spa/packages/ui-trellis/src/library/types/jobs/JobDefinition.ts#L1-L95) | Executable jobs carry target filters, options, schedules, enablement, and ordered steps | Reference automation jobs; do not copy executable job configuration into a descriptive runbook |

No inspected OSS source established a broadly adopted repository-purpose taxonomy. The proposed
roles below are therefore an alpha contract to test, not a standard claim. Context7's current
Backstage documentation agreed with the pinned GitHits entity/relationship evidence; no material
contract-versus-implementation disagreement was found in that lane.

### Alternatives considered

| Alternative | Strength | Why it is not phase one | Revisit trigger |
|---|---|---|---|
| One central Git repository | Simple review, atomic references, one validator, small operational burden | Cross-team permissions and ownership can become a bottleneck at larger scale | Start here with directory ownership and a source-independent contract |
| One repository per team plus a central index | Teams own permissions and cadence; smaller blast radius | Cross-repository revisions, broken references, discovery, and atomic migrations add complexity before scale proves it necessary | Team permission boundaries or repository size/change contention make the central source materially unsafe or slow |
| Backstage as the primary runtime | Mature catalog API, relations, UI, integrations, and search | Adds a service/runtime and a broad entity model; an agent still needs a small deterministic resolved bundle; Backstage itself recommends upstream sources remain authoritative | The organization already operates Backstage as an approved catalog, or human portal/search needs justify the service |
| Commercial service catalog / IDP | Managed UI, integrations, scorecards | Vendor data model, API availability, exportability, cost, and agent-context fit need a separate build/buy decision | A named organizational platform decision supplies the product and authority boundary |
| Score as the catalog | Strong workload/platform separation | It specifies runnable workloads and resources, not ownership, runbooks, repositories, incident context, or operational knowledge | Use only as a referenced workload source if teams adopt Score |
| Kubernetes CRDs | Versioned kind/schema pattern and tooling | This team does not operate self-managed Kubernetes; CRD lifecycle and controller semantics are not required; using a cluster as a document catalog broadens authority | An approved platform already exposes the catalog as CRDs and the platform team owns it |
| CUE, Jsonnet, Helm, or Kustomize overlays | Powerful composition and generation | Adds a language or patch semantics that an LLM and human must interpret; hidden merge behavior conflicts with fail-closed resolution | Repeated, measured duplication remains after reference-based composition and justifies one separately designed overlay contract |
| One large YAML file or environment variables | Easy initial prototype | Merge conflicts, unbounded context, ambiguous indexing, weak collections, and no progressive disclosure | Never as the canonical design; a generated small resolved bundle is acceptable |
| MCP server as the source of truth | Natural agent discovery interface | Transport does not define data meaning or authority and creates a runtime dependency before the file contract is proven | Add a read-only facade after the resolver and URI authorization tests are stable |

## 3. Recommended architecture

```text
reviewed Git context sources
        |
        v
schema + semantic validator -----> deterministic entity index
        |                                  |
        |                                  v
        |                      explicit selector + consumer contract
        |                                  |
        +----------------------------------v
                              resolved context bundle
                                  /             \
                                 v               v
                         reusable skill      typed live-system
                         or agent            references/queries
```

| Component | Owns | Must not own |
|---|---|---|
| Context source repository | Curated entities, stable documents, references, review history, source ownership | Current health, alerts, incidents, credentials, authorization, or copied live-system state |
| Structural schemas | Per-kind shape, types, required fields, closed objects, reusable definitions | Cross-file existence, alias uniqueness, live reachability, defaults, or authority |
| Semantic validator/indexer | Duplicate IDs/aliases, broken/cyclic refs, selection uniqueness, FQDN/URL semantics, secret-key policy, schema compatibility, deterministic index | Live effect authorization or silent repair of bad input |
| Resolver | Explicit selection, alias canonicalization, reference expansion, consumer requirement checks, projection, provenance, size budget | Guessing, network discovery by default, hidden inheritance, or target approval |
| Consumer requirement sidecar | Context paths and alternatives one skill actually needs | Team values, credentials, procedures, or a new host routing mechanism |
| Optional CLI/MCP adapters | Transport, listing, targeted reading, human diagnostics | A second data model or policy bypass |
| Existing production gates | Approval, exact effect target, rollback, credential/effect enforcement | Treating context validity as permission |

### Central repository recommendation

Use one `sre-context` repository for the generic alpha and the first separately approved operational
onboarding. Protect `main`, require the validator in CI, and assign owners to schema and tooling
roots. When a real team onboards, add `CODEOWNERS` for its directory and keep review ownership local
to the team that owns the values. The repository is authoritative only for **catalog-owned** facts.
A repository record can be authoritative for its purpose mapping; PCF remains authoritative for a
current app GUID; Grafana remains authoritative for a dashboard's current content; Jira remains
authoritative for tickets.

The resolver input is a source root plus exact Git revision. Nothing in the entity contract assumes
that all entities must remain in one repository. A future root manifest may enumerate approved
source repositories and pinned revisions, but phase one has exactly one source and no network
fetches during validation.

### Recommended repository layout

```text
sre-context/
├── README.md
├── catalog.yaml                    # source version and entity roots, not an item database
├── schemas/
│   ├── catalog/
│   ├── source/v1alpha1/
│   │   ├── team.schema.json
│   │   ├── system.schema.json
│   │   ├── service.schema.json
│   │   ├── environment.schema.json
│   │   ├── deployment.schema.json
│   │   ├── repository.schema.json
│   │   ├── integration.schema.json
│   │   ├── resource.schema.json
│   │   └── runbook.schema.json
│   ├── context-requirement/v1/
│   └── resolved-context/v1/
├── teams/
│   ├── payments/
│   │   ├── team.yaml
│   │   ├── systems/
│   │   ├── services/
│   │   ├── environments/
│   │   ├── deployments/<service>/
│   │   ├── repositories/
│   │   ├── runbooks/<service>/
│   │   └── knowledge/
│   └── identity/
├── shared/
│   ├── integrations/
│   ├── repositories/
│   ├── runbooks/
│   ├── knowledge/
│   └── standards/
├── migrations/
├── tooling/
└── tests/
```

Directory placement optimizes human ownership and progressive reads; it is not entity identity.
References remain valid if a file moves. Do not commit a hand-edited generated index. A CLI may
materialize a deterministic index in CI or a release artifact and prove it was generated from the
named source revision.

## 4. Context hierarchy: use a graph with one explicit selection path

The normal lookup path remains easy:

```text
team -> service -> environment -> unique deployment -> requested resources
```

The source model is richer:

```text
Team --owns--> Service --part-of--> System (optional)
  |                |  \
  |                |   +--uses--> Repository
  |                +------depends-on--> Service / external Resource
  |                +------has--> Deployment --in--> Environment
  |                                      |
  +--provides--> Integration <-----------+
                                         +--references--> dashboard/logs/pipeline/runbook
```

`Organization` is deliberately optional. Add it only when multiple organizations need shared
policy or identity and a real consumer distinguishes them. Requiring it now adds a level that every
lookup must traverse without improving the current team's decisions.

`Environment` is a logical, team-scoped operating classification such as `production` or
`development`. It does not contain an app GUID, workload name, FQDN, or dashboard. `Deployment`
binds those facts to one service in one environment. This prevents `production` from becoming a
large mixed object containing every application and prevents a service document from accumulating
every platform's nested override tree.

The minimum selector is `team + service + environment`. If that coordinate has more than one active
deployment—for example two regions or a migration with PCF and Cloud Run coexisting—the resolver
fails as ambiguous and requires an explicit `deployment` ID. It never silently chooses the first,
latest, or production target.

## 5. Proposed source schemas

These are design shapes, not committed machine contracts. The implementation phase must express
them as JSON Schema 2020-12 and add red-first semantic-validator fixtures before calling them valid.

### Common envelope

```yaml
apiVersion: sre-context/v1alpha1
kind: Service
metadata:
  id: checkout-api                 # immutable canonical slug in kind + namespace
  name: Checkout API               # display name, mutable
  namespace: payments              # team scope for team-owned entities
  aliases:
    - value: checkout
      type: human
  ownerRef: team:payments            # required for owned kinds; Team is itself an ownership target
  lifecycle: active
  managedBy: manual                # manual | generated
  sourceRef: null                  # required when generated or discovered
  lastReviewed: 2026-08-24
spec: {}
```

Use the uniform envelope for dispatch and traversal, but do not copy Kubernetes `status`, UID,
resourceVersion, finalizers, or ownerReferences. `metadata.id` is not a platform object name and is
never reused for a different logical entity. A full reference is always lowercase:
`kind:namespace/id`, for example `service:payments/checkout-api`.

### Team-level fields

| Field | Required | Purpose |
|---|---:|---|
| `metadata.id`, `name`, `lifecycle` | yes | Stable identity, display, and lifecycle; Team is itself an ownership target |
| `spec.description` | yes | One-sentence scope and boundary; detailed documentation is referenced |
| `spec.accountabilityRef` | no | Organizational/contact authority above the team, when one exists; do not self-reference the Team |
| `spec.onCallRef`, `spec.escalationRefs` | active teams | Links to schedule/escalation systems, not the current person |
| `spec.integrationRefs` | no | Jira, change system, Confluence import source, Grafana, Wavefront, Splunk, Git, cloud, and other typed endpoints |
| `spec.environmentRefs` | yes for operational teams | Allowed logical environments and their safety classifications |
| `spec.systemRefs`, `serviceRefs` | no | Discoverable owned entities; may be generated by the indexer rather than authored twice |
| `spec.domainRefs` | no | Team-owned DNS/domain boundaries with a stated purpose; avoid ambiguous `team.fqdn` |
| `spec.documentationRefs`, `runbookRefs` | no | Team-wide operational references |
| `spec.platformBoundaryRef` | active teams | What the team owns versus escalates |
| `spec.changePolicyRef` | effect-capable teams | Which external change process applies; no ticket state is copied |

Do not put a singular Jira project, Grafana URL, Git organization, or domain directly at the team
root when the team can have more than one. Define typed `Integration` or `Domain` references with a
purpose and mark a default only where the consumer contract permits it.

### System and service/application fields

`System` is optional and groups services that deliver one business application or user capability.
Its minimum fields are `id`, `name`, `ownerRef`, `description`, `criticality`, and `serviceRefs`.

`Service` is the normal SRE selection target:

| Field | Required | Purpose |
|---|---:|---|
| `metadata.id`, `name`, `ownerRef`, `lifecycle` | yes | Canonical operational identity and owner |
| `spec.type` | yes | `service`, `worker`, `job`, `website`, `data-pipeline`, or another versioned supported type |
| `spec.description` | yes | What it does and its boundary |
| `spec.systemRef` | no | Composite application/business capability membership |
| `spec.criticality` | active services | `critical`, `high`, `medium`, or `low`; response policy may consume it |
| `spec.repositoryUses` | active services | First-class repository references plus why each matters |
| `spec.deploymentRefs` | active deployed services | Concrete environment/platform bindings |
| `spec.runbookRefs`, `documentationRefs` | no | Operational and architecture knowledge links |
| `spec.dependencyRefs` | no | Typed direction, failure effect, criticality, and owner; no copied live status |
| `spec.userJourneys` | externally meaningful services | What user/business outcome fails and the blast-radius vocabulary |
| `spec.reliabilityRefs` | no | SLO, SLI, health, capacity, and recovery evidence locations |
| `spec.dataProfileRef` | stateful/sensitive services | Statefulness, classification, RTO/RPO, backup/restore authority |
| `spec.cicdRefs`, `configurationRefs` | no | Authoritative delivery and configuration locations |
| `spec.telemetryIdentity` | instrumented services | Explicit OTel `service.name` and optional `service.namespace`; never inferred from display name |

### Environment-level fields

```yaml
apiVersion: sre-context/v1alpha1
kind: Environment
metadata:
  id: production
  name: Production
  namespace: payments
  ownerRef: team:payments
  lifecycle: active
spec:
  classification: production      # production | preproduction | nonproduction | sandbox
  actionSelection: explicit-only
  changePolicyRef: integration:payments/jira-change
  dataClassificationCeiling: restricted
  sharedIntegrationRefs:
    - integration:payments/grafana-primary
```

Environment owns classification and team-wide policy/reference choices. It does not own one
service's PCF GUID, route, dashboard UID, Kubernetes namespace, or Cloud Run name.

### Deployment binding

```yaml
apiVersion: sre-context/v1alpha1
kind: Deployment
metadata:
  id: checkout-api-production-pcf-east
  name: Checkout API production on PCF east
  namespace: payments
  ownerRef: team:payments
  lifecycle: active
spec:
  serviceRef: service:payments/checkout-api
  environmentRef: environment:payments/production
  region: us-east
  platform:
    type: cloudfoundry
    cloudfoundry:
      foundationRef: platform:shared/pcf-prod-east
      organization: payments
      space: production
      applicationName: checkout-api
      applicationGuid: abc123
  endpoints:
    - id: public
      kind: https
      fqdn: checkout.example.com
      purpose: customer-api
  observabilityRefs:
    - resource:payments/checkout-prod-dashboard
  deploymentMethodRef: resource:payments/checkout-pipeline
  rollbackRunbookRef: runbook:payments/checkout-rollback
  provenance:
    authorityRef: platform:shared/pcf-prod-east
    validatedAt: 2026-08-24T00:00:00Z
    validationRef: evidence:payments/pcf-inventory-20260824
```

Platform identifiers are qualified and precise:

- `cloudfoundry.applicationGuid` and `applicationName` are different facts;
- `kubernetes.clusterRef`, `namespace`, `workload.kind`, and `workload.name` identify a workload;
  recreation-sensitive object UIDs stay live;
- `gcp.projectRef`, `region`, and `cloudRun.serviceName` identify Cloud Run;
- OTel `service.name`, `service.namespace`, and `service.instance.id` remain telemetry mappings, not
  catalog IDs.

Do not expose a generic environment-level `application_id`.

### Repository model

Repositories are first-class entities because they may be shared, referenced by multiple services,
or carry several roles.

```yaml
apiVersion: sre-context/v1alpha1
kind: Repository
metadata:
  id: checkout-service
  name: Checkout service source
  namespace: payments
  ownerRef: team:payments
  lifecycle: active
spec:
  provider: github
  host: github.example.com
  organization: payments
  repository: checkout-service
  defaultBranch: main
  webUrl: https://github.example.com/payments/checkout-service
```

Purpose belongs on the relationship because one repository may serve different purposes for
different consumers:

```yaml
repositoryUses:
  - repositoryRef: repository:payments/checkout-service
    roles: [source, test]
    purpose: Application code and its component tests
    paths: [src/, tests/]
  - repositoryRef: repository:payments/payments-delivery
    roles: [delivery, configuration]
    purpose: Build, promotion, and PCF manifests for checkout-api
    paths: [services/checkout-api/]
```

Use a small provisional role vocabulary: `source`, `delivery`, `infrastructure`, `configuration`,
`operations`, `automation`, `data`, `test`, and `documentation`. Multiple roles are legal. `other`
requires a non-empty purpose. Do not infer purpose from a repository name, and do not call this list
an industry taxonomy until the two-fixture portability proof and later onboarding evidence show that
its distinctions are useful.

### Integration and operational-resource model

An `Integration` defines a stable endpoint/capability once:

```yaml
apiVersion: sre-context/v1alpha1
kind: Integration
metadata:
  id: grafana-primary
  name: Primary Grafana
  namespace: payments
  ownerRef: team:payments
  lifecycle: active
spec:
  type: grafana
  baseUrl: https://grafana.example.com
  credentialProfileRef: secret-profile:grafana-read
  authority: grafana
```

A `Resource` reference identifies the specific dashboard, Jira project, Confluence source page,
log location, pipeline, SLO, secret retrieval profile, or other operational target. Use typed
locators rather than one unlimited URL bag:

```yaml
apiVersion: sre-context/v1alpha1
kind: Resource
metadata:
  id: checkout-prod-dashboard
  name: Checkout production health dashboard
  namespace: payments
  ownerRef: team:payments
  lifecycle: active
spec:
  type: grafana-dashboard
  integrationRef: integration:payments/grafana-primary
  locator:
    uid: checkout-prod
  purpose: Primary production health and incident drill-down
  authoritativeFor: [dashboard-location]
```

Schema-defined resource types own their locator fields. An extensible `type: other` requires a URI,
purpose, authority, and retrieval mode but cannot satisfy a typed consumer requirement.

### Runbook and knowledge model

Do not require all runbook bodies to move into the context repository. The registry must index
runbooks stored centrally or in a service repository through the same stable `Runbook` reference.
Central storage is appropriate for shared/team procedures and for teams whose approved living
documentation home is this registry. A service-local runbook may stay with the code or deployment
definition when that ownership gives safer review and version coupling.

Retain the existing useful metadata: stable runbook/service identity, status, alert names, owner,
source revision, version, `lastReviewed`, `lastVerified`, and bound verification evidence. Add fields
only for a named consumer:

| Field | Rule |
|---|---|
| `serviceRef` | Required for a service-specific runbook; replaces an unscoped string across repositories |
| `environmentRefs` | Optional; empty means environment-neutral, never “all environments including production” for an effectful procedure |
| `alertRefs` / `symptoms` | Exact alert references where they exist; short symptom terms improve discovery without copying alert logic |
| `requiredContextRef` | Optional and useful only for a reusable/parameterized runbook whose steps consume resolved fields |
| `safetyClass` | Required only when procedure steps are effect-shaped; it classifies but does not authorize them |

Knowledge documents remain human-readable Markdown. Add structured frontmatter only when the
resolver or index has a concrete lookup need—normally stable ID, service/system references, owner,
status, source revision, and last review. Do not schema every architecture paragraph or duplicate
commands, alert queries, manifests, dashboard JSON, or configuration.

## 6. Context contract for skills and agents

The context requirement is a consumer-owned sidecar such as
`skills/service-readiness-audit/context-requirements.yaml`. Keeping it with the consumer means a team
cannot weaken what a skill needs, and the context repository does not need to know every installed
skill. Do not add `requires:` to skill frontmatter until the host documents that field.

```yaml
apiVersion: sre-context/requirements/v1
kind: ContextRequirement
metadata:
  consumerId: save-toolkit:service-readiness-audit
  consumerRevision: <plugin-or-source-revision>
spec:
  selectors: [team, service, environment]
  required:
    - /context/team/id
    - /context/service/id
    - /context/service/owner
    - /context/environment/id
    - /context/environment/classification
    - /context/deployment/id
    - /context/deployment/platform/type
    - /context/service/repositoryUses
  anyOf:
    - [/context/deployment/platform/cloudfoundry]
    - [/context/deployment/platform/gcp/cloudRun]
    - [/context/deployment/platform/kubernetes]
  optional:
    - /context/service/runbookRefs
    - /context/deployment/observabilityRefs
    - /context/service/dependencyRefs
  maxResolvedBytes: 20000
```

Use JSON Pointer for the machine contract and dot notation only in prose. Required paths fail
closed. `anyOf` expresses legitimate platform alternatives. Optional fields remain absent; the
resolver never fabricates an empty value that a skill could misread as confirmed absence.

The contract may request stable context and typed live **references**, but never live metric values,
credentials, or an effect. A skill still loads its platform-specific method and retrieves current
evidence through its allowed tools and authority.

## 7. Context resolution mechanism

The phase-one resolver is a small CLI/library with deterministic offline behavior:

1. Load the exact source root and Git revision; reject a dirty or unbound source when the caller
   requires revision-bound evidence.
2. Parse YAML with duplicate-key rejection and no executable/custom object tags.
3. Validate each entity against its exact `apiVersion` and `kind` schema without network schema
   retrieval.
4. Build a canonical index keyed by full entity reference. Reject duplicate IDs, invalid refs,
   forbidden alias collisions, and relationship cycles where the relationship must be acyclic.
5. Resolve the explicit team, service, and environment selectors. An alias must produce exactly one
   canonical entity in its allowed scope; zero or multiple matches fail.
6. Resolve exactly one deployment. If the coordinate has zero or multiple applicable deployments,
   return a structured error and the candidate canonical IDs; never select one heuristically.
7. Expand only the references requested by the consumer contract, preserving typed reference IDs
   and source provenance. Detect cycles and enforce a depth/byte budget.
8. Check every required/alternative JSON Pointer. Return missing requirements as errors, not model
   instructions to improvise.
9. Emit canonical JSON with stable ordering, the exact selection, source revision/digest, source
   paths, field-group provenance, warnings, and omitted optional paths.
10. For an effect-capable consumer, require explicit environment/deployment input and carry the
    target classification into the effect gate. The resolver itself performs no effect and grants no
    approval.

Example output envelope:

```yaml
schemaVersion: 1
selection:
  teamRef: team:payments
  serviceRef: service:payments/checkout-api
  environmentRef: environment:payments/production
  deploymentRef: deployment:payments/checkout-api-production-pcf-east
  explicit: true
context: {}
provenance:
  sourceRevision: <full-git-sha>
  resolverVersion: <version-or-full-sha>
  sources: []
warnings: []
omittedOptionalPaths: []
```

An MCP facade may later expose URI templates such as
`sre-context://teams/{team}/services/{service}/environments/{environment}`. The URI resolves through
the same library, and authorization must constrain list and read results. MCP priority/audience
annotations are hints, not context requirements or security controls.

## 8. Inheritance and override rules

Do **not** implement general inheritance in v1. Most duplication in the example disappears through
references:

- define the Grafana base URL once as an `Integration` and reference it from dashboard resources;
- define `production` once as an `Environment` and reference it from deployments;
- define a repository once and attach service-specific roles on the relationship;
- define team ownership and escalation once and reference the team;
- reference shared runbooks and standards rather than copying them.

These are the complete v1 composition rules:

1. An authored entity owns its own fields; no parent silently changes them.
2. A reference expands the referenced entity without copying or merging its fields into the source
   entity.
3. The resolved bundle may present convenient normalized projections, but it records every source
   reference and never writes the projection back as authored truth.
4. Collections are keyed by canonical IDs and cannot contain duplicate keys.
5. There is no YAML merge key, template execution, order-dependent overlay, wildcard default, or
   implicit array merge.
6. Missing required data is an error. Null, absent, empty, and inherited are not interchangeable.

If measured synthetic-proof and later-onboarding duplication still requires overlays, design a
separately versioned v2 resolver
contract. At minimum it must specify scalar replacement, map behavior, collection merge keys,
explicit deletion, maximum depth, cycle handling, precedence, provenance per effective field, and
red tests for order changes. JSON Schema `default`, `allOf`, and `$ref` do not define instance merge
semantics and must not be presented as inheritance.

## 9. Canonical ID and alias strategy

- IDs are lowercase kebab-case and immutable for the logical entity's lifetime.
- Full references are `kind:namespace/id`; a team itself uses `team:<id>`.
- Display names are mutable and never used for joins.
- Aliases are typed (`human`, `legacy`, `repository`, `platform`, `observability`) and scoped by
  entity kind plus team unless an explicit broader scope exists.
- Alias resolution must be unique. Ambiguity returns candidates and requires a canonical selection.
- Aliases can help read-only discovery but never substitute for the exact canonical target in an
  effect approval.
- Retired IDs are tombstoned or redirected; they are not silently reused for a different service.
- Platform identifiers stay in deployment/platform blocks and may change without renaming the
  catalog service.

## 10. Static data, live data, provenance, and truth ownership

| Information | Git treatment | Authority |
|---|---|---|
| Team/service identity, ownership reference, lifecycle, repository purpose | Store as curated entities | Context repository after approved review; ownership system may remain referenced if it is primary |
| Environment classification and platform boundary | Store as curated policy/reference | Team/platform policy owner |
| PCF app name/GUID, Cloud project/region/service, stable FQDN | Store as deployment mapping with authority and validation evidence; warn when stale | Platform API or DNS is authoritative for observed existence/current mapping |
| Repository coordinates and default branch | Store as first-class repository data; optionally validate | Git provider |
| Runbook and architecture bodies | Store or reference their approved living Git location | Owning documentation repository/revision |
| Dashboard, saved search, SLO, pipeline, Jira/Confluence locations | Store typed locators/references, not copied content | Referenced system |
| Secret retrieval profile | Store only an opaque allowlisted reference | Secret manager/host credential policy |
| Current deployment/revision, health, instances, routes actually serving traffic | Retrieve live | Platform runtime |
| Current alerts, incidents, tickets, on-call person, metrics, logs, traces | Retrieve live | Alerting/incident/ticket/on-call/telemetry system |
| Dashboard JSON, current query results, build logs | Do not copy; retrieve when needed | Owning live/versioned system |

Document-level Git provenance is the default: entity path, full revision, owner, management mode,
and review state. Do not wrap every scalar as `{value, source}`. Add field-group provenance only to
facts whose authority/freshness differs materially from the document, especially platform bindings,
DNS/endpoints, generated records, and external resource locators.

Generated entities require `managedBy`, the authoritative `sourceRef`, generator identity, and
generation evidence. Humans do not edit generated entities. Staleness policy belongs to the entity
type or team policy, not an arbitrary timestamp copied onto every string. Expired or unverified
facts produce structured warnings and may fail an effect-capable consumer contract.

## 11. Validation and schema versioning

### Structural validation

- JSON Schema 2020-12 with pinned `$schema`, absolute immutable `$id`, and one schema per
  `apiVersion + kind`.
- Closed known objects (`unevaluatedProperties: false` when validator conformance is proven).
- Required fields, types, bounded strings/arrays, canonical ID patterns, lifecycle/classification
  enums, and typed platform alternatives.
- Explicit format assertion or semantic validation for URI, FQDN, UUID, date, and date-time fields.
- YAML duplicate-key and custom-tag rejection before schema validation.

### Semantic validation

- unique full IDs and aliases within their declared scopes;
- valid, kind-compatible references and no forbidden cycles;
- a service/environment coordinate resolves to the declared number of deployments;
- repository use has at least one role and a meaningful purpose;
- active effect-shaped runbooks have explicit environment applicability and safety metadata;
- no production default or effect-capable contract with an implicit environment;
- no secret-bearing keys/values; secret references use only approved opaque schemes;
- platform blocks do not use ambiguous generic IDs and satisfy platform-specific required fields;
- source paths stay inside approved roots; no traversal or unapproved remote schema fetch;
- consumer requirement paths resolve on positive fixtures and fail on missing/alternative fixtures;
- deterministic output is byte-identical for the same source, resolver, selector, and contract;
- the resolved projection stays inside its declared depth/byte budget.

Split optional network checks from offline validity. Repository existence, default branch, FQDN,
dashboard UID, Jira project, and runbook-link checks are valuable drift evidence but must report
unreachable/auth-blocked separately from structurally invalid. A temporary provider outage must not
make a valid Git commit unparsable.

### Versioning and migration

- Start at `sre-context/v1alpha1` while synthetic portability fixtures can still drive breaking
  changes through reviewed migrations. Do not claim compatibility during alpha.
- Prove generic alpha portability with at least two synthetic tenant fixtures and multiple consumer
  contracts using the same resolver without tenant-specific branches.
- Promote to operational `v1` only after that generic proof and at least one separately approved
  real-team onboarding uses the same contract without a schema fork or team-specific skill branch.
- A published schema URI is immutable. Breaking shape or meaning changes use a new version and a
  migration; changing only `apiVersion` without transforming fields is invalid.
- Writers emit one current version. Readers support the current version and, only during a declared
  migration window, the immediately previous version.
- Source entity, consumer requirement, and resolved-bundle versions evolve independently.
- Every migration has before/after fixtures, idempotency, explicit lossy-field handling, rollback or
  source-branch recovery, and a repository-wide dry-run report before write mode.

## 12. Security, secrets, and environment safety

- Store no password, token, private key, cookie, service key, connection string, copied environment
  output, or encrypted secret blob. Encryption does not turn the context repository into a secret
  manager.
- A secret reference is an opaque profile or approved secret-manager locator; it never contains the
  value and never implies the caller may retrieve it.
- Repository content, runbooks, imported Confluence text, live output, and resolver data remain
  untrusted data. None can select tools, widen authority, approve an effect, or override a consumer
  contract.
- Context selection is explicit and included in every resolved bundle and handoff. Environment and
  deployment are mandatory for any consumer that can change state.
- Production has `actionSelection: explicit-only`. There is no global, team, service, CLI, session,
  or alias default to production.
- Before an effect, the consumer echoes canonical team/service/environment/deployment IDs, exact
  target locators, source revision, and any stale warnings into the existing approval/effect gate.
- Valid context is identification evidence, not live-state verification. Re-read the target through
  the authoritative system before an action.
- The resolver is read-only in phase one. Any automatic discovery/update workflow is separate,
  least-privileged work with a reviewed source-to-generated contract.

## 13. Worked synthetic-fixture example

Every identity and locator below is a synthetic, non-operational fixture. Its source manifest must
declare `mode: fixture` and `nonOperational: true`; hostnames use reserved example domains; the
resolver may load it only with `--allow-fixtures`; and resolved output must retain both the fixture
provenance and `target.actionSelection: prohibited`. The names do not assert that these teams exist,
and the Cloud Run-shaped representation does not select Cloud Run for this fleet.

The example is intentionally small and omits unchanged envelope fields.

```yaml
# fixtures/tenant-alpha/team.yaml
apiVersion: sre-context/v1alpha1
kind: Team
metadata: {id: tenant-alpha, name: Fixture Team Alpha, lifecycle: active}
spec:
  description: Operates example transaction services.
  environmentRefs: [environment:tenant-alpha/development, environment:tenant-alpha/production]
  integrationRefs:
    - integration:tenant-alpha/jira
    - integration:tenant-alpha/grafana

---
# fixtures/tenant-alpha/services/checkout-api.yaml
apiVersion: sre-context/v1alpha1
kind: Service
metadata: {id: checkout-api, name: Checkout API, namespace: tenant-alpha, ownerRef: team:tenant-alpha, lifecycle: active}
spec:
  type: service
  description: Authorizes and creates checkout transactions.
  criticality: critical
  repositoryUses:
    - repositoryRef: repository:tenant-alpha/checkout-service
      roles: [source, test]
      purpose: Checkout implementation and component tests
    - repositoryRef: repository:tenant-alpha/transaction-delivery
      roles: [delivery, configuration]
      purpose: Promotion workflows and deployment manifests
  deploymentRefs:
    - deployment:tenant-alpha/checkout-development
    - deployment:tenant-alpha/checkout-production
  telemetryIdentity: {serviceName: checkout-api, serviceNamespace: tenant-alpha}

---
# fixtures/tenant-alpha/services/settlement-worker.yaml
apiVersion: sre-context/v1alpha1
kind: Service
metadata: {id: settlement-worker, name: Settlement Worker, namespace: tenant-alpha, ownerRef: team:tenant-alpha, lifecycle: active}
spec:
  type: worker
  description: Settles completed payment batches.
  criticality: high
  repositoryUses:
    - repositoryRef: repository:tenant-alpha/settlement
      roles: [source, data]
      purpose: Worker code and settlement database migrations
  deploymentRefs: [deployment:tenant-alpha/settlement-production]

---
# fixtures/tenant-beta/team.yaml
apiVersion: sre-context/v1alpha1
kind: Team
metadata: {id: tenant-beta, name: Fixture Team Beta, lifecycle: active}
spec:
  description: Operates example authentication services.
  environmentRefs: [environment:tenant-beta/test, environment:tenant-beta/production]
  integrationRefs: [integration:tenant-beta/jira, integration:tenant-beta/grafana]

---
# fixtures/tenant-beta/services/authentication-api.yaml
apiVersion: sre-context/v1alpha1
kind: Service
metadata: {id: authentication-api, name: Authentication API, namespace: tenant-beta, ownerRef: team:tenant-beta, lifecycle: active}
spec:
  type: service
  description: Issues and validates customer authentication sessions.
  criticality: critical
  repositoryUses:
    - repositoryRef: repository:tenant-beta/authentication
      roles: [source, test, documentation]
      purpose: Authentication implementation, contract tests, and protocol documentation
  deploymentRefs:
    - deployment:tenant-beta/authentication-test-cloud-run
    - deployment:tenant-beta/authentication-production-cloud-run
  telemetryIdentity: {serviceName: authentication-api, serviceNamespace: tenant-beta}
```

Representative deployments remain separate:

```yaml
# Fixture team alpha PCF production
apiVersion: sre-context/v1alpha1
kind: Deployment
metadata: {id: checkout-production, name: Checkout production, namespace: tenant-alpha, ownerRef: team:tenant-alpha, lifecycle: active}
spec:
  serviceRef: service:tenant-alpha/checkout-api
  environmentRef: environment:tenant-alpha/production
  platform:
    type: cloudfoundry
    cloudfoundry:
      foundationRef: platform:shared/pcf-prod-east
      organization: fixture-team-alpha
      space: production
      applicationName: checkout-api
      applicationGuid: abc123
  endpoints: [{id: public, kind: https, fqdn: checkout.example.com, purpose: customer-api}]
  observabilityRefs: [resource:tenant-alpha/checkout-prod-dashboard]

---
# Fixture team beta Cloud Run production
apiVersion: sre-context/v1alpha1
kind: Deployment
metadata: {id: authentication-production-cloud-run, name: Authentication production, namespace: tenant-beta, ownerRef: team:tenant-beta, lifecycle: active}
spec:
  serviceRef: service:tenant-beta/authentication-api
  environmentRef: environment:tenant-beta/production
  platform:
    type: gcp
    gcp:
      projectRef: platform:shared/gcp-fixture-project
      region: us-central1
      cloudRun:
        serviceName: authentication-api
  endpoints: [{id: public, kind: https, fqdn: auth.example.com, purpose: authentication-api}]
  observabilityRefs: [resource:tenant-beta/auth-prod-dashboard]
```

The service-readiness consumer receives only the selected effective context, repository uses,
runbook/dependency references, and platform/observability locators. It does not load the other team,
the other service, shared knowledge bodies, or live dashboard state.

## 14. Target team-onboarding workflow

After the alpha schemas and resolver exist, onboarding a team should be a reviewable data workflow:

1. Add the Team entity with its canonical ID, owner, boundary, escalation/on-call references, and
   approved integration endpoints.
2. Add optional Systems and the supported Services with canonical IDs, aliases, owners, types,
   criticality, and purpose.
3. Add the team's Environment profiles and classify their safety/change boundaries. Do not select a
   default production environment.
4. Register Repository entities and attach each Service's repository uses, roles, paths, and purpose.
5. Add Deployment bindings with qualified platform identities, regions, endpoints/FQDNs, deployment
   and rollback references, and authoritative provenance for discovered mappings.
6. Add typed observability, health, SLO, log, pipeline, configuration, dependency, data/recovery,
   and capacity references that materially apply.
7. Add Jira/change-system and Confluence/import-source references without copying current tickets or
   treating Confluence as a second living runbook home.
8. Add or reference Runbooks and operational knowledge. Fill only metadata the resolver/index uses;
   leave executable automation in its authoritative system.
9. Run offline structural and semantic validation, then separately run approved network/drift checks.
   Resolve every error and explicitly disposition warnings that affect the selected consumer.
10. Resolve representative read-only contexts for each Service/Environment, review the exact bundle
    and provenance, and merge through the team's ownership rules. Generalized skills remain unchanged
    unless their consumer-owned requirement contract genuinely needs a new portable field.

The onboarding result is a schema-valid, review-accepted context source. It is not proof that a live
service is healthy, a runbook works, an alert routes, a deployment is current, or an effect is
authorized; those remain separate readiness and runtime evidence.

## 15. Additional SRE context not explicit in the request

Only add a field when an operational decision consumes it. The following concepts meet that bar.

| Concept | Why needed | Belongs | Static/dynamic/reference | Required | Authority |
|---|---|---|---|---|---|
| User journeys and blast-radius vocabulary | Lets incident response translate a component failure into affected users/business outcomes | Service or System | Curated static + reference to product docs | Required for user-facing critical services | Product/service owner |
| Dependency direction and failure effect | Investigation needs upstream/downstream traversal and the consequence of failure, not merely a name | Service relationship | Curated reference; current health is live | Required when a material dependency exists | Owning service definition plus dependency owner review |
| Stateful/data profile | Changes recovery, diagnosis, backup, privacy, and migration requirements | Service | Curated classification + references | Required for stateful or sensitive services | Data/service owner; policy system for classification |
| SLI/SLO and health authority | Defines what healthy means and which signal should drive incident decisions | Service/Deployment resource refs | Reference; current measurements live | Required for critical/high active services, otherwise readiness gap | Versioned SLO/health definition and observability backend |
| RTO/RPO and last restore/recovery evidence | Prevents “backup exists” from being treated as recoverable | Service data/reliability profile | Curated objectives + evidence references; latest job state live | Required for stateful critical/high services | Business/service owner for objective; backup system/drill record for evidence |
| Deployment, promotion, and rollback sources | Agents must know where changes originate and how recovery is governed | Deployment resource refs | Stable references; current run/revision live | Required for active deployments | CI/CD and platform control plane |
| Platform ownership boundary | Stops app teams from operating foundation/org infrastructure outside their lane | Team and Deployment | Curated policy reference | Required for each platform type used | Platform/team operating agreement |
| Data/security classification | Controls redaction, access, retention, and whether external tools may receive content | Service and Resource | Curated classification; access decision live | Required when non-public data exists | Security/data governance system |
| Ingress, egress, and dependency endpoints | Materially narrows network-failure hypotheses and exposure review | Deployment and dependency refs | Stable policy/location refs; actual flows live | Optional until a networked consumer needs it; required for critical external edges | Network/service definitions and observed platform |
| Capacity, quota, and limit references | Saturation investigation needs the controlling limit and escalation path | Deployment/Resource | Reference; current usage and quota live | Required where a known quota can stop service | Platform/cloud provider and service owner |
| Lifecycle, deprecation, and replacement | Prevents agents from treating retired systems or migration targets as current | Every entity | Curated static | Required | Owning team's approved roadmap/record |
| Feature-flag and configuration authorities | Explains where behavior can change without a code deploy | Service/Deployment resource refs | Reference; current values live | Required when flags/config materially alter runtime behavior | Flag/configuration system |
| Incident communications and status-page references | Speeds correct stakeholder communication without copying an active incident | Team/System | Stable reference; active incident state live | Required only for externally significant services | Incident-management policy/system |
| Cost/billing owner and budget reference | Cloud or vendor incidents may be quota/budget-related and remediation may create cost | Team/Platform/Deployment | Stable reference; current spend live | Optional unless budget/quota can stop service | FinOps/cloud billing system |

## 16. Deliberately exclude from the canonical context

- passwords, tokens, private keys, cookies, service keys, secret values, and encrypted secret blobs;
- current alerts, incidents, Jira tickets, deployments, pods/instances, health, metrics, logs, traces,
  dashboards, on-call person, or build output;
- copies of manifests, alert queries, dashboard JSON, CI definitions, API specifications, or
  repository documentation that already has an authoritative versioned location;
- platform-generated instance IDs and Kubernetes object UIDs whose lifetime is shorter than the
  catalog service;
- arbitrary executable templates, shell commands, dynamic expressions, or code embedded in YAML;
- general-purpose inheritance, YAML anchors/merge keys, unbounded custom maps, and silently accepted
  unknown fields;
- skill instructions, routing rules, approvals, credentials, or tool authority in team data;
- a default team/service/environment stored in the repository for effectful work;
- a second incident, ticket, alert, or deployment state ledger;
- metadata whose only purpose is completeness theater and has no validator, resolver, lookup,
  safety, or operational consumer.

## 17. Staged implementation plan

| Stage | Scope | Evidence and exit | Rollback / stop condition |
|---|---|---|---|
| 0. Owner decision and ADR | Accept/revise the entity graph, central-first/federatable source boundary, `Service`/`System` terminology, no-general-inheritance rule, generic fixture policy, and security boundary | Accepted ADR names contract owner, resolver owner, synthetic-alpha scope, and non-goals; no team-specific values are required | Stop with this proposal; no schemas or skill edits if the owner rejects the boundary |
| 1. Contract skeleton | Create `sre-context` with source schemas, catalog, validator/indexer skeleton, fixtures, and contributor rules; no live discovery and no MCP | Red-first tests reject duplicate YAML keys, unknown fields, duplicate IDs/aliases, broken refs, ambiguous deployments, implicit production, secret-bearing fields, and nondeterministic output | Delete/revert the new unpublished repository/branch; no existing skill depends on it |
| 2. First synthetic-tenant read-only proof | Model one fixture tenant with two services, two environments, repositories, runbook refs, integrations, and deployments; add one `service-readiness-audit` requirement sidecar and explicit resolver invocation | Same skill works for both services without tenant branches; fixture opt-in and non-operational/action-prohibited markers survive resolution; missing data fails clearly; resolved bundle stays within budget | Remove the optional fixture invocation and sidecar; existing manual caller-supplied workflow remains |
| 3. Second synthetic-tenant portability proof | Add a fixture tenant with a different platform representation, repository mix, and integrations; run the same resolver and read-only consumer contract | No schema fork, tenant-specific skill edit, implicit fallback, alias ambiguity, non-example locator, or lost fixture taint; migration fixtures cover alpha changes | If the contract cannot represent both without a generic bag, revise alpha before operational onboarding rather than adding exceptions |
| 4. Selected fleet adoption | Add consumer-owned requirements to the smallest related read-only skills first, then approved effect-capable skills with exact selection handoff | Positive, missing-context, wrong-team, ambiguous-alias, stale-platform, and production-selection cases pass; existing component tests/evals remain green | Each consumer change is independently removable; do not big-bang rewrite every skill |
| 5. Onboarding and drift evidence | Make context creation/validation a bounded service-onboarding step; add optional authenticated link/platform validation with provenance | Ten-step onboarding can produce a valid context packet; network failure remains distinct from invalid config; generated facts cannot be hand-edited | Keep offline source validation; disable optional probes without invalidating the catalog |
| 6. Optional adapters | Evaluate Backstage import/export, federated sources, and a read-only MCP list/read/templates facade | Exact source revisions, URI authorization, pagination, projection budgets, and adapter parity tests pass; no adapter becomes a second model | CLI/file resolver remains canonical; remove the adapter if operational burden exceeds measured value |
| 7. v1 promotion | Freeze only after the two-fixture generic proof, multiple consumers, and one separately approved real-team onboarding demonstrate portability without a fork or branch | Immutable schemas/catalog, migration policy, support window, threat model, owner/runbook, and independent exact-revision review accepted | Remain alpha; do not promise compatibility based on structural or synthetic evidence alone |

Do not create the largest possible schema in stage one. The first vertical slice is successful only
when one unchanged read-only skill can resolve two different services from configuration and fails
closed when a required fact or exact environment is missing.

## 18. Risks, open decisions, and recommendation

| Decision | Recommendation | Remaining evidence |
|---|---|---|
| Central versus federated source | One central Git repo first; source-independent resolver contract | Team count, permission boundaries, and expected change volume |
| Canonical operational noun | `Service` for deployable/operable unit; optional `System` for composite application | Owner acceptance and mapping of current service cards |
| Runbook location | Index both central and service-repository runbooks; do not force migration | Synthetic proof plus later onboarding ergonomics |
| Inheritance | References only in v1 | Measure residual duplication after two fixtures; confirm during later onboarding |
| Resolver implementation language/library | Defer until repository/toolchain constraints and JSON Schema/YAML validator behavior are tested | Windows behavior, duplicate-key rejection, 2020-12/format support, dependency policy |
| Consumer contract location | Sidecar with the skill, schema defined by the context contract | Generator/package behavior and host loading test |
| MCP | Optional read-only adapter after CLI contract | Stable host support, URI authorization, context-size behavior |
| Provenance granularity | Document-level by default; field-group only for platform/resource authority/freshness | Fixture staleness cases, then later operational validation |
| Organization entity | Omit until a real cross-org consumer exists | Organization count and shared-policy need |

**Recommendation:** accept the architecture direction and authorize stages 1–3 as one bounded,
synthetic generic alpha. Keep real-team onboarding and stage 4 fleet adoption behind that evidence
and a separate exact-scope owner decision. The proposed central repository is the right initial
operating shape; it is not the logical architecture, a runtime control plane, or the authority for
every referenced system.

## 19. Requested-deliverable coverage

| # | Deliverable | Section |
|---:|---|---|
| 1 | Current repository assessment | 1 |
| 2 | Research findings | 2 and Evidence method |
| 3 | Recommended architecture | Conclusion and 3 |
| 4 | Repository layout | 3 |
| 5 | Context hierarchy | 4 |
| 6 | Proposed schemas | 5 |
| 7 | Team-level fields | 5 |
| 8 | Application/service-level fields | 5 |
| 9 | Environment-level fields | 5 |
| 10 | Repository model | 5 |
| 11 | Runbook/knowledge model | 5 |
| 12 | Context-contract model | 6 |
| 13 | Resolution mechanism | 7 |
| 14 | Inheritance/override rules | 8 |
| 15 | Canonical ID/alias strategy | 9 |
| 16 | Static/dynamic rules | 10 |
| 17 | Source-of-truth/provenance strategy | 10 |
| 18 | Validation strategy | 11 |
| 19 | Schema versioning strategy | 11 |
| 20 | Security/secrets boundaries | 12 |
| 21 | Multi-team/application/repository/environment examples | 13 |
| 22 | Additional SRE context | 15 |
| 23 | Deliberate exclusions | 16 |
| 24 | Staged implementation plan | 17 |

## Primary source register

### Local canonical sources

- [`AGENTS.md`](../../AGENTS.md)
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
- [`stack-profile`](../../skills/stack-profile/SKILL.md)
- `service-onboarding` (renamed to `service-lifecycle` after this review)
- [`service-readiness-audit`](../../skills/service-readiness-audit/SKILL.md)
- [`operational-learning`](../../skills/operational-learning/SKILL.md)
- [Runbook frontmatter v1](../../schemas/runbook-frontmatter-v1.schema.json)
- [Schema compatibility](../schema-compatibility.md)

### Official contracts

- [Backstage descriptor format](https://backstage.io/docs/features/software-catalog/descriptor-format/),
  [system model](https://backstage.io/docs/features/software-catalog/system-model/), and
  [catalog graph](https://backstage.io/docs/features/software-catalog/creating-the-catalog-graph/)
- [Score overview](https://docs.score.dev/docs/) and
  [specification reference](https://docs.score.dev/docs/score-specification/score-spec-reference/)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [Kubernetes API conventions](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md),
  [names/UIDs](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/), and
  [labels/selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)
- [OpenTelemetry service](https://opentelemetry.io/docs/specs/semconv/resource/service/),
  [deployment environment](https://opentelemetry.io/docs/specs/semconv/resource/deployment-environment/),
  [cloud](https://opentelemetry.io/docs/specs/semconv/resource/cloud/), and
  [Kubernetes](https://opentelemetry.io/docs/specs/semconv/resource/k8s/) semantic conventions
- [OpenGitOps principles 1.0.0](https://opengitops.dev/)
- [MCP stable resources 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)
- [RFC 6570 URI Templates](https://www.rfc-editor.org/rfc/rfc6570.html)

### GitHits upstream implementation evidence

- Backstage `de92faeb4a375af5bd4f7a84311e702736e98964`:
  [system model](https://github.com/backstage/backstage/blob/de92faeb4a375af5bd4f7a84311e702736e98964/docs/features/software-catalog/system-model.md#L15-L141),
  [descriptor format](https://github.com/backstage/backstage/blob/de92faeb4a375af5bd4f7a84311e702736e98964/docs/features/software-catalog/descriptor-format.md#L159-L236),
  [entity references](https://github.com/backstage/backstage/blob/de92faeb4a375af5bd4f7a84311e702736e98964/docs/features/software-catalog/references.md#L11-L21), and
  [catalog API projection](https://github.com/backstage/backstage/blob/de92faeb4a375af5bd4f7a84311e702736e98964/docs/features/software-catalog/api.md#L204-L224)
- Score specification `1c2427db4e1c96e05956e0546e767fc994a5421d`:
  [scope and environment separation](https://github.com/score-spec/spec/blob/1c2427db4e1c96e05956e0546e767fc994a5421d/README.md#L53-L63) and
  [JSON Schema](https://github.com/score-spec/spec/blob/1c2427db4e1c96e05956e0546e767fc994a5421d/score-v1b1.json#L1-L92)
- Runme `dea82115348945835f326f75db0a35c37c5a4100`:
  [human-readable notebook/runbook model](https://github.com/runmedev/runme/blob/dea82115348945835f326f75db0a35c37c5a4100/README.md#L7-L30) and
  [namespaced frontmatter](https://github.com/runmedev/runme/blob/dea82115348945835f326f75db0a35c37c5a4100/document/frontmatter.go#L27-L152)
- Rundeck `a462982aa22bf350c9e121d213283ffaa7994b4e`:
  [executable job definition](https://github.com/rundeck/rundeck/blob/a462982aa22bf350c9e121d213283ffaa7994b4e/rundeckapp/grails-spa/packages/ui-trellis/src/library/types/jobs/JobDefinition.ts#L1-L95)

These findings remain implementation/adoption evidence and do not override the official contract or
the local workspace.
