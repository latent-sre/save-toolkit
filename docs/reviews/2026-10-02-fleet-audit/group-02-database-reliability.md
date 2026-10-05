# Group 02 — database-reliability

Reviewed 2026-10-02 in `F:\repos\sre-agents-audit-20261002`. Canonical baseline: `a2d2e57d2de70125dbde002072853e73b788bd8d`; HEAD includes the first audit-report commit. Invoking caller: `/root`; human owner: the user. Assignment: six read-only passes on this skill and its bounded consumers. The parent objective remains all skills, then agents, committed in groups of three.

**Verdict: suitable, with partial verification. No material correctness defect confirmed.** The bundle preserves the important distinction between preparing a migration and executing it, and between a completed restore command and demonstrated recovery. Three focused recommendations concern direct behavioral coverage, synchronization during backfill, and making concurrent-index acceptance more explicit. None is a report of observed data loss or a failed production operation.

## Scope and evidence contract

[verified] Read the entire six-file bundle: `SKILL.md` and `references/{postgres-migrations,sql-server-migrations,query-plan-safety,saturation-triage,restore-drill}.md`. Inspected the relevant passages in `agents/{software-engineer,sre-assistant,reliability-engineer}.md`, `skills/backend-craft/SKILL.md`, `skills/stack-profile/{SKILL.md,references/application-and-data-stack.md}`, and the shared production gate. Inspected the adjacent recovery scenarios and their exact-field grader. A scoped diff against the frozen baseline returned exit 0 and no content changes for `skills/database-reliability`.

Requirements were safe diagnostic selection, version-aware migration design, supported-consumer compatibility, preserved writes, explicit authority, and measured recovery. Static source inspection establishes the written contract. Current primary documentation supplies engine semantics. Target database behavior and model compliance remain unverified. No database, cloud, or restore operation was attempted; no dependency was installed and no canonical file was edited.

## Pass 1 — suitability, routing, and consumers

[verified] `SKILL.md:4-7` names slow queries, contention, replication, pools, migrations, and recovery, with useful exclusions for application triage, alerts, and persistence implementation. The application/data boundary at `:12-16` matches the on-prem PostgreSQL and SQL Server inventory in `skills/stack-profile/references/application-and-data-stack.md:55-64`. SQLite is explicitly outside the operated-engine lane. Nothing here assumes a cloud database has already been adopted.

The skill is consumed by the read-only SRE assistant for symptoms (`agents/sre-assistant.md:61`), by the software engineer before migration/index/pool changes (`agents/software-engineer.md:221`), and by the reliability engineer for integrity and recovery (`agents/reliability-engineer.md:50-55`). `backend-craft:56,78` supplies the reciprocal migration-safety link. The references therefore support diagnosis, design, and implementation handoff without creating another applying actor.

The five conditional reference rows (`SKILL.md:63-72`) are a good division: the caller can load a PostgreSQL migration procedure without the SQL Server or restore material. The main suitability gap is measurement: there is no direct discovery or contract scenario for this skill. This does not prove misrouting; it leaves discovery and consumer loading unmeasured.

## Pass 2 — technical correctness and currency

[sourced] PostgreSQL 18 documentation supports named `NOT NULL ... NOT VALID` constraints, enforcement for inserted/updated rows, later validation under `SHARE UPDATE EXCLUSIVE`, virtual generated columns, concurrent-index transaction restrictions, and invalid-index outcomes. The distinction between PostgreSQL 18 and earlier constraint paths in `postgres-migrations.md:37-68` is useful and should survive simplification. Its warning that an unrelated update can trip a legacy NULL is particularly valuable.

[sourced] Current Microsoft documentation supports the SQL Server low-priority version boundaries, unsupported `WAIT_AT_LOW_PRIORITY` on online `ALTER COLUMN`, runtime-constant/default eligibility, row-size restrictions, and lock-timeout cleanup. The reference correctly avoids assuming `XACT_ABORT` alone closes the migration transaction (`sql-server-migrations.md:15-20`). `LOCK_TIMEOUT` persists for the connection; a future executable recipe should dispose of the dedicated migration connection or restore its settings.

Context7 supplied the PostgreSQL 18 and Microsoft SQL documentation contracts; official web pages were used for exact restrictions. A requested GitHits lookup of `postgres/postgres@REL_18_STABLE`, `src/backend/commands/indexcmds.c`, remained indexing after bounded retries. No upstream source-level corroboration is claimed. This is a research limit, not evidence of a product defect. No deployed major version, SQL Server edition, migration framework configuration, or representative data volume was available.

## Pass 3 — operational workflow, authority, and recovery

[verified] `SKILL.md:18-22,44-59` preserves granted reads, bounded load/output, DBA authorization, and the production gate. The scratch-drill exception requires an assigned target, data scope, and actor; it does not authorize arbitrary backup copying. `restore-drill.md:7-11` specifically isolates restored jobs, integrations, and networking, which prevents a disposable name from being mistaken for a safe environment.

