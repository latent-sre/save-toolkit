Read this when the tool is a CLI — exit codes, streams, --dry-run, confirm-before-destruct are the scripting contract.

This file owns CLI shape; language idiom remains the caller's responsibility—the `craft` skill is an ownership label, not a load.

Starter: [cli_skeleton.py](../assets/cli_skeleton.py).

## Framework
- **Python → Typer** (or Click; `argparse` for zero-dep); follow the repository's Python conventions. **Bash →** use strict mode and explicit argument parsing. **PowerShell →** use advanced functions, approved verbs, and `CmdletBinding`. Match the repo.

## Exit codes & streams (the scripting contract)
- **Exit `0` on success, distinct non-zero codes for distinct failures** — document them; CI branches on
  them. Fail loud to **stderr** with a message stating what failed and the next step.
- **stdout is for the result; stderr is for logs, progress, and diagnostics** — so `| jq` and pipelines
  stay clean. Don't `print` chatter to stdout; in Python, configure `logging` to stderr.
- **Human-readable by default; `--json` for machines.** Keep the JSON shape stable: version the JSON contract and preserve or explicitly migrate consumers before changing it. Detect a TTY and honor `NO_COLOR`.

## Safety (state-changing CLIs)
- **`--dry-run` for anything that changes state**, made real: **separate decision from effect** so
  dry-run computes the plan and calls nothing — prove it in a test with a spy.
- **Confirm destructive actions** unless `--yes`/`--force`; print the plan + what will change first.
- **Idempotent and re-runnable** — re-running converges, doesn't double-apply. State-changing
  cf/platform actions stay gated (human sign-off via a human release owner).

## Config & secrets
- **Precedence: flag > env > config file > default.** **Secrets come from env / service binding, never a
  flag** (flags leak in shell history and `ps`). Never echo a token. External calls set connect/read timeouts, bounded retry/backoff, pagination limits, and response-schema validation.

## UX
`--help` on every command with examples; sane defaults; `--verbose/-q`; progress to stderr; stable flag
names. Small, composable subcommands beat one mega-flag.

## Testing
Test **exit codes, stdout vs stderr, and the `--json` shape**; assert `--dry-run` performs **no** side effects (spy/mock the effect). Write the failing exit/output/side-effect assertion first; tools include `pytest` + Typer/Click runner, `bats`, or `Pester`.

## Definition of done
Distinct documented exit codes · result on stdout / logs on stderr · `--json` stable · `--dry-run` calls
nothing and destructive actions confirm · secrets never in flags/logs · idempotent · `--help` is useful ·
exit codes + dry-run covered by tests.
