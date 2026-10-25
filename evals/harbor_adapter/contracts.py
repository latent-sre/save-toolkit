"""Offline provenance, candidate/hidden separation and strict upstream reward mapping."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from typing import Any

HARBOR_VERSION = "0.24.0"
HARBOR_COMMIT = "b53b8134e1241686dca7759af188f987ecc48e8b"
HARBOR_WHEEL_SHA256 = "23b7ba616a3aae4eff561ced5e2c51c7186f2981e53a770dea9c689d3969877c"
SOURCE_COMMIT = "2fd12b88aafdd04a52c298e3940bcb189f9766d6"
TASK_NAMES = (
    "cancel-async-tasks",
    "llm-inference-batching-scheduler",
    "write-compressor",
    "db-wal-recovery",
    "kv-store-grpc",
)
PROFILE = "static authoring, independently verified (DEC-13); Terminal-Bench submission-script adaptation v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("JSON must be a bounded regular file")
    return json.loads(path.read_bytes(), object_pairs_hook=_pairs)


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    if (
        not isinstance(manifest, dict)
        or manifest.get("format") != "wp09-terminal-selection"
        or manifest.get("schema_version") != 1
        or manifest.get("source_commit") != SOURCE_COMMIT
        or manifest.get("harbor", {}).get("wheel_sha256") != HARBOR_WHEEL_SHA256
    ):
        raise ValueError("unsupported Terminal-Bench manifest identity")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or [c.get("source_path") for c in cases] != list(TASK_NAMES):
        raise ValueError("selection must retain the frozen five tasks in order")
    for case in cases:
        name = case["source_path"]
        if (
            case.get("task_id") != f"terminal-bench/{name}"
            or case.get("local_case_id") != f"wp09-terminal-static-v1-{name}"
            or case.get("content_sha256") != canonical_digest(case.get("files"))
        ):
            raise ValueError("task identity or source digest mismatch")
        files = case["files"]
        if (
            not isinstance(files, dict)
            or not {"instruction.md", "task.toml", "environment/Dockerfile", "tests/test.sh", "solution/solve.sh"}
            <= files.keys()
        ):
            raise ValueError("incomplete Harbor task layout")
        for relative, digest in files.items():
            parts = Path(relative).parts
            if (
                not parts
                or Path(relative).is_absolute()
                or ".." in parts
                or "\\" in relative
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
            ):
                raise ValueError("invalid frozen source path/digest")
    return manifest


def verify_source(source: Path, case: dict[str, Any]) -> Path:
    task = source / str(case["source_path"])
    for relative, expected in case["files"].items():
        path = task / relative
        if (
            not path.is_file()
            or any(parent.is_symlink() for parent in [path, *path.parents])
            or sha256(path) != expected
        ):
            raise ValueError(f"source mismatch: {case['source_path']}/{relative}")
    actual = {path.relative_to(task).as_posix() for path in task.rglob("*") if path.is_file()}
    if actual != set(case["files"]):
        raise ValueError("source tree contains unrecorded files")
    return task


def stage_task(source: Path, case: dict[str, Any], output: Path) -> dict[str, Any]:
    """Stage host-owned task bytes and a separate candidate-visible source tree; execute nothing."""
    task = verify_source(source, case)
    visible = case.get("candidate_source_files", [])
    expected_visible = [
        name
        for name in case["files"]
        if name == "instruction.md"
        or (name.startswith("environment/") and name not in {"environment/Dockerfile", "environment/main.rs"})
    ]
    if visible != expected_visible:
        raise ValueError("candidate staging differs from upstream Docker COPY inputs")
    if output.exists():
        raise ValueError("staging output must be new")
    output.mkdir(parents=True)
    try:
        for relative in case["files"]:
            src = task / relative
            dst = output / "verifier-task" / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            if relative in case["candidate_source_files"]:
                visible = output / "author-input" / relative
                visible.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, visible)
        receipt = {
            "format": "wp09-terminal-staging",
            "schema_version": 1,
            "task_id": case["task_id"],
            "local_case_id": case["local_case_id"],
            "source_commit": SOURCE_COMMIT,
            "content_sha256": case["content_sha256"],
            "execution_profile": PROFILE,
            "author_inputs": ["author-input/instruction.md", "author-input/environment/"],
            "hidden_inputs": ["verifier-task/tests/", "verifier-task/solution/"],
            "environment_execution": "unmeasured",
            "candidate_trial": "not_started",
        }
        (output / "staging.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return receipt
    except BaseException:
        shutil.rmtree(output)
        raise


def reward_assessment(verifier_dir: Path) -> dict[str, Any]:
    """Preserve raw upstream files; admit only the selected tasks' scalar binary reward."""
    result: dict[str, Any] = {
        "verdict": "INCONCLUSIVE",
        "reason": "reward unavailable",
        "rewards": None,
        "upstream_reward_json": None,
        "upstream_reward_text": None,
    }
    try:
        for suffix, key in (("json", "upstream_reward_json"), ("txt", "upstream_reward_text")):
            path = verifier_dir / f"reward.{suffix}"
            if path.is_symlink():
                raise ValueError("reward symlink refused")
            if path.exists():
                if not path.is_file() or path.stat().st_size > 65536:
                    raise ValueError("invalid reward file")
                result[key] = path.read_text()
        if result["upstream_reward_json"] is not None:
            rewards = json.loads(result["upstream_reward_json"], object_pairs_hook=_pairs)
            if not isinstance(rewards, dict) or set(rewards) != {"reward"}:
                raise ValueError("selected tasks require exactly one reward")
            value = rewards["reward"]
        elif result["upstream_reward_text"] is not None:
            value = float(result["upstream_reward_text"])
        else:
            return result
        if type(value) not in (int, float) or not math.isfinite(value) or value not in (0, 1):
            raise ValueError("selected tasks require a finite binary reward")
        result.update(
            rewards={"reward": value}, verdict="PASS" if value == 1 else "FAIL", reason="upstream binary task reward"
        )
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError) as exc:
        result["reason"] = type(exc).__name__ + ": invalid or unavailable reward"
    return result
