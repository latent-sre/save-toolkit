# Group 03 — frontend-craft

Reviewed 2026-10-02 in `F:\repos\sre-agents-audit-20261002`, against frozen canonical baseline `a2d2e57d2de70125dbde002072853e73b788bd8d`. Invoking caller: `/root`; human owner: the user. Assignment: six read-only passes on the frontend bundle and its direct consumers/verification. The parent objective remains all skills, then agents, with findings committed after each group of three.

**Verdict: the skill is suitable; its independent UI oracle has two confirmed, medium-severity acceptance weaknesses.** The visible-state checks can accept hidden or unrelated status content, and the filter check does not verify filtered results. These weaken evidence about generated interfaces; they are not evidence that a deployed interface currently has either defect. No material defect was confirmed in the four skill guidance files themselves.

## Scope and evidence contract

[verified] Read the complete bundle: `skills/frontend-craft/SKILL.md` and `references/{design-language,stack,network-and-sessions}.md`. There are no scripts or executable assets in this bundle. Read the entire direct build scenario `evals/build-scenarios/build-software-engineer-incidents-page.yaml` and its 279-line oracle `evals/oracles/incidents-page/probe_ui.test.tsx`; inspect all three directly overlapping discovery scenarios, relevant `evals/README.md` and harness-test passages, the software engineer's loading contract, and `stack-profile`'s application/data reference. A scoped diff against the frozen baseline returned exit 0 without changes to these skill/oracle/scenario paths.

Requirements: respect the existing application stack; provide accessible, observable interface behavior; preserve request/session identity; serve assets and backend routes correctly; and distinguish rendered/tested behavior from missing verification. Evidence comprises local source, current primary documentation, and two pinned upstream reads. No native model trial, browser installation, live application, source repair, or dependency installation occurred.

## Pass 1 — suitability, routing, and boundaries

[verified] `SKILL.md:4-7` distinguishes application dashboard pages from Grafana/observability dashboards and backend service implementation. The reciprocal negative cases in `discovery-frontend-craft-defers-observability-dashboard.yaml:3-17` and `discovery-obs-dashboards-defers-app-ui-dashboard.yaml:3-17` check both sides of that routing boundary. The Mantine dependency question supplies an additional positive discovery surface without naming the skill.

`agents/software-engineer.md:97,223` loads the skill for operator-facing UI work. `SKILL.md:13-18` and `stack.md:3-12` preserve existing framework/tooling precedence; the team inventory expressly supports both React and Vue. The build fixture deliberately uses React Router rather than the greenfield TanStack Router default. That is a useful test of repository fit.

The greenfield design reference stays conditional. Keep that boundary: forcing a dark-first visual identity into an established product would violate the entrypoint. The skill reasonably owns interaction and rendering while delegating production deployment to the human release owner (`stack.md:55-56`). No split into extra styling/auth/hosting skills is warranted by the evidence.

## Pass 2 — technical correctness and source currency

[sourced] Current TanStack documentation supports response-defining variables in query keys and three client-side retries; the reference correctly qualifies client queries and makes retry ownership explicit (`network-and-sessions.md:8-20`). The identity-switch rule also requires closing streams and preventing old results from entering the new scope. This is stronger than merely changing a visible username.

[sourced] The EventSource constructor exposes URL and credentials options rather than arbitrary request headers, supporting the cookie/BFF versus fetch-reader distinction at `network-and-sessions.md:35-39`. Vite documents `vite:preloadError` for missing dynamic chunks after deployment. The local guidance adds useful bounded recovery and unsaved-work preservation rather than prescribing unconditional reloads (`stack.md:45-49`).

GitHits retrieved Staticfile buildpack revision `22b502fd`, `src/staticfile/finalize/data.go:123-130`: when pushstate is enabled, any missing request path is rewritten to the index location. This directly supports the warning at `stack.md:39-43`. The surrounding procedure correctly reserves backend and public/static asset paths, checks with `dist/` mounted when co-serving, and distinguishes revalidated HTML from hashed assets. No current product-specific contradiction was found. Target buildpack versions, routing configuration, CSP, IdP/session setup, and actual deployed cache headers remain unverified.

## Pass 3 — workflow, trust, failures, and recovery

[verified] Destructive/bulk actions require target/count confirmation, a pending-state control, one idempotency key per accepted user intent, and per-item outcomes including unknown (`SKILL.md:41`). Authentication guidance preserves the application's contract, keeps bearer tokens out of URLs/localStorage, and limits auth-retry replay to safe cases (`network-and-sessions.md:24-31`). These are coherent requirements rather than a grant of infrastructure authority.

