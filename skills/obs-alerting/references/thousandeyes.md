# Cisco ThousandEyes synthetics and network paths

Use application, DNS, BGP and path evidence under the [parent causal and access boundaries](../SKILL.md).
A changed path or matching timestamp alone establishes no cause.

## Reading results during an incident

- Bind test/agent IDs, target, first/last times and collection cadence; compare failing and healthy
  regions/vantages, including inside versus outside.
- Use Path Visualization for hop loss/latency and BGP for reachability/route changes. Preserve
  healthy controls, hop/AS deltas and DNS observations.
- Compare the same window with `cf app`, events and app logs for the route/dependency. Keep
  platform-edge health separate from user-facing errors and synthetic results.
- Send network evidence to network/platform owners; a clean path with app errors remains an app
  investigation. Observed layer does not prove fault ownership.

Return these observations, scope and unresolved alternatives to the responder or dispatched SRE helper.

## Designing checks

Pair Cloud and Enterprise Agents when the inside-versus-outside comparison changes the response
path. Exercise failure, recovery, and delivery from a safe target before declaring coverage. Hand
steady-state tuning to the `observability-engineer` agent with the coverage gap, proposed test and
vantages, threshold evidence, expected cost, runbook, validation plan, and rollback condition.

## Test inventory

| Test / ID | Type | Target | Agents | Alert rule | Runbook | Owner |
|---|---|---|---|---|---|---|
| `<checkout journey>` | transaction | `<URL>` | `<cloud + enterprise>` | `<rule>` | `<runbook URL>` | `<team>` |
| `<dependency reachability>` | agent-to-server | `<host:port>` | `<enterprise>` | `<rule>` | `<runbook URL>` | `<team>` |
| `<DNS>` | DNS server/trace | `<record>` | `<agents>` | `<rule>` | `<runbook URL>` | `<team>` |

Record Enterprise Agent placement (site, resolver, inside path, journeys covered, owner) and BGP
monitors (prefix, healthy control, escalation owner) beside this table when they exist.

## Automation

For `/v7/tests` and `/v7/agents`, verify account role, endpoint/schema and target before use.
Record account-group labels and repository paths, never tokens. Test creation/update/deletion is
controlled external work for `software-engineer` and a human release owner; this reference grants
no execution authority.
