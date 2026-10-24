# Audit findings 21–25 repairs

The requester authorized all remaining findings after second-batch commit
`9961edf3e0b4ecffd91b086c9dacd698a95efe14`. Original reports describe source at `8b4f9b78`;
this follow-up records the final five repairs. The [fleet roadmap](../../fleet-roadmap.md) remains
the only live backlog. Sandbox changes remain unpromoted under GRAPH-007.

## Changes and acceptance evidence

| Finding | Repair | Focused evidence and limits |
|---|---|---|
| AUDIT-GATE-001 | Both intended-passing approval fixtures carry explicit UTC-relative approval/expiry evidence covering the bound action time. The executor's immediate pre-action identity/expiry check remains pending. | Four supplied-time cases failed before correction; focused approval plus grader tests passed 47 cases and 301 subtests. Exact-JSON calibration retains missing execution authority as the sole failing boundary in its fixture; missing-validity control remains unchanged. No production approval or model behavior established. |
| AUDIT-PYTHON-001 | Package oracle retains the actual borrowed generator through malformed/numeric-validation failure, checks it was not closed, and verifies the next input remains available before caller-owned cleanup. | Supervised yield-from adapters in calculation and preview previously passed, now fail with contract code 10. Safe for-loop forwarding controls still pass. |
| AUDIT-PYTHON-002 | Schema batch checks use beta/gamma/beta/alpha identities, preserving duplicates and a nonmonotonic, nonpalindromic order. Public replacement returns distinct sentinels and preserves originally-invalid-input override sensitivity. | Reversal, replacement-only reversal and sorting mutants previously passed, now fail with contract code 10. Existing correct implementations and supervision distinctions remain passing. |
| AUDIT-GRAPH-001 | Sandbox effect rows require a persisted logical request ID stable across retries and distinct for new identical operations, atomically bound to an immutable payload digest. Attempt identity remains separate; fork/replay/template/telemetry contracts agree. | Document-derived key inputs distinguish new identical operations from retries; changed payload cannot evade mismatch checks by changing the key. Static design evidence only. |
| AUDIT-GRAPH-002 | Sandbox consistently prohibits automatic redispatch while UNKNOWN/RECONCILING/STILL_UNKNOWN, including native-dedupe claims. A durable success receipt or definitive non-application with no possible late commit must resolve uncertainty before any bounded retry. | Missing, expired and valid dedupe-proof cases all hold unresolved effects; source state-machine/review/template checks agree. No graph engine or runtime effect is exercised. |

[verified] All five Python mutants were run against the original supervised oracle and returned
false PASS (exit 0); repaired oracles reject them with exit 10. Both affected Python calibration
files pass **107 tests**, including existing unavailable/crash/early-exit distinctions. Test lint,
formatting and isolated oracle syntax/name checks pass. No dependency or production application
code changes are involved.

[verified] All ten sandbox contract probes fail against the original bundle and pass after repair.
They evaluate declared symbolic key inputs and source/state-machine consistency; they do not
implement or validate a production idempotency service. Canonical fleet routing and packaging
remain separate from the sandbox; promotion still requires its own owner decision.

## Integrated verification

[verified] Final coordinated default-plus-heavy suite: **4,355 passed, 84 skipped, 4,958 subtests
passed**; 4,439 collected, zero failures, exit 0 in 80.183 seconds. Command:
`/home/hawkfire/save-toolkit/.venv/bin/python scripts/local_tests.py --heavy`.
Receipt: `/home/hawkfire/save-toolkit/.git/local-test-runs/20261024T115913Z-dfbe0bb8/run.json`.
All new tests were staged before execution. Tracked diff hashes were identical before and after
the run, and all 14 changed source/test files matched the independently captured hash snapshot.
Subsequent edits record these results in documentation only.

[verified] Gate A passed both structural steps. Configured Ruff lint/format, isolated oracle
syntax/name lint, mypy (35 files), and validation of 373 scenarios / 2,139 expectations passed.
The 84 skips comprise 39 opt-in UI cases, 29 Windows cases, 11 external producer cases,
three Docker cases, and two shell/PowerShell cases. No skipped host behavior is claimed passing.

[verified] Independent Sol source review found no material new false-pass, false-fail,
contradiction or regression in the final five repairs. This is local source and executable
calibration evidence, not human merge acceptance. Sandbox canonical/generated paths remain
absent and the GRAPH-007 roadmap section is unchanged; no adapter generation or fleet routing
change was needed. All 186 checked links/anchors across the final report, ledger, roadmap and changed sandbox
references resolve after the documentation updates.

[verified] Sandbox instruction growth totals 3,822 bytes: entrypoint +216, template +322,
durability +630, effects +2,266, telemetry +45 and review checklist +343. This supplies the missing
persisted-operation identity, consistent uncertainty handling, and explicit reconciliation
counterexamples across the candidate's authoring/review surfaces; no runtime engine or new
production authority is introduced.

[unverified] Live model adherence, installed-host enforcement, protected production execution,
and durable distributed runtime guarantees remain outside these local checks. No live writes,
paid model calls, deployment, publication, promotion, or archive restoration are included.
