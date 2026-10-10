# Design direction and visual craft

Read for a new visual direction, redesign or substantial layout change. Follow the user's references
and preserve the product's existing language where the task calls for it. Choose palette, type,
themes, spacing and decoration to suit the audience and content.

## Make the design specific

Start with the main task and representative content. Identify what the user should notice first,
what they act on next, and which details can recede. Choose density, navigation and composition
around that sequence: a compact operational workspace and an expressive public page have different
needs. Use references to identify concrete qualities to carry forward, such as typography, rhythm,
image treatment or information density; do not substitute a stock dashboard shell for the brief.

- **Layout:** group related information, align repeated elements and distinguish primary actions
  from secondary ones. Use whitespace, columns, borders or surfaces where they clarify relationships.
  Adapt navigation and reading order to narrow screens; avoid merely shrinking the desktop layout.
- **Typography:** choose fonts, scale, line length, weight and spacing for the content. Test actual
  headings, long labels and dense data. Use aligned numerals where comparison benefits from them.
  Account for font licensing, loading cost, fallback metrics and the project's asset/privacy policy.
- **Color and themes:** choose the palette and supported themes from the brief and usage context.
  Light-only, dark-only and multiple themes are all valid. Keep emphasis and status legible in each
  shipped theme; use shared semantic values where they make consistency and theme changes easier.
- **Imagery and detail:** use icons, illustration, photography, texture, gradients or depth when
  they express the intended character or explain content. Check asset rights, delivery cost,
  cropping and useful alternatives. Give icon-only actions accessible names.
- **Motion:** choose CSS, browser animation APIs or a library to suit the interaction and visual
  direction. Tune timing to the action; make interrupted transitions behave sensibly and provide a
  reduced-motion experience. Animation should preserve control and access to the content.

## Review with real content

Render early enough to correct the direction. Compare the result with the brief or reference at
the intended viewports: hierarchy, readability, alignment, density, visual character and the path
to the main action. Exercise hover, focus, selected, disabled, pending and failure states that the
view actually has. Check long content, missing values and realistic data volume as well as the
polished example. Iterate on visible problems; a screenshot alone does not verify interaction.
Follow the parent skill's verification and gap-reporting rules when a browser is unavailable.
