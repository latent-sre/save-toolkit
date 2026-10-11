# Interaction completion

Read only the sections needed for the product's selected capabilities. Use them to define behavior and meaningful checks, not to expand the feature list.

## Rich tables: help users find and act on a set

Choose a table when the job needs scanning, comparing, filtering, or acting on many records. Use another presentation when sequence, narrative, or relationships carry the answer better.

Choose columns from the decision being made. Give identity and key status enough space; align comparable values, show units, and make missing values explicit. Long values need an inspectable path. Set sensible initial ordering and density. Add column control, saved views, export, pinning, or bulk actions when their use justifies their cost.

Define search and sorting scope. A server-paginated collection needs collection-wide behavior where promised; sorting the loaded page must not masquerade as sorting all results. Keep filters, page boundaries, counts, and cleared states coherent. Stable record identity must survive sorting, refresh, and virtualization.

For selection, distinguish current rows, explicit record IDs, and all matching results. Make the count and action scope visible. Define what changing a filter does to selection. Bulk outcomes need per-record failures where the API provides them, with recoverable work preserved.

Choose semantic HTML tables for ordinary tabular content. An application-style grid requires deliberate focus management and keyboard behavior. Virtualization and nested controls need particular care; test the actual rendered behavior with the intended assistive technologies.

**Completion exercise:** locate a record through a combination of filters, sort the full relevant set, open its detail, return without losing context, and exercise a failed action if actions exist. Include a missing field, a long label, an empty result, and a refresh that changes ordering.

## Linked charts and timelines: make a question traversable

Choose linked views when users need to move between an aggregate, a time interval, and the records behind it. Specify the question before choosing chart types. Treat metric definitions, units, aggregation, timezone, missing samples, and freshness as part of the design.

Give related views a common model of selected entities and time range. Distinguish transient hover from persistent selection. Brushing a chart, choosing a timeline event, or selecting a table row should update the relevant views consistently. Make active scope and reset behavior visible. Support a shareable or restorable view where the job needs it, with sensitive values kept out of URLs.

Handle late responses so an old range cannot replace the currently selected range. Show gaps as gaps; do not silently turn missing telemetry into zero. If data is sampled or aggregated, disclose the resolution needed to interpret it. Temporal coincidence alone does not establish a cause.

In live views, define how incoming data changes the display. Keep a paused or historical view stable and identify its time boundary. Avoid moving a row, selection, or timeline under an active investigation without a comprehensible update policy.

Provide readable values and summaries through keyboard and non-visual access. Tooltips need focus behavior as well as hover behavior. Allow users to inspect the underlying events or measurements when the product job requires it.

**Completion exercise:** select a service and interval, drill into an event, and confirm that linked charts, timeline, and records agree. Reverse the order of two responses, introduce missing samples, and switch between live and historical modes if both are supported.

## Dependency graphs: expose useful relationships

Choose a graph when a relationship or path is the information the user needs. First define nodes, edge direction, relationship type, scope, and data provenance. Distinguish observed, configured, inferred, and unknown relationships where the source supports those distinctions.

Start from a useful entity or bounded neighborhood. Supply search, filtering, readable labels, zoom, and a way to recover orientation. Give selection a stable details surface. Expand large graphs progressively and retain the user's position when inspecting details. Grouping, layout, and edge emphasis should explain structure rather than suggest unsupported severity or causality.

Make relationship inspection possible without dragging or precise pointer movements. A synchronized list, tree where appropriate, or relationship table can complement the graph. Keep that alternative synchronized with selection and scope.

Choose a rendering and layout approach based on expected graph size and update rate. Check label legibility and interaction cost using dense and disconnected examples. A continuously moving layout should not prevent selection or reading.

**Completion exercise:** find a service, trace one defined relationship, inspect the evidence behind an edge, and return to the starting context. Repeat the essential investigation using the keyboard or the synchronized alternative. Include a cycle, disconnected node, and missing metadata.

## Visual workflows: connect editing to durable meaning

Choose a workflow editor when users benefit from manipulating relationships among steps. Establish the workflow model before polishing the canvas: node kinds, typed inputs and outputs, connection rules, parameters, branch semantics, and which cycles or loops the execution model permits.

