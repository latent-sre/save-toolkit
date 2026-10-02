"""Closed, revision-bound source snapshots for the fleet knowledge atlas.

Reads Git objects and repository files; never imports or executes inspected sources.
Generated atlas output never enters the corpus; untracked canonical inputs fail closed.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from fleet_atlas_v2_model import Span, canonical_bytes, digest, validate_path


OUTPUT_ROOTS = ("docs/fleet-atlas/generated/", "docs/fleet-atlas/v2/")
SOURCE_ROOTS = ("agents/", "skills/", "commands/", "docs/", "schemas/", "hooks/",
                "scripts/", "evals/", ".github/", "platforms/", "com.github.copilot/")
ROOT_SOURCES = frozenset({"AGENTS.md", "CLAUDE.md", "README.md", "CHANGELOG.md",
                          "CONTRIBUTING.md", ".claude-plugin/plugin.json",
                          ".claude-plugin/marketplace.json", "requirements-dev.txt",
                          "requirements-test.txt", "pyproject.toml", ".python-version"})


def is_source(path: str) -> bool:
    return (not path.startswith(OUTPUT_ROOTS)
            and (path in ROOT_SOURCES or path.startswith(SOURCE_ROOTS)))


def git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, input=input_bytes,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise ValueError(f"git {' '.join(args[:2])} failed: "
                         + result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


@dataclass(frozen=True, order=True)
class Source:
    path: str
    content: bytes

    def __post_init__(self) -> None:
        validate_path(self.path)
        if type(self.content) is not bytes:
            raise TypeError("source content must be immutable bytes")

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    @property
    def lines(self) -> tuple[str, ...]:
        return tuple(self.text.splitlines())

    def span(self, start: int, end: int) -> Span:
        return Span.from_bytes(self.path, self.content, start, end)

    def locate(self, needle: str) -> tuple[Span, ...]:
        """All exact occurrences; an absent needle is never assigned fabricated line 1."""
        if not needle:
            raise ValueError("empty source locator")
        matches = tuple(self.span(i, i) for i, line in enumerate(self.lines, 1) if needle in line)
        if not matches:
            raise ValueError(f"needle absent from {self.path}: {needle!r}")
        return matches


@dataclass(frozen=True)
class Snapshot:
    revision: str
    sources: tuple[Source, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.sources, tuple) or any(not isinstance(s, Source) for s in self.sources):
            raise TypeError("snapshot sources must be an immutable tuple")
        paths = [s.path for s in self.sources]
        if paths != sorted(set(paths)):
            raise ValueError("snapshot requires unique, sorted source paths")

    @property
    def tree_digest(self) -> str:
        return digest(canonical_bytes([(s.path, digest(s.content)) for s in self.sources]))

    def source(self, path: str) -> Source:
        for source in self.sources:
            if source.path == path:
                return source
        raise ValueError(f"source outside closed corpus: {path}")

    def verify_span(self, span: Span) -> None:
        span.verify(self.source(span.path).content)


def read_revision(root: Path, revision: str) -> Snapshot:
    """Read named Git objects in one batch, retaining Git's cross-platform bytes."""
    resolved = git(root, "rev-parse", "--verify", f"{revision}^{{commit}}").decode().strip()
    entries = git(root, "ls-tree", "-rz", resolved).split(b"\0")
    paths_and_ids: list[tuple[str, str]] = []
    for entry in entries:
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8")
        if not is_source(path):
            continue
        validate_path(path)
        if kind != "blob" or mode not in ("100644", "100755"):
            raise ValueError(f"non-regular source is not supported: {path}")
        paths_and_ids.append((path, oid))
    paths_and_ids.sort()
    requests = "".join(oid + "\n" for _, oid in paths_and_ids).encode("ascii")
    data = git(root, "cat-file", "--batch", input_bytes=requests)
    offset = 0
    sources: list[Source] = []
    for path, expected_oid in paths_and_ids:
        end = data.index(b"\n", offset)
        oid, kind, size_text = data[offset:end].decode("ascii").split()
        if oid != expected_oid or kind != "blob":
            raise ValueError(f"unexpected Git object for {path}")
        size = int(size_text)
        start = end + 1
        content = data[start:start + size]
        if len(content) != size or data[start + size:start + size + 1] != b"\n":
            raise ValueError(f"truncated Git object for {path}")
        sources.append(Source(path, content))
        offset = start + size + 1
    if offset != len(data):
        raise ValueError("unexpected trailing Git object data")
    return Snapshot(resolved, tuple(sources))


def current_snapshot(root: Path) -> Snapshot:
    """Refuse modified tracked inputs and untracked canonical inputs alike."""
    before = git(root, "rev-parse", "HEAD").decode().strip()
    # -z --name-only avoids display quoting, spaces and rename-arrow ambiguity.
    changes = git(root, "diff", "--no-renames", "--name-only", "-z", "HEAD", "--").split(b"\0")
    # Tracked diffs omit a newly created, never-added canonical file, which would
    # otherwise yield a verified snapshot that silently drops that guidance.
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    dirty = [raw.decode("utf-8") for raw in changes + untracked
             if raw and is_source(raw.decode("utf-8"))]
    if dirty:
        raise ValueError(f"dirty canonical inputs: {sorted(dirty)}")
    snapshot = read_revision(root, before)
    after = git(root, "rev-parse", "HEAD").decode().strip()
    changed_after = git(root, "diff", "--no-renames", "--name-only", "-z", "HEAD", "--")
    untracked_after = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if (before != after or changed_after != b"\0".join(changes)
            or untracked_after != b"\0".join(untracked)):
        raise ValueError("repository changed while reading atlas inputs")
    return snapshot


def verify_revision(root: Path, recorded: str, snapshot: Snapshot) -> None:
    """Every reachable recorded revision must match, including nonancestor commits."""
    previous = read_revision(root, recorded)
    if previous.tree_digest != snapshot.tree_digest:
        raise ValueError("recorded revision has different canonical inputs")
