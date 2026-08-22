#!/usr/bin/env python3
"""Validate and run the fixed Codex/Terra ROUTE-001 preflight and canary."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
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
LINUX_MANIFEST_PATH = EVAL_ROOT / "conformance" / "codex-terra-routing-linux-v1.json"
MANIFEST_PATH = LINUX_MANIFEST_PATH
INSTRUMENT = "route-001-codex-terra-canary-v1"
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
TIMEOUT_S = 300
CURRENT_REVISION = "7aef80aede95394f6c4237ed2aedb911e141c3c0"
CANARY_SCENARIO_ID = "discovery-gcp-ops-cloud-run-startup"
CANARY_SOURCE_SHA256 = (
    "3d3507272fbe0e6d3ee28bf51ad33cf2d913c5afb2e69a79881fba5ce29712fd"
)
CANARY_EXPLICIT_SKILL = "gcp-ops"
CANARY_TRIAL = 1
CANARY_PROBE_MODES = frozenset({"body", "description"})
CANARY_DESCRIPTION_PROMPT_PREFIX = (
    "This is a skill-description selection check. Do not solve the task. Choose the one "
    "available skill whose description best matches it. Reply with exactly the bare skill name "
    "and no other text.\n\nTask:\n"
)
CANARY_SKILL_BODY_SHA256 = (
    "a319096742e87f45fa6e9cf3652247237a9aff3cdec7835cd775b78bd4dd3bd6"
)
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

SAFE_HOOK_PATH_RE = re.compile(r"^[A-Za-z0-9 _.:\\/\-]+$")

MANIFEST_KEYS = {
    "schema_version",
    "instrument",
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
    "tool_policy",
    "source_model_entry_sha256",
    "safe_model_catalog_sha256",
    "timeout_s",
    "current_revision",
    "snapshot_tree_sha256",
    "canary_scenario",
    "runtime_kind",
    "container_user",
    "base_image_digest",
    "python_executable_path",
    "codex_executable_path",
}
EXPECTED_VALUES = {
    "instrument": INSTRUMENT,
    "provider": "openai-codex",
    "codex_cli_version": codex_harness.CODEX_CLI_VERSION,
    "model": MODEL,
    "reasoning_effort": REASONING_EFFORT,
    "sandbox": SANDBOX,
    "approval_policy": APPROVAL_POLICY,
    "skill_activation_evidence": "behavioral-only-codex-0.148",
    "tool_policy": "no-model-tools-non-root",
    "source_model_entry_sha256": codex_model_catalog.EXPECTED_SOURCE_ENTRY_SHA256,
    "safe_model_catalog_sha256": codex_model_catalog.EXPECTED_SAFE_CATALOG_SHA256,
    "timeout_s": TIMEOUT_S,
    "current_revision": CURRENT_REVISION,
    "snapshot_tree_sha256": codex_snapshot.EXPECTED_SNAPSHOT_TREE_SHA256,
    "schema_version": 3,
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
}
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


def runtime_profile(
    manifest: Mapping[str, object], *, manifest_path: Path
) -> codex_runtime.RuntimeProfile:
    problems = [*validate_manifest(manifest), *validate_canary_scenario(manifest)]
    if problems:
        raise ValueError("runtime profile requires one valid exact canary manifest")
    return codex_runtime.profile_from_manifest(manifest, manifest_path=manifest_path)


def validate_manifest(manifest: Mapping[str, object]) -> list[str]:
    problems: list[str] = []
    unknown = set(manifest) - MANIFEST_KEYS
    missing = MANIFEST_KEYS - set(manifest)
    if unknown:
        problems.append(f"manifest has unknown keys: {', '.join(sorted(unknown))}")
    if missing:
        problems.append(f"manifest is missing keys: {', '.join(sorted(missing))}")
    for key, expected in EXPECTED_VALUES.items():
        if manifest.get(key) != expected:
            problems.append(f"manifest {key} must be {expected!r}")
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
    if (
        scenario.get("id") != CANARY_SCENARIO_ID
        or scenario.get("_source_sha256") != CANARY_SOURCE_SHA256
    ):
        problems.append("manifest canary_scenario is not bound to its fixed source digest")
    return problems


def canary_spec(
    manifest: Mapping[str, object], scenario_id: str = CANARY_SCENARIO_ID
) -> TrialSpec:
    """Return the one fixed development canary; it is not baseline evidence."""

    if scenario_id != CANARY_SCENARIO_ID:
        raise ValueError(f"canary scenario must be {CANARY_SCENARIO_ID}")
    canary_problems = validate_canary_scenario(manifest)
    if canary_problems:
        raise ValueError("fixed canary scenario contract is invalid")
    return TrialSpec(
        scenario_id=CANARY_SCENARIO_ID,
        revision=CURRENT_REVISION,
        trial=CANARY_TRIAL,
        scenario_sha256=CANARY_SOURCE_SHA256,
    )


def build_command(codex_bin: Path, workspace: Path) -> tuple[str, ...]:
    """Build the fixed stdin-driven Codex command; prompt bytes never enter argv."""

    command = [
        str(codex_bin),
        "--disable",
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
        "multi_agent = false",
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
        expected_manifest = LINUX_MANIFEST_PATH.resolve(strict=True)
        observed_entrypoint = Path(sys.argv[0]).resolve(strict=True)
        observed_manifest = Path(manifest_path).resolve(strict=True)
        observed_import_root = Path(sys.path[-1]).resolve(strict=True)
    except (IndexError, OSError) as exc:
        raise ValueError("canary staged launch could not be resolved") from exc
    if (
        observed_entrypoint != expected_entrypoint
        or observed_manifest != expected_manifest
        or observed_import_root != EVAL_ROOT
    ):
        raise ValueError("canary must execute the fixed staged entrypoint and manifest")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--canary",
        action="store_true",
        help="run one paid, sanitized development trial; never baseline evidence",
    )
    mode.add_argument(
        "--preflight",
        action="store_true",
        help="exercise fixed credential-free setup without auth or a model request",
    )
    parser.add_argument("--codex-bin", type=Path, help="exact Codex executable for a live probe")
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
        "--scenario-id",
        default=CANARY_SCENARIO_ID,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--canary-arm",
        choices=sorted(CANARY_PROBE_MODES),
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    if not args.canary and args.canary_arm is not None:
        print(
            "codex-terra-routing: --canary-arm is canary-only",
            file=sys.stderr,
        )
        return 3

    try:
        manifest_before, manifest = load_stable_manifest(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"codex-terra-routing: invalid manifest: {exc}", file=sys.stderr)
        return 3
    problems = [*validate_manifest(manifest), *validate_canary_scenario(manifest)]
    if problems:
        for problem in problems:
            print(f"codex-terra-routing: {problem}", file=sys.stderr)
        return 3
    live_mode = args.canary or args.preflight
    if live_mode:
        if (
            args.codex_bin is None
            or args.repo_root is None
            or args.private_root is None
        ):
            print(
                "codex-terra-routing: live setup requires its fixed executable, repository, and private-root inputs",
                file=sys.stderr,
            )
            return 3
        if args.preflight and args.auth_file is not None:
            print(
                "codex-terra-routing: --preflight rejects auth input",
                file=sys.stderr,
            )
            return 3
        if args.canary and args.auth_file is None:
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
                    canary_probe_mode="body",
                    **common,
                )
            else:
                spec = canary_spec(manifest, args.scenario_id)
                result = codex_trial.run_trial(
                    auth_file=args.auth_file,
                    scenario=manifest["canary_scenario"],
                    spec=spec,
                    canary_probe_mode=args.canary_arm or "body",
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
    print("codex-terra-routing: manifest valid (one fixed canary)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
