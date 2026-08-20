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
| `incident-command` | 5,935 | 5,970 | -43.7% |
| `root-cause` | 4,099 | 1,549 | -24.4% |
| `postmortem` | 4,083 | 0 | -15.8% |
| `operational-learning` | 5,562 | 11,365 | -41.0% |

`[verified]` Activated-body mass fell from 30,247 to 19,679 bytes (34.9%). Installed bundle mass did
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
`c278a2d61d8d4394b38a81e273d9ea89b33d6143`, followed by the closed-grammar repair
`22b0cca2260a29f1b8febf6c5068377a50d0109c`. Red-first fixtures now cover every canonical
mitigation row, non-human automation, plan/intention laundering, pre-approval and negative-state
human execution, object/joint-actor laundering, and ordinary labeled recommendations.

`[verified]` At exact commit `22b0cca2260a29f1b8febf6c5068377a50d0109c`, a clean normal
checkout passed Gate A 40/40 and `evals/test_graders.py` passed 408/408. A fresh exact-SHA review of
that last repair is still pending; Batch 1 is not called accepted until it returns no P0/P1.

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
| `merge-gate` | 4,038 | 0 | -23.3% |
| `release-gate` | 3,971 | 0 | +7.8% |
| `production-change-gate` | 5,353 | 4,145 | -20.0% |
| `ci-actions` | 6,326 | 9,366 | -31.6% |
| `pcf-deploy` | 5,375 | 7,407 | -40.6% |

`[verified]` Activated-body mass fell from 33,930 to 25,063 bytes (26.1%). The installed bundle grew
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
- `[sourced]` A Context7-generated Cloud Foundry summary called route mapping an atomic cutover, while
  the canonical source says Blue and Green both receive traffic until Blue is explicitly unmapped.
  The skill follows the canonical source and records the disagreement rather than averaging it away.

`[verified]` Candidate checks pass: `check_links.py`, `test_validate_fleet.py` (35 tests), the
72-scenario schema suite (20 direct, 52 discovery, 32 regression), all 410 grader checks, evaluator
bootstrap integrity, and `git diff --check`. The generator wrote 300 adapter files and parity passed;
strict Claude plugin validation also passed. Exact-candidate Gate A and independent Sol review remain
required before Batch 2 is accepted.
