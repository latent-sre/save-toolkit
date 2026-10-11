# Fresh evaluation scenarios

All ten scenarios below were authored from this request during this authoring pass. **None has been executed as a behavioral evaluation.** The performed checks are listed separately in [integration record](integration.md).

These are scenario specifications, not a runnable application test suite. No application, API stub, or rendered concept was built in this task.

## How to use the scenarios

Run each in a fresh context with this skill bundle, the scenario's user prompt, and the minimum raw artifacts described in its packet. Keep assessor criteria out of the executing agent's prompt. Do not supply previous frontend skills, prior outcomes, or a preferred visual answer.

Two levels of future evaluation are useful:

- **Decision rehearsal:** stop after discovery, direction proposals, interaction design, or an implementation plan. This can reveal decision errors; it cannot demonstrate a working product, accessibility, performance, or actual visual quality without rendered artifacts.
- **Product exercise:** authorize a disposable local implementation and browser checks. Prepare the packet's minimal OpenAPI documents, deterministic data, and stub behavior before the run. Freeze those inputs and record their hashes. These fixtures and applications have not been created in this pass.

Use synthetic data and local effects only. For new-product cases, have a human inspect the two proposals and choose one before full implementation. If a scenario explicitly delegates selection, the agent can choose and explain its rationale.

Record the skill file hashes, tool/model environment, input artifacts, choices made, implementation revision, actions attempted, and observed results. For each criterion, record observed satisfaction, an observed defect, insufficient evidence, or not applicable with a reason. Keep appearance judgments separate from functional observations. Do not average a broken main journey into a successful result using unrelated strengths.

For visual differentiation, describe the actual hierarchy, spatial organization, navigation, and interaction in both proposals. Ask whether those differences remain meaningful with color removed. This is a human review aid, not an automated aesthetic score or a requirement that a layout be monochrome.

## 1. Team site for a mixed-experience audience

**User prompt**

> Design and build a new site for the Relay platform team. New starters need to understand what we own, find a service contact, and reach useful guides. Experienced engineers need fast access to the same material. We have no visual identity yet. Give the site a strong personality. Most use will be at a desk, but people sometimes open team links on their phones.

**Raw packet**

Supply six owned service descriptions, four short guides, three team contacts, and an ownership lookup list. Include one long service name and one missing contact. Content is synthetic and maintained locally. There is no live monitoring feed, automation engine, or AI requirement.

**Measures**

- Two directions provide different composition and interaction, using the same content.
- The agent makes a concrete mobile decision from the described phone job.
- A visitor can identify ownership and reach a relevant guide without knowing internal jargon.
- Product character survives beyond the opening screen; navigation, empty search, and detail views are finished.
- Motion or illustration supports the site's identity. Unnecessary operational dashboards or workflow editors are not introduced.

**Product exercise**

Find the guide for a named service from the home page, then repeat on a narrow viewport and with keyboard navigation. Inspect the missing-contact path and verify every prominent link.

## 2. Incident workspace with linked evidence

**User prompt**

> Build an incident investigation workspace for comparing latency, errors, and deployment events. Operators use wide monitors. A service and time selection must stay consistent while they inspect details. The workspace should feel calm under pressure and visually distinctive. We have no established direction. Phone use only needs a readable incident overview.

**Raw packet**

Describe read-only OpenAPI operations for service lookup, telemetry samples, and incident events. The packet uses UTC timestamps and explicit units. Include three services, a telemetry gap, two events at the same timestamp, and one stale source. A stub can return the earlier of two requested ranges last. Live mode is simulated polling; it causes no production action.

**Measures**

- Direction choice changes how the investigation is organized, not merely its colors.
- Charts, timeline, table, and detail selection share the relevant scope.
- Missing samples remain distinct from zero and stale information is visible.
- Late responses cannot replace a newer selection; historical inspection remains stable.
- Event proximity does not become an unsupported causal assertion.
- Keyboard paths and a palette, if chosen, support an understandable visible workflow.

**Product exercise**

Change service and range quickly, inspect an event, reset selection, and pause simulated live updates. Verify the resulting values, timestamps, and active scope across views. Check the limited phone overview separately from desktop investigation.

## 3. Vue automation builder with durable edits

**User prompt**

> Build a visual automation editor in Vue for our Go service. People need to assemble a branching flow, configure steps, validate it, and save drafts. We want an expressive workspace for desktop use. There is no established visual direction. Runs are simulated in this prototype; label them clearly.

**Raw packet**

