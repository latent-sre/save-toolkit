"""Independent pinned upstream SWT verifier; no image builds or author credentials.

The upstream six-variant run_instance and grading functions stay intact. Its
run_eval_exec_spec seam is replaced with fresh quota-bound containers and its
exec helper with bounded capture. Upstream's cache and host-PID cleanup fallback
are bypassed. Use a dedicated Python process; the supervisor owns its deadline.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from types import ModuleType
from typing import Any

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from swebench_adapter.artifacts import store_bytes, store_json
from swebench_adapter.containers import Docker
from swebench_adapter.limits import BoundedContainer, bounded_exec, run_bounded
from swebench_adapter.verifier import _CheckedBaseline, artifact_files

from swt_adapter.core import UPSTREAM_REVISION, VARIANTS, admit_patch, assess, digest, transform


def runtime_problems() -> list[str]:
    required = {
        "docker": "7.2.0",
        "unidiff": "0.7.5",
        "editdistance": "0.8.1",
        "GitPython": "3.2.1",
        "tqdm": "4.67.3",
        "datasets": "5.0.1",
        "python-dotenv": "1.2.2",
        "requests": "2.33.1",
    }
    problems = []
    for package, version in required.items():
        try:
            if metadata.version(package) != version:
                problems.append(f"{package}=={version} is required")
        except metadata.PackageNotFoundError:
            problems.append(f"{package}=={version} is required")
    return problems


def install_windows_import_guards() -> None:
    """Permit import-only Unix modules in the isolated Windows worker.

    Image building/locking and upstream CLI resource tuning are unavailable in
    this pinned-image execution profile. Reaching either path is an error; actual
    process limits come from WindowsJob and actual task limits from Docker.
    """

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("upstream Unix build/lock/resource path is unavailable in the pinned-image verifier")

    for name, symbols in {"fcntl": ("flock",), "resource": ("setrlimit",)}.items():
        if sys.modules.get(name) is not None:
            continue
        module = ModuleType(name)
        for symbol in symbols:
            setattr(module, symbol, unavailable)
        for constant in ("LOCK_EX", "LOCK_UN", "RLIMIT_NOFILE"):
            setattr(module, constant, -1)
        sys.modules[name] = module


def container_names(run_id: str) -> list[str]:
    if re.fullmatch(r"wp09-[a-z0-9-]{1,40}", run_id) is None:
        raise ValueError("invalid SWT run identity")
    return [f"{run_id}-{v.replace('_', '-')}" for v in VARIANTS]


def check_source(source: Path) -> None:
    def git(*args: str) -> bytes:
        return subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True, timeout=30).stdout

    if git("rev-parse", "HEAD").decode().strip() != UPSTREAM_REVISION:
        raise ValueError("SWT checkout revision mismatch")
    # Any extra source module could shadow a dependency; require clean checkout.
    if git("status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("SWT checkout must be clean")


def create_container(client: Any, image: str, name: str, base: str, receipt: dict[str, Any]) -> Any:
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image) is None or client.images.get(image).id != image:
        raise ValueError("verifier image must match immutable image Id")
    raw = client.containers.create(
        image=image,
        name=name,
        user="root",
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
        storage_opt={"size": "10G"},
    )
    return _CheckedBaseline(BoundedContainer(raw, storage_quota=True), base, receipt)


def swt_exec(container: Any, command: Any, timeout: float = 60) -> bytes:
    text, timed_out, _ = bounded_exec(container, command, timeout)
    if timed_out:
        raise TimeoutError("SWT variant deadline exceeded")
    return text.encode()


def worker_environment(home: Path, endpoint: str) -> dict[str, str]:
    env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP") if k in os.environ}
    env.update(HOME=str(home), DOCKER_HOST=endpoint, PYTHON_DOTENV_DISABLED="1", PYTHONNOUSERSITE="1")
    return env


def run_upstream(
    source: Path,
    row: dict[str, Any],
    patch: str,
    roots: list[str],
    output: Path,
    run_id: str,
    image: str,
    engine_id: str,
) -> dict[str, Any]:
    """Called only by the credential-free worker, after independent admission."""
    check_source(source)
    names = container_names(run_id)
    admission = admit_patch(patch, roots)
    if admission["state"] != "PASS":
        raise ValueError(admission["reason"])
    sys.path[:0] = [str(source.resolve()), str((source / "src").resolve())]
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    if os.name == "nt":
        install_windows_import_guards()
    upstream: Any = importlib.import_module("src.run_evaluation")
    grading = importlib.import_module("src.grading")
    docker = importlib.import_module("docker")
    client = docker.DockerClient(base_url=os.environ["DOCKER_HOST"], timeout=10)
    if client.info().get("ID") != engine_id or client.info().get("OSType") != "linux":
        raise ValueError("Docker engine identity mismatch")
    spec = upstream.make_test_spec(transform(row), exec_mode="unit_test")
    variants: dict[str, Any] = {}
    paths: list[Path] = []
    cleanup: list[dict[str, Any]] = []
    original_exec = upstream.exec_run_with_timeout
    original_run = upstream.run_eval_exec_spec

    def evaluate(exec_spec: Any, model_patch: str, log_dir: Any = None, build_mode: str = "api") -> tuple[str, Path]:
        name = exec_spec.patch_id.split("__")[0]
        if name not in VARIANTS or name in variants:
            raise ValueError("unexpected or repeated upstream variant")
        index = VARIANTS.index(name)
        if index != len(variants):
            raise ValueError("upstream variant order changed")
        evidence: dict[str, Any] = {"completed": False, "patch_applied": False, "tests": {}}
        variants[name] = evidence
        directory = output / name
        directory.mkdir(mode=0o700)
        logger, _ = upstream.setup_logging(directory, row["instance_id"])
        container = None
        try:
            container = create_container(client, image, names[index], row["base_commit"], evidence)
            container.start()
            path = Path(
                upstream.eval_in_container_with_diff(
                    directory,
                    container,
                    logger,
                    exec_spec.eval_script,
                    exec_spec.timeout,
                    row["instance_id"],
                    False,
                    build_mode="api",
                )
            )
            # Upstream get_logs_eval checks an applied-patch marker even for a variant
            # with no patch. For base_pre, absence is expected; errors still fail closed.
            tests, applied = grading.get_logs_eval(str(path), row["repo"], "unit_test")
            raw = path.read_text()
            no_patch = name == "base_pre"
            evidence.update(
                completed=True,
                patch_applied=applied
                or (
                    no_patch
                    and not any(
                        marker in raw
                        for marker in (
                            ">>>>> Patch Apply Failed",
                            ">>>>> Reset Failed",
                            ">>>>> Tests Errored",
                            ">>>>> Tests Timed Out",
                            "Failed to reset task environment",
                            "error: patch failed",
                            "error: corrupt patch",
                        )
                    )
                ),
                tests=tests,
            )
            artifact_files(output)
            paths.append(path)
            return row["instance_id"], path
        finally:
            clean = False
            try:
                if container is not None:
                    container.remove(force=True)
                clean = not client.containers.list(all=True, filters={"name": "^/" + names[index] + "$"})
            finally:
                cleanup.append({"name": names[index], "removed": clean})
                upstream.close_logger(logger)

    report: dict[str, Any] = {}
    failure = None
    try:
        upstream.exec_run_with_timeout = swt_exec
        upstream.run_eval_exec_spec = evaluate
        upstream.run_instance(
            spec,
            {"instance_id": row["instance_id"], "model_patch": patch, "model_name_or_path": "wp09-static-tests"},
            False,
            False,
            False,
            run_id,
            ["vanilla"],
            timeout=600,
            build_mode="api",
        )
        if len(paths) == 6:
            report = grading.get_pred_report(
                row["instance_id"],
                variants["pred_pre"]["patch_applied"],
                spec.golden_code_patch,
                [variants[v]["tests"] for v in VARIANTS],
                [{} for _ in VARIANTS],
                True,
            )
    except Exception as error:
        # Keep paths and partial observations; avoid serializing credentials from third-party errors.
        failure = type(error).__name__
    finally:
        upstream.exec_run_with_timeout = original_exec
        upstream.run_eval_exec_spec = original_run
        client.close()
    result = assess(row["instance_id"], report, variants, admission)
    result.update(
        outcome=result["mechanical"],
        instance_id=row["instance_id"],
        base_commit=row["base_commit"],
        row_sha256=digest(row),
        patch_sha256=admission["patch_sha256"],
        upstream_revision=UPSTREAM_REVISION,
        verifier_actor="independent-swt",
        # Independent verification cannot establish what the author executed.
        agent_executed_tests=None,
        image_id=image,
        docker_engine_id=engine_id,
        variants=variants,
        cleanup=cleanup,
        execution_failure=failure,
    )
    # Preserve supported mechanical evidence if later cleanup fails.
    result["cleanup_complete"] = len(cleanup) == 6 and all(c["removed"] for c in cleanup)
    artifact_files(output)
    store_json(output, "verifier-receipt.json", result)
    return result


def supervise(
    source: Path,
    row: dict[str, Any],
    patch: str,
    roots: list[str],
    output: Path,
    run_id: str,
    image: str,
    endpoint: str,
    engine_id: str,
) -> dict[str, Any]:
    """Bounded independent process; clean up its six exact container names on every exit."""
    check_source(source)
    names = container_names(run_id)
    docker = Docker()
    docker.pin(endpoint)
    info = json.loads(docker.call(["info", "--format", "{{json .}}"]).stdout)
    if info.get("ID") != engine_id or info.get("OSType") != "linux":
        raise ValueError("Docker engine identity mismatch")
    for name in names:
        if docker.call(["container", "ls", "-aq", "--filter", f"name=^/{name}$"]).stdout.strip():
            raise ValueError("verifier resource name already exists")
    if output.exists():
        raise ValueError("verifier destination already exists")
    output.mkdir(parents=True, mode=0o700)
    task = store_json(output, "task.json", row)
    candidate = store_bytes(output, "submitted.diff", patch.encode())
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--source",
        str(source.resolve()),
        "--task",
        str(task.resolve()),
        "--patch",
        str(candidate.resolve()),
        "--output",
        str(output.resolve()),
        "--run-id",
        run_id,
        "--image",
        image,
        "--engine-id",
        engine_id,
        "--roots",
        *roots,
    ]
    executed = run_bounded(command, cwd=output, env=worker_environment(output, endpoint), timeout=3900)
    cleanup = []
    for name in names:
        removed = False
        try:
            existing = docker.call(["container", "ls", "-aq", "--filter", f"name=^/{name}$"]).stdout.strip()
            if existing:
                docker.call(["container", "rm", "-f", name])
            removed = not docker.call(["container", "ls", "-aq", "--filter", f"name=^/{name}$"]).stdout.strip()
        except RuntimeError:
            pass
        cleanup.append({"name": name, "removed": removed})
    result = {
        "run_id": run_id,
        "exit_code": executed.returncode,
        "stop": executed.stop,
        "process_cleanup_complete": executed.cleanup_complete,
        "cleanup": cleanup,
        "receipt_available": (output / "verifier-receipt.json").is_file(),
    }
    store_json(output, "supervisor-receipt.json", result)
    store_bytes(output, "worker.stdout", executed.stdout)
    store_bytes(output, "worker.stderr", executed.stderr)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "task", "patch", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("run-id", "image", "engine-id"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--roots", nargs="+", required=True)
    args = parser.parse_args()
    result = run_upstream(
        args.source,
        json.loads(args.task.read_text()),
        args.patch.read_text(),
        args.roots,
        args.output,
        args.run_id,
        args.image,
        args.engine_id,
    )
    return 0 if result["mechanical"] in {"PASS", "FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