Recovery is outcome-based: `SKILL.md:30-36` permits an evidenced forward repair instead of requiring a lossy inverse. `restore-drill.md:15-26` starts elapsed recovery before backup/runbook retrieval and separates the recovered write watermark from the elapsed clock. Its inconclusive verdict preserves missing RPO evidence. Keep these rules: successful SQL or a backup filename cannot establish the recovered business state.

The plan-only table is a default selection guide, not a guarantee that arbitrary SQL is inert. `query-plan-safety.md:11-17,28-35` requires classification of side effects, volatile functions, triggers, and external transaction boundaries. A `SELECT` invoking sequence or advisory-lock operations is not automatically the authorized read-only case. PostgreSQL can evaluate immutable functions during planning; that documented nuance means an unreviewed function body deserves inspection even for `EXPLAIN`. Existing qualifications prevent a confirmed finding that the skill categorically authorizes such SQL.

DBA approval, human execution of live changes, and refusing automatic blocker termination are repository policy choices, not vendor limitations. No change to those policies is recommended by this audit.

## Pass 4 — LLM readability and context cost

[verified] The bundle is 21,885 bytes and 2,954 whitespace-delimited words; the entrypoint is 5,881 bytes/788 words. These are measured file/word counts, not tokens. Conditional loading, two-column plan semantics, engine/version separation, and the short output types are effective. The references contain little decorative prose. A broad compression pass is not warranted.

Two phrases deserve precision when next editing behavior. First, the sequence at `SKILL.md:34-36` lists backfill before dual-write/read; it does not explicitly state how concurrent accepted writes remain synchronized throughout that backfill. The general preserve-writes and verification rules help, but they leave the design mechanism implicit (DB-R02). Second, the concurrent-index exception says to watch and cancel a wait “if one persists” (`postgres-migrations.md:25-27`), without naming the agreed stop bound (DB-R03).

Prefer replacing those phrases with concrete conditions over appending a second migration framework. Preserve the short authority reminder in each conditional reference, since references can be retrieved independently. Source links for the PostgreSQL behavior are mostly versioned and directly useful; several SQL Server citations remain generic page names. Normalize those during a substantive refresh rather than inflating every paragraph with repeated citations.

## Pass 5 — tests, evals, and oracle validity

[verified] Exact searches across `scripts` and `evals` for this skill name, its five reference names, `indisvalid`, and `CREATE INDEX CONCURRENTLY` found no direct test or scenario. The adjacent `eng-ladder-principal-preserves-writes-in-recovery.yaml:17-40,60-70` and `production-change-gate-release-preserves-recovery.yaml:22-46,68-77` use meaningful supplied-state examples: accepted-write reconciliation, per-stage recovery, retired-consumer compatibility, and separate execution authority. They pin `eng-ladder` and `production-change-gate`, respectively. Their success cannot be attributed to loading this skill.

`evals/graders.py:114-138` checks exact expected field values and duplicate/missing fields; `evals/test_graders.py:137-168` exercises those rejection paths. That is stronger than checking for reassuring keywords, but it grades a supplied decision packet, not a real database interleaving, transaction cleanup, or restoration. The caller also reproduced the extra-prose weakness in this shared grader; see EL-01 in the [eng-ladder report](group-02-eng-ladder.md). The scenarios also reveal the correct options in their closed answer vocabulary, so passing them would not establish open-ended migration planning competence.

[verified: centralized execution] The root's centralized offline run passed 1,470 tests and 2,690 subtests with 19 skips; 192 scenario specifications and 737 expectations validated. This reviewer did not repeat the suite. These results support repository structure and the existing oracles, while direct database-skill behavior remains untested. Live model trials and actual engine rehearsals require a separately scoped verification task.

## Pass 6 — adversarial walkthrough and findings

These are static counterexamples and contract comparisons, not observed model failures:

| Input or failure | Required conclusion | Existing protection or residual gap |
|---|---|---|
| `SELECT` invokes `nextval`, a volatile function, or a session advisory lock | Classify actual effects; do not equate the statement keyword with read-only authority | `query-plan-safety.md:12-17,28-35` supplies the qualification; no direct scenario |
| `EXPLAIN` can pre-evaluate an immutable function | Plan-only avoids ordinary executor work, not all possible function evaluation | Source nuance; no blanket execution-free claim in the skill |
| SQL Server DDL times out inside a transaction | Inspect and roll back the remaining transaction before retry; clean up the session | `sql-server-migrations.md:17-20` already requires this |
| Legacy NULL row receives an unrelated update after a `NOT VALID` constraint | The update can fail; writers must repair the NULL or backfill first | `postgres-migrations.md:41-49` covers both orders |
| Concurrent index build leaves an invalid, same-name index | Existing name or notice is insufficient evidence of successful completion | Existing cleanup guidance helps; make the acceptance checks explicit |
| Restore exits zero but recovered writes lack a validated watermark | RPO remains unverified and the verdict cannot pass | `restore-drill.md:23-26,35-39` states this |
| An old-only writer updates a row already copied during backfill | Reconcile that accepted write before cutover | General contract requires preservation; synchronization order is implicit |

