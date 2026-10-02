# Consolidated reference audit recommendations

Date: 2026-10-02. Frozen source: `c7fdbe314c95f6bbe29b11519214c30655322ba1`.
See the [method and nine group reports](README.md) and [complete inventory](inventory.csv).

**Follow-up:** the owner authorized implementation after this audit. All 39 actionable records
are applied; REF-GCP-02 remains pending. See [actual changes and verification](implementation.md).
The proposal classifications, measurements and no-cleanup statements below describe the frozen
audit snapshot, not the current implementation state.

## Conclusion

[verified source review] All **103 references across 25 skills** received six review lenses.
Most serve distinct tasks, preserve platform-specific mechanics, or explain failure cases that
their entrypoints do not supply. Retain that material. The supported cleanup is bounded:
**74 KEEP, 26 TRIM, one paired MERGE, and two CONDITIONAL inventories**. No file is recommended
for unconditional deletion. KEEP means retain the separate reference; some KEEP files still
need a small correction or navigation addition. TRIM can include receiving relocated content,
as Alloy does in the paired trace-exporter proposal.

The **40 records** comprise **two documentation correctness defects, seven navigation-convention
records, 30 optional recommendations, and one shared ownership decision**. These are not 40 new
runtime bugs. Some refine optional recommendations from the preceding fleet audit. The nine
records labeled `confirmed-defect` in group data comprise the two correctness defects and seven
local-convention mismatches. No cleanup is implemented by this packet.

## Recommended order

1. Correct **REF-AK-01** and **REF-RUN-01**. SIEM replay limits do not establish exclusive portal
   retention; curl's `--fail-with-body` can save an error response while returning failure.
   Include **REF-II-01** as a bounded inference clarification: different timers alone cannot
   place latency outside a container. Its counterexample is logical, not an observed incident.
2. Apply the small, exact duplication/provenance cuts selected below. Keep source links, immutable
   version pins, actual task differences, authority rules and UNKNOWN/recovery behavior.
3. Consider **REF-RUN-02** and **REF-TRACE-01** as paired edits. Their destination content and
   callers must survive before removing the source. The runbook merge is the only whole-file
   retirement candidate; its entrypoint grows slightly.
4. Add concise Contents links to the ten long references covered by seven records. This follows
   existing authoring convention; improved model navigation has not been measured. A further
   101-line artifact reference falls below the threshold if REF-AA-01 is accepted; otherwise
   reassess its navigation too.
5. Resolve **REF-GCP-02** before populating real team inventory. Keep the two placeholder files
   until an approved record location and replacement read/ask path exist. This is the existing
   context-ownership decision, not a new permission gate for ordinary document edits.

## Complete action register

Links lead to the full evidence, exact spans or replacement text, preserved rules and validation
requirements in each group. **Reduction** is positive for fewer canonical UTF-8/LF bytes and
negative for growth. Exact figures measure a proposed edit, not an applied change. Navigation
and Copilot figures are estimates; placement alternatives are not additive.

