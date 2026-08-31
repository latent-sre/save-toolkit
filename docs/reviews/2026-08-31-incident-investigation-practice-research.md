# incident-investigation: practice research for the advisor's turn shape and elicitation catalog

**Status:** research evidence for the human-facing `incident-investigation` skill (branch
`work/incident-investigation-companion`). Two questions: does the advisor's turn shape and ledger
match established incident-management practice, and what generic data points should an advisor ask
a responder for. All findings are `[sourced]` to public pages and repositories read on 2026-08-31;
nothing here was executed or independently verified.

## Sources

| # | Source | Read |
|---|---|---|
| S1 | Google SRE Book, "Managing Incidents" — https://sre.google/sre-book/managing-incidents/ | 2026-08-31 |
| S2 | Google SRE Workbook, "Incident Response" — https://sre.google/workbook/incident-response/ | 2026-08-31 |
| S3 | Google SRE Book, "Effective Troubleshooting" — https://sre.google/sre-book/effective-troubleshooting/ | 2026-08-31 |
| S4 | Google SRE Book, "Emergency Response" — https://sre.google/sre-book/emergency-response/ | 2026-08-31 |
| S5 | PagerDuty Incident Response, "During an Incident" — https://response.pagerduty.com/during/during_an_incident/ | 2026-08-31 |
| S6 | PagerDuty Incident Response, "Different Roles" — https://response.pagerduty.com/before/different_roles/ | 2026-08-31 |
| S7 | PagerDuty Incident Response, "Security Incident Response" — https://response.pagerduty.com/during/security_incident_response/ | 2026-08-31 |
| S8 | Netflix Dispatch, `src/dispatch/incident/models.py` (default branch) — https://github.com/Netflix/dispatch | 2026-08-31 via GitHits |
| S9 | Monzo Response, `response/core/models/{incident,action,timeline}.py` (default branch, archived project) — https://github.com/monzo/response | 2026-08-31 via GitHits |

## Question 1 — does the turn shape and ledger match practice?

| Advisor element (skill body) | What practice says | Source | Verdict |
|---|---|---|---|
| Ledger carried every turn (Discoveries · Actions needed · Decisions · Unknowns) | "Keep a working record of debugging and mitigation as you go" is one of four core principles; case studies kept "a working document to collect notes" with actions, owners, timestamps | S2 | matches |
| Finding first; first screen is what the responder acts on | The live incident state document keeps "the most important information at the top"; maintaining it is the commander's "most important responsibility" | S1 | matches |
| Decisions line with who asked · who decided · UTC | The Scribe "documents the timeline of an incident as it progresses and makes sure all important decisions and data are captured for later review"; OSS tools store decisions as timestamped timeline events (`TimelineEvent.timestamp/text/event_type`), not as a separate field | S6, S9 | matches; the UTC stamp is load-bearing, which is exactly the slot both E5 runs left as "now" |
| "Do this now" as item 2, mitigation before cause | "Stopping the bleeding should be your first priority"; "make the system work as well as it can under the circumstances"; "Encourage a mitigation-first response" | S3, S2 | matches |
| The advisor never executes; the release owner applies | The Ops Lead is "the only group modifying the system during an incident"; the IC is "NOT a resolver"; SMEs "announce all suggestions for resolution to the Incident Commander" and execute only on direction | S1, S6, S5 | matches — the advisor sits where a SME/scribe sits, never where Ops sits |
| "The call": declare / page, with the observable trigger and a clock time | "Declare incidents early and often"; Google's declare criteria: a second team is needed, the outage is customer-visible, or the issue is unsolved after an hour of analysis | S2, S1 | matches; the three Google criteria are a good **generic default** when no runbook supplies a threshold |
| Suspected compromise: stop, preserve, escalate to the human security owner; never restart or redeploy | "do not delete or terminate if you can help it, as we'll need to do forensics"; page an IC "at the earliest possible opportunity"; the security team is always included | S7 | matches |
| Onset as a bound, not the page time | Monzo separates `report_time` from `start_time`; Dispatch separates `reported_at`, `stable_at`, `closed_at` | S9, S8 | matches; practice tooling encodes report ≠ onset ≠ stable ≠ closed |
| Closeout packet: resolved time + recovery criterion met | Dispatch's `stable_at` (mitigated) is distinct from `closed_at`; the advisor's "recovery criterion met" is the `stable_at` moment | S8 | matches |
| Actions needed: what · owner · urgency · artifact | Monzo `Action`: details, user (owner), due_date, priority, done; Dispatch tasks carry assignees and overdue reminders | S9, S8 | matches; **due date** is the one common field the ledger lacks |
| "A card that names a cause is a hypothesis to test" | Pitfalls: "latching on to causes of past problems", mistaking correlation for causation | S3 | matches |
| Steady the responder ("Three things, in order") | "First of all, don't panic! You aren't alone"; "pull in more people" when overwhelmed | S4 | matches |
| Mid-incident handover gets the first screen and ledger | Handoffs need explicit verbal confirmation — "You're now the incident commander, okay?" — and a "firm acknowledgment" before leaving; teams rotated IC every four hours | S1, S2 | **gap**: the body has no acknowledgment step |
| (absent) periodic status updates | Liaisons post updates "roughly every 30 minutes"; Dispatch has tactical and executive report reminders | S5, S8 | **gap**: the turn shape has no "next update due at" slot; comms cadence is `incident-command`'s lane, but the advisor should surface when one falls due |

