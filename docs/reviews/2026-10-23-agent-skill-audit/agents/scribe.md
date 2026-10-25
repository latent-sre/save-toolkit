# Scribe audit

[verified] Target: `agents/scribe.md` at `8b4f9b785e520944319e04fd8e5018d4545b6800`, inspected on 2026-10-23. The complete agent (93 lines / 6,167 bytes) and both projections were read. Generated copies match; audited source paths remain unchanged.

## Conclusion and findings

[sourced] **No material defect validated.** Scribe's documentation-only authority, three primary modes, evidence rules and caller return are consistent with the linked methods. No severity-ranked finding is warranted.

[sourced] **Specification: partial; engineering: partial.** Source and mechanical coverage align. General document usefulness, arbitrary evidence reconciliation, runtime tool denial and end-to-end closeout behavior remain unverified for this revision. A prepared document is not approved operational guidance.

## Contract coverage

| Contract | Evidence and assessment |
|---|---|
| Routing and authority | [sourced] [Agent](../../../../agents/scribe.md), lines 3–23, owns runbooks, resolved-incident retrospectives and approved KB work. It returns active incidents to the responder and leaves code, alert definitions, live queries, execution and delegation outside its role. Write/Edit are explicitly workspace-wide, so document-only paths remain a cooperative constraint. Canonical tools and Copilot read/search/edit match that posture. |
| Mode selection and failure | [sourced] Lines 25–42 select one primary artifact/method, stop when the required skill is unavailable and keep postmortems separate from knowledge dispositions. [Runbook](https://github.com/latent-sre/save-toolkit/blob/8b4f9b785e520944319e04fd8e5018d4545b6800/skills/runbook/SKILL.md) supports small contact corrections without unnecessary restructuring; [postmortem](https://github.com/latent-sre/save-toolkit/blob/8b4f9b785e520944319e04fd8e5018d4545b6800/skills/postmortem/SKILL.md) distinguishes unknown cause from unresolved incident and preserves unknown metadata. Neither missing evidence nor a requested document authorizes live verification. |
| Checkout and provisioning identity | [sourced] Lines 39–42 and [operational learning](https://github.com/latent-sre/save-toolkit/blob/8b4f9b785e520944319e04fd8e5018d4545b6800/skills/operational-learning/SKILL.md), lines 35–49, require an actual diff and caller-supplied verified checkout binding for `prepared`, with status/dirty-path limits and no guessed identity from `.git`. [Disposition policy](https://github.com/latent-sre/save-toolkit/blob/8b4f9b785e520944319e04fd8e5018d4545b6800/skills/operational-learning/references/disposition-policy.md), evidence rule 1, separately binds source-managed definitions to their source revision and API-owned alerts to target/UID/readback evidence. An export cannot replace the owning configuration or supply an unknown API version. |
| Evidence and publication | [sourced] Agent lines 46–60 preserve labels, taint, target and time. Exact command syntax, historical execution and current health remain separate claims; the lane never runs a command to fill a gap. Runbook procedure changes invalidate current-version rehearsal stamps while retaining history. New artifacts remain draft/unreviewed, and human PR review is required before use. |
| Handoffs and output | [sourced] Lines 64–93 return one next owner to the invoking caller, the exact runbook/alert link, changed paths, code state, gaps and explicit non-actions. Missing closeout binding returns proposed/blocked work with an owned tracker follow-up. The Copilot automation button is a human-selected transition requiring explicit approval and target binding; it adds no Agent grant. Observability remains the owner of any actual alert-definition edit. |
| Focused coverage | [sourced] [Validator tests](../../../../scripts/test_validate_fleet.py), lines 389–394 and 496–521, pin non-execution and binding language. [Document tests](../../../../evals/test_researcher_scribe_cases.py), lines 24–54 and 168 onward, reject invented execution labels and preserve command/source distinctions. Lines 304–431 exercise failed/missing/crashed oracles, narrow contact corrections, taint/version promotion, and wrong provisioning ownership. These are calibrated fixture assertions, not proof of general writing quality. |

## Behavioral evidence and limits

[sourced] The runbook fixture checks a real documentation path alongside application/alert files, draft metadata, target confirmation, UNKNOWN readback/retry ownership, per-step outcomes and recovery. Postmortem fixtures separate impact end from human confirmation, preserve unknown cause/data integrity and retain existing follow-up IDs. The contact and alert-definition closeouts require a completed `scribe` child under a builder caller that obtains the checkout binding; they therefore specify real delegation rather than only a pasted return.

[sourced] The supplied-state contradictory-record case preserves both acceptance and denial records without inventing execution or approval. [WP-10](../../2026-10-10-wp10-first-step.md), line 51, records 3/3 for that case on its historical candidate/host. It does not certify the broader document flows or this revision.

[unverified] Artifact checks are bounded: a populated slot, matching label or expected field does not prove a safe procedure, correct causal explanation, staffed escalation path or truthful caller binding. The full linked templates/oracles receive their own bundle audits later. Actual helper timing, host enforcement and complete prose consistency need trace/manual review. The current contract does not claim otherwise, and no harmful repetition or impossible tool step was found. No external question arose.

[verified] No source changes, tests, network, installs, live queries or operational execution occurred. Source/projection comparisons completed. Existing broad-suite evidence is reused with the identity limits in [the first report](agent-engineer.md).

## Inspection manifest

[verified] Complete primary/method reads: `agents/scribe.md`; `.github/agents/scribe.agent.md`; `com.github.copilot/agents/scribe.agent.md`; `skills/runbook/SKILL.md`; `skills/postmortem/SKILL.md`; `skills/operational-learning/SKILL.md`; `skills/operational-learning/references/disposition-policy.md`.

[verified] Scenario content: `evals/build-scenarios/build-scribe-writes-only-docs.yaml`; `evals/build-scenarios/build-scribe-knowledge-closeout.yaml`; `evals/build-scenarios/build-scribe-alert-definition-closeout.yaml`; excerpts of `evals/build-scenarios/build-scribe-postmortem-evidence.yaml` and `evals/build-scenarios/build-scribe-postmortem-unknown-metadata.yaml`; `evals/scenarios/agent-direct-scribe-command-evidence.yaml`; `evals/scenarios/agent-direct-scribe-contradictory-record.yaml`.

[verified] Supporting sections/searches: `evals/test_researcher_scribe_cases.py`; `scripts/test_validate_fleet.py`; `scripts/test_skill_assets.py`; `docs/reviews/2026-10-10-wp10-first-step.md`.

[sourced] Reused guidance: `AGENTS.md`, `CONTRIBUTING.md`, `.github/copilot-instructions.md`, validator/adapter source and tests, projection/frontmatter references, production-change gate, observability's approved-alert handoff and installed review-method instructions. The full runbook, postmortem and learning bundles remain separate audit items.
