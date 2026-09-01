# SKILL-001 Phase 2 — `backend-craft` disposition evidence

**Status:** Accepted disposition evidence recorded on 2026-09-01. [The fleet
roadmap](../fleet-roadmap.md) is the only live backlog; this record does not queue work.

## Conclusion

`backend-craft` is dispositioned as a **confirmed router with a recitation cut and correctness
repair, retained above the screen**. From exact base
`fd1d8bbae0b20b0db885cb2fb4386a6e20e6fb24` to owner-accepted candidate
`7b4badd1bdce795edbeb2d1297876df6dac495b3`, the always-loaded entrypoint falls from 11,123 to
10,131 immutable bytes (-992, -8.9%); conditional references grow from 29,198 to 30,182 bytes as
endpoint, upstream-client, and persistence test detail moves behind its matching predicate. The
bundle changes by only -8 bytes, but every affected load path is smaller. The description is
byte-identical.

The entrypoint remains above the 7,800-byte screen because its retained body is the shared API,
resiliency, operability, security, and verification contract. It already routes 30,182 reference
bytes while retaining 10,131. This closes the `backend-craft` Phase 2 slice only; it does not claim
that every conditional reference is irreducible.

## Probe-first checkpoint

`[verified]` Before editing, two clean-room probes ran with no plugin, tools, or repository context
from `.eval-runs/backend-craft-workspace/probes/` (gitignored): one Sonnet and one Opus response to
the same 14-question knowledge probe plus the two committed backend discovery prompts as no-skill
pressure controls. Both models reconstructed most generic API and backend mechanics. Both controls
found all four endpoint defects, but each found only five of the six upstream-client defects: both
omitted circuit breaking/fail-fast behavior under pressure. They also disagreed on error shape:
Sonnet proposed a nested envelope while Opus proposed top-level RFC 9457 problem details. Those
results support cutting generic testing recitation while retaining the exact error contract and
persistent-failure rule.

The two calls were sequential with no retry. Reported list-basis usage was approximately USD
0.084341 for Sonnet and USD 0.332179 for Opus, USD 0.416520 total; the operator used a subscriber
account, so this is provider-reported list usage rather than a claim of incremental billing.

## Candidate changes

### Conditional testing detail

Commit `b816035989cba2ec06a32a86ecd013afbe226142` keeps two universal quality-gate bullets in the
entrypoint and moves mechanics to the predicates that need them:

- endpoint authentication, validation, absence, rate-limit, idempotency, upload, and contract-drift
  cases to `references/api-design.md`;
- timeout, retry/backoff, breaker, token, pagination, and malformed-upstream cases to
  `references/consuming-apis.md`;
- real supported-database integration testing to `references/persistence.md`.

Independent review found that an early candidate collapsed missing, expired, and malformed
credentials into a generic 401/403 statement and weakened the recorded-response/no-second-effect
idempotency assertion. Both obligations were restored before the commit. No deterministic test or
eval scenario was removed: the endpoint and upstream discovery scenarios exercise distinct failure
surfaces, and structural link checks cannot prove conditional reference behavior.

### Persistence contract correction

Commit `7b4badd1bdce795edbeb2d1297876df6dac495b3` removes the unconditional PostgreSQL/driver catalog
from the persistence reference. Existing repository choices now win; an unresolved datastore or
driver choice loads `stack-profile` first, preserving the operated PostgreSQL and SQL Server facts.
Migration guidance now requires a tested recovery strategy, not a universally reversible script,
matching `database-reliability`. A focused asset-contract regression failed on the old text and
passes on the candidate.

## Context measurement

| Loaded path | Base bytes | Candidate bytes | Delta |
|---|---:|---:|---:|
| Entrypoint only | 11,123 | 10,131 | -992 |
| Entrypoint + API design | 13,763 | 13,334 | -429 |
| Entrypoint + upstream client | 15,896 | 15,129 | -767 |
| Entrypoint + persistence | 12,274 | 11,478 | -796 |
| Entrypoint + all nine references | 40,321 | 40,313 | -8 |

## Verification

`[verified]` On the exact candidate bytes:

- `py -3.12 scripts/run_component_tests.py`: 39/39 component suites passed, 0 quarantined;
- `py -3.12 scripts/gate_a.py`: 8/8 structural steps passed;
- `claude plugin validate . --strict`: passed;
- `git diff --check`: passed;
- canonical source matches the regenerated Copilot projections; and
- independent Terra review of each batch, followed by an exact post-commit review of
  `7b4badd1bdce795edbeb2d1297876df6dac495b3`, found no P0/P1 issue.

## Deliberate limits

- No paid after-change model run was made. The description is unchanged, so no routing-description
  run is owed; behavior on the exact candidate remains `[unverified]` beyond deterministic tests and
  review.
- The 1,342-byte product-specific catalog at the end of `consuming-apis.md` may be separable from
  generic client resilience while preserving the PCF exact-target/action/rollback gate. It remains
  an unqueued reference-level hypothesis, not unfinished SKILL-001 work and not deletion authority.
- Product/version capsules and actual conditional-reference load frequency remain `[unverified]`
  until refreshed or instrumented. Neither gap reopens this accepted entrypoint disposition.
