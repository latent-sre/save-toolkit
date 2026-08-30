# ADR: Separate local repository investigation from external research

- Date: 2026-07-31
- Status: Accepted
- Decision owners: save-toolkit maintainers
- Sister-lab input: commit `f4741c778a825a6353cc99e969f4ed05755aa574`

## Context

The six-agent fleet assigned one `researcher` both local checkout tools (`Read`, `Grep`, `Glob`) and
external egress (`WebSearch`, `WebFetch`, Context7, and GitHits). That authority combined sensitive
private or uncommitted data, untrusted fetched content, and a channel capable of sending data out.
Prompt instructions warned against disclosure, but did not remove any leg of that capability chain.

The same direct web grants also appeared on `sde`, `sre`, and `prompt-engineer`. Local engineering
roles still need external contracts, but they do not need to perform those lookups in the same context
that holds repository evidence.

## Decision

1. Add `repository-investigator` as a terminal local-only agent with exactly `Read`, `Grep`, and
   `Glob`. It answers bounded questions about the current, private, or uncommitted checkout and cites
   `file:line` evidence.
2. Make `researcher` terminal and external-only. It retains generic web search plus exact Context7
   and GitHits evidence tools, but loses local reads, Bash, writes, skills, and delegation.
3. Remove direct `WebSearch` and `WebFetch` from every other canonical local role. Roles that need a
   public fact delegate a sanitized question to `researcher`; the main session sequences mixed
   local/external work and compares separately labeled provenance.
4. Validate the authority and delegation maps as roster invariants. Generated Copilot adapters must
   expose exactly local `read`/`search` for `repository-investigator` and `web` for `researcher`.
5. Do not claim equivalent Codex enforcement. Custom-agent TOML cannot deny inherited tools, so the
   generated local-only role requires outer network isolation and the external-only role requires a
   repository-unmounted environment with only approved evidence tools.

## Alternatives considered

- **Keep one researcher and strengthen its warning:** rejected because prose does not remove
  capability.
- **Make the split a skill:** rejected because a skill changes method, not tool authority.
- **Give every local role both local and web tools:** rejected because convenience preserves the
  highest-risk capability combination and makes provenance easier to blur.
- **Add a broker immediately:** deferred. A redacting, destination-allowlisted evidence broker is
  stronger across hosts, but it is a new runtime component with its own authentication, audit, and
  failure modes. The role split is useful now and makes that future boundary explicit.

## Consequences

- Local repository questions and public ecosystem questions have distinct routing lanes and
  mechanically distinct Claude/Copilot authority.
- Mixed questions take two calls and a caller-owned synthesis. The added latency is accepted in
  exchange for isolation and clearer provenance.
- Removing direct web tools is not full egress prevention for `sde` and `prompt-engineer`, which keep
  unguarded Bash. Host/network controls remain load-bearing for those roles.
  Current names: `software-engineer` and `agent-engineer`
  ([`2026-08-25-software-engineer-rename.md`](2026-08-25-software-engineer-rename.md),
  [`2026-08-26-agent-engineer-rename.md`](2026-08-26-agent-engineer-rename.md)).
- The `researcher` input gate cannot prevent a caller from placing sensitive content directly in its
  prompt. Sanitization is a caller obligation until a brokered boundary exists.
- Generated Codex profiles preserve the method but require outer isolation to enforce it. A passing
  prompt canary proves profile loading, not per-agent tool denial.

## Rollback

Revert the roster, validator, generated adapters, and documentation together. Do not partially remove
`repository-investigator` while leaving local-read denial on `researcher`, or restore local reads to
the external role as a convenience workaround. If a critical workflow cannot operate through the
split, temporarily keep external facts `[unverified]` while maintainers decide whether to add a
brokered evidence service or explicitly accept a broader authority boundary in a new ADR.
