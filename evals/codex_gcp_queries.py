"""Precompile bounded synthetic GCP01 query receipts for the Codex adapter.

Only trusted fixture setup calls this module. Models select exact catalog keys
later; their requests never reach a shell. Receipts remain synthetic fixture
evidence, including nonzero statuses, rather than native model shell activity.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from probe import workspaces

_SCOPE = ("--project=synthetic-quotes-prod", "--region=us-central1")
_QUERIES = (
    ("describe", ("run", "services", "describe", "quote-service", *_SCOPE)),
    ("describe", ("run", "revisions", "describe", "quote-service-00042-xom", *_SCOPE)),
    ("describe", ("run", "revisions", "describe", "quote-service-00041-pav", *_SCOPE)),
    ("inventory", ("run", "revisions", "list", "--service=quote-service", *_SCOPE)),
    (
        "logs",
        (
            "logging",
            "read",
            "resource.type=cloud_run_revision AND resource.labels.project_id=synthetic-quotes-prod "
            "AND resource.labels.location=us-central1 AND resource.labels.service_name=quote-service",
            "--project=synthetic-quotes-prod",
            "--limit=100",
            "--order=asc",
        ),
    ),
    ("logs", ("run", "services", "logs", "read", "quote-service", *_SCOPE, "--limit=100")),
    ("inventory", ("logging", "logs", "list", "--project=synthetic-quotes-prod")),
)


def prepare_queries(spec: dict[str, Any], ws: workspaces.Workspace) -> dict[str, dict[str, Any]]:
    """Execute the fixed catalog against the trusted seeded wrapper, never real gcloud.

    The caller binds the scenario, this module and workspace-seeding source to
    the run identity. Shell/startup/timeout and unexpected command failures
    abort preparation. Only declared unavailable observations become receipts.
    """
    if spec.get("id") not in ("build-gcp01-startup-a", "build-gcp01-startup-b"):
        raise ValueError("query preparation only supports the GCP01 startup A/B cases")
    shell = shutil.which("sh")
    if shell is None:
        raise RuntimeError("GCP01 fixture preparation requires POSIX sh; no gcloud fallback")
    env = {
        "PATH": os.pathsep.join((str(Path(sys.executable).parent), str(Path(shell).parent), os.defpath)),
        "STATE_DIR": ws.state_dir.as_posix(),
        "HOME": (ws.root / "home").as_posix(),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if os.name == "nt" and "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    prepared = {}
    for kind, argv in _QUERIES:
        proc = subprocess.run(
            [shell, str(ws.bin_dir / "gcloud"), *argv],
            cwd=ws.repo,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        command = shlex.join(("gcloud", *argv))
        unavailable = (
            proc.returncode == 1 and proc.stdout == "" and proc.stderr.startswith("Fixture observation unavailable:")
        )
        if proc.returncode != 0 and not unavailable:
            raise RuntimeError(f"GCP01 fixture query failed (exit {proc.returncode}): {command}\n{proc.stderr}")
        prepared[command] = {
            "kind": kind,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
        }
    return prepared
