"""Run the pinned independent SWE-bench verifier without model credentials.

The host passes a full pinned task row and the observed immutable Docker image Id.
Only the upstream create_container seam is replaced; run_instance and its grading
remain swebench==5.0.2. No dependency source is edited. Each invocation needs a
fresh run Id and output evidence paths. The predictable container name is
``sweb.eval.<instance_id.lower()>.<run_id>`` so the parent can clean it on timeout.
The parent owns the subprocess deadline, host storage cap and outer cleanup.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import json
import os
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from swebench_adapter.limits import BoundedContainer, bounded_exec

VERSION = "5.0.2"
MODEL_LABEL = "wp08"
EXIT_STATUS = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2}
ARTIFACT_LIMIT = 64 * 1024 * 1024
ARTIFACT_TOTAL = 256 * 1024 * 1024


def verifier_command(
    task_path: Path,
    patch_path: Path,
    output: Path,
    run_id: str,
    image_digest: str,
    *,
    baseline: bool = False,
    storage_quota: bool = False,
    engine_id: str | None = None,
    docker_host: str | None = None,
) -> list[str]:
    """Launch this file in the caller's project interpreter as an isolated process."""
    return (
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--task",
            str(task_path.resolve()),
            "--patch",
            str(patch_path.resolve()),
            "--output",
            str(output.resolve()),
            "--run-id",
            run_id,
            "--image-digest",
            image_digest,
        ]
        + (["--engine-id", engine_id] if engine_id is not None else [])
        + (["--docker-host", docker_host] if docker_host is not None else [])
        + (["--storage-quota"] if storage_quota else [])
        + (["--baseline"] if baseline else [])
    )


def artifact_files(root: Path) -> list[tuple[str, Path]]:
    """Validate the whole artifact inventory before allocating file contents."""
    result: list[tuple[str, Path]] = []
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("linked verifier artifact refused")
        if path.is_file():
            size = path.stat().st_size
            total += size
            if size > ARTIFACT_LIMIT or total > ARTIFACT_TOTAL or len(result) >= 4096:
                raise ValueError("verifier artifact limit exceeded")
            result.append((path.relative_to(root).as_posix(), path))
    return result


def read_artifact(path: Path) -> bytes:
    if path.is_symlink() or path.stat().st_size > ARTIFACT_LIMIT:
        raise ValueError("verifier artifact limit exceeded")
    with path.open("rb") as stream:
        data = stream.read(ARTIFACT_LIMIT + 1)
    if len(data) > ARTIFACT_LIMIT:
        raise ValueError("verifier artifact grew beyond its limit")
    return data


class _CheckedBaseline:
    """Attest the image's source before run_instance can apply any candidate patch.

    Untracked environment/build artifacts are preserved. A wrong HEAD or dirty
    tracked/index state is refused; the benchmark image is never silently reset.
    """

    def __init__(self, container: Any, base: str, receipt: dict[str, Any]) -> None:
        self.container, self.base, self.receipt = container, base, receipt

    def __getattr__(self, name: str) -> Any:
        return getattr(self.container, name)

    def start(self) -> None:
        self.container.start()
        state: dict[str, Any] = {
            "head": None,
            "tracked_clean": None,
            "index_clean": None,
            "replace_objects_disabled": True,
            "untracked_policy": "preserved",
        }
        self.receipt["initial_state"] = state
        git = [
            "git",
            "--no-replace-objects",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            "core.attributesFile=/dev/null",
        ]
        options = {
            "workdir": "/testbed",
            "environment": {
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            },
        }
        head = self.container.exec_run([*git, "rev-parse", "--verify", "HEAD^{commit}"], **options)
        if head.exit_code != 0:
            raise ValueError("verifier image HEAD is unavailable")
        observed = head.output.decode("ascii").strip()
        self.receipt["observed_base_commit"] = state["head"] = observed
        if observed != self.base:
            raise ValueError("verifier image HEAD differs from the selected base")
        for field, extra in (("tracked_clean", []), ("index_clean", ["--cached"])):
            result = self.container.exec_run(
                [*git, "diff", "--no-ext-diff", "--no-textconv", "--quiet", *extra], **options
            )
            state[field] = result.exit_code == 0
            if result.exit_code != 0:
                raise ValueError("verifier image source baseline is dirty or unavailable")


