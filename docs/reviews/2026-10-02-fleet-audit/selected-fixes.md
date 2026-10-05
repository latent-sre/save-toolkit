# Selected audit repairs

Date: 2026-10-02. Human owner: the user; implementation and integration caller: `/root`.
This record dispositions selected findings under `AUDIT-001`; it is not another backlog.

## Candidate and scope

The repair branch is `work/fleet-audit-selected-fixes-20261002`, in
`F:/repos/sre-agents-audit-fixes-20261002`, based on the completed audit commit
`d8e36baa7ca6fe64ad33a409df6c9352a43a73f6`. The reviewed source baseline remains
`a2d2e57d2de70125dbde002072853e73b788bd8d`. The audit branch and original dirty checkout
are separate. The implementation identity below records the exact
working-tree bytes verified before publication.

The owner first selected AE-01, RUN-01/02, PY-01/02/03, LEARN-01/02 and LOG-01/02,
then added FE-01/02, GP-01 and GRA-01/02/03. Findings outside those sixteen remain
unchanged. Original group reports preserve the defects and evidence at the audit baseline;
the dispositions below describe the repair candidate, not a rewrite of that history.

## First batch: implementation and focused verification

[verified] All ten repairs are implemented and their integrated local checks pass.
Independent static review found no material findings in these working-tree bytes. Native/model and target-platform behavior remain
unverified; local checks do not confer human acceptance of a candidate revision.

| Finding | Original problem | Repair and discriminating evidence |
|---|---|---|
| [AE-01](group-11-agent-engineer.md) | The repair oracle stripped leading whitespace, accepting frontmatter rejected by the actual parser. | Preserve the start of the document. The actual embedded predicate rejects leading LF, CRLF and space, unchanged typos and unrelated edits; exact repair, trailing whitespace and CRLF controls pass. |
| [RUN-01](group-09-runbook.md) | A file created after the existence check could be overwritten without force. | Use exclusive creation at the write boundary. A deterministic competing creation remains byte-identical and returns the documented refusal; explicit force retains its existing behavior. |
| [RUN-02](group-09-runbook.md) | HTML `br` elements inside code blocks joined separate code lines. | Preserve them as newlines, including nested code, indentation and blank lines. Literal newline, `br` and `br/` controls pass; suppressed content remains suppressed. |
| [PY-01](group-08-python-craft.md) | The tiny streaming fixture rejected valid bounded buffers. | Separate tiny-file value/lifetime checks from a larger first-yield workload. Fixed buffers of 4, 64 and 8,192 characters pass; existing eager-consumption negatives still fail. This is bounded workload evidence, not proof for arbitrary buffer sizes. |
| [PY-02](group-08-python-craft.md) | Candidate `SystemExit(0)` bypassed checks and reported process success. | Convert candidate exit to an assertion failure at the shared entrypoint. Cover eight modes, import/API/iteration exits, codes 0/2 and fresh-child import orders. |
| [PY-03](group-08-python-craft.md) | Error strings returned as values were indistinguishable from required exceptions. | Tag returned and raised outcomes separately. Returned error text, wrong messages and wrong exception classes fail; valid `ValueError` subclasses pass. |
| [LEARN-01](group-06-operational-learning.md) | A detached labeled audit marker could stand in for provenance on the corrected owner/contact. | Require the actual corrected owner and contact on the labeled AUDIT-73 record. Detached markers, wrong values, misleading prefixes, lost labels and evidence promotion fail. |
| [LEARN-02](group-06-operational-learning.md) | Cards assumed every authoritative alert definition lived in a repository. | Follow the provisioning owner: source path/revision or API locator/UID with supplied receipt/version evidence. Unknown API versions stay unverified; recovery exports remain evidence. A new bounded supplied-state scenario covers both owners and incorrect authority/receipt/version/provenance cases. KB binding, approval and dirty-path controls remain separate. |
| [LOG-01](group-05-obs-logs.md) | Blanket case-insensitivity advice omitted payload and label keys. | State exact-case map/struct keys, alongside the different protobuf-field, ordinary-string and regex rules. Checked against current official documentation. |
| [LOG-02](group-05-obs-logs.md) | An event-time-bounded query was treated as proof that current ingestion stopped. | Explain delayed/backfilled/skewed events and add a bounded index-time follow-up with explicit event-time coverage. At 12:00 an event timestamped 05:50 and indexed at 11:59 is absent from a four-hour event window despite recent ingestion. |

### Red-to-green evidence

The new failure cases were run before their respective executable repairs:

- AE-01: three leading-prefix mutants were falsely accepted; after repair all nine controls pass.
- RUN-01/02: the competing creation and four HTML-break cases failed before repair; the
  affected converter/schema suite then passed 47 tests and 47 subtests.
- PY-01/02/03: the focused red run had 69 failing subtests across larger valid buffers,
  candidate exits and returned errors; the complete repaired calibration passed 23 tests
  and 180 subtests.
- LEARN-01: detached provenance and wrong owner/contact records produced three false
  acceptances before repair. The repaired checks include those and prefix controls.
