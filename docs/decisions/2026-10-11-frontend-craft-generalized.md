# ADR: Generalize frontend-craft — React first, any approved kit, mixable, no house look

- **Date:** 2026-10-11
- **Status:** accepted by the owner on 2026-10-11 (the decisions below); supersedes
  [2026-10-11-frontend-craft](2026-10-11-frontend-craft.md); the implementing candidate awaits
  exact-candidate acceptance
- **Decision owner:** Save Toolkit owner

## Context

PR #355 rebuilt `frontend-craft` on 2026-10-10 and 2026-10-11 around two caller-picked React
defaults, one component system per app, two design registers and a shipped console theme
[verified: `b5ec1be`]. The same day the owner asked for a fresh start that uses no history from
other branches or pull requests: the team does a great deal of frontend work across more kinds of
GUI than operator consoles, kept hitting friction from being held to one product line, and wanted a
generalized skill on modern tooling whose pages do not carry the generic AI-generated look
[sourced: owner, 2026-10-11 interview]. The interview's answers are the decisions below.

## Decision

Recorded in the skill's owner-decisions table [sourced: owner]:

1. **Replace in place.** Fresh content under the same `frontend-craft` name, so the
   `software-engineer` load rule, the eval scenarios, the README and the Copilot projection keep
   working. Nothing is carried over by inheritance; the old rules survive only where the owner's
   answers re-chose them.
2. **React is the focus; Vue is allowed.** A new app is React on Vite with TypeScript; Vue is
   allowed when the caller or neighbouring apps say so; an existing app keeps its framework.
3. **The API binding stays.** The UI consumes the team's FastAPI and Go services through their
   OpenAPI documents under backend-craft's contract: a generated typed client, RFC 9457 problems
   carrying a request ID, cursor pages, an `Idempotency-Key` on writes.
4. **Well-defined starting code ships with the skill:** a parametric theme, the problem and
   idempotent-write helpers, a runtime-configuration loader, an error panel, a Vite configuration,
   the PCF deploy files and the serving contract, each with its test where one can run.
5. **Different from the AI default.** No house theme. The skill names the tells of the generic
   look, requires a design brief before any styling, and derives each app's palette from chosen hues
   in OKLCH so every app is its own identity.
6. **Generalized across GUI kinds.** An archetype spectrum — operator console, workbench,
   in-app dashboard, status or catalog site, guided workflow — replaces two registers; nothing
   traps the team in one product line.
7. **The agent asks.** Every new app or area starts with one round of forks put to the caller
   with recommended defaults: audience, archetype, kit, look, density and input, motion, live data,
   serving.
8. **Visual and clickable first.** The team's users look and click: actions sit where the eye
   is, with full keyboard and screen-reader parity. Keyboard-first density is a choice, not the
   register.
9. **Animation is welcome** and budgeted, with a reduced-motion variant of everything.
10. **Kits are mixable.** Any approved kit — shadcn/ui, Radix UI, Base UI, HeroUI, Mantine,
    Material UI, daisyUI, Magic UI, Animate UI, Aceternity UI, React Bits, Motion — may start an
    app or join one; one base kit owns the reset, tokens and provider, and the stack reference's
    mixing rules govern the rest. No kit is banned.
11. **The greenfield stack is a recommendation, not a limit.** The stack reference presents a
    menu per need with a recommended default; the owner asked not to be limited by one stack.
12. **Deep capability references are deferred.** Charts, grids, editors, terminals and graphs
    keep one-line pointers in the stack reference; dedicated references come later.
13. **Serving is localhost and PCF.** The Vite dev server proxies the API locally; on PCF the UI
    runs on the staticfile buildpack with the API on a context-path route of the same host, with
    runtime configuration and a CSP.
14. **A rendered proof** of the skill's own defaults accompanies the candidate.
15. **The reader** is an SRE who is competent but not a frontend specialist: the skill explains
    the why and gives the commands.

Recorded after the candidate's first review, on the owner's answers of 2026-10-11 [sourced: owner]:

16. **One identity per app.** No shared brand or family resemblance is required across the
    team's apps; each brief chooses its own palette, type and signature.
17. **npm and Node 22 or 24.** npm is the package manager for a new app, with one committed
    lockfile; pnpm only where a repository already uses it. Node 22.12 or later, 24 being the
    active LTS line.
18. **The GUI mix is a mix.** The team builds across the archetypes and defines the weighting
    after a few runs rather than up front; the archetypes stay evenly weighted until then
    (`FRONTEND-001` in the roadmap).
19. **ROUTE-004 is closed.** The single Mantine discovery positive, regraded for the mixing rules
    at threshold 1.0, suffices; no replacement calibration case is needed.

Rejected [sourced: owner]: a house theme or register; a ban on any kit; one component system per
app; React only; keyboard-first as the default look; a single default stack.

## Consequences

- The skill loads the design reference before any page and writes a brief; a page that matches
  the tells list is a defect. The shipped theme is parametric, and the repository test proves AA
  contrast at every brand hue in both schemes [verified: `scripts/test_frontend_craft_assets.py`,
  60 passed on 2026-10-11].
- Eval wiring: the three build scenarios and their oracles grade behaviour the new skill still
  requires and are unchanged; the Mantine discovery case is regraded for the mixing rules and the
  owner closed `ROUTE-004` on that case; the asset contract test is rewritten for the new files.
- Library facts in the skill were verified against registries and primary documentation on
  2026-10-11 [verified]: Vite 8, React 19.3, TypeScript 7 as the latest major with no compiler
  API (so new apps pin 6.x while typescript-eslint needs it), Tailwind 4.3, shadcn on Base UI by
  default, HeroUI 3, Mantine 9, Material UI 9, daisyUI 5, Motion 14, TanStack Table 9, MSW 3,
  Vitest 5. Instruction files carry the facts without dates, per the fleet rule; this record is
  where the verification date lives.
- Risks to watch: `light-dark()` is Baseline newly available, which the owner's evergreen-browser
  stance accepts; the staticfile buildpack's `location_include` nesting and the `.profile`
  runtime-configuration write were reproduced against the buildpack's own nginx template locally
  [verified: 2026-10-11, nginx 1.24] but not yet on a foundation, so the serving contract is the
  proof there; the TypeScript 6 pin is a dated workaround to revisit when typescript-eslint
  supports 7.1.
- The rendered proof the owner asked for is retained as
  [docs/reviews/2026-10-11-frontend-craft-proof](../reviews/2026-10-11-frontend-craft-proof/README.md):
  an operator console built from the skill's defaults, typechecked, tested, built, and screenshotted in
  both themes and at 320 px with zero axe violations [verified: 2026-10-11]. It found seven defects
  in the starting code and references, each fixed before this candidate.
- What would show this decision wrong: rendered trials whose pages still read as generic, or
  callers who find the fork questions a burden rather than a service.