def _validate_task(task: Any, run_id: str, image_digest: str) -> None:
    if not isinstance(task, dict):
        raise ValueError("task must be a JSON object")
    for key in ("instance_id", "base_commit", "repo", "version", "image", "eval_script", "log_parser", "eval_type"):
        if not isinstance(task.get(key), str) or not task[key].strip():
            raise ValueError("task is missing required verifier fields")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", task["instance_id"]) is None:
        raise ValueError("invalid instance identifier")
    if re.fullmatch(r"[0-9a-f]{40}", task["base_commit"]) is None:
        raise ValueError("invalid base commit")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", run_id) is None:
        raise ValueError("invalid run identifier")
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image_digest) is None:
        raise ValueError("verifier requires an immutable Docker image Id")
    for field in ("FAIL_TO_PASS", "PASS_TO_PASS"):
        expected = task.get(field)
        if not isinstance(expected, list) or any(not isinstance(t, str) or not t.strip() for t in expected):
            raise ValueError("invalid expected test list")
        if len(set(expected)) != len(expected) or (field == "FAIL_TO_PASS" and not expected):
            raise ValueError("invalid expected test list")
    # The 5.0.2 harness fetches binary assets from the host; this static Python
    # repair profile has no such assets and must not introduce an unpinned fetch.
    if task.get("image_assets"):
        raise ValueError("network image assets are outside the verifier profile")


def _container_factory(
    image_digest: str,
    user: str,
    base: str,
    receipt: dict[str, Any],
    *,
    storage_quota: bool,
) -> Callable[..., Any]:
    def create(test_spec: Any, client: Any, run_id: str, logger: Any) -> Any:
        if test_spec.image != image_digest or client.images.get(image_digest).id != image_digest:
            raise ValueError("verifier image differs from the pinned image Id")
        raw = client.containers.create(
            image=image_digest,
            name=f"sweb.eval.{test_spec.instance_id.lower()}.{run_id}",
            user=user,
            detach=True,
            command="tail -f /dev/null",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            nano_cpus=2_000_000_000,
            mem_limit="2g",
            memswap_limit="2g",
            pids_limit=256,
            network_disabled=True,
            privileged=False,
            **({"storage_opt": {"size": "10G"}} if storage_quota else {}),
        )
        return _CheckedBaseline(BoundedContainer(raw, storage_quota=storage_quota), base, receipt)

    return create


def _classify(report: Any, task: Mapping[str, Any]) -> tuple[str, str | None]:
    instance_id = task["instance_id"]
    if not isinstance(report, dict) or set(report) != {instance_id} or not isinstance(report[instance_id], dict):
        return "INCONCLUSIVE", "verifier report does not identify exactly the requested instance"
    result = report[instance_id]
    flags = ("patch_is_None", "patch_exists", "patch_successfully_applied", "resolved", "infra_failure")
    if any(type(result.get(field)) is not bool for field in flags):
        return "INCONCLUSIVE", "verifier report is missing valid outcome flags"
    if result["infra_failure"]:
        return "INCONCLUSIVE", "upstream verifier reported an infrastructure failure"
    if result["patch_is_None"] or not result["patch_exists"] or not result["patch_successfully_applied"]:
        return "INCONCLUSIVE", "verifier report does not establish successful patch application and test execution"
    statuses = result.get("tests_status")
    failed = False
    for field in ("FAIL_TO_PASS", "PASS_TO_PASS"):
        bucket = statuses.get(field) if isinstance(statuses, dict) else None
        if not isinstance(bucket, dict) or set(bucket) != {"success", "failure"}:
            return "INCONCLUSIVE", "verifier report lacks complete expected-test evidence"
        success, failure = bucket["success"], bucket["failure"]
        if any(
            not isinstance(values, list) or any(not isinstance(t, str) for t in values) for values in (success, failure)
        ):
            return "INCONCLUSIVE", "verifier report has invalid test-result lists"
        if (
            len(set(success)) != len(success)
            or len(set(failure)) != len(failure)
            or set(success) & set(failure)
            or set(success) | set(failure) != set(task[field])
        ):
            return "INCONCLUSIVE", "verifier report does not account for every expected test exactly once"
        failed = failed or bool(failure)
    if result["resolved"] != (not failed):
        return "INCONCLUSIVE", "verifier resolution contradicts its expected-test evidence"
    return ("FAIL", "one or more expected tests failed") if failed else ("PASS", None)


