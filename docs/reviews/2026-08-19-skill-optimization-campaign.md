# Skill optimization campaign — research and evidence

> **Date:** 2026-08-19
> **Base:** `origin/main` at `e31d04e06d3d50e7351f0251768b11c8016c3f10`
> **Scope:** all 29 canonical skills, in batches of 3–5; generated adapters are consequences
> **State:** active; this record is evidence, not release or merge authority

## Conclusion

Optimize for decision value rather than raw brevity. Remove text that merely narrates the process,
repeats generic expertise, embeds a volatile remembered command, or restates the body in discovery
metadata. Retain author-only context, reasons for constraints, exact output contracts, evidence labels,
untrusted-input boundaries, approval gates, failure states, and fragile procedures that prevent a
demonstrated error.

Every deletion is a behavioral hypothesis. Structural validity proves shape, not routing, correctness,
or safety.

## External evidence

### Preferred recent evidence

- `[sourced]` OpenAI Codex commit
  [`5e32f72` (2026-08-13)](https://github.com/openai/codex/commit/5e32f728f1f86a967c6be057351f12505778df8f)
  reworked `skill-creator` around concise scoped instructions, progressive disclosure, explicit
  invocation policy, observable tests, and risk-based forward verification. Its resulting guidance
  says to retain material that changes decisions and make the entrypoint only as long as the task
  requires.
- `[sourced]` Anthropic skills commit
  [`f6656c1` (2026-08-13)](https://github.com/anthropics/skills/commit/f6656c1256d5a8adfa37db9110046ef20bac644c)
  added a prompt-audit method whose rule is specific, tested instructions—not indiscriminate
  shortening. It separates discovery text from behavioral instructions and treats deletion as an
  old/new comparison hypothesis.
- `[sourced]` The Agent Skills specification snapshot updated 2026-08-04 recommends progressive
  disclosure, direct supporting-file links, and a body below 500 lines/5,000 tokens as a ceiling,
  not a size target
  ([specification](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/docs/specification.mdx)).
- `[sourced]` GitHub's 2026-07-29
  [Copilot skills/MCP GA announcement](https://github.blog/changelog/2026-07-29-copilot-code-review-agent-skills-and-mcp-now-generally-available/)
  and current documentation reinforce that skill support is host-specific. Copilot `allowed-tools`
  is preapproval, not a restriction boundary; safety claims remain host-specific.
- `[sourced]` A July-2026 GitHits snapshot of Meta's `secpriv-skill` uses positive, hard near-miss,
  held-out, stability, latency, and overfitting checks
  ([evaluation plan](https://github.com/facebookresearch/secpriv-skill/blob/0493f052bc0f6946cf70d865e65af7c686088b3f/experiment/eval_plan.md)).
  This is adoption evidence, not a universal standard.

### Current official contracts, publication date unavailable

Context7 was queried on 2026-08-19. Results from `/openai/codex`, `/openai/skills`, and
`/websites/code_claude` agree that descriptions control discovery, detailed workflows belong behind
activation, supporting files should load on demand through relative links, and permission enforcement
is separate from prose. Context7 did not expose reliable publication dates, so these results establish
current contracts without claiming a 90-day date.

### Older foundations retained where useful

The current Agent Skills
[best-practices](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/docs/skill-creation/best-practices.mdx),
[evaluation](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/docs/skill-creation/evaluating-skills.mdx), and
[description-optimization](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/docs/skill-creation/optimizing-descriptions.mdx)
guides predate the preferred window but remain compatible: use realistic prompts, fresh contexts,
objective assertions where possible, near-miss negatives, held-out validation, and old/new comparison.

## Four passes per batch

1. **Contract and baseline.** Freeze 3–5 related skills; inventory trigger, owner, authority,
   dependents, bundles, byte/token mass, volatile claims, and existing scenarios. Add realistic
   positive and adjacent-negative scenarios before changing discovery text.
2. **Accuracy and provenance.** Separate local behavior, current official documentation, and upstream
   implementation/adoption evidence. Correct contradictions; remove remembered syntax owned by a
   different skill; date or label unresolved volatile claims.
3. **Routing and context economy.** Keep the always-needed decision core and output contract inline.
   Move genuine sub-modes to one-level conditional references. Descriptions state capability,
   activation, and a meaningful boundary—not workflow choreography or synonym piles.
4. **Adversarial verification.** Check missing approval, injected text, credentials, wrong target or
   host, partial evidence, unsafe rollback assumptions, output slots, links, projections, and relevant
   tests. Compare old/new routing and behavior when model-call authority exists.

A fresh independent reviewer then examines the immutable candidate commit for correctness, security
and authority, prompt efficiency, and plan conformance. A repaired commit requires a fresh verdict.

## Batch map

| Batch | Skills | Shared boundary |
|---|---|---|
| 1 | `incident-command`, `root-cause`, `postmortem`, `operational-learning` | active response → diagnosis → retrospective → durable learning |
| 2 | `merge-gate`, `release-gate`, `production-change-gate`, `ci-actions`, `pcf-deploy` | readiness, authorization, promotion, and deployment |
| 3 | `backend-craft`, `frontend-craft`, `language-idiom`, `database-reliability` | implementation and data-layer correctness |
| 4 | `agent-authoring`, `agent-security`, `ops-tooling`, `eng-ladder` | fleet authoring, authority, orchestration, and engineering altitude |
| 5 | `stack-profile`, `pcf-ops`, `gcp-ops`, `akamai-edge` | runtime ownership and platform boundaries |
| 6 | `obs-logs`, `obs-metrics`, `obs-traces`, `obs-pipeline` | signal acquisition, query, correlation, and transport |
| 7 | `obs-alerting`, `obs-dashboards`, `service-onboarding`, `runbook` | operational outputs and service documentation |

This partition covers all 29 skills once. It follows explicit cross-references and shared agent
bindings. The self-referential authoring batch is not used to rewrite the rubric mid-campaign.

## Verification authority and instrument boundary

The user's first approval in this session authenticated Context7; it did not authorize model calls.
The user later explicitly authorized five `gpt-5.6-sol` test/review runs for the next two batches and
the full review.

`[verified]` The maintained clean-room routing instrument is pinned to `gpt-5.6-terra` and two trials
per scenario in `evals/codex_harness.py`. The repository does not currently contain a maintained,
approved five-trial Sol routing configuration; historical Sol artifacts are not current routing
evidence. Silently changing model and trial count would change the instrument rather than run it.

The authorized five Sol runs will therefore be fresh independent behavioral/adversarial and
correctness/security passes against an immutable final candidate. They are model-based verification,
not before/after routing-rate measurements. Live description rate comparisons remain deferred until a
reviewed Sol/5 routing instrument exists, or the maintained Terra/2 instrument is explicitly selected.
No static or qualitative judgment is presented as a routing rate.

Deterministic validation, generation, tests, Git commits, and independent local review remain in
scope. No push, PR, release, or production effect is authorized.

## Batch evidence

### Batch 1 — incident learning loop

`[verified]` Baseline body/reference bytes from `origin/main`:

| Skill | Body bytes | Reference bytes |
|---|---:|---:|
| `incident-command` | 10,542 | 0 |
| `root-cause` | 5,422 | 0 |
| `postmortem` | 4,849 | 0 |
| `operational-learning` | 9,434 | 7,564 |

The edit keeps incident authority and security carve-outs inline, removes duplicated Cloud Foundry
mutation syntax from incident command, makes the severity/cadence table an explicit local fallback,
and routes conditional communications/mitigation detail. Root-cause loses the startup announcement
and generic maxims while retaining untrusted-input handling and an observable diagnostic contract.
Postmortem and operational-learning retain their evidence, disposition, and human-review invariants
while moving only conditional examples or machine-readable contract detail behind direct links.

Candidate body/reference bytes after the four author passes:

| Skill | Body bytes | Reference bytes | Body change |
|---|---:|---:|---:|
| `incident-command` | 5,972 | 5,970 | -43.3% |
| `root-cause` | 4,099 | 1,549 | -24.4% |
| `postmortem` | 4,083 | 0 | -15.8% |
| `operational-learning` | 5,562 | 11,365 | -41.0% |

`[verified]` Activated-body mass fell from 30,247 to 19,716 bytes (34.8%). Installed bundle mass did
not drive the decision: conditional references grew so exact examples and invariants remain available
without loading them on every activation.

Deterministic evidence before candidate commit:

- `python scripts/check_links.py` — PASS.
- `python evals/run_evals.py --validate` — 69 scenarios parsed: 19 direct, 50 discovery,
  30 regression. Two incident-command discovery scenarios are new.
- `python scripts/test_operational_learning.py` — 47/47 passed outside the managed temp ACL
  restriction.
- `python scripts/test_packet_drift.py` — 24/24 passed outside the managed temp ACL restriction.
- `python scripts/generate_platform_adapters.py --write` — 286 generated files; parity PASS.
- `claude plugin validate . --strict` — PASS.
- `python scripts/gate_a.py` in the linked worktree — 39/40 steps passed. The sole failure is the
  repository's intentional full-`.git` snapshot check; final Gate A must run from a normal clone of
  the exact candidate commit.
- Live old/new routing — deferred under the authority statement above; no model process was started.

The initial candidate was committed as `6975ced4138d8e717ebfd2fff18c9d34dcfd4ce1`.
Independent exact-SHA Sol reviews then found authority-grader bypasses that keyword-only checks had
missed. Repairs were committed separately as `c60b4cf01adb5e0d2cfc34c93f7e18d032f564dc`,
`c03852555ac2a9b2b97868eb2d342237b2ea1cee`,
`f1e0d45bdc959f0db7d6da57efd12281ac4afefb`, and
`c278a2d61d8d4394b38a81e273d9ea89b33d6143`, `22b0cca2260a29f1b8febf6c5068377a50d0109c`,
`bd7899b4984092d618d9a6d5ed6364e0ac6bc3e6`, and
`2cb7b16b5dd27f64c028dd69cb54075f3252e543`. Those repairs proved that free-form actor/action grammar
kept exchanging one bypass for another false positive. Commit
`81338871e12a1778a8b6be464d66f5ded99178cb` removes that grammar from the active-incident scenario:
the response is one closed JSON decision record with fixed recommendation-only, human-executor,
not-approved, and not-started enums. Extra fields, prose, duplicate keys, or different authority
states fail closed.

The final Batch 1 authority-schema repair is
`65aa407540f4a51c1c5e72f605a5416edab5d143`. `[verified]` A clean normal checkout at that exact
commit passed Gate A 40/40. A fresh independent `gpt-5.6-sol` review bound to the immutable commit and
tree returned `APPROVE` with no P0, P1, or P2 finding. Batch 1 is accepted for this campaign.

### Batch 2 — readiness, authorization, and deployment

`[verified]` Baseline body/reference bytes from `origin/main`:

| Skill | Body bytes | Reference bytes |
|---|---:|---:|
| `merge-gate` | 5,262 | 0 |
| `release-gate` | 3,684 | 0 |
| `production-change-gate` | 6,694 | 0 |
| `ci-actions` | 9,248 | 1,620 |
| `pcf-deploy` | 9,042 | 0 |

The four passes removed invented review-size/speed thresholds, separated merge/readiness/production
authority, made approvals effect-bound, and corrected volatile GitHub Actions and Cloud Foundry
claims. Conditional mechanics moved behind direct links; the entrypoints retain the decision core,
failure states, authority boundary, and output contract.

Candidate body/reference bytes after the author passes:

| Skill | Body bytes | Reference bytes | Body change |
|---|---:|---:|---:|
| `merge-gate` | 4,415 | 0 | -16.1% |
| `release-gate` | 3,971 | 0 | +7.8% |
| `production-change-gate` | 5,949 | 4,346 | -11.1% |
| `ci-actions` | 6,326 | 10,966 | -31.6% |
| `pcf-deploy` | 5,375 | 9,076 | -40.6% |

`[verified]` Activated-body mass fell from 33,930 to 26,036 bytes (23.3%). The installed bundle grew
because current sourced contracts, examples, and version-sensitive boundaries moved to conditional
references; raw bundle minimization was not allowed to erase accuracy.

Context7 and GitHits provenance remained separate:

- `[sourced]` Current GitHub documentation establishes that classic protection and rulesets can both
  apply; a classic-endpoint 404 is inconclusive; one listed environment reviewer is sufficient;
  self-review and administrator bypass are separate settings; full action SHAs are immutable;
  `pull_request_target` becomes dangerous when privileged workflow code executes PR-head content;
  `id-token: write` is only token-request authority; and attestations prove provenance, not safety.
- `[sourced]` GitHits implementation evidence at
  `actions/runner@258d6c857db3519913f7deb6004b60172f8043ae` confirms that ephemeral registration
  accepts one job and unregisters; it does not wipe the host.
- `[sourced]` Cloud Foundry CLI claims were pinned to `cloudfoundry/cli@v8.18.4` commit
  `3fcd823a19e8254f99337765d98fd6e13149a77c`. Canonical developer docs and source establish mixed
  traffic during blue-green route overlap, conditional manifest-name override, version-sensitive
  canary behavior, limited revision rollback, independent revision/droplet retention, and distinct
  restart/restage/scale behavior.
- `[sourced]` Context7 library `/cloudfoundry/docs-dev-guide`, queried on 2026-08-19 for blue-green
  route mapping, traffic overlap, and unmap behavior, returned
  `_autodocs/deployment-operations-reference.md` with an atomic-cutover claim. GitHits canonical source
  `cloudfoundry/docs-dev-guide@04fbae722396625104af6c856d6825130def554e`,
  `deploy-apps/blue-green.html.md.erb`, says Blue and Green both receive traffic until Blue is
  explicitly unmapped. The skill follows the canonical source and records the disagreement.

The first exact review of `e4401df5d8bed71ebc9ec618937434a99ad325ba` found two live-activation
defects: a fixed `checkout-green` name could retain the production route across deployments, and a
runner label was described as a scoped runner group. It also found keyword-rich grader bypasses,
missing production-change discovery near-misses, and incomplete retention provenance. Commit
`81338871e12a1778a8b6be464d66f5ded99178cb` uses a unique release-bound candidate after app/route
reconciliation, uses the real `runs-on.group` form, adds a stale-Green regression, adds one positive
and two adjacent-negative production-change discovery cases, replaces keyword bags with exact or
relationship-aware graders, and pins both revision-row and droplet-pruning implementation paths.

The next review found that free-form safety graders still accepted contradictory prose, rejected
valid negated refusals, and encoded an impossible automatic alternative for the explicit-only
`pcf-deploy` skill. Commit `7ce30e1398689fef7448e7190895696aad877e37` replaced those graders with
one closed, strictly typed JSON-object contract: duplicate keys, non-finite values, extra fields,
wrong JSON types, and trailing prose fail closed. A clean normal checkout at that exact commit passed
Gate A 40/40. The follow-up exact-SHA review verified the strict parser but found that five discovery
prompts disclosed their expected enum values, turning those cases into answer-copying tests. The
current candidate removes that leakage from discovery and direct scenarios and adds adversarial
fixtures for nested types, extra fields, duplicate keys, `NaN`, `Infinity`, and invalid evaluator
configuration. Three later exact-SHA Sol reviews verified these named Batch 2 repairs as closed and
reported no remaining Batch 2 P0, P1, or P2 finding; final cross-batch acceptance still depends on
the closing reviews recorded below.

### Batch 3 — implementation and data-layer correctness

`[verified]` Baseline body/reference bytes from `origin/main`:

| Skill | Body bytes | Reference bytes |
|---|---:|---:|
| `backend-craft` | 11,080 | 17,198 |
| `frontend-craft` | 14,201 | 35,502 |
| `language-idiom` | 2,605 | 23,176 |
| `database-reliability` | 8,528 | 2,081 |

The contract pass preserved each lane's trigger, near-miss boundary, stack-profile dependency,
authority boundary, and output contract. The accuracy pass removed framework defaults and corrected
API, browser, language, accessibility, migration, and database claims. The context-economy pass
deduplicated entrypoints and kept framework or language detail behind directly linked references.
The adversarial pass added positive and adjacent-negative routing cases plus closed typed behavior
records for unsafe retries, production DDL, `EXPLAIN ANALYZE`, PowerShell trust, and Go-version
semantics.

Candidate body/reference bytes after the four author passes:

| Skill | Body bytes | Reference bytes | Body change |
|---|---:|---:|---:|
| `backend-craft` | 8,200 | 12,673 | -26.0% |
| `frontend-craft` | 7,026 | 32,185 | -50.5% |
| `language-idiom` | 2,433 | 14,721 | -6.6% |
| `database-reliability` | 5,833 | 6,177 | -31.6% |

`[verified]` Activated-body mass fell from 36,414 to 23,492 bytes (35.5%). The
`language-idiom` entrypoint still makes its five-language routing and boundary explicit while its
conditional references lost 8,587 bytes of generic ceremony and volatile tool mandates.

Context7 established the documented contracts; GitHits separately checked current source,
implementation, version, or adoption evidence:

- `[sourced]` FastAPI response models are output boundaries; Pydantic `from_attributes=True` is not a
  substitute. HTTPX `ASGITransport` does not run ASGI lifespan events. Evidence was queried through
  Context7 `/websites/fastapi_tiangolo`, `/pydantic/pydantic`, and `/encode/httpx`, then checked
  against FastAPI `0.140.13` commit `628663f4…`, Pydantic `2.13.4` commit `cf67d4b3…`, and HTTPX
  `0.28.1` documentation commit `b5addb64…`.
- `[sourced]` Browser `EventSource` construction has no arbitrary request-header option, so native
  SSE cannot be described as accepting a bearer `Authorization` header. WCAG 2.2 AA target-size
  minimum is 24×24 CSS pixels with exceptions; 44×44 is a stricter project preference, not the AA
  minimum. Context7 sources were `/mdn/content` and `/websites/w3_tr_wcag22`; GitHits checked WCAG
  commit `58080bdb…`.
- `[sourced]` RFC 9457 problem-details members are optional, `Sunset` does not require HTTP 410, and
  legacy `X-RateLimit-*` names are not a universal HTTP standard. The rewrite keeps project-specific
  contracts explicit rather than presenting them as protocol requirements. Sources were Context7
  `/websites/rfc-editor_rfc` and GitHits snapshots `ef2a6da1…`, `9addc0a2…`, and `9b4bc45c…`.
- `[sourced]` `pytest --cov` comes from `pytest-cov`; Bash strict mode is not safe as an unconditional
  library/sourced-script default; Go loop, timer, vendor, and toolchain behavior depends on the
  repository's target version; PowerShell signing and `AllSigned` are not sandboxes, while WDAC or
  AppLocker policy governs Constrained Language Mode. Context7 sources were the current pytest,
  pytest-cov, GNU Bash, Go, and Microsoft PowerShell documentation; GitHits checked pytest `9.1.1`,
  pytest-cov `7.1.0`, and current Go source.
- `[sourced]` Database rollback is a recovery decision, not a requirement to ship a destructive down
  script. PostgreSQL concurrent-index and `NOT NULL` techniques have transaction and lock caveats,
  and `EXPLAIN ANALYZE` executes the statement. Context7 sources included
  `/websites/postgresql_current`, `/microsoftdocs/sql-docs`, and
  `/websites/oracle_en_database_oracle_oracle-database_19`; PostgreSQL source was checked at
  `cb217c4f…`.

The author observed a local red run before the Batch 3 scenario files existed, but no committed or
runnable failing snapshot was retained, so it is `[unverified]` as independent red-first evidence.
The exact pre-change inventory implies ten failing cases, not the nine initially recorded. The first
exact candidate, `3e284d8913828419b1428a5452f0172318411eee`, passed Gate A 40/40
in a normal full-history checkout and strict plugin validation. A full `evals/graders.py` mutation
sweep then exposed four under-tested branches in the new strict-JSON path and one missing invalid
configuration case. Repairs `ea9510d65c5b266d4bfcc126d0ec9173236b6ca9` and
`e439e2ad71ca560239e7f59cee7e3e42d8bf7ea7` add missing/extra/equal-length-wrong nested arrays,
top-level arrays, non-finite values, and non-object expected-value fixtures, and remove a redundant
strict-zip branch. `[verified]` At exact `e439e2ad…`, 530/530 grader checks pass and the full mutation
sweep leaves no surviving mutant in `json_exact_object`; 62 survivors remain elsewhere in the
pre-existing grader module and are recorded as residual test debt, not a clean mutation score.
At exact candidate `af0b15f3cc414d2f165befa6ad843cc0a1e489d9`, three fresh independent
`gpt-5.6-sol` reviews found no P0 issue and three remaining defects: a P2 database-licensing claim
without reconstructible official source links, a P1 exact-object evaluator that treated
unannounced open-ended scalar vocabulary as closed, and a P1 README claim that the historical
Terra routing revision remained equivalent to HEAD despite changed skill descriptions. The same
reviews independently verified the named Batch 2 deployment, authority, and grader repairs and the
other named Batch 3 accuracy repairs as closed.

Repair commit `f75ab2e9f79f1ef6d0ca226c516072da8217b11c`:

- links the exact PostgreSQL, SQL Server, and Oracle official sources needed to reconstruct the
  query-plan and Oracle diagnostics-licensing boundary;
- makes each craft scenario's complete two-choice scalar vocabulary explicit, alternates the
  expected choice's position, accepts the contract-accurate
  `principal_operation_request_fingerprint` value, and adds checks that reject every wrong choice;
- marks the pinned Terra campaign historical and not routing-equivalent to the changed fleet.

`[verified]` The new checks were run against the unrepaired candidate before the content repairs:
the craft-closure checks reported 29 failures, and the fleet contract reported two failures for the
missing exact source links and stale routing-equivalence claim. At exact repaired commit
`f75ab2e9…`, strict plugin validation passes, Gate A passes 40/40 in a clean normal checkout,
651/651 grader checks pass, and all 87 scenarios validate (23 direct, 64 discovery, 42 regression).
The unbounded `evals/graders.py` mutation sweep generated 224 mutants and left 55 legacy survivors;
it therefore exits nonzero and is not represented as a clean mutation score. No mutant survives in
`json_incident_command_packet` or `json_exact_object`.

Two independent exact-SHA closing reviews of this repaired, evidence-bound candidate remain the
acceptance condition. No live routing/model campaign, production effect, release, push, or external
system mutation is part of this evidence.
