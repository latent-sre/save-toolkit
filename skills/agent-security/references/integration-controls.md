# Integration controls

Read this when reviewing this fleet's current runtime boundary, selecting controls for an agent with
secrets or external tool/network actions, designing a tool-result envelope, or assessing a Claude
Code, MCP, or OAuth enforcement boundary. The entrypoint owns the lethal-trifecta decision,
cross-agent trust boundary, evidence rules, and final review output.

## Current fleet runtime boundary

`reviewer` and `repository-investigator` are local-only and hold no Bash, Write, web, or external MCP
tools; `researcher` is external-only and holds no local read, Bash, Write, Skill, or Agent tool. `sre`
runs Bash under the fail-closed allowlist guard (the repo's `readonly-guard.py`, wired through the
plugin-level session hook). `sde`, `observability-engineer`, and `prompt-engineer` retain unguarded
Bash (team-authored repository work; Grafana dashboard applies), so host/network egress controls
remain load-bearing even though their direct web tools are absent. Verify every claim against agent
frontmatter and guard tests; generated Codex profiles need outer isolation because their TOML cannot
deny inherited tools.

## Integration design

For mixed local-plus-external questions, the main session sequences two isolated tasks: first obtain
local `file:line` evidence from `repository-investigator`, then construct a sanitized public question
for `researcher`, and finally compare the separately labeled results. Never copy private excerpts,
paths, internal identifiers, logs, or uncommitted text into the external task. This handoff discipline
is cooperative; a brokered redaction and egress boundary would be stronger.

- **Least privilege.** Give an agent/tool only the data and reach the task needs. Don't hand a
  log-reading agent write access to prod.
- **Allowlist external destinations** and gate any send/exfiltrate step; prefer dedicated, auditable
  tools over a raw `bash`/`curl` the harness can't inspect.
- **Keep secrets out of the model's context** — inject at the boundary (e.g. a git/credential proxy),
  never paste tokens where injected text could read them back.
- **Sandbox/quarantine untrusted input** before it reaches a privileged step; sanitize, don't trust.
- **Wrap every tool result in a provenance envelope, and strip what the eye can't see.** The
  pattern that independent agent frameworks converge on: fenced block naming the source
  (`<untrusted_tool_result source="web_fetch">…`), a one-line reminder that its contents are data,
  forged open/close sentinels escaped so the payload can't end the envelope early, and — the step
  people skip — **invisible Unicode removed first**: zero-width characters, bidi overrides
  (`U+202A–202E`, `U+2066–2069`), and the Unicode *tag* block (`U+E0000–E007F`) all carry
  instructions a human reviewer cannot see in a diff. A heuristic "ignore previous instructions"
  matcher is a tripwire, not a filter; the envelope and the application-side approval are the
  control. *[sourced: cross-OSS pattern via GitHits, seven agent frameworks; reviewed 2026-08-21]*
- **On Claude Code, know what each layer actually does.** Denying the `WebFetch` tool "does not
  prevent access via other tools like Bash" — only OS-level sandboxing "enforc[es] a network
  domain allowlist"; `curl`/`wget` are not auto-approved by default; and Anthropic runs
  "server-side classifiers that scan tool results for suspicious content" — a layer to be glad
  of, never the thing a review relies on. The fleet's own enforcement order — tool absence, then
  the hook allowlist, then host network controls — is this principle applied. *[sourced: Claude
  Code security, glossary, and admin-setup docs; reviewed 2026-08-21]*
- **An MCP server is a dependency with your privileges.** A local (`stdio`) server "runs with the
  same privileges as the client" — review its launch command exactly as you would a `curl | sh`,
  and prefer sandboxed launch. For remote servers: a server must never forward a token it was not
  issued (token passthrough is forbidden by the spec), OAuth metadata URLs are an SSRF vector a
  malicious server controls, and scopes should start minimal and elevate on challenge. In this
  fleet, `reviewer`, `repository-investigator`, and `scribe` hold no external MCP at all — that is
  the review finding to preserve, not relax. *[sourced: MCP specification 2025-11-25, security best
  practices; reviewed 2026-08-21]*
- **A mutable path is not an exemption boundary.** A checkout can replace the file at an allowed path.
  If a helper ever needs privileged admission, bind the reviewed bytes by content hash and re-verify
  them at the execution boundary; a path allowlist alone does not establish identity.
