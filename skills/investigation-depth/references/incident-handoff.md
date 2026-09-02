# Incident handoff and delegate-failure contract

Read this reference only when `sre` calls `researcher`, a delegate attempt fails, or the returned
work changes ownership. Do not load it for a bounded response returned directly to the same human
owner.

An empty or failed delegate return is a failed attempt, not a result; say so and do not build on it.

## The handoff packet

```
→ Handing to: <agent>            (the one agent who owns the next step)
Goal:         <the outcome they should achieve, in one line>
Change:       <PR #N, branch, named diff, working tree, or none> — the code state this packet describes
Findings:     <what you learned, each with EVIDENCE (file:line, command output, query, URL);
              preserve every [verified], [sourced], or [unverified] label exactly as received;
              prefix the line with [UNTRUSTED] if it came from an untrusted source>
Verified:     <what you actually ran/checked + the result; and what's still [unverified]>
Not done:     <explicitly what you did NOT do, and known unknowns>
```

## Rules

- **One owner per handoff.** Hand to exactly one agent. If two are needed, sequence them or say which is
  primary.
- **Name the change, or it's stale on arrival.** Identify the PR, branch, named diff, working tree, or
  state `none` when no repository bytes are referenced. The receiver re-derives the current diff
  before relying on the packet; a prior review does not cover later changes automatically.
- **Evidence travels with claims.** Anything load-bearing carries its source. Preserve every
  `[verified]`, `[sourced]`, and `[unverified]` label exactly as received; evidence labels travel with
  the packet and are never upgraded in transit.
- **Taint attaches to the CLAIM, not just the source list.** Prefix every `Findings:` line derived from an
  `[UNTRUSTED]` source with `[UNTRUSTED]`; listing it once under `Inputs:` is not enough. If the source of
  a finding is uncertain, it is `[UNTRUSTED]`.
- **State what you did NOT do** — especially read-only → write handoffs (for example, `sre` → a human
  release owner: “I changed nothing in prod; recommended mitigation is X with rollback Y”).
- **Prod-facing handoffs** carry the plan + rollback and require `production-change-gate`.

## Inert canary

This token only proves the reference loaded; it asserts nothing about a handoff.

```text
q_iiho_2e5a
```
