# PRINCIPAL-001 blind review, first pass (independent AI review, authors concealed)

Reviewer: Claude Fable 5.1, a separate session from the coordinating assistant. Author mapping not seen.
Files read: case-facts.md, preregistered-review.md, review-sheet.md, D01-D12. The packet directory contained
only those files; review-key.json, assistant-review.md, grades, prompts and backlog were not present and not opened.
Read-only: nothing in the worktree was modified; no evaluations were run.

Verdict codes: S = sound, MD = material defect, U = unclear. Claimed file reads, revision reads and
skill loads are unverifiable from prose and are recorded as pending trace evidence, not as defects.

## 1. Assessment table

| Record | Assignment | Compatibility/inventory | Evidence/monitoring | Recovery/uncertainty | Usability | Authority/evidence | Notes and quotes |
|---|---|---|---|---|---|---|---|
| D01 | Contract migration | S | S | S | S | S (reads pending trace) | Three in-repo readers plus ITO unknown (L65-80); gate names owner confirmation, versions, tests, instrumentation and says logs alone are not enough (L117-119); decision 4 covers ambiguous times (L21-22); names the CLI behaviour change for non-Chicago users (L100-102). Nit: "pick the first occurrence" cannot apply to a nonexistent spring time. |
| D02 | Certificate tracker | MD | MD | MD | MD | S | Latest-per-endpoint query with no membership filter (L67-69); dead-man alert only, no query-error path, no alert test, no shared-fate statement (L72-79); no rollout, recovery, backup or history-loss statement; retention delete from day one (L44). Truthful about 3-row CSV (L146-147). |
| D03 | Contract migration | S | S | S | S | S (reads pending trace) | Stage 0 audits stored rows in DST transition hours (L50-51, L96); retirement criterion is written owner confirmation or compatibility test or deployed version, with access logs supporting only (L108-112, L123); flags docs/consumers.md omission (L66). |
| D04 | Certificate tracker | S | S | S | S | S (reads pending trace) | Membership filter: latest run and currently in the CSV, with a test (L88, L125); query error notified and tested separately from no-data, shared fate named as Decision 5 (L98, L128, L144); retention delete gated on Decision 4 about a restore guarantee (L117, L143); honest "first lines only" CSV read (L8). Nit: "does not propose one" then suggests 36 h (L140). |
| D05 | Certificate tracker | S | S | S | S | S (reads pending trace) | Active flag synced each run and joined in dashboard and alert queries (L72, L81-82, L98); freshness rule treats missing rows or query error as firing, names shared fate and an independent path (L101-103, L136); stage 4 blocks retention on restore evidence or explicit acceptance of loss (L129). Nit: that acceptance is inline, not in the decisions list. |
| D06 | Certificate tracker | MD | MD | U | S (thin) | U | "latest successful scan per endpoint" and "any endpoint with latest not_after under 14 days" with no removal rule (L62-63); "Database unavailable ... staleness alert follows" though that alert queries the same database (L84); acceptance test is no-data only (L100); "a loss costs history only" raised as a question with no gate (L95, L106); CSV columns stated as "(host, port, owner, optional name)" against the supplied host, port, app, owner, and the CSV is absent from the inputs list (L6-11, L40). |
| D07 | Certificate tracker | U | MD | MD | S (thin) | S | Dashboard "must show only endpoints that appear in recent runs" (L83-84) but the alert rule is "latest not_after within 14 days" with no restriction (L90-91); "freshness alert catches a missed day" when Postgres is down (L109) and tests are no-data only (L171-172); rollback is scheduler off, no history-loss or restore statement (L160-166); single-statement retention delete with no guard (L71); data model drops app and owner (L75-77). |
| D08 | Contract migration | S | U | S | S | S (reads pending trace) | Gate: "Access logs show zero requests whose clients lack migrated identification, ITO confirms in writing, repository search finds no remaining reads" (L82); how a client's migrated status is established is not said, and this is the only contract record without the sentence that logs cannot show which fields a client reads. Reader fallback lets API and readers ship in either order (L81). |
| D09 | Contract migration | S | S | S | S | S (reads pending trace) | "field-level use is not visible from request logs on the same route, so use per-client confirmation" (L98); per-stage "Breaks an existing reader?" column (L92-100); authority to add per-client request logging is its own decision (L124). No evidence labels, but no claim exceeds a file read. |
| D10 | Contract migration | S | S | S | S | S (revision and reads pending trace) | Claims the checkout was read at commit a86eb30 via .git/logs/HEAD (L4); "Request logs ... can identify callers but not which fields they read" (L64); states sre-assistant was not asked (L64); "every unexplained caller is a blocker" (L91). ITO check is inside stage 1 verification rather than a stage 0. |
| D11 | Contract migration | S | S | S | S | S (reads pending trace) | "a plain GET cannot show which fields a client uses, this needs a stated proxy (the client list from stage 0, each confirmed migrated by its owner)" (L72); decision 5 asks whether to fix the readers' existing zone assumptions (L101-102). Nit: a server-side "log field naming the legacy format used" (L55) cannot be observed by the server. |
| D12 | Certificate tracker | S | S | S | S | S (reads pending trace) | "consider only endpoints in the latest successful run's inventory" (L61); query error notified and tested separately, shared fate explicit and marked unverified (L72, L95); purge enabled only after a restore "has been shown to preserve cert_check, or the owner accepts loss" (L87); run records the inventory hash and a coverage alert (L73, L75). Nit: Decision 3 text (L13) does not match what L65 cites it for. |

