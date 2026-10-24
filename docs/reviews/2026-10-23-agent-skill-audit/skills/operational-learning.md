# Operational learning skill audit

[verified] Target: `skills/operational-learning/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. Specification: partial; engineering quality: partial. No material source-contract finding confirmed. Static coverage supports the bounded documentation method; live host/model behavior and human approval remain unverified.

## Contract and findings

[verified] The entrypoint separates ownership reads from closeout, forbids active-incident preparation, gates `prepared` on an actual authorized diff and caller-supplied checkout binding/status, and excludes pre-existing dirty paths. Policy fallback roots, outside-root rejection, source/API provisioning ownership, dispositions, retirement propagation, unresolved owners and follow-up persistence agree with the entrypoint. Review stamps require separately supplied review or exact-version execution evidence; a failing drill cannot verify its repair.

[verified] The templates' `sourced | unverified` card metadata/provenance examples do not override the explicit requirement to retain incoming verified observations. A document sourced to an observation does not itself become operationally verified. This provisional concern is not a finding. Scribe's tool/body constraints and mode selection preserve the same boundary; service-lifecycle supplies the checkout binding and receipts, and incident-investigation orders postmortem then knowledge closeout after resolution.

## Requirement and evidence coverage

| Risk | Evidence | Result |
|---|---|---|
| Unapproved or unbound KB preparation | Entrypoint, policy and scribe body; existing closeout fixtures | [verified] Explicit boundary; no live execution assurance |
| Duplicate configuration or evidence upgrade | All templates and policy; root's independent artifact/oracle review | [sourced] Bounded exact owner/contact, locator/version and claim-bound label checks |
| Lost retirement or follow-up state | Policy event map/state transitions; lifecycle caller | [verified] Records retained, indexes updated, owner named; live removal outside scope |
| Routing or host permission behavior | Three discovery fixtures and two build fixtures reviewed by coordinator | [sourced] Fixture intent only; no new live model run |

[sourced] Coordinator read full `evals/oracles/researcher-scribe/probe_documents.py` (159 lines), including closeout 87–108 and alert closeout 109–149; bounded calibration `evals/test_researcher_scribe_cases.py` 304–435; full discovery owner-lookup/defers-retrospective/defers-fleet-failure fixtures and build-scribe-knowledge-closeout/build-scribe-alert-definition-closeout fixtures; bounded `scripts/test_validate_fleet.py` 409–561 and `scripts/test_skill_assets.py` 35–62. Oracle checks cover unchanged lifecycle/review/source revision, exact owner/contact, taint labels, source vs API identity, absent version and index ownership. Negative mutations include detached labels, wrong owner, prefix decoys and stale recovery/export revision. These are artifact checks, not proof of every prose, approval or target behavior.

## Read and verification manifest

[verified] Full canonical reads: `SKILL.md`, `references/disposition-policy.md`, `assets/service-card-template.md`, `assets/alert-card-template.md`, `assets/knowledge-index-template.md` (five files, 384 lines). Full supporting reads: `agents/scribe.md`, `skills/service-lifecycle/SKILL.md`. Bounded supporting reads: incident-investigation closeout/caller search; generated skill references and entrypoint comparison; trusted AGENTS/CONTRIBUTING guidance. Coordinator evidence above is attributed, not represented as this reviewer's full reads.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_bundle_check.py` exited 0: all relative bundle links resolve; all four supporting files equal `.github/skills/operational-learning/` copies byte for byte; canonical source diff against the target revision is empty. The coordinator independently compared the entrypoint too: it is byte-identical, so all five workspace files match. The coordinator's unchanged-source passing suite is reused; no new tests or live evals ran.

[verified] Only this report changed for this item. No canonical source, tests, configuration, production state, installation, commit, push or repair was performed. Remaining assurance: live loading, model adherence, target-specific evidence and human acceptance. No acceptance or promotion is implied.
