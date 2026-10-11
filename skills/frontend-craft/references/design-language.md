# Product visual direction

Read for a new product, a full redesign, or substantial visual work. Use the product brief and
selected direction from the parent skill; preserve an existing identity for scoped changes.

## Two directions with a meaningful choice

Give the same representative content and task to both directions. Each should show the main
composition, navigation, typography, information density, palette, and one important interaction.
Use rendered concept screens or prototypes when available. A description of intended animation is
not evidence that it has been implemented.

Make the alternatives materially different. An incident workspace might explore a timeline-led
investigation with an evidence inspector, and a service-led composition linking a dependency map
to a working table. A team site might explore an editorial narrative and an interactive map of the
team's capabilities. These illustrate differences in structure; derive the actual concepts from
the current product instead of reusing these layouts by default.

Explain what each direction makes easier, how it handles dense or incomplete content, and its main
tradeoff. Recommend one with a reason. Carry the user's selection forward without asking again.

## Build an identifiable visual system

Choose the product's visual character deliberately: type pairing and hierarchy, spacing rhythm,
grid, density, surface treatment, icon treatment, emphasis, and motion behavior. Record the choices
in theme tokens and reusable components so screens belong together. Shared fleet quality does not
require the same visual identity across products.

Avoid interchangeable starter compositions. Repeated cards, a sidebar, a large hero, gradients,
monospace labels, or oversized metrics can each be appropriate, but their presence does not supply
the design idea. Let content priority, relationships, and the user's next decision shape the page.
An untouched starter template with renamed headings does not meet the brief for a distinctive
product. Removing a logo should still leave recognizable choices in structure and interaction.

Typography is part of the identity; no house font or fixed count of type sizes is required. Balance
character with sustained reading, dense data, and clear hierarchy. Use tabular numerals where
alignment helps comparison, and make identifiers easy to distinguish and copy. Choose font loading
and licensing that fit the project.

## Dark-first, with deliberate color and depth

Develop the dark theme first unless the user or existing product specifies otherwise. Choose its
neutral or tinted surfaces, accent palette, borders, elevation, and chart colors as a system.
Dark-first does not prescribe one background hue, card style, or radius. Keep secondary text and
quiet controls readable; state and selected context must remain distinct.

Decide whether light and system modes belong in the product brief. If shipped, design and verify
each theme, persist the user's choice, and apply it before paint. Theme tokens must cover charts,
graph edges, workflow nodes, tooltips, focus, and overlays as well as the page shell. Keep semantic
status colors separate from categorical data colors and reinforce status with text or icons.

## Mixed experience levels and large workspaces

Make the main path visible: clear labels, meaningful grouping, useful defaults, and feedback at
the place of action. Offer deeper controls, shortcuts, saved views, and commands without requiring
users to discover a gesture before they can complete basic work. Explain unfamiliar terms in context.

Use desktop space for useful comparisons and related information. Resizable panes, an inspector,
linked visualizations, or a wide table may suit the task; avoid stretching a sparse layout simply
to fill a monitor. Keep the current service, environment, time range, and selection recognizable
where they determine the meaning of the data. Decide smaller-device workflows per product.

## Expressive motion and interactive visuals

Treat motion as part of the visual direction and interaction design. Use it for spatial continuity,
selection, graph exploration, workflow execution, staged explanations, and visual character.
Use animated illustrations, rich transitions, canvas, SVG, or other interactive treatments
throughout the product where they support the concept.

Choose timing and easing by the interaction. Immediate controls must remain responsive; an animated
transition must not delay a command, obscure an outcome, or move a target under the pointer.
Keep live updates from repeatedly animating the whole workspace or disrupting reading and selection.
Provide pause or reduced-motion alternatives for continuous movement and preserve the information
and navigation when animation is reduced. Test the actual effect at representative data volume.

## Review the rendered design

Compare the result with the selected concept at its intended size. Assess hierarchy, character,
content fit, density, legibility, motion, and interaction continuity. Inspect a dense state and an
incomplete or failed state as well as the attractive initial view. Confirm that the chosen library's
defaults have been integrated into the product's identity. Follow the parent skill's browser,
keyboard, performance, and gap-reporting requirements.