| ID / evidence | Classification | Smallest useful action and preservation requirement | Proposed reduction |
|---|---|---|---:|
| [REF-AA-01](group-01.md) | Optional | Remove two same-file artifact repeats; preserve independent review, scoped PASS and human promotion. | 351 B |
| [REF-AA-02](group-01.md) | Optional | Consolidate Copilot's repeated unused-field table after moving unique pin/host-verification reasons to the primary rows. | 800–1,000 B estimated |
| [REF-AA-03](group-01.md) | Navigation convention | Add Contents to agent-security; retain every security boundary. | −250 to −150 B estimated |
| [REF-AK-01](group-01.md) | Correctness, P2 | Replace the portal-only archive inference with destination-retention and portal-availability conditions; keep 12-hour replay urgency. | 52 B |
| [REF-AK-02](group-01.md) | Optional | Shorten disputed retry-count history; keep source disagreement, no-backup and missing-data caveats. | 216 B |
| [REF-AK-03](group-01.md) | Optional | Use current mPulse timer definitions instead of historical exposition; keep asset waits and causal/missing-beacon limits. | 168 B |
| [REF-CI-01](group-02.md) | Navigation convention | Add Contents to the PCF deployment example without altering its test-consumed YAML. | −180 to −100 B estimated |
| [REF-DB-01](group-02.md) | Optional | Name a DBA-agreed wait deadline; retain concurrent-index failure/cleanup and maintenance qualifications. | −9 B |
| [REF-DB-02](group-02.md) | Optional | Trim the restore footer's repeated warnings; retain stage timings, all verdicts and watermark/RPO limits. | 119 B |
| [REF-EL-01](group-02.md) | Optional | Replace the aphorism with direct consumer checks; preserve unknown consumers, implicit dependencies and retirement/versioning. | 127 B |
| [REF-FE-01](group-03.md) | Optional | Move four check-date suffixes into audit provenance; keep source URLs and the reliance-bounding Staticfile revision. | 84 B |
| [REF-FE-02](group-03.md) | Optional | Delete the immediately repeated existing-stack precedence clause; retain the primary rule and greenfield exceptions. | 51 B |
| [REF-GCP-01](group-03.md) | Optional | Tie minimum instances to measured SLO need and billed cost; preserve runtime-decision ownership. | 47 B |
| [REF-GCP-02](group-03.md) | Shared decision | Select an approved home for real inventory, then atomically update pointers and missing-context handling; keep placeholders meanwhile. | None claimed |
| [REF-GRAF-01](group-03.md) | Optional | Replace duplicate platform/plugin facts with their existing owners; keep the explicit entitlement link and complete write/recovery loop. | 562 B |
| [REF-GRAF-02](group-03.md) | Optional | Relax the categorical edit-only MCP payload clause; retain selective-read preference and tool limits. No task refusal was demonstrated. | 44 B |
| [REF-GRAF-03](group-03.md) | Optional | Remove the error-directed namespace shortcut; retain authorized organization preflight. No cross-tenant exploit is claimed. | 85 B |
| [REF-GRAF-04](group-03.md) | Navigation convention | Add Contents to grafana-alerting, http-api, json-model and visual-verification; preserve existing scopes and anchors. | −1,000 to −700 B estimated |
| [REF-GRAF-05](group-03.md) | Optional | Remove one repeated fixed-UID sentence; retain portability classification and ownership rules. | 81 B |
| [REF-II-01](group-04.md) | Optional inference clarification, P2 | Match request identity and timer boundaries before locating delay; retain the discrepancy as a diagnostic clue. | −99 B |
| [REF-II-02](group-04.md) | Optional | Keep the team dependency prior in its parent; retain the early dependency-team check and all discriminators. | 166 B |
| [REF-II-03](group-04.md) | Optional | Link the shorter mitigation readback paragraph to its detailed same-file rule; retain receipt-versus-readback, UNKNOWN and ITO ownership. | 163 B |
| [REF-II-04](group-04.md) | Navigation convention | Add Contents to helper-exchange; keep its single fenced reply byte-for-byte for its test reader. | −210 to −150 B estimated |
| [REF-ALERT-01](group-04.md) | Optional | Delete the superseded retrieval-blocked aside; preserve target-version and suppression semantics. | 37 B |
| [REF-LOG-01](group-04.md) | Navigation convention | Add Contents to the task-query catalog; preserve every query, field and explicit empty-coverage section. | −600 to −350 B estimated |
| [REF-MET-01](group-05.md) | Optional | Remove WQL's generic closing handoff already owned by the parent; keep all query and missing-data rules. | 264 B |
| [REF-MET-02](group-05.md) | Navigation convention | Add Contents to PromQL without changing queries or version/evidence qualifications. | −240 to −140 B estimated |
| [REF-PIPE-01](group-05.md) | Optional | Compact Alloy's retrieval/release-cadence introduction; keep deployed-version checks, component sources and repaired PowerShell recipe. | 177 B |
| [REF-PIPE-02](group-05.md) | Optional | Remove the SDK bootstrap check-date clause; retain source, lock/bootstrap workflow and target-canary limits. | 32 B |
| [REF-PIPE-03](group-05.md) | Navigation convention | Add SDK Contents links for Steps and Done; preserve commands and scope. | −70 to −40 B estimated |
| [REF-TRACE-01](group-05.md) | Optional paired relocation | Move exporter configuration from trace reading to Alloy; retain transports, ADC, writer/quota roles, sources and preview/target limits. | 242 B net |
| [REF-DEP-01](group-06.md) | Optional | Remove the earlier duplicate resize pointer; retain the full warning, scale recovery and human execution ownership. | 93 B |
| [REF-GATE-01](group-07.md) | Optional | Add the organization field to the fictional PCF target; preserve its unverified status and existing approval rule. | −13 B |
| [REF-PY-01](group-07.md) | Optional | Trim generic reporting/cleanup closing clauses; retain complete-path, boundary/failure, consumer and installed-artifact checks. | 146 B |
| [REF-PY-02](group-07.md) | Optional | Shorten the generic parent-ownership reminder; retain concrete diff, behavior, parser, lint/type and tool-safety checks. | 65 B |
| [REF-RUN-01](group-08.md) | Correctness, P3 | Explain curl's saved error body and require checking exit status before conversion; preserve the command and tested phrases. | −31 B |
| [REF-RUN-02](group-08.md) | Optional paired merge | Move unique upkeep clauses into the existing runbook parent, then retire living-runbooks and rewire callers/history links. | 2,635 B net |
| [REF-STACK-01](group-08.md) | Optional | Remove the universal CredHub-integration negative; preserve the team's identity policy and UAA rationale. | 34 B |
| [REF-STACK-02](group-08.md) | Optional | Remove the blanket agent-execution sentence from the glossary; preserve human ownership and complete scoped authority rules. | 39 B |
| [REF-STACK-03](group-08.md) | Optional | Remove the repeated no-retirement sentence; retain parent policy, coexistence table and entitlement/service unknowns. | 155 B |