def _cleanup(client: Any, name: str, not_found: Any, owned: bool) -> dict[str, Any]:
    evidence: dict[str, Any] = {"name": name, "present": None, "removed": False}
    try:
        container = client.containers.get(name)
        evidence["present"] = True
        if owned:
            with contextlib.suppress(Exception):
                container.remove(force=True, v=True)
            # Removal can fail after taking effect; only an independent lookup
            # establishes whether the resource remains.
            try:
                client.containers.get(name)
            except not_found:
                evidence.update(present=False, removed=True)
    except not_found:
        evidence.update(present=False, removed=True)
    except Exception:
        # A failed recheck makes presence unknown, even if removal was requested.
        evidence["present"] = None
    return evidence


def verify(
    task_path: Path,
    patch_path: Path,
    output: Path,
    run_id: str,
    image_digest: str,
    *,
    baseline: bool = False,
    storage_quota: bool = False,
    engine_id: str | None = None,
    docker_host: str | None = None,
) -> dict[str, Any]:
    """Write independently bound receipt/report evidence, returning the receipt.

    ``present`` in cleanup is the post-cleanup observation; null means Docker
    could not establish presence. ``removed`` means absence was established.
    Existing adapter evidence is refused without overwriting it.
    """
    output.mkdir(parents=True, exist_ok=True)
    if any((output / name).exists() for name in ("verifier-receipt.json", "verifier-report.json")):
        raise ValueError("output already contains verifier evidence")
    receipt: dict[str, Any] = {
        "instance_id": None,
        "baseline": baseline,
        "storage_quota": storage_quota,
        "docker_endpoint": docker_host,
        "docker_engine_id": None,
        "observed_base_commit": None,
        "initial_state": None,
        "interrupted": False,
        "base_commit": None,
        "patch_sha256": None,
        "swebench_version": None,
        "verifier_image_digest": image_digest,
        "command": verifier_command(
            task_path,
            patch_path,
            output,
            run_id,
            image_digest,
            baseline=baseline,
            storage_quota=storage_quota,
            engine_id=engine_id,
            docker_host=docker_host,
        ),
        "exit_status": 2,
        "report_path": "verifier-report.json",
        "evaluated_at": None,
        "outcome": "INCONCLUSIVE",
        "reason": "verifier did not complete",
        "cleanup": [],
    }
    raw_report: Any = {}
    client: Any = None
    harness: Any = None
    name: str | None = None
    owned = False
    try:
        task = json.loads(read_artifact(task_path))
        if isinstance(task, dict):
            receipt.update(instance_id=task.get("instance_id"), base_commit=task.get("base_commit"))
        patch_bytes = read_artifact(patch_path)
        receipt["patch_sha256"] = hashlib.sha256(patch_bytes).hexdigest()
        _validate_task(task, run_id, image_digest)
        patch = patch_bytes.decode("utf-8")
        receipt["swebench_version"] = metadata.version("swebench")
        if receipt["swebench_version"] != VERSION:
            raise ValueError("swebench==5.0.2 is required")
        if not patch.strip() and not baseline:
            receipt.update(outcome="FAIL", reason="candidate patch is empty")
        else:
            # mkdir is exclusive: run_instance's cached-report branch cannot run.
            log_root = output / "harness-logs"
            log_root.mkdir(exist_ok=True)
            (log_root / run_id).mkdir()
            harness = importlib.import_module("swebench.harness.run_evaluation")
            if (
                not isinstance(engine_id, str)
                or not engine_id
                or not isinstance(docker_host, str)
                or os.environ.get("DOCKER_HOST") != docker_host
                or not (docker_host.startswith("unix:///") or docker_host.startswith("npipe:////./pipe/"))
            ):
                raise ValueError("verifier requires the explicitly pinned local Docker endpoint")
            client = harness._docker_client()
            info = client.info()
            receipt["docker_engine_id"] = info.get("ID") if isinstance(info, dict) else None
            if receipt["docker_engine_id"] != engine_id:
                raise ValueError("verifier Docker engine differs from its parent")
            name = f"sweb.eval.{task['instance_id'].lower()}.{run_id}"
            try:
                client.containers.get(name)
            except harness.docker.errors.NotFound:
                owned = True
            else:
                raise ValueError("verifier container name already exists")
            fields = (
                "instance_id",
                "repo",
                "version",
                "eval_script",
                "log_parser",
                "eval_type",
                "FAIL_TO_PASS",
                "PASS_TO_PASS",
            )
            spec = harness.make_test_spec({**{field: task[field] for field in fields}, "image": image_digest})
            prediction = {"instance_id": task["instance_id"], "model_name_or_path": MODEL_LABEL, "model_patch": patch}
            original_factory, original_logs = harness.create_container, harness.RUN_EVALUATION_LOG_DIR
            original_exec = harness.exec_run_with_timeout
            harness.create_container = _container_factory(
                image_digest, harness.CONTAINER_USER, task["base_commit"], receipt, storage_quota=storage_quota
            )
            harness.exec_run_with_timeout = bounded_exec
            harness.RUN_EVALUATION_LOG_DIR = log_root
            try:
                result = harness.run_instance(
                    spec,
                    prediction,
                    client,
                    run_id,
                    timeout=2700,
                    rewrite_reports=False,
                    skip_patch=baseline,
                    task_repo=None,
                )
            finally:
                harness.create_container, harness.RUN_EVALUATION_LOG_DIR = original_factory, original_logs
                harness.exec_run_with_timeout = original_exec
            artifact_files(output)
            initial = receipt["initial_state"]
            if (
                receipt["observed_base_commit"] != task["base_commit"]
                or not isinstance(initial, dict)
                or initial.get("tracked_clean") is not True
                or initial.get("index_clean") is not True
            ):
                raise ValueError("verifier image base was not established")
            logs = log_root / run_id / MODEL_LABEL / task["instance_id"]
            if result is None:
                log_path = logs / harness.LOG_INSTANCE
                log = read_artifact(log_path).decode("utf-8") if log_path.is_file() else ""
                prefix = r"(?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - INFO - )?"
                if re.search(rf"^{prefix}{re.escape(harness.APPLY_PATCH_FAIL)}:[ \t]*$", log, re.MULTILINE):
                    receipt.update(
                        outcome="FAIL", reason="upstream verifier explicitly recorded patch application failure"
                    )
                else:
                    receipt["reason"] = "upstream verifier returned no result"
            else:
                raw_report = json.loads(read_artifact(logs / harness.LOG_REPORT))
                if (
                    not isinstance(result, tuple)
                    or len(result) != 2
                    or result[0] != task["instance_id"]
                    or result[1] != raw_report
                ):
                    raise ValueError("returned verifier result disagrees with the fresh report")
                outcome, reason = _classify(raw_report, task)
                receipt.update(outcome=outcome, reason=reason)
    except KeyboardInterrupt:
        receipt.update(interrupted=True, outcome="INCONCLUSIVE", reason="verifier interrupted")
    except Exception:
        receipt.update(
            outcome="INCONCLUSIVE", reason="verifier setup, identity, execution or evidence validation failed"
        )
    finally:
        if client is not None:
            if name is not None:
                cleanup = _cleanup(client, name, harness.docker.errors.NotFound, owned)
                receipt["cleanup"] = [cleanup]
                if cleanup["present"] is not False or cleanup["removed"] is not True:
                    receipt.update(outcome="INCONCLUSIVE", reason="verifier container cleanup is unresolved")
            with contextlib.suppress(Exception):
                client.close()
        receipt["exit_status"] = EXIT_STATUS[receipt["outcome"]]
        receipt["evaluated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        (output / "verifier-report.json").write_text(json.dumps(raw_report, indent=2) + "\n", encoding="utf-8")
        (output / "verifier-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--baseline", action="store_true", help="run baseline tests with no candidate patch")
    parser.add_argument("--storage-quota", action="store_true")
    parser.add_argument("--engine-id")
    parser.add_argument("--docker-host")
    args = parser.parse_args(argv)
    try:
        receipt = verify(
            args.task,
            args.patch,
            args.output,
            args.run_id,
            args.image_digest,
            baseline=args.baseline,
            storage_quota=args.storage_quota,
            engine_id=args.engine_id,
            docker_host=args.docker_host,
        )
    except (OSError, ValueError):
        print("verifier output cannot be created or already contains evidence", file=sys.stderr)
        return 3
    return int(receipt["exit_status"])


if __name__ == "__main__":
    raise SystemExit(main())