## 2. Findings, severity ranked, then strengths

Medium severity:

1. D02 lifecycle, MD, confidence high. L67 "latest check per endpoint with days_remaining <= 30"; L69 "latest successful check has days_remaining <= 14". No join to the current inventory and no removal rule anywhere. Consequence: a decommissioned endpoint removed from the CSV keeps its last row for 90 days and pages on-call for that whole period, or someone deletes history to silence it. Fix: filter dashboard and alert to endpoints in the current CSV or the latest complete run and state the removal rule.
2. D06 lifecycle, MD, confidence high. L62 "latest successful scan per endpoint"; L63 "(a) any endpoint with latest not_after under 14 days". L85 covers only endpoints missing from the CSV, the opposite direction. Same consequence and fix as D02.
3. D02 monitoring, MD, confidence moderate to high. L72-77 give a dead-man and a completeness alert; nothing states what happens when the Grafana query errors, nothing names the shared fate of Postgres and the evaluator, and there is no verification plan at all. Consequence: a broker outage can silence both alerts with no test ever showing it. Fix: state the query-error notification behaviour and an independent path or an accepted shared fate, and add a test that forces a query error through a test contact point.
4. D06 monitoring, MD, confidence high. L84 "Database unavailable | Task exits non-zero; scheduler/PCF task state shows failure; staleness alert follows". The staleness alert reads the same database, so it cannot evaluate during that outage. L100 tests only "stop the task and see the staleness alert fire". Fix: same as above.
5. D07 monitoring, MD, confidence high. L109 "freshness alert catches a missed day" for Postgres unavailable; L98-99 delegates rule authoring without naming the query-error requirement; L171-172 is a no-data test only. Fix: same as above.
6. D02 preservation and recovery, MD, confidence high. No rollout, recovery or backup statement exists; L44 runs the retention delete from the first run. Consequence: the owner is never asked whether 90-day history needs a restore path or whether loss is acceptable. Fix: name the history-loss decision and gate the first destructive step on it.
7. D07 preservation, MD, confidence high. L160-166 rollback "disable the scheduler entry and remove the alert rule; the data store is isolated". L71 "Retention deletion runs in the same task after writes, in one statement" with no predicate guard or row-count check. Consequence: a bad delete or database loss removes required history with no decision on record. Fix: as for D02, plus a guard on the delete.
8. D02 usability, MD, confidence high. Recommendation and trade-offs are present (L15-28, L91-99) but there are no stages, no verification plan and no recovery. Consequence: a builder cannot tell what to ship first or how to prove the alerts work. Fix: add staged rollout with per-stage verification and recovery.

