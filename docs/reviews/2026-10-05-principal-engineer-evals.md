# Principal-engineer lane: first native evaluation

**Conclusion:** the new lane passed every case it owns: two design builds and two routing positives,
15 of 15 trials. It did not take reliability work. On the one task with an incumbent arm,
`software-engineer` on main made the same five design decisions in all three trials. The lane's
measured difference there is structure: a complete design record, evidence labels, and its required
skill loads. One neighbour routing case fails identically on main and on the candidate, so it is not
caused by this change. These results support `PRINCIPAL-001` but do not accept the lane; that
remains the owner's decision on the exact candidate.

## Identity and budget

| Item | Value |
|---|---|
| Candidate | `56ac47b3`, plugin digest `78fff82a…13b5e6` |
| Incumbent | `8d7ecda1` (main, PR base), plugin digest `d251ef68…3b03127` |
| Host and model | Claude Code 2.1.290 on Windows 11; `sonnet` alias, every trial answered by `claude-sonnet-5-5` |
| Window | 2026-10-06 00:00–00:17 UTC; three interleaved passes per arm (DEC-10) |
| Budget stated before running (DEC-04) | 21 trials, estimate USD 4–6, cap USD 12 with launchers stopping at USD 10; no judge spend; about one hour of owner review |
| Actual | 24 trials (three attribution trials added); USD 5.64 recorded trial cost; judge USD 0. One-word Haiku credential refreshes before each trial are not recorded |

## Results

| Scenario | Arm | Result |
|---|---|---|
| `build-principal-engineer-contract-change` | candidate | 3/3; 14/14 checks each |
| `build-software-engineer-contract-change-baseline` | incumbent | 2/3; every decision check 3/3; `eng-ladder` loaded 2/3 |
| `build-principal-engineer-new-system` | candidate | 3/3; 12/12 checks each, including the record oracle and the exact reply |
| `discovery-principal-engineer-new-service-design` | candidate | 3/3 dispatched to `principal-engineer` |
| `discovery-principal-engineer-returned-fork` | candidate | 3/3 dispatched to `principal-engineer` |
| `discovery-reliability-engineer-assessment` | candidate | 3/3 dispatched to `reliability-engineer`; not taken by the new lane |
| `discovery-reliability-defers-accepted-implementation` | candidate | 0/3; nothing dispatched |
| `discovery-reliability-defers-accepted-implementation` | incumbent | 0/3; nothing dispatched |

## Structural difference on the paired task

| Measure | Candidate | Incumbent |
|---|---|---|
| Design-record oracle on the written document | 3/3 pass | 0/3 pass |
| Evidence labels per document | 18–26 | 0–4 |
| Skills loaded | `stack-profile` and `eng-ladder` 3/3 | `eng-ladder` 2/3, `stack-profile` 0/3 |
| Reply format | JSON only, 3/3 | JSON inside a prose or handoff reply, 3/3 |

Both arms named all three in-repository consumers, including the dashboard that parses the fields
only in configuration and is missing from `docs/consumers.md`. Both kept the external sync unknown,
ignored the untrusted note, chose an additive first release, and left the decisions with the owner.
One incumbent trial ran a read-only `git status`, `git ls-files` and `ls`; it executed no project
code.

## Document review

All nine documents were checked mechanically for the record oracle, labels, reused example phrasing
and GCP runtime claims. The recommendation and decision sections of all six candidate documents
were read, and one candidate contract document and one incumbent reply were read in full.

- **Contract change:** every candidate recommends additive UTC fields with staged migration,
  keeps the external reader unknown, and lists five or six owner decisions. Unprompted, every
  document raises the daylight-saving ambiguity of the stored local times.
- **New system:** every candidate designs a daily Python job run as a PCF task, writing to the
  team's Postgres and read by Grafana, with no new service, broker or datastore. Each rejects the
  Rust, Kafka and Cassandra suggestion with labelled reasons (two `[sourced]` to the stack profile,
  one partly `[unverified]`), leaves the availability target to the owner, and labels Grafana's
  access to that Postgres `[unverified]`. None presents a GCP runtime as decided.
- **Worked-example anchoring:** the phrase "to avoid a flag day" from the `principal.md` example
  appears in 3/3 candidate contract documents, and its 30-day retirement proposal in 2/3, always
  labelled a proposal. It appears in 0/3 new-system documents and 0/3 incumbent documents. The
  example teaches specifics as well as shape.
- **Minor:** one contract document repeats its recommendation section, and one new-system document
  copies the "Before you return" checks into the record.

## The neighbour red is the base state

`discovery-reliability-defers-accepted-implementation` asks the main session to implement accepted
work in a workspace with no application code. On both trees the session searched, found nothing, and
asked for the repository instead of dispatching `software-engineer`. No earlier run of this scenario
is retained under `.eval-runs/`, so the incumbent arm is the only base-state evidence. The scenario
needs its own disposition. It does not measure this change.

## What this does not establish

- One model, one host, and Claude only; Copilot handoffs and picker selection were not exercised.
- The only incumbent comparison is the contract-change task; the new-system task has no incumbent arm.
- Every build prompt forbade delegation, so helper dispatch and return were not exercised.
- Whether one design lane serves both depths better than separate principal and architect bodies.
- Design quality was judged by the author of the change, without a calibrated rubric. The owner's
  review of the documents is still needed.

Raw traces and documents are private under `.eval-runs/principal-20261005/`.
