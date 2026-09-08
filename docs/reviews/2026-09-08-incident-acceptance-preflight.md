# Incident acceptance: isolation preflight

Date: 2026-09-08 UTC. Outcome: **inconclusive; incident behavior was not tested**.
This evidence supports the unresolved isolation decision in
[`INCIDENT-QUALITY-001`](../fleet-roadmap.md#incident-quality-001--verify-decision-quality-after-the-sre-contract-repairs).

## Candidate and authorized scope

[verified] Both probes used revision `0450ea58d3403a56ae7cc94aef979bd033076de9`, with plugin
SHA-256 `450f5fc1d6f9ad852559b574fc3a88e703503858eef3950ca10867bba1b15c69`.
Claude Code 2.1.263 resolved requested `sonnet` to `claude-sonnet-5`.
Manifests froze the plugin snapshot, runner/parser dependencies, CLI identity, cases and acceptance.
Independent read-only inspection confirmed the recorded identities and raw-trace accounting.

The human approved one final-candidate check: two native incident workflows with real helper
returns and same-session recovery, plus two repetitions of each of the three retained helper
exchange cases. The cumulative ceiling is 16 initiated sessions, including preflights, helper
children and resumed turns, and $4 in summed CLI estimates. No retries, paid judges, live
infrastructure, or candidate edits during measurement. A later approval permitted a revised
isolation probe; it did not reset the budget or accept a broader discovery context.

## Observed preflights

| Probe | Discovery inventory | Initiated sessions | CLI estimate | Result |
|---|---|---:|---:|---|
| Initial restricted clean room | Candidate plus 17 noncandidate skills | 1 | $0.0356584 | Isolation criterion failed |
| Bundled skills disabled explicitly | Candidate plus `doctor` only | 1 | $0.0269164 | Strict zero-extra-skills criterion still failed |

[verified] Both traces advertise only `Read` and `Skill`, empty MCP, and exactly the intended
plugin snapshot. Neither call invoked a tool or child. The workspace and snapshot were outside
the repository and home directory; the recorded ancestry checks found no named instruction/settings
files or directory redirections. Credentials-only configuration was outside granted read roots;
the temporary configuration was cleaned up after each call. No credentials or raw traces are published.

The second probe added `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1` and
`CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` to the actual scrubbed child environment, supplied
`{"disableBundledSkills": true}` through `--settings`, and configured `Skill(doctor)` in
`--disallowedTools`. Setting these environment variables only in the parent shell would not work:
the existing clean-room allowlist drops them.

[sourced] The [official skills documentation](https://code.claude.com/docs/en/skills) identifies
`doctor` as an exception to disabling bundled skills. Its continued advertisement was observed;
the configured denial was **not exercised**, and an init inventory is not a complete capture of
the model's hidden context. The responses reported no supplied user/project instruction headings,
but model self-report alone does not prove their absence.

The existing parser's plugin-identity check does not inspect `init.skills`. A correct plugin list
therefore did not establish candidate-only discovery. The task-local preflight inspected that
inventory explicitly and stopped on the discrepancy; shared evaluator code was not changed.

## Disposition and remaining work

[verified] Cumulative use: **2 sessions / $0.0625748**. Remaining under the original ceiling:
**14 sessions / $3.9374252**. These are client estimates, not verified billing charges.
No incident workflow, helper exchange, source comparison or recovery follow-up ran. Neither
successful CLI execution nor the short glossary responses establish incident acceptance.

The pending decision is whether to allow the documented `doctor` catalogue exception with its
denial configured, or retain strict zero-extra-skills isolation. Publishing this evidence does not
accept that exception. Neither strict preflight passed. Any continuation must freeze its exact
scope and preserve both results.

Native continuation code is prepared; incident phases remain unrun. Before execution, it must enforce a
single helper slot before dispatch, require a successful helper return before parent resume,
reserve cost/session capacity before each call, and stop on missing accounting or changed inputs.
Offline checks of the helper-slot guard do not prove the installed CLI will invoke it.

Private manifests, prompts, raw results and prepared orchestration remain under
`.eval-runs/incident-acceptance-20260907-final*`. Retain this short report while the live isolation
decision depends on it; raw traces and temporary runners remain outside the published repository.