Supply an OpenAPI description for loading and saving a versioned workflow. A graph has node IDs, kinds, parameters, typed ports, and directed edges. Node kinds are trigger, condition, action, and bounded-retry. A retry construct is permitted by the domain; other cycles are invalid. Save may succeed, time out, or return a version conflict. No production run endpoint exists.

**Measures**

- Vue remains the framework unless the user authorizes a change; dependencies are researched for the selected ecosystem.
- The two directions differ in authoring flow and spatial composition.
- Connections and parameters are validated against the supplied rules, including allowed retry behavior.
- Users can author essential connections without dragging.
- Undo/redo, save acknowledgement, reopen, failed saves, and conflicts have coherent behavior.
- Simulation cannot be confused with an actual operational run.

**Product exercise**

Build a branching flow, attempt a type-invalid edge, create a permitted retry, delete and undo a node, save, reopen, then trigger a conflict. Confirm the local draft survives failure and that simulation is visibly identified.

## 4. Service catalog using styled Mantine and charts

**User prompt**

> Build a service catalog in React using Mantine styled components and Mantine charts. We have about 50,000 services and want fast owner lookup, filtered comparison, and an understandable view of dependencies. There is no existing design direction. Make it feel like our own product. Desktop exploration comes first; phones need owner and runbook lookup.

**Raw packet**

Supply server-side filtering, ordering, and cursor pagination contracts, plus service details and directed dependency records. The seeded dataset contains duplicate display names with unique IDs, missing owners, unknown health, and long labels. Chart summaries describe the full filtered set. A dependency edge means “calls,” and includes its observation time. Provide a small cycle and a disconnected service.

**Measures**

- Mantine styled components and charts are used as valid choices without an arbitrary restriction to unstyled primitives.
- Current peers, styles, and needed interaction capabilities are checked.
- Full-set filtering, sorting, and chart summaries remain consistent with paginated rows.
- IDs remain stable across ordering and refresh; selection scope is visible if selection is included.
- A graph answers a relationship question and exposes edge meaning and evidence.
- Distinctiveness comes from the product's structure, type, visual language, and interaction.
- The phone lookup job remains practical without shrinking the entire desktop explorer.

**Product exercise**

Find one of the duplicate names by owner, sort and page, open the service, trace a caller, and return with context intact. Compare the visible count and chart totals to the stub's full filtered result. Repeat owner lookup on a phone viewport and relationship inspection without a pointer.

## 5. Direction selection and faithful refinement

**User prompt**

> Start a new reliability knowledge site. The main job is finding a tested operational guide by service or symptom. We have no established visual direction. Show me two distinct approaches before building the rest.

**Raw packet**

Supply twelve guide summaries, service tags, symptoms, and two long titles. No existing layout or component library is supplied.

**Staged reply**

After reviewing the actual proposals, the evaluator selects one and asks for a refinement to its information density. The evaluator records the reason for the choice without dictating a different composition.

**Measures**

- Both proposals use representative content and differ in both composition and interaction.
- The agent provides inspectable concept slices and explains real tradeoffs.
- It waits for selection for dependent work rather than treating silence as a choice.
- The refinement preserves the selected concept instead of silently blending both directions.
- A delegated-selection variant proceeds when the user explicitly says to choose.

**Evidence**

Keep both proposals, the selection message, and the refined result. A prose-only run can establish the decision sequence; rendered and interaction evidence is needed to judge the concepts.

## 6. Focused change in an established light-theme Vue product

**User prompt**

> Our service directory already uses Vue and an established light theme. Add a useful empty-result state and a “clear filters” action. Keep the current design and the existing API.

**Raw packet**

For a future run, create a small authorized Vue fixture with one existing directory view, URL-backed filters, and a documented light palette. Preserve its initial files so scope changes can be inspected.

**Measures**

- The change stays within the requested work and current framework.
- The agent does not force dark styling, propose two replacement directions, or introduce a new component system without need.
- Clear filters resets the right state and restores results while preserving unrelated navigation.
- Language explains the empty result without implying that no services exist.
- Verification is proportional to the narrow change.

**Product exercise**

Apply a no-match filter, use the action by keyboard, reload, and inspect the resulting URL and records. Review the diff for unrelated changes.

## 7. Compatibility research under incomplete evidence

**User prompt**

> Recommend the UI, table, chart, and animation tools for this frontend. React with Vite and TypeScript is familiar to us, but we can use Vue or another suitable approach. Mantine is approved. Explain the fit and verify important compatibility claims before installing anything.

**Raw packet**

Supply a hypothetical product brief and a permitted package manifest with a specific framework version. The evaluator records actual current documentation and package results at run time; no expected “latest” version is hardcoded in this scenario. A variant disables one research service. Another supplies a clearly marked old public example that targets a different major version.

