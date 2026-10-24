# Resilience analysis skill audit

[verified] Target: `skills/resilience-analysis/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. No material source-contract finding confirmed. Specification and engineering-quality verdicts: partial. The source supports bounded evidence-led analysis; actual service performance, experiments and model adherence require separate evidence.

## Contract assessment

[verified] Analysis begins with a user/batch/data outcome and owner-supplied requirements, preserving intended, implemented and observed behavior with revision/time binding. It separates observed defects, conditional design risks, verification gaps and improvement opportunities. Missing controls by name, absent incidents and unsuccessful observations cannot establish failure or resilience. Existing controls and counterevidence can close a bounded lead without certifying the service.

[verified] Failure scenarios cover latency/overload, shared capacity/failure domains, partial effects, mixed versions, restore, control planes, telemetry and operator access. Replicas do not imply independence; configured pools do not imply actual occupancy; backup success does not imply recoverability. The method requires both useful outcomes and resource/recovery measurements instead of inferring recovery from restarts, cleared alerts or reverted commits.

[verified] Retry examples correctly retain distinctions between retries and attempts, requested and enforced timeouts, false returns and exceptions, deadlines and underlying cancellation/resource release. Admission must precede shared-slot acquisition or reject/defer without retaining reserved slots. The worked proposal requires overload plus concurrent protected work and counts permit waiters/retries, addressing a common false proof from representative demand that never reaches the boundary. Its assumptions, falsification and stop/recovery criteria stay explicit.

[verified] Reliability-engineer's full caller body agrees with document-only assessment, permitted helpers, no direct execution, proposed experiments and separate implementation/review owners. Load rules for stack, data/recovery and consequential architecture complement the skill without expanding authority. Public practices remain guidance, not invented company SLOs or policy. No finding quota or blanket reliability score is required.

## Evidence coverage

| Risk | Evidence | Result |
|---|---|---|
| Overclaiming production defect from source | Entrypoint, worked contrasts and caller | [verified] Conditional claims and source/observation distinctions explicit |
| Unbounded retry/shared-slot propagation | Scenario/reference and complete worked proposal | [verified] Mechanism, counterevidence, occupancy and falsification addressed |
| Mistaking verification gap for absent control | Restore/replica contrasts and result taxonomy | [verified] Missing evidence remains a gap |
| Experiment authority or fake results | Entrypoint, failure scenarios and caller | [verified] Proposed only until authorized actor supplies results |
| Real workload proof and model adherence | No new experiment/model run | [unverified] Not established by static method |

## Read manifest and checks

[verified] Full canonical reads: `SKILL.md`; `references/failure-scenarios.md`, `sources.md`, `worked-contrasts.md` (four files, 221 lines). Full supporting read: `agents/reliability-engineer.md`. Bounded supporting coverage: caller/method searches and reliability build/discovery inventory. Shared stack-profile guidance is reused. Root owns independent evaluation/oracle and public-source review; its evidence retains separate attribution.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_current_check.py resilience-analysis` exited 0: entrypoint and all three reference projections are byte-identical, relative local links resolve, and canonical source diff against target is empty. Existing unchanged-source baseline is reused. No new tests, experiments, live reads or model calls ran. Prose examples are not measured service results.

[verified] Only this report changed for this item. No canonical/test/configuration edits, installs, live actions, commits, pushes, repair or acceptance occurred.

[sourced] Root independently read the discovery case, complete proportionate-options build scenario and calibration lines 390–445 in `evals/test_reliability_cases.py`. Supplied evidence supports a two-hour monthly restart-toil bound, rejects the already-refuted larger pool and unsupported vendor benefits, and requires admission protecting shared read capacity. The fixture explicitly reserves prose/mechanism quality for review: filled headings and a JSON decision do not prove it. Previously reviewed reliability-agent cases and known RELIABILITY-001 acceptance limits remain applicable; no new oracle defect was established.

[sourced] All six bibliography links were read by the public-source reviewer. Google SRE's [design](https://sre.google/workbook/non-abstract-design/), [cascades](https://sre.google/sre-book/addressing-cascading-failures/), [testing](https://sre.google/sre-book/testing-reliability/) and [SLO](https://sre.google/workbook/implementing-slos/) chapters support the named methods; “discriminating tests” is a synthesis, not a named official framework. Both frozen inspiration files exist and fit their stated scope; their timings, ownership and instructions are not adopted as authority.
