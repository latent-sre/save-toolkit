"""Offline configuration validation and exact identity gates for WP-08."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from probe.fingerprints import HARNESS_FILES, plugin_digest

_ROOT = Path(__file__).resolve().parents[2]
_MAX_JSON = 8 * 1024 * 1024
_FIELDS = frozenset(
    {
        "schema_version",
        "plugin_root",
        "cli_path",
        "cli_sha256",
        "cli_version",
        "model",
        "haiku_model",
        "images",
        "proxy_bind",
        "proxy_target",
        "storage_quota",
        "api_key_helper",
    }
)
_RUNTIME = ("model", "haiku_model", "images", "proxy_bind", "proxy_target", "storage_quota", "api_key_helper")
_CHECKS = (
    "reference_resolves",
    "empty_rejected",
    "guard_allow",
    "guard_deny",
    "no_cr",
    "history_pruned",
    "egress",
    "cpu_cap",
    "storage_cap",
    "cleanup",
)
_SECRET = re.compile(r"(?i)(?:\bbearer\s+\S+|\bsk-[a-z0-9_-]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY)")


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError, UnicodeError):
        raise ValueError("identity requires canonical JSON") from None


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate config field")
        result[key] = value
    return result


def _constant(_value: str) -> None:
    raise ValueError("nonfinite config number")


def _secret(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_SECRET.search(value))
    if isinstance(value, dict):
        return any(_secret(key) or _secret(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_secret(child) for child in value)
    return False


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _native_cli(path: Path, expected: Any) -> bool:
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None or not path.is_file():
        return False
    with path.open("rb") as stream:
        magic = stream.read(4)
    binary = magic.startswith((b"\x7fELF", b"MZ")) or magic in {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
    }
    return binary and _file_sha256(path) == expected


def load_config(path: Path) -> dict[str, Any]:
    """Validate local files and pins; never invoke the CLI, Docker, or dependencies."""
    try:
        if not path.is_file() or path.stat().st_size > _MAX_JSON:
            raise ValueError
        raw = path.read_bytes()
        if len(raw) > _MAX_JSON:
            raise ValueError
        config = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise ValueError("invalid configuration JSON") from None
    if not isinstance(config, dict) or set(config) - _FIELDS or (_FIELDS - {"api_key_helper"}) - set(config):
        raise ValueError("invalid configuration fields")
    if _secret(config):
        raise ValueError("configuration must not contain credentials")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ValueError("invalid configuration schema_version")
    for name in ("plugin_root", "cli_path", "cli_version"):
        if not isinstance(config[name], str) or not config[name].strip() or "\x00" in config[name]:
            raise ValueError(f"invalid configuration {name}")
    try:
        root = path.resolve().parent
        plugin = (root / config["plugin_root"]).resolve(strict=True)
        cli = (root / config["cli_path"]).resolve(strict=True)
        if not plugin.is_dir():
            raise ValueError("invalid configuration plugin_root")
        if not _native_cli(cli, config["cli_sha256"]):
            raise ValueError("invalid configuration cli binary or digest")
    except (OSError, RuntimeError):
        raise ValueError("configuration plugin_root or cli_path is unavailable") from None
    if config["model"] != "anthropic/claude-sonnet-5.5":
        raise ValueError("invalid configuration model")
    haiku = config["haiku_model"]
    if (
        not isinstance(haiku, str)
        or re.fullmatch(r"anthropic/claude-haiku-[0-9][a-z0-9.-]*", haiku) is None
        or "latest" in haiku
    ):
        raise ValueError("invalid configuration haiku_model")
    images = config["images"]
    if not isinstance(images, dict) or not images:
        raise ValueError("invalid configuration images")
    for instance, image in images.items():
        if not isinstance(instance, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}", instance) is None:
            raise ValueError("invalid configuration image instance")
        if not isinstance(image, dict) or set(image) != {"reference", "image_id"}:
            raise ValueError("invalid configuration image fields")
        if (
            not isinstance(image["reference"], str)
            or re.fullmatch(r"[a-z0-9][a-z0-9./_:-]*@sha256:[0-9a-f]{64}", image["reference"]) is None
        ):
            raise ValueError("invalid configuration image reference")
        if not isinstance(image["image_id"], str) or re.fullmatch(r"sha256:[0-9a-f]{64}", image["image_id"]) is None:
            raise ValueError("invalid configuration image_id")
    try:
        ipaddress.IPv4Address(config["proxy_bind"])
    except (ipaddress.AddressValueError, TypeError):
        raise ValueError("invalid configuration proxy_bind") from None
    if not isinstance(config["proxy_bind"], str) or config["proxy_target"] != "host.docker.internal":
        raise ValueError("invalid configuration proxy target")
    config.setdefault("api_key_helper", False)
    for name in ("storage_quota", "api_key_helper"):
        if type(config[name]) is not bool:
            raise ValueError(f"invalid configuration {name}")
    config.update(plugin_root=str(plugin), cli_path=str(cli))
    return config


def adapter_digest() -> str:
    """Hash every adapter module plus entrypoint, imported harness and dependency pins."""
    paths = {
        *(_ROOT / "evals/swebench_adapter").glob("*.py"),
        _ROOT / "evals/swebench_repair.py",
        *HARNESS_FILES,
        _ROOT / "requirements-dev.txt",
        _ROOT / "requirements-test.txt",
        _ROOT / "requirements-swebench.txt",
    }
    digest = hashlib.sha256()
    try:
        for path in sorted(paths, key=lambda item: item.relative_to(_ROOT).as_posix()):
            if path.is_symlink() or not path.is_file():
                raise ValueError
            digest.update(path.relative_to(_ROOT).as_posix().encode("utf-8") + b"\0")
            digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    except (OSError, ValueError):
        raise ValueError("adapter identity inputs are unavailable") from None
    return digest.hexdigest()


def binding(config: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Bind exact selection, measured plugin, CLI, adapter and runtime configuration."""
    try:
        if not _native_cli(Path(config["cli_path"]), config["cli_sha256"]):
            raise ValueError("configuration cli changed")
        result = {
            "schema_version": 1,
            "selection_sha256": hashlib.sha256(_canonical(manifest)).hexdigest(),
            "plugin_sha256": plugin_digest(Path(config["plugin_root"])),
            "cli_sha256": config["cli_sha256"],
            "cli_version": config["cli_version"],
            "adapter_sha256": adapter_digest(),
            **{name: config[name] for name in _RUNTIME},
        }
        return dict(json.loads(_canonical(result)))
    except OSError:
        raise ValueError("configuration cli or binding inputs are unavailable") from None


