#!/usr/bin/env python3
"""Safely synchronize generated Codex custom agents into a project or user scope.

Codex plugins load the generated skills, but custom-agent TOML remains a separate scope. This
installer owns only files carrying ``INSTALL_MARKER``. It preflights every collision before any
write, prunes only stale files that it previously managed, and ``--uninstall`` removes only those
same marker-managed files, so an unmanaged role survives every mode.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts import generate_platform_adapters
except ModuleNotFoundError:
    import generate_platform_adapters  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = REPO_ROOT / ".codex" / "agents"
INSTALL_MARKER = "# Managed by save-toolkit scripts/install_codex_agents.py; do not edit."
# Markers written by earlier releases under a previous plugin name. Ownership is claimed by ANY of
# these, but only INSTALL_MARKER is ever written. Without this, renaming the plugin silently orphans
# every already-installed file: `_is_managed` would stop recognizing them, so neither the stale-file
# prune nor `--uninstall` would touch them, and the user would be left with both generations of the
# fleet side by side in Codex's flat global agents directory. Never drop an entry from this tuple.
LEGACY_INSTALL_MARKERS = (
    "# Managed by sre-agents scripts/install_codex_agents.py; do not edit.",
)


@dataclass(frozen=True)
class PlannedWrite:
    path: Path
    desired: bytes
    expected: bytes | None


@dataclass(frozen=True)
class PlannedRemoval:
    path: Path
    expected: bytes


@dataclass(frozen=True)
class SyncPlan:
    writes: tuple[PlannedWrite, ...]
    removals: tuple[PlannedRemoval, ...]
    conflicts: tuple[Path, ...]

    @property
    def out_of_sync(self) -> bool:
        return bool(self.writes or self.removals or self.conflicts)


def _installed_bytes(source: bytes) -> bytes:
    return f"{INSTALL_MARKER}\n".encode("utf-8") + source


def _is_managed(content: bytes) -> bool:
    first = content.splitlines()[0] if content else b""
    return any(
        first == marker.encode("utf-8")
        for marker in (INSTALL_MARKER, *LEGACY_INSTALL_MARKERS)
    )


def build_sync_plan(source_directory: Path, target_directory: Path) -> SyncPlan:
    sources = {
        source.name: source.read_bytes()
        for source in sorted(source_directory.glob("*.toml"))
        if source.is_file()
    }
    if not sources:
        raise ValueError(f"{source_directory}: no generated Codex agents found")

    writes: list[PlannedWrite] = []
    removals: list[PlannedRemoval] = []
    conflicts: list[Path] = []
    for name, source_content in sources.items():
        target = target_directory / name
        desired = _installed_bytes(source_content)
        if not target.exists():
            writes.append(PlannedWrite(target, desired, None))
            continue
        if not target.is_file():
            conflicts.append(target)
            continue
        current = target.read_bytes()
        if current == desired:
            continue
        if _is_managed(current) or current == source_content:
            writes.append(PlannedWrite(target, desired, current))
        else:
            conflicts.append(target)

    if target_directory.is_dir():
        for target in sorted(target_directory.glob("*.toml")):
            if target.name in sources or not target.is_file():
                continue
            current = target.read_bytes()
            if _is_managed(current):
                removals.append(PlannedRemoval(target, current))
    return SyncPlan(tuple(writes), tuple(removals), tuple(conflicts))


def build_uninstall_plan(target_directory: Path) -> SyncPlan:
    """Plan removal of exactly the marker-managed files, wherever they came from.

    Unmanaged files are never listed, so applying the plan cannot delete a role the installer
    does not own. A missing target directory is an empty plan: uninstall stays idempotent.
    """

    removals: list[PlannedRemoval] = []
    if target_directory.is_dir():
        for target in sorted(target_directory.glob("*.toml")):
            if not target.is_file():
                continue
            current = target.read_bytes()
            if _is_managed(current):
                removals.append(PlannedRemoval(target, current))
    return SyncPlan((), tuple(removals), ())


class ConcurrentChangeError(ValueError):
    """The target changed after the plan was built; no changed bytes may be overwritten."""


def _publish_new(path: Path, content: bytes) -> None:
    """Publish a complete file only if the target name is still absent."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # A same-directory hard link is an atomic create-if-absent operation on supported
            # filesystems. Unlike os.replace, it cannot overwrite a concurrently created file.
            os.link(temporary, path)
        except FileExistsError as exc:
            raise ConcurrentChangeError(f"{path}: target appeared after preflight; refusing overwrite") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _claim_existing(path: Path) -> Path:
    """Atomically move the current name aside so its exact bytes can be verified."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_claim = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".claim")
    os.close(descriptor)
    claim = Path(raw_claim)
    try:
        os.replace(path, claim)
    except OSError:
        claim.unlink(missing_ok=True)
        raise ConcurrentChangeError(f"{path}: target disappeared or changed type after preflight")
    return claim


def _restore_claim(claim: Path, path: Path) -> None:
    """Restore claimed bytes without overwriting a concurrent replacement."""

    try:
        os.link(claim, path)
    except FileExistsError as exc:
        raise ConcurrentChangeError(
            f"{path}: concurrent replacement preserved; prior bytes remain at {claim}"
        ) from exc
    claim.unlink()


def _claim_expected(path: Path, expected: bytes) -> Path:
    claim = _claim_existing(path)
    if claim.read_bytes() == expected:
        return claim
    try:
        _restore_claim(claim, path)
    except ConcurrentChangeError:
        raise
    raise ConcurrentChangeError(f"{path}: content changed after preflight; restored without overwrite")


def apply_sync_plan(plan: SyncPlan) -> None:
    if plan.conflicts:
        rendered = ", ".join(str(path) for path in plan.conflicts)
        raise ValueError(f"refusing to overwrite unmanaged Codex agents: {rendered}")
    for write in plan.writes:
        if write.expected is None:
            _publish_new(write.path, write.desired)
            continue
        claim = _claim_expected(write.path, write.expected)
        try:
            _publish_new(write.path, write.desired)
        except (OSError, ValueError):
            _restore_claim(claim, write.path)
            raise
        claim.unlink()
    for removal in plan.removals:
        claim = _claim_expected(removal.path, removal.expected)
        # Delete the claimed inode only. A concurrently created file at the original name survives.
        claim.unlink()


def _user_agents_directory() -> Path:
    configured = os.environ.get("CODEX_HOME")
    if configured:
        home = Path(configured).expanduser().resolve()
        if not home.is_dir():
            raise ValueError(f"CODEX_HOME is not an existing directory: {home}")
    else:
        home = (Path.home() / ".codex").resolve()
    return home / "agents"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--user", action="store_true", help="use CODEX_HOME/agents")
    target.add_argument("--target", type=Path, help="explicit Codex agents directory")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report drift without writing")
    mode.add_argument(
        "--uninstall",
        action="store_true",
        help="remove only marker-managed files; unmanaged roles are left untouched",
    )
    args = parser.parse_args(argv)

    try:
        destination = _user_agents_directory() if args.user else args.target.expanduser().resolve()
        if destination == SOURCE_DIRECTORY.resolve():
            raise ValueError("target is the generated source directory; choose another Codex scope")
        if args.uninstall:
            plan = build_uninstall_plan(destination)
        else:
            adapter_failures = generate_platform_adapters.validate_generated_outputs(REPO_ROOT)
            if adapter_failures:
                for failure in adapter_failures:
                    print(failure, file=sys.stderr)
                return 2
            plan = build_sync_plan(SOURCE_DIRECTORY, destination)
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.uninstall:
        try:
            apply_sync_plan(plan)
        except (OSError, ValueError) as exc:
            print(f"Codex agent uninstall failed: {exc}", file=sys.stderr)
            return 2
        print(f"Removed {len(plan.removals)} managed Codex agent file(s) from {destination}.")
        return 0
    if plan.conflicts:
        for conflict in plan.conflicts:
            print(f"{conflict}: unmanaged file conflicts with a save-toolkit role", file=sys.stderr)
        return 2
    if args.check:
        if plan.out_of_sync:
            print(f"Codex agents are not synchronized: {len(plan.writes)} update(s), {len(plan.removals)} stale file(s).")
            return 1
        print("Codex agents are synchronized.")
        return 0
    try:
        apply_sync_plan(plan)
    except (OSError, ValueError) as exc:
        print(f"Codex agent synchronization failed: {exc}", file=sys.stderr)
        return 2
    print(f"Synchronized {len(plan.writes)} Codex agent file(s) to {destination}; removed {len(plan.removals)} stale file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