No new numbered recommendation was justified for backend-craft, operational-learning,
pcf-ops, resilience-analysis, service-lifecycle or toil-reduction. PCF's empty foundations
inventory shares REF-GCP-02. Existing substantive log/metric schemas and alerting inventories
remain useful; any real values must follow the same accepted ownership decision.

## Size and loading tradeoffs

[verified measurements; estimated total] The measured proposals, including corrective growth
and both paired edits, sum to **6,083 bytes of net reduction** before the estimated items.
The Copilot consolidation contributes an estimated **800–1,000 bytes**. Seven navigation
records add an estimated **1,630–2,550 bytes** across ten files. Thus the preferred combined
proposal is **4,333–5,453 bytes smaller** across canonical skill files:

```text
Minimum reduction = 6,083 + 800 − 2,550 = 4,333 bytes
Maximum reduction = 6,083 + 1,000 − 1,630 = 5,453 bytes
```

This is a modest reduction relative to 553,914 reference bytes. The calculation includes parent
changes and excludes generated mirrors, historical-link repair bytes and this audit packet.
It is an estimate for the specified proposal spans, not a guaranteed final patch size.
Inventory choices claim no savings. Adding extra wording or links changes the final result.

The runbook merge removes 2,946 reference bytes but adds 311 bytes to its entrypoint, saving
2,635 bytes overall. Its alternative keeps the reference and shortens the parent by 590 bytes;
choose one placement. The trace relocation removes 626 bytes from trace reading and adds 384
bytes to Alloy, saving 242 bytes overall. Neither proposal establishes a lower cost for every
task. **No token count, latency, reference-loading frequency or behavioral uplift was measured.**

## What should survive cleanup

- Independent entry paths need their own applicable authority, evidence and recovery boundaries.
  The symptom/systemic incident guides, glossary and guarded Grafana access instructions cannot
  depend on an assumed parent read when they have direct consumers.
- Worked examples, executable documentation and platform-specific queries need their actual
  task distinctions. Short files are not automatically waste; a static test's existence is not
  proof of model utility. The four toil examples illustrate four different decisions.
- Keep source citations and version/date pins when they limit reliance. Only provenance that
  does not change the instruction is proposed for relocation into this dated evidence packet.
- Keep human ownership, ITO/TLC continuity, scoped Grafana authority, exact-target checks,
  UNKNOWN outcomes, no blind retry, secret boundaries and current-state-versus-causal-proof
  distinctions. Cleanup must not broaden execution authority or promote a candidate.

## Validation for selected follow-up changes

The group reports specify narrow checks for each proposal. For any accepted cleanup, rebase the
selected spans against the current source, inspect the surviving reading paths, update current
links and preserve historical claims through immutable source links. Edit canonical files and
regenerate adapters. Run link/fleet/adapter checks and the existing checks that actually consume
changed examples or fields; do not mistake unexecuted scenario declarations for passing tests.

The runbook merge additionally needs history/version/rehearsal and closeout-path checks. The
trace move needs both reading and pipeline ownership checked together. New model calibration
is warranted only for a claimed behavioral improvement or a changed behavioral boundary, with
an explicit bounded scope. This audit does not close native reliability, service-context,
target-platform or model-behavior acceptance gaps recorded in the live roadmap.

This packet completes the reference review. The human owner selects cleanup; the caller then
implements and verifies that selected scope. The original fleet audit's remaining 12 findings
retain their existing dispositions and are not replaced by this reference register.
