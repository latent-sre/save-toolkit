# DRILL-001, INCIDENT-001, ROUTE-002, and SURFACE-001 closeout packet

> **Status: mixed closure and exact-revision candidate evidence.** `INCIDENT-001` and
> `SURFACE-001` were already accepted and merged; this packet closes their stale roadmap entries.
> `DRILL-001` and `ROUTE-002` have new Terra evidence bound to repository revision
> `9ca5758f109eb3b7004df2418cda7aeefb92a52e` and remain live until the owner accepts the stated
> transfer limitations and the evidence merges.

## Conclusion

- `DRILL-001`: implementation items 1–8 are already in `main`; three reconstructed published case
  categories pass on `gpt-5.6-terra`. The old prompts and current usage telemetry are unavailable,
  so exact transcript replay and a numeric cost delta are not claimed.
- `INCIDENT-001`: complete. PR #171's exact accepted hardening revision is an ancestor of current
  `main`; no duplicate edit or replacement model run was warranted.
- `ROUTE-002`: all seven current overlap prompts select the expected owner in independent
  clean-context Terra classification. This is a host-neutral description transfer, not a Claude
  Code Skill-discovery result.
- `SURFACE-001`: complete. Its last two footnote compactions merged in PR #175; the roadmap entry
  was stale.

## DRILL-001

Implementation commit `be8a274` merged in PR
[#175](https://github.com/latent-sre/save-toolkit/pull/175) at `f1b039a`. It carries backlog items
1–8, including the documented pack format, held-back ground-truth file, dispatch-composed packets,
retro destination, drill card, Windows path guard, and tool-grant cross-check.

Three clean-context Terra runners exercised the same published case categories:

| Case | Result | Fresh evidence |
|---|---|---|
| Scaffold and first-lane setup | PASS | 13 service files, 7 evidence files, 14 prompts, no Python placeholder, two tags and the expected release diff; documented scratch virtualenv returned 5/5 service tests |
| Author a migration-lock scenario | PASS | Real parser materialized 6 service files, 7 evidence files, and 5 packets; all hops dispatchable; distinctive ground-truth phrases absent; no deferred-hop marker; service test 1/1 |
| Write a retro from planted lane defects | PASS | Fleet and coordinator findings separated; tainted instruction, digest mismatch, timeout, revision binding, absent tool metadata, and synthetic boundary dispositioned |

The original evidence retained case descriptions but not the byte-exact prompts. The original
authoring arm reported 205k tokens and 19 minutes. The Terra subagent host exposes neither token nor
USD telemetry, so the current numeric cost and delta are unavailable. That limitation is recorded,
not inferred away. Durable measurement:
[`terra-drill-001-acceptance`](2026-08-26-exercise-terra-drill-001-acceptance.md).

## INCIDENT-001

The live entry lagged already merged state. PR
[#171](https://github.com/latent-sre/save-toolkit/pull/171) merged exact head
`8d0e3f8c14514077994bcecc2e6d1345404d71bd` at
`e475d91c158aef4343a756c04c0439d082e856bc`; both are ancestors of this branch.

The retained PR evidence records the frozen incumbent at 0/2 for fractional and unknown recovery
progress and the exact candidate at 2/2 for both direct scenarios. It also records 831/831 grader
checks, 98 valid scenarios, 30/30 component suites, Gate A 6/6, and four green exact-head CI jobs.
The accepted contract keeps SRE through sustained recovery, ends operator prose with one
`incident-state/v2` record, preserves fractional minutes as integer seconds, uses paired nulls for
unknown progress, rejects competing fences, and retains human production authority. This closeout
performed no new eval and does not relabel the historical Sonnet measurement as Terra.

## ROUTE-002

The canonical ownership boundary is unchanged: `obs-alerting` owns steady-state alert design and
`obs-logs` owns backend query dialects. Seven independent clean-context Terra runners each received
one exact committed prompt and only the four current descriptions (`akamai-edge`, `gcp-ops`,
`obs-alerting`, `obs-logs`), with no expected target or grader visible.

| Prompt class | Expected | Terra result |
|---|---|---|
| Akamai DataStream paging alert | `obs-alerting` | PASS |
| Akamai DataStream SPL query | `obs-logs` | PASS |
| Cloud Run burn-rate alert | `obs-alerting` | PASS |
| Cloud Logging query through the GCP near miss | `obs-logs` | PASS |
| Direct Splunk saved-search alert | `obs-alerting` | PASS |
| Direct bounded Cloud Logging query | `obs-logs` | PASS |
| Log-derived saved-search paging alert | `obs-alerting` | PASS |

Result: 7/7. No description changed, so no prior-revision baseline was indicated. The platform does
not expose Claude Code's Skill-discovery mechanism to Terra; this is semantic description transfer,
not host-routing or content-grader evidence. Durable measurement:
[`terra-route-002-overlap`](2026-08-26-exercise-terra-route-002-overlap.md).

## SURFACE-001

Commit `f37e446` changed the two remaining self-retracting examples into one-line `[unverified]`
footnotes in canonical `pcf-deploy` and `runbook` content, regenerated the projections, and merged
through PR [#175](https://github.com/latent-sre/save-toolkit/pull/175) at `f1b039a`. The banner and
retired learning packet/ledger paths were already absent. The owner decision to retain maintenance
skills remains unchanged because no measured consumer impact exists.

## Fresh local verification

| Command | Result |
|---|---|
| `python scripts/test_incident_drill_harness.py` | 10/10 passed |
| `python scripts/test_check_links.py` | 33 passed, 1 skipped |
| `python scripts/test_canary_tokens.py` | 6/6 passed |
| `python scripts/test_observability_skill_contracts.py` | 7/7 passed |
| `python evals/test_graders.py` | 884/884 checks passed |
| `python evals/run_evals.py --validate` | 107 scenarios valid |
| `python scripts/test_release_skill_contracts.py` | 11/11 passed |
| `python scripts/test_runbook_schema.py` | 6/6 passed |
| `python scripts/test_platform_adapters.py` | 29 passed, 2 skipped |
| `python scripts/check_plan_status.py` | PASS |
| `python scripts/check_evidence_refs.py` | PASS |

Gate A, the full component runner, strict plugin validation, and final diff hygiene run on the
combined documentation tree at the push boundary.

## Owner decisions still required

1. Accept the reconstructed DRILL cases and unavailable numeric cost delta, or request one priced
   Terra rerun on a host that exposes usage.
2. Accept the 7/7 host-neutral Terra ROUTE transfer as the requested substitute for the Claude-only
   live runner, or require a host-specific discovery run.

Until those exact-revision decisions are recorded, `DRILL-001` and `ROUTE-002` stay in the live
roadmap. `INCIDENT-001` and `SURFACE-001` are closed because their accepted implementation and
verification had already merged before this packet.
