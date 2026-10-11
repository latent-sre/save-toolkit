# ADR: Rebuild frontend-craft on the owner's decisions

- **Date:** 2026-10-11
- **Status:** accepted by the owner on 2026-10-10 and 2026-10-11 (the decisions below); the
  implementing candidate, PR #355, awaits exact-candidate acceptance
- **Decision owner:** Save Toolkit owner

## Context

`frontend-craft` arrived whole from a sister repository on 2026-07-14 (`e3466b89`) [verified]. On
2026-10-10, five read-only scans found that none of its rules carried an owner decision [verified]:
- The Mantine ban had lost its technical reason on 2026-09-08 (`9d3589e3`) and survived as an
  unowned "house styling policy".
- Vue, which the team runs, had two lines of guidance.
- The skill said almost nothing about consuming the team's API contract.
- Rendered trials later showed its operator pages coming out in browser defaults.

The owner asked for a total rewrite.

## Decision

The owner's decisions, recorded in the skill's owner-decisions table [sourced: owner]:

1. **Purpose.** The skill serves the UIs of the team's SRE tooling and a few outward-facing
   sites. Its bar is "not the standard AI style, not a basic UI": the skill brings
   modern-frontend capability the team may not know to ask for. That covers live data and
   streaming, dense data and keyboard navigation, motion, and rich editing.
2. **Frameworks.** React and Vue are both supported. An existing app keeps its framework. A new app
   is React, unless the caller or its neighbouring apps say Vue.
3. **Component library.** One component system per app, with animated collections and Motion
   layered on top. Any kit the caller names is allowed, including Mantine and Blueprint. A new
   React app starts from either shadcn/ui + Tailwind + Motion or HeroUI + Motion; the agent asks
   the caller which. A new Vue app starts from shadcn-vue + Tailwind + motion-v. The Mantine and
   `@mantine/charts` bans are withdrawn: the owner wants Mantine available.
4. **Design registers.** Operator tools get the dense, keyboard-first console register; sites get
   the expressive register. The agent names the register in a design brief before styling, even
   when the request never mentions a look.
5. **API.** The UI binds to `backend-craft`'s house contract, published as OpenAPI by the team's
   FastAPI and Go services. That means RFC 9457 problems with a `request_id`, cursor pages, and an
   `Idempotency-Key` on writes. Error surfaces show the request ID.
6. **Where decisions live.** In the skill's own table, not only in `stack-profile`.
7. **Delivery.** The core skill comes first; the four capability references (live data, dense
   data, motion, rich editing) follow in their own pull requests.

Rejected [sourced: owner]:
- **A house ban on any kit.**
- **No component-library policy at all.** The owner chose it first, then replaced it with
  decision 3.
- **One default stack for new React apps.**
- **React only for new apps.**
- **A generic, contract-free API rule.**

## Consequences

- **Agents style pages unprompted.** They load the design reference and write a brief before any
  page, and start an unstyled app from `assets/console-theme.css`.
- **Library combinations are limited by fact, not policy.** The animated collections (Animate UI,
  Aceternity, React Bits, Magic UI) install through the shadcn registry. They share shadcn's
  token names, which HeroUI defines differently, so they belong with the shadcn default [sourced:
  public documentation, 2026-10-10].
- **Evidence.** On 2026-10-10 and 2026-10-11, clean-room trials took the operator pages from
  browser defaults to styled consoles [verified; one trial per arm]. The owner judged the first
  round's log tail "very plain" and the second round "so much better" [sourced: owner]. The
  harness, voided runs and grader scores are in PR #355.
- **Measurement.** The three build scenarios added with the skill (incidents console, live log
  tail, status front page) and their stylesheet check measure these decisions. The Mantine
  discovery case is graded for the one-component-system-per-app rule.