- LEARN-02: supplied-state calibration accepts both ownership types and rejects stale
  exports, invented versions, wrong receipts, detached labels and misleading source links.
  This validates the instrument; no model performed the closeout.

[verified] Root's integrated command used Python 3.14.7 at
`F:/repos/sre-agents/.venv/Scripts/python.exe`:

```text
python -B -m pytest -q evals/test_agent_engineer_cases.py evals/test_python_craft_oracle.py evals/test_researcher_scribe_cases.py scripts/test_confluence_import.py scripts/test_runbook_schema.py scripts/test_skill_assets.py scripts/test_validate_fleet.py -o cache_dir=F:/iso-tmp/fleet-audit-fixes-20261002/combined-pytest
```

Result: **219 passed, 548 subtests passed**, 47.09 seconds, exit 0. The raw log is
`F:/iso-tmp/fleet-audit-fixes-20261002/first-batch-tests.txt`.
Adapter generation passed; link and fleet validation passed (9 agents, plugin/adapters
consistent). Scenario validation passed **193 specs / 742 expectations**, including the
new supplied-state alert closeout. These checks preceded the second repair batch.

### Documentation evidence and context cost

[sourced] Retrieved through Context7 on 2026-10-02: Google Cloud's
[field-path contract](https://docs.cloud.google.com/logging/docs/view/logging-query-language#field_path_identifiers),
Splunk Enterprise 10.4's
[time modifiers](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/time-format-variables-and-modifiers/time-modifiers)
and [indexing-delay checks](https://help.splunk.com/en/splunk-enterprise/administer/troubleshoot/10.4/data-acquisition-problems/event-indexing-delay).
These establish the LOG-01/02 corrections; neither query was executed against a target.
No prose-mirroring test was added for those small documentation changes.

The three operational-learning documents grow by 989 UTF-8 bytes to describe the missing
API-owned branch and its evidence boundaries. Skill entrypoint and agent-body text is unchanged
in this batch. The new alert closeout fixture is a bounded artifact check, not a general document
quality grader, Grafana schema validator or grant of live access to scribe.

## Second batch: implementation and verification

[verified] FE-01/02, GP-01 and GRA-01/02/03 are implemented. Independent static review
found no open material findings after the additional FE-01 counterexample below was repaired.

| Finding | Repair | Discriminating evidence |
|---|---|---|
| [FE-01](group-03-frontend-craft.md) | Scope state checks to the rendered page, require visible or accessible signals, and compare their meaning/count across controlled requests. Hidden text, unrelated permanent messages and remounts cannot supply the requested transition. | Actual copied oracle; visible text, named roles, same-node updates, progress/busy alternatives, hidden messages/descendants and permanent/remounted-message controls. |
| [FE-02](group-03-frontend-craft.md) | Check visible closed/open rows after selection and deep-link restoration, alongside URL/control state. | Working client filtering, server filtering and CSS-hidden rows pass; URL-only and ignored-deep-link variants fail. |
| [GP-01](group-03-gcp-ops.md) | Separate the fleet credential tripwire from SRE-only gcloud flag restrictions. Guard code and permissions are unchanged. | Twelve synthetic hook decisions cover both shells, both lanes, the two flags and token-output controls. |
| [GRA-01](group-04-grafana.md) | Validate traversed object/array/text shapes and return one location-specific exit-2 diagnostic. Catch only the dedicated input-shape exception. | Actual subprocess: clean 0, violations 1, uncheckable/V2 2. Optional nulls, rows, wrappers, legacy datasource names and opaque plugin queries retain their behavior. |
| [GRA-02](group-04-grafana.md) | Preserve case, quoted bytes and token boundaries; permit cosmetic spacing/comments and the established consistent rate-window substitution. Decode proxy query parameters once. | Case/literal/escape/raw-string, token-join, comment/subquery, quoted-macro, minimum-window and literal `+`/`%20` controls. |
| [GRA-03](group-04-grafana.md) | Reject response errors and failing/malformed statuses. Bind actual finite numeric data to frame schemas/refIds or valid proxy samples. Zero remains data. | Error-plus-frame, timestamp-only, null-only, boolean/string/nonfinite, malformed schema/sample and ordinary/zero positive controls. |

### Executed failures and affected suites

- FE baseline: **10 failed, 8 passed** in the calibration because the original oracle
  accepted every mutant. These were 72 executions of the four affected bars.
- Independent review found that a visible role wrapper could still derive its changing
  signal from hidden descendants. The reviewed candidate reproduced **2 failed, 18 passed**.
  The correction separates visible text-node content from computed accessible names,
  including valid hidden `aria-labelledby` references. Final focused calibration:
  **22 passed / 88 bar executions**, 10 valid variants and 12 mutants, 57.22 seconds.
- GRA-01: **27 failing malformed-input subcases** before repair; final helper suite
  **42 tests / 44 subtests passed**.
- GRA-02/03: **68 failing subtests** before repair; the proxy double-decoding pair added
  two failures. Candidate comment/subquery compatibility controls also failed before their
  correction. Final `evals/test_build_probe.py`: **200 tests / 276 subtests passed**,
  82.44 seconds. DASH-01 quantile semantics remain outside this selected scope.
- GP-01: both Bash and PowerShell return 43 for SRE impersonation/flags-file forms and
  42 for those forms in the observability lane. Both return 43 for direct token printing.
  Denial JSON and empty allow output were checked. No gcloud command or flags file ran.

The first combined-suite attempt was intentionally interrupted after review identified the
hidden-descendant gap. It supplies no final-suite pass. Its log and implementation manifest
are retained separately from the fresh final run.

### Frontend execution boundary

The runner executes the actual copied oracle, using an independently authored reference app
and mutants. The explicitly selected bounded mode substitutes only MSW transport and the
unused axe import. Existing dependencies were reused from
`F:/repos/backbox-ui/frontend/node_modules`; nothing was installed or downloaded.

| Dependency | Executed version |
|---|---|
| Node | 24.16.0 |
| React / React DOM | 19.2.7 |
| React Router DOM | 7.18.1 |
| Testing Library React / jest-dom / user-event | 16.3.2 / 6.9.1 / 14.6.1 |
| Vitest / JSDOM | 4.1.10 / 29.1.1 |

[unverified] The original fixture's pinned versions differ from this reused tree. Full MSW
integration, bars 4/6/7, native browser rendering, keyboard/reflow, assistive technology and
model behavior were not exercised. The available full mode still selects only bars 1/2/3/5;
it has not been executed here. The bounded pass is not full frontend acceptance.

### External contracts and growth

[sourced] Context7 retrieval on 2026-10-02 supplied
[jest-dom visibility](https://github.com/testing-library/jest-dom/blob/main/README.md),
[role-name matching](https://github.com/testing-library/testing-library-docs/blob/main/docs/queries/byrole.mdx),
[PromQL literals](https://prometheus.io/docs/prometheus/latest/querying/basics/),
and [Grafana datasource response shapes](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/data_source/).
The Grafana example binds typed fields to columns and permits an omitted per-result status.
GitHits separately corroborated Prometheus
[comment handling](https://github.com/prometheus/prometheus/blob/7d180b0c/promql/parser/lex.go#L425)
and [API samples](https://github.com/prometheus/prometheus/blob/7d180b0c/docs/querying/api.md#L738),
and Grafana [status/error handling](https://github.com/grafana/grafana/blob/d0982ab/pkg/services/diagnostics/diagnostics.go#L335).
These source contracts do not establish deployed-platform behavior.

Relative to the audit commit, the GCP entrypoint grows 194 bytes/2 lines; the Grafana helper
2,973 bytes/61 lines; the query predicate file 4,706 bytes/104 lines; and the final UI oracle
3,981 bytes/103 lines. Growth covers reproduced malformed-input and false-acceptance cases,
with positive compatibility controls. No agent body changed. PromQL comparison remains a
bounded lexical check; the hygiene helper is not a full Grafana schema validator, and the
positive-data predicate is specific to the populated histogram fixture.

## Final integrated verification

[verified] **1,528 passed, 19 skipped, 2,922 subtests passed**, exit 0, 714.48 seconds.
The run reported one Starlette/AnyIO deprecation warning. Skips were three unavailable
Windows directory-symlink cases, two shell/CI cases, eleven external-producer acceptance
cases and three opt-in Docker/Claude smoke checks. The 22 bounded frontend calibrations
ran as part of this suite; they were not skipped.

The final run enables `INCIDENTS_PAGE_MODE=bounded` and the explicit dependency/scratch
paths above, clears `INCIDENTS_PAGE_ORACLE`, and sets `RUN_INSPECT_DOCKER_SMOKE=0`:

```text
python -B -m pytest -q -rs -o cache_dir=F:/iso-tmp/fleet-audit-fixes-20261002/final-pytest-retry
```

Scenario validation: **193 specs / 742 expectations**. Canonical links and fleet validation
pass; eight changed generated copies match their canonical sources. `git diff --check` passes.
The full-suite log is `F:/iso-tmp/fleet-audit-fixes-20261002/full-suite-final.txt`; focused
failure/green logs, frontend versions/hashes and the twelve-decision GCP matrix are retained
under that scratch directory. No native/model campaign or live platform operation ran.

Implementation identity: base `d8e36baa7ca6fe64ad33a409df6c9352a43a73f6` plus the
33 changed/new non-report files in `implementation-manifest.json`; sorted path/size/SHA-256
manifest digest `d7d2a6486999daa03ab52fc3f2fe616d4e3aee20e9d253ad666803c5eb201875`.
The final check confirms those implementation bytes stayed unchanged during verification.

## Disposition

The sixteen named findings are repaired and locally verified, with no open material static
review findings. The remaining **34** confirmed audit findings and optional recommendations
are unchanged. `AUDIT-001` retains their owner disposition and exact-candidate acceptance.
The original dirty checkout and completed audit branch remain separate. The owner has
authorized commit and push of this repair branch after verification. No merge or deployment
was performed; local verification is not merge approval. The publication commit retains this
record and the normal pre-push gate result is recorded with the publication receipt.
