# SRE-CF-001: Adama gcx acceptance

[verified] The attended Adama controller path reads the configured Grafana organization with
the existing encrypted Ansible credential. This record does not establish protected SRE agent
execution, Windows/macOS installed-client acceptance or browser access. The live
backlog remains [SRE-CF-001](../fleet-roadmap.md#sre-cf-001--complete-protected-sre-investigation-access).

## Candidate and scope

[verified] Toolkit base: `13301b621f06496b4e8dbeed61d5848587ae0a73`, task branch
`docs/backlog-triage-20261113`. Operations-repository base:
`27ed21a89aba374a79a76739ad59a23ca7f99446`, task branch
`work/gcx-ansible-credentials-20261113`. The local operations-repository candidate is
`e2811183569a60d466d5c6d2d3a78a089b87ae05`, preceded by the test-only ARC fixture correction
`333362fa`. The toolkit candidate is the commit containing this record. Neither candidate
is a merged or natively accepted release.

[verified] Operations-repository working Git blobs:

- `maintenance-gcx-read.yml`: `0954adb8b07efc76614118203a1e25766fcfe136`.
- `tools/test_gcx_access.py`: `2d0c5631dc7292e093f531e75244ed48575881f7`.
- `roles/zfs-arc/tests/test_zfs_arc_contract.py`: `84a0da6b77d2d782dcea3a67fe6fdbe00169c368`.

[verified] Native tools observed on Adama: gcx 1.7.1, Claude Code 2.1.325 and PowerShell 7.7.0.
Tool presence is not proof of native agent invocation or hook payload behavior.

## Exercised reads

| Operation | Evidence | Limit |
|---|---|---|
| Connection and organization | [verified] Encrypted import, non-admin read-only permissions, organization 1 binding and authenticated CLI check passed | Import verification is not continuous issuer/account lifecycle monitoring |
| Dashboard inventory | [verified] Ten identifiers/titles returned, `changed=0` | Inventory capped at ten |
| Overview configuration | [verified] 13 non-row panels, 15 saved queries and one host variable; `changed=0`, no truncation | Stored configuration; no rendered image or transformations |
| Host reporting | [verified] At `2026-11-14T06:26:56.667Z`, 19 reporting, zero failed exporters and zero expected hosts missing telemetry; `changed=0`, no truncation | One instant evaluation; no service-health, inventory-completeness or scrape-cadence claim |
| Alert state | [verified] At the returned `2026-11-14T06:35:40Z` evaluation, one visible group contained 138 rules: two firing, 136 inactive, no paused rules or non-OK evaluation health; `changed=0` | Full-page counts, 100 rule details; truncation reported; notification delivery and other permissions/tenants not established |

[verified] Alert summaries prioritize unhealthy/firing/pending rules and exclude raw labels,
annotations, alert instances, errors and continuation tokens. `DiskFilling` and
`GrafanaAlertingHeartbeat` were firing. [sourced] The operations repository's
`configs/dradis/grafana/provisioning/alerting/fleet-rules.yaml` defines the heartbeat as
intentionally always firing; its receiver checks absence. DiskFilling warrants separate
operational triage. Neither rule was changed or silenced during this work.

## Checks

| Check | Result |
|---|---|
| Operations-repository focused gcx tests | [verified] 44 passed, including native gcx, real PromQL, masking, unsafe grants, empty/query-error handling and caps/pagination |
| Toolkit helper/guard/hook/platform tests | [verified] 386 passed, six skipped and 921 subtests passed; the new cases deny raw gcx and editable Ansible invocation under Bash, PowerShell and Copilot preview |
| Touched Ansible syntax, YAML, Ruff and ansible-lint | [verified] Passed; existing tooling deprecation/configuration notices remain |
| Toolkit default full suite | [verified] 4,569 passed, 85 skipped and 4,309 subtests passed in 56.95 seconds; coordinated receipt `.git/local-test-runs/20261114T063945Z-4f7018a0` |
| Native Linux hook launchers | [verified] Actual POSIX hook command and PowerShell 7.7 launcher allow a harmless Git read and deny direct gcx/editable Ansible reads from synthetic SRE payloads; this is not a client-generated hook event |
| Native Ansible time bound | [verified] A sleeping fake CLI with a synthetic credential was terminated by the fixed 45-second timeout (exit 124); the play failed closed in 46.79 seconds including Ansible overhead and printed no synthetic credential |
| Claude plugin validation | [verified] Marketplace strict validation and plugin validation pass under 2.1.325; root CLAUDE.md and listing-icon warnings remain |
| Redirect/destination qualification | [verified] **FAIL:** a synthetic-only loopback probe redirected from `127.0.0.1` to `localhost` on another port; gcx 1.7.1 followed it and sent the synthetic bearer token, exiting zero. No real credential was used. Latest upstream release checked remains v1.7.1 |
| Initial full operations-repository tests | [verified] 4,484 passed, 119 skipped, 15 subtests passed and one ZFS fixture failure in 1,194 seconds. The fixture compared two different live MemTotal readings; runtime/config reconciliation itself agreed |
| Corrected affected operations-repository tests | [verified] 1,546 passed, 119 skipped and 15 subtests passed across the selected 31 test files in 225.09 seconds, including gcx and the fixed-memory ARC fixture |
| Current formatting and Gitleaks | [verified] Repository-wide format/lint passes; Gitleaks checked 1,740 Git-visible source files successfully |
| Current repository and Trivy secret scans | [verified] Passed on 1,740 Git-visible files after the example-value correction; Trivy retains three reviewed baseline configuration findings |

[verified] The synthetic gcx fixture uses the scanner's documented `example-` form; no scan
policy or exclusion was added. The ARC fixture now supplies a known 16 GiB input to the role's
actual awk read and checks the independent literal expected ceiling, apply/check/disabled
behavior and replay. No production ARC role or live ZFS setting was changed.

[verified] The first `make verify` exited nonzero for the fixture scan and ARC test. The
changed-scope retry's tests passed, but its parallel format leg observed a removed unused
import before correction, so that wrapper also exited nonzero. The current format leg was
rerun independently and passed; passed test legs were retained instead of replayed wholesale.
Inventory/source counts, all 158 playbooks' syntax, generated Grafana assets, documentation
links and changed Ansible lint passed in the same verification sequence.

[verified] Toolkit skips include Windows-only argument transfer/launcher/job tests, opt-in
incidents UI calibration, and optional evaluator environments. The skipped native host tests
remain open acceptance work; the default suite is not the opt-in heavy/evaluation campaign.

[verified] The redirect probe executed `gcx api /api/health --method GET --output json`
with temporary loopback context metadata, telemetry disabled and a synthetic environment token.
The origin redirected to a second loopback server under a different hostname/port; that server
observed the synthetic Authorization bearer. This is the API transport used by `alerts`.
Other gcx transports were not independently qualified for redirects by this probe.

## Remaining acceptance gates

| Gate | Current evidence and action |
|---|---|
| Protected agent execution | [verified] The encrypted vault and vault password file are owner-only 0600, owned/readable by the current controller user; values were not read during this metadata check. The reader uses that identity, so no independent credential/tamper boundary is established. `sudo -n true` requires interactive authentication. Prepare a platform-protected execution identity and immutable operation entrypoint, then prove direct reads and helper tampering are denied before granting the SRE agent access |
| Redirect rejection | [verified] Native 1.7.1 does not satisfy fail-closed destination binding. Qualify an upstream correction or protected transport that refuses redirects before agent admission; no CLI flag workaround has been verified. A successful initial organization check cannot substitute for this |
| Windows/macOS clients | [unverified] No target/access path supplied. Adama has no VS Code CLI; Linux fixture/PowerShell results do not establish native Windows/macOS host behavior |
| Browser and returned images | [unverified] This session has no Playwright/browser connector for the intended client. Verify Viewer session reuse/expiry, viewing controls, denied mutations and actual image delivery there |
| Scratch analysis | [unverified] No isolated analysis execution grant was added. Preserve the no-production-credentials/no-network requirement before admitting it |
| Source integration and tracking | [verified] Candidate changes are preserved in local task-branch commits. Main-branch integration and Jira mirroring remain pending; these commits do not accept or promote the candidate |

[verified] The current guard and standard Copilot tool posture remain unchanged. The legacy
helper is retained until required CLI operation coverage and the matching protection/native
gates pass. Passing local tests does not accept or promote the candidate revision.

The owner removed CF work from this ticket on November 14. The ticket ID and its old anchor
are retained for tracking; no CF CLI installation, connection or qualification is required by
this acceptance record. Existing fleet CF command policy is unchanged.

## Upstream behavior checked

[sourced] The pinned [gcx alert command](https://github.com/grafana/gcx/blob/v1.7.1/internal/providers/alert/rules_commands.go)
flattens/truncates typed rule groups while dropping API status and continuation metadata.
The fixed API GET preserves those fields for explicit validation and truncation reporting.
[sourced] The deployed-version [Grafana endpoint implementation](https://github.com/grafana/grafana/blob/v13.3.1/pkg/services/ngalert/api/prometheus/api_prometheus.go)
sets evaluation status, last error, folder/rule identity and group continuation metadata.
