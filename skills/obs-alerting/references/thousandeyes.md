# Cisco ThousandEyes synthetics and network paths

ThousandEyes distinguishes application, DNS, routing, and network-path symptoms from multiple
vantage points. It locates evidence; a path difference or a correlated time is not a cause, and the
parent skill's bar for asserting cause applies before any path is blamed.

Sources reviewed 2026-07-14: `[sourced]` [test types](https://docs.thousandeyes.com/product-documentation/tests),
[agents](https://docs.thousandeyes.com/product-documentation/getting-started/getting-started-with-cloud-and-enterprise-agents),
[network tests](https://docs.thousandeyes.com/product-documentation/tests/network-tests),
[API](https://docs.thousandeyes.com/product-documentation/getting-started/getting-started-with-the-thousandeyes-api).

## Reading results during an incident

1. Bound the time and blast radius: failing agents and regions, healthy controls, test and target,
   first and last timestamps, and whether the failure tracks an inside or an outside vantage point.
2. Path Visualization locates new loss or latency by hop; the BGP view shows reachability and route
   changes. Keep the healthy comparison and the collection cadence.
3. Correlate the same timestamps with `cf app` health and events and the application logs for the
   affected route or dependency. Say whether the app is healthy at the platform edge and whether
   user-facing errors agree with the synthetic.
4. Separate the observed layer from ownership: network evidence goes to the network or platform
   team; a clean path with app errors stays in the application lane.

Hand incident evidence to the responder, or the `sre-assistant` slice they dispatched, with test and
agent IDs, target, time range, failing and healthy vantages, hop or AS and loss or latency deltas, DNS
and BGP observations, `cf app` and log excerpts, timestamps, blast radius, and every alternative that
remains unverified.

## Designing checks

Cover each critical user journey with an HTTP, transaction, or API test and each key dependency with
a network or DNS test matched to its failure mode; pair Cloud and Enterprise Agents when the
inside-versus-outside comparison changes the response path. Alert on actionable availability, loss,
latency, or correctness symptoms with minimum-sample behaviour, owner, notification route, and
runbook set, and exercise failure, recovery, and delivery from a safe target before declaring
coverage. Hand steady-state tuning to the `observability-engineer` agent with the coverage gap,
proposed test and vantages, threshold evidence, expected cost, runbook, validation plan, and
rollback condition.

## Test inventory

| Test / ID | Type | Target | Agents | Alert rule | Runbook | Owner |
|---|---|---|---|---|---|---|
| `<checkout journey>` | transaction | `<URL>` | `<cloud + enterprise>` | `<rule>` | `<runbook URL>` | `<team>` |
| `<dependency reachability>` | agent-to-server | `<host:port>` | `<enterprise>` | `<rule>` | `<runbook URL>` | `<team>` |
| `<DNS>` | DNS server/trace | `<record>` | `<agents>` | `<rule>` | `<runbook URL>` | `<team>` |

Record Enterprise Agent placement (site, resolver, inside path, journeys covered, owner) and BGP
monitors (prefix, healthy control, escalation owner) beside this table when they exist.

## Automation

`[sourced]` The current API guide documents `/v7/tests` and `/v7/agents`; verify account role,
endpoint, schema, and target in the current developer reference before use. Keep only account-group
labels and repository paths here, never tokens. Creating, updating, or deleting tests is a controlled
external change for the `software-engineer` agent and a human release owner, not permission granted by
this reference.
