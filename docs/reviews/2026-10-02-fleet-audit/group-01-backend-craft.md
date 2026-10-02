# Group 01: backend-craft — six-pass audit

Reviewed 2026-10-02 against `a2d2e57d2de70125dbde002072853e73b788bd8d` in `F:\repos\sre-agents-audit-20261002`. Invoking caller and recipient: `/root`; human owner: the user. Assignment: complete. Parent objective: audit every skill, then every agent, in groups of three and commit each group's findings before continuing. This report makes no changes to the candidate and does not authorize remediation or promotion.

**Conclusion:** the skill is suitable for the team's backend authoring lane, and its core recovery guidance is substantially stronger than its verification layer. Two confirmed findings concern a contradictory webhook grading rule and incomplete HTTP shape predicates. Additional improvements concern oracle evidence, conditional instructions, and measured coverage. No production-service defect or live platform failure was established.

Evidence labels: `[verified]` means current source inspection or the specifically identified local execution; `[sourced]` means fetched public documentation/source; `[unverified]` means behavior not established. File locations below are repository-relative at the frozen revision.

## Pass 1 — suitability, activation, and neighboring responsibilities

**Evidence:** all nine tracked files under `skills/backend-craft/`; `agents/software-engineer.md:43-47,77,97,216-225`; `skills/stack-profile/SKILL.md:13-20,27-37`; `skills/stack-profile/references/application-and-data-stack.md:9-16,24-45`; neighboring descriptions in `database-reliability`, `frontend-craft`, and `operator-cli`.

[verified] The description selects API construction, services, workers, schedulers, and outbound integrations. It excludes frontend work and live database operations. The body explicitly preserves existing interfaces/authentication, permits native non-HTTP worker tests, and makes FastAPI scaffolds conditional (`SKILL.md:19-35`). Those qualifications prevent a CLI integration or scheduler change from acquiring an unnecessary web service. The software-engineer caller loads it before backend changes, alongside Python, database, or telemetry skills as applicable. Java/JVM remains support-only through the stack reference; the bundle does not contain a competing Java authoring template.

**Conclusion:** good scope fit, coherent neighboring lanes, and useful support for a human SRE who needs runnable work and operational evidence. The platform-specific detail should remain conditional; Cloud Run is still a candidate runtime in the stack profile, not an accepted migration decision.

**Gap:** [unverified] description selection and timely reference loading on each supported model/host. Source agreement is not routing evidence. No fresh model campaign ran.

## Pass 2 — technical correctness, dependencies, and changing facts

**Evidence:** `references/fastapi.md:6-44`, `references/consuming-apis.md:9-42`, `references/background-work.md:9-40`, `references/api-writes.md:8-69`, every asset, `requirements-dev.txt:14-18`, and the primary sources below, fetched 2026-10-02.

[sourced] Context7's official FastAPI documentation confirms strict JSON Content-Type checking and the `APIRouter` setting, plus built-in SSE imports, keepalive, and response headers. GitHits independently returned FastAPI tag `0.141.1`, resolved snapshot `95f8322e`: `fastapi/routing.py:436-445,638-646`, `tests/test_sse.py:116-120`, and release notes at `681-686,736-743` confirm the stated 0.132/0.135 introduction points. Documentation and implementation agree. Sources: [strict Content-Type](https://fastapi.tiangolo.com/advanced/strict-content-type/), [SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/), [versioned source](https://github.com/fastapi/fastapi/blob/0.141.1/fastapi/routing.py), [release notes](https://github.com/fastapi/fastapi/blob/0.141.1/docs/en/docs/release-notes.md).

[sourced] Celery's official task documentation confirms that late acknowledgement alone does not redeliver a task after its child process dies. GitHits separately returned `celery/worker/request.py:689-701` at snapshot `e48dc8e6`, with the worker-loss/requeue condition. Preserve the accompanying poison-message warning. Sources: [Celery tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html), [worker implementation](https://github.com/celery/celery/blob/e48dc8e6/celery/worker/request.py).

[sourced] HTTPX distinguishes connect/read/write/pool timeouts and does not initiate ASGI lifespan events, supporting the logical-deadline and explicit-lifespan advice. The Idempotency-Key draft remains expired; RateLimit remains draft `-11`. The skill labels these correctly. Cloud Run's runtime contract retains a ten-second SIGTERM shutdown period. Sources: [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/), [ASGI lifespan](https://www.python-httpx.org/advanced/transports/#asgi-startup-and-shutdown), [idempotency status](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/), [RateLimit status](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/), [Cloud Run shutdown](https://docs.cloud.google.com/run/docs/container-contract#shutdown).

**Conclusion:** no contradiction found in these refreshed technical claims. The version limit, `/v1`, `422` default, and mandatory `Retry-After` are house choices, not universal requirements imposed by every cited standard.

