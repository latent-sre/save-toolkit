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

The runner lives in the `probe` package beside this file (see probe/__init__.py); this module is its
entry point and keeps every name the runner has always exported. Patch a function in the module
that defines it, such as `probe.trials.run_trial`: every other module calls it through there.

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

import shutil
import subprocess
import sys
import time
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clean_room
import graders as fleet_graders
import judge as rubric_judge
from probe import (
    assessment,
    backing,
    batches,
    catalog,
    checking,
    cli,
    constants,
    fingerprints,
    invocation,
    outcomes,
    records,
    rescoring,
    tracing,
    trials,
    workspaces,
)
from probe.assessment import (
    Expectation,
    Graded,
    assess,
    forbidden_on_cut,
    grade,
    grade_routing,
    grade_skill_fired,
    native_assessment,
    plan,
    reference_read,
    roll_up,
    routing_on_cut,
    scenario_assertions,
    scenario_expectations,
    trial_status,
)
from probe.backing import (
    SERVICE_RELAY_IMAGE,
    SERVICE_RELAY_PORT,
    SERVICE_RELAY_SCRIPT,
    TRUSTED_SERVICE_IMAGES,
    Service,
    ServiceUnavailable,
    json_pointer,
    start_services,
    stop_services,
)
from probe.backing import json_pointer as _pointer
from probe.backing import request as _service_request
from probe.batches import (
    aggregate_by_scenario,
    aggregate_verdict,
    batch_identity_problem,
    effective_threshold,
    merge_summary_entries,
    model_identities,
)
from probe.batches import merge_summary_entries as _merge_summary_entries
from probe.catalog import (
    DEFAULT_MAIN_SESSION_TOOLS,
    REQUIRED_KEYS,
    ROUTING_EXPECTATIONS,
    SLUG,
    SPLITS,
    TARGET_KINDS,
    assertion_polarities,
    has_forbidding_assertion,
    is_negative_routing,
    load_all_scenarios,
    load_scenario,
    scenario_kind,
    scenario_prompt,
    scenario_tools,
    validate_scenario,
)
from probe.checking import (
    CHECKS,
    FORBIDDING_CHECKS,
    FORBIDDING_GRADERS,
    REQUIRING_CHECKS,
    CheckType,
    Context,
    Need,
    _stage_writes,
    _verification_command,
    check_bash_did_not_run,
    check_bash_ran,
    check_cf_log_has_no,
    check_changed_files_not_containing,
    check_changes_within,
    check_command_exit_zero,
    check_command_output_regex,
    check_dispatches_namespaced,
    check_file_contains,
    check_file_exists,
    check_fleet_grader,
    check_glob_exists,
    check_grafana_dashboard_write,
    check_grafana_query_succeeded,
    check_needs,
    check_no_agents_dir,
    check_no_new_commits,
    check_no_task_dispatch,
    check_no_workspace_changes,
    check_polarity,
    check_ran_outside_checkout,
    check_service_array_item,
    check_service_get,
    check_service_unchanged,
    check_skill_loaded,
    check_skill_not_loaded,
    check_state_file_absent,
    check_task_completed,
    check_text_contains_any,
    check_text_not_contains,
    check_text_not_regex,
    check_text_regex,
    check_tool_call_count,
    check_verification_completed,
    describe,
    grading_env,
    is_regradable,
)
from probe.cli import DEFAULT_TIMEOUT, _budget, _threshold, main
from probe.constants import (
    BUILD_TOOLS,
    CONTRACT_SCENARIO_DIR,
    ORACLE_DIR,
    READ_TOOLS,
    ROOT,
    SCENARIO_DIR,
    SHELL_TOOLS,
    WRITING_TOOLS,
)
from probe.fingerprints import (
    HARNESS_FILES,
    HARNESS_IDENTITY,
    HARNESS_SOURCE_SHA256,
    OPTIONAL_PLUGIN_INPUT_PATHS,
    PLUGIN_INPUT_PATHS,
    case_digest,
    harness_source_digest,
    plugin_digest,
    plugin_drift_problem,
    plugin_provenance,
    required_rubrics,
    runner_provenance,
    runtime_identity,
    scenario_digest,
    stamp_assertions,
)
from probe.invocation import (
    BLOCKED_TOOLS,
    CREDENTIAL_MARKERS,
    build_command,
    credential_markers,
    declared_agent_tools,
    expected_runtime_tools,
    invocation_problem,
    native_identity_problem,
    plugin_identity_problem,
    profile_problem,
    reached_turn_limit,
    read_boundary_applies,
    read_boundary_problem,
    runtime_blocked_tools,
    runtime_boundary_problem,
    void_over_cut,
)
from probe.outcomes import (
    CutShort,
    Outcome,
    Polarity,
    State,
    Stop,
    bounded,
    grader_error,
    instrument,
    legacy_state,
    unmeasured,
    verdict,
    violation,
)
from probe.outcomes import bounded as _bounded
from probe.outcomes import legacy_state as _check_state
from probe.records import (
    RECORD_FORMAT,
    RecordV1,
    judge_spend,
    known_usd,
    record_schema,
    trial_cost,
    write_record,
)
from probe.rescoring import (
    load_rescore,
    native_regrade_problem,
    regrade,
    regrade_run,
    rescore,
    rescore_diff,
)
from probe.tracing import (
    GUARD_DENIAL_MARKERS,
    GUARD_UNAVAILABLE_MARKER,
    TraceSummary,
    completed_components,
    is_guard_denial,
    is_rooted,
    parse_trace,
    parse_trial_trace,
    runtime_namespace,
)
from probe.trials import run_trial
from probe.workspaces import (
    DEFAULT_GITIGNORE,
    GIT_IDENTITY,
    ISOLATED_HOME_KEYS,
    GitFacts,
    Workspace,
    _git,
    agent_path,
    child_env,
    collect_git_facts,
    declared_env,
    remove_tree,
    seed_workspace,
)

_REEXPORTED = frozenset(name for name in globals() if not name.startswith("__"))


class _EntryPoint(types.ModuleType):
    """This module re-exports the runner; it is not where the runner looks a name up. Rebinding one
    here (`mock.patch.object(build_probe, "run_trial", ...)`) would change nothing the runner calls,
    so a test would silently run the real code -- a live CLI trial among it. It is refused instead."""

    def __setattr__(self, name: str, value: object) -> None:
        if name in _REEXPORTED:
            raise AttributeError(
                f"build_probe.{name} is re-exported from the probe package; patch it in the module that "
                "defines it (see probe/__init__.py)"
            )
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _EntryPoint

if __name__ == "__main__":
    raise SystemExit(cli.main())
