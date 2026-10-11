---
name: frontend-craft
description: "Design and build distinctive, complete frontend products for mixed-experience users, especially SRE team sites, incident investigation workspaces, visual automation builders, and service catalogs. Use for frontend product creation, substantial experience redesign, and complex interaction work. Triggers: \"design a team site\", \"build an incident workspace\", \"create a workflow builder\", \"build a service catalog\"."
---

# Frontend craft

Create a product with a recognizable identity and a dependable path through its users' work. Treat information architecture, visual design, interaction behavior, and implementation as connected decisions. Quality is shared; the composition, character, and feature set belong to the individual product.

Match the requested deliverable. For design work, deliver inspectable designs and decisions. For implementation work, carry the selected experience through working routes, real behavior, integration, and verification.

## Establish the product target

Use the brief and the files the user permits you to inspect. In an existing product, learn its actual navigation, visual language, dependency versions, contracts, and incomplete behavior before proposing changes. Respect the authorized scope and preserve unrelated work.

Form a compact working brief:

- Who uses the product, what they know, and the job they need to finish. Identify both the occasional user and the frequent operator.
- The main journey, the information it needs, and the outcome that demonstrates success.
- Whether the work is a new product, an extension, or a focused repair; what already constrains the design.
- Data sources, expected volume and update frequency, permissions, and actions that have consequences beyond the interface.
- Target screens and devices, including the intended mobile job, if any.

Ask focused questions when an unknown changes the main journey, visual direction, data authority, or implementation feasibility. State reasonable assumptions for small reversible details and continue useful work.

Use these product jobs as starting questions, not screen templates:

| Product | Questions the experience should help answer |
| --- | --- |
| Team site | What does this team do, who owns a topic, and where do I go for help or useful material? |
| Incident investigation workspace | What changed, which evidence supports it, what is uncertain, and what should I inspect next? |
| Visual automation builder | What will this flow do, how do its steps connect, and can I validate, save, and inspect a run? |
| Service catalog | Which service is this, who owns it, what depends on it, and where are its operational resources? |

Choose capabilities from these jobs. A table, chart, graph, palette, or animation earns its place by improving a decision or action. A product does not need the entire capability list.

## Make the direction choice tangible

Prefer dark-first for a new product. Respect an established identity or an explicit alternative. Make dark surfaces legible through tonal separation, typography, edges, and semantic colors; keep severity distinguishable from selection and brand accents.

For a new product without an established direction, develop **two genuinely different visual directions** before committing to the full interface.

- Use the same representative content and main job in both, so the user can compare experiences.
- Change composition and interaction: how information is grouped, the entry point, navigation, density, detail disclosure, and the way a task progresses. A new palette or font alone is insufficient.
- Give each a coherent visual idea: type hierarchy, spatial rhythm, surface treatment, data styling, imagery or illustration where useful, and a characteristic use of motion.
- Show comparable rendered concept slices, with the important interaction demonstrated through states or a small prototype. If rendering is unavailable, provide concrete layouts and transitions and state that the choice has not been visually validated.
- Explain what each direction makes easier and its main tradeoff. Ask for the user's selection after showing the alternatives.

Wait for that selection before making direction-dependent implementation choices. Continue independent contract or data work where useful. If the user explicitly delegates the selection, choose, explain why, and proceed. An existing direction or a focused change does not require another two-direction exercise.

Refine the chosen direction into a coherent system. Derive product-specific typography, spacing, density, surfaces, borders, focus, status, and motion rules. Carry them through secondary routes, forms, menus, charts, and failure states. Keep the chosen composition recognizable during refinement.

Judge identity through actual content: distinctive hierarchy, navigation, data arrangement, and voice. Customize a component library's theme and composition as needed. Decoration cannot compensate for identical page structures or weak task flow. Use motifs deliberately; familiar controls can remain familiar.

## Choose the implementation around the experience

Frontend selection is open. React, Vite, and TypeScript are familiar candidates; Vue is welcome. Consider other approaches when rendering needs, team experience, deployment constraints, accessibility, or maintenance make them a better fit.

Mantine is fully approved, including its styled components and charts. HeroUI, Aceternity, Animate UI, shadcn/ui, Motion, React Bits, Blueprint, Tailwind, and other suitable technologies are options. These names are neither an allowlist nor a required stack. Choose the tools that support the selected experience; verify framework and version compatibility before combining them.

