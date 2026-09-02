# Agent tooling safety notes

Read this only when the task names an installed Grafana CLI, MCP server, vendor skill, or Foundation
SDK. The repository installs none of them. Adoption is a `stack-profile` decision, and current tool
names, flags, and compatibility come from the installed version's `--help` plus current upstream
documentation—not this file.

The HTTP API in [http-api](./http-api.md) remains the portable path and owns this fleet's
concurrency, verification, and evidence rules. A helper may implement a call; it does not replace
those rules or widen dashboard-only authority.

## `gcx`

If `gcx` is installed, confirm the live command surface before use. Prefer its server-side validation,
dry-run, push, version history/restore, and dashboard snapshot flow when those commands exist. Pin the
dashboard API version instead of accepting a server-preferred shape, and stop when
`grafana.app/managed-by` names another owner.

Agent-mode safeguards and a successful dry-run are not approval. After a push, read the resource
back, run changed queries, inspect a snapshot when rendering exists, and confirm the save record.
Credentials stay in the process environment; never embed a token in a context, command transcript,
or tracked config.

*[sourced: `grafana/gcx` README, safety design, and live CLI help; re-check before use]*

## `grafana/mcp-grafana`

Use summary/property/query tools for narrow reads; a complete-dashboard read consumes much more
context and is justified only for a full model edit.

**Do not use patch-mode `update_dashboard` for a live write.** In the reviewed implementation,
JSONPath operations re-fetch the model and save with `overwrite: true`, silently defeating the
concurrency rule. Full-JSON mode can preserve the returned `version` with `overwrite: false`; if the
installed server cannot do that, use the HTTP path instead. Re-check the installed tool source or
version before relying on this behavior because it can change.

For a read-only deployment, combine the server's current write-disable option with a Viewer service
account. A flag is defense in depth, not proof of isolation; inspect the registered live tool list.

*[sourced: `grafana/mcp-grafana` dashboard tool source and README, reviewed 2026-08-21]*

## Vendor skills and Foundation SDK

Grafana's skill packages and `gcx` plugin overlap this skill. Their product knowledge may help author
a model, but this fleet's stack, target discovery, authority, evidence labels, and no-force write
contract still govern. Do not install or update a package as part of a dashboard task without a
separate stack decision.

The Foundation SDK can generate typed Classic, V1, or V2 dashboard models. Use it only when already
adopted for repository-managed dashboard-as-code work; this team's live dashboards currently have no
committed source. Pin the package through the repository dependency process and validate generated
output against the target API version before applying it.

*[sourced: `grafana/skills` and `grafana/grafana-foundation-sdk` upstream documentation; fetch current
versions when adoption is actually proposed]*

<!-- terminal-canary: q_odtool_5b2a -->
