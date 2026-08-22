#!/usr/bin/env python3
"""Immutable runtime profile for the canonical Linux evaluator."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class RuntimeProfile:
    runtime_kind: str
    runtime_platform: str
    python_version: str
    python_executable_path: Path
    python_executable_sha256: str
    git_cli_version: str
    git_executable_path: Path
    git_executable_sha256: str
    codex_cli_version: str
    codex_executable_path: Path
    codex_executable_sha256: str
    manifest_path: Path
    evaluator_files: tuple[str, ...]
    container_user: str | None = None


LINUX_EVALUATOR_FILES = (
    "codex_campaign.py",
    "codex_harness.py",
    "codex_hook_recorder.py",
    "codex_model_catalog.py",
    "codex_routing_grade.py",
    "codex_runtime.py",
    "codex_snapshot.py",
    "codex_trial.py",
    "graders.py",
    "run_codex_routing.py",
    "conformance/codex-terra-routing-linux-v1.json",
    "conformance/codex-terra-scenarios-v1.json",
)


class RuntimeProfileError(ValueError):
    """A routing manifest does not describe one supported exact runtime."""


def _text(manifest: Mapping[str, object], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeProfileError(f"manifest {key} must be non-empty text")
    return value


def _sha(manifest: Mapping[str, object], key: str) -> str:
    value = _text(manifest, key)
    if not SHA256_RE.fullmatch(value):
        raise RuntimeProfileError(f"manifest {key} must be one lowercase SHA-256")
    return value


def profile_from_manifest(
    manifest: Mapping[str, object], *, manifest_path: Path
) -> RuntimeProfile:
    """Create a typed profile only after the caller has validated exact manifest values."""

    platform = _text(manifest, "runtime_platform")
    if platform != "linux-x86_64" or manifest.get("runtime_kind") != "linux-container":
        raise RuntimeProfileError("manifest runtime is not a supported exact profile")
    python_path = Path(_text(manifest, "python_executable_path"))
    git_path = Path(_text(manifest, "git_executable_path"))
    codex_path = Path(_text(manifest, "codex_executable_path"))
    if not all(
        PurePosixPath(_text(manifest, key)).is_absolute()
        for key in ("python_executable_path", "git_executable_path", "codex_executable_path")
    ):
        raise RuntimeProfileError("Linux runtime executable paths must be absolute")
    return RuntimeProfile(
        runtime_kind="linux-container",
        runtime_platform=platform,
        python_version=_text(manifest, "python_version"),
        python_executable_path=python_path,
        python_executable_sha256=_sha(manifest, "python_executable_sha256"),
        git_cli_version=_text(manifest, "git_cli_version"),
        git_executable_path=git_path,
        git_executable_sha256=_sha(manifest, "git_executable_sha256"),
        codex_cli_version=_text(manifest, "codex_cli_version"),
        codex_executable_path=codex_path,
        codex_executable_sha256=_sha(manifest, "codex_executable_sha256"),
        manifest_path=manifest_path,
        evaluator_files=LINUX_EVALUATOR_FILES,
        container_user=_text(manifest, "container_user"),
    )