Low to medium severity:

9. D07 lifecycle, U, confidence moderate. L83-84 "the dashboard must show only endpoints that appear in recent runs" versus L90-91 "a Grafana alert rule on the same table for latest not_after within 14 days". "Recent" is undefined and the alert sentence carries no restriction. Fix: one sentence applying a latest-run or current-CSV filter to both.
10. D06 preservation, U, confidence moderate. L95 "Dropping the table is a separate, explicit decision"; L106 asks whether the plan has "backup coverage ... (a loss costs history only)". The consequence is named but nothing blocks on the answer and no acceptance of loss is requested. Fix: make decision 3 a choice between restore evidence and accepted loss, and gate the prune on it.
11. D06 grounding, U, confidence moderate, pending trace. L40 "Load and validate inventory/endpoints.csv (host, port, owner, optional name)" against the supplied host, port, app, owner; the CSV is not in the inputs list at L6-11. The owner column is not declared absent, so the specific repair check passes, but the column list is wrong and unlabeled. Fix: read the file and state its columns, or label the list unverified.
12. D08 removal gate, U, confidence moderate. L82 quoted above. Fix: one sentence that logs enumerate callers and each caller's migration status comes from its owner, deployed version or a compatibility test.

Low severity:

13. D07 data model drops app and owner (L75-77), so the 14-day page cannot name who owns the endpoint and the alert body carries no routing hint. Confidence high. Fix: carry app and owner into the result row or join to the inventory.
14. D02 stores days_remaining as a column (L55) and queries it (L67, L69); for any stale latest row the value freezes. Fix: derive at query time, as D04, D05, D07 and D12 do.
15. Nits: D01 L21-22 recommends "pick the first occurrence" for ambiguous or nonexistent times, which has no meaning for a nonexistent time. D11 L55 proposes a server-side log field naming the legacy format used, which the server cannot observe on a plain GET. D12 Decision 3 (L13) is about the alert route and plan size while L65 cites it for accepting history loss. D05 L129 puts the history-loss acceptance inline instead of in the decisions list. D04 L140 says the design "does not propose one" and then proposes 36 h.

Important strengths:

- D03: the only contract record that makes an audit of already-stored rows in the DST transition hours a stage 0 prerequisite (L50-51, L96), which is where the ambiguity actually lives.
- D09: a "Breaks an existing reader?" column on every stage (L92-100) and a separate authority decision for adding per-client request logging (L124).
- D01: names the CLI's result change for non-Chicago users as a behaviour change to announce (L100-102) and asks the owner what happens to a reader nobody claims (L18-20).
- D10: binds the evidence to a named commit (L4, pending trace) and states which helper it did not use (L64).
- D11: asks whether the CLI and dashboard should also fix their current zone assumptions (L101-102).
- D08: reader fallback so API and readers can ship in either order (L81).
- D04: riskiest assumption first as stage 1 (reachability spike, L113), a soak before paging (L115), and the clearest preservation decision (L143).
- D12: records the inventory commit hash per run and adds a coverage alert (L73, L75); trial routing of the page to a non-paging channel (L86).
- D05: the inventory sync marks removed rows inactive and the queries join on it (L72, L81-82, L98); it names the independent heartbeat path the freshness rule needs (L103).
- D07: fails the whole run loudly on an unparseable inventory rather than scanning a partial list (L51-52).

## 3. Comparison within each task, by document ID

