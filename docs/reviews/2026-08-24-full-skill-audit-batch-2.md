# Full skill audit — batch 2: engineering and build

> **Status: review evidence, not a second backlog.** This batch audits exactly five canonical
> skills on the revision named below. Recommendations not implemented here require a new owner
> decision before they become work.

**Audit baseline:** `87d3d8cdd80ac9caeef5c4ee2d8021c1f596e243`
**Batch scope:** `backend-craft`, `frontend-craft`, `ci-actions`, `database-reliability`, and
`ops-tooling`
**Audit date:** 2026-08-24

## Conclusion

The five skills have distinct ownership and strong verification boundaries. Four need small
corrections; `database-reliability` should remain unchanged. This batch implements six bounded
improvements:

1. Correct backend liveness/readiness semantics and make the OpenAPI starter expose distinct
   endpoints.
2. Require `stack-profile` before the backend or frontend greenfield stack reference can recommend
   a framework or tool.
3. Prevent React-only form, chart, and component-test libraries from leaking into Vue work.
4. Correct the claim that React 19 form Actions replace every mutation-form submit handler.
5. Scope the reusable CI starter's concurrency key to the calling workflow as well as the ref.
6. Let the operator CLI starter complete its side-effect-free dry run before requiring a credential
   used only by the apply path.

No description, routing metadata, agent, skill, dependency, graph, retry loop, or production
authority changes in this batch.

## Method and evidence

### Local baseline

- `[verified]` The baseline contains 30 canonical skill entrypoints totaling 193,143 Git-object
  bytes. Batch 2 entrypoints range from 5,970 to 13,827 bytes.
- `[verified]` All 45 files in the five bundles were inspected: 33 references, seven assets, and
  five entrypoints. Every supporting file is predicate-linked from its entrypoint.
- `[verified]` The exact tree committed as the Batch 2 baseline passed 28 link tests, the live link
  check, 42 fleet-validator tests, all 84 scenario definitions, 553 grader checks, and strict
  plugin validation immediately before this batch began.
- `[verified]` Only `database-reliability` has an executable scenario in the current suite: one
  direct safety case that rejects an irreversible one-shot `DROP COLUMN`. The other four skills
  have no targeted discovery or direct scenario.
- `[verified]` A new focused standard-library regression failed three of three tests before the
  initial asset edits: the OpenAPI starter lacked `/readyz`, the reusable workflow omitted
  `github.workflow` from its concurrency group, and the CLI credential check preceded the dry-run
  return. A fresh independent review then found that the new readiness path documented only its
  success response and that the assertions were too broad. The strengthened test rejected a
  commented-out `503`, an `apply(plan)` call in the dry-run branch, and exit-before-emit ordering;
  all three asset contracts passed again after each named mutant was removed.
- `[verified]` After the changes, the test-layout check, 28 link tests, live link check, 42
  fleet-validator tests, 84-scenario schema validation, 553 grader checks, Python compilation, YAML
  parsing, and strict plugin validation all passed.
- `[unverified]` No live routing trial was run. No routing description changed, and the repository
  contract does not require a paid discovery campaign for body/reference/asset corrections.
- `[unverified]` The optional CLI starter could not be executed end to end in this checkout because
  Typer is deliberately not a repository dependency. Its ordering contract is verified by parsing
  the Python AST; a copied implementation still needs its target repository's runtime tests.

### Current external contracts

