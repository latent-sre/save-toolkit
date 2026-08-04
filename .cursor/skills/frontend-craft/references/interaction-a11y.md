# Interaction accessibility — overlays, widgets, announcements

Read for dialogs, drawers, menus, tooltips, tabs, custom widgets, or asynchronous status. The
baseline semantics remain in `../SKILL.md`; form wiring remains in `forms.md`.

## Overlays

- Opening moves focus inside; closing restores focus to the opener. Store the opener before moving
  focus. Trap Tab/Shift+Tab with native `<dialog>` or the repository's proven focus primitive.
- Give the dialog an accessible name, `aria-modal="true"`, and Escape behavior. Background content
  must not remain keyboard-interactive.

## Widgets

- Prefer native elements or the established component library. A custom widget owns its entire
  keyboard grammar: arrows navigate, Enter/Space activates, Escape closes, and Tab leaves.
- Keep state and accessibility state synchronized (`aria-expanded`, `aria-controls`,
  `aria-selected`, and `aria-activedescendant` where focus remains on a combobox trigger).
- Never use positive `tabIndex`, hide a focusable element from assistive technology, or put a click
  handler on a non-interactive element without equivalent keyboard behavior.

## Async status and media

- Announce save/error/background results through a mounted live region (`role="status"`; urgent
  failures only use `role="alert"`). A region inserted with its first message may not announce.
- Icon-only buttons need an accessible name; decorative icons/images are hidden or use empty alt;
  meaningful images describe what they convey.
- Test the actual interaction with keyboard and an automated accessibility scan; static JSX review
  is not enough.
