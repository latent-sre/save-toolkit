# Advanced interactions for SRE products

Read for rich tables, linked visualizations, dependency graphs, visual workflow editors, command
palettes, or complex workspaces. Select patterns from the product's jobs and finish the behavior
behind every visible control. The parent skill owns visual direction, accessibility, and verification.

## Rich tables and saved views

Design the table as a working surface: sorting, meaningful filters, column sizing/visibility,
grouping, pinning, selection, row details, and saved views are options to fit the task. Distinguish
selection of visible rows from selection across an entire filtered dataset, particularly before
bulk actions. Preserve stable row identity when sorting, filtering, paging, or refreshing.

Choose server-side operations, pagination, incremental fetching, or virtualization from data volume
and measured cost. Keep counts and sort/filter semantics honest across pages. Save and share the
appropriate non-sensitive view state; distinguish personal preferences from a shared URL. Handle
loading, no matches, no data, partial results, and failed refreshes without losing the user's place.

Use semantic tables where appropriate and a well-supported grid interaction model when cell-level
navigation or editing needs one. Check keyboard navigation and focus with virtualization enabled.
An inspector or detail route should retain enough context to return to the working set.

## Linked charts and timelines

Coordinate charts, evidence tables, and timelines through explicit service/environment/time-range
context. Brushing, zooming, selecting an event, comparing a baseline, or focusing a series should
update the related views predictably, with a visible way to clear or reset the selection. Make
time zones, units, aggregation, and missing intervals clear so related views remain comparable.

Preserve the distinction between live time and a historical investigation. New data must not move
the selected time window or erase the operator's place without a deliberate return to live mode.
Give charts accessible text or data-table alternatives and show unavailable data as unknown, not
zero. Bound retained samples and measure interaction cost with representative data.

## Dependency graphs

Define what nodes and edges mean, their direction, and the source/time of the relationships. Separate
known dependencies from missing or inferred relationships and current health from historical state.
Enable focused neighborhood exploration, search, filtering, path tracing, and an inspector where
useful. Preserve graph context when opening service detail or linked evidence.

Choose layout and progressive expansion for readability at the expected size. Avoid making a dense
graph the only way to find a service or understand a relationship; provide a navigable list/table
or equivalent detail path. Keep pan/zoom, selection, labels, and keyboard alternatives usable. An
attractive connected diagram without meaningful edge semantics is not a dependency explorer.

## Visual automation workflows

Let users add, connect, configure, inspect, and rearrange steps with clear ports and connection
meaning. Offer a keyboard or form-based path for essential edits. Explain validation at the
affected node/edge and in a useful summary. Validate required inputs, references, and allowed
connections against the workflow contract; allow or reject cycles according to that contract.

Support undo/redo and preserve drafts where the product needs an editor. Distinguish draft changes,
saved definitions, validation, preview/dry-run, and actual execution. Label simulations, and show a
dry-run option only when its behavior is implemented and its backend semantics are known.

When execution is in scope, bind a run to its workflow version and show per-step progress, outputs,
failure, cancellation, and unknown outcome using real service state. Opening or editing the canvas
must not execute it. Retrying a node, resuming a run, or cancelling work must respect the backend's
actual support and authorization; a disconnected frontend cannot assume the work stopped.

## Command palettes and workspace navigation

Use command palettes for navigation, search, and task actions with recognizable labels, groups,
context, and discoverable shortcuts. Keep ordinary navigation and visible action paths available.
Make the active service, environment, selection, and target count clear for context-dependent
commands. Reuse the same action handlers, authorization, and confirmation as visible controls.

Manage focus and keyboard conflicts with dialogs, tables, editors, and text inputs. Restore focus
when a palette or inspector closes. In a multi-pane workspace, preserve selection and useful pane
sizes without letting a hidden region retain confusing keyboard focus.

## Verify relationships and transitions

Exercise a complete task across the linked surfaces: filter a table, inspect a row, follow a graph
relationship, select a time interval, and return without losing context where those steps apply.
For a workflow editor, exercise invalid configuration, correction, save, and the implemented
preview/run path. Test reduced motion, keyboard access, late/out-of-order data, and partial failure.
Judge visual character separately from behavior; a screenshot cannot establish that these flows work.