def _local_docker_host(value: str) -> bool:
    try:
        host = urlsplit(value)
        if host.scheme == "unix":
            return not host.netloc and host.path.startswith("/") and not host.query and not host.fragment
        if host.scheme == "npipe":
            return value.startswith("npipe:////./pipe/")
        if (
            host.scheme == "tcp"
            and not host.username
            and not host.password
            and not host.path
            and not host.query
            and not host.fragment
        ):
            return host.hostname == "localhost" or ipaddress.ip_address(host.hostname or "").is_loopback
    except ValueError:
        return False
    return False


def dependency_problems() -> list[str]:
    """Inspect availability and metadata only; no executable or daemon calls."""
    problems = []
    if shutil.which("docker") is None:
        problems.append("Docker executable is unavailable")
    try:
        if metadata.version("swebench") != "5.0.2":
            problems.append("swebench==5.0.2 is required")
    except metadata.PackageNotFoundError:
        problems.append("swebench==5.0.2 is not installed")
    if sys.version_info < (3, 12):  # noqa: UP036 -- admission must diagnose unsupported operator interpreters
        problems.append("Python 3.12 or later is required")
    if os.environ.get("DOCKER_HOST") and not _local_docker_host(os.environ["DOCKER_HOST"]):
        problems.append("DOCKER_HOST must identify a local daemon")
    if os.environ.get("DOCKER_CONTEXT") not in (None, "", "default"):
        problems.append("DOCKER_CONTEXT override cannot establish a local daemon")
    return problems


def _git(cwd: Path, *args: str) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", "--no-optional-locks", "--literal-pathspecs", *args],
            cwd=cwd,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def selection_committed(path: Path) -> bool:
    """Prove tracked, unstaged and staged-clean bytes equal HEAD without mutating Git."""
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_JSON:
            return False
        path = path.resolve(strict=True)
        top = _git(path.parent, "rev-parse", "--show-toplevel")
        if not top:
            return False
        root = Path(os.fsdecode(top).strip()).resolve()
        relative = path.relative_to(root).as_posix()
        if _git(root, "ls-files", "--error-unmatch", "--", relative) is None:
            return False
        if _git(root, "diff", "--no-ext-diff", "--no-textconv", "--quiet", "HEAD", "--", relative) is None:
            return False
        if _git(root, "diff", "--no-ext-diff", "--no-textconv", "--cached", "--quiet", "HEAD", "--", relative) is None:
            return False
        size = _git(root, "cat-file", "-s", f"HEAD:{relative}")
        if size is None or not size.strip().isdigit() or int(size) > _MAX_JSON:
            return False
        expected = _git(root, "cat-file", "blob", f"HEAD:{relative}")
        return expected is not None and path.read_bytes() == expected
    except (OSError, ValueError, RuntimeError):
        return False


def smoke_problem(receipt: Mapping[str, Any], bound: Mapping[str, Any]) -> str | None:
    """Name the first missing smoke prerequisite; unknown evidence never passes."""
    if not isinstance(receipt, Mapping) or receipt.get("format") != "wp08-smoke":
        return "smoke format must be wp08-smoke"
    if type(receipt.get("schema_version")) is not int or receipt["schema_version"] != 1:
        return "smoke schema_version must be 1"
    if receipt.get("error") is not None:
        return "smoke recorded an error"
    try:
        if _canonical(receipt.get("binding")) != _canonical(bound):
            return "smoke binding does not match the current candidate"
    except ValueError:
        return "smoke binding is invalid"
    checks = receipt.get("checks")
    if not isinstance(checks, Mapping):
        return "smoke checks are missing"
    for name in _CHECKS:
        if checks.get(name) is not True:
            return f"smoke check {name} is missing or did not pass"
    cleanup = receipt.get("cleanup")
    if not isinstance(cleanup, list) or not cleanup:
        return "smoke cleanup evidence is missing"
    if any(not isinstance(item, Mapping) or item.get("present") is not False for item in cleanup):
        return "smoke cleanup has unconfirmed resource absence"
    return None
