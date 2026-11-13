# WP04 Codex subscription comparison

[verified] The owner requested GPT-6.1 Sol testing through the existing Codex subscription login.
The evaluator now supports individually bound WP04 fixtures with scoped read-only browsing.
Four serial model attempts completed: two each on cases 7 and 24. All four have intact model,
session and tool-receipt evidence, and separately pass the strict submission parser. Their native
INCONCLUSIVE statuses are the expected manual-review gate, not instrument failures.

[sourced] The completed reviews below separate material factual/authority errors from investigation
coverage. An honest partial handoff at an actual limit does not violate a requirement to establish
a unique cause: the task explicitly allows unknowns and capped reads. Full qualification remains
HOLD, and only human acceptance of an exact candidate can promote it.

## Implementation and boundaries

[verified] The [operator guide](../fleet-evaluation/multi-model-testing.md#separate-wp04-subscription-profile)
documents the new single-fixture selector. The existing fifteen-case testing block is unchanged.
The loader admits only the five indexed-v6/v7 WP04 case IDs, the SRE role, files-only fixtures and
their exact recorded checks; arbitrary fixture commands, environment changes, writes and path
escapes are rejected. Historical v6 checks and case identities remain unchanged.

[verified] The Codex profile supplies canonical role guidance in its prompt and makes the supplied
observations and skill references available through an exact file allowlist. It adds bounded name
listing, literal search and character-range reads, with explicit continuations and independently
recorded call/result receipts. It does not place tens of thousands of paths into the prompt.
Native shell, web, edits and delegation are prohibited. This file allowlist is an application
boundary; native Claude routing, hooks and filesystem isolation are separate controls.

[verified] The child uses a private copy of the existing ChatGPT login. API-key authentication is
refused. Independent review found a race in checking the operator's login before later copying it;
a regression reproduced replacement during workspace preparation. The correction validates the
private copy before staging, and the reviewer closed the finding. No actual credentials were used
in that regression or copied into evidence artifacts.

## Frozen comparison

| Item | Binding |
|---|---|
| Model / effort | `gpt-6.1-sol`, high |
| Runtime / host | Codex CLI 0.167.2, Linux `adama`, uid 1000, Python 3.14.10 |
| Candidate plugin SHA-256 | `8446d62f8b3479ed09898c9bbc084f7b622dd1190d6fe419eeb9b68c669b46f7` |
| Shared runner SHA-256 | `763b4bc011f23fb4e10ddffc9d8bf2b17f6f46643c39c32eee59f68c212f34d6` |
| Reviewed implementation patch SHA-256 | `5794bf3569abdddade925ef3069e00faf6758f805fb38e10a3b50ec7d8c3844f` |
| Codex profile | `wp04-readonly-v1`; prompt-injected guidance and scoped MCP tools |
| Case 7 SHA-256 | `518723629c356061022638befce7444c96a9fb391dd20e160bb6c0f1177d6895` |
| Case 24 SHA-256 | `e818bfce9456b447bce36c7a2440c1cc5c8886034b346635643c9b89af47cdcd` |
| Order | 7:1, 24:1, 24:2, 7:2 |
| Limits | 900 seconds and 64 fixture-call budget per attempt; serial; no model retries |

[verified] Both case hashes exactly match the retained Sonnet v17/indexed-v6 fixtures. The SRE
agent and root-cause skill bytes are also unchanged from v17. The whole plugin, runner, CLI and
tool interface differ from that historical baseline; this is not a controlled model-only comparison.
The frozen private plugin snapshot and all adapter hashes are retained in `approved-plan.json`.

## Results

| Case / trial | Model seconds | Successful fixture calls | Material-gate review proposal | Investigation coverage |
|---|---:|---:|---|---|
| 7 / 1 | 273.172 | 63 | PASS | PARTIAL |
| 24 / 1 | 355.361 | 62 | PASS | PARTIAL |
| 24 / 2 | 364.839 | 62 | PASS | PARTIAL |
| 7 / 2 | 355.625 | 63 | PASS | PARTIAL |

[verified] Each attempt made 65 fixture requests: the 65th was refused because the call budget
was exhausted. One or two earlier requests were refused for invalid limits or unavailable
directories. These refusals are retained in the traces. Each model then
returned a final answer; all four declared their partial scope. A complete instrument record does
not imply complete investigation coverage.

[sourced] Case 7 trial 1 correctly extracts the same-UID ConfigMap's `paymentFailure` change from
`off` to `100%`, preserves unknown collection zones and undefined alert units, and separates the
configuration from runtime activation. It reads all 41 alert snapshots and performs a useful
configuration discriminator. No material factual or causal overclaim was established. Payment
rollout and failing HTTP/request linkage remain unread after the cap. Twenty-eight calls went to
the fourteen alert page descriptors and their fourteen data pages.

[sourced] Case 7 trial 2 independently preserves the same configuration facts, separate clocks,
undefined alert units and runtime uncertainty, with no asserted causal edges. Its complete alert
catalog and configuration comparison are verified; rollout and failing-request linkage remain
unexamined. Both case 7 replies satisfy the material gates while honestly returning partial work.

[sourced] Both case 24 replies recover `kafka:9092` to `kafka:9999`, the recorded Kafka Service
ports, and the actual replacement Pod `qqtsz`. They preserve the unknown exit mechanism and user
recovery, and separate the earlier frontend-proxy activation from the later configuration update.
The second trial additionally reads complete current Pod records, Kafka Endpoints and the later
BackOff/Started events; it correctly avoids treating a subsequent start as recovery.

[unverified] Neither case 24 attempt retrieves the older `bqsrz` alert episode. They do not make
the historical Sonnet answer's false old/current Pod attribution, but full reconciliation of that
older episode remains unmeasured. Selective alert and consumer coverage is explicitly acknowledged.

[sourced] Relative to the [retained v17 results](2026-11-12-wp0405-field-history-repair.md#third-repair-and-measured-limits),
these completed handoffs show useful source discipline: the old case 7 attempt returned no final
diagnosis, while the old case 24 answer joined an older Pod to the later rollout and overstated its
read scope. The new observations support further use of this Codex profile as a development
comparison, not a universal model ranking or a causal claim that changing the model alone fixed it.

## Verification and accounting

[verified] Focused adapter/profile/compatibility checks passed 119 tests and 107 subtests before the
final authentication correction; its focused WP04 checks then passed 10 tests and 13 subtests.
The final full heavy suite passed **5,353 tests, 90 skips and 5,074 subtests**, exit 0, with unchanged
source before and after. Receipt: `.git/local-test-runs/20261113T052059Z-ae3fce14/run.json`.
Configured mypy passed 93 source files; scoped Ruff, catalog validation and Gate A passed.

[verified] Real-fixture offline smoke checks preserved the original case identities, staged all
62,935 case 7 files and 22,606 case 24 files, exercised listing/search/paged reads, refused outside
paths and writes, and confirmed unchanged evidence. Peak RSS was 2,746,836 KiB and 1,043,364 KiB.
One initial launch refused a plugin snapshot without its own Git checkout metadata, before any
Codex model process or subscription call. That setup failure is retained; initializing the private
snapshot's Git metadata preserved the plugin digest. The four authorized model attempts then ran
once each, with no authentication failure or model retry.

[verified] Saved artifact hashes, trace/ledger/session inventories and model identities verify for
all four attempts. Separate strict collection accepts all four JSON submissions without changing
their historical v6 grades. No judge or API-key-authenticated run occurred. Subscription usage is
recorded; per-attempt dollar cost remains **unmeasured**, not zero. The earlier reported dollar
estimate is USD 76.9843344; it is not an invoice and does not price these subscription attempts.

[verified] Private evidence is retained under `.eval-runs/wp04-codex-20261113/`: the approved plan,
case bindings, frozen plugin, source patch, offline smoke receipts, original setup failure, four
launch/result directories, semantic reviews, saved-evidence checks and final completion receipt.
Input-token totals include repeated cached inputs across model turns; they are not a single context
size. No further model calls are scheduled.

[unverified] Two repetitions on two development cases do not establish stability across WP04,
native Claude/Codex equivalence, held-out generalization or human reviewer calibration. Cases 21,
80 and 102, the reserved qualification cases and Windows were not run in this comparison.
Remaining work is to improve evidence navigation efficiency and complete the unresolved comparisons
under a separately bounded test, while retaining source-faithful uncertainty and candidate HOLD.
