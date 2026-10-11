# Motion that preserves control

Read for transitions, orchestrated effects and moving visualizations. The [design brief](./design.md)
sets the register and motion budget; React/Vue references name the implementation choices.
This reference owns behavior when animation interacts with the task.

## Define the final state first

Choose the purpose: continuity between views, expansion, changed order, response to input,
progress, or the site's one expressive moment. Essential feedback and urgent actions must be
available promptly; an animation's completion callback is not evidence that a write succeeded.
Keep pending, confirmed and unknown outcomes tied to the API response.

Opening, closing and reversing an interaction must converge on the user's latest intent. Cancel
superseded work and clean up timers, listeners, animation handles and detached elements on route
or component teardown. A late completion callback must not reopen a dismissed panel or overwrite
the new view. Focus and pointer availability follow actual visibility; invisible overlays must
not intercept input, and removal must leave focus at a sensible visible destination.

Animate with stable entity identity when lists reorder. Do not move a live investigation's
selected row or graph target under the pointer merely to make arrival look polished. Coordinate
with [live data](./live-data.md) for paused selections. Avoid competing movement in dense views.

## Reduced motion and interruption

Provide equivalent information and control when motion is reduced: immediate final states,
static connections or restrained effects. Check CSS, component libraries, canvas/camera movement
and video separately; one library setting may not govern every mechanism. Repeated autonomous
effects need a reachable pause/stop control. Keyboard focus must receive the same actionable
feedback as hover, and animation cannot be the only way to learn that something changed.

Test realistic data volume and rapid input before optimizing. Measure the costly path; reduce
work or the effect rather than hiding input lag behind a longer transition. Keep navigation,
loading and error states usable when frames are delayed or the tab is backgrounded.

## Completion exercise

Open, close and immediately reopen the affected surface; navigate away before completion; and
repeat under reduced motion and delayed frames. The latest requested state must win, with no
ghost overlay, lost focus or blocked control. Perform the same task in both motion modes, checking
the resulting state and keyboard access rather than requiring an animation to have run.
