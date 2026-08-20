#!/usr/bin/env python3
"""Build and launch the fixed headless Linux Docker boundary for ROUTE-001."""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MODES = frozenset({"preflight", "canary", "campaign"})
CONTAINER_USER = "65532:65532"
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
        "--mount",
        _mount(source=output, target="/output", readonly=False),
    ]
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=sorted(MODES))
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
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