**Measures**

- The agent starts with the supplied environment and the product's actual capability needs.
- Context7 documentation and GitHits package/source/test evidence have separate provenance.
- It compares exact versions and catches mismatched peers or framework examples.
- An unavailable service is reported with a sensible primary-source fallback or a precise uncertainty.
- It neither fabricates searches nor treats upstream tests as proof of an untested integration.
- Other suitable tools remain eligible; popularity or the names in the brief do not become an allowlist.

**Evidence**

Capture the decision, source URLs/revisions, selected versions, unresolved claims, and any separately authorized local spike. A research recommendation alone does not prove a built product.

## 8. Keyboard access and motion under pressure

**User prompt**

> Give this investigation workspace more expressive transitions and faster keyboard operation. Keep it usable for responders who avoid motion and for people unfamiliar with our shortcuts.

**Raw packet**

Use a product-exercise fixture with a chart, filterable table, graph details panel, text editor, and command palette. It has both CSS effects and an animation-library transition. Include a modal and a simulated live update.

**Measures**

- The agent preserves meaningful motion while providing a deliberate reduced-motion mode.
- Reduced-motion behavior covers all active mechanisms, including camera movement if present.
- Palette opening, search, dismissal, and action return focus sensibly.
- Typing and text composition are not intercepted by global shortcuts.
- Graph and table jobs have keyboard-operable paths and information is not color-only.
- Rapid toggling and updates do not strand focus, block controls, or leave incorrect states.

**Product exercise**

Run the same task sequence with keyboard only in normal and reduced-motion settings. Interrupt a transition, dismiss a modal, and type in the editor. Review contrast, zoom, and screen-reader behavior where tooling permits; label missing coverage.

## 9. Interactive explanation with transparent assumptions

**User prompt**

> Add an interactive capacity explanation to our team learning site. New engineers should be able to vary incoming work and worker count and understand the estimated utilization. This is educational; it must not suggest a production scaling change occurred.

**Raw packet**

Use the synthetic model: estimated utilization (%) = arrival_rate / (worker_count * service_rate_per_worker) * 100. Inputs have visible units. Workers must be at least one; service rate must be positive. The model is a simplified teaching aid and excludes queue dynamics.

**Measures**

- The visual answers the stated learning question, with meaningful controls and synchronized explanation.
- Values, units, assumptions, and limits are clear.
- The agent handles invalid boundaries, reset, keyboard use, and reduced motion.
- Values above 100% convey the model's overload condition without pretending it predicts a full queueing system.
- The agent does not add a workflow editor, operational controls, or a live-change success message.

**Product exercise**

Use arrival rate 120 jobs/second, four workers, and service rate 40 jobs/second per worker; the estimate is 75%. Change workers to two; the estimate is 150%. Test invalid zero inputs and reset. These are expected calculations, not observed run results.

## 10. OpenAPI integration and an unavailable backend

**User prompt**

> Connect the catalog frontend to our FastAPI OpenAPI contract. The service supports search and details, but the dependency endpoint is not ready. Keep useful frontend progress possible and report exactly what is connected.

**Raw packet**

Supply an OpenAPI document with search and detail operations, optional/null fields, validation errors, and authentication failure. Do not include a dependency endpoint. A local stub can simulate a slow response, an expired session, and a network timeout. There is no AI feature request.

**Measures**

- OpenAPI remains the API specification; no AI provider, model, credential, or chat workflow is introduced.
- Client tooling is compatible with the document's actual version; generated code, if used, is reproducible.
- Optional and null values, failures, and obsolete responses are handled coherently.
- Missing dependency data has an explicit contract/fixture boundary.
- The agent reports which operations were tested and which remain simulated or unavailable.
- A successful build or fixture response is not presented as complete live integration.

**Product exercise**

Search, open details, expire the session, reverse two response timings, and inspect the dependency view. Compare the agent's final claims with observed requests and stub configuration.

## Coverage and limits

Scenarios 1-4 exercise the four product types. Scenarios 5-10 isolate design choice, scope preservation, technical evidence, keyboard/motion quality, explanatory visuals, and API truthfulness. The suite uses different device jobs and includes both new and established visual direction.

These scenarios can expose clear defects and gather evidence of good decisions. They do not establish general design excellence, broad assistive-technology support, production-scale performance, security, or cross-host skill discovery by themselves. Actual runs need an authorized environment, prepared fixtures, implementation artifacts, and a reviewer for visual and usability judgments.