#!/usr/bin/env python3
"""Launch the fixed ROUTE-001 Linux boundary; canary mode preflights before one paid trial."""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MODES = frozenset({"preflight", "canary", "campaign"})
CONTAINER_USER = "65532:65532"
CONTAINER_UID = 65532
CANARY_RESULT_NAME = "canary-result.json"
CANARY_PROMPT_SHA256 = "65139f00bc31a3b18f82a3563f7a96c8300c40166ecd133f1c77227e681128c3"
MAX_CHILD_JSON_BYTES = 1024 * 1024
ENTRYPOINT = [
    "/usr/local/bin/python3.12",
    "-I",
    "-S",
    "-B",
    "/opt/route001/evals/run_codex_routing.py",
    "--manifest",
    "/opt/route001/evals/conformance/codex-terra-routing-linux-v1.json",
    "--repo-root",
    "/source",
    "--codex-bin",
    "/opt/route001/codex-runtime/bin/codex",
    "--private-root",
    "/run/route001",
]


class ContainerContractError(ValueError):
    """The host launch does not match the reviewed container boundary."""


@dataclass(frozen=True)
class ContainerInputs:
    image_id: str
    repository: Path
    output_root: Path
    auth_file: Path | None


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _normal_path(path: Path, *, label: str, directory: bool) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute() or candidate != Path(os.path.abspath(candidate)):
        raise ContainerContractError(f"{label} must be absolute and normalized")
    if _is_link_or_reparse(candidate):
        raise ContainerContractError(f"{label} must not be a link or reparse point")
    try:
        metadata = candidate.lstat()
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ContainerContractError(f"{label} is unavailable") from exc
    expected = stat.S_ISDIR(metadata.st_mode) if directory else stat.S_ISREG(metadata.st_mode)
    if not expected or resolved != candidate:
        raise ContainerContractError(f"{label} must be one ordinary exact path")
    if "," in str(candidate):
        raise ContainerContractError(f"{label} contains an unsupported Docker mount character")
    return candidate


def _mount(*, source: Path, target: str, readonly: bool) -> str:
    value = f"type=bind,source={source},target={target}"
    return value + (",readonly" if readonly else "")


def _host_requires_container_uid_ownership() -> bool:
    """Native Linux bind mounts preserve host ownership; Docker Desktop translates it."""

    return sys.platform.startswith("linux")


def _path_owner_uid(path: Path) -> int:
    return path.lstat().st_uid


def _require_container_uid_owner(path: Path, *, label: str) -> None:
    if (
        _host_requires_container_uid_ownership()
        and _path_owner_uid(path) != CONTAINER_UID
    ):
        raise ContainerContractError(
            f"{label} must be owned by UID {CONTAINER_UID} for the fixed native Linux container user"
        )


def _validate_inputs(mode: str, inputs: ContainerInputs) -> tuple[Path, Path, Path | None]:
    if mode not in MODES:
        raise ContainerContractError("mode must be preflight, canary, or campaign")
    if not IMAGE_ID_RE.fullmatch(inputs.image_id):
        raise ContainerContractError("container image must be one immutable image ID")
    repository = _normal_path(inputs.repository, label="repository", directory=True)
    git_path = repository / ".git"
    if _is_link_or_reparse(git_path) or not git_path.is_dir():
        raise ContainerContractError("repository must contain an ordinary Git directory")
    output = _normal_path(inputs.output_root, label="output root", directory=True)
    if os.name != "nt" and output.lstat().st_mode & 0o077:
        raise ContainerContractError("output root must be private to its owner")
    auth: Path | None = None
    if mode == "preflight":
        if inputs.auth_file is not None:
            raise ContainerContractError("credential-free preflight rejects auth input")
    else:
        if inputs.auth_file is None:
            raise ContainerContractError("live container modes require the fixed auth file")
        auth = _normal_path(inputs.auth_file, label="auth file", directory=False)
        if os.name != "nt" and auth.lstat().st_mode & 0o077:
            raise ContainerContractError("auth file must be private to its owner")
        if mode == "campaign":
            _require_container_uid_owner(output, label="output root")
        _require_container_uid_owner(auth, label="auth file")
    return repository, output, auth