The interface needs understandable ways to add, connect, configure, select, and remove steps. Provide reachable forms for node details. Offer alternatives to dragging for operations essential to authoring. Label edges and branches where meaning would otherwise be ambiguous. Keep selection, canvas, and inspector state in agreement.

Validate at the point of editing and before saving or running, as appropriate. Explain errors near the affected node or connection and in a navigable summary. Validate required parameters, type mismatches, unreachable steps, and cycles according to the actual execution contract. Do not invent a universal ban on loops.

Define undo and redo for edits, including deletion and connections. Separate unsaved changes, an in-progress save, confirmed persistence, and a save error. Preserve the draft after a failed save. Resolve concurrent edits according to the backend's versioning contract; make conflicts understandable without silently overwriting another user's work.

Use run controls only when execution is in scope and supported. Distinguish local preview or simulation from a real run. Show run identity, node state, errors, and cancellation semantics from the execution contract. Never manufacture a successful operational outcome from a local animation.

Add import/export, collaboration, version history, or reusable subflows when required by the jobs, rather than treating them as automatic canvas features.

**Completion exercise:** create a branching flow, reject an invalid connection with a useful explanation, undo a deletion, save and reopen it, and recover from a failed or conflicting save. If runs are supported, trace a run failure back to its step.

## Command palettes and keyboard navigation: accelerate a visible system

Use a palette when the product has enough navigation or repeated actions to benefit from fast lookup. Give it a visible entry point and a discoverable shortcut appropriate to the platform. Commands should name their action and relevant object or scope.

Model results, empty search, loading, disabled actions, and errors. Distinguish navigation from state-changing commands. Reflect the user's current permissions and context. Consequential actions need their normal scope disclosure and confirmation where warranted, even when launched from a palette.

Keep focus visible. On opening, place it deliberately; support navigation, activation, and dismissal; on closing, return it to a sensible origin. Ensure nested widgets and text editing retain their own keys. Avoid global shortcut handlers that intercept ordinary typing, composition, or expected browser behavior.

Use consistent, documented keyboard behavior in dialogs, menus, tabs, tables, and canvases. Every essential task needs an accessible route; shortcuts improve speed but should not become the only discoverable route.

**Completion exercise:** open the palette from a detail view, search, activate a result, dismiss another search, and confirm focus and context. Repeat during text editing and with an unavailable command.

## Motion: express character and make change understandable

Decide what motion should communicate: object continuity, expansion, connection, response to input, progress, or a deliberate moment of delight. Shape timing, easing, scale, and choreography to the product's character. A team site can support a different rhythm from an urgent investigation workspace.

Use movement to preserve orientation when things change. Essential feedback must arrive promptly; animation must not delay an urgent action or make users wait to read a result. Keep hover and press responses coherent with keyboard focus. Limit competing movement in dense analytical views.

Provide an intentional reduced-motion experience. Preserve status and spatial understanding with immediate state changes, restrained transitions, or static cues. Check CSS animation, third-party effects, canvas rendering, video, and programmatic camera movement; one library setting may not govern them all. Repeated or autonomous effects need an appropriate pause or stop behavior.

Choose the animation mechanism according to the effect and measured cost. Test interruption, rapid toggling, route changes, and cleanup so transitions cannot leave ghost elements, blocked controls, or incorrect final states.

**Completion exercise:** perform the same job with normal and reduced-motion preferences, interrupt transitions, and inspect behavior under load. Both modes must preserve information and control.

## Interactive explanations: reveal a relationship or consequence

Use interactive visuals when manipulating an input helps users understand a relationship, compare alternatives, or inspect a large body of information. Name the question, the adjustable inputs, the visible response, and the assumptions of the model.

Choose controls with clear units and reachable defaults. Keep the visual and explanatory text synchronized. Include a reset and a keyboard-operable route. Distinguish measured data, derived values, and hypothetical output; disclose approximation where it changes interpretation. Simulation must not imply a live operational change.

Decoration and illustration may establish identity, but an explanatory control must change something meaningful. If the user would learn the same thing faster from a static diagram, use that simpler form.

**Completion exercise:** change an input, inspect the resulting values and explanation, reset, and repeat without a pointer. Verify boundary values and missing input; check that a hypothetical result cannot be mistaken for observed evidence.