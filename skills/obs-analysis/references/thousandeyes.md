# Cisco ThousandEyes synthetics and network paths

A changed network path or matching timestamp ranks hypotheses rather than proving cause: promote
one only with a disprovable mechanism, corroboration from an independent signal class, a
disconfirmation test, and blast radius.

## Reading results during an incident

- Bind test/agent IDs, target, first/last timestamps, and collection cadence; compare failing vs.
  healthy vantages (including inside vs. outside networks) plus hop/AS deltas and DNS checks.
- Cross-check the same window against `cf app`, events, and application logs — keep platform-edge
  health separate from user-facing errors and synthetic probes, and send network path faults to
  network/platform owners.

## Designing and automating checks

- Exercise failure, recovery, and notification delivery from a safe target before claiming coverage.
  Hand steady-state test changes to `observability-engineer` with coverage gap, proposed vantages,
  threshold evidence, expected cost, runbook, validation plan, and rollback condition.
- For `/v7/tests` and `/v7/agents`, record account-group labels and repository paths (never tokens).
  Automated test creation/update/deletion belongs to `software-engineer` and a human release owner.
