# Forms

Read this when the view collects user input for submission.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Forms

- Match the target repository's framework and form/validation layer. In the React greenfield stack,
  use `react-hook-form` or `@mantine/form`; the latter ships no CSS, but wire it to existing
  non-Mantine inputs rather than importing `@mantine/core`. In Vue, use `v-model` plus the
  repository's established Vue validation layer; React-only form packages do not apply. Validate
  on blur and submit, not only on submit.
- **The server is the source of validation truth** — mirror obvious rules client-side for speed, but always map the server's field errors back to the offending fields inline.
- **Dirty tracking**: Save disabled until something changed; warn before leaving unsaved edits (route guard + `beforeunload`). Never make the user retype after an error.
- **Label and error wiring is accessibility wiring.** Every control is programmatically labeled —
  `<label for>`/`id` association (`htmlFor` in JSX) or a field component that renders it; visible
  text near an input is not a label until associated. Error text links to its field via
  `aria-describedby` plus `aria-invalid` and announces (`role="alert"`), so what the sighted user
  sees inline, the screen-reader user hears.
- **Required** is conveyed to assistive tech (`required`/`aria-required`), never by an asterisk
  alone — the asterisk itself is `aria-hidden` decoration. Identity and credential fields carry
  `autocomplete` (`email`, `current-password`, …) — autofill is usability and accessibility at once.
