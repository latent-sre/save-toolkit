from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
import platform


REQUIREMENTS = Path(__file__).resolve().parent / "requirements.txt"


def pinned_packages(path: Path = REQUIREMENTS) -> dict[str, str]:
    """Return the image's exact pins; requirements.txt is the only version source."""
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        requirement = line.split("#", 1)[0].strip()
        if not requirement:
            continue
        name, separator, pinned = (part.strip() for part in requirement.partition("=="))
        if not separator or not name or not pinned:
            raise ValueError(f"runner requirement is not an exact pin: {requirement}")
        pins[name.lower()] = pinned
    return pins


def runtime_evidence() -> dict[str, object]:
    """Return versions observed by the executing graph-runner interpreter."""

    return {
        "runtime_version": "graph-runner-runtime/v1",
        "python_version": platform.python_version(),
        "packages": {name: version(name) for name in pinned_packages()},
    }
