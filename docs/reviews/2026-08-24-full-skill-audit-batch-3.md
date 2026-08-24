# Full skill audit — batch 3: diagnosis, incidents, and operating evidence

> **Status: review evidence, not a second backlog.** This batch audits exactly five canonical
> skills on the revision named below. Recommendations not implemented here require a new owner
> decision before they become work.

**Audit baseline:** `92f425dcf279071f6e06d18936e24b3f526cbf6f`
**Batch scope:** `root-cause`, `incident-command`, `postmortem`, `runbook`, and
`service-readiness-audit`
**Audit date:** 2026-08-24

## Conclusion

The five skills have coherent ownership and unusually strong evidence boundaries. `root-cause`
should remain unchanged. The other four needed bounded corrections:

1. Prevent incident command from inventing human names when the packet supplies only roles.
2. Let postmortems choose a causal-analysis method that matches branching evidence instead of
   forcing every incident into a linear Five Whys quota.
3. Complete the Confluence export path: keep the API token out of curl's argument, propagate HTTP
   and missing-body failures, and extract the rendered `body.view.value` HTML from the v2 JSON.
4. Make the Confluence converter require and validate a schema-compatible `service_id`, and encode
   CLI metadata as one quoted value so newline-bearing input cannot inject structure.
5. Replace a stale unverified Pandoc syntax note with current primary documentation.
6. Ask for up to three readiness fixes and prohibit padding when fewer validated gaps exist.

No description, routing metadata, agent, dependency, delegation edge, retry loop, production
authority, severity policy, or generated adapter changes in this batch.

## Method and evidence

### Local baseline

- `[verified]` The baseline contains 30 canonical skill entrypoints totaling 193,636 Git-object
  bytes. The five Batch 3 entrypoints total 25,331 bytes.
- `[verified]` All 13 files in the five bundles were inspected: five entrypoints, five references,
  two assets, and one deterministic converter. Every supporting file is linked from its
  entrypoint.
- `[verified]` Current scenarios cover discovery for all five skills: one root-cause calibration,
  one incident-command regression, one postmortem deferral calibration, two runbook discovery
  cases, and one readiness-audit regression. A direct scribe scenario covers the runbook artifact.
- `[verified]` The existing Confluence converter suite covered nine behaviors but did not validate
  the reference's credential example, the schema pattern for `service_id`, or multiline metadata.
  Three focused tests were added first and failed for those exact omissions while the other nine
  cases passed.
- `[verified]` After the changes, all 12 converter/reference tests pass. Invalid service IDs fail
  before a draft is written; a multiline owner round-trips as one quoted YAML scalar; the reference
  contains no token-bearing curl argument, fails closed on HTTP/null-body responses, and extracts
  the rendered HTML from the API envelope.
- `[unverified]` No paid/live routing trial was run. No routing description changed, so the
  repository's change playbook does not require a routing campaign for these body, asset,
  reference, script, and output-contract corrections.

### Current external sources

