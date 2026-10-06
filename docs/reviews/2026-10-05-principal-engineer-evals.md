# Principal-engineer lane: native evaluation

**Conclusion:** on the final candidate `7993b130` the lane passed every case it owns: a
contract-change design, two routing positives, and, on the earlier revisions, a new-system design.
It never took reliability work. On identical bytes, `software-engineer` made the same five design
decisions, so the lane's difference is the record, not the decisions. The lane produced a complete
design record in 3/3 trials against 0/3, loaded `stack-profile` 3/3 against 0/3, and returned the
closed reply 3/3 against 0/3. The rewritten `eng-ladder` reference also raised `software-engineer`'s
evidence labelling. One neighbour routing case fails identically on main and on the candidate.
These results support `PRINCIPAL-001`; acceptance of the exact candidate remains the owner's decision.

## Identity and budget

| Item | Value |
|---|---|
| Candidate revisions | `56ac47b3` (digest `78fff82a…13b5e6`); `72f748a0` after the first review fixes (`0bdf82ef…dd253ed`); final `7993b130` after the rename and the second review's fixes (`9ace6a27…14229ec8`) |
| Incumbent | `8d7ecda1` (main, PR base), digest `d251ef68…3b03127` |
| Host and model | Claude Code 2.1.290 on Windows 11; `sonnet` alias, every trial answered by `claude-sonnet-5-5` |
| Windows (2026-10-06 UTC) | first campaign 00:00–00:17, re-measure 00:43–00:49, final 01:27–01:41; three interleaved passes per arm (DEC-10) |
| Budgets stated before running (DEC-04) | first: 21 trials, USD 4–6, cap 12; re-measure: 6 trials, USD 1.20, cap 3; final: 15 trials, USD 4.40, cap 7 |
| Actual | 45 trials, three of them attribution trials added to the first campaign; USD 10.73 recorded trial cost (5.64, 1.16, 3.94); judge USD 0. One-word Haiku credential refreshes are not recorded |

## Results

| Scenario | Arm | `56ac47b3` | `72f748a0` | `7993b130` |
|---|---|---|---|---|
| `build-principal-engineer-contract-change` | lane | 3/3 | 3/3 | 3/3 |
| `build-principal-engineer-new-system` | lane | 3/3 | 3/3 | not run |
| `build-software-engineer-contract-change-baseline` | `software-engineer`, main bytes | 2/3 | — | — |
| `build-software-engineer-contract-change-baseline` | `software-engineer`, candidate bytes | — | — | 2/3 |
| `discovery-principal-engineer-new-service-design` | candidate | 3/3 | — | 3/3 |
| `discovery-principal-engineer-returned-fork` | candidate | 3/3 | — | 3/3 |
| `discovery-reliability-engineer-assessment` | candidate; not taken by the lane | 3/3 | — | 3/3 |
| `discovery-reliability-defers-accepted-implementation` | candidate / main | 0/3 / 0/3 | — | — |

The lane's own four cases were 12/12 in the first campaign, plus 3/3 on the reliability neighbour.
Both `software-engineer` failures are the `eng-ladder` load check; every decision check passed in
every `software-engineer` trial. The final rename changes the lane's description, so its routing
cases and the reliability neighbour were re-run on `7993b130`.

## Lane versus reference

The first comparison changed the agent and the `eng-ladder` reference together, because the
incumbent read main's reference, which has no design record. The final run separates them: both
agents on identical bytes, interleaved.

| Arm, 3 trials each | Complete record (oracle) | Slots per document | Labels per document | Closed JSON reply | `stack-profile` loaded |
|---|---|---|---|---|---|
| Lane, final bytes | 3/3 | 12, 12, 12 | 17, 23, 20 | 3/3 | 3/3 |
| `software-engineer`, final bytes | 0/3 | 11, 6, 6 | 23, 8, 11 | 0/3 | 0/3 |
| `software-engineer`, main bytes | 0/3 | 7, 5, 6 | 0, 1, 4 | 0/3 | 0/3 |

- **The reference raises labelling.** It does so for an agent that loads it; trial-to-trial
  variation is large, and one `software-engineer` trial skipped `eng-ladder` and still wrote 8 labels.
- **Only the lane produced the rest.** The complete record, the `stack-profile` load and the closed
  reply came only from the lane.
