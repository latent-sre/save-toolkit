# Open frontend stack

Read when selecting or combining frontend technologies. Load `stack-profile` for the team's language
tooling and deployment environment. Frontend choice is open; it does not change the hosting platform
or authorize deployment. For an existing application, inspect its dependencies, conventions, and
constraints before proposing a change. An authorized rebuild can replace its current choices.

## Choose for the product

React + TypeScript + Vite is a familiar starting point for an application workspace. Vue is welcome;
other frameworks, rendering models, and tools are eligible when they serve the task. Choose a SPA,
static generation, server rendering, or a combination according to navigation, content, indexing,
delivery, and interaction needs. Do not force a site into an application shell.

Frontend library selection is unrestricted. Mantine is approved, including styled
`@mantine/core` components, charts, hooks, and forms. HeroUI, Aceternity, Animate UI, shadcn/ui,
Motion, React Bits, Blueprint, Tailwind, and other suitable libraries are available choices, not
a mandatory bundle or a ceiling. Motion and interactive visual libraries may play a substantial
role in the product.

Select the combination against the actual capabilities and visual direction. A component system,
data grid, chart library, graph/canvas library, animation tool, and styling approach solve different
problems. Prefer a supported capability over rebuilding it merely to avoid a dependency; custom
work is appropriate where it materially improves the product. Explain important tradeoffs such as
interaction coverage, accessibility, integration effort, performance, license, and maintenance.

Check current official documentation and exact-version upstream exports/examples before relying on
a component or configuration. Use Context7 for documented contracts and GitHits for upstream source,
tests, and package evidence when available through the acting lane; otherwise request the supported
research path and label unverified compatibility. Do not assume a React package has a Vue equivalent
or that a third-party component is exported by the underlying library.

## Integrate a coherent system

Combining libraries is supported. Establish how their CSS resets, cascade layers, stylesheets,
providers, theme variables, portals, and stacking contexts interact. Map component styling to the
product's semantic tokens and test overlays, keyboard focus, and appearance together. For Mantine
with Tailwind, check the installed versions' stylesheet and layer setup and verify their combined
theme and interaction behavior.

Use the design system's components and behavior where they fit; extend them deliberately. Keep one
clear owner for each interaction and each piece of state so combined libraries do not duplicate
focus handling, requests, animation, or conflicting selection state.

Modern CSS, browser APIs, SVG, canvas, WebGL, and workers are options alongside framework packages.
Select them for layout, responsiveness, visualization, or computation the product actually needs.
Verify browser support and a usable fallback for the target environment. Choose client/server work
and code loading with the expected data size and interaction latency in mind.

## Contracts and application state

Python and Go services supply the backend; FastAPI is the Python framework and OpenAPI describes the
API contract. Choose a compatible typed client generator or maintain the project's existing typed
client, and verify it against the actual schema.

Choose routing, server-state caching, table behavior, form handling, and shared state independently
from the visual library when useful. TanStack tools and framework-native alternatives are examples,
not mandated dependencies. Keep authoritative server data, shareable navigation, and transient UI
state distinct. Use a store when the workflow benefits from it.

Use the relevant patterns from [advanced interactions](./interactions.md) and the request/session
contract in [network and sessions](./network-and-sessions.md). Read [build and serving](./serving.md)
when packaging or serving the chosen frontend.
