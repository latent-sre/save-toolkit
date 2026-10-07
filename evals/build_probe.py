"""Fixture-backed, tool-bearing agent probes: measure what an agent DOES in a disposable repo.

The clean-room runner denies every file, shell, and web tool, so a build lane can
only be graded on what it says. This probe seeds a small fixture repository in a system temp
directory, runs `claude -p --agent <plugin agent>` there with the agent's real tools pre-approved,
and grades outcomes with code: the tests it wrote pass when the probe runs them, a fake `cf` on
PATH never received `push`, a booby-trapped `conftest.py` on a fork branch never executed (a
canary file), nothing was committed or written to `.agents/` uninvited, which skills were loaded,
whether a test command actually ran before "Verified" was claimed.

Isolation is the host level, always on: the harness's `clean_room.clean_env()`
(allowlisted env, credential-only `CLAUDE_CONFIG_DIR`), a workspace outside the repository, and an
empty HOME / USERPROFILE / CF_HOME for the child so no real `cf` session or operator dotfile is
reachable through the home lookup. It is NOT a sandbox: the agent's Bash still runs on the host
with network access, and the credential copy in `CLAUDE_CONFIG_DIR` is reachable by an unguarded
Read or Bash (the probe scans every output for credential markers and warns loudly). The former
`--container` level, which routed the shell into a network-less Docker container, was removed under
EVAL-011: no saved run used it, and externally authored code runs only in separately authorized CI
(EVAL-012 DEC-13). A service-backed scenario's service container stays restricted to an exact
reviewed-image allowlist with capability and resource limits. Every run records `isolation: host`.

A trial is INCONCLUSIVE, never a verdict about the agent, when `claude` reports an error result,
exits nonzero, never advertises its tool inventory, advertises a different inventory than the
probe asked for, or carries an MCP server in a strict-empty run; an authentication failure aborts
the batch. Each run also records the plugin root's commit,
plugin-input dirty state, and source digest, and `--expect-plugin-digest` refuses any other bytes.

The runner lives in the `probe` package beside this file (see probe/__init__.py); this module is only
its command line. Code that uses the runner imports its modules, and a test patches a name where the
runner reads it: a function in the module that defines it, such as `probe.trials.run_trial`, since
every other module calls it through there, and a class or constant in each module that imports it.

Usage:
  python evals/build_probe.py run --scenario all --label new_skill --model sonnet --trials 2 \\
      --out .eval-runs/build/iteration-3-sonnet
  python evals/build_probe.py run --scenario build-software-engineer-cli-with-tests \\
      --plugin-root ../incumbent-783f462 --label old_skill --model opus --trials 3 --run-offset 2
  python evals/build_probe.py validate
  python evals/build_probe.py regrade ITERATION_DIR
  python evals/build_probe.py rescore ITERATION_DIR --out NEW_DIR
  python evals/build_probe.py diff BASE_RESCORE CANDIDATE_RESCORE
  python evals/build_probe.py schema --out docs/fleet-evaluation/eval-record-v1.schema.json
The flat flags of earlier runners (`--validate`, `--regrade`, `--rescore`, `--rescore-diff`, and a
bare run) still work.

Output layout matches the skill-creator reviewer/aggregator: <out>/eval-<name>/<label>/run-N/
{outputs/response.md, outputs/workspace.patch, outputs/trace-summary.json, grading.json,
timing.json, record.json} plus eval_metadata.json per eval. Raw traces stay next to them (private,
gitignored).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from probe import cli

if __name__ == "__main__":
    raise SystemExit(cli.main())
