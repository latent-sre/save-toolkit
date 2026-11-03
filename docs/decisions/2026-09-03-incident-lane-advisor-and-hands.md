# ADR: The incident lane is an advisor and a pair of hands

- **Date:** 2026-09-03
- **Status:** Accepted 2026-09-03
- **Decision owner:** Save Toolkit maintainers
- **Roadmap item:** closes ROUTE-005 (the incumbent it asked the owner to decide on is archived)
- **Supersedes:** the sustained-response design in `agents/sre.md` and the `investigation-depth`
  mode ladder, both parked under [`archive/incident-autonomy/`](../../archive/incident-autonomy/README.md)
- **Does not supersede:**
  [`2026-08-24-sre-operational-context-contract.md`](2026-08-24-sre-operational-context-contract.md)
  (the evidence-label and operational-context rules stand; the agent that carries them is now
  `sre-assistant`)

## Context

The fleet serves a human SRE who owns the incident. Two components claimed the same job. The
`incident-investigation` skill advises the responder in their own session. The `sre` agent's
description also carried the responder's phrases ("why is X failing", "investigate this", "triage
this alert"), so a plain ask routed to a dispatched agent that returned a slice instead of loading
the advisor, and the routing corpus encoded that as correct.

Behind the agent sat `investigation-depth`, a 29.7 KB mode ladder that no human ever loaded: its
triggers were machinery phrases, and every rule it carried was already in the advisor, in the
agent body, or in `pcf-ops`. The agent also carried a sustained-response mode that owned the
incident record through recovery with an `incident-state/v2` JSON contract. That design is the
skeleton of an agent re-invoked on its own record without a human holding the thread, and nothing
in the repository can drive it: there is no trigger loop, and the agent cannot read the team's
signals in Splunk, Wavefront, Grafana, or Apps Manager.

## Decision

- The advisor owns a responder's own troubleshooting. The agent is a second set of hands: one
  bounded, read-only evidence slice, dispatched by the human or by the advisor, returned with
  evidence labels and a mitigation stance, then it stops.
- The agent is renamed `sre-assistant`; its description describes the dispatched ask and excludes
  the responder's phrasing. The read-only guard, the adapter generator, and the fleet validator
  carry the new name; the guard was proven live for it.
- `investigation-depth` and the sustained-response machinery (the recovery reference, two
  scenarios, three rubrics with 35 calibration cases, the validator's conditional-handoff rule) are
  removed from the live tree and kept byte-exact under `archive/incident-autonomy/` with restore
  patches, so a future automation effort restores rather than rebuilds. The `no_blind_retry_after_unknown`
  rubric stays live; another scenario grades with it.
- The advisor gains three sentences: the self-sustaining-mechanism pattern, shedding load as the
  reversible action for it, and the rule that two incidents in one window are not one cause.
- Two routing scenarios now expect the advisor for a responder's triage ask; a new scenario expects
  the agent for a dispatched read.

## Consequences

- Measured in [`2026-09-03-incident-lane-fold-evidence.md`](../reviews/2026-09-03-incident-lane-fold-evidence.md):
  the trimmed agent passes the guarded-triage probe 17/17 in three trials with a third fewer tokens
  than the incumbent's 18/18, and on Sonnet the four incident routing scenarios pass 3/3 each.
- A restore needs what the archive README states: a trigger loop, read paths to the signals, and a
  re-proof of the existing `sre-assistant` guard, since the restored body keeps that name. Until
  those exist the machinery is weight with no reader.
- Seven skill descriptions changed by the agent's name token only, and `eng-ladder`'s exclusion
  points at the advisor; neither had an after-run beyond the four incident scenarios.
- The catalogue is 25 skills; the agent's incident context path fell from 89 KB to 72 KB.
- Routing a responder's generic incident ask to the advisor puts pasted, attacker-controllable
  evidence in the main session, whose Bash the read-only guard does not scope and whose
  credential tripwire exempts the main loop by design (`scripts/readonly-guard.py`, "the fleet
  has no standing to gate a human's own terminal"). The advisor runs nothing and treats pastes
  as data, and the host's permission mode decides whether a Bash call needs the responder's
  approval. Extending the credential tripwire to the main loop, or scoping the advisor's turn
  with a host-specific `disallowed-tools` key, are owner calls recorded here as open.