Net: the shape is the practitioners' shape — a scribe's running record plus a mitigation-first
advisor. Two generic additions are supported by the sources: an acknowledgment step on handover,
and a "next update due" slot in the call. One field addition: a due date on actions.

## Question 2 — generic elicitation catalog (what to ask the responder for)

Platform-neutral data points, in the order practice gathers them. Each ask still carries what the
command does and what a healthy/unhealthy result looks like (the skill's CLI-fluency rule).

| Phase | Ask for | Why | Source |
|---|---|---|---|
| Report | The expected behaviour, the actual behaviour, and how to reproduce it | The definition of an effective problem report | S3 |
| Report | What fired (exact alert or probe), when it fired, and the evaluation window | Report time is not onset; both are tracked separately in tooling | S9, S8 |
| Triage | User-visible impact ("What impact is this having?"), share of users or traffic, whether it is still happening and its trend | Severity assignment precedes diagnosis; stabilise first | S9, S3 |
| Triage | Who owns the service and who is on call for it | Roles and contact lists prepared beforehand "save critical time" | S2 |
| Examine | Metrics as time series (latency, traffic, errors, saturation) | "Graphing time-series … can be an effective way to understand the behavior" | S3 |
| Examine | Logs and request traces for one failing request across services | Request tracing shows "how a distributed system is working" | S3 |
| Examine | Current state exposed by the service (recent requests, error rates, latency histograms) | Server endpoints exposing recent RPCs and histograms | S3 |
| Examine | What changed — deploys, config, flags, traffic shifts, dependency changes — with times | "Recent changes to a system can be a productive place to start" | S3 |
| Diagnose | Which single observation would eliminate each candidate cause | Hypothesis testing on the system, not on stories; avoid correlation-as-cause | S3 |
| Mitigate | The reversible action, its rollback, and the signal that proves recovery | Mitigation-first; `stable_at` is a measured state, not a feeling | S2, S8 |
| Compromise | Preserve first: images/dumps, the attacker timeline, what data was reachable; do not terminate | Forensics needs the instance; page IC and security | S7 |
| Handover | Explicit acknowledgment from the receiver | "Firm acknowledgment" before leaving | S1 |

## What is generic and what is a fill-in

Everything in the two tables above is platform- and organisation-neutral. The organisation-specific
layer the advisor reads at runtime is small: the knowledge-repository layout, the escalation path
and severity scale (from the service card or the org's rubric), the platform lanes, and the update
cadence. That is the profile the protocol body should point at, not restate.

## Limits

`[sourced]` summaries were produced from fetched pages and indexed source; quotations are short
and verbatim where marked, paraphrase elsewhere. No claim here was executed or measured. Monzo
Response is an archived project; its model is cited as a design reference, not as a maintained
tool. Atlassian's incident handbook was attempted and returned only navigation content, so it is not
cited.