- **Every arm made the same five decisions:**
  - found all three consumers, including the dashboard that parses the fields only in configuration;
  - kept the external reader unknown;
  - chose an additive first release;
  - removed the old format only on evidence;
  - left the decision with the owner.
- **The decisions did not separate the arms.** The decision fields are closed choices; only the
  consumer inventory required a search. The pair's pass rates turn on the `eng-ladder` load check,
  which is a method check, not a decision.
- Two `software-engineer` trials, one on each tree, ran a read-only `git status` and `git ls-files`;
  neither executed project code. The lane has no shell.

## Re-measure after the first review fixes

Codex's review of `1d955923` found five issues, fixed in `72f748a0`:

- **Worked example:** it labels each option, names an owner per failure mode, and regenerates the
  retired field from current data in its stage-3 recovery. Its "flag day" phrasing and 30-day
  figure are gone.
- **Failure modes slot:** it now asks for an owner.

Both lane build cases were then re-run.

| Measure, per document | `56ac47b3` | `72f748a0` |
|---|---|---|
| Checks and record oracle | 6/6 pass | 6/6 pass |
| "flag day" in contract-change documents | 3/3 | 0/3 |
| 30-day retirement proposal in contract-change documents | 2/3 | 0/3 |
| Failure-mode owner lines, contract change | 1, 0, 0 | 6, 5, 9 |
| Failure-mode owner lines, new system | 1, 2, 0 | 4, 5, 4 |
| Labels inside the contract-change Options section | 0, 4, 2 | 5, 1, 2 |

**Counting rule for owner lines:** lines in the Failure modes section containing "owned by",
"owner:" or an owner table column. The independent review's broader rule (`owner|owned by|owns`)
gives 1, 1, 0 → 6, 6, 11 and 1, 2, 1 → 5, 5, 5: the same direction.

- **The owner change worked.** Owners now appear in every document.
- **Options labelling shows no clear change** in three documents.
- **The new example's wording still travels:** "quiet period" appears in 3/3 contract-change
  documents and "day of release" in 1/3, both without a figure.

## Document review

All documents were checked mechanically for the record oracle, labels, reused example phrasing and
GCP runtime claims. The recommendation and decision sections of the six first-campaign lane
documents were read, and one lane contract document and one incumbent reply were read in full.

- **Contract change:** every lane document recommends additive UTC fields with staged migration,
  keeps the external reader unknown, and lists five or six owner decisions. Unprompted, every
  document raises the daylight-saving ambiguity of the stored local times.
- **New system:** every lane document designs a daily Python job run as a PCF task, writing to the
  team's Postgres and read by Grafana, with no new service, broker or datastore.
  - Each rejects the Rust, Kafka and Cassandra suggestion with labelled reasons: two `[sourced]` to
    the stack profile, one partly `[unverified]`.
  - Each leaves the availability target to the owner and labels Grafana's access to that Postgres
    `[unverified]`.
  - None presents a GCP runtime as decided.
- **Minor:** one contract document repeats its recommendation section, and one new-system document
  copies the "Before you return" checks into the record.

## The neighbour red is the base state

`discovery-reliability-defers-accepted-implementation` asks the main session to implement accepted
work in a workspace with no application code. On both trees the session searched, found nothing, and
asked for the repository instead of dispatching `software-engineer`. No earlier run of this scenario
is retained under `.eval-runs/`, so the incumbent arm is the only base-state evidence. The scenario
is tracked as `EVAL-013`. It does not measure this change.

## Known grader limits

Codex's adversarial review of `7993b130` found two holes, and no recorded trial exercises either.

- **The record oracle counts a slot by its name alone.** It accepts a slot with an empty section,
  an empty table cell, or a contents list.
- **The reply checks search the whole reply**, so a discarded correct JSON draft or a duplicate key
  could pass.

All 15 saved contract-change replies contain exactly one JSON object and no duplicate keys, and no
saved record leaves a slot section empty. No recorded verdict depends on either hole.

## What this does not establish

- One model, one host, and Claude only; Copilot handoffs and picker selection were not exercised.
- The new-system case has no `software-engineer` arm and was not re-run on `7993b130`.
- Every build prompt forbade delegation, so helper dispatch and return were not exercised.
- Whether one design lane serves both depths better than separate principal and architect bodies.
- Design quality was judged by the author of the change, without a calibrated rubric. The owner's
  review of the documents is still needed.

Raw traces and documents are private under `.eval-runs/principal-20261005/`.
