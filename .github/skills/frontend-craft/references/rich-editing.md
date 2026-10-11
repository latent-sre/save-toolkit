# Rich editing with durable meaning

Read for workflow canvases, structured editors, undo and draft persistence. The
[API reference](./api.md) owns write/retry/conflict mechanics and the core skill owns action
authority. Existing execution contracts determine what an editor can offer.

## Model before canvas

Define node kinds, stable IDs, typed inputs/outputs, ports, branch meaning and connection rules
before choosing a graph layout. Validate required inputs, references, incompatible types and
unreachable steps where the execution contract requires them. Allow or reject cycles according
to that contract; an editor must not invent a universal ban on loops.

Provide understandable add, connect, configure, select and remove operations. Essential authoring
has a keyboard or form-based alternative to dragging. Canvas, selection and inspector share the
same model; labels explain branches or connections whose meaning is otherwise ambiguous.
Show errors at the affected node/edge and in a navigable summary that takes the user to the issue.

## Draft, save and undo

Define undo/redo for model edits, including deletion and connections, with stable references
restored together. Navigation, selection and data refresh must not unexpectedly consume undo
history. Separate unsaved changes, saving, confirmed persistence and save failure. Preserve the
draft after a failed save using storage appropriate to its sensitivity, never persisting secrets
just to restore an editor.

Capture the submitted revision so an earlier save response cannot mark newer edits as saved.
Reopen the confirmed definition and verify its meaning, not only its appearance. Resolve
concurrent edits through the backend's actual version/conditional-write contract; expose conflict
without silently overwriting someone else's definition. Make leave-with-unsaved-work behavior
explicit. Import/export, collaboration and version history are added only when the task needs them.

## Execution is a separate action

Opening or editing a canvas does not run it. Distinguish draft validation, preview or simulation,
saved definitions and real execution. Show a dry-run control only when that behavior is implemented
and its backend semantics are known. A local animation cannot manufacture a successful run.

Bind each run to its saved workflow version and run ID. Show per-step state, outputs, failures and
unknown outcomes from the real execution contract, with sensitive outputs handled by the core
skill's content rules. Retrying, resuming and cancelling use backend-supported authorization and
semantics; a disconnected browser cannot assume execution stopped. Use the same confirmation and
scope disclosure from a canvas, palette or visible button.

## Completion exercise

Create a branching flow, reject an invalid connection, undo a connected-node deletion, then save
and reopen it. Fail a save and introduce a version conflict: retain the draft and show a useful
recovery path. Edit again while a save is pending and deliver its old response; new edits must
remain unsaved. If execution is in scope, trace a failure to the exact saved version and step,
then disconnect during cancellation: show uncertainty until authoritative state resolves it.