def build_docker_command(mode: str, inputs: ContainerInputs) -> tuple[str, ...]:
    """Return the complete argument vector; no credential or provider secret enters it."""

    repository, output, auth = _validate_inputs(mode, inputs)
    command = [
        "docker",
        "run",
        "--rm",
        "--pull",
        "never",
        "--platform",
        "linux/amd64",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--pids-limit",
        "256",
        "--memory",
        "4g",
        "--cpus",
        "2",
        "--user",
        CONTAINER_USER,
        "--network",
        "none" if mode == "preflight" else "bridge",
        "--tmpfs",
        "/run/route001:rw,noexec,nosuid,nodev,size=2147483648,mode=0700,uid=65532,gid=65532",
        "--mount",
        _mount(source=repository, target="/source", readonly=True),
    ]
    if mode == "campaign":
        command.extend(
            ("--mount", _mount(source=output, target="/output", readonly=False))
        )
    if auth is not None:
        command.extend(
            (
                "--mount",
                _mount(source=auth, target="/run/secrets/auth.json", readonly=True),
            )
        )
    command.append(inputs.image_id)
    if mode == "preflight":
        command.append("--preflight")
    elif mode == "canary":
        command.extend(("--canary", "--auth-file", "/run/secrets/auth.json"))
    else:
        command.extend(
            (
                "--campaign",
                "--auth-file",
                "/run/secrets/auth.json",
                "--campaign-root",
                "/output",
                "--container-image-id",
                inputs.image_id,
            )
        )
    return tuple(command)


def validate_image_inspection(raw: str, *, image_id: str) -> Mapping[str, object]:
    """Validate Docker daemon facts before the reviewed image is launched."""

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContainerContractError("Docker image inspection was not JSON") from exc
    if not isinstance(parsed, list) or len(parsed) != 1 or not isinstance(parsed[0], dict):
        raise ContainerContractError("Docker image inspection must describe exactly one image")
    image = parsed[0]
    config = image.get("Config")
    rootfs = image.get("RootFS")
    if (
        image.get("Id") != image_id
        or image.get("Os") != "linux"
        or image.get("Architecture") != "amd64"
        or not isinstance(config, dict)
        or config.get("User") != CONTAINER_USER
        or config.get("Entrypoint") != ENTRYPOINT
        or config.get("WorkingDir") != "/"
        or not isinstance(rootfs, dict)
        or rootfs.get("Type") != "layers"
        or not isinstance(rootfs.get("Layers"), list)
        or not rootfs["Layers"]
    ):
        raise ContainerContractError("Docker image does not match the fixed runtime shape")
    return image