- `[sourced, OpenAI model guidance]` [OpenAI's current prompting guidance](https://developers.openai.com/api/docs/guides/latest-model)
  recommends starting from a working prompt, changing one instruction group at a time, retaining
  requirements-bearing detail, and rerunning representative checks rather than assuming a rewrite
  improved behavior.
- `[sourced, Spring-specific]` [Spring Boot 4.1 probe guidance](https://github.com/spring-projects/spring-boot/blob/v4.1.0/documentation/spring-boot-docs/src/docs/antora/modules/reference/pages/actuator/endpoints.adoc)
  keeps liveness process-local and says shared external dependencies are not included in readiness
  by default; the operator must decide whether withdrawing every instance helps or merely converts
  a dependency outage into a full traffic outage.
- `[sourced, React-specific]` The current React [`<form>` reference](https://react.dev/reference/react-dom/components/form)
  documents both `onSubmit` and function-valued `action`; [`useActionState`](https://react.dev/reference/react/useActionState)
  composes with an action but is not a mandate for every React 19 mutation form.
- `[sourced, Vue-specific]` Current [Vue form guidance](https://vuejs.org/guide/essentials/forms.html)
  uses Vue's `v-model` contract. React package choices are not portable into a Vue target.
- `[sourced, GitHub-specific]` [GitHub Actions concurrency guidance](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
  says concurrency groups are repository-wide and recommends including `github.workflow` to avoid
  one workflow cancelling another on the same ref.
- `[verified, upstream refs]` The starter pins resolve exactly: `actions/checkout` v7.0.1 is
  `3d3c42e5aac5ba805825da76410c181273ba90b1`, and `astral-sh/setup-uv` v10.0.1 is
  `20cfd1bf945f4377ade1205e4dbc17946fc9a30d`.
- `[sourced, PostgreSQL-specific]` PostgreSQL 18 documents
  [`ADD table_constraint [ NOT VALID ]`](https://www.postgresql.org/docs/18/sql-altertable.html)
  for not-null constraints and [virtual generated columns as the default](https://www.postgresql.org/docs/18/ddl-generated-columns.html).
- `[sourced, SQL Server-specific]` Microsoft's current
  [`ALTER TABLE` reference](https://learn.microsoft.com/en-us/sql/t-sql/statements/alter-table-transact-sql)
  supports the reference's metadata-only Enterprise path and documents the type, row-size, online
  alteration, and extra-space limitations.
- `[verified, GitHits]` Current npm package graphs show `react-hook-form@7.86.0` and
  `recharts@3.10.1` declare React peers. That implementation evidence supports scoping those choices
  to React rather than presenting them as Vue defaults.

## Skill: `backend-craft`

### Overall Assessment

**Minor Changes**

### Purpose

Owns implementation of APIs, services, workers, schedulers, webhooks, and outbound integration
clients, with failure-first contracts, operability, security, testing, and explicit boundaries to
frontend, live database operations, and language mechanics.

### Findings

- **Routing:** The action-shaped description covers endpoints, services, workers, and API clients
  and names the three closest owners. No current scenario measures its discovery or direct behavior.
- **Instructions:** The contract-first sequence, conditional resource table, and execute-verify-
  report gate are explicit. One global instruction was unsafe: it equated readiness with all
  dependencies being reachable.
- **Accuracy:** **Incorrect** for the old readiness shorthand; a shared dependency check can make
  every replica unready during the same outage. **Verified** for the corrected process-local
  liveness and traffic-admission readiness distinction. Core RFC 9457, HTTP, pagination, timeout,
  retry, and authorization guidance is **Likely correct** and target versions remain gated.
- **Context:** The 10,814-byte baseline entrypoint keeps framework, auth, persistence, live-data,
  background-work, and upstream detail in nine conditional references. The repeated external-call
  reminders in `consuming-apis.md` are deliberate at the integration boundary; no safe extraction
  justified itself in this batch.
- **References / Assets / Scripts:** The OpenAPI starter contradicted the entrypoint by labelling one
  path as both liveness and readiness and omitting `/readyz`. The corrected starter now carries the
  two explicit paths. No new script or schema layer is needed.
- **Tools:** Timeouts, bounded retries, pagination, typed response parsing, dry-run/effect separation,
  and result validation are well specified. Greenfield tool selection now loads `stack-profile`
  before the local default.
- **Orchestration:** Frontend consumes the versioned contract; `database-reliability` owns live-data
  safety; `reviewer` is required for sensitive auth work. These are ownership handoffs, not
  unconditional context loads.
- **Failure Handling:** Dependency degradation, retry safety, circuit breaking, graceful shutdown,
  partial upstream data, and validation failures have explicit behavior and stop conditions.
- **Verification:** The quality gate requires real requests, redacted evidence, contract tests, and
  failure-path tests. The starter health split now has a focused regression.
- **Portability:** HTTP and OpenAPI rules are portable. FastAPI, Spring Boot, PCF, and the team stack
  are conditional/internal choices and remain labelled as such.

### Routing Tests

#### Should trigger

1. “Add a cursor-paginated FastAPI endpoint and its contract tests.”
2. “Build a typed client for this third-party API with rate-limit handling.”
3. “Implement a signed inbound webhook that queues durable processing.”

#### Should not trigger

1. “Tune this live PostgreSQL query and diagnose its lock waits.”
2. “Build the React form that consumes the existing API.”
3. “Investigate why the production app is timing out right now.”

#### Boundary cases

1. “Build an endpoint and a page for it” — backend owns the service contract; frontend owns the UI.
2. “Write the migration code and assess running it on a hot table” — backend writes the persistence
   change; database reliability owns live execution safety.

**Evaluation:** `[unverified]` No targeted scenario or representative traffic sample supports a
precision or recall estimate. The explicit ownership map is strong static evidence only.

### Recommended Changes

#### Change 1 — correct health semantics and the starter

- **Problem:** Readiness was defined as generic dependency reachability, and the starter exposed one
  combined liveness/readiness endpoint.
- **Evidence:** Current Spring guidance warns that shared-dependency readiness can withdraw every
  replica and amplify the outage; the starter lacked `/readyz`.
- **Change:** Keep liveness process-local, define readiness as traffic admission with selective
  dependency inclusion, and add distinct `/healthz` and `/readyz` starter paths with explicit
  ready and not-ready responses.
- **Expected improvement:** Prevents restart/cascading-failure amplification and keeps generated
  service contracts aligned with the instructions.
- **Risk/tradeoff:** Readiness design now requires workload judgment; a single generic dependency
  checklist was simpler but operationally unsafe.

#### Change 2 — load the stack authority before a greenfield choice

- **Problem:** The greenfield reference could recommend a framework without first loading the
  repository's canonical current-stack and platform boundary.
- **Evidence:** `docs/rules.md` and `stack-profile` require that load before runtime/tool changes.
- **Change:** Route greenfield selection through `stack-profile`, then the backend stack reference.
- **Expected improvement:** Keeps tool choices current and in lane without preloading stack facts for
  ordinary changes in an established repository.
- **Risk/tradeoff:** A true greenfield decision consumes one additional reference; that context is
  decision-bearing.

### Keep As-Is

- Keep one living API contract, top-level RFC 9457 errors, explicit response-model allowlists, and
  bounded version overlap.
- Keep failure matrices conditional on route behavior rather than inventing irrelevant test rows.
- Keep external-call and persisted-state mechanics in separate predicate-linked references.
- Keep production execution with the human release owner.

## Skill: `frontend-craft`

### Overall Assessment

**Minor Changes**

### Purpose

Owns implementation and verification of product web UIs, including layout, state, resilience UX,
accessibility, framework mechanics, forms, data views, visualization, authentication UX, and PCF
serving, while excluding Grafana dashboards and backend services.

### Findings

- **Routing:** The description is action-shaped and distinguishes app dashboards from Grafana. Its
  “TypeScript/React” ownership shorthand is narrower than the bundle's React-and-Vue support, but no
  observed misroute justifies a description edit or paid routing campaign.
- **Instructions:** The entrypoint has a concrete quality gate and strongly separates server state,
  UI state, URL state, and failure state. Two shared references and the core component-test rule
  incorrectly applied React-only package defaults after the Vue predicate selected them.
- **Accuracy:** **Incorrect** for the old claim that React 19 form Actions replace every manual
  submit handler. Current React supports both `onSubmit` and actions. **Incorrect** for presenting
  React packages as framework-neutral form/chart defaults. Other inspected React and Vue lifecycle,
  hydration, security, and reactivity claims are **Likely correct** and version-gated.
- **Context:** The 13,827-byte baseline entrypoint is the largest in this batch but still routes ten
  specialized concerns to focused references. Its visual language is intentionally detailed and
  requirement-bearing; shortening it without a design-quality regression would be preference, not
  evidence.
- **References / Assets / Scripts:** React and Vue have separate deep references, but the shared
  `forms` and `data-viz` files needed framework branches; the core test rule now defers to the
  target repository's component-testing layer. No asset or deterministic script would improve
  semantic UI judgment.
- **Tools:** The target repository's typecheck, lint, framework-appropriate component-test, build,
  browser, accessibility, and screenshot tools remain authoritative. Stack/tool recommendations
  now load `stack-profile`.
- **Orchestration:** Backend owns the contract; language idiom supplies universal TypeScript rules;
  frontend owns component/framework behavior. The references compose without an extra agent.
- **Failure Handling:** Loading, empty, timeout, retry, rollback, panel boundary, stale work, and
  cleanup behavior are explicit for both React and Vue.
- **Verification:** Real-browser and keyboard passes are required after component/unit checks. No
  current scenario measures routing or the framework-reference selection.
- **Portability:** Accessibility and interaction rules are portable. React, Vue, TanStack, Mantine,
  Recharts, Tremor, Vite, Tailwind, and PCF instructions are framework/internal choices and now stay
  inside matching predicates.

### Routing Tests

#### Should trigger

1. “Build a Vue settings form with accessible validation and failure states.”
2. “Add a React table page whose filters survive refresh and back navigation.”
3. “Fix this SPA dialog's focus trap and keyboard behavior.”

#### Should not trigger

1. “Create a Grafana operations dashboard for this SLO.”
2. “Add the API endpoint behind this existing form.”
3. “Build a new operator CLI with requirements, review, and mission verification.”

#### Boundary cases

1. “Add a product chart to the app and a Grafana panel for on-call” — split frontend product UI
   from `obs-dashboards` operations work.
2. “Fix a TypeScript state bug inside a React component” — frontend owns component/state behavior;
   `language-idiom` supplies universal TypeScript mechanics.

**Evaluation:** `[unverified]` No targeted scenario or representative traffic sample supports
precision or recall. The batch does not infer routing quality from prose alone.

### Recommended Changes

#### Change 1 — scope shared resources by selected framework

- **Problem:** A Vue form, chart, or core test task loaded guidance that prescribed React-only
  packages.
- **Evidence:** Current Vue docs use `v-model`; GitHits package graphs show React peers for
  `react-hook-form` and Recharts.
- **Change:** Preserve the target repository's form, chart, and component-testing layer; name the
  package defaults only for the React greenfield branch and leave Vue on its established Vue layer.
- **Expected improvement:** Prevents invalid imports and accidental framework migration while
  preserving strong React defaults.
- **Risk/tradeoff:** A greenfield Vue project no longer receives a single prescribed chart/form
  library; selecting one requires repository/team evidence.

#### Change 2 — make React 19 actions conditional

- **Problem:** The reference treated one React 19 form mechanism as a universal replacement and
  discouraged still-supported event-handler/library paths.
- **Evidence:** Current React documents both forms and makes action-specific hooks compositional.
- **Change:** Use actions when their transition/pending/Server Function behavior fits; otherwise
  keep the repository's `onSubmit` or form-library contract.
- **Expected improvement:** More accurate framework guidance and fewer unnecessary form rewrites.
- **Risk/tradeoff:** The model must choose between two valid forms based on repository/workflow
  context rather than following one absolute rule.

#### Change 3 — load stack facts before greenfield selection

- **Problem:** The frontend stack reference could choose tools without the canonical current-stack
  boundary.
- **Evidence:** The repository requires `stack-profile` before runtime or tool recommendations.
- **Change:** Load `stack-profile` only when the greenfield-stack predicate matches, then load the
  local frontend stack reference.
- **Expected improvement:** Current, in-lane recommendations with no extra context for ordinary UI
  work.
- **Risk/tradeoff:** One additional conditional reference for genuine stack decisions.

### Keep As-Is

- Keep real-browser, keyboard, and rendered-state verification after static/component checks.
- Keep React and Vue mechanics in separate version-aware references.
- Keep failure UX, accessibility, URL state, and API contract generation as first-class behavior.
- Keep Grafana operations dashboards outside this skill.

## Skill: `ci-actions`

### Overall Assessment

**Minor Changes**

### Purpose

Authors and repairs GitHub Actions workflows with least privilege, event-trust boundaries,
immutable dependencies/artifacts, protected environments, bounded execution, and human-owned
deployment authority.

### Findings

- **Routing:** CI setup, deploy-job authoring, failures, and hardening are clear. The description's
  OIDC term is valid for a future target but the body correctly states that current PCF uses
  environment secrets.
- **Instructions:** Local-first inspection, smallest workflow shape, trust-path design, narrow
  changes, and layered verification form a complete method.
- **Accuracy:** **Incorrect** in the reusable starter's old concurrency key: groups are repository-
  wide, not isolated per workflow. **Verified** after adding `github.workflow`. Exact action pins
  match their named upstream tags. Remaining environment, runner, permission, event, and
  provenance claims are **Likely correct** and current-source labelled.
- **Context:** The 7,282-byte entrypoint routes security/provenance, execution/runners, PCF deploy,
  and the starter independently. Simple syntax failures need no reference.
- **References / Assets / Scripts:** One optional reusable starter is appropriate. A project-owned
  workflow suppresses it, preventing parallel-pipeline creation.
- **Tools:** Static linting, trusted run evidence, immutable pins, protected secrets, and exact
  artifact promotion are distinguished. Imported workflows are never executed locally.
- **Orchestration:** Build and deploy are separated; production credentials release only after the
  protected-environment human gate. CI evidence does not self-approve deployment.
- **Failure Handling:** Untrusted forks, cache poisoning, runner drift, timeouts, cancellations,
  missing secrets, and static/runtime evidence gaps are explicit.
- **Verification:** Static checks, red-to-green contract checks, and a trusted non-deploy CI run are
  layered. The concurrency starter now has a deterministic regression.
- **Portability:** GitHub expressions, events, environments, runner groups, attestations, and action
  pins are GitHub-specific. Least privilege, immutable artifacts, and trust-boundary separation are
  portable principles.

### Routing Tests

#### Should trigger

1. “Create a reusable GitHub Actions test workflow for these supported Python versions.”
2. “Why does this Actions job fail only on our self-hosted runner?”
3. “Harden this `pull_request_target` workflow and its permissions.”

#### Should not trigger

1. “Deploy this artifact to production PCF now.”
2. “Fix the application test that the workflow correctly reports as failing.”
3. “Write a local PowerShell release helper with no CI changes.”

#### Boundary cases

1. “Design GCP workload identity for Actions” — this skill owns workflow identity, but must load
   `stack-profile` and keep the landing runtime/identity decision unverified.
2. “The workflow is green but production is unhealthy” — CI reports artifact/run evidence; incident
   and deployment verification stay with their owning lanes.

**Evaluation:** `[unverified]` No targeted scenario measures discovery or behavior.

### Recommended Changes

#### Change 1 — isolate reusable-workflow cancellation domains

- **Problem:** Different workflows using the starter on the same ref shared one concurrency group
  and could cancel each other.
- **Evidence:** GitHub documents concurrency keys as repository-wide and recommends including the
  workflow name.
- **Change:** Set the group to `${{ github.workflow }}-${{ github.ref }}`.
- **Expected improvement:** Superseded runs still cancel within one workflow/ref without cancelling
  unrelated workflows.
- **Risk/tradeoff:** Concurrent workflows on the same ref now run independently and may consume more
  runner capacity; that is the correct isolation boundary.

### Keep As-Is

- Keep explicit permissions, full-SHA/action and digest/container pinning, and untrusted-event rules.
- Keep the current environment-secret decision distinct from a future documented OIDC exchange.
- Keep build-once/promote-the-same-artifact and non-cancellable production deployment.
- Keep static, trusted-run, and production evidence as separate layers.

## Skill: `database-reliability`

### Overall Assessment

**Good**

### Purpose

Owns safe operation of relational persistence: query/lock/pool/replication diagnosis, engine-aware
migrations, executing-plan safety, restore evidence, and production handoff without taking DBA or
release-owner authority.

### Findings

- **Routing:** Slow query, migration, pool, and recovery triggers are concrete and the app-side,
  alerting, implementation, and language boundaries are named.
- **Instructions:** Engine/version/topology facts are frozen before DDL selection; expand-contract,
  recovery, and approval requirements are explicit.
- **Accuracy:** **Verified** for the inspected PostgreSQL 18 named not-null/`NOT VALID`, validation
  lock, and virtual-generated-column claims. **Verified** for the inspected SQL Server metadata-
  only and online-alter limitations. Target engine/edition still remains `[unverified]` until read.
- **Context:** The 5,970-byte entrypoint routes five distinct procedures by engine and task. It does
  not preload both engine guides.
- **References / Assets / Scripts:** Engine-specific mechanics, plan safety, saturation, and restore
  drills are the right reference boundaries. A generic execution script would be unsafe.
- **Tools:** Plan-only versus executing diagnostics are distinguished. State-changing SQL, kills,
  failover, and scaling require the exact human-approved packet.
- **Orchestration:** `sde` implements query/migration code; the database lane supplies the measured
  plan and operating contract; DBA and release owners retain live action.
- **Failure Handling:** Lossy reverse migrations, partial restores, blocking, replication lag,
  capacity pressure, and escaped transaction effects have explicit stop/escalation behavior.
- **Verification:** Recovery requires a restore drill; performance requires before/after evidence;
  migrations require production-scale lock/risk and tested recovery. One direct safety eval rejects
  irreversible DDL.
- **Portability:** The safety method is portable. PostgreSQL 18 and SQL Server edition mechanics are
  explicitly vendor/version-specific.

### Routing Tests

#### Should trigger

1. “Explain this PostgreSQL plan and why the query regressed.”
2. “Plan an online SQL Server column migration on a hot table.”
3. “Prove this backup meets the stated RPO and RTO with a restore drill.”

#### Should not trigger

1. “Implement this repository method and its ORM unit tests.”
2. “Investigate why the PCF application instances are crashing.”
3. “Design an SLO burn-rate alert for connection exhaustion.”

#### Boundary cases

1. “The pool is exhausted” — use database reliability for DB/pool evidence; route app-instance
   triage to `pcf-ops` when the discriminator points there.
2. “Generate a migration and run it tonight” — `sde` owns implementation; this skill owns the live
   safety packet and never executes without the human boundary.

**Evaluation:** `[verified]` One direct safety scenario covers irreversible one-shot DDL.
`[unverified]` Discovery precision/recall and engine-specific execution behavior are unmeasured.

### Recommended Changes

None. The current version gates and human action boundary prevent the usual unsafe generalization;
rewriting verified engine procedures would add risk without an observed gap.

### Keep As-Is

- Keep actual/analyzed plans classified as execution.
- Keep recovery strategy broader than a mechanically generated reverse script.
- Keep PostgreSQL and SQL Server mechanics separate and target-version-gated.
- Keep backup existence distinct from measured recovery.

## Skill: `ops-tooling`

### Overall Assessment

**Minor Changes**

### Purpose

Runs the bounded requirements-to-verification pipeline for a net-new operator tool whose size,
blast radius, or gates justify more than a focused single-layer implementation.

### Findings

- **Routing:** The entry gate excludes scoped existing-pattern work and names backend/frontend as
  focused owners. A Grafana dashboard near-miss is not named in the description, but no observed
  misroute justifies routing churn before the later observability batch is reviewed.
- **Instructions:** Mission transaction, phase exits, one-owner gates, bounded relaunch/re-review,
  and compaction-safe plan state are explicit.
- **Accuracy:** **Incorrect** in one starter behavior: a dry run using only argument-derived state
  required `CF_TOKEN` before it could return. The reordered source now matches the CLI contract.
- **Context:** The 6,922-byte entrypoint progressively loads six procedures and five optional
  assets. Existing project artifacts suppress templates.
- **References / Assets / Scripts:** Templates cover only repeated artifact shapes. The Python CLI
  skeleton is an asset to copy, not repository runtime code; its optional Typer dependency remains
  target-owned.
- **Tools:** Decision/effect separation, streams, exit codes, exact handoffs, independent review,
  mission verification, and cleanup are clear. The pipeline does not infer spawn availability.
- **Orchestration:** Independent builders have disjoint ownership; the contract has one owner;
  review remains unseeded by suspected defects; loops stop after named caps.
- **Failure Handling:** Missing spawn/review capability, stale contract versions, missed
  checkpoints, contested safety findings, partial builds, stale processes, and cleanup are all
  explicit.
- **Verification:** Unit/build checks are prerequisites; the independently reconstructed mission
  transaction is the success gate. The starter dry-run ordering now has an AST regression, while a
  copied CLI still needs a real runtime test.
- **Portability:** The method and templates are host-neutral prose. Typed fleet agent names,
  `.agents/` state paths, Typer, and PCF examples are internal/framework choices.

### Routing Tests

#### Should trigger

1. “Build a new operator portal with an API, UI, review gate, and end-to-end verification.”
2. “Create a new CLI that automates this destructive workflow and needs a dry run and audit trail.”
3. “Build a multi-component internal monitor from requirements through independent review.”

#### Should not trigger

1. “Add one endpoint to this established service.”
2. “Fix this existing CLI's parsing bug.”
3. “Add a panel to the existing Grafana operations dashboard.”

#### Boundary cases

1. “Build a small new CLI with real production blast radius” — the blast radius and human gate can
   justify the pipeline even when the codebase is small.
2. “Build an internal page using an existing API and repository pattern” — use focused frontend
   implementation unless a real cross-component/gate requirement emerges.

**Evaluation:** `[unverified]` No targeted routing or behavior scenario exists.

### Recommended Changes

#### Change 1 — keep preview independent of apply credentials

- **Problem:** The starter rejected `--dry-run` without a credential even though its decision used
  only CLI arguments and performed no read or write.
- **Evidence:** Source order placed `CF_TOKEN` validation before the dry-run return; the focused AST
  regression failed on that ordering.
- **Change:** Compute and emit the plan for dry-run first; require `CF_TOKEN` only before apply.
- **Expected improvement:** Operators and CI can inspect a no-effect plan without acquiring a
  credential that the preview does not use.
- **Risk/tradeoff:** A real tool whose plan requires a live read may still need read-only
  authentication during dry-run; copied implementations must place checks according to their
  actual decision inputs rather than copying this order blindly.

### Keep As-Is

- Keep the mission transaction distinct from boot, build, and health prerequisites.
- Keep explicit commit/cadence authority and human-owned deployment.
- Keep independent review unseeded by the orchestrator's suspected defects.
- Keep relaunch and fix/re-review loops hard-bounded and recorded outside conversation memory.

## Architecture Findings

1. **Stack authority must precede local defaults:** `ci-actions` and `ops-tooling` already loaded
   `stack-profile`; backend and frontend greenfield routers now follow the same conditional rule.
2. **Shared references need framework predicates inside them:** A resource selected for both React
   and Vue cannot silently prescribe a package whose peer/runtime contract is React-only.
3. **Health contracts span instructions and starters:** Correct prose does not protect a user who
   copies a contradictory OpenAPI asset. Both now state the same liveness/readiness split.
4. **Starter assets are executable contracts:** Small standard-library checks can catch semantic
   drift in YAML and Python starters without making the skill body longer.
5. **Verification layers remain distinct:** Static CI checks, application tests, browser/API
   exercise, database recovery drills, and mission transactions prove different properties.

## Routing Conflicts

- `backend-craft` versus `database-reliability`: implementation versus live operation is explicit.
- `frontend-craft` versus `obs-dashboards`: product UI versus Grafana operations UI is explicit in
  frontend, but the later observability batch must confirm the reciprocal boundary.
- `ops-tooling` versus focused backend/frontend work: the entry gate correctly routes ordinary
  scoped changes down; net-new blast radius or gates can still qualify a small codebase.
- `ci-actions` versus `pcf-deploy`: workflow authoring is not deployment execution.

## Shared Resource Opportunities

None recommended. `stack-profile` is already the correct shared source for current stack facts.
Moving HTTP, UI, CI, database, or CLI contracts into one global reference would make independently
installed skills incomplete and reduce local execution clarity.

## Missing Capabilities

No new capability is established by this batch alone. End-to-end capacity/load planning may be a
fleet-level question, but it cannot be classified until the readiness and observability batches are
reviewed; do not create a skill from this partial view.

## Standards / Portability Issues

- OpenAPI and RFC 9457 are portable protocol choices; PCF paths and buildpacks are internal runtime
  choices.
- React, Vue, GitHub Actions, PostgreSQL, SQL Server, Typer, and the chosen UI packages are
  framework/vendor-specific and must remain behind target predicates.
- `stack-profile`, evidence labels, fleet agent names, cadence authority, and `.agents/` paths are
  internal conventions.
- Full Git SHAs, protected environments, immutable promotion, process-local liveness, and
  side-effect-free previews are portable principles even though their syntax varies by host.

## Evaluation Gaps

- Four of five Batch 2 skills have no targeted scenario.
- The one database scenario covers destructive DDL refusal, not discovery, engine-specific plans,
  saturation, or restore evidence.
- No current test executes the optional Typer starter in a generated target repository.
- No representative prompt distribution supports numeric routing precision or recall.
- No live CI run proves the reusable starter on a real caller; the regression proves only its
  repository contract and current upstream pins.

These are evidence gaps, not automatic backlog items. Promote one only after a human accepts a
named failure or coverage contract.

## Recommended Architectural Changes

### Critical

None.

### High

- **Implemented:** Separate process liveness from traffic readiness in both instructions and the
  starter asset.

### Medium

- **Implemented:** Scope shared frontend guidance to the selected framework.
- **Implemented:** Scope reusable-workflow concurrency by workflow and ref.
- **Implemented:** Route every genuine greenfield stack/tool decision through `stack-profile`.

### Low

- **Implemented:** Keep a pure dry-run path independent of apply-only credentials.

No further architectural work is activated by this review.
