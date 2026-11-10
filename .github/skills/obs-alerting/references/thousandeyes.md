# Cisco ThousandEyes synthetics and network paths

Use application, DNS, BGP and path evidence under the [parent access boundaries](../SKILL.md).
A changed path or matching timestamp ranks hypotheses; it does not prove cause. Promote one only
with a disprovable mechanism, corroboration from an independent signal class, a disconfirmation
test, and the path's blast radius; below that bar, call it a leading hypothesis and keep the
alternatives open.

## Reading results during an incident

- Bind test/agent IDs, target, first/last times and collection cadence; compare failing and healthy
  regions/vantages, including inside versus outside.
- Preserve healthy controls, hop/AS deltas and DNS observations.
- Compare the same window with `cf app`, events and app logs for the route/dependency. Keep
  platform-edge health separate from user-facing errors and synthetic results.
- Send network evidence to network/platform owners; a clean path with app errors remains an app
  investigation. Observed layer does not prove fault ownership.

Return these observations, scope and unresolved alternatives to the responder or dispatched SRE helper.

## Designing checks

Exercise failure, recovery, and delivery from a safe target before declaring coverage. Hand
steady-state tuning to the `observability-engineer` agent with the coverage gap, proposed test and
vantages, threshold evidence, expected cost, runbook, validation plan, and rollback condition.

Record each test's ID, type, target, agents, alert rule, runbook and owner, Enterprise Agent
placement and BGP monitors in the team's own inventory.

## Automation

For `/v7/tests` and `/v7/agents`, verify account role, endpoint/schema and target before use.
Record account-group labels and repository paths, never tokens. Test creation/update/deletion is
controlled external work for `software-engineer` and a human release owner; this reference grants
no execution authority.
