# Agent tooling safety notes

This fleet adopts no Grafana MCP server, `gcx`, vendor skill package, or Foundation SDK; the rules
in [http-api](./http-api.md) govern dashboard and folder writes. Never install or adopt a tool as
part of a task: adoption is a `stack-profile` decision. Do not write with `gcx` or an MCP server unless
`stack-profile` records its adoption. If `grafana/mcp-grafana` is present, never use its patch-mode
`update_dashboard` for a live write: it saves with `overwrite: true`, defeating the concurrency rule
*[sourced: `grafana/mcp-grafana` dashboard tool source]*. For renderer/browser capability use
[visual verification](./visual-verification.md).
