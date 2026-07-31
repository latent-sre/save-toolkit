# Frontend stack selection

Read this when starting a **greenfield** UI. An existing repository's stack always wins — if you are
working in one, you do not need this file.

This file also carries the one hard prohibition: never import `@mantine/core` or any styled Mantine
component. Mantine's *hooks* mix freely with Tailwind; its *components* do not.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Stack

An existing repo's stack always wins — match it. Greenfield is always a **React + TypeScript SPA on Vite**. Keep two layers cleanly separated — enterprise-grade logic, custom-painted SPA:

**Paint — one Tailwind reset, one token system:**
- **Tailwind** for all styling.
- **shadcn/ui pattern on Radix (or Base UI) primitives** — headless, accessible components you style yourself; this owns the calibrated look. Base UI is the newer foundation, either is fine.
- **lucide-react** icons; **Framer Motion** only when CSS transitions aren't enough (CSS is right for hovers, fades, modals).
- Optional, same Tailwind world: **HeroUI v3** as a styled layer only when it can share the existing reset and token system; **Aceternity / Magic UI** as a sparing garnish for hero / login / empty-state moments — named in the review packet.

**Logic — zero CSS, decoupled from the paint:**
- **TanStack Query** (server state), **TanStack Router** (typed routing + URL state), **TanStack Table** (headless data grids) — one type-safe, zero-CSS suite that *is* the logic layer, painted with Tailwind.
- **@mantine/hooks** for utility logic (disclosure, debounce, local storage, hotkeys, click-outside, media query, element size); optionally **@mantine/form** for form state. Both ship no CSS and need no provider.
- Accessible *widget* behavior (focus trap, ARIA, roving tabindex) comes from **Radix / Base UI**, not from Mantine hooks.

**One hard rule:** never import **@mantine/core** or any styled Mantine component — its CSS reset fights Tailwind's, and that mix is the one incoherent hybrid. Mantine's *hooks* are pure logic and mix freely; its *components* do not.

For a greenfield SPA, use this stack no matter how small. Existing repositories keep their established stack as required above. If the user explicitly asks for plain HTML or a static page, comply; that call is theirs. Any greenfield deviation from this default gets one line in the review packet.

## Build & serve on PCF

Build hashed static assets (`vite build`). Serve via the **`staticfile`/`nginx` buildpack** or co-serve
from the API app; add the **SPA fallback** (rewrite unknown paths → `index.html`) so deep links and
refresh work, and cache-bust on the hashed filenames. Before handoff, verify the production build,
static route, SPA fallback, cache behavior, and health endpoint; deployment execution belongs to the human release owner.
Capture browser error, latency, and navigation telemetry using approved correlation fields.