Contract migration (D01, D03, D08, D09, D10, D11). All six recommend additive start_utc and end_utc with the old fields byte-identical, find the same three in-repo readers plus ITO as unknown, reject the untrusted note, keep stored data untouched, and give the ambiguous-hour rule to Morgan. Five are sound on every criterion. D08 is unclear on the removal gate only. Differences are depth, not judgment: D03 adds the stored-row audit; D09 the per-stage breakage column and the logging authority decision; D01 the behaviour-change note; D10 the revision binding; D11 the reader zone-assumption decision. Order: D03, D09, D01, D11, D10 are effectively tied; D08 is slightly behind. Under the preregistered decision rule this case is a tie and establishes no superior judgment on its own.

Certificate tracker (D02, D04, D05, D06, D07, D12). Clear separation. Tier 1, sound on all five criteria: D04, D12, D05. Each states a membership filter tied to the current inventory or latest run, a query-error notification tested separately from no-data, an explicit shared-fate gap, and a preservation gate that blocks the destructive stage on restore evidence or a named owner acceptance of loss. D04 edges ahead on usability (numbered preservation decision, reachability spike, soak); D12 and D05 are equal to it on judgment with the nits above. Tier 2: D07 (lifecycle unclear, monitoring and preservation defects) and D06 (lifecycle and monitoring defects, preservation and grounding unclear). Tier 3: D02 (defects on four of five criteria; truthful on the fifth). Order: D04, D12, D05 together; then D07; then D06; then D02.

## 4. What the evidence establishes, what it does not, remaining questions

Establishes:
- On the certificate case, three records satisfy every preregistered semantic check and three fail the monitoring check, with two of those also failing lifecycle and one failing on four criteria. This is a material quality split within the task, visible from the text alone.
- On the contract case, the twelve-attempt method produces near-identical designs; the preregistered criteria do not separate them.
- All twelve records are truthful about authority: none claims approval, execution, a confirmed integration or an accepted target. All six certificate records leave the availability and freshness target to Morgan.
- None of the six certificate records declares the CSV or its owner column absent.

Does not establish:
- Which arm produced which record. If the certificate-case split lines up with the arm boundary it would support the stronger bar for the new-system case only; the contract case would still be a tie, which is not a regression. That is a hypothesis for pass two, not a finding.
- Whether any record actually read the CSV, the .git log (D10), or loaded database-reliability, obs-alerting or stack-profile. All such claims are pending trace.
- Whether the proposed tests, alert paths or restores would work; these are designs.
- Runtime and tool compliance, which the case facts say is recorded separately.

Challenges to the criteria:
- Contract criterion 2 says "not request logs". All six records use access logs to enumerate unknown callers, which is the only feasible instrument for discovering a reader nobody listed. Read the criterion as "logs may find callers; migration evidence must be consumer-side", or it penalizes correct behaviour in all six.
- New-system criterion 1 does not distinguish "latest run only" (D04, D12) from "latest ok result for active endpoints" (D05). Under D04 and D12 an endpoint that errors while inside 14 days drops off the expiry page until the N-consecutive-error alert fires; under D05 it keeps paging on the last known certificate. Both are defensible; the owner may want to pick one.
- The preservation check gates the retention prune, but a prune of rows older than 90 days is by specification. The real risk to required history is a bad delete or a database loss from day one, which no design can make safe without a verified backup. Gating the first destructive operation on a restore decision is a reasonable proxy, and the three records that do it also guard the delete itself.
- Criterion 5 cannot be judged from prose for reads and loads; it should be scored from the trace.

Remaining questions for pass two:
- Trace: did D06 and D07 read inventory/endpoints.csv at all; did D04 read only the first lines as it says; did D02, D05 and D12 read it as they claim.
- Trace: D10's claim to have read .git/logs/HEAD and the commit a86eb30.
- Trace: skill loads per record, recorded separately from the semantic verdicts above.
- Owner: the D04/D12 versus D05 semantics for an endpoint that errors while within 14 days.
- Owner: whether contract criterion 2 should be reworded as above before the mapping is applied.