- `[sourced]` Current curl documentation says username-only `--user` prompts for a password and
  warns that a password placed in the option argument may remain visible briefly even when curl
  tries to hide it: [curl `--user`](https://curl.se/docs/manpage.html#-u).
- `[verified]` GitHits confirmed the same behavior in current curl upstream at
  `curl/curl@a1bca29bdd7c8ae2d7e195e47bca1f471f333e54`: the
  [option contract](https://github.com/curl/curl/blob/a1bca29bdd7c8ae2d7e195e47bca1f471f333e54/docs/cmdline-opts/user.md#L18-L33),
  [password-prompt path](https://github.com/curl/curl/blob/a1bca29bdd7c8ae2d7e195e47bca1f471f333e54/src/tool_paramhlp.c#L546-L597),
  and [no-echo terminal read](https://github.com/curl/curl/blob/a1bca29bdd7c8ae2d7e195e47bca1f471f333e54/src/tool_getpass.c#L164-L192).
- `[sourced]` Current Atlassian Confluence Cloud documentation identifies account email plus API
  token as the Basic-auth pair and documents `body-format` on the v2 page endpoint:
  [Basic auth](https://developer.atlassian.com/cloud/confluence/basic-auth-for-rest-apis/) and
  [Get page by id](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/).
- `[sourced]` Current Pandoc documentation supports `-f`/`--from`, `-t`/`--to`, `gfm`, and `-o`:
  [format selection](https://pandoc.org/demo/example33/2.2-specifying-formats.html) and
  [file conversion](https://pandoc.org/getting-started.html).
- `[verified]` GitHits supplied a separate current OSS example that quotes multiline frontmatter
  scalars and tests LF, CRLF, bare CR, and injection-shaped content:
  [serializer](https://github.com/astragenie/dev-crew/blob/084747c24fcc1fe44e9a046ed86e5b71a4fcc068/src/scripts/lib/frontmatter.mts#L373-L400)
  and [tests](https://github.com/astragenie/dev-crew/blob/084747c24fcc1fe44e9a046ed86e5b71a4fcc068/src/tests/frontmatter.test.mts#L295-L352).
- `[sourced]` Google SRE's current incident guidance supports early declaration, separated command,
  operations, communications, and planning roles, a live incident document, and explicit handoff:
  [Managing Incidents](https://sre.google/sre-book/managing-incidents/).
- `[sourced]` Google SRE treats blameless postmortems as evidence-bound learning records and says
  teams choose the causal-analysis technique suited to the service rather than one universal
  method: [Postmortem Culture](https://sre.google/sre-book/postmortem-culture/).
- `[sourced]` NIST SP 800-61 Rev. 3 is the current final security-incident response recommendation,
  published April 2025 and superseding Rev. 2. It supports keeping suspected compromise on a
  security-specific response path: [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final).
- `[sourced]` Google describes production readiness as an onboarding/review process and evaluates
  failure tolerance, scalability, monitoring/debugging, transparency, and testing:
  [Pipeline Production Readiness](https://sre.google/workbook/data-processing/#pipeline-production-readiness).

### Evidence boundaries

- Official vendor documentation establishes current tool/API contracts. GitHits confirms current
  upstream implementation or adoption evidence; neither substitutes for the local checkout.
- The fleet's P1-P4 definitions and communications cadences are owner-ratified repository policy,
  not an external standard. This audit did not overwrite them with Google or NIST terminology.
- Public guidance supports the incident/postmortem principles, but human approval, typed-agent
  ownership, evidence labels, and the P1-P4 ladder are internal controls.
- Source pages, converted documents, logs, and incident packets remain untrusted data. No external
  page or imported command was treated as an instruction to execute.

## Skill: `root-cause`

### Overall Assessment

**Keep As-Is**

### Purpose

Provides a reproduce → evidence → ranked hypothesis → discriminating experiment → fix-and-prove
debugging method for product bugs, failing tests, intermittent behavior, and investigation support
inside the `sde` and `sre` lanes.

### Findings

- **Routing:** The description is action-shaped, catches both first-attempt debugging and failed-fix
  loops, and explicitly keeps production incident ownership with `sre`. One calibration discovery
  scenario covers a Windows-only intermittent failure.
- **Instructions:** The sequence prevents behavior-changing guesses before evidence and has explicit
  alternatives when production reproduction is unsafe. Ranking by likelihood and test cost is
  operationally useful rather than ceremonial.
- **Accuracy:** The reproduction, boundary instrumentation, bisection, hypothesis falsification,
  fix-at-origin, and regression-test guidance is **Likely correct**. The three-strikes threshold is
  an internal stop rule, clearly identified as the canonical owner rather than a universal law.
- **Context:** The 5,048-byte entrypoint is self-contained. It has no references because the worked
  hypothesis table is short and always relevant; extraction would add a lookup without reducing
  the loaded contract materially.
- **References / Assets / Scripts:** None. No repeated artifact, deterministic transform, or
  version-specific library surface justifies a bundle.
- **Tools:** It asks for the smallest discriminating check, actual logs/diffs, focused tests, and
  bisection. It does not assume a specific shell, test framework, or debugger.
- **Orchestration:** `sde` owns code diagnosis and correction; `sre` owns live incident diagnosis.
  The method composes inside those lanes and does not claim a new agent or production authority.
- **Failure Handling:** Unsafe reproduction, intermittence, indistinguishable hypotheses, three
  failed fixes, symptom patching, and architectural-layer mismatch all have explicit stop/restart
  behavior.
- **Verification:** Success requires the corrected regression plus the original reproduction, not
  a passing narrow test alone. The existing discovery case checks activation and evidence-first
  behavior but does not exercise a complete diagnosis.
- **Portability:** The method is language, host, and vendor neutral. `git bisect` is an example for a
  Git checkout, not a required runtime.

### Routing Tests

#### Should trigger

1. “This parser test fails only on one Windows runner; diagnose it before changing code.”
2. “The last two fixes did not stop duplicate jobs. Rebuild the evidence and ranked hypotheses.”
3. “Why does this request become corrupt between the API and worker boundary?”

#### Should not trigger

1. “Coordinate the active customer outage and publish the next incident update.”
2. “Write the resolved incident's repository postmortem from this evidence packet.”
3. “Implement the already-diagnosed null check and regression test.”

#### Boundary cases

1. “Production is failing and cause is unknown” — `sre` owns; it may load this method without
   transferring incident ownership.
2. “A local test failure suggests a production risk” — `sde` diagnoses the reproducible code path;
   do not declare an incident without live impact evidence.

**Evaluation:** `[verified]` One calibration discovery scenario covers an intermittent Windows
failure and evidence-first response. `[unverified]` No direct scenario proves ranked hypothesis
elimination, three-strikes restart, or original-reproduction closure.

### Recommended Changes

None. The current content is dense because each step prevents a distinct guessing failure; no
contradiction, stale tool contract, or unnecessary resource load was found.

### Keep As-Is

- Keep unsafe-production alternatives adjacent to the reproduce rule.
- Keep the hypothesis table in the entrypoint as the method's compact executable shape.
- Keep the three-strikes owner statement in one place.
- Keep fix-at-origin distinct from adding downstream validation defenses.

## Skill: `incident-command`

### Overall Assessment

**Minor Changes**

### Purpose

Coordinates a live reliability incident: provisional P1-P4 classification, explicit command roles,
one UTC state record, stakeholder cadence, reversible mitigation selection for human execution,
and resolution handoff without absorbing technical investigation or production authority.

### Findings

- **Routing:** Declaration, severity, coordination, communications, and mitigation-choice triggers
  are distinct from `sre` diagnosis and `scribe` retrospective writing. One regression discovery
  scenario exercises a growing checkout outage and the no-execution boundary.
- **Instructions:** Command separation, one source of truth, early declaration, security carve-out,
  human-only effects, and conditional reference loading are precise. The old role rule said to name
  humans even when the packet contained no people, creating pressure to fabricate names.
- **Accuracy:** The role separation and live state record align with current Google SRE guidance.
  The security exit aligns with the current NIST security-response boundary. The P1-P4 thresholds
  are **Verified internal policy**, not claimed as Google or NIST standards.
- **Context:** The 3,953-byte entrypoint loads only the severity, command/comms, or mitigation lane
  that matches. Cross-lane incidents reuse one state record instead of loading parallel processes.
- **References / Assets / Scripts:** Three references partition classification, coordination, and
  mitigation cleanly. No executable asset belongs in a recommendation-only command lane.
- **Tools:** Status blocks, UTC timelines, fixed communications cadences, decision packets, and
  golden-signal windows are operational tools. Example production commands remain explicitly
  unverified and human-run.
- **Orchestration:** The IC owns process; `sre` owns investigation; a human release owner executes;
  `observability-engineer` owns recovery/detection evidence; `scribe` receives the final timeline.
  The corrected role rule uses supplied names or accountable pager/team roles without invention.
- **Failure Handling:** Unbounded blast radius rounds severity up; growing impact re-pages; security
  events preserve evidence; failed mitigations stay recorded; a single green data point cannot
  close a metastable service.
- **Verification:** Resolution requires sustained recovery evidence and a labelled handoff. Current
  discovery coverage checks activation, roles, UTC timeline, update time, and non-execution but
  cannot load detailed references in its tool-restricted environment.
- **Portability:** Incident Command System roles, UTC state, and mitigation packets are portable.
  P-level meanings, typed agents, PCF commands, and the production gate are internal/platform
  choices.

### Routing Tests

#### Should trigger

1. “Checkout is failing for most users; declare, assign roles, and set the next update.”
2. “Should this growing degradation be P1 or P2, and who must be paged?”
3. “Choose between rollback and route remap, but prepare only the human approval packet.”

#### Should not trigger

1. “Trace this latency regression through logs and form hypotheses.”
2. “Write the postmortem for yesterday's resolved outage.”
3. “Execute the approved production rollback now.”

#### Boundary cases

1. “A suspected compromise is causing errors” — declare at least P1, preserve evidence, and hand
   control to the human security incident owner; do not use generic reliability mitigation.
2. “No responder names were supplied” — assign accountable pager/team roles and mark human binding
   pending; never invent a person merely to fill the status block.

**Evaluation:** `[verified]` One regression discovery case covers declaration and shared entrypoint
controls. `[unverified]` No component-capable direct case exercises severity/reference selection,
security exit, mitigation packet completeness, or supplied-name versus unknown-role behavior.

### Recommended Changes

#### Change 1 — make incomplete role packets explicit without inventing people

- **Problem:** “Name” every live human role was impossible when the input contained no responder
  roster and could reward fabricated names.
- **Evidence:** The current regression prompt supplies no people while asking for assignment; the
  fleet's evidence rule forbids inventing facts.
- **Change:** Bind supplied names. Otherwise assign an accountable pager/team role, mark named-human
  assignment pending, and ask the human commander to bind it in the live record.
- **Expected improvement:** Keeps the response operationally owned without converting missing
  incident data into a hallucinated identity.
- **Risk/tradeoff:** The first status block may contain a clearly labelled pending human binding;
  that gap is more honest than a false person and must be resolved by the live commander.

### Keep As-Is

- Keep provisional severity and round-up-on-uncertainty behavior.
- Keep command separate from investigation and production execution.
- Keep the suspected-security-event carve-out in the entrypoint.
- Keep one authoritative status block and explicit handoff acknowledgment.

## Skill: `postmortem`

### Overall Assessment

**Minor Changes**

### Purpose

Supplies the evidence-bound, blameless structure used by `scribe` after resolution: impact,
timeline, trigger and systemic causes, detection, response, learning, luck, and owned durable
actions.

### Findings

- **Routing:** Explicit invocation or selected postmortem mode loads the structure; ordinary writing
  belongs to `scribe`, and active incidents stay with `sre`/`incident-command`. One calibration
  scenario checks that ordinary writing defers correctly.
- **Instructions:** The blameless stance, evidence for “no data loss,” detection-gap ownership,
  mitigative/preventative actions, proof of done, and learning dispositions are high-signal. The old
  template made Five Whys look mandatory for every incident despite the body recognizing multiple
  systemic and contributing causes.
- **Accuracy:** Current Google SRE guidance supports blameless, evidence-based learning and explicitly
  says teams choose causal techniques suited to their services. The corrected template makes Five
  Whys optional and permits branching methods.
- **Context:** The 4,475-byte entrypoint keeps the always-used method inline and one fill-in template
  in an asset. There is no unnecessary source preload.
- **References / Assets / Scripts:** The single template mirrors the body and now names a method
  field. A deterministic generator would not improve incident-specific causal judgment.
- **Tools:** Timeline evidence, causal method, action table, durable artifact, proof-of-done, and
  disposition table are sufficient. The documentation lane correctly does not fetch or execute.
- **Orchestration:** `scribe` writes; `sre` supplies diagnosis; `observability-engineer` owns
  detection changes; `sde` owns code; human release owners own deploy/rollback safety.
- **Failure Handling:** Unknown causes remain unverified; absent data-loss evidence stays explicit;
  unsupported action items cannot masquerade as completed; near-misses retain a smaller but complete
  learning path.
- **Verification:** Every claim preserves evidence labels, action items require proof of done, and
  unresolved claims land in verification gaps. No direct postmortem artifact scenario targets this
  skill; scribe behavior carries the output test.
- **Portability:** Blameless analysis and action ownership are portable. Typed fleet handoffs,
  repository dispositions, and evidence labels are internal conventions.

### Routing Tests

#### Should trigger

1. “Postmortem mode is selected; apply the fleet template to this supplied timeline.”
2. “Use the postmortem structure for this resolved data-integrity near-miss.”
3. “Explicitly invoke the postmortem skill and disposition every new operational fact.”

#### Should not trigger

1. “The outage is still active; establish severity and restore service.”
2. “Write the resolved incident document from this packet” without selected mode — route to
   `scribe`.
3. “Debug why the worker duplicated messages.”

#### Boundary cases

1. “Cause is not confirmed, but the incident is resolved” — write the record with `[unverified]`
   cause and a confirmation owner; do not delay all learning or manufacture certainty.
2. “The incident has several independent contributing paths” — use a branching method; do not force
   a single Five Whys chain.

**Evaluation:** `[verified]` One discovery calibration checks deferral to `scribe` and preserves the
postmortem outcome. `[unverified]` No direct scenario checks causal branching, data-loss evidence,
luck, or action proof-of-done.

### Recommended Changes

#### Change 1 — make causal analysis evidence-shaped, not template-shaped

- **Problem:** A mandatory-looking Five Whys section could flatten a distributed incident into one
  linear story and reward filling five rows after the evidence stopped.
- **Evidence:** The body names root and contributing causes; current Google SRE guidance says teams
  select the analysis technique suited to their service.
- **Change:** Name Five Whys as one option, add a causal-method field, and permit fault trees, causal
  graphs, or another evidence-suited method with branches.
- **Expected improvement:** Preserves multiple causal paths and uncertainty while keeping a compact
  default for simple incidents.
- **Risk/tradeoff:** Postmortems may use different analysis shapes; the required evidence, action,
  and disposition sections still preserve comparable outcomes.

### Keep As-Is

- Keep the blameless system-and-decision stance.
- Keep explicit evidence for “no data loss” and human detection.
- Keep mitigative versus preventative action typing and proof of done.
- Keep luck and near-miss sections because they expose latent risk cheaply.

## Skill: `runbook`

### Overall Assessment

**Major Changes**

### Purpose

Provides the evidence-bound structure for one operational failure/task, living-runbook accretion,
and one-way Confluence import into the repository while keeping direct documentation with `scribe`
and execution with authorized humans or `sde` where appropriate.

### Findings

- **Routing:** Selected runbook mode or explicit invocation loads the structure; ordinary authoring
  defers to `scribe`, retrospectives to `postmortem`, and live incidents to command/investigation.
  Two skill discovery cases and one direct scribe artifact case cover part of this boundary.
- **Instructions:** The 3 a.m. standard, required slot policy, command evidence rule, living history,
  and import provenance are strong. The export example contradicted its own security statement by
  expanding an API token into curl's `--user` argument.
- **Accuracy:** Current curl documentation confirms the token exposure risk and username-only
  prompt. Current Atlassian v2 documentation confirms that the endpoint returns a JSON `PageSingle`
  envelope, so the primary path now propagates HTTP/null-body failures and extracts
  `body.view.value` before Pandoc. Current Pandoc documentation supports the corrected format
  guidance. The converter's old “schema-valid” claim was false when its default service ID violated
  the published slug pattern.
- **Context:** The 7,385-byte entrypoint progressively loads one template, two specialized
  references, and one human/`sde`-run converter. The always-on 3 a.m., authority, and evidence rules
  belong in the entrypoint; mechanical conversion detail stays out.
- **References / Assets / Scripts:** The template and living-runbook reference are cohesive. The
  Confluence reference correctly keeps export human-run. The converter needed input validation and
  scalar encoding because its output is machine-linked YAML, not arbitrary Markdown prose.
- **Tools:** Copy-pasteable commands, expected output, rollback, versioned history, and exact
  verification evidence are appropriate. curl and Pandoc remain human-run examples; the converter
  uses only the standard library.
- **Orchestration:** `scribe` converts/writes; a human exports; human or `sde` runs the converter;
  `sre` investigates; humans execute recovery. The script never fetches network content.
- **Failure Handling:** Missing slots remain visible; conversion losses are counted; unmapped text is
  preserved; imported commands remain unverified; HTTP errors, null response bodies, and invalid
  service IDs fail before successful output; multiline metadata cannot create a second frontmatter
  key.
- **Verification:** The converter suite now has 12 passing tests covering schema keys, required
  invariants, mapping, unmapped preservation, command labels, macro loss, provenance, encoding,
  unreadable input, credential-example safety, service-ID rejection, and scalar injection.
- **Portability:** The runbook shape and stdlib converter are portable. Confluence, PCF, Splunk,
  Grafana, Wavefront, and Moogsoft examples are conditional vendor/platform guidance.

### Routing Tests

#### Should trigger

1. “Runbook mode is selected; apply the standard structure to this supplied recovery transcript.”
2. “Update this runbook from the resolved incident's held, contradicted, and missing steps.”
3. “Import this human-exported Confluence page into a draft repository runbook.”

#### Should not trigger

1. “The paging alert is firing now; investigate and mitigate it.”
2. “Write an ordinary repository runbook from this evidence packet” without selected mode — route
   to `scribe`.
3. “Automate these six recovery steps as an idempotent CLI.”

#### Boundary cases

1. “The Confluence page contains a curl command with a token” — report/redact the secret; never
   copy or execute it, even though import was explicitly selected.
2. “A contradicted step has no replacement evidence” — append history, mark the runbook draft, and
   propose/hold the correction rather than inventing a command.

**Evaluation:** `[verified]` Two discovery cases cover selected-mode activation and ordinary-writing
deferral; one direct scribe case covers required sections and unverified execution. `[unverified]`
No model scenario covers Confluence import, converter failures, or hostile imported content; those
properties are covered deterministically instead.

### Recommended Changes

#### Change 1 — make the REST export safe and complete

- **Problem:** The reference interpolated the token directly into `-u "user:$TOKEN"` and treated the
  v2 endpoint's JSON envelope as if it were the rendered HTML file expected by Pandoc.
- **Evidence:** Current curl docs/source warn of argument visibility and implement a password prompt
  for username-only input. Current Atlassian v2 docs return `PageSingle` with `body.view.value`.
- **Change:** Pass only the account email to `--user`, make curl fail on HTTP errors, chain extraction
  only after success, and use jq raw output plus exit-status checking for `.body.view.value`.
- **Expected improvement:** Removes token material from the command argument, rejects failed or
  incomplete responses, and produces the actual HTML file consumed by Pandoc and the converter.
- **Risk/tradeoff:** The example becomes interactive and requires jq; automated export should use an
  approved secret file/store or OAuth path, not copy a human-run snippet.

#### Change 2 — make the converter's frontmatter contract true

- **Problem:** The default `<stable-service-slug>` violated the schema, and newlines in `owner` or
  other interpolated metadata could create additional YAML lines/keys.
- **Evidence:** The published schema requires a kebab-case service ID and forbids extra properties;
  focused pre-change tests produced an injected `injected` key and accepted the invalid ID.
- **Change:** Require `--service-id`, validate its schema regex before writing, JSON-quote the
  service ID and owner as YAML scalars, and quote the source URL as one Markdown value.
- **Expected improvement:** Every successful converter run preserves the promised key set and keeps
  CLI metadata data rather than frontmatter structure.
- **Risk/tradeoff:** Calls that omitted `--service-id` now fail clearly and must supply the real
  service-card slug; this is intentional because a placeholder was not schema-valid evidence.

#### Change 3 — replace stale Pandoc uncertainty with current evidence

- **Problem:** The reference marked ordinary `-f html -t gfm -o` syntax unverified because the
  official manual had once been unreachable.
- **Evidence:** Current primary Pandoc pages document the format and output options.
- **Change:** Cite the current pages while retaining the instruction to diff converted output.
- **Expected improvement:** Removes stale uncertainty without overstating conversion fidelity.
- **Risk/tradeoff:** Syntax validity still does not prove macro/attachment fidelity; the diff and
  explicit loss record remain required.

### Keep As-Is

- Keep command execution outside the documentation lane.
- Keep imported commands unverified regardless of page authority.
- Keep append-only incident history pinned to the runbook version used.
- Keep conversion losses and unmapped content visible rather than guessing.
- Keep `last_verified` bound to exact target, actor, timestamp, version, and outcome.

## Skill: `service-readiness-audit`

### Overall Assessment

**Minor Changes**

### Purpose

Performs a read-only, evidence-cited assessment of an existing service across ownership, runtime,
delivery, telemetry, SLOs, dashboards, alerts, runbooks, dependencies, capacity, recovery, and
drift without creating onboarding artifacts or changing live state.

### Findings

- **Routing:** The discoverable audit is clearly separated from explicit-only effectful
  `service-onboarding`. A regression discovery scenario covers the audit; a paired negative
  onboarding case prevents effect-shaped capture.
- **Instructions:** Stack loading, prohibited credential reads, minimum sanitized excerpts,
  evidence-owner routing, and unchanged authority are strong. The old output demanded “the top
  three fixes” even when the evidence supported zero, one, or two findings.
- **Accuracy:** The readiness surfaces align with current production-readiness practice. The P0-P3
  finding rubric is internal risk policy; no external severity vocabulary is substituted. Requiring
  exactly three findings was inaccurate for a fully ready or sparsely evidenced service.
- **Context:** The 4,470-byte entrypoint is self-contained. It loads owning skills only when their
  evidence surface applies and explicitly suppresses their write paths.
- **References / Assets / Scripts:** None. A generic checklist asset would duplicate the evidence
  table; a live collector would violate the read-only/tool-boundary design.
- **Tools:** Repository citations, approved records, guard-safe reads, sanitized excerpts, and
  explicit blocked gaps are sufficient. Credential-bearing `cf`/GCP reads are denied.
- **Orchestration:** Each gap names one owning skill/lane; loading it supplies standards, not
  authority. Onboarding effects require explicit invocation and an approved plan.
- **Failure Handling:** Missing access becomes a blocked evidence gap; absent proof stays
  unverified; effect-shaped requests stop and route to manual onboarding; fewer findings no longer
  cause padded recommendations.
- **Verification:** Findings require authoritative citations or minimal command evidence. The
  discovery scenario is routing-only and does not prove a complete evidence-cited readiness report.
- **Portability:** Ownership, health, telemetry, SLO, recovery, and drift surfaces are portable.
  `stack-profile`, PCF/GCP owners, evidence labels, and onboarding invocation are internal.

### Routing Tests

#### Should trigger

1. “Audit this existing service's operational readiness read-only and cite every gap.”
2. “Is payments ready for on-call ownership? Check alerts, SLOs, runbooks, and recovery evidence.”
3. “Compare declared and observed service readiness without creating any artifacts.”

#### Should not trigger

1. “Onboard this service and create its cards, alerts, and dashboards.”
2. “The service is down now; diagnose the active failure.”
3. “Design the missing SLO and implement its burn-rate alerts.”

#### Boundary cases

1. “Audit readiness and then fix every gap” — perform/report only the read-only audit; each effect
   needs its owning workflow and authority.
2. “The audit found only one validated gap” — return one top fix and passed checks; do not invent two
   more to satisfy a presentation count.

**Evaluation:** `[verified]` One regression discovery case covers activation and read-only posture;
the paired onboarding regression covers the effect boundary. `[unverified]` No direct scenario
supplies a full service evidence packet and grades severity, citations, passed checks, gaps, and
non-actions.

### Recommended Changes

#### Change 1 — make the top-fix count evidence-driven

- **Problem:** Requiring exactly three fixes conflicts with “do not invent evidence” when fewer
  validated findings exist.
- **Evidence:** A ready service or a bounded audit can legitimately have fewer than three gaps; the
  old output contract had no no-padding clause.
- **Change:** Return up to three validated fixes in priority order and explicitly prohibit padding.
- **Expected improvement:** Preserves a concise lead section without turning formatting pressure
  into fabricated readiness defects.
- **Risk/tradeoff:** Reports may have different fix counts, which accurately reflects the evidence.

### Keep As-Is

- Keep the audit discoverable and onboarding explicit-only.
- Keep `stack-profile` as the first platform/runtime authority.
- Keep prohibited credential-bearing reads explicit.
- Keep passed checks, verification gaps, and “What I did NOT do” separate from findings.

## Architecture Findings

1. **Evidence scarcity must shape output cardinality.** Fixed “top N” requirements need a no-padding
   rule or they can manufacture findings.
2. **Human-role requirements need an unknown-input state.** Incident coordination must remain owned
   without fabricating identities absent from the packet.
3. **Machine-linked Markdown needs data/structure separation.** Values interpolated into YAML
   frontmatter require validation or scalar encoding even when the artifact is only a draft.
4. **Documentation examples are part of the security surface.** A human-run command can still leak a
   credential through shell history or process arguments.
5. **Templates must not overrule causal evidence.** A compact default method is useful only while it
   permits branching or another method when the incident demands it.

## Routing Conflicts

- `root-cause` versus `sre`: method versus live-incident ownership is explicit.
- `incident-command` versus `sre`: process/severity/comms versus technical investigation is explicit.
- `postmortem`/`runbook` versus `scribe`: structure skills are explicit/mode-selected; ordinary
  artifact writing belongs to the terminal documentation agent.
- `runbook` versus `ops-tooling`: document the procedure versus automate it is explicit.
- `service-readiness-audit` versus `service-onboarding`: discoverable read-only assessment versus
  explicit-only approved effects has paired regression coverage.

## Shared Resource Opportunities

No extraction is justified. Incident roles, postmortem causal analysis, runbook conversion, and
readiness evidence have different consumers and authority. A shared generic “operations checklist”
would erase those distinctions and increase unconditional context.

## Missing Capabilities

No new capability is established by this batch. Security incident response intentionally exits to
a human owner; this repository should not grow a containment lane from a prompt-only audit. Full
disaster-recovery/capacity capabilities remain owner-held decisions in existing review evidence,
not automatic backlog from this batch.

## Standards / Portability Issues

- curl, Pandoc, Atlassian Confluence, Google SRE, and NIST are external sources with separate
  provenance; none defines the fleet's internal P-level or authority policy.
- P1-P4 severity, typed agents, evidence labels, production gates, and operational-learning
  dispositions are internal conventions.
- Incident Command System roles, UTC state, blameless causal analysis, rollback/verification, and
  evidence-driven readiness are portable principles.
- PCF commands, Confluence imports, and named observability vendors are conditional examples.

## Evaluation Gaps

- All five skills have some discovery coverage, but only incident command, runbook update, and
  readiness audit are regression-labelled; root cause and postmortem remain calibration.
- No component-capable direct case exercises incident reference selection or mitigation packets.
- No direct postmortem case grades evidence-backed data-loss claims, branching causality, luck, and
  action proof-of-done.
- No direct readiness case grades a full evidence packet, including the zero/fewer-than-three
  finding outcome.
- Confluence import is covered deterministically, not by model trials; that is the correct first
  control for serializer, schema, and credential-example contracts.
- No representative prompt distribution supports numeric precision/recall claims. These are
  evidence gaps, not automatic roadmap items.

## Ranked architectural changes

### Critical

None.

### High

- **Implemented:** Remove the API token from curl arguments, fail closed on HTTP/null-body responses,
  and extract rendered HTML from the Confluence v2 JSON envelope for the human export path.
- **Implemented:** Require/validate the converter's service ID and encode metadata as one quoted
  value so successful output satisfies the published frontmatter shape.

### Medium

- **Implemented:** Preserve incident ownership without inventing human identities.
- **Implemented:** Make postmortem causal analysis method-selectable and branching-aware.
- **Implemented:** Prohibit padded readiness recommendations.

### Low

- **Implemented:** Replace stale Pandoc uncertainty with current primary-source evidence while
  retaining the conversion diff requirement.

No further architectural work is activated by this review.