**Gaps:** [unverified] actual PCF foundation grace settings, ingress behavior, cloud probes, deployed vendor versions, and provider-specific token flows. No credentials, real service binding values, or live platform calls were inspected.

## Pass 3 — authority, trust, failure, and recovery

**Evidence:** `SKILL.md:45-57,61-69,78`; `references/consuming-apis.md:5-7,11-37,49-53`; `references/api-writes.md:16-43,47-64`; `references/background-work.md:9-37`; `assets/problem_fastapi.py:29-56,87-92,160-225,297-321`.

[verified] Strong protections include bounded logical deadlines, one retry owner, response/permit cleanup, caller-scoped replay, authorization on every retry, durable uniqueness, atomic local mutation/receipt recording, and explicit UNKNOWN handling for remote effects. The background reference treats publication and consumption crash windows separately, requires replay-horizon deduplication, and addresses poison messages and stale lease owners. Live migration execution stays with the human owner. Upstream responses are explicitly untrusted data.

[verified] The error asset defaults to generated correlation IDs; ingress trust is opt-in and shape-checked. It preserves protocol headers while rebuilding representation metadata. It identifies the unhandled-server-log redaction boundary and requires production debug off; these qualifications should not be removed during compression.

**Conclusion:** source guidance appropriately separates authorized repository work from live effects and distinguishes acceptance from completion. The webhook evaluator conflicts with its required security-review behavior (BC-01 below).

**Gaps:** [unverified] queue persistence/acknowledgement configuration, real datastore arbitration, process termination at both write commit boundaries, revoked-authorization replay, and real server/error-reporter redaction. A test double cannot establish a remote business outcome.

## Pass 4 — LLM readability, ambiguity, and context cost

**Evidence:** `SKILL.md:17-35,37-57,71-82`; `references/consuming-apis.md:14-18`; `references/fastapi.md:3-11`; complete bundle size inspection.

[verified] The entrypoint is 7,718 bytes and 1,109 whitespace-delimited words; the nine-file bundle is 61,265 bytes. These are file measurements, not token estimates. The entrypoint presents a coherent inspect/regress/build/verify sequence and conditional reference table. Most detailed mechanics live outside the always-read body.

The main readability issue is competing specificity: `SKILL.md:47` says a breaker is required for long-lived clients, while the outbound reference requires one when failures need shared suppression. The reference also says the entrypoint wins. A capable model therefore has reason to add a breaker even where bounded retries are sufficient. The FastAPI settings bullet similarly sounds mandatory despite preserving established project patterns elsewhere.

**Conclusion:** readable and reasonably factored; prefer removing or qualifying those blanket prescriptions over adding another general precedence section. No evidence justifies deleting the recovery distinctions or the error helper's redaction/ingress integration notes.

**Gap:** [unverified] comprehension or output-quality gains from further compression. Record byte deltas and measure a narrow counterexample before treating smaller prose as better behavior.

## Pass 5 — actual verification coverage and oracle soundness

**Evidence:** full `scripts/test_backend_craft_assets.py`, `scripts/test_api_write_contract.py`; all three backend build scenarios; all three `evals/oracles/*/probe_checks.py` files; `evals/test_incidents_api_oracle.py`, `evals/test_incident_writes_oracle.py`, `evals/test_pager_webhook_oracle.py`; `evals/README.md:304-339`.

[verified] The asset suite exercises real in-process HTTP responses, malformed JSON versus invalid values, repeated authentication/cookie headers, recomputed representation metadata, redacted exception chains, request-ID trust, lifecycle startup/cleanup, and the actual documented CORS setup. The write acceptance controls include negative cases for missing overlap, false crashes, corrupted state, lost replay, and cross-scope contamination. Their comments correctly limit synthetic controls to assertion quality.

The build-oracle tests go further: disposable SQLite/uvicorn fixtures, independent database reads, targeted mutants, and webhook kill/restart recovery. Preserve these. However, incident-write overlap can fall back to client scheduling rather than observed server arbitration (`incident-writes/probe_checks.py:233-241`); its own output admits that limitation. This does not satisfy the stronger claim required of adapted write tests by `references/api-writes.md:57-60`.

**Conclusion:** substantial offline evidence exists, but BC-01/BC-02 prevent treating every green criterion as the stated contract. [verified] Root execution: Python 3.14.7 full offline pytest exited 0: 1,470 passed, 19 skipped, 1 warning, and 2,690 subtests passed in 671.13 seconds. `evals/build_probe.py --validate` exited 0: 192 specifications (57 build, 57 contract, 1 native, 77 routing), 737 graded expectations. These fresh results cover repository checks; the 19 skips and host/live behavior limits remain visible in the caller's consolidated evidence. No fresh model result is claimed.

