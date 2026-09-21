SRE assistant - investigation and access implementation notes
============================================================

Planning context for SRE-CF-001. The status, owner, and next action live in
../docs/fleet-roadmap.md under SRE-CF-001; that remains the only backlog.
The canonical behavior is in sre-assistant.md. This note records implementation
limits and remaining access work; it is not a second agent definition or grant.

Purpose
-------
Answer a bounded lookup or investigative question dispatched by a human or the
main incident/runbook workflow. Follow relevant evidence within the named scope
and return findings and recommendations while the human continues other work.
Preserve exact extraction, evidence/taint, timing and causal limits, mitigation
readiness, and caller ownership. The generated Copilot body has a 25,000-character
working budget, enforced in ../scripts/generate_platform_adapters.py.

Decisions to preserve
---------------------
- The owner now wants selected read-only CF observations (2026-09-21).
  The broader tool configuration remains open.
- Credential helpers are for authentication without displaying credentials.
  Reuse an existing authenticated SSO/session first when available to the task.
  Personal user credentials may be needed, including credentials configured in
  gitignored local files. The implementation is still to be selected.
- Reading change/deployment history through dashboards, the operations repo, or
  the read-only Helix helper remains part of the intended investigation role.
- The SRE assistant must not deploy, roll back, restart, restage, scale, change
  runtime configuration, or otherwise apply production changes through any tool.
- A command that does not mutate state may still reveal credentials. Sensitive
  environment/service-key output is outside the proposed capability.

Initial diagnostic scope
------------------------
Start with these existing forms against the caller's named target:
- cf target: display the current foundation/org/space; no target-changing flags.
- cf app <app>: app and instance status.
- cf events <app>: recorded app events.
- cf logs <app> --recent: bounded recent-log collection, not an ongoing stream.
- cf revisions <app>: revision-history metadata, not rollback authorization.

The updated guard narrows CF to these command forms, with --recent on either
side of the app name. Inventory expansion, streaming and other flags are denied.
This is command admission, not authentication-identity masking or proof of
installed-host enforcement. Recent logs also need host timeout/output limits;
--recent is not an exact historical-window selector.

Authentication helper requirements
----------------------------------
First reuse a valid authenticated session already available to the task for the
intended target, including an existing browser SSO or CLI session. Use it through
the supported tool's session handling; keep cookies and tokens out of LLM-visible
arguments and output. Browser sign-in does not establish API or other-tool access.
If reauthentication is needed, use the normal sign-in flow with the human
completing any required SSO/MFA interaction; never ask for credentials in chat.

Use a credential-backed helper when the chosen access path needs one. Support
personal accounts where needed; a service account is not a prerequisite.
A human may configure credentials in a local gitignored file or the team's
credential store. Gitignore keeps matching untracked
files out of ordinary Git tracking; it does not prevent filesystem/tool access.
This requirement applies to CF and other configured investigation sources.

Where a helper is needed, its public inputs should be a logical connection alias,
an allowed read operation, and its target. The helper resolves and uses credentials
internally. The agent does not supply or retrieve their raw values. Keep aliases
independent of personal usernames; a tracked example contains placeholders only.

Keep authentication usernames, passwords, and tokens out of agent-visible inputs,
command arguments, debug output, errors, and saved evidence. Return the requested
diagnostic result or a credential-free access error. Omit or mask authentication
identity if a result echoes it, including current-user fields in target/status
output. Apply this before the tool result reaches the LLM; masking only the final
report is insufficient.

This request covers authentication only. It does not add a general log/JSON
redaction tool; existing sensitive-evidence handling still applies. Authentication
does not widen the allowed CF operations or permit credential-bearing reads.
The agent's file, search, and shell tools must not expose the credential source,
and the agent must not be able to alter the executing helper to disclose it.
Gitignore, a prompt prohibition, or an editable wrapper alone cannot establish
this boundary. Select and verify host/tool restrictions that enforce it on each
supported host; this note does not implement those restrictions.

Current source and remaining work
---------------------------------
- Canonical agent and incident caller: bounded investigation, scoped follow-up,
  early findings/partial-return fallback, source selection and preserved safeguards.
  Regression fixtures cover supplied-state decisions; native behavior is unverified.
- CF: selected grammar and pure-filter checks in the command guard. Output masking,
  target binding inside a protected helper, timeout/output bounds and both-host
  acceptance remain open. A permitted command may still print a username.
- Browser: exact native VS Code/Playwright viewing grants now include navigation,
  unsaved variables/time, scrolling keys and panel inspection. Read-only session
  permissions, protected results and installed-host acceptance remain required.
  Existing SSO comes first; an unshared or separately opened tab is not access.
- APIs/helpers: skills/grafana/scripts/grafana_read.py now provides one dashboard
  model read and bounded Prometheus/Loki query operation, with internal token/basic
  authentication and masked results/errors. The guard binds its installed path and
  arguments; it grants no arbitrary Python. Human credential configuration and the
  operations-repo path still need binding. Helper masking is not OS isolation.
- Analysis: temporary code may analyze collected evidence through an isolated
  scratch path with no production credentials/network. No such execution grant is
  added by this source update. Broken team helpers get a repair proposal, not an edit.
- Helix/BigQuery: read-only incident/change lookup is a planned integration. The
  helper is not imported; do not invent dataset, schema, endpoint or results.

The standard Copilot profile still has no terminal. Its command preview remains
an acceptance candidate, and the shell guard does not filter file or browser tools.
The source update therefore does not claim complete credential isolation or verified
installed-host browser behavior. Finish those boundaries alongside the first real
Grafana workflow; do not add general shell/Python/browser grants to bypass gaps.

Use ../docs/vscode-plugin-acceptance.md for the pending installed-host cases:
session reuse/expiry; allowed reads and denied effects; wrong targets; synthetic
personal credentials in normal/failure output and images; direct-file and helper
tampering; returned image delivery; automatic dispatch, early finding and caller
continuation. Test both supported hosts and record what was actually proven.

This file uses .txt because agents/*.md are parsed as agent definitions.

References checked for this note:
https://git-scm.com/docs/gitignore
https://cli.cloudfoundry.org/en-US/v8/app.html
https://cli.cloudfoundry.org/en-US/v8/target.html
https://cli.cloudfoundry.org/en-US/v8/login.html
https://docs.cloudfoundry.org/running/managing-cf/audit-events.html
https://docs.cloudfoundry.org/devguide/deploy-apps/troubleshoot-app-health.html
https://docs.cloudfoundry.org/devguide/revisions.html