The failure paths include independent panel errors, stale/disconnected live data, stream teardown, replay-gap resynchronization, and old-chunk recovery. Important adversarial cases therefore have written coverage: a late response after a tenant switch; a write whose network outcome is unknown; an SSE reconnect missing events; and a lazy import from a prior release. None was exercised against a running application in this audit.

The screenshot rule is conditional on available repository/browser tooling, prohibits unapproved browser downloads, and requires explicit gap reporting (`SKILL.md:49-58`). That is appropriate for the current audit, whose caller prohibited installations. A component test or screenshot alone does not prove keyboard navigation, announcement timing, production asset routing, or release transitions; the skill does not claim otherwise.

## Pass 4 — LLM readability, policy, and context cost

[verified] The four-file bundle is 16,530 bytes and 2,336 whitespace-delimited words; the entrypoint is 6,300 bytes/945 words. These are measured file/word counts, not tokens. The tables carry concise decisions, and the three references avoid making every UI task load the whole stack, visual-language, and network material.

The Mantine prohibition explicitly identifies itself as house policy and disclaims a technical incompatibility claim (`SKILL.md:36-37`). Dark-first design, the spacing scale, font suggestions, optional decoration libraries, chart defaults, and generated OpenAPI clients are also conventions, not universal technical requirements. Existing project conventions remain the first rule. Do not file these preferences as correctness defects.

Deletion-first improvement is optional: prune optional visual-library brand examples at `stack.md:17-18` if they do not help the team choose a capability. Preserve the behavior-versus-styling distinction, semantic HTML default, and rule to add only needed dependencies. The main actionable work is in the oracle, not another layer of prompt instructions. No evidence here justifies a large rewrite or token budget.

## Pass 5 — verification coverage and oracle validity

[verified] The build scenario is substantially better than a discovery-only test. It loads the real skill, renders the submitted `App` against probe-owned MSW responses, checks URL state, names, row status text, and an axe result, then separately checks typechecking and the agent's own completed verification. The oracle is written after the agent's work, reducing direct answer leakage (`build-software-engineer-incidents-page.yaml:279-309`). Preserve these strengths.

However, bars 1–3 reduce presence to counts and bar 5 checks URL/control state without its data effect (FE-01/FE-02). The scenario uses JSDOM (`:99-108`); its seven assertions do not measure screenshot appearance, 320-pixel reflow, native keyboard traversal, first-paint theme behavior, or a real screen reader. Bar 6 also disables three document-level axe rules (`probe_ui.test.tsx:250-257`). Those are declared fixture limits, not proof of full WCAG conformance.

The Mantine discovery case's prose success criteria are broader than its routing-only executable expectation (`discovery-frontend-craft-blocks-mantine-tailwind.yaml:7-16`). A successful invocation does not itself establish a correct policy explanation. Shared reference-identity and exact-fields findings AA-01/EL-01 are not duplicated here.

[verified: centralized execution] The centralized offline suite passed 1,470 tests/2,690 subtests, with 19 skips; 192 specs/737 expectations validated. The root checked module availability for this focused reproduction: React, Testing Library, Vitest, and JSDOM were unavailable. They were not installed. Accordingly, FE-01/FE-02 are supported by direct predicate inspection and primary/upstream query semantics; a complete mutant UI was not executed.

## Pass 6 — adversarial review and findings

| Counterexample | Present evidence and required result |
|---|---|
| A hidden span says “Loading”, “Error”, or “No incidents” | Text fallbacks count it; the claimed visible-state result must fail (FE-01) |
| A permanent unrelated connection status exists during the incidents request | A `role=status` count alone is insufficient; require the relevant state and transition (FE-01) |
| The status select updates `?status=closed`, but both open and closed rows remain | URL round-trip passes; actual filter acceptance must fail (FE-02) |
| Tenant A's slow response finishes after switching to tenant B | The network contract requires scope isolation; runtime result unverified |
| A browser tab requests a removed old chunk after rollout | Preserve work, show bounded recovery, and avoid reload loops; runtime result unverified |
| Missing `/favicon.ico`, `/assets/missing.js`, or a co-served unknown API path | Keep asset 404/API handler semantics; do not return SPA HTML/200 |
| A visually correct status is never announced, or a table forces all controls offscreen | Perform the stated accessibility/reflow checks; the current DOM oracle is insufficient |

### FE-01 — Presence-based state checks can pass invisible or unrelated content

**Category:** confirmed verification defect. **Severity:** Medium. **Confidence:** High. **Locations:** `evals/oracles/incidents-page/probe_ui.test.tsx:66-75,133-185`; corresponding claimed outcomes at `evals/build-scenarios/build-software-engineer-incidents-page.yaml:290-293`.

