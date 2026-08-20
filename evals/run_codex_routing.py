#!/usr/bin/env python3
"""Validate and plan the fixed Codex/Terra ROUTE-001 campaign.

The live executor is added only after the provider-native activation trace has an independently
tested contract.  This module already freezes the model, scenario, revision, and authority inputs
so a behavior-only Codex transcript cannot be mistaken for routing evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

# Isolated mode intentionally omits the script directory from sys.path.  Restore only this
# immutable evaluator directory so the sibling modules can be imported without enabling site or
# environment-provided paths.
EVAL_IMPORT_ROOT = Path(__file__).resolve().parent
if str(EVAL_IMPORT_ROOT) not in sys.path:
    sys.path.append(str(EVAL_IMPORT_ROOT))

import codex_harness
import codex_model_catalog
import codex_runtime
import codex_snapshot


EVAL_ROOT = Path(__file__).resolve().parent
WINDOWS_MANIFEST_PATH = EVAL_ROOT / "conformance" / "codex-terra-routing-v1.json"
LINUX_MANIFEST_PATH = EVAL_ROOT / "conformance" / "codex-terra-routing-linux-v1.json"
SCENARIO_BUNDLE_PATH = EVAL_ROOT / "conformance" / "codex-terra-scenarios-v1.json"
# The Linux container is the canonical execution arm.  The Windows path remains accepted only as
# historical/optional conformance evidence and retains its historical runtime identity.
MANIFEST_PATH = LINUX_MANIFEST_PATH
MODEL = "gpt-5.6-terra"
REASONING_EFFORT = "medium"
SANDBOX = "read-only"
APPROVAL_POLICY = "never"
RUNTIME_PLATFORM = "linux-x86_64"
PYTHON_VERSION = "3.12.10"
PYTHON_EXECUTABLE_SHA256 = (
    "4dbf3143240288fb2170257ffaa7bd030cdda5d2703d1f5f30b627042267e2e3"
)
CODEX_EXECUTABLE_SHA256 = (
    "ac2cfed85fb647d61e0150b8548102b330e4799d9d81ad5d354de701edf6b074"
)
WINDOWS_CODEX_CLI_VERSION = "0.147.0"
TIMEOUT_S = 300
TRIALS = 2
THRESHOLD = 1.0
BEFORE_REVISION = "a39a81f33f7ad7325c52d883822bbbdd80c7ed28"
CURRENT_REVISION = "7aef80aede95394f6c4237ed2aedb911e141c3c0"
CANARY_SCENARIO_ID = "discovery-gcp-ops-cloud-run-startup"
CANARY_EXPLICIT_SKILL = "gcp-ops"
CANARY_TRIAL = 1
CANARY_CANONICAL_SHA256 = (
    "5c516ab15a31cd26923193b97ab69e7c16337ef8ab916bf43706c3047f79fd6b"
)
CANARY_LINEAR_GRADER_TYPES = frozenset(
    {
        "cloud_run_rollback_packet",
        "contains_all",
        "contains_any",
    }
)

PAIRED_IDS = frozenset(
    {
        "discovery-obs-alerting-splunk-saved-search",
        "discovery-obs-logs-cloud-logging",
        "discovery-obs-metrics-cloud-monitoring",
        "discovery-obs-traces-cloud-trace",
        "discovery-runbook-incident-update",
    }
)
CURRENT_ONLY_IDS = frozenset(
    {
        "discovery-akamai-edge-defers-active-incident",
        "discovery-akamai-edge-defers-obs-alerting",
        "discovery-akamai-edge-defers-obs-logs",
        "discovery-akamai-edge-defers-obs-metrics",
        "discovery-akamai-edge-defers-obs-traces",
        "discovery-akamai-edge-defers-pcf",
        "discovery-akamai-edge-reference-error",
        "discovery-gcp-ops-cloud-run-startup",
        "discovery-gcp-ops-defers-active-incident",
        "discovery-gcp-ops-defers-obs-alerting",
        "discovery-gcp-ops-defers-obs-logs",
        "discovery-gcp-ops-defers-obs-metrics",
        "discovery-gcp-ops-defers-obs-traces",
        "discovery-gcp-ops-defers-pcf",
    }
)
ALL_SCENARIO_IDS = PAIRED_IDS | CURRENT_ONLY_IDS
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
SAFE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFE_HOOK_PATH_RE = re.compile(r"^[A-Za-z0-9 _.:\\/\-]+$")

BASE_MANIFEST_KEYS = {
    "schema_version",
    "campaign",
    "provider",
    "runtime_platform",
    "python_version",
    "python_executable_sha256",
    "git_cli_version",
    "git_executable_path",
    "git_executable_sha256",
    "codex_cli_version",
    "codex_executable_sha256",
    "model",
    "reasoning_effort",
    "sandbox",
    "approval_policy",
    "skill_activation_evidence",
    "agent_activation_evidence",
    "tool_policy",
    "source_model_entry_sha256",
    "safe_model_catalog_sha256",
    "timeout_s",
    "trials",
    "threshold",
    "before_revision",
    "current_revision",
    "snapshot_tree_sha256",
    "canary_scenario",
    "scenarios",
}
LINUX_MANIFEST_KEYS = BASE_MANIFEST_KEYS | {
    "runtime_kind",
    "container_user",
    "base_image_digest",
    "python_executable_path",
    "codex_executable_path",
    "scenario_bundle_sha256",
}
WINDOWS_MANIFEST_KEYS = BASE_MANIFEST_KEYS
MANIFEST_KEYS = LINUX_MANIFEST_KEYS
SCENARIO_KEYS = {"id", "cohort", "sha256"}
COMMON_EXPECTED_VALUES = {
    "provider": "openai-codex",
    "codex_cli_version": codex_harness.CODEX_CLI_VERSION,
    "model": MODEL,
    "reasoning_effort": REASONING_EFFORT,
    "sandbox": SANDBOX,
    "approval_policy": APPROVAL_POLICY,
    "skill_activation_evidence": "behavioral-only-codex-0.148",
    "agent_activation_evidence": "root-delegation-unobservable-v2",
    "tool_policy": "no-model-tools-non-root-root-collaboration-unscored",
    "source_model_entry_sha256": codex_model_catalog.EXPECTED_SOURCE_ENTRY_SHA256,
    "safe_model_catalog_sha256": codex_model_catalog.EXPECTED_SAFE_CATALOG_SHA256,
    "timeout_s": TIMEOUT_S,
    "trials": TRIALS,
    "threshold": THRESHOLD,
    "before_revision": BEFORE_REVISION,
    "current_revision": CURRENT_REVISION,
    "snapshot_tree_sha256": codex_snapshot.EXPECTED_SNAPSHOT_TREE_SHA256,
}
WINDOWS_EXPECTED_VALUES = {
    **COMMON_EXPECTED_VALUES,
    "schema_version": 1,
    "campaign": "route-001-codex-terra-v1",
    "runtime_platform": "win32-amd64",
    "python_version": "3.12.10",
    "python_executable_sha256": (
        "4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"
    ),
    "git_cli_version": "2.53.0.windows.2",
    "git_executable_path": str(codex_snapshot.GIT_EXECUTABLE_PATH),
    "git_executable_sha256": codex_snapshot.GIT_EXECUTABLE_SHA256,
    "codex_cli_version": WINDOWS_CODEX_CLI_VERSION,
    "skill_activation_evidence": "behavioral-only-codex-0.147",
    "source_model_entry_sha256": (
        "dd06f2ae3786e852ca884d6c189a364da38f7b7492fd960b05cdd2e3e232e443"
    ),
    "safe_model_catalog_sha256": (
        "2d23cea7bd13463424eca49df927a38f8480501820eec853e3789015c6a321b6"
    ),
    "codex_executable_sha256": (
        "935a1911ed2556e4ffcec995f4886ac2ac425863ba26fed264df62e30272ad9d"
    ),
}
LINUX_EXPECTED_VALUES = {
    **COMMON_EXPECTED_VALUES,
    "schema_version": 2,
    "campaign": "route-001-codex-terra-linux-v1",
    "runtime_kind": "linux-container",
    "runtime_platform": RUNTIME_PLATFORM,
    "container_user": "65532:65532",
    "base_image_digest": (
        "sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4"
    ),
    "python_version": PYTHON_VERSION,
    "python_executable_path": "/usr/local/bin/python3.12",
    "python_executable_sha256": PYTHON_EXECUTABLE_SHA256,
    "git_cli_version": "2.39.5",
    "git_executable_path": "/usr/bin/git",
    "git_executable_sha256": (
        "2540879925a6881e3877ff7e3330746ba3027b04edf16a3a12dccd1644c4f32d"
    ),
    "codex_executable_path": "/opt/route001/codex-runtime/bin/codex",
    "codex_executable_sha256": CODEX_EXECUTABLE_SHA256,
    "scenario_bundle_sha256": (
        "640ed0da086f976b390e1f1e2c664a4181aef302c7f2dd9d7031cfe881c549cb"
    ),
}
EXPECTED_VALUES = LINUX_EXPECTED_VALUES
RESERVED_AUTHORITY = {
    "source_review",
    "independent_evaluator",
    "baseline_eligible",
    "release_granted",
    "exact_revision",
}
DISABLED_MODEL_FEATURES = (
    "apps",
    "auth_elicitation",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "code_mode",
    "code_mode_host",
    "computer_use",
    "goals",
    "guardian_approval",
    "guardianv2",
    "image_generation",
    "in_app_browser",
    "memories",
    "network_proxy",
    "plugin_sharing",
    "plugins",
    "remote_plugin",
    "request_permissions_tool",
    "respect_system_proxy",
    "shell_tool",
    "skill_mcp_dependency_install",
    "tool_call_mcp_elicitation",
    "tool_suggest",
    "unified_exec",
    "view_image",
    "workspace_dependencies",
)


TrialSpec = codex_harness.TrialSpec


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"manifest contains non-JSON numeric constant {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"manifest contains duplicate key {key}")
        result[key] = value
    return result


def parse_manifest(raw: bytes) -> dict:
    try:
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Terra routing manifest must be strict UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("Terra routing manifest must be a JSON object")
    return data


def load_stable_manifest(path: Path = MANIFEST_PATH) -> tuple[bytes, dict]:
    before = path.read_bytes()
    after = path.read_bytes()
    if before != after:
        raise ValueError("manifest changed while it was loaded")
    return before, parse_manifest(before)


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    _raw, manifest = load_stable_manifest(path)
    return manifest


def load_stable_scenario_bundle(
    path: Path = SCENARIO_BUNDLE_PATH,
    *,
    expected_sha256: str,
) -> tuple[bytes, dict[str, dict]]:
    """Load the JSON-only live scenario closure without PyYAML or mutable suite discovery."""

    before = path.read_bytes()
    after = path.read_bytes()
    if before != after:
        raise ValueError("scenario bundle changed while it was loaded")
    if (
        not isinstance(expected_sha256, str)
        or not SHA256_RE.fullmatch(expected_sha256)
        or hashlib.sha256(before).hexdigest() != expected_sha256
    ):
        raise ValueError("scenario bundle digest does not match the manifest")
    payload = parse_manifest(before)
    if set(payload) != {"schema_version", "scenarios"} or payload.get("schema_version") != 1:
        raise ValueError("scenario bundle has an invalid schema")
    rows = payload.get("scenarios")
    if not isinstance(rows, list) or len(rows) != len(ALL_SCENARIO_IDS):
        raise ValueError("scenario bundle must contain exactly nineteen scenarios")
    result: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("scenario bundle rows must be objects")
        scenario_id = row.get("id")
        if (
            not isinstance(scenario_id, str)
            or scenario_id not in ALL_SCENARIO_IDS
            or scenario_id in result
            or row.get("mode") != "discovery"
            or row.get("split") != "regression"
            or not isinstance(row.get("routing"), dict)
            or not isinstance(row.get("prompt"), str)
            or not isinstance(row.get("_source_sha256"), str)
            or not SHA256_RE.fullmatch(str(row["_source_sha256"]))
        ):
            raise ValueError("scenario bundle contains an invalid fixed scenario")
        result[scenario_id] = row
    if set(result) != ALL_SCENARIO_IDS:
        raise ValueError("scenario bundle does not match the fixed scenario set")
    return before, result


def validate_scenario_bundle(
    manifest: Mapping[str, object], scenarios: Mapping[str, dict]
) -> list[str]:
    problems: list[str] = []
    rows = manifest.get("scenarios")
    if not isinstance(rows, list):
        return ["manifest scenarios must be a list"]
    expected = {
        row.get("id"): row.get("sha256")
        for row in rows
        if isinstance(row, dict)
    }
    if set(expected) != ALL_SCENARIO_IDS or set(scenarios) != ALL_SCENARIO_IDS:
        problems.append("scenario bundle does not match the manifest scenario set")
        return problems
    for scenario_id, digest in expected.items():
        if scenarios[scenario_id].get("_source_sha256") != digest:
            problems.append(f"scenario bundle digest mismatch for {scenario_id}")
    if scenarios.get(CANARY_SCENARIO_ID) != manifest.get("canary_scenario"):
        problems.append("scenario bundle canary differs from the manifest canary")
    return problems


def runtime_profile(
    manifest: Mapping[str, object], *, manifest_path: Path
) -> codex_runtime.RuntimeProfile:
    problems = validate_manifest(manifest, None)
    if problems:
        raise ValueError("runtime profile requires one valid exact routing manifest")
    return codex_runtime.profile_from_manifest(manifest, manifest_path=manifest_path)


def validate_manifest(
    manifest: Mapping[str, object], scenarios: Mapping[str, dict] | None
) -> list[str]:
    problems: list[str] = []
    campaign = manifest.get("campaign")
    if campaign == "route-001-codex-terra-linux-v1":
        manifest_keys = LINUX_MANIFEST_KEYS
        expected_values = LINUX_EXPECTED_VALUES
    elif campaign == "route-001-codex-terra-v1":
        manifest_keys = WINDOWS_MANIFEST_KEYS
        expected_values = WINDOWS_EXPECTED_VALUES
    else:
        manifest_keys = LINUX_MANIFEST_KEYS
        expected_values = LINUX_EXPECTED_VALUES
        problems.append("manifest campaign is not one supported exact ROUTE-001 arm")
    unknown = set(manifest) - manifest_keys
    missing = manifest_keys - set(manifest)
    if unknown:
        problems.append(f"manifest has unknown keys: {', '.join(sorted(unknown))}")
    if missing:
        problems.append(f"manifest is missing keys: {', '.join(sorted(missing))}")
    for key, expected in expected_values.items():
        if manifest.get(key) != expected:
            problems.append(f"manifest {key} must be {expected!r}")
    before = manifest.get("before_revision")
    if not isinstance(before, str) or not REVISION_RE.fullmatch(before):
        problems.append("manifest before_revision must be a full lowercase Git SHA")

    rows = manifest.get("scenarios")
    if not isinstance(rows, list):
        return [*problems, "manifest scenarios must be a list"]
    seen: set[str] = set()
    cohort_ids = {"paired": set(), "current_only": set()}
    for index, row in enumerate(rows):
        where = f"manifest scenarios[{index}]"
        if not isinstance(row, dict):
            problems.append(f"{where} must be an object")
            continue
        row_unknown = set(row) - SCENARIO_KEYS
        row_missing = SCENARIO_KEYS - set(row)
        if row_unknown:
            problems.append(f"{where} has unknown keys: {', '.join(sorted(row_unknown))}")
        if row_missing:
            problems.append(f"{where} is missing keys: {', '.join(sorted(row_missing))}")
        scenario_id = row.get("id")
        cohort = row.get("cohort")
        digest = row.get("sha256")
        if not isinstance(scenario_id, str) or not SAFE_ID_RE.fullmatch(scenario_id):
            problems.append(f"{where} id must be a canonical lowercase slug")
            continue
        if scenario_id in seen:
            problems.append(f"{where} has duplicate scenario id {scenario_id}")
        seen.add(scenario_id)
        if cohort not in cohort_ids:
            problems.append(f"{where} cohort must be paired or current_only")
        else:
            cohort_ids[str(cohort)].add(scenario_id)
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            problems.append(f"{where} digest must be a lowercase SHA-256")
        if scenarios is not None:
            scenario = scenarios.get(scenario_id)
            if scenario is None:
                problems.append(f"{where} scenario is missing from the evaluator suite")
                continue
            if digest != scenario.get("_source_sha256"):
                problems.append(f"{where} scenario digest does not match evaluator bytes")
            if scenario.get("mode") != "discovery" or scenario.get("split") != "regression":
                problems.append(f"{where} must select a discovery regression scenario")
            if not isinstance(scenario.get("routing"), dict):
                problems.append(f"{where} has no routing contract")

    if seen != ALL_SCENARIO_IDS:
        problems.append("manifest must contain the exact ROUTE-001 scenario set")
    if cohort_ids["paired"] != PAIRED_IDS:
        problems.append("manifest paired cohort does not match the fixed five scenarios")
    if cohort_ids["current_only"] != CURRENT_ONLY_IDS:
        problems.append("manifest current_only cohort does not match the fixed fourteen scenarios")

    if scenarios is not None:
        import run_evals

        selected = [scenarios[item] for item in sorted(seen) if item in scenarios]
        problems.extend(run_evals.validate(selected))
    return problems


def validate_canary_scenario(manifest: Mapping[str, object]) -> list[str]:
    scenario = manifest.get("canary_scenario")
    if not isinstance(scenario, dict):
        return ["manifest canary_scenario must be an object"]
    canonical = json.dumps(
        scenario, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    problems: list[str] = []
    if hashlib.sha256(canonical).hexdigest() != CANARY_CANONICAL_SHA256:
        problems.append("manifest canary_scenario does not match the fixed canonical bytes")
    grader_specs = scenario.get("graders")
    if not isinstance(grader_specs, list) or not grader_specs:
        problems.append("manifest canary_scenario requires linear-only response graders")
    else:
        for index, grader_spec in enumerate(grader_specs):
            grader_type = (
                grader_spec.get("type") if isinstance(grader_spec, Mapping) else None
            )
            if grader_type not in CANARY_LINEAR_GRADER_TYPES:
                problems.append(
                    "manifest canary_scenario graders["
                    f"{index}] is outside the linear-only grader allowlist"
                )
    rows = manifest.get("scenarios")
    matching = (
        [row for row in rows if isinstance(row, dict) and row.get("id") == CANARY_SCENARIO_ID]
        if isinstance(rows, list)
        else []
    )
    if (
        len(matching) != 1
        or scenario.get("id") != CANARY_SCENARIO_ID
        or scenario.get("_source_sha256") != matching[0].get("sha256")
    ):
        problems.append("manifest canary_scenario is not bound to its fixed scenario row")
    return problems


def campaign_plan(manifest: Mapping[str, object], current_revision: str) -> list[TrialSpec]:
    if not REVISION_RE.fullmatch(current_revision):
        raise ValueError("current revision must be a full lowercase Git SHA")
    if current_revision != CURRENT_REVISION or manifest.get("current_revision") != CURRENT_REVISION:
        raise ValueError(f"current revision must be the fixed ROUTE-001 target {CURRENT_REVISION}")
    rows = manifest.get("scenarios")
    if not isinstance(rows, list):
        raise ValueError("manifest scenarios must be a list")
    trials = manifest.get("trials")
    if trials != TRIALS:
        raise ValueError(f"manifest trials must be {TRIALS}")
    plan: list[TrialSpec] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("manifest scenario rows must be objects")
        scenario_id = row.get("id")
        cohort = row.get("cohort")
        scenario_sha256 = row.get("sha256")
        if (
            not isinstance(scenario_id, str)
            or cohort not in {"paired", "current_only"}
            or not isinstance(scenario_sha256, str)
            or not SHA256_RE.fullmatch(scenario_sha256)
        ):
            raise ValueError("manifest contains an invalid scenario row")
        revisions = (BEFORE_REVISION, current_revision) if cohort == "paired" else (current_revision,)
        for revision in revisions:
            for trial in range(1, TRIALS + 1):
                plan.append(
                    TrialSpec(
                        scenario_id,
                        str(cohort),
                        revision,
                        trial,
                        scenario_sha256,
                    )
                )
    return plan


def canary_spec(
    manifest: Mapping[str, object], scenario_id: str = CANARY_SCENARIO_ID
) -> TrialSpec:
    """Return the one fixed development canary; it is not a campaign trial or baseline."""

    if scenario_id != CANARY_SCENARIO_ID:
        raise ValueError(f"canary scenario must be {CANARY_SCENARIO_ID}")
    canary_problems = validate_canary_scenario(manifest)
    if canary_problems:
        raise ValueError("fixed canary scenario contract is invalid")
    rows = manifest.get("scenarios")
    if not isinstance(rows, list):
        raise ValueError("manifest scenarios must be a list")
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("id") == CANARY_SCENARIO_ID
    ]
    if len(matches) != 1 or matches[0].get("cohort") != "current_only":
        raise ValueError("fixed canary is missing from the current-only manifest cohort")
    return TrialSpec(
        scenario_id=CANARY_SCENARIO_ID,
        cohort="current_only",
        revision=CURRENT_REVISION,
        trial=CANARY_TRIAL,
        scenario_sha256=str(matches[0]["sha256"]),
    )


def build_command(
    codex_bin: Path, workspace: Path, *, enable_multi_agent: bool
) -> tuple[str, ...]:
    """Build the fixed stdin-driven Codex command; prompt bytes never enter argv."""

    command = [
        str(codex_bin),
        "--enable" if enable_multi_agent else "--disable",
        "multi_agent",
    ]
    for feature in DISABLED_MODEL_FEATURES:
        command.extend(("--disable", feature))
    command.extend(
        (
        "--model",
        MODEL,
        "--sandbox",
        SANDBOX,
        "--ask-for-approval",
        APPROVAL_POLICY,
        "-c",
        f'model_reasoning_effort="{REASONING_EFFORT}"',
        "-c",
        'model_provider="openai"',
        "-c",
        'openai_base_url=""',
        "-c",
        'chatgpt_base_url="https://chatgpt.com/backend-api/"',
        "-c",
        'web_search="disabled"',
        "-c",
        "agents.max_concurrent_threads_per_session=1",
        "-c",
        "agents.max_depth=1",
        "--dangerously-bypass-hook-trust",
        "exec",
        "--json",
        "--strict-config",
        "--ephemeral",
        "--skip-git-repo-check",
        "--ignore-rules",
        "--color",
        "never",
        "--cd",
        str(workspace),
        "-",
        )
    )
    return tuple(command)


def render_config(
    python_executable: Path,
    recorder: Path,
    receipt_directory: Path,
    model_catalog: Path,
    nonce: str,
) -> str:
    """Render the entire disposable Codex config with three trusted sync hooks."""

    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ValueError("hook nonce must be exactly 32 lowercase hex characters")
    hook_paths = tuple(
        str(path.resolve()) for path in (python_executable, recorder, receipt_directory)
    )
    if any(not SAFE_HOOK_PATH_RE.fullmatch(value) for value in hook_paths):
        raise ValueError("hook command paths must use the fixed safe-character set")
    arguments = (
        hook_paths[0],
        "-E",
        "-s",
        "-S",
        "-B",
        hook_paths[1],
        "--receipt-directory",
        hook_paths[2],
        "--nonce",
        nonce,
    )
    posix_command = shlex.join(arguments)
    windows_command = subprocess.list2cmdline(arguments)
    lines = [
        f"model_catalog_json = {json.dumps(str(model_catalog.resolve()))}",
        'web_search = "disabled"',
        "",
        "[tools.update_plan]",
        "enabled = false",
        "",
        "[tools.experimental_request_user_input]",
        "enabled = false",
        "",
        "[skills.bundled]",
        "enabled = false",
        "",
        "[features]",
        "hooks = true",
        "multi_agent = true",
        "skill_search = true",
        *(f"{feature} = false" for feature in DISABLED_MODEL_FEATURES),
        "",
        "[orchestrator.skills]",
        "enabled = false",
        "",
        "[orchestrator.mcp]",
        "enabled = false",
        "",
    ]
    for event in ("SessionStart", "SubagentStart", "PostToolUse"):
        lines.extend(
            (
                f"[[hooks.{event}]]",
                f"[[hooks.{event}.hooks]]",
                'type = "command"',
                f"command = {json.dumps(posix_command)}",
                f"command_windows = {json.dumps(windows_command)}",
                "timeout = 10",
                "async = false",
                "",
            )
        )
    return "\n".join(lines)


def authority_facts(candidate: Mapping[str, object], *, exact_revision: bool) -> dict[str, object]:
    """Return report facts while keeping authority decisions outside model/runner control."""

    facts = {key: value for key, value in candidate.items() if key not in RESERVED_AUTHORITY}
    facts.update(
        {
            "source_review": "not-verified-by-runner",
            "independent_evaluator": False,
            "baseline_eligible": False,
            "release_granted": False,
            "exact_revision": bool(exact_revision),
        }
    )
    return facts


def require_isolated_canary_launch(manifest_path: Path) -> None:
    """Reject a canary unless the reviewed runner is executing from its isolated stage."""

    for name in ("isolated", "no_site", "dont_write_bytecode", "safe_path"):
        if not bool(getattr(sys.flags, name, False)):
            raise ValueError("canary interpreter isolation is incomplete")
    try:
        expected_entrypoint = (EVAL_ROOT / "run_codex_routing.py").resolve(strict=True)
        expected_manifests = {
            WINDOWS_MANIFEST_PATH.resolve(strict=True),
            LINUX_MANIFEST_PATH.resolve(strict=True),
        }
        observed_entrypoint = Path(sys.argv[0]).resolve(strict=True)
        observed_manifest = Path(manifest_path).resolve(strict=True)
        observed_import_root = Path(sys.path[-1]).resolve(strict=True)
    except (IndexError, OSError) as exc:
        raise ValueError("canary staged launch could not be resolved") from exc
    if (
        observed_entrypoint != expected_entrypoint
        or observed_manifest not in expected_manifests
        or observed_import_root != EVAL_ROOT
    ):
        raise ValueError("canary must execute the fixed staged entrypoint and manifest")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="print the fixed campaign shape")
    mode.add_argument(
        "--canary",
        action="store_true",
        help="run one paid, sanitized development trial; never campaign/baseline evidence",
    )
    mode.add_argument(
        "--preflight",
        action="store_true",
        help="exercise fixed credential-free setup without auth or a model request",
    )
    mode.add_argument(
        "--campaign",
        action="store_true",
        help="run or safely resume the fixed 48-trial Linux-container campaign",
    )
    parser.add_argument("--current-revision", help="full SHA used only with --plan")
    parser.add_argument("--codex-bin", type=Path, help="exact Codex 0.147 executable for --canary")
    parser.add_argument("--auth-file", type=Path, help="existing Codex auth.json for --canary")
    parser.add_argument(
        "--private-root",
        type=Path,
        help="externally protected private ancestor for the staged canary trial",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="source repository whose fixed Git objects are materialized for --canary",
    )
    parser.add_argument(
        "--campaign-root",
        type=Path,
        help="precreated private result root used only with --campaign",
    )
    parser.add_argument(
        "--container-image-id",
        help="immutable outer image ID used only with --campaign",
    )
    parser.add_argument(
        "--scenario-id",
        default=CANARY_SCENARIO_ID,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    try:
        manifest_before, manifest = load_stable_manifest(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"codex-terra-routing: invalid manifest: {exc}", file=sys.stderr)
        return 3
    scenario_map: dict[str, dict] | None = None
    live_mode = args.canary or args.preflight or args.campaign
    live_scenarios: dict[str, dict] | None = None
    if live_mode:
        problems = [
            *validate_manifest(manifest, None),
            *validate_canary_scenario(manifest),
        ]
        if args.campaign:
            try:
                _scenario_bytes, live_scenarios = load_stable_scenario_bundle(
                    expected_sha256=manifest.get("scenario_bundle_sha256")
                )
            except (OSError, ValueError) as exc:
                print(
                    f"codex-terra-routing: scenario bundle could not be frozen: {type(exc).__name__}",
                    file=sys.stderr,
                )
                return 3
            problems.extend(validate_scenario_bundle(manifest, live_scenarios))
    else:
        try:
            import run_evals

            scenarios, _suite_digest = run_evals.load_stable_suite()
        except (OSError, ValueError, run_evals.clean_room.RunnerFailed) as exc:
            print(
                f"codex-terra-routing: scenario suite could not be frozen: {type(exc).__name__}",
                file=sys.stderr,
            )
            return 3
        scenario_map = {item["id"]: item for item in scenarios}
        problems = validate_manifest(manifest, scenario_map)
    if problems:
        for problem in problems:
            print(f"codex-terra-routing: {problem}", file=sys.stderr)
        return 3
    if live_mode:
        if (
            args.codex_bin is None
            or args.repo_root is None
            or args.private_root is None
            or (args.campaign and args.campaign_root is None)
            or (args.campaign and args.container_image_id is None)
        ):
            print(
                "codex-terra-routing: live setup requires its fixed executable, repository, and private-root inputs",
                file=sys.stderr,
            )
            return 3
        if not args.campaign and args.container_image_id is not None:
            print(
                "codex-terra-routing: --container-image-id is campaign-only",
                file=sys.stderr,
            )
            return 3
        if args.preflight and args.auth_file is not None:
            print(
                "codex-terra-routing: --preflight rejects auth input",
                file=sys.stderr,
            )
            return 3
        if (args.canary or args.campaign) and args.auth_file is None:
            print(
                "codex-terra-routing: --canary requires its fixed auth input",
                file=sys.stderr,
            )
            return 3
        try:
            require_isolated_canary_launch(args.manifest)
            profile = runtime_profile(
                manifest, manifest_path=Path(args.manifest).resolve(strict=True)
            )
            if args.campaign and profile.runtime_kind != "linux-container":
                raise ValueError("the 48-trial executor is Linux-container only")
            import codex_trial

            common = {
                "repo_root": args.repo_root,
                "codex_bin": args.codex_bin,
                "manifest_sha256": hashlib.sha256(manifest_before).hexdigest(),
                "exact_revision": False,
                "temp_parent": args.private_root,
                "runtime_profile": profile,
            }
            if args.preflight:
                spec = canary_spec(manifest, args.scenario_id)
                result = codex_trial.run_preflight(
                    scenario=manifest["canary_scenario"],
                    spec=spec,
                    canary_body_probe=True,
                    **common,
                )
            elif args.campaign:
                if live_scenarios is None or args.campaign_root is None:
                    raise ValueError("campaign scenario or result boundary is unavailable")
                import codex_campaign

                plan = campaign_plan(manifest, CURRENT_REVISION)
                campaign_root = Path(args.campaign_root).resolve(strict=True)
                with codex_campaign.CampaignLock(campaign_root) as lock:
                    if (campaign_root / "campaign.json").is_file():
                        journal = codex_campaign.CampaignJournal.open(
                            campaign_root,
                            plan=plan,
                            manifest_sha256=common["manifest_sha256"],
                            container_image_id=args.container_image_id,
                            lock=lock,
                        )
                    else:
                        journal = codex_campaign.CampaignJournal.create(
                            campaign_root,
                            plan=plan,
                            manifest_sha256=common["manifest_sha256"],
                            container_image_id=args.container_image_id,
                            lock=lock,
                        )

                    def run_campaign_trial(item: TrialSpec) -> Mapping[str, object]:
                        trial_result = codex_trial.run_trial(
                            auth_file=args.auth_file,
                            scenario=live_scenarios[item.scenario_id],
                            spec=item,
                            **{**common, "exact_revision": True},
                        )
                        return trial_result.as_dict()

                    summary = codex_campaign.run_campaign(journal, run_campaign_trial)
                print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
                return 0 if summary["status"] == "complete" else 4
            else:
                spec = canary_spec(manifest, args.scenario_id)
                result = codex_trial.run_trial(
                    auth_file=args.auth_file,
                    scenario=manifest["canary_scenario"],
                    spec=spec,
                    canary_body_probe=True,
                    **common,
                )
        except (KeyError, OSError, ValueError) as exc:
            print(f"codex-terra-routing: canary contract failed: {type(exc).__name__}", file=sys.stderr)
            return 3
        if args.preflight:
            print(
                json.dumps(
                    {
                        "mode": "credential-free-preflight",
                        "authenticated_call_started": False,
                        "live_authorized": False,
                        "host_trust": "not-verified-by-runner",
                        "result": result.as_dict(),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0 if result.reason_codes == ("credential-free-preflight-pass",) else 4
        print(json.dumps(result.as_dict(), sort_keys=True, separators=(",", ":")))
        return {
            "PASS": 0,
            "FAIL": 2,
            "INCONCLUSIVE": 4,
        }[result.state.value]
    if args.plan:
        if not args.current_revision:
            print("codex-terra-routing: --plan requires --current-revision", file=sys.stderr)
            return 3
        try:
            plan = campaign_plan(manifest, args.current_revision)
        except ValueError as exc:
            print(f"codex-terra-routing: {exc}", file=sys.stderr)
            return 3
        before = sum(item.revision == BEFORE_REVISION for item in plan)
        print(
            json.dumps(
                {
                    "campaign": manifest["campaign"],
                    "model": MODEL,
                    "trials": len(plan),
                    "before_trials": before,
                    "current_trials": len(plan) - before,
                },
                sort_keys=True,
            )
        )
    else:
        print(f"codex-terra-routing: manifest valid ({len(manifest['scenarios'])} scenarios, 48 trials)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