Read [Implementation decisions](references/implementation-decisions.md) when selecting or integrating tools, connecting APIs, or resolving compatibility questions. Use Context7 for official documentation and GitHits for upstream source, tests, and package evidence when available. Inspect the permitted product workspace first for its actual behavior and versions. Keep documented capabilities, upstream evidence, and locally tested behavior distinct.

Backends use Python or Go, with FastAPI for Python and OpenAPI contracts. Treat OpenAPI as the API specification. AI features, chat interfaces, model providers, and credentials enter scope only when the product brief calls for them.

## Build a whole journey before expanding

Implement one representative path from entry to meaningful outcome, including its non-ideal states. Then extend the pattern across the agreed product scope. This early slice should expose layout, data, navigation, and interaction problems while they are still cheap to fix.

For the chosen capabilities, read the relevant sections of [Interaction completion](references/interaction-completion.md). That reference covers rich tables, linked charts and timelines, dependency graphs, workflows, command palettes, keyboard navigation, motion, and explanatory interactive visuals.

For each consequential interaction, decide what activates it, what state changes, what data it uses, how the user knows it worked, and how failure or cancellation behaves. Implement those answers. Define shared selection and filter state when several views describe the same entities.

Use realistic content and data distributions early: long names, missing owners, sparse and dense results, outliers, and delayed responses. Label fixtures or simulations clearly. Preserve their boundary from live data. Every visible control should perform its promised behavior, explain its unavailable state, or be removed from the delivered scope.

Keep the experience approachable. Use direct labels, descriptive errors, units, and explanatory context for unfamiliar terms. Reveal technical detail where it helps the job; keep expert shortcuts discoverable and provide visible ways to accomplish the same work.

Desktop and large screens lead the layout. Use space for useful comparison, persistent context, and appropriately sized detail areas. Decide mobile scope per product: full participation, a reduced set of jobs, or an explicitly desktop-only workspace. Document that decision. Handle resizing, zoom, text expansion, and overflow deliberately. Keep reading and controls usable under zoom even when full mobile authoring is outside scope. A graph or wide table may need its own scrolling region; surrounding controls must remain usable.

Keep access and operational state truthful. A hidden or disabled control does not enforce authorization. Pending work is distinct from confirmed success; stale data is distinct from current data; an unknown outcome is distinct from failure. Preserve useful user work through errors and make recovery specific. Building an interface does not itself authorize deployment or live operational changes.

## Evaluate the rendered experience

Use the browser to complete the main journey, then inspect the routes and states that could invalidate it. Screenshots establish appearance; interaction checks establish behavior. Read the implementation when the two disagree.

Evaluate these outcomes:

| Outcome | Evidence to gather |
| --- | --- |
| The selected identity survives implementation | Rendered primary and secondary views using real or clearly identified fixture content; compare hierarchy and interaction with the selected direction. |
| Users can finish their jobs | Exercise navigation, search, editing, save or submit, cancellation, and recovery as applicable. Reload or revisit where persistence matters. |
| Linked views remain truthful | Change filters and selection, race slow requests, inspect missing data, and verify consistent scope, units, time, and freshness. |
| Mixed-experience users can operate it | Review labels and help; complete essential jobs with keyboard only; check visible focus, focus return, and non-pointer alternatives. |
| The visual system remains usable | Check supported widths, zoom, long text, dense content, empty/error states, contrast, non-color cues, and reduced motion. |
| The implementation holds at realistic scale | Measure loading and key interactions with representative volumes and update rates; inspect request behavior and browser errors. |

Use WCAG 2.2 AA as the accessibility target unless the product has a stricter requirement. Choose semantic controls and established interaction patterns. Combine automated checks with manual keyboard, focus, zoom, and assistive-technology checks appropriate to the product. Report coverage; an automated scan does not establish full conformance.

Set performance expectations from the actual job and environment. Check large tables, graph layouts, linked updates, and animation under plausible load. Optimize measured bottlenecks and recheck that optimization preserves interaction and accessibility.

Run the project's applicable type, build, lint, and test checks. Add focused behavioral tests for important state transitions, data coordination, and regressions. Do not substitute a screenshot gallery or a successful build for a functioning product. When browser or backend access is missing, state precisely which conclusions remain unverified.

## Deliver an inspectable result

Finish with the product outcome, how to run or inspect it, the chosen direction and relevant tradeoffs, and a concise account of actual verification. Identify mocked integrations, unsupported device jobs, remaining defects, and decisions that still need an owner.

Resolve material gaps within the authorized task before calling the implementation complete. If a dependency blocks completion, name the affected job and the evidence needed to unblock it. Keep proposals, implemented behavior, and tested behavior distinguishable.