def inspect_image(image_id: str) -> Mapping[str, object]:
    if not IMAGE_ID_RE.fullmatch(image_id):
        raise ContainerContractError("container image must be one immutable image ID")
    try:
        process = subprocess.run(
            ["docker", "image", "inspect", image_id],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContainerContractError("Docker image inspection could not run") from exc
    if process.returncode != 0:
        raise ContainerContractError("the immutable Docker image is not available locally")
    return validate_image_inspection(process.stdout, image_id=image_id)


def _run_captured(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def _json_object(raw: str) -> dict[str, object] | None:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_CHILD_JSON_BYTES:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _reason_codes(value: object) -> list[str] | None:
    if (
        not isinstance(value, list)
        or not value
        or any(
            not isinstance(item, str)
            or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", item)
            for item in value
        )
    ):
        return None
    return list(value)


def _preflight_result(process: subprocess.CompletedProcess[str]) -> dict[str, object]:
    payload = _json_object(process.stdout)
    result = payload.get("result") if payload is not None else None
    reasons = _reason_codes(result.get("reason_codes")) if isinstance(result, dict) else None
    valid_envelope = (
        payload is not None
        and payload.get("mode") == "credential-free-preflight"
        and payload.get("authenticated_call_started") is False
        and payload.get("live_authorized") is False
        and reasons is not None
    )
    passed = (
        valid_envelope
        and process.returncode == 0
        and reasons == ["credential-free-preflight-pass"]
    )
    return {
        "passed": passed,
        "exit_code": process.returncode,
        "reason_codes": reasons if valid_envelope else ["preflight-output-invalid"],
    }


def _usage(payload: Mapping[str, object]) -> dict[str, int] | None:
    trace = payload.get("trace")
    value = trace.get("usage") if isinstance(trace, Mapping) else None
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count < 0
        for key, count in value.items()
    ):
        return None
    return dict(sorted(value.items()))


def _failed_grader_indices(payload: Mapping[str, object]) -> list[int] | None:
    """Reduce the trusted verdict to bounded numeric failure identifiers."""

    verdict = payload.get("verdict")
    behavior = verdict.get("behavior") if isinstance(verdict, Mapping) else None
    if not isinstance(behavior, Mapping):
        return None
    grader_count = behavior.get("grader_count")
    passed_count = behavior.get("passed_count")
    rows = behavior.get("graders")
    if (
        isinstance(grader_count, bool)
        or not isinstance(grader_count, int)
        or grader_count < 1
        or grader_count > 64
        or isinstance(passed_count, bool)
        or not isinstance(passed_count, int)
        or passed_count < 0
        or passed_count > grader_count
        or not isinstance(rows, list)
        or len(rows) != grader_count
    ):
        return None
    failed: list[int] = []
    observed_passed = 0
    for expected_index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != {"index", "passed"}:
            return None
        index = row.get("index")
        passed = row.get("passed")
        if (
            isinstance(index, bool)
            or index != expected_index
            or not isinstance(passed, bool)
        ):
            return None
        if passed:
            observed_passed += 1
        else:
            failed.append(expected_index)
    if observed_passed != passed_count:
        return None
    return failed


def _canary_result(process: subprocess.CompletedProcess[str]) -> tuple[dict[str, object], int]:
    payload = _json_object(process.stdout)
    state = payload.get("state") if payload is not None else None
    reasons = _reason_codes(payload.get("reason_codes")) if payload is not None else None
    configuration = payload.get("configuration") if payload is not None else None
    invocation_mode = (
        configuration.get("invocation_mode")
        if isinstance(configuration, dict)
        else None
    )
    scenario = payload.get("scenario") if payload is not None else None
    prompt_sha256 = (
        scenario.get("prompt_sha256") if isinstance(scenario, dict) else None
    )
    failed_grader_indices = (
        _failed_grader_indices(payload)
        if payload is not None and state in {"PASS", "FAIL"}
        else None
    )
    behavior_result_valid = (
        state == "INCONCLUSIVE"
        or (state == "PASS" and failed_grader_indices == [])
        or (state == "FAIL" and bool(failed_grader_indices))
    )
    expected_exit_code = {"PASS": 0, "FAIL": 2, "INCONCLUSIVE": 4}.get(state)
    if (
        state not in {"PASS", "FAIL", "INCONCLUSIVE"}
        or reasons is None
        or invocation_mode != "explicit-skill-body-probe"
        or prompt_sha256 != CANARY_PROMPT_SHA256
        or not behavior_result_valid
        or process.returncode != expected_exit_code
    ):
        return (
            {
                "started": True,
                "exit_code": process.returncode,
                "state": "INCONCLUSIVE",
                "reason_codes": ["canary-output-invalid"],
                "failed_grader_indices": None,
                "invocation_mode": None,
                "prompt_sha256": None,
                "usage": None,
            },
            3,
        )
    return (
        {
            "started": True,
            "exit_code": process.returncode,
            "state": state,
            "reason_codes": reasons,
            "failed_grader_indices": failed_grader_indices,
            "invocation_mode": invocation_mode,
            "prompt_sha256": prompt_sha256,
            "usage": _usage(payload),
        },
        process.returncode,
    )


def run_development_canary(inputs: ContainerInputs) -> tuple[int, dict[str, object]]:
    """Run one credential-free preflight and at most one authenticated trial."""

    canary_command = build_docker_command("canary", inputs)
    preflight_inputs = ContainerInputs(
        image_id=inputs.image_id,
        repository=inputs.repository,
        output_root=inputs.output_root,
        auth_file=None,
    )
    preflight = _preflight_result(
        _run_captured(build_docker_command("preflight", preflight_inputs))
    )
    summary: dict[str, object] = {
        "schema_version": 1,
        "image_id": inputs.image_id,
        "preflight": preflight,
        "canary": {
            "started": False,
            "exit_code": None,
            "state": None,
            "reason_codes": ["preflight-failed"],
            "failed_grader_indices": None,
            "invocation_mode": None,
            "prompt_sha256": None,
            "usage": None,
        },
    }
    if preflight["passed"] is not True:
        return (4 if preflight["exit_code"] == 4 else 3), summary

    canary, exit_code = _canary_result(
        _run_captured(canary_command)
    )
    summary["canary"] = canary
    return exit_code, summary


def _write_canary_result(output_root: Path, result: Mapping[str, object]) -> None:
    rendered = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".canary-result-",
            suffix=".tmp",
            dir=output_root,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output_root / CANARY_RESULT_NAME)
    except OSError as exc:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        raise ContainerContractError("canary result could not be written") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=sorted(MODES))
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="result directory; canary mode writes the latest canary-result.json",
    )
    parser.add_argument("--auth-file", type=Path)
    args = parser.parse_args(argv)
    inputs = ContainerInputs(
        image_id=args.image_id,
        repository=args.repository,
        output_root=args.output_root,
        auth_file=args.auth_file,
    )
    try:
        inspect_image(inputs.image_id)
        if args.mode == "canary":
            exit_code, result = run_development_canary(inputs)
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
            _write_canary_result(inputs.output_root, result)
            return exit_code
        command = build_docker_command(args.mode, inputs)
        process = subprocess.run(command, check=False)
    except ContainerContractError as exc:
        print(f"codex-container: {exc}", file=sys.stderr)
        return 3
    except OSError:
        print("codex-container: Docker launch failed", file=sys.stderr)
        return 3
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
