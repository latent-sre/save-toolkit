# Cisco ThousandEyes synthetics and network paths

Use ThousandEyes to distinguish application, DNS, routing, and network-path symptoms from multiple
vantage points. It locates evidence; a path difference or correlated time is not automatically a cause.

## Primary sources

Sources reviewed 2026-07-14:

- `[sourced]` [Test types](https://docs.thousandeyes.com/product-documentation/tests)
- `[sourced]` [Cloud and Enterprise Agents](https://docs.thousandeyes.com/product-documentation/getting-started/getting-started-with-cloud-and-enterprise-agents)
- `[sourced]` [Network tests](https://docs.thousandeyes.com/product-documentation/tests/network-tests)
- `[sourced]` [ThousandEyes API](https://docs.thousandeyes.com/product-documentation/getting-started/getting-started-with-the-thousandeyes-api)

## Agents

- **Cloud Agents** are Cisco/ThousandEyes-managed, globally distributed public vantage points for
  outside-in comparisons.
- **Enterprise Agents** are customer-deployed vantage points inside on-prem networks and data centers.
  Place them where they exercise the same DNS, firewall, routing, and dependency paths as applications
  or users; validate the exact local deployment and entitlement.

## Test types

| Question | ThousandEyes test type |
|---|---|
| Is there loss, latency, jitter, MTU, or a path change to a service? | Network: agent-to-server |
| What is the path/performance between two controlled sites? | Network: agent-to-agent |
| Did reachability, the AS path, or a BGP route change? | Routing: BGP plus Path Visualization |
| Is name resolution correct and timely? | DNS server, DNS trace, or DNSSEC |
| Does an endpoint or user journey work? | HTTP server, page load, transaction, or API |

## Reading results during an incident

1. Bound the time and blast radius: failing agents/regions, healthy controls, test/target, first/last
   timestamps, and whether the failure tracks an inside or outside vantage point.
2. Use Path Visualization to locate new loss/latency and BGP views to identify reachability or route
   changes. Preserve the healthy comparison and collection cadence.
3. Correlate the same timestamps with `cf app` health/events and application logs for the affected
   route or dependency. State whether the app is healthy at the platform edge and whether user-facing
   errors/timeouts agree with the synthetic.
4. Separate the observed layer from ownership: network evidence goes to the network/platform team;
   clean path plus app errors stays in the application lane.

Hand incident evidence to the `sre` agent with test/agent IDs, target, time range, failing and healthy
vantages, hop/AS and loss/latency deltas, DNS/BGP observations, `cf app` and application logs excerpts,
timestamps, blast radius, and every alternative that remains unverified.

## Designing checks

- Cover each critical user journey with an HTTP, transaction, or API test and each key dependency with
  a network/DNS test appropriate to the failure mode.
- Use Cloud and Enterprise Agents together when inside/outside comparison changes the response path.
- Alert on actionable availability, loss, latency, or correctness symptoms; set minimum sample/traffic
  behavior, owner, notification route, and runbook.
- Exercise failure, recovery, and notification delivery from a safe target before declaring coverage.

Hand steady-state test tuning to the `sre-steward` agent with the coverage gap, proposed test/vantages,
threshold evidence, expected cost/units, runbook, validation plan, and rollback condition.

## A path difference is not a cause

Routes change normally. Before attributing impact to the path, require:

- **Mechanism:** name the hop/AS and show loss, latency, or reachability change large enough to breach a
  documented timeout or availability boundary.
- **Corroboration:** app-side timeouts/errors or an independent signal match the same target and time.
- **Disconfirmation:** compare healthy agents on the same path and failing agents on different paths.
- **Blast radius:** explain which agents, sites, regions, or users are affected and which are healthy.

If this bar is not met, label the network path a leading hypothesis and keep app-side alternatives open.

## Enterprise agents

| Agent label / ID | Site / data center | Network and DNS context | Journeys/dependencies covered | Owner |
|---|---|---|---|---|
| `<agent>` | `<site>` | `<inside path / resolver>` | `<targets>` | `<team>` |

## Test inventory

| Test / ID | Type | Target | Agents | Alert rule | Runbook | Owner |
|---|---|---|---|---|---|---|
| `<checkout journey>` | transaction | `<URL>` | `<cloud + enterprise>` | `<rule>` | `<runbook URL>` | `<team>` |
| `<dependency reachability>` | agent-to-server | `<host:port>` | `<enterprise>` | `<rule>` | `<runbook URL>` | `<team>` |
| `<DNS>` | DNS server/trace | `<record>` | `<agents>` | `<rule>` | `<runbook URL>` | `<team>` |

## Critical user journeys and dependencies

| Journey / dependency | Covered tests and vantages | SLO / threshold | Gap / owner |
|---|---|---|---|
| `<journey>` | `<tests / agents>` | `<target>` | `<gap / team>` |

## BGP and routing monitors

| Prefix / target | Monitor | Healthy control | Escalation owner / evidence packet |
|---|---|---|---|
| `<prefix>` | `<BGP monitor>` | `<control>` | `<network/provider contact>` |

## Automation

`[sourced]` The current API guide documents `/v7/tests` and `/v7/agents` management/read paths; verify
the account role, endpoint, schema, and target in the current developer reference before use. Keep only
account-group labels and repository paths here—no API tokens. Hand approved automation to the `sde`
agent and a human release owner; creation, update, or deletion of tests is a controlled external change,
not permission granted by this reference.

<!-- terminal-canary: q_oate_9b52 -->