## Pass 6 — adversarial cases and prioritized findings

### BC-01 — webhook probe penalizes mandatory security review

**Confirmed defect; Medium severity; high confidence; [verified] source contradiction.** `evals/build-scenarios/build-software-engineer-pager-webhook.yaml:15-18,35-40` asks for a new receiver implementing HMAC authentication, yet line 277 requires `no_task_dispatch` to `reviewer`. `SKILL.md:54` requires review for auth changes; `agents/software-engineer.md:175` also explicitly covers authentication, secrets, cryptography, and trust boundaries.

**Trigger → consequence:** an agent correctly implements the signed endpoint and dispatches the required independent review; the eval marks that action as failure, rewarding omission of the protection. This is a grading-policy conflict, not evidence that a live model actually skipped review.

**Smallest fix:** remove the unconditional no-review criterion from this security-sensitive scenario; retain scope/no-uninvited-commit controls. Add a positive completed-review criterion only if that behavior is part of this probe's intended measurement.

**Verify:** a no-model fixture containing a scoped reviewer dispatch must no longer fail this scenario merely for dispatching; a separate routine non-security scenario should retain its no-extra-review assertion.

### BC-02 — HTTP shape predicates accept outputs outside their declared contracts

**Confirmed bounded oracle defect; Low severity for the starter, Medium for eval-evidence integrity; high confidence; [verified] root reproduction.** `assets/test_http_contract.py:93-106` checks cursor presence but not type, and allows an empty `limit=1` result even when the default page contains records. The paired schema requires a string or null cursor (`assets/openapi.starter.yaml:150-155`). The three eval `is_problem` helpers (`incidents-api:58-71`, `incident-writes:97-107`, `pager-webhook:151-159`) use a media-type prefix and weaker body checks than the fixture's established problem shape.

**Trigger → consequence:** a malformed cursor or error contract can receive a green assertion, hiding a consumer incompatibility. Root executed the disposable pagination reproduction under verified Python 3.14.7, exit 0: numeric cursor and empty limited page were accepted; a populated endpoint ignoring `limit=1` was rejected. Root also inspected and reran the extended reproduction, exit 0: all three malformed problem predicates accepted `application/problem+json-extra` with `type: []`, `title: false`, `status: 422`, and no request ID. These are individual predicates, not a complete native trial. Sparse one-row ignored-limit acceptance is specifically a missing fixture/precondition issue. The starter already requires a populated maximum-cap test at lines 3-5; this finding does not claim that advice is absent.

**Smallest fix:** validate cursor type and require a project-owned populated traversal/limit case. Tighten eval media-type parsing and required problem fields without importing candidate-owned validation into the independent oracle.

**Verify:** valid string/null pages and legitimate problem responses pass; numeric/empty-string cursors, populated empty limited pages, `application/problem+json-extra`, malformed field types, and missing required fields fail for their intended assertion. Avoid building a generic datastore adapter just for these checks.

### Recommendations and remaining acceptance ideas

- **BC-R01 — strengthen evidence of fetched owner (Medium priority; high confidence; [verified] root reproduction).** `incidents-api/probe_checks.py:164-170` accepts any 200 response whose raw text includes `alice`, including a title with that word and `owner: null`. Parse the owner field and record a stub request or vary its returned identity. Add a no-call/wrong-field mutant. Root verified this exact in-memory false acceptance, exit 0. The current predicate establishes substring presence, not a fetched owner.
- **BC-R02 — delete duplicated blanket decisions (Low priority; high confidence).** Remove the unconditional breaker clause from `SKILL.md:47` and let `consuming-apis.md:14-18` own conditional use. Qualify `fastapi.md:10-11` as the new-project default so an existing validated settings mechanism need not gain a dependency. Verify with one existing-service and one client-only scenario.
- **BC-R03 — target missing behavioral boundaries (Medium priority; [unverified] runtime).** Before claiming broad backend readiness, prioritize one cancellation/slow-trickle/Retry-After deadline case, actual server-observed write arbitration, and signed-webhook validation before durable acceptance. Include bounded response size, revoked authorization on replay, and stale-writer takeover only when the changed surface needs them. Use disposable provider/queue/datastore targets and explicit expected outcomes; no large model campaign is implied.

**Handoff:** `/root` should reconcile these source findings with its fresh suite results and the disposable reproduction, commit the group findings, and continue the parent audit. Product fixes, dependency installs, model calls, live platform operations, and commits were not performed by this reviewer.



## Central verification

[verified] The caller completed the full offline baseline (1,470 tests and 2,690 subtests passed; 19 skipped) and validated 192 scenario specifications. See [shared verification and reproduced counterexamples](verification.md) for commands, environment, exact outcomes and limits. These results do not close the runtime gaps above.