**Trigger:** a page leaves matching status text in a `display:none` element, or has an unrelated permanent status region. `loadingIndicator()` accepts a nonzero text/attribute/status count; bar 2 adds alert and error-text counts; bar 3 accepts empty-state text anywhere. None of those fallback assertions verifies visibility or response-driven appearance/disappearance. Role queries ordinarily exclude inaccessible elements; the hidden-text/attribute fallbacks create the concrete visibility gap, while the unrestricted status-role branch creates the unrelated-status gap.

**Consequence:** checks described as a visible loading state, inline failure, and designed empty state can pass while the relevant region remains blank. This is a false-positive acceptance path in the oracle, not an observed application incident.

**Evidence:** local control flow plus Testing Library's official example that finds `display:none` text and separately asserts `not.toBeVisible`. GitHits `dom-testing-library@6049cc0b`, `src/queries/text.ts:18-45`, confirms text queries filter selectors/text without a visibility test.

**Smallest fix:** scope the observation to the affected page/state, assert visibility of the matching state, and check the transition when the controlled request resolves. Preserve legitimate accessible loading alternatives instead of requiring one CSS implementation. **Verification:** a correct reference page passes; hidden-message and permanent-unrelated-status mutants fail their bars. Native browser/accessibility verification remains separate.

### FE-02 — The status-filter oracle never checks the filtered result

**Category:** confirmed verification coverage defect. **Severity:** Medium. **Confidence:** High. **Locations:** `evals/oracles/incidents-page/probe_ui.test.tsx:212-244`; task requirement at `evals/build-scenarios/build-software-engineer-incidents-page.yaml:19-21`.

**Trigger:** implement a select that reads/writes the `status` URL parameter while always displaying every incident. Bar 5 sees `status=closed` and later an `open` selected control; it never checks whether the nonmatching row disappeared. The baseline status-text check at `:265-278` runs separately without filtering, so it does not close this gap.

**Consequence:** an essential requested feature can be ineffective while the independent filter check passes. The page's own tests may catch it, but the scenario only requires some passing incidents test, not this behavior (`build-software-engineer-incidents-page.yaml:299-300`).

**Smallest fix:** after selecting closed, assert the closed incident is present and the open incident absent; after loading the open URL, assert the inverse. Verify the visible output so both valid client-side and server-side filtering remain acceptable. **Verification:** a URL-only mutant fails, a real filter passes, and deep-link restoration checks both control and rows. Full mutant execution remains pending the existing fixture dependencies.

### FE-R01 — Add bounded evidence for untested browser and session behavior

**Category:** recommendation / runtime gap. **Priority:** Low. **Confidence:** High on missing coverage, unverified on actual failure. **Locations:** `SKILL.md:24-30,44-58`; `network-and-sessions.md:8-16,35-39`; `stack.md:45-56`.

Avoid broad new campaigns. When these flows next change, select the affected case: an old tenant request completing late, a reconnect replay gap, or a missing lazy chunk with unsaved input. Use available browser tooling for keyboard/reflow/status checks and record what was observed. Calibrate FE-01/FE-02 first; otherwise a larger evaluation batch can repeat false-positive evidence. No installation or live/model campaign is authorized by this recommendation.

## Sources and return

Sources checked 2026-10-02:

- Context7: [Testing Library visibility example](https://testing-library.com/docs/example-findByText/), [query keys](https://tanstack.com/query/latest/docs/framework/react/guides/query-keys), and [important defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults).
- GitHits: [text-query implementation at 6049cc0b](https://github.com/testing-library/dom-testing-library/blob/6049cc0b/src/queries/text.ts); [Staticfile rewrite at 22b502fd](https://github.com/cloudfoundry/staticfile-buildpack/blob/22b502fd325f5725e0a1d5972f9b59ca9ec6d8c2/src/staticfile/finalize/data.go#L123).
- Official web documentation: [W3C status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html), [W3C reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html), [EventSource constructor](https://developer.mozilla.org/en-US/docs/Web/API/EventSource/EventSource), and [Vite import-error handling](https://vite.dev/guide/build.html#load-error-handling).

Recipient: `/root`. Assignment complete; only this UTF-8 scratch report was written. Caller next step: retain the static-versus-executed distinction, include FE-01/FE-02 and the evidence gaps in group 03's findings commit, then continue the parent audit. Repair and native acceptance remain separate work.

## Central verification

The caller adjudicated this report against its cited source and [group 03 verification](verification.md). Static findings, executed counterexamples, the frozen-baseline atlas contract and unavailable UI execution remain explicitly distinguished.