### DB-R01 — Add direct behavior and discovery evidence

**Category:** recommendation / verification gap. **Priority:** Medium. **Confidence:** High. **Locations:** `SKILL.md:4-7,44-59,63-72`; adjacent scenarios and grader locations above.

**Trigger/consequence:** A change to this skill can retain green fleet tests while incorrectly authorizing analyzed mutation, calling an incomplete restore successful, or failing to load an engine reference. No existing case directly detects that regression. **Smallest improvement:** add one unhinted positive discovery case and a small supplied-evidence contract set covering plan effects, version-specific migration selection, and recovery evidence. Include a missing-engine/edition case. Use explicit decisions or a calibrated rubric, not keyword presence. **Verification:** prove each oracle rejects an intentionally wrong answer, validate the specs offline, and preserve the distinction between those fixture checks and any later budgeted native-model trials.

### DB-R02 — Make synchronization during backfill explicit

**Category:** clarity/design recommendation; no confirmed deployed defect. **Priority:** Medium. **Confidence:** High on the ambiguous sequence, medium on likely model impact. **Location:** `SKILL.md:34-36`.

**Trigger/consequence:** Copy old value A into new field B; an old-only writer changes A after that copy; enable dual-writing later; B remains stale unless a catch-up/reconciliation mechanism revisits the row. The listed phase order does not name that protection. “Switch only after verification” mitigates the risk but does not specify the invariant to verify. **Smallest improvement:** replace the sequence with a requirement to preserve/synchronize every supported write path throughout bounded backfill, then reconcile accepted writes before cutover. Leave the mechanism—single-transaction dual writes, change capture, or another evidenced approach—to the accepted design. **Verification:** a deterministic interleaving case changes an already-backfilled row and retries a partial batch; all accepted writes and supported-reader results must reconcile before switching. No real database execution is needed to expose the design counterexample; engine proof remains separate.

### DB-R03 — State concurrent-index completion and stop conditions directly

**Category:** optional operational clarity recommendation. **Priority:** Low. **Confidence:** High. **Locations:** `postgres-migrations.md:19-29,70-77`.

**Trigger/consequence:** A migration runner defaults to a transaction, a retry finds an invalid/wrong-definition same-name index, or an old snapshot keeps a build waiting. The current text asks for transaction-mode, cleanup, and runtime verification, but leaves their concrete acceptance conditions to the reader. **Smallest improvement:** in the existing checklist, explicitly require execution outside a transaction block, matching index identity/definition plus validity after completion, and an agreed total duration/DBA cancellation bound. State that `IF NOT EXISTS` is not evidence of equivalence or success. Preserve cleanup limited to the failed attempt's index. **Verification:** review a supplied transaction-wrapped plan, an invalid-index retry, and a stalled-build packet; reject each until its missing condition is resolved. A later isolated engine rehearsal should prove cancellation and catalog state for the actual migration tool.

## Sources checked and remaining limits

Primary documentation checked 2026-10-02:

- [PostgreSQL 18 ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html): Context7 and direct web retrieval for constraints, validation, and generated-column behavior.
- [PostgreSQL 18 CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html) and [progress reporting](https://www.postgresql.org/docs/18/progress-reporting.html): Context7; direct web confirmation of same-name semantics.
- [PostgreSQL client timeouts](https://www.postgresql.org/docs/18/runtime-config-client.html) and [function volatility](https://www.postgresql.org/docs/18/xfunc-volatility.html): official web retrieval. The latter confirms planning-time constant evaluation, rather than a claim that all plans execute application code.
- [SQL Server CREATE INDEX](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql), [ALTER TABLE](https://learn.microsoft.com/en-us/sql/t-sql/statements/alter-table-transact-sql), [lock-timeout cleanup](https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide#customize-the-lock-time-out), and [SET LOCK_TIMEOUT](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-lock-timeout-transact-sql): Context7 and official Microsoft web retrieval.

Target engine/edition, SQL permissions, migration connection lifecycle, production-scale lock behavior, backup completeness, restore watermarks, host enforcement, and model behavior remain `[unverified]`. GitHits source indexing did not complete within the bounded review. No source-level or runtime proof is substituted for that missing evidence.

Recipient: `/root`. Assignment complete; only this UTF-8 scratch report was written. Caller next step: reconcile the recommendations and centralized check evidence, include the report in the group-02 findings commit, and continue the parent audit. No canonical repair, live action, commit, or promotion was performed by this reviewer.

## Central verification

See [shared verification and group 02 counterexamples](verification.md) for the fresh baseline, executed controls, and evidence limits. The caller inspected each reported defect against its source before committing this group.
