from __future__ import annotations

from importlib.metadata import version
import platform


RUNTIME_PACKAGES = (
    "httpx",
    "langgraph",
    "langgraph-checkpoint-sqlite",
)


def runtime_evidence() -> dict[str, object]:
    """Return versions observed by the executing graph-runner interpreter."""

    return {
        "runtime_version": "graph-runner-runtime/v1",
        "python_version": platform.python_version(),
        "packages": {name: version(name) for name in RUNTIME_PACKAGES},
    }
