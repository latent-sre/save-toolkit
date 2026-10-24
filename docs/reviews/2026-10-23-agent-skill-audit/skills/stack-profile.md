# Stack profile skill audit

[verified] Target: `skills/stack-profile/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. No material source-contract finding confirmed. Specification and engineering-quality verdicts: partial. Internal consistency is assessed; repository assertions about the team's live estate and licensed picker are not independently observed team facts.

## Contract assessment

[verified] The entrypoint makes owner-recorded decisions authoritative and preserves candidate runtime/GCP boundary status as unresolved. Existing PCF/on-prem operations, approved migration direction and possible landing runtime are distinguished. It forbids treating a candidate as selected or proposing self-managed Kubernetes. Support-only Java/JVM is separated from authoring languages; local Java build/test/run is excluded while operational diagnosis remains supported.

[verified] Toolchain rows are defaults for unset new-code decisions; repository tooling takes precedence. CI authentication is settled as environment secrets for this team, while host/runtime minor versions still require confirmation. Data-store inventory separates operated engines, embedded SQLite and potential future cloud choices. The known SQLite ephemeral multi-instance limitation is not presented as an approved service architecture.

[verified] Observability is additive: incumbent and new backends coexist until service-specific instrumentation supports the latter. Recovery exports do not establish provisioning ownership, fresh backup or tested restore. Missing DX entitlement and DataStream destination remain named gaps. The Grafana version/target assertion is repository-supplied inventory, not proof of current reachability or live configuration.

[verified] Copilot ordering has an explicit selection rule and an explicitly unconfirmed team-license list; it cannot select Claude aliases or establish host availability. Terms preserve human/ITO roles, the existing TLC, approval boundaries and unresolved rota/severity ownership. Documentation remains repository-owned with one-way Confluence import. Conditional references match caller needs without transferring authority.

| Risk | Evidence | Result |
|---|---|---|
| Candidate technology promoted to fact | Entrypoint and owner-update rule | [verified] Decision-pending status and platform boundaries explicit |
| Support estate mistaken for authoring authority | Application/data reference and software-engineer caller | [verified] Java operation vs implementation separated |
| Backend coexistence interpreted as retirement | Observability reference and entrypoint | [verified] Additive inventory and instrumentation condition |
| Model inventory inferred from prose | Copilot reference | [verified] Team-license evidence explicitly absent |
| Actual team versions, entitlement, access and ownership | Repository assertions only | [unverified] Require target/owner records; public product facts do not establish them |

## Read manifest and checks

[verified] Full canonical reads: `SKILL.md`; `references/application-and-data-stack.md`, `copilot-models.md`, `observability-stack.md`, `terms-and-roles.md` (five files, 214 lines). Bounded supporting coverage: software-engineer, SRE, principal, reliability and observability caller searches; support-only/platform-selection scenario inventory; adapter/test inventory. Previously inspected callers retain their separate manifests. Root owns independent scenario/oracle and public-source review.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_current_check.py stack-profile` exited 0: all four reference projections and entrypoint are byte-identical, relative local links resolve, canonical diff against target is empty. Existing unchanged-source test baseline is reused. No new test, licensed-picker inspection, target read or model call occurred in this pass.

[verified] Only this report changed for this item. No canonical/test/configuration edit, install, live operation, commit, push, repair or acceptance occurred.

[verified] Root fully read the support-only Java build case and platform-selection build case. They separate allowed recommendations from Java source/build effects and require a proposed owner decision consistent with a supplied accepted ADR; vendor claims remain unverified. These are bounded fixture/trace contracts, not evidence about actual team infrastructure. Prior agent audits cover the shared graders' limits.

[sourced] [Red Hat package evidence](https://access.redhat.com/errata/RHSA-2023:0340) supports Bash 5.1 as the RHEL 9 baseline, not an exact installed patch. [CredHub authentication](https://docs.cloudfoundry.org/api/credhub/version/main/#_authentication) supports trusted-UAA Bearer tokens and mutual TLS; direct GitHub OIDC acceptance is not established. Earlier sourced TS6/TS7 tooling and DX OpenExplore facts are reused. Grafana's reviewed-target record and the unconfirmed licensed picker remain repository assertions, not live inventory. No new material contradiction was validated.